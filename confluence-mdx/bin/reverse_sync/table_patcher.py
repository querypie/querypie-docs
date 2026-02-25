"""테이블 블록 패치 — MDX table 블록 변경을 XHTML에 패치한다."""
import html as html_module
import re
from typing import Dict, List, Optional

from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.sidecar import SidecarEntry, find_mapping_by_sidecar


def is_markdown_table(content: str) -> bool:
    """Content가 Markdown table 형식인지 판별한다."""
    lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        return False
    pipe_lines = sum(1 for l in lines if l.startswith('|') and l.endswith('|'))
    return pipe_lines >= 2


def split_table_rows(content: str) -> List[str]:
    """Markdown table content를 데이터 행(non-separator) 목록으로 분리한다."""
    rows = []
    for line in content.strip().split('\n'):
        s = line.strip()
        if not s:
            continue
        # separator 행 건너뛰기 (| --- | --- | ...)
        if re.match(r'^\|[\s\-:|]+\|$', s):
            continue
        if s.startswith('|') and s.endswith('|'):
            rows.append(s)
    return rows


def normalize_table_row(row: str) -> str:
    """Markdown table row를 XHTML plain text 대응 형태로 변환한다."""
    cells = [c.strip() for c in row.split('|')[1:-1]]
    parts = []
    for cell in cells:
        s = cell
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'`([^`]+)`', r'\1', s)
        s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', s)
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
        s = re.sub(
            r'<Badge\s+color="([^"]+)">(.*?)</Badge>',
            lambda m: m.group(2) + m.group(1).capitalize(),
            s,
        )
        s = re.sub(r'<[^>]+/?>', '', s)
        s = html_module.unescape(s)
        s = s.strip()
        if s:
            parts.append(s)
    return ' '.join(parts)


def build_table_row_patches(
    change: BlockChange,
    mappings: List[BlockMapping],
    used_ids: 'set | None' = None,
    mdx_to_sidecar: Optional[Dict[int, SidecarEntry]] = None,
    xpath_to_mapping: Optional[Dict[str, 'BlockMapping']] = None,
) -> List[Dict[str, str]]:
    """Markdown table 블록의 변경된 행을 XHTML table에 패치한다.

    sidecar를 통해 parent table mapping을 찾아 containing block으로 사용한다.
    """
    from reverse_sync.patch_builder import _flush_containing_changes

    old_rows = split_table_rows(change.old_block.content)
    new_rows = split_table_rows(change.new_block.content)
    if len(old_rows) != len(new_rows):
        return []

    # sidecar에서 parent mapping 획득
    container = None
    if mdx_to_sidecar is not None and xpath_to_mapping is not None:
        container = find_mapping_by_sidecar(
            change.index, mdx_to_sidecar, xpath_to_mapping)

    if container is None:
        return []

    patches = []
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    for old_row, new_row in zip(old_rows, new_rows):
        if old_row == new_row:
            continue
        old_plain = normalize_table_row(old_row)
        new_plain = normalize_table_row(new_row)
        if not old_plain or old_plain == new_plain:
            continue
        bid = container.block_id
        if bid not in containing_changes:
            containing_changes[bid] = (container, [])
        containing_changes[bid][1].append((old_plain, new_plain))

    patches.extend(_flush_containing_changes(containing_changes, used_ids))
    return patches
