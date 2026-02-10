"""Reverse Sync — MDX 변경사항을 Confluence XHTML에 역반영하는 파이프라인.

중간 파일은 var/<page_id>/ 에 reverse-sync. prefix로 저장된다.
"""
import argparse
import difflib
import html as html_module
import json
import re
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

from reverse_sync.mdx_block_parser import parse_mdx_blocks, MdxBlock
from reverse_sync.block_diff import diff_blocks, BlockChange
from reverse_sync.mapping_recorder import record_mapping, BlockMapping
from reverse_sync.xhtml_patcher import patch_xhtml
from reverse_sync.roundtrip_verifier import verify_roundtrip
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
    """src/content/ko/...mdx 경로에서 pages.yaml을 이용해 page_id를 유도한다."""
    rel = ko_mdx_path.removeprefix('src/content/ko/').removesuffix('.mdx')
    path_parts = rel.split('/')
    pages_path = _PROJECT_DIR / 'var' / 'pages.yaml'
    if not pages_path.exists():
        raise ValueError("var/pages.yaml not found")
    pages = yaml.safe_load(pages_path.read_text())
    for page in pages:
        if page.get('path') == path_parts:
            return page['page_id']
    raise ValueError(f"MDX path '{ko_mdx_path}' not found in var/pages.yaml")


def _resolve_attachment_dir(page_id: str) -> str:
    """page_id에서 pages.yaml의 path를 조회하여 attachment-dir를 반환."""
    pages = yaml.safe_load((_PROJECT_DIR / 'var' / 'pages.yaml').read_text())
    for page in pages:
        if page['page_id'] == page_id:
            return '/' + '/'.join(page['path'])
    raise ValueError(f"page_id '{page_id}' not found in var/pages.yaml")


def _forward_convert(patched_xhtml_path: str, output_mdx_path: str, page_id: str) -> str:
    """patched XHTML 파일을 forward converter로 MDX로 변환한다.

    입력 파일이 var/<page_id>/ 에 직접 있으므로 메타데이터를 자동 발견한다.
    모든 경로를 절대 경로로 변환하여 cwd에 의존하지 않도록 한다.
    """
    bin_dir = Path(__file__).parent
    converter = bin_dir / 'converter' / 'cli.py'
    var_dir = (_PROJECT_DIR / 'var' / page_id).resolve()

    abs_input = Path(patched_xhtml_path).resolve()
    abs_output = Path(output_mdx_path).resolve()
    attachment_dir = _resolve_attachment_dir(page_id)
    result = subprocess.run(
        [sys.executable, str(converter), '--log-level', 'warning',
         str(abs_input), str(abs_output),
         '--public-dir', str(var_dir.parent),
         '--attachment-dir', attachment_dir,
         '--skip-image-copy'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Forward converter failed: {result.stderr}")
    return abs_output.read_text()


def _clean_reverse_sync_artifacts(page_id: str) -> Path:
    """var/<page_id>/ 내의 이전 reverse-sync 산출물을 정리하고 var_dir을 반환한다."""
    var_dir = _PROJECT_DIR / 'var' / page_id
    for f in var_dir.glob('reverse-sync.*'):
        f.unlink()
    verify_mdx = var_dir / 'verify.mdx'
    if verify_mdx.exists():
        verify_mdx.unlink()
    verify_dir = var_dir / 'verify'
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    return var_dir


def run_verify(
    page_id: str,
    original_src: MdxSource,
    improved_src: MdxSource,
    xhtml_path: str = None,
) -> Dict[str, Any]:
    """로컬 검증 파이프라인을 실행한다.

    모든 중간 파일을 var/<page_id>/ 에 reverse-sync. prefix로 저장한다.
    """
    now = datetime.now(timezone.utc).isoformat()
    var_dir = _clean_reverse_sync_artifacts(page_id)

    original_mdx = original_src.content
    improved_mdx = improved_src.content
    if not xhtml_path:
        xhtml_path = str(_PROJECT_DIR / 'var' / page_id / 'page.xhtml')
    xhtml = Path(xhtml_path).read_text()

    # Step 1: MDX 블록 파싱 + Step 2: 블록 Diff 추출
    original_blocks = parse_mdx_blocks(original_mdx)
    improved_blocks = parse_mdx_blocks(improved_mdx)
    changes = diff_blocks(original_blocks, improved_blocks)

    if not changes:
        result = {'page_id': page_id, 'created_at': now,
                  'status': 'no_changes', 'changes_count': 0,
                  'mdx_diff_report': '', 'xhtml_diff_report': ''}
        (var_dir / 'reverse-sync.result.yaml').write_text(
            yaml.dump(result, allow_unicode=True, default_flow_style=False))
        return result

    # diff.yaml 저장
    diff_data = {
        'page_id': page_id, 'created_at': now,
        'original_mdx': original_src.descriptor, 'improved_mdx': improved_src.descriptor,
        'changes': [
            {'index': c.index, 'block_id': f'{c.old_block.type}-{c.index}',
             'change_type': c.change_type,
             'old_content': c.old_block.content, 'new_content': c.new_block.content}
            for c in changes
        ],
    }
    (var_dir / 'reverse-sync.diff.yaml').write_text(
        yaml.dump(diff_data, allow_unicode=True, default_flow_style=False))

    # Step 3: 원본 매핑 생성 → mapping.original.yaml 저장
    original_mappings = record_mapping(xhtml)
    original_mapping_data = {
        'page_id': page_id, 'created_at': now, 'source_xhtml': 'page.xhtml',
        'blocks': [m.__dict__ for m in original_mappings],
    }
    (var_dir / 'reverse-sync.mapping.original.yaml').write_text(
        yaml.dump(original_mapping_data, allow_unicode=True, default_flow_style=False))

    # Step 4: XHTML 패치 → patched.xhtml 저장
    patches = _build_patches(changes, original_blocks, improved_blocks, original_mappings)
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
    _forward_convert(
        str(var_dir / 'reverse-sync.patched.xhtml'),
        str(var_dir / 'verify.mdx'),
        page_id,
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

    status = 'pass' if verify_result.passed else 'fail'
    result = {
        'page_id': page_id, 'created_at': now,
        'status': status,
        'changes_count': len(changes),
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


def _strip_frontmatter(mdx: str) -> str:
    """MDX 문자열에서 YAML frontmatter 블록을 제거한다."""
    if mdx.startswith('---\n'):
        end = mdx.find('\n---\n', 4)
        if end != -1:
            return mdx[end + 5:]
    return mdx


_NON_CONTENT_TYPES = frozenset(('empty', 'frontmatter', 'import_statement'))
_EMOJI_RE = re.compile(
    r'[\U0001F000-\U0001F9FF\u2700-\u27BF\uFE00-\uFE0F\u200D]+'
)


def _normalize_mdx_to_plain(content: str, block_type: str) -> str:
    """MDX 블록 content를 XHTML plain text와 대응하는 형태로 변환한다."""
    text = content.strip()

    if block_type == 'heading':
        return text.lstrip('#').strip()

    lines = text.split('\n')
    parts = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith('<figure') or s.startswith('<img') or s.startswith('</figure'):
            continue
        s = re.sub(r'^\d+\.\s+', '', s)
        s = re.sub(r'^[-*+]\s+', '', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'`([^`]+)`', r'\1', s)
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
        s = re.sub(r'<[^>]+/?>', '', s)
        s = html_module.unescape(s)
        s = s.strip()
        if s:
            parts.append(s)
    return ' '.join(parts)


def _collapse_ws(text: str) -> str:
    """연속 공백을 하나의 스페이스로 축약한다."""
    return ' '.join(text.split())


def _find_mapping_by_text(
    mdx_plain: str,
    mappings: List[BlockMapping],
    exclude: 'set | None' = None,
) -> 'BlockMapping | None':
    """MDX normalized plain text와 가장 잘 매칭되는 XHTML mapping을 찾는다.

    Args:
        exclude: 이미 사용된 mapping block_id 집합. 중복 매칭을 방지한다.
    """
    mdx_norm = _collapse_ws(mdx_plain)
    if not mdx_norm:
        return None

    def _excluded(m):
        return exclude is not None and m.block_id in exclude

    # 1차: 완전 일치
    for m in mappings:
        if _excluded(m):
            continue
        if _collapse_ws(m.xhtml_plain_text) == mdx_norm:
            return m

    # 2차: prefix 일치 (50자 이상) — 길이가 가장 유사한 후보 선택
    min_prefix = 50
    candidates = []
    for m in mappings:
        if _excluded(m):
            continue
        xhtml_norm = _collapse_ws(m.xhtml_plain_text)
        if len(mdx_norm) >= min_prefix and xhtml_norm.startswith(mdx_norm[:min_prefix]):
            candidates.append(m)
        elif len(xhtml_norm) >= min_prefix and mdx_norm.startswith(xhtml_norm[:min_prefix]):
            candidates.append(m)
    if candidates:
        return min(candidates, key=lambda m: abs(len(_collapse_ws(m.xhtml_plain_text)) - len(mdx_norm)))

    # 3차: 공백 무시 비교 (table/html_block/list 등 셀/항목 경계 공백 차이 대응)
    mdx_nospace = re.sub(r'\s+', '', mdx_norm)
    if mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            if mdx_nospace == xhtml_nospace:
                return m

    # 3.5차: 공백+이모지 무시 비교 (Confluence ac:emoticon → MDX 이모지 차이 대응)
    mdx_clean = _EMOJI_RE.sub('', mdx_nospace)
    if mdx_clean and mdx_clean != mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            xhtml_clean = _EMOJI_RE.sub('', xhtml_nospace)
            if mdx_clean == xhtml_clean:
                return m

    # 4차: 리스트 마커 제거 후 공백 무시 비교
    # (ac:adf-content 내 <p> 요소가 "- " 등 리스트 마커를 포함하는 경우 대응)
    mdx_unmarked = _strip_list_marker(mdx_nospace)
    if mdx_unmarked and mdx_unmarked != mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            xhtml_unmarked = _strip_list_marker(xhtml_nospace)
            if mdx_unmarked == xhtml_unmarked:
                return m
    # 양쪽 모두 마커 제거 시도
    if mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            xhtml_unmarked = _strip_list_marker(xhtml_nospace)
            if xhtml_unmarked != xhtml_nospace and mdx_nospace == xhtml_unmarked:
                return m

    return None


def _strip_list_marker(text: str) -> str:
    """공백 없는 텍스트에서 선행 리스트 마커를 제거한다."""
    return re.sub(r'^[-*+]|^\d+\.', '', text)


def _align_chars(source: str, target: str) -> dict:
    """source와 target의 문자를 정렬하여 source index → target index 맵을 반환한다.

    1단계: 비공백 문자를 SequenceMatcher로 전역 정렬 (이모지 drift 방지)
    2단계: 인접 비공백 앵커 사이의 공백을 위치순으로 매핑
    """
    src_nonspace = [(i, c) for i, c in enumerate(source) if not c.isspace()]
    tgt_nonspace = [(i, c) for i, c in enumerate(target) if not c.isspace()]

    src_chars = ''.join(c for _, c in src_nonspace)
    tgt_chars = ''.join(c for _, c in tgt_nonspace)

    matcher = difflib.SequenceMatcher(None, src_chars, tgt_chars, autojunk=False)
    mapping = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                mapping[src_nonspace[i1 + k][0]] = tgt_nonspace[j1 + k][0]

    # 2단계: 인접 앵커 사이의 공백을 위치순으로 매핑
    anchors = sorted(mapping.items())
    boundaries = [(-1, -1)] + anchors + [(len(source), len(target))]
    for idx in range(len(boundaries) - 1):
        s_lo, t_lo = boundaries[idx]
        s_hi, t_hi = boundaries[idx + 1]
        s_spaces = [j for j in range(s_lo + 1, s_hi) if source[j].isspace()]
        t_spaces = [j for j in range(t_lo + 1, t_hi) if target[j].isspace()]
        for s, t in zip(s_spaces, t_spaces):
            mapping[s] = t

    return mapping


def _find_insert_pos(char_map: dict, mdx_pos: int) -> int:
    """MDX 삽입 위치에 대응하는 XHTML 위치를 찾는다."""
    for k in range(mdx_pos - 1, -1, -1):
        if k in char_map:
            return char_map[k] + 1
    return 0


def _transfer_text_changes(mdx_old: str, mdx_new: str, xhtml_text: str) -> str:
    """MDX 블록 간의 텍스트 변경을 XHTML plain text에 전이한다.

    MDX old와 XHTML text의 문자 정렬(alignment)을 구축하고,
    MDX old→new 변경의 위치를 XHTML 상의 위치로 매핑하여 적용한다.
    이를 통해 XHTML의 공백 구조를 보존하면서 콘텐츠만 업데이트한다.
    """
    # 1. MDX old ↔ XHTML text 문자 정렬
    char_map = _align_chars(mdx_old, xhtml_text)

    # 2. MDX old → new 변경 추출
    matcher = difflib.SequenceMatcher(None, mdx_old, mdx_new)

    # 3. 변경을 XHTML 위치로 매핑
    edits = []  # (xhtml_start, xhtml_end, replacement)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        replacement = mdx_new[j1:j2] if tag != 'delete' else ''
        if tag in ('replace', 'delete'):
            mapped = sorted(char_map[k] for k in range(i1, i2) if k in char_map)
            if not mapped:
                continue  # MDX 전용 공백 — XHTML에 대응 없음
            edits.append((mapped[0], mapped[-1] + 1, replacement))
        elif tag == 'insert':
            xpos = _find_insert_pos(char_map, i1)
            edits.append((xpos, xpos, replacement))

    # 4. 역순 적용 (위치 보존)
    chars = list(xhtml_text)
    for xstart, xend, repl in reversed(edits):
        chars[xstart:xend] = list(repl)
    return ''.join(chars)


def _build_patches(
    changes: List[BlockChange],
    original_blocks: List[MdxBlock],
    improved_blocks: List[MdxBlock],
    mappings: List[BlockMapping],
) -> List[Dict[str, str]]:
    """diff 변경과 매핑을 텍스트 기반으로 결합하여 XHTML 패치 목록을 구성한다.

    MDX 블록의 normalized plain text와 XHTML 매핑의 xhtml_plain_text를
    비교하여 올바른 대상 요소를 찾는다.
    """
    patches = []
    used_ids: set = set()  # 이미 매칭된 mapping block_id (중복 매칭 방지)
    for change in changes:
        if change.old_block.type in _NON_CONTENT_TYPES:
            continue

        old_plain = _normalize_mdx_to_plain(
            change.old_block.content, change.old_block.type)
        mapping = _find_mapping_by_text(old_plain, mappings, exclude=used_ids)

        if mapping is None:
            # 리스트 블록: 항목별로 분리하여 개별 매핑 시도
            if change.old_block.type == 'list':
                patches.extend(
                    _build_list_item_patches(change, mappings, used_ids))
            continue

        used_ids.add(mapping.block_id)
        new_block = change.new_block
        new_plain = _normalize_mdx_to_plain(new_block.content, new_block.type)

        # MDX와 XHTML의 공백 구조가 같으면 (paragraph/heading 등)
        # MDX normalized text를 직접 사용.
        # 다르면 (table/html_block/list 등 셀/항목 경계 공백 차이)
        # XHTML 공백 구조를 보존하면서 콘텐츠 변경만 전이.
        if _collapse_ws(old_plain) != _collapse_ws(mapping.xhtml_plain_text):
            new_plain = _transfer_text_changes(
                old_plain, new_plain, mapping.xhtml_plain_text)

        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': mapping.xhtml_plain_text,
            'new_plain_text': new_plain,
        })

    return patches


def _split_list_items(content: str) -> List[str]:
    """리스트 블록 content를 개별 항목으로 분리한다."""
    items = []
    current: List[str] = []
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped:
            if current:
                items.append('\n'.join(current))
                current = []
            continue
        # 새 리스트 항목 시작
        if (re.match(r'^[-*+]\s+', stripped) or re.match(r'^\d+\.\s+', stripped)) and current:
            items.append('\n'.join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        items.append('\n'.join(current))
    return items


def _build_list_item_patches(
    change: BlockChange,
    mappings: List[BlockMapping],
    used_ids: 'set | None' = None,
) -> List[Dict[str, str]]:
    """리스트 블록의 각 항목을 개별 매핑과 대조하여 패치를 생성한다."""
    old_items = _split_list_items(change.old_block.content)
    new_items = _split_list_items(change.new_block.content)
    if len(old_items) != len(new_items):
        return []

    patches = []
    for old_item, new_item in zip(old_items, new_items):
        if old_item == new_item:
            continue
        old_plain = _normalize_mdx_to_plain(old_item, 'list')
        mapping = _find_mapping_by_text(old_plain, mappings, exclude=used_ids)
        if mapping is None:
            continue
        if used_ids is not None:
            used_ids.add(mapping.block_id)
        new_plain = _normalize_mdx_to_plain(new_item, 'list')

        xhtml_text = mapping.xhtml_plain_text
        # XHTML 텍스트에 리스트 마커 prefix가 있으면 제거 후 전이, 이후 복원
        prefix = _extract_list_marker_prefix(xhtml_text)
        if prefix and _collapse_ws(old_plain) != _collapse_ws(xhtml_text):
            xhtml_body = xhtml_text[len(prefix):]
            if _collapse_ws(old_plain) != _collapse_ws(xhtml_body):
                new_plain = _transfer_text_changes(old_plain, new_plain, xhtml_body)
            new_plain = prefix + new_plain
        elif _collapse_ws(old_plain) != _collapse_ws(xhtml_text):
            new_plain = _transfer_text_changes(old_plain, new_plain, xhtml_text)

        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': xhtml_text,
            'new_plain_text': new_plain,
        })
    return patches


def _extract_list_marker_prefix(text: str) -> str:
    """텍스트에서 선행 리스트 마커 prefix를 추출한다."""
    m = re.match(r'^([-*+]\s+|\d+\.\s+)', text)
    return m.group(0) if m else ''


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
  reverse-sync verify <mdx> [--original-mdx <mdx>]
  reverse-sync verify --branch <branch>
  reverse-sync debug  <mdx> [--original-mdx <mdx>]
  reverse-sync debug  --branch <branch>
  reverse-sync push   <mdx> [--original-mdx <mdx>] [--dry-run]
  reverse-sync push   --branch <branch> [--dry-run]
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
    parser.add_argument('--xhtml', help='원본 XHTML 경로 (기본: var/<page-id>/page.xhtml)')
    parser.add_argument('--limit', type=int, default=0,
                        help='배치 모드에서 최대 처리 파일 수 (기본: 0=전체)')
    parser.add_argument('--failures-only', action='store_true',
                        help='실패한 결과만 출력 (--limit와 함께 사용 시 실패 건수 기준으로 제한)')


def _do_verify(args) -> dict:
    """공통 verify 로직: MDX 소스 해석 → run_verify() 실행 → 결과 반환."""
    improved_src = _resolve_mdx_source(args.improved_mdx)
    if args.original_mdx:
        original_src = _resolve_mdx_source(args.original_mdx)
    else:
        ko_path = _extract_ko_mdx_path(improved_src.descriptor)
        original_src = _resolve_mdx_source(f'main:{ko_path}')
    page_id = _resolve_page_id(_extract_ko_mdx_path(improved_src.descriptor))
    return run_verify(
        page_id=page_id,
        original_src=original_src,
        improved_src=improved_src,
        xhtml_path=args.xhtml,
    )


def _do_verify_batch(branch: str, limit: int = 0, failures_only: bool = False) -> List[dict]:
    """브랜치의 모든 변경 ko MDX 파일을 배치 verify 처리한다."""
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
                original_mdx=None, xhtml=None,
            )
            result = _do_verify(args)
            result['file'] = ko_path
            print(result.get('status', 'unknown'), file=sys.stderr)
            results.append(result)
        except Exception as e:
            print("error", file=sys.stderr)
            results.append({'file': ko_path, 'status': 'error', 'error': str(e)})
        if results[-1].get('status') not in ('pass', 'no_changes'):
            failure_count += 1
        if failures_only and limit > 0 and failure_count >= limit:
            break
    return results


def _do_push(page_id: str):
    """verify 통과 후 Confluence에 push한다."""
    var_dir = _PROJECT_DIR / 'var' / page_id
    patched_path = var_dir / 'reverse-sync.patched.xhtml'
    xhtml_body = patched_path.read_text()

    from reverse_sync.confluence_client import ConfluenceConfig, get_page_version, update_page_body
    config = ConfluenceConfig()
    if not config.email or not config.api_token:
        print('Error: ~/.config/atlassian/confluence.conf 파일을 설정하세요. (형식: email:api_token)',
              file=sys.stderr)
        sys.exit(1)

    page_info = get_page_version(config, page_id)
    new_version = page_info['version'] + 1
    resp = update_page_body(config, page_id,
                            title=page_info['title'],
                            version=new_version,
                            xhtml_body=xhtml_body)
    return {
        'page_id': page_id,
        'title': resp.get('title', page_info['title']),
        'version': resp.get('version', {}).get('number', new_version),
        'url': resp.get('_links', {}).get('webui', ''),
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
            if getattr(args, 'branch', None) and (args.original_mdx or args.xhtml):
                print('Error: --branch와 --original-mdx/--xhtml는 동시에 사용할 수 없습니다.', file=sys.stderr)
                sys.exit(1)

            use_json = getattr(args, 'json', False)
            failures_only = getattr(args, 'failures_only', False)

            if getattr(args, 'branch', None):
                # 배치 모드
                results = _do_verify_batch(args.branch, limit=getattr(args, 'limit', 0),
                                           failures_only=failures_only)
                if use_json:
                    output = results
                    if failures_only:
                        output = [r for r in results if r.get('status') not in ('pass', 'no_changes')]
                    print(json.dumps(output, ensure_ascii=False, indent=2))
                else:
                    _print_results(results, show_all_diffs=show_all_diffs,
                                   failures_only=failures_only)
                has_failure = any(r.get('status') not in ('pass', 'no_changes') for r in results)
                if not dry_run:
                    passed = [r for r in results if r.get('status') == 'pass']
                    if has_failure:
                        print(f"Error: 일부 파일이 검증에 실패했습니다. push하지 않습니다.", file=sys.stderr)
                        sys.exit(1)
                    for r in passed:
                        push_result = _do_push(r['page_id'])
                        print(json.dumps(push_result, ensure_ascii=False, indent=2))
                elif has_failure:
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
                    push_result = _do_push(page_id)
                    print(json.dumps(push_result, ensure_ascii=False, indent=2))
                elif not dry_run and result.get('status') != 'pass':
                    print(f"Error: 검증 상태가 '{result.get('status')}'입니다. push하지 않습니다.",
                          file=sys.stderr)
                    sys.exit(1)
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
