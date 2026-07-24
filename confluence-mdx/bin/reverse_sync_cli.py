#!/usr/bin/env python3
"""Reverse Sync — MDX 변경사항을 Confluence XHTML에 역반영하는 파이프라인.

중간 파일은 var/<page_id>/ 에 reverse-sync. prefix로 저장된다.
"""
import argparse
import difflib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import yaml
# 스크립트 위치 기반 경로 상수
_SCRIPT_DIR = Path(__file__).resolve().parent   # confluence-mdx/bin/
_PROJECT_DIR = _SCRIPT_DIR.parent               # confluence-mdx/
_REPO_ROOT = _PROJECT_DIR.parent                # 레포 루트

# Ensure bin/ is on sys.path so local package imports resolve without PYTHONPATH
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from mdx_to_storage.parser import parse_mdx_blocks
from reverse_sync.block_diff import diff_blocks
from reverse_sync.mapping_recorder import record_mapping
from reverse_sync.xhtml_patcher import patch_xhtml
from reverse_sync.roundtrip_verifier import verify_roundtrip
from reverse_sync.planner import plan_patches
from reverse_sync.equivalence import (
    PUSH_EQUIVALENCE_POLICY,
    verify_push_equivalence,
)
from xhtml_beautify_diff import xhtml_diff

_PUSH_VERIFIER_POLICY = PUSH_EQUIVALENCE_POLICY
_TOOL_VERSION = "reverse-sync-cli-v5"


@dataclass
class MdxSource:
    """MDX 파일의 내용과 출처 정보."""
    content: str        # MDX 파일 내용
    descriptor: str     # 출처 표시 (예: "main:src/content/ko/...", 파일 경로 등)


@dataclass(frozen=True)
class ManifestPushSummary:
    """explicit manifest push의 확인 화면에 필요한 immutable identity."""

    manifest_path: Path
    run_id: str
    page_id: str
    title: str
    base_version: int
    candidate_sha256: str
    change_count: int
    operation_count: int


def _is_valid_git_ref(ref: str) -> bool:
    """ref가 유효한 git ref인지 확인한다."""
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', ref],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def _get_file_from_git(ref: str, path: str) -> str:
    """git show <ref>:<path>로 파일 내용을 반환한다."""
    result = subprocess.run(
        ['git', 'show', f'{ref}:{path}'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"Failed to get {path} at ref {ref}: {result.stderr.strip()}")
    return result.stdout


def _resolve_mdx_source(arg: str) -> MdxSource:
    """2-tier MDX 소스 해석: ref:path → 파일 경로."""
    # 1. ref:path 형식
    if ':' in arg:
        ref, path = arg.split(':', 1)
        if _is_valid_git_ref(ref):
            content = _get_file_from_git(ref, path)
            return MdxSource(content=content, descriptor=f'{ref}:{path}')

    # 2. 파일 경로
    if Path(arg).is_file():
        return MdxSource(content=Path(arg).read_text(), descriptor=arg)

    raise ValueError(f"Cannot resolve MDX source '{arg}': not a file path or ref:path")


def _extract_ko_mdx_path(descriptor: str) -> str:
    """descriptor에서 src/content/ko/...mdx 경로를 추출한다."""
    path = descriptor.split(':', 1)[-1] if ':' in descriptor else descriptor
    prefix = 'src/content/ko/'
    if prefix in path and path.endswith('.mdx'):
        idx = path.index(prefix)
        return path[idx:]
    raise ValueError(f"Cannot extract ko MDX path from '{descriptor}'")


def _get_changed_ko_mdx_files(branch: str) -> List[str]:
    """브랜치에서 변경된 src/content/ko/**/*.mdx 파일 목록을 반환한다."""
    if not _is_valid_git_ref(branch):
        raise ValueError(f"Invalid git ref: {branch}")
    result = subprocess.run(
        ['git', 'diff', '--name-only', f'main...{branch}', '--', 'src/content/ko/'],
        capture_output=True, text=True, cwd=str(_REPO_ROOT),
    )
    if result.returncode != 0:
        raise ValueError(f"Failed to get changed files: {result.stderr.strip()}")
    files = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    return [f for f in files if f.startswith('src/content/ko/') and f.endswith('.mdx')]


def _resolve_page_id(ko_mdx_path: str) -> str:
    """src/content/ko/...mdx 경로에서 pages.qm.yaml을 이용해 page_id를 유도한다."""
    rel = ko_mdx_path.removeprefix('src/content/ko/').removesuffix('.mdx')
    path_parts = rel.split('/')
    pages_path = _PROJECT_DIR / 'var' / 'pages.qm.yaml'
    if not pages_path.exists():
        raise ValueError("var/pages.qm.yaml not found")
    pages = yaml.safe_load(pages_path.read_text())
    for page in pages:
        if page.get('path') == path_parts:
            return page['page_id']
    raise ValueError(f"MDX path '{ko_mdx_path}' not found in var/pages.qm.yaml")


def _resolve_attachment_dir(page_id: str) -> str:
    """page_id에서 pages.qm.yaml의 path를 조회하여 attachment-dir를 반환."""
    pages = yaml.safe_load((_PROJECT_DIR / 'var' / 'pages.qm.yaml').read_text())
    for page in pages:
        if page['page_id'] == page_id:
            return '/' + '/'.join(page['path'])
    raise ValueError(f"page_id '{page_id}' not found in var/pages.qm.yaml")


def _detect_language(descriptor: str) -> str:
    """descriptor에서 src/content/{lang}/ 의 언어 코드를 추출한다. 기본값: 'ko'."""
    path = descriptor.split(':', 1)[-1] if ':' in descriptor else descriptor
    prefix = 'src/content/'
    if prefix in path:
        idx = path.index(prefix) + len(prefix)
        lang = path[idx:].split('/')[0]
        if lang in ('ko', 'ja', 'en'):
            return lang
    return 'ko'


def _forward_convert(patched_xhtml_path: str, output_mdx_path: str, page_id: str,
                     language: str = 'ko', page_dir: str = None) -> str:
    """patched XHTML 파일을 forward converter로 MDX로 변환한다.

    모든 경로를 절대 경로로 변환하여 cwd에 의존하지 않도록 한다.
    page_dir이 주어지면 converter에 --page-dir로 전달하여 page.v1.yaml을 읽는다.
    """
    bin_dir = Path(__file__).parent
    converter = bin_dir / 'converter' / 'cli.py'
    var_dir = (_PROJECT_DIR / 'var' / page_id).resolve()

    abs_input = Path(patched_xhtml_path).resolve()
    abs_output = Path(output_mdx_path).resolve()
    attachment_dir = _resolve_attachment_dir(page_id)

    cmd = [sys.executable, str(converter), '--log-level', 'warning',
           str(abs_input), str(abs_output),
           '--public-dir', str(var_dir.parent),
           '--attachment-dir', attachment_dir,
           '--skip-image-copy',
           '--language', language]
    if page_dir:
        cmd += ['--page-dir', str(Path(page_dir).resolve())]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Forward converter failed: {result.stderr}")
    return abs_output.read_text()


def _clean_reverse_sync_artifacts(page_id: str) -> Path:
    """var/<page_id>/ 내의 이전 reverse-sync 산출물을 정리하고 var_dir을 반환한다."""
    var_dir = _PROJECT_DIR / 'var' / page_id
    var_dir.mkdir(parents=True, exist_ok=True)
    for f in var_dir.glob('reverse-sync.*'):
        if f.name == 'reverse-sync.backup.xhtml':
            continue
        f.unlink()
    verify_mdx = var_dir / 'verify.mdx'
    if verify_mdx.exists():
        verify_mdx.unlink()
    verify_dir = var_dir / 'verify'
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    return var_dir


def _parse_and_diff(original_mdx: str, improved_mdx: str):
    """MDX 블록 파싱 + diff 추출.

    Returns: (changes, alignment, original_blocks, improved_blocks)
    """
    original_blocks = parse_mdx_blocks(original_mdx)
    improved_blocks = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original_blocks, improved_blocks)
    return changes, alignment, original_blocks, improved_blocks


def _save_diff_yaml(
    var_dir: Path, page_id: str, now: str,
    original_descriptor: str, improved_descriptor: str,
    changes,
) -> None:
    """diff.yaml를 var_dir에 저장한다."""
    diff_data = {
        'page_id': page_id, 'created_at': now,
        'original_mdx': original_descriptor, 'improved_mdx': improved_descriptor,
        'changes': [
            {'index': c.index,
             'block_id': f'{(c.old_block or c.new_block).type}-{c.index}',
             'change_type': c.change_type,
             'old_content': c.old_block.content if c.old_block else None,
             'new_content': c.new_block.content if c.new_block else None}
            for c in changes
        ],
    }
    (var_dir / 'reverse-sync.diff.yaml').write_text(
        yaml.dump(diff_data, allow_unicode=True, default_flow_style=False))


def _extract_frontmatter_title(mdx_blocks) -> str:
    """MDX frontmatter에서 title 값을 추출한다."""
    for block in mdx_blocks:
        if block.type != 'frontmatter':
            continue
        for raw_line in block.content.splitlines():
            line = raw_line.strip()
            if not line.startswith('title:'):
                continue
            value = line.split(':', 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                return value[1:-1]
            return value
    return ''


def _compile_result(
    var_dir: Path, page_id: str, now: str,
    changes_count: int,
    mdx_diff_report: str, xhtml_diff_report: str,
    verify_result, roundtrip_diff_report: str, title: str = '',
    skipped_changes: list = None,
) -> Dict[str, Any]:
    """검증 결과를 조립하여 저장하고 반환한다."""
    status = 'pass' if verify_result.passed else 'fail'
    result = {
        'page_id': page_id, 'created_at': now,
        'status': status,
        'push_eligible': False,
        'changes_count': changes_count,
        'mdx_diff_report': mdx_diff_report,
        'xhtml_diff_report': xhtml_diff_report,
        'verification': {
            'exact_match': verify_result.passed,
            'diff_report': roundtrip_diff_report,
        },
    }
    if isinstance(getattr(verify_result, "policy", None), str):
        result["verification"].update(
            policy=verify_result.policy,
            expected_sha256=verify_result.expected_sha256,
            actual_sha256=verify_result.actual_sha256,
        )
    if title:
        result['title'] = title
    if skipped_changes:
        result['skipped_changes'] = skipped_changes
    (var_dir / 'reverse-sync.result.yaml').write_text(
        yaml.dump(result, allow_unicode=True, default_flow_style=False))
    return result


def _blocked_result(
    var_dir: Path,
    page_id: str,
    now: str,
    reason_code: str,
    *,
    detail: str = "",
) -> Dict[str, Any]:
    """push proof가 fail-closed된 결과를 저장한다."""
    result = {
        "page_id": page_id,
        "created_at": now,
        "status": "blocked",
        "push_eligible": False,
        "changes_count": 0,
        "reason_code": reason_code,
    }
    if detail:
        result["detail"] = detail
    (var_dir / "reverse-sync.result.yaml").write_text(
        yaml.dump(result, allow_unicode=True, default_flow_style=False)
    )
    return result


def _find_blockquotes_missing_blank_line(content: str) -> list:
    """blockquote 다음에 빈 줄이 없는 줄 목록을 반환한다.

    forward converter 가 blockquote 이후 항상 빈 줄을 추가하므로,
    improved.mdx 도 동일하게 blockquote 이후 빈 줄을 요구한다.

    fenced code block(```) 내부는 검사하지 않는다.
    multi-line blockquote (연속된 > 줄) 에서는 마지막 줄에서만 검사한다.

    Returns:
        (1-based line number, line content) 튜플의 리스트.
    """
    lines = content.splitlines()
    in_code_block = False
    violations = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code_block = not in_code_block
        if in_code_block:
            continue
        if stripped.startswith('>'):
            next_line = lines[i + 1] if i + 1 < len(lines) else ''
            next_stripped = next_line.strip()
            # 다음 줄이 빈 줄이 아니고 blockquote 도 아닌 경우
            if next_stripped and not next_stripped.startswith('>'):
                violations.append((i + 1, line))
    return violations


def _validate_improved_mdx(content: str, descriptor: str) -> None:
    """improved MDX 입력값을 검증한다. 문제가 있으면 ValueError를 raise한다."""
    trailing_ws_lines = [
        (i + 1, line)
        for i, line in enumerate(content.splitlines())
        if line != line.rstrip()
    ]
    if trailing_ws_lines:
        locations = '\n'.join(
            f'  line {lineno}: {repr(line)}'
            for lineno, line in trailing_ws_lines
        )
        raise ValueError(
            f"Trailing whitespace found in improved MDX ({descriptor}).\n"
            f"This is an input error, not a reverse-sync bug. "
            f"Please remove trailing whitespace before running reverse-sync.\n"
            f"Locations:\n{locations}"
        )

    missing_blank = _find_blockquotes_missing_blank_line(content)
    if missing_blank:
        locations = '\n'.join(
            f'  line {lineno}: {repr(line)}'
            for lineno, line in missing_blank
        )
        raise ValueError(
            f"Blockquote not followed by a blank line in improved MDX ({descriptor}).\n"
            f"Forward converter always adds a blank line after blockquotes. "
            f"Please add a blank line after each blockquote.\n"
            f"Locations:\n{locations}"
        )


def run_verify(
    page_id: str,
    original_src: MdxSource,
    improved_src: MdxSource,
    xhtml_path: str = None,
    lenient: bool = False,
    no_normalize: bool = False,
    language: str = None,
    page_dir: str = None,
    base_snapshot=None,
    attachment_catalog=None,
    for_push: bool = False,
) -> Dict[str, Any]:
    """로컬 검증 파이프라인을 실행한다.

    모든 중간 파일을 var/<page_id>/ 에 reverse-sync. prefix로 저장한다.

    lenient=True면 변경된 행만 검사하는 관대 모드로 검증한다.
    """
    now = datetime.now(timezone.utc).isoformat()
    var_dir = _clean_reverse_sync_artifacts(page_id)

    original_mdx = original_src.content
    improved_mdx = improved_src.content
    dependency_result = None
    link_resolver = None
    attachment_filenames: frozenset[str] = frozenset()

    _validate_improved_mdx(improved_mdx, improved_src.descriptor)

    if for_push and base_snapshot is None:
        return _blocked_result(
            var_dir,
            page_id,
            now,
            "invalid_page_snapshot",
            detail="online push에는 remote PageSnapshot이 필요합니다.",
        )
    if base_snapshot is not None:
        from reverse_sync.base_parity import (
            load_provenance_storage_xhtml,
            verify_base_parity,
            verify_repository_source_identity,
            verify_source_identity,
        )
        from reverse_sync.dependencies import verify_dependencies

        if base_snapshot.page_id != str(page_id) or base_snapshot.status != "current":
            return _blocked_result(
                var_dir,
                page_id,
                now,
                "invalid_page_snapshot",
                detail="snapshot page ID 또는 status가 요청과 다릅니다.",
            )
        pages_path = _PROJECT_DIR / "var" / "pages.qm.yaml"
        source_identity = verify_repository_source_identity(
            base_snapshot,
            original_mdx,
            improved_mdx,
            original_descriptor=original_src.descriptor,
            improved_descriptor=improved_src.descriptor,
            pages_path=pages_path,
        )
        if not source_identity.passed:
            return _blocked_result(
                var_dir,
                page_id,
                now,
                source_identity.reason_code,
                detail=source_identity.diff_report,
            )
        dependency_result, link_resolver = verify_dependencies(
            page_id=page_id,
            original_mdx=original_mdx,
            improved_mdx=improved_mdx,
            pages_path=pages_path,
            attachment_catalog=attachment_catalog,
        )
        if not dependency_result.passed:
            return _blocked_result(
                var_dir,
                page_id,
                now,
                dependency_result.reason_code,
                detail=dependency_result.detail,
            )
        attachment_filenames = frozenset(
            requirement.filename
            for requirement in dependency_result.evidence.attachments
        )

        base_xhtml_path = var_dir / "reverse-sync.base.xhtml"
        base_mdx_path = var_dir / "reverse-sync.base.mdx"
        base_xhtml_path.write_text(base_snapshot.storage_xhtml)
        _forward_convert(
            str(base_xhtml_path),
            str(base_mdx_path),
            page_id,
            language=language or _detect_language(improved_src.descriptor),
            page_dir=page_dir,
        )
        converted_base_mdx = base_mdx_path.read_text()
        provenance_dir = (
            Path(page_dir)
            if page_dir
            else _PROJECT_DIR / "var" / page_id
        )
        base_parity = verify_base_parity(
            base_snapshot,
            original_mdx,
            converted_base_mdx,
            provenance_storage_xhtml=load_provenance_storage_xhtml(
                provenance_dir / "page.v1.yaml",
                expected_page_id=page_id,
            ),
            require_confluence_url=True,
        )
        if not base_parity.passed:
            return _blocked_result(
                var_dir,
                page_id,
                now,
                base_parity.reason_code,
                detail=base_parity.diff_report,
            )
        xhtml_path = str(base_xhtml_path)
        xhtml = base_snapshot.storage_xhtml
    else:
        if not xhtml_path:
            xhtml_path = str(_PROJECT_DIR / 'var' / page_id / 'page.xhtml')
        xhtml = Path(xhtml_path).read_text()

    # Step 1-2: MDX 파싱 + diff
    changes, alignment, original_blocks, improved_blocks = _parse_and_diff(
        original_mdx, improved_mdx)
    title = _extract_frontmatter_title(improved_blocks)

    if not changes:
        result = {'page_id': page_id, 'created_at': now,
                  'status': 'no_changes', 'changes_count': 0,
                  'push_eligible': False,
                  'mdx_diff_report': '', 'xhtml_diff_report': ''}
        if title:
            result['title'] = title
        (var_dir / 'reverse-sync.result.yaml').write_text(
            yaml.dump(result, allow_unicode=True, default_flow_style=False))
        return result

    _save_diff_yaml(var_dir, page_id, now,
                    original_src.descriptor, improved_src.descriptor, changes)

    # Step 3.5: Roundtrip sidecar v3 구축 — mapping.yaml 재생성 없이 v3 경로로 동작
    from reverse_sync.sidecar import (
        build_sidecar,
        load_page_lost_info,
    )
    # forward converter가 생성한 mapping.yaml에서 lost_info만 로드
    page_lost_info = load_page_lost_info(str(var_dir / 'mapping.yaml'))
    roundtrip_sidecar = build_sidecar(xhtml, original_mdx, page_id=page_id)

    # Step 3+4: typed plan → validated renderer operation → patched XHTML
    patch_plan, original_mappings = plan_patches(
        changes, original_blocks, improved_blocks,
        page_xhtml=xhtml,
        alignment=alignment,
        page_lost_info=page_lost_info,
        roundtrip_sidecar=roundtrip_sidecar,
        link_resolver=link_resolver,
        attachment_filenames=attachment_filenames,
        allow_text_identity_fallback=not for_push,
        enforce_capabilities=for_push,
        enforce_provenance=for_push,
    )
    skipped_changes = patch_plan.to_legacy_skipped_changes()

    # mapping.original.yaml artifact 저장
    original_mapping_data = {
        'page_id': page_id, 'created_at': now, 'source_xhtml': 'page.xhtml',
        'blocks': [m.__dict__ for m in original_mappings],
    }
    (var_dir / 'reverse-sync.mapping.original.yaml').write_text(
        yaml.dump(original_mapping_data, allow_unicode=True, default_flow_style=False))
    if for_push:
        from reverse_sync.preserving_patcher import render_patch_plan_preserving

        patched_xhtml = render_patch_plan_preserving(
            xhtml,
            patch_plan,
            roundtrip_sidecar,
        )
    else:
        diagnostic_patches = patch_plan.to_patch_dicts()
        patched_xhtml = patch_xhtml(xhtml, diagnostic_patches)
    (var_dir / 'reverse-sync.patched.xhtml').write_text(patched_xhtml)

    # XHTML beautify-diff (page.xhtml → patched.xhtml)
    xhtml_diff_lines = xhtml_diff(
        xhtml, patched_xhtml,
        label_a="page.xhtml", label_b="reverse-sync.patched.xhtml",
    )
    xhtml_diff_report = '\n'.join(xhtml_diff_lines)

    # Step 5: 검증 매핑 생성 → mapping.patched.yaml 저장
    verify_mappings = record_mapping(patched_xhtml)
    verify_mapping_data = {
        'page_id': page_id, 'created_at': now, 'source_xhtml': 'patched.xhtml',
        'blocks': [m.__dict__ for m in verify_mappings],
    }
    (var_dir / 'reverse-sync.mapping.patched.yaml').write_text(
        yaml.dump(verify_mapping_data, allow_unicode=True, default_flow_style=False))

    # Step 6: Forward 변환 → verify.mdx 저장
    # xhtml_path 옆에 있는 page.v1.yaml을 var/<page_id>/로 복사하여
    # forward converter가 크로스 페이지 링크를 정상 해석할 수 있게 한다.
    src_page_v1 = Path(xhtml_path).parent / 'page.v1.yaml'
    dst_page_v1 = var_dir / 'page.v1.yaml'
    if src_page_v1.exists() and not dst_page_v1.exists():
        shutil.copy2(src_page_v1, dst_page_v1)

    lang = language or _detect_language(improved_src.descriptor)
    _forward_convert(
        str(var_dir / 'reverse-sync.patched.xhtml'),
        str(var_dir / 'verify.mdx'),
        page_id,
        language=lang,
        page_dir=page_dir,
    )
    verify_mdx = (var_dir / 'verify.mdx').read_text()
    if for_push:
        candidate_identity = verify_source_identity(
            base_snapshot,
            improved_mdx,
            verify_mdx,
            require_confluence_url=True,
        )
        if not candidate_identity.passed:
            return _blocked_result(
                var_dir,
                page_id,
                now,
                candidate_identity.reason_code,
                detail=candidate_identity.diff_report,
            )

    # MDX input diff (original → improved)
    orig_stripped = _strip_frontmatter(original_mdx)
    impr_stripped = _strip_frontmatter(improved_mdx)
    mdx_input_diff = difflib.unified_diff(
        orig_stripped.splitlines(keepends=True),
        impr_stripped.splitlines(keepends=True),
        fromfile=original_src.descriptor,
        tofile=improved_src.descriptor,
        lineterm='',
    )
    mdx_diff_report = ''.join(mdx_input_diff)

    # Step 7: 완전 일치 검증 → result.yaml 저장
    verify_stripped = _strip_frontmatter(verify_mdx)
    if for_push:
        verify_result = verify_push_equivalence(impr_stripped, verify_stripped)
    else:
        verify_result = verify_roundtrip(
            expected_mdx=impr_stripped,
            actual_mdx=verify_stripped,
            lenient=lenient,
            no_normalize=no_normalize,
        )
    # Roundtrip diff (improved → verify): PASS/FAIL 무관하게 항상 생성
    roundtrip_diff_lines = difflib.unified_diff(
        impr_stripped.splitlines(keepends=True),
        verify_stripped.splitlines(keepends=True),
        fromfile='improved.mdx',
        tofile='verify.mdx (from patched XHTML)',
        lineterm='',
    )
    roundtrip_diff_report = ''.join(roundtrip_diff_lines)

    result = _compile_result(
        var_dir, page_id, now, len(changes),
        mdx_diff_report, xhtml_diff_report,
        verify_result, roundtrip_diff_report, title=title,
        skipped_changes=skipped_changes)

    if for_push:
        from reverse_sync.manifest import create_sync_manifest
        from reverse_sync.models import sha256_text
        from reverse_sync.preserving_patcher import render_patch_plan_preserving
        from reverse_sync.proof import build_local_proof

        plan_json = patch_plan.to_canonical_json()
        (var_dir / "reverse-sync.plan.json").write_text(plan_json)

        deterministic_plan, _ = plan_patches(
            changes,
            original_blocks,
            improved_blocks,
            page_xhtml=xhtml,
            alignment=alignment,
            page_lost_info=page_lost_info,
            roundtrip_sidecar=roundtrip_sidecar,
            link_resolver=link_resolver,
            attachment_filenames=attachment_filenames,
            allow_text_identity_fallback=False,
            enforce_capabilities=True,
            enforce_provenance=True,
        )
        deterministic_plan_json = deterministic_plan.to_canonical_json()
        deterministic_candidate = render_patch_plan_preserving(
            xhtml,
            deterministic_plan,
            roundtrip_sidecar,
        )

        try:
            candidate_sidecar = build_sidecar(
                patched_xhtml,
                verify_mdx,
                page_id=page_id,
            )
            (
                idempotency_changes,
                idempotency_alignment,
                idempotency_original_blocks,
                idempotency_improved_blocks,
            ) = _parse_and_diff(verify_mdx, improved_mdx)
            if not idempotency_changes:
                idempotent_candidate = patched_xhtml
            else:
                (
                    idempotency_plan,
                    _,
                ) = plan_patches(
                    idempotency_changes,
                    idempotency_original_blocks,
                    idempotency_improved_blocks,
                    page_xhtml=patched_xhtml,
                    alignment=idempotency_alignment,
                    page_lost_info=page_lost_info,
                    roundtrip_sidecar=candidate_sidecar,
                    link_resolver=link_resolver,
                    attachment_filenames=attachment_filenames,
                    allow_text_identity_fallback=False,
                    enforce_capabilities=True,
                    enforce_provenance=True,
                )
                idempotent_candidate = (
                    ""
                    if idempotency_plan.issues
                    else render_patch_plan_preserving(
                        patched_xhtml,
                        idempotency_plan,
                        candidate_sidecar,
                    )
                )
        except (ValueError, KeyError):
            idempotent_candidate = ""

        proof = build_local_proof(
            base_xhtml=xhtml,
            improved_mdx=improved_mdx,
            roundtrip_mdx=verify_mdx,
            candidate_xhtml=patched_xhtml,
            sidecar=roundtrip_sidecar,
            changes=changes,
            patches=None,
            skipped_changes=skipped_changes,
            plan_json=plan_json,
            deterministic_plan_json=deterministic_plan_json,
            deterministic_candidate_xhtml=deterministic_candidate,
            idempotent_candidate_xhtml=idempotent_candidate,
            source_identity_passed=True,
            base_parity_passed=True,
            dependency_result=dependency_result,
            plan=patch_plan,
        )
        proof_json = proof.to_canonical_json()
        (var_dir / "reverse-sync.proof.json").write_text(proof_json)

        diagnostics = {}
        if lenient:
            diagnostic = verify_roundtrip(
                expected_mdx=impr_stripped,
                actual_mdx=verify_stripped,
                lenient=True,
            )
            diagnostics["lenient"] = {
                "passed": diagnostic.passed,
                "diff_report": diagnostic.diff_report,
                "push_eligible": False,
            }
        if no_normalize:
            diagnostic = verify_roundtrip(
                expected_mdx=impr_stripped,
                actual_mdx=verify_stripped,
                no_normalize=True,
            )
            diagnostics["raw"] = {
                "passed": diagnostic.passed,
                "diff_report": diagnostic.diff_report,
                "push_eligible": False,
            }

        result.update(
            status=proof.status,
            push_eligible=proof.push_eligible,
            reason_code=proof.blocked_reasons[0] if proof.blocked_reasons else "",
            blocked_reasons=list(proof.blocked_reasons),
            local_gates=[gate.to_dict() for gate in proof.gates],
            verification=proof.equivalence.to_dict(),
        )
        if diagnostics:
            result["diagnostics"] = diagnostics

        if not proof.push_eligible:
            (var_dir / "reverse-sync.result.yaml").write_text(
                yaml.dump(result, allow_unicode=True, default_flow_style=False)
            )
            return result

        manifest_path = create_sync_manifest(
            runs_dir=var_dir / "reverse-sync",
            base=base_snapshot,
            original_mdx=original_mdx,
            original_descriptor=original_src.descriptor,
            improved_mdx=improved_mdx,
            improved_descriptor=improved_src.descriptor,
            patch_plan=plan_json,
            candidate_xhtml=patched_xhtml,
            local_proof=proof_json,
            verifier_policy=_PUSH_VERIFIER_POLICY,
            tool_version=_TOOL_VERSION,
            push_eligible=True,
            gates=proof.gates,
        )
        result.update(
            push_eligible=True,
            manifest_path=str(manifest_path),
            run_id=manifest_path.parent.name,
            base_version=base_snapshot.version,
            base_storage_sha256=base_snapshot.storage_sha256,
            candidate_sha256=sha256_text(patched_xhtml),
        )
        (var_dir / "reverse-sync.manifest.path").write_text(str(manifest_path) + "\n")

    (var_dir / "reverse-sync.result.yaml").write_text(
        yaml.dump(result, allow_unicode=True, default_flow_style=False)
    )
    return result


def _strip_frontmatter(mdx: str) -> str:
    """MDX 문자열에서 YAML frontmatter 블록을 제거한다."""
    if mdx.startswith('---\n'):
        end = mdx.find('\n---\n', 4)
        if end != -1:
            return mdx[end + 5:]
    return mdx


def _supports_color() -> bool:
    """stdout가 컬러 출력을 지원하는지 확인한다."""
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def _print_diff_block(lines: str, label: str, c, BOLD, CYAN, RED, GREEN, DIM) -> None:
    """컬러 diff 블록 하나를 출력한다."""
    print(c(DIM, '─' * 72))
    print(c(BOLD, f'  {label}'))
    for line in lines.splitlines():
        if line.startswith('---') or line.startswith('+++'):
            print(c(BOLD, line))
        elif line.startswith('@@'):
            print(c(CYAN, line))
        elif line.startswith('-'):
            print(c(RED, line))
        elif line.startswith('+'):
            print(c(GREEN, line))
        else:
            print(line)


def _display_status(result: Dict[str, Any]) -> str:
    """출력/요약용 상태를 계산한다. push 실패가 있으면 verify 결과보다 우선한다."""
    push_status = (result.get('push') or {}).get('status')
    if push_status == 'conflict':
        return 'push_conflict'
    if push_status == 'error':
        return 'push_error'
    if push_status == 'postcondition_failed':
        return 'push_postcondition_failed'
    return result.get('status', 'unknown')


def _is_success_status(status: str) -> bool:
    """offline diagnostic pass와 online verified_local을 성공으로 분류한다."""
    return status in ("pass", "verified_local", "no_changes")


def _display_error(result: Dict[str, Any], status: str) -> str:
    """출력용 에러 메시지를 반환한다."""
    if status in ('push_conflict', 'push_error', 'push_postcondition_failed'):
        return (result.get('push') or {}).get('error', '')
    return result.get('error', '')


def _print_results(results: List[Dict[str, Any]], *, show_all_diffs: bool = False,
                   failures_only: bool = False) -> None:
    """검증 결과를 컬러 diff 포맷으로 출력한다.

    show_all_diffs=True (debug 모드): MDX diff, XHTML diff, Verify diff 모두 출력.
    show_all_diffs=False (verify 모드): Verify diff만 출력 (FAIL 시).
    failures_only=True: pass/no_changes 결과를 출력에서 제외.
    """
    use_color = _supports_color()

    def c(code: str, text: str) -> str:
        return f'\033[{code}m{text}\033[0m' if use_color else text

    RED, GREEN, CYAN, YELLOW, BOLD, DIM = '31', '32', '36', '33', '1', '2'

    for r in results:
        status = _display_status(r)
        if failures_only and _is_success_status(status):
            continue
        file_path = r.get('file', r.get('page_id', '?'))
        changes = r.get('changes_count', 0)

        # 상태별 컬러 배지
        if status == 'verified_local':
            badge = c(GREEN, 'VERIFIED LOCAL')
        elif status == 'pass':
            badge = c(GREEN, 'PASS')
        elif status == 'no_changes':
            badge = c(DIM, 'NO CHANGES')
        elif status == 'push_conflict':
            badge = c(YELLOW, 'PUSH CONFLICT')
        elif status == 'push_error':
            badge = c(YELLOW, 'PUSH ERROR')
        elif status == 'push_postcondition_failed':
            badge = c(RED, 'POSTCONDITION FAILED')
        elif status == 'error':
            badge = c(YELLOW, 'ERROR')
        elif status == 'blocked':
            badge = c(RED, 'BLOCKED')
        else:
            badge = c(RED, 'FAIL')

        print(f'\n{c(BOLD, file_path)}  {badge}  ({changes} change(s))')

        # 에러 메시지
        if status in (
            'error',
            'push_conflict',
            'push_error',
            'push_postcondition_failed',
        ):
            print(f'  {c(RED, _display_error(r, status))}')
            continue
        if status == "blocked":
            reason_code = r.get("reason_code", "unknown")
            print(f'  {c(RED, f"reason: {reason_code}")}')

        if show_all_diffs:
            # MDX diff (original → improved)
            mdx_diff_report = r.get('mdx_diff_report', '')
            if mdx_diff_report:
                _print_diff_block(mdx_diff_report,
                                  'MDX diff (original → improved):',
                                  c, BOLD, CYAN, RED, GREEN, DIM)

            # XHTML diff (page.xhtml → patched.xhtml)
            xhtml_diff_report = r.get('xhtml_diff_report', '')
            if xhtml_diff_report:
                _print_diff_block(xhtml_diff_report,
                                  'XHTML diff (page.xhtml → patched.xhtml):',
                                  c, BOLD, CYAN, RED, GREEN, DIM)

            # Verify diff (improved.mdx → verify.mdx)
            diff_report = (r.get('verification') or {}).get('diff_report', '')
            if diff_report:
                _print_diff_block(diff_report,
                                  'Verify diff (improved.mdx → verify.mdx):',
                                  c, BOLD, CYAN, RED, GREEN, DIM)
        else:
            # verify 모드: FAIL 시에만 Verify diff 출력
            diff_report = (r.get('verification') or {}).get('diff_report', '')
            if diff_report:
                _print_diff_block(diff_report,
                                  'Verify diff (improved.mdx → verify.mdx):',
                                  c, BOLD, CYAN, RED, GREEN, DIM)

        # skipped_changes 출력
        skipped = r.get('skipped_changes', [])
        if skipped:
            print(c(DIM, '─' * 72))
            print(c(YELLOW, f'  Skipped changes ({len(skipped)}):'))
            for s in skipped:
                print(f'    [{s["reason"]}] {s["description"]}')

    # 요약
    total = len(results)
    display_statuses = [_display_status(r) for r in results]
    passed = sum(1 for status in display_statuses if status == 'pass')
    verified_local = sum(
        1 for status in display_statuses if status == 'verified_local'
    )
    failed = sum(1 for status in display_statuses if status == 'fail')
    errors = sum(1 for status in display_statuses if status == 'error')
    conflicts = sum(1 for status in display_statuses if status == 'push_conflict')
    push_errors = sum(1 for status in display_statuses if status == 'push_error')
    postcondition_failures = sum(
        1 for status in display_statuses if status == 'push_postcondition_failed'
    )
    no_chg = sum(1 for status in display_statuses if status == 'no_changes')

    parts = []
    if passed:
        parts.append(c(GREEN, f'{passed} passed'))
    if verified_local:
        parts.append(c(GREEN, f'{verified_local} verified local'))
    if failed:
        parts.append(c(RED, f'{failed} failed'))
    if errors:
        parts.append(c(YELLOW, f'{errors} errors'))
    if conflicts:
        parts.append(c(YELLOW, f'{conflicts} conflicts'))
    if push_errors:
        parts.append(c(YELLOW, f'{push_errors} push errors'))
    if postcondition_failures:
        parts.append(c(RED, f'{postcondition_failures} postcondition failures'))
    if no_chg:
        parts.append(c(DIM, f'{no_chg} no changes'))

    print(f'\n{c(BOLD, "Summary:")} {", ".join(parts)} / {total} total')


_USAGE_SUMMARY = """\
reverse-sync — MDX 변경사항을 Confluence XHTML에 역반영

Usage:
  reverse-sync verify <mdx> [--original-mdx <mdx>] [--lenient] [--no-normalize]
  reverse-sync verify --branch <branch> [--lenient] [--no-normalize]
  reverse-sync debug  <mdx> [--original-mdx <mdx>] [--lenient] [--no-normalize]
  reverse-sync debug  --branch <branch> [--lenient] [--no-normalize]
  reverse-sync push   <mdx> [--original-mdx <mdx>] [--dry-run] [--yes] [--lenient] [--no-normalize]
  reverse-sync push   --branch <branch> [--dry-run] [--yes] [--lenient] [--no-normalize]
  reverse-sync push   --manifest <manifest.json> [--yes]
  reverse-sync -h | --help

Commands:
  push     원격 current snapshot을 기준으로 검증 후 Confluence에 반영
           (--dry-run은 manifest까지만 만들고 PUT을 생략)
           (--manifest는 이미 검증한 explicit run을 online verify 없이 발행)
  verify   로컬 page.xhtml 기반 진단 (push_eligible은 항상 false)
  debug    로컬 verify + MDX diff, XHTML diff, Verify diff 상세 출력

Arguments:
  <mdx>
    MDX 소스를 지정한다. 두 가지 형식을 사용할 수 있다:

    ref:path  git ref와 파일 경로를 콜론으로 구분
              예) main:src/content/ko/user-manual/user-agent.mdx
                  proofread/fix-typo:src/content/ko/overview.mdx
                  HEAD~1:src/content/ko/admin/audit.mdx

    path      로컬 파일 시스템 경로
              예) src/content/ko/user-manual/user-agent.mdx
                  /tmp/improved.mdx

    page-id는 경로의 src/content/ko/ 부분에서 var/pages.yaml을 통해
    자동 유도된다.

Options:
  --branch <branch>
    브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 배치 처리한다.
    <mdx>와 동시에 사용할 수 없다.

  --lenient
    관대 모드: trailing whitespace, 날짜 형식 등 XHTML↔MDX 변환기 한계에
    의한 차이를 기본 비교보다 더 넓게 정규화한다.
    진단 결과만 추가하며 online push eligibility에는 영향을 주지 않는다.

Examples:
  # 단일 파일 검증
  reverse-sync verify "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 검증
  reverse-sync verify --branch proofread/fix-typo

  # 검증 + Confluence 반영
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 push
  reverse-sync push --branch proofread/fix-typo

  # 원격 snapshot을 사용하되 PUT은 생략
  reverse-sync push --dry-run "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 이미 검증한 immutable manifest를 명시적으로 발행
  reverse-sync push --manifest \
    var/<page-id>/reverse-sync/<run-id>/manifest.json

Run 'reverse-sync <command> -h' for command-specific help and more examples.
"""

_PUSH_HELP = """\
MDX 변경사항을 검증한 Confluence snapshot에 패치하고, manifest로 결합한 뒤 반영한다.

파이프라인:
  1. version/title/Storage body를 단일 remote PageSnapshot으로 조회
  2. snapshot의 forward conversion과 original MDX base parity 검증
  3. original / improved MDX diff를 snapshot XHTML에 적용
  4. candidate XHTML round-trip과 dependency gate 검증
  5. snapshot/MDX/candidate hash를 immutable SyncManifest로 기록
  6. PUT 직전 remote snapshot과 manifest base를 다시 비교
  7. base version + 1로 한 번만 업데이트하고 persisted snapshot을 재검증

실행별 산출물은 var/<page-id>/reverse-sync/<run-id>/ 에 저장된다.
기존 reverse-sync.* 파일은 진단용 compatibility output이며 push payload가 아니다.

MDX 소스 지정 방식:
  ref:path  git ref와 파일 경로를 콜론으로 구분
            예) main:src/content/ko/user-manual/user-agent.mdx
                proofread/fix-typo:src/content/ko/overview.mdx
  path      로컬 파일 시스템 경로
            예) /tmp/improved.mdx

  --branch <branch>
            브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 배치 처리한다.
            <mdx>, --original-mdx, --xhtml과 동시에 사용할 수 없다.

Examples:
  # 검증 + Confluence 반영
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 검증만 수행 (= verify)
  reverse-sync push --dry-run "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 검증
  reverse-sync verify --branch proofread/fix-typo

  # 브랜치 전체 배치 push
  reverse-sync push --branch proofread/fix-typo

  # 이전 online verify에서 생성한 explicit run을 발행
  reverse-sync push --manifest \\
    var/<page-id>/reverse-sync/<run-id>/manifest.json

  # original을 명시적으로 지정
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx" \\
    --original-mdx "main:src/content/ko/user-manual/user-agent.mdx"

  # 로컬 파일로 검증
  reverse-sync push --dry-run /tmp/improved.mdx \\
    --original-mdx /tmp/original.mdx \\
    --xhtml /tmp/page.xhtml
"""


def _add_common_args(parser: argparse.ArgumentParser):
    """verify/push 공통 인자를 등록한다."""
    parser.add_argument('improved_mdx', nargs='?',
                        help='개선 MDX (ref:path 또는 파일 경로)')
    parser.add_argument('--branch',
                        help='브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 처리')
    parser.add_argument('--original-mdx',
                        help='원본 MDX (ref:path 또는 파일 경로, 기본: main:<improved 경로>)')
    parser.add_argument('--page-dir',
                        help='page.xhtml / page.v1.yaml 등 페이지 데이터 디렉토리 (var/<page-id>/를 대체)')
    parser.add_argument('--page-id',
                        help='page ID를 직접 지정 (기본: improved_mdx 경로에서 자동 유도)')
    parser.add_argument('--limit', type=int, default=0,
                        help='배치 모드에서 최대 처리 파일 수 (기본: 0=전체)')
    parser.add_argument('--failures-only', action='store_true',
                        help='실패한 결과만 출력 (--limit와 함께 사용 시 실패 건수 기준으로 제한)')
    parser.add_argument('--lenient', action='store_true',
                        help='관대 모드: 정규화 후 비교 (기본은 문자 그대로 비교하는 엄격 모드)')
    parser.add_argument('--no-normalize', action='store_true',
                        help='원시 모드: 정규화 없이 비교 (FC/패치 차이의 실제 규모를 확인)')


def _do_verify(args, *, config=None, prepare_push: bool = False) -> dict:
    """공통 verify 로직: MDX 소스 해석 → run_verify() 실행 → 결과 반환."""
    improved_src = _resolve_mdx_source(args.improved_mdx)
    if args.original_mdx:
        original_src = _resolve_mdx_source(args.original_mdx)
    else:
        ko_path = _extract_ko_mdx_path(improved_src.descriptor)
        original_src = _resolve_mdx_source(f'main:{ko_path}')
    if getattr(args, 'page_id', None):
        page_id = args.page_id
    else:
        page_id = _resolve_page_id(_extract_ko_mdx_path(improved_src.descriptor))

    # --page-dir: var/<page_id>/ 를 대체하는 디렉토리 (page.xhtml, page.v1.yaml 제공)
    page_dir = getattr(args, 'page_dir', None)
    xhtml_path = str(Path(page_dir) / 'page.xhtml') if page_dir else None
    base_snapshot = None
    attachment_catalog = None
    if prepare_push:
        from reverse_sync.confluence_client import (
            get_attachment_catalog,
            get_page_snapshot,
        )
        from reverse_sync.dependencies import added_attachment_filenames

        if config is None:
            config = _ensure_confluence_config()
        base_snapshot = get_page_snapshot(config, page_id)
        if added_attachment_filenames(
            original_src.content,
            improved_src.content,
        ):
            attachment_catalog = get_attachment_catalog(config, page_id)

    return run_verify(
        page_id=page_id,
        original_src=original_src,
        improved_src=improved_src,
        xhtml_path=xhtml_path,
        lenient=getattr(args, 'lenient', False),
        no_normalize=getattr(args, 'no_normalize', False),
        page_dir=page_dir,
        base_snapshot=base_snapshot,
        attachment_catalog=attachment_catalog,
        for_push=prepare_push,
    )


def _confirm(prompt: str) -> bool:
    """터미널에서 y/N 확인을 받는다. 비대화형이면 False."""
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        print(file=sys.stderr)
        return False
    except KeyboardInterrupt:
        print(file=sys.stderr)
        raise
    return answer in ('y', 'yes')


def _do_verify_batch(branch: str, limit: int = 0, failures_only: bool = False,
                     push: bool = False, yes: bool = False,
                     lenient: bool = False,
                     no_normalize: bool = False,
                     prepare_push: bool = False) -> List[dict]:
    """브랜치의 변경 ko MDX 파일을 배치 처리한다.

    push=True이면 online verify 전체 완료 후 verified_local 건만 일괄 push한다.
    yes=True이면 확인 프롬프트를 스킵한다.
    lenient=True이면 변경된 행만 검사하는 관대 모드로 검증한다.
    """
    files = _get_changed_ko_mdx_files(branch)
    if not files:
        return [{'status': 'no_changes', 'branch': branch, 'changes_count': 0}]
    total = len(files)
    if limit > 0 and not failures_only:
        files = files[:limit]
    print(f"Processing {'up to ' + str(total) if failures_only and limit > 0 else str(len(files))}/{total} file(s) from branch {branch}...", file=sys.stderr)
    results = []
    failure_count = 0
    online = push or prepare_push
    config = _ensure_confluence_config() if online else None
    for idx, ko_path in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] {ko_path} ... ", end='', file=sys.stderr, flush=True)
        try:
            args = argparse.Namespace(
                improved_mdx=f"{branch}:{ko_path}",
                original_mdx=None,
                lenient=lenient,
                no_normalize=no_normalize,
            )
            if online:
                result = _do_verify(
                    args,
                    config=config,
                    prepare_push=True,
                )
            else:
                result = _do_verify(args)
            if online and result.get("status") == "pass":
                result.update(
                    status="blocked",
                    push_eligible=False,
                    reason_code="diagnostic_result_not_pushable",
                )
            result['file'] = ko_path
            status = result.get('status', 'unknown')
            print(status, file=sys.stderr)
            results.append(result)
        except Exception as e:
            print("error", file=sys.stderr)
            results.append({'file': ko_path, 'status': 'error', 'error': str(e)})
        if not _is_success_status(results[-1].get('status', 'unknown')):
            failure_count += 1
        if not push and failures_only and limit > 0 and failure_count >= limit:
            break

    if not push:
        return results

    # push 대상 집계
    pushable = [
        r for r in results
        if r.get('status') == 'verified_local'
        and r.get('push_eligible') is True
    ]
    if not pushable:
        print("\nPush 대상 없음 (verified_local 0건)", file=sys.stderr)
        return results

    # 확인 프롬프트
    if not yes:
        print(
            f"\n검증 완료: verified_local {len(pushable)}건 / "
            f"전체 {len(results)}건",
            file=sys.stderr,
        )
        if not _confirm(f"{len(pushable)}건을 Confluence에 push 할까요? [y/N] "):
            print("Push 취소", file=sys.stderr)
            return results

    # 일괄 push
    push_count = 0
    for r in pushable:
        page_id = r['page_id']
        try:
            push_result = _do_push(
                page_id,
                config=config,
                manifest_path=r.get("manifest_path"),
            )
            r['push'] = push_result
            push_count += 1
            print(f"  pushed {page_id} (v{push_result.get('version', '?')})", file=sys.stderr)
        except PushConflictError as e:
            r['push'] = {'status': 'conflict', 'error': str(e)}
            print(f"  conflict {page_id}: {e}", file=sys.stderr)
        except Exception as e:
            if getattr(e, "reason_code", "") == "postcondition_failed":
                r['push'] = {'status': 'postcondition_failed', 'error': str(e)}
                print(f"  postcondition failed {page_id}: {e}", file=sys.stderr)
                break
            r['push'] = {'status': 'error', 'error': str(e)}
            print(f"  error {page_id}: {e}", file=sys.stderr)

    print(f"\nPushed {push_count}/{len(pushable)} file(s)", file=sys.stderr)
    return results


class PushConflictError(Exception):
    """Confluence 페이지 버전 충돌 (409)."""
    pass


def _ensure_confluence_config():
    """Confluence 인증 설정을 확인하고 (config, ) 튜플을 반환한다."""
    from reverse_sync.confluence_client import ConfluenceConfig
    config = ConfluenceConfig()
    if not config.email or not config.api_token:
        print('Error: ~/.config/atlassian/confluence.conf 파일을 설정하세요. (형식: email:api_token)',
              file=sys.stderr)
        sys.exit(1)
    return config


def _load_manifest_push_summary(manifest_path: str) -> ManifestPushSummary:
    """explicit manifest의 integrity와 typed plan schema를 PUT 전에 검증합니다."""
    from reverse_sync.manifest import (
        ArtifactTamperedError,
        load_sync_manifest,
        verify_manifest_integrity,
    )

    resolved_path = Path(manifest_path).expanduser().resolve()
    manifest = load_sync_manifest(resolved_path)
    verify_manifest_integrity(resolved_path, manifest)
    if not manifest.push_eligible:
        raise ValueError("push eligible이 아닌 manifest는 발행할 수 없습니다")

    plan_ref = manifest.artifact("patch_plan")
    try:
        plan = json.loads((resolved_path.parent / plan_ref.path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactTamperedError("patch plan JSON을 읽을 수 없습니다") from exc
    if not isinstance(plan, dict) or plan.get("schema_version") != 2:
        raise ArtifactTamperedError("explicit push는 PatchPlan schema v2가 필요합니다")
    if plan.get("intent_complete") is not True:
        raise ArtifactTamperedError(
            "intent_complete가 아닌 PatchPlan은 발행할 수 없습니다"
        )
    intents = plan.get("intents")
    operations = plan.get("operations")
    if not isinstance(intents, list) or not isinstance(operations, list):
        raise ArtifactTamperedError(
            "PatchPlan intents/operations 형식이 올바르지 않습니다"
        )
    operation_count = sum(
        1
        for operation in operations
        if isinstance(operation, dict) and operation.get("executable") is True
    )
    if operation_count < 1:
        raise ArtifactTamperedError("PatchPlan에 executable operation이 없습니다")

    candidate_ref = manifest.artifact("candidate_xhtml")
    return ManifestPushSummary(
        manifest_path=resolved_path,
        run_id=manifest.run_id,
        page_id=manifest.page_id,
        title=manifest.base_title,
        base_version=manifest.base_version,
        candidate_sha256=candidate_ref.sha256,
        change_count=len(intents),
        operation_count=operation_count,
    )


def _do_push(page_id: str, config=None, *, manifest_path: str):
    """verified manifest에 결합된 candidate만 안전하게 push한다."""
    from reverse_sync.confluence_client import ConfluenceGateway, VersionConflictError
    from reverse_sync.manifest import load_sync_manifest
    from reverse_sync.publisher import publish_verified_manifest

    if config is None:
        config = _ensure_confluence_config()

    if not manifest_path:
        raise ValueError("push에는 explicit manifest_path가 필요합니다")

    var_dir = _PROJECT_DIR / 'var' / page_id
    summary = _load_manifest_push_summary(manifest_path)
    resolved_manifest_path = summary.manifest_path
    manifest = load_sync_manifest(resolved_manifest_path)
    if manifest.page_id != str(page_id):
        raise ValueError(
            f"manifest page ID({manifest.page_id})와 요청 page ID({page_id})가 다릅니다."
        )

    def semantic_verifier(snapshot, verified_manifest_path: Path) -> bool:
        improved_ref = manifest.artifact("improved_mdx")
        expected_mdx = (
            verified_manifest_path.parent / improved_ref.path
        ).read_text()
        persisted_xhtml_path = verified_manifest_path.parent / "postcondition.xhtml"
        persisted_mdx_path = verified_manifest_path.parent / "postcondition.mdx"
        persisted_xhtml_path.write_text(snapshot.storage_xhtml)
        _forward_convert(
            str(persisted_xhtml_path),
            str(persisted_mdx_path),
            page_id,
            language=_detect_language(manifest.improved_descriptor),
            page_dir=str(var_dir),
        )
        actual_mdx = persisted_mdx_path.read_text()
        from reverse_sync.base_parity import verify_source_identity

        identity = verify_source_identity(
            snapshot,
            expected_mdx,
            actual_mdx,
            require_confluence_url=True,
        )
        if not identity.passed:
            return False
        return verify_push_equivalence(
            _strip_frontmatter(expected_mdx),
            _strip_frontmatter(actual_mdx),
        ).passed

    try:
        receipt = publish_verified_manifest(
            resolved_manifest_path,
            ConfluenceGateway(config),
            semantic_verifier=semantic_verifier,
        )
    except VersionConflictError as exc:
        raise PushConflictError(
            f"페이지 {page_id} ({manifest.base_title})가 preflight 이후 변경되었습니다. "
            "최신 snapshot으로 online verify를 다시 실행하세요."
        ) from exc

    backup_path = var_dir / 'reverse-sync.backup.xhtml'
    var_dir.mkdir(parents=True, exist_ok=True)
    base_ref = manifest.artifact("base_xhtml")
    shutil.copy2(resolved_manifest_path.parent / base_ref.path, backup_path)

    return {
        'page_id': page_id,
        'status': receipt.status.value,
        'title': receipt.title,
        'version': receipt.version,
        'url': '',
        'backup': str(backup_path),
        'manifest_path': str(resolved_manifest_path),
        'manifest_sha256': receipt.manifest_sha256,
    }


def main():
    # -h/--help 또는 인자 없음 → 사용법 출력 (argparse 자동 생성 우회)
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        print(_USAGE_SUMMARY, file=sys.stderr if len(sys.argv) < 2 else sys.stdout)
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    parser = argparse.ArgumentParser(prog='reverse-sync', add_help=False)
    subparsers = parser.add_subparsers(dest='command')

    # push (primary command)
    push_parser = subparsers.add_parser(
        'push', prog='reverse-sync push',
        description=_PUSH_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(push_parser)
    push_parser.add_argument('--dry-run', action='store_true',
                             help='검증만 수행, Confluence 반영 안 함 (= verify)')
    push_parser.add_argument(
        '--manifest',
        help='online verify에서 생성한 explicit manifest.json을 발행',
    )
    push_parser.add_argument('--yes', '-y', action='store_true',
                             help='확인 프롬프트 없이 바로 push (CI/자동화용)')
    push_parser.add_argument('--json', action='store_true',
                             help='결과를 JSON 형식으로 출력')

    # verify (= push --dry-run alias)
    verify_parser = subparsers.add_parser(
        'verify', prog='reverse-sync verify',
        description=_PUSH_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(verify_parser)
    verify_parser.add_argument('--json', action='store_true',
                               help='결과를 JSON 형식으로 출력')

    # debug (= verify + 상세 diff 출력)
    debug_parser = subparsers.add_parser(
        'debug', prog='reverse-sync debug',
        description='verify와 동일하되 MDX diff, XHTML diff, Verify diff를 모두 출력한다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(debug_parser)
    debug_parser.add_argument('--json', action='store_true',
                              help='결과를 JSON 형식으로 출력')

    args = parser.parse_args()

    if args.command in ('verify', 'push', 'debug'):
        dry_run = args.command in ('verify', 'debug') or getattr(args, 'dry_run', False)
        show_all_diffs = args.command == 'debug'

        try:
            explicit_manifest = getattr(args, "manifest", None)
            if explicit_manifest:
                conflicting = (
                    args.improved_mdx
                    or getattr(args, "branch", None)
                    or args.original_mdx
                    or getattr(args, "page_dir", None)
                    or getattr(args, "page_id", None)
                    or getattr(args, "limit", 0)
                    or getattr(args, "failures_only", False)
                    or getattr(args, "lenient", False)
                    or getattr(args, "no_normalize", False)
                    or getattr(args, "dry_run", False)
                )
                if conflicting:
                    print(
                        "Error: --manifest는 MDX/branch/diagnostic 옵션과 "
                        "동시에 사용할 수 없습니다.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                auto_yes = getattr(args, "yes", False)
                if not auto_yes and not sys.stdin.isatty():
                    print(
                        "Error: 비대화형 환경에서는 --yes 옵션이 필요합니다.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                summary = _load_manifest_push_summary(explicit_manifest)
                if not auto_yes:
                    prompt = (
                        f"Push verified run {summary.run_id} "
                        f"{summary.title} ({summary.page_id}) "
                        f"v{summary.base_version}→v{summary.base_version + 1}, "
                        f"{summary.change_count} change(s), "
                        f"{summary.operation_count} operation(s), "
                        f"candidate {summary.candidate_sha256[:12]} "
                        "to Confluence? [y/N] "
                    )
                    if not _confirm(prompt):
                        print("Push 취소", file=sys.stderr)
                        sys.exit(0)
                config = _ensure_confluence_config()
                push_result = _do_push(
                    summary.page_id,
                    config=config,
                    manifest_path=str(summary.manifest_path),
                )
                print(json.dumps(push_result, ensure_ascii=False, indent=2))
                return

            # 인자 검증
            if not args.improved_mdx and not getattr(args, 'branch', None):
                print('Error: <mdx> 또는 --branch 중 하나를 지정하세요.', file=sys.stderr)
                sys.exit(1)
            if args.improved_mdx and getattr(args, 'branch', None):
                print('Error: <mdx>와 --branch는 동시에 사용할 수 없습니다.', file=sys.stderr)
                sys.exit(1)
            if getattr(args, 'branch', None) and args.original_mdx:
                print('Error: --branch와 --original-mdx는 동시에 사용할 수 없습니다.', file=sys.stderr)
                sys.exit(1)

            use_json = getattr(args, 'json', False)
            failures_only = getattr(args, 'failures_only', False)

            auto_yes = getattr(args, 'yes', False)

            if not dry_run and not auto_yes and not sys.stdin.isatty():
                print('Error: 비대화형 환경에서는 --yes 옵션이 필요합니다.', file=sys.stderr)
                sys.exit(1)

            if getattr(args, 'branch', None):
                # 배치 모드
                batch_kwargs = {
                    "limit": getattr(args, "limit", 0),
                    "failures_only": failures_only,
                    "push": not dry_run,
                    "yes": auto_yes,
                    "lenient": getattr(args, "lenient", False),
                    "no_normalize": getattr(args, "no_normalize", False),
                }
                if args.command == "push" and dry_run:
                    batch_kwargs["prepare_push"] = True
                results = _do_verify_batch(args.branch, **batch_kwargs)
                if use_json:
                    output = results
                    if failures_only:
                        output = [r for r in results
                                  if not _is_success_status(
                                      r.get('status', 'unknown')
                                  )
                                  or r.get('push', {}).get('status')
                                  in ('conflict', 'error', 'postcondition_failed')]
                    print(json.dumps(output, ensure_ascii=False, indent=2))
                else:
                    _print_results(results, show_all_diffs=show_all_diffs,
                                   failures_only=failures_only)
                has_failure = any(
                    not _is_success_status(r.get('status', 'unknown'))
                    for r in results
                )
                has_push_failure = any(
                    r.get('push', {}).get('status')
                    in ('conflict', 'error', 'postcondition_failed')
                    for r in results
                )
                if has_failure or has_push_failure:
                    sys.exit(1)
            else:
                # 기존 단일 파일 모드
                config = _ensure_confluence_config() if args.command == 'push' else None
                result = _do_verify(
                    args,
                    config=config,
                    prepare_push=args.command == 'push',
                )
                if use_json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    _print_results([result], show_all_diffs=show_all_diffs)

                if (not dry_run
                        and result.get('status') == 'verified_local'
                        and result.get('push_eligible') is True):
                    page_id = result['page_id']
                    title = result.get('title', page_id)
                    if not auto_yes:
                        base_version = result.get("base_version", "?")
                        target_version = (
                            base_version + 1 if isinstance(base_version, int) else "?"
                        )
                        candidate_hash = result.get("candidate_sha256", "unknown")[:12]
                        changes_count = result.get("changes_count", 0)
                        prompt = (
                            f"Push {title} ({page_id}) "
                            f"v{base_version}→v{target_version}, "
                            f"{changes_count} change(s), "
                            f"candidate {candidate_hash} to Confluence? [y/N] "
                        )
                        if not _confirm(prompt):
                            print("Push 취소", file=sys.stderr)
                            sys.exit(0)
                    try:
                        push_result = _do_push(
                            page_id,
                            config=config,
                            manifest_path=result.get("manifest_path"),
                        )
                        print(json.dumps(push_result, ensure_ascii=False, indent=2))
                    except PushConflictError as e:
                        print(f"Error: {e}", file=sys.stderr)
                        sys.exit(1)
                    except Exception as e:
                        reason_code = getattr(e, "reason_code", "push_error")
                        print(f"Error [{reason_code}]: {e}", file=sys.stderr)
                        sys.exit(1)
                elif result.get('status') == 'no_changes':
                    if not dry_run:
                        print(
                            "변경 사항이 없어 Confluence update를 생략합니다.",
                            file=sys.stderr,
                        )
                elif (
                    args.command == "push"
                    and result.get('status') != 'verified_local'
                ):
                    print(f"Error: 검증 상태가 '{result.get('status')}'입니다. push하지 않습니다.",
                          file=sys.stderr)
                    sys.exit(1)
                elif (args.command == "push"
                      and result.get("status") == "verified_local"
                      and result.get("push_eligible") is not True):
                    print("Error: online verify 결과가 push eligible 상태가 아닙니다.",
                          file=sys.stderr)
                    sys.exit(1)
        except PushConflictError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            reason_code = getattr(e, "reason_code", "reverse_sync_error")
            print(f"Error [{reason_code}]: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
