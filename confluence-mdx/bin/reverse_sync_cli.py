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
from reverse_sync.patch_builder import build_patches
from xhtml_beautify_diff import xhtml_diff


@dataclass
class MdxSource:
    """MDX 파일의 내용과 출처 정보."""
    content: str        # MDX 파일 내용
    descriptor: str     # 출처 표시 (예: "main:src/content/ko/...", 파일 경로 등)


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


def _compile_result(
    var_dir: Path, page_id: str, now: str,
    changes_count: int,
    mdx_diff_report: str, xhtml_diff_report: str,
    verify_result, roundtrip_diff_report: str,
) -> Dict[str, Any]:
    """검증 결과를 조립하여 저장하고 반환한다."""
    status = 'pass' if verify_result.passed else 'fail'
    result = {
        'page_id': page_id, 'created_at': now,
        'status': status,
        'changes_count': changes_count,
        'mdx_diff_report': mdx_diff_report,
        'xhtml_diff_report': xhtml_diff_report,
        'verification': {
            'exact_match': verify_result.passed,
            'diff_report': roundtrip_diff_report,
        },
    }
    (var_dir / 'reverse-sync.result.yaml').write_text(
        yaml.dump(result, allow_unicode=True, default_flow_style=False))
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
    language: str = None,
    page_dir: str = None,
) -> Dict[str, Any]:
    """로컬 검증 파이프라인을 실행한다.

    모든 중간 파일을 var/<page_id>/ 에 reverse-sync. prefix로 저장한다.

    lenient=True면 변경된 행만 검사하는 관대 모드로 검증한다.
    """
    now = datetime.now(timezone.utc).isoformat()
    var_dir = _clean_reverse_sync_artifacts(page_id)

    original_mdx = original_src.content
    improved_mdx = improved_src.content

    _validate_improved_mdx(improved_mdx, improved_src.descriptor)

    if not xhtml_path:
        xhtml_path = str(_PROJECT_DIR / 'var' / page_id / 'page.xhtml')
    xhtml = Path(xhtml_path).read_text()

    # Step 1-2: MDX 파싱 + diff
    changes, alignment, original_blocks, improved_blocks = _parse_and_diff(
        original_mdx, improved_mdx)

    if not changes:
        result = {'page_id': page_id, 'created_at': now,
                  'status': 'no_changes', 'changes_count': 0,
                  'mdx_diff_report': '', 'xhtml_diff_report': ''}
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

    # Step 3+4: XHTML 패치 → patched.xhtml 저장
    # build_patches()가 내부에서 record_mapping()을 호출하여 mappings를 생성한다
    patches, original_mappings = build_patches(
        changes, original_blocks, improved_blocks,
        page_xhtml=xhtml,
        alignment=alignment,
        page_lost_info=page_lost_info,
        roundtrip_sidecar=roundtrip_sidecar,
    )

    # mapping.original.yaml artifact 저장
    original_mapping_data = {
        'page_id': page_id, 'created_at': now, 'source_xhtml': 'page.xhtml',
        'blocks': [m.__dict__ for m in original_mappings],
    }
    (var_dir / 'reverse-sync.mapping.original.yaml').write_text(
        yaml.dump(original_mapping_data, allow_unicode=True, default_flow_style=False))
    patched_xhtml = patch_xhtml(xhtml, patches)
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
    verify_result = verify_roundtrip(
        expected_mdx=impr_stripped,
        actual_mdx=verify_stripped,
        lenient=lenient,
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

    return _compile_result(
        var_dir, page_id, now, len(changes),
        mdx_diff_report, xhtml_diff_report,
        verify_result, roundtrip_diff_report)


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
        status = r.get('status', 'unknown')
        if failures_only and status in ('pass', 'no_changes'):
            continue
        file_path = r.get('file', r.get('page_id', '?'))
        changes = r.get('changes_count', 0)

        # 상태별 컬러 배지
        if status == 'pass':
            badge = c(GREEN, 'PASS')
        elif status == 'no_changes':
            badge = c(DIM, 'NO CHANGES')
        elif status == 'error':
            badge = c(YELLOW, 'ERROR')
        else:
            badge = c(RED, 'FAIL')

        print(f'\n{c(BOLD, file_path)}  {badge}  ({changes} change(s))')

        # 에러 메시지
        if status == 'error':
            print(f'  {c(RED, r.get("error", ""))}')
            continue

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

    # 요약
    total = len(results)
    passed = sum(1 for r in results if r.get('status') == 'pass')
    failed = sum(1 for r in results if r.get('status') == 'fail')
    errors = sum(1 for r in results if r.get('status') == 'error')
    no_chg = sum(1 for r in results if r.get('status') == 'no_changes')

    parts = []
    if passed:
        parts.append(c(GREEN, f'{passed} passed'))
    if failed:
        parts.append(c(RED, f'{failed} failed'))
    if errors:
        parts.append(c(YELLOW, f'{errors} errors'))
    if no_chg:
        parts.append(c(DIM, f'{no_chg} no changes'))

    print(f'\n{c(BOLD, "Summary:")} {", ".join(parts)} / {total} total')


_USAGE_SUMMARY = """\
reverse-sync — MDX 변경사항을 Confluence XHTML에 역반영

Usage:
  reverse-sync verify <mdx> [--original-mdx <mdx>] [--lenient]
  reverse-sync verify --branch <branch> [--lenient]
  reverse-sync debug  <mdx> [--original-mdx <mdx>] [--lenient]
  reverse-sync debug  --branch <branch> [--lenient]
  reverse-sync push   <mdx> [--original-mdx <mdx>] [--dry-run] [--yes] [--lenient]
  reverse-sync push   --branch <branch> [--dry-run] [--yes] [--lenient]
  reverse-sync -h | --help

Commands:
  push     verify 수행 후 Confluence에 반영 (--dry-run으로 검증만 가능)
  verify   push --dry-run의 alias
  debug    verify + MDX diff, XHTML diff, Verify diff 상세 출력

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
    의한 차이를 정규화한 후 비교한다. 기본 동작은 정규화 없이 문자 그대로
    비교하는 엄격 모드이다.

Examples:
  # 단일 파일 검증
  reverse-sync verify "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 검증
  reverse-sync verify --branch proofread/fix-typo

  # 검증 + Confluence 반영
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 push
  reverse-sync push --branch proofread/fix-typo

  # push --dry-run = verify
  reverse-sync push --dry-run "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

Run 'reverse-sync <command> -h' for command-specific help and more examples.
"""

_PUSH_HELP = """\
MDX 변경사항을 XHTML에 패치하고, round-trip 검증 후 Confluence에 반영한다.

파이프라인:
  1. original / improved MDX를 블록 단위로 파싱
  2. 블록 diff 추출
  3. 원본 XHTML 블록 매핑 생성
  4. XHTML 패치 적용
  5. 패치된 XHTML을 다시 MDX로 forward 변환 (round-trip)
  6. improved MDX와 비교하여 pass/fail 판정
  7. pass인 경우 Confluence API로 업데이트 (--dry-run 시 생략)

중간 산출물은 var/<page-id>/ 에 reverse-sync.* prefix로 저장된다.

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


def _do_verify(args) -> dict:
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

    return run_verify(
        page_id=page_id,
        original_src=original_src,
        improved_src=improved_src,
        xhtml_path=xhtml_path,
        lenient=getattr(args, 'lenient', False),
        page_dir=page_dir,
    )


def _confirm(prompt: str) -> bool:
    """터미널에서 y/N 확인을 받는다. 비대화형이면 False."""
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return False
    return answer in ('y', 'yes')


def _do_verify_batch(branch: str, limit: int = 0, failures_only: bool = False,
                     push: bool = False, yes: bool = False,
                     lenient: bool = False) -> List[dict]:
    """브랜치의 변경 ko MDX 파일을 배치 처리한다.

    push=True이면 verify 전체 완료 후 pass 건만 일괄 push한다.
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
    for idx, ko_path in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] {ko_path} ... ", end='', file=sys.stderr, flush=True)
        try:
            args = argparse.Namespace(
                improved_mdx=f"{branch}:{ko_path}",
                original_mdx=None,
                lenient=lenient,
            )
            result = _do_verify(args)
            result['file'] = ko_path
            status = result.get('status', 'unknown')
            print(status, file=sys.stderr)
            results.append(result)
        except Exception as e:
            print("error", file=sys.stderr)
            results.append({'file': ko_path, 'status': 'error', 'error': str(e)})
        if results[-1].get('status') not in ('pass', 'no_changes'):
            failure_count += 1
        if failures_only and limit > 0 and failure_count >= limit:
            break

    if not push:
        return results

    # push 대상 집계
    pushable = [r for r in results if r.get('status') == 'pass']
    if not pushable:
        print("\nPush 대상 없음 (pass 0건)", file=sys.stderr)
        return results

    # 확인 프롬프트
    if not yes:
        print(f"\n검증 완료: pass {len(pushable)}건 / 전체 {len(results)}건", file=sys.stderr)
        if not _confirm(f"{len(pushable)}건을 Confluence에 push 할까요? [y/N] "):
            print("Push 취소", file=sys.stderr)
            return results

    # 일괄 push
    config = _ensure_confluence_config()
    push_count = 0
    for r in pushable:
        page_id = r['page_id']
        try:
            push_result = _do_push(page_id, config=config)
            r['push'] = push_result
            push_count += 1
            print(f"  pushed {page_id} (v{push_result.get('version', '?')})", file=sys.stderr)
        except PushConflictError as e:
            r['push'] = {'status': 'conflict', 'error': str(e)}
            print(f"  conflict {page_id}: {e}", file=sys.stderr)
        except Exception as e:
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


def _do_push(page_id: str, config=None):
    """verify 통과 후 Confluence에 push한다.

    1. 현재 페이지 XHTML을 백업 (reverse-sync.backup.xhtml)
    2. patched XHTML을 Confluence에 push
    3. 409 충돌 시 PushConflictError 발생
    """
    from reverse_sync.confluence_client import get_page_version, get_page_body, update_page_body
    import requests as _requests

    if config is None:
        config = _ensure_confluence_config()

    var_dir = _PROJECT_DIR / 'var' / page_id
    patched_path = var_dir / 'reverse-sync.patched.xhtml'
    xhtml_body = patched_path.read_text()

    # 1) 현재 페이지 정보 조회 + XHTML 백업
    page_info = get_page_version(config, page_id)
    current_xhtml = get_page_body(config, page_id)
    backup_path = var_dir / 'reverse-sync.backup.xhtml'
    backup_path.write_text(current_xhtml)

    # 2) push (optimistic locking — version mismatch → 409)
    new_version = page_info['version'] + 1
    try:
        resp = update_page_body(config, page_id,
                                title=page_info['title'],
                                version=new_version,
                                xhtml_body=xhtml_body)
    except _requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            raise PushConflictError(
                f"페이지 {page_id} ({page_info['title']})가 Confluence에서 변경되었습니다. "
                f"fetch로 최신 버전을 가져온 후 다시 시도하세요."
            ) from e
        raise

    return {
        'page_id': page_id,
        'title': resp.get('title', page_info['title']),
        'version': resp.get('version', {}).get('number', new_version),
        'url': resp.get('_links', {}).get('webui', ''),
        'backup': str(backup_path),
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

            if getattr(args, 'branch', None):
                # 배치 모드
                results = _do_verify_batch(args.branch, limit=getattr(args, 'limit', 0),
                                           failures_only=failures_only, push=not dry_run,
                                           yes=auto_yes,
                                           lenient=getattr(args, 'lenient', False))
                if use_json:
                    output = results
                    if failures_only:
                        output = [r for r in results if r.get('status') not in ('pass', 'no_changes')]
                    print(json.dumps(output, ensure_ascii=False, indent=2))
                else:
                    _print_results(results, show_all_diffs=show_all_diffs,
                                   failures_only=failures_only)
                has_failure = any(r.get('status') not in ('pass', 'no_changes') for r in results)
                has_push_failure = any(
                    r.get('push', {}).get('status') in ('conflict', 'error')
                    for r in results
                )
                if has_failure or has_push_failure:
                    sys.exit(1)
            else:
                # 기존 단일 파일 모드
                result = _do_verify(args)
                if use_json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    _print_results([result], show_all_diffs=show_all_diffs)

                if not dry_run and result.get('status') == 'pass':
                    page_id = result['page_id']
                    title = result.get('title', page_id)
                    if not auto_yes:
                        if not _confirm(f"Push {title} ({page_id}) to Confluence? [y/N] "):
                            print("Push 취소", file=sys.stderr)
                            sys.exit(0)
                    try:
                        push_result = _do_push(page_id)
                        print(json.dumps(push_result, ensure_ascii=False, indent=2))
                    except PushConflictError as e:
                        print(f"Error: {e}", file=sys.stderr)
                        sys.exit(1)
                elif not dry_run and result.get('status') != 'pass':
                    print(f"Error: 검증 상태가 '{result.get('status')}'입니다. push하지 않습니다.",
                          file=sys.stderr)
                    sys.exit(1)
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
