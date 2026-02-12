"""패치 빌더 — MDX diff 변경과 XHTML 매핑을 결합하여 XHTML 패치를 생성."""
import html as html_module
import re
from typing import Dict, List, Optional

from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.mdx_block_parser import MdxBlock
from reverse_sync.text_normalizer import (
    normalize_mdx_to_plain, collapse_ws, strip_list_marker,
)
from reverse_sync.text_transfer import transfer_text_changes
from reverse_sync.sidecar_lookup import find_mapping_by_sidecar, SidecarEntry


NON_CONTENT_TYPES = frozenset(('empty', 'frontmatter', 'import_statement'))


def build_patches(
    changes: List[BlockChange],
    original_blocks: List[MdxBlock],
    improved_blocks: List[MdxBlock],
    mappings: List[BlockMapping],
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
) -> List[Dict[str, str]]:
    """diff 변경과 매핑을 결합하여 XHTML 패치 목록을 구성한다.

    sidecar 인덱스를 사용하여 O(1) 직접 조회를 수행한다.
    """
    patches = []
    used_ids: set = set()  # 이미 매칭된 mapping block_id (중복 매칭 방지)
    # child → parent 역참조 맵 (부모-자식 간 중복 매칭 방지)
    child_to_parent: dict = {}
    for m in mappings:
        for child_id in m.children:
            child_to_parent[child_id] = m.block_id

    # block_id → BlockMapping 인덱스 (child 해석용)
    id_to_mapping: Dict[str, BlockMapping] = {m.block_id: m for m in mappings}

    def _mark_used(block_id: str, m: BlockMapping):
        """매핑 사용 시 부모/자식도 함께 사용 완료로 표시."""
        used_ids.add(block_id)
        for child_id in m.children:
            used_ids.add(child_id)
        parent_id = child_to_parent.get(block_id)
        if parent_id:
            used_ids.add(parent_id)

    # 상위 블록에 대한 그룹화된 변경
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    for change in changes:
        if change.old_block.type in NON_CONTENT_TYPES:
            continue

        old_plain = normalize_mdx_to_plain(
            change.old_block.content, change.old_block.type)

        # Sidecar 직접 조회 (O(1))
        mapping = find_mapping_by_sidecar(
            change.index, mdx_to_sidecar, xpath_to_mapping)

        # Parent mapping → child 해석 시도
        if mapping is not None and mapping.children:
            child = _resolve_child_mapping(
                old_plain, mapping, id_to_mapping)
            if child is not None:
                mapping = child
            else:
                # Child 해석 실패 → parent를 containing block으로 사용
                new_plain = normalize_mdx_to_plain(
                    change.new_block.content, change.new_block.type)
                bid = mapping.block_id
                if bid not in containing_changes:
                    containing_changes[bid] = (mapping, [])
                containing_changes[bid][1].append((old_plain, new_plain))
                continue

        if mapping is None:
            # sidecar에 없는 블록 → list/table 분리 시도, 그 외는 skip
            if change.old_block.type == 'list':
                patches.extend(
                    build_list_item_patches(
                        change, mappings, used_ids,
                        mdx_to_sidecar, xpath_to_mapping, id_to_mapping))
                continue

            if is_markdown_table(change.old_block.content):
                patches.extend(
                    build_table_row_patches(
                        change, mappings, used_ids,
                        mdx_to_sidecar, xpath_to_mapping))
                continue

            # sidecar에 매핑되지 않은 블록 → skip
            continue

        _mark_used(mapping.block_id, mapping)
        new_block = change.new_block
        new_plain = normalize_mdx_to_plain(new_block.content, new_block.type)

        if collapse_ws(old_plain) != collapse_ws(mapping.xhtml_plain_text):
            new_plain = transfer_text_changes(
                old_plain, new_plain, mapping.xhtml_plain_text)

        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': mapping.xhtml_plain_text,
            'new_plain_text': new_plain,
        })

    # 상위 블록에 대한 그룹화된 변경 적용
    for bid, (mapping, item_changes) in containing_changes.items():
        xhtml_text = mapping.xhtml_plain_text
        for old_plain, new_plain in item_changes:
            xhtml_text = transfer_text_changes(
                old_plain, new_plain, xhtml_text)
        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': mapping.xhtml_plain_text,
            'new_plain_text': xhtml_text,
        })
        used_ids.add(bid)

    return patches


def _resolve_child_mapping(
    old_plain: str,
    parent_mapping: BlockMapping,
    id_to_mapping: Dict[str, BlockMapping],
) -> Optional[BlockMapping]:
    """Parent mapping의 children 중에서 old_plain과 일치하는 child를 찾는다."""
    old_norm = collapse_ws(old_plain)
    if not old_norm:
        return None

    # 1차: collapse_ws 완전 일치
    for child_id in parent_mapping.children:
        child = id_to_mapping.get(child_id)
        if child and collapse_ws(child.xhtml_plain_text) == old_norm:
            return child

    # 2차: 공백 무시 완전 일치
    old_nospace = re.sub(r'\s+', '', old_norm)
    for child_id in parent_mapping.children:
        child = id_to_mapping.get(child_id)
        if child:
            child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
            if child_nospace == old_nospace:
                return child

    # 3차: 리스트 마커 제거 후 비교 (XHTML child가 "- text" 형식인 경우)
    for child_id in parent_mapping.children:
        child = id_to_mapping.get(child_id)
        if child:
            child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
            child_unmarked = strip_list_marker(child_nospace)
            if child_unmarked != child_nospace and old_nospace == child_unmarked:
                return child

    # 4차: MDX 쪽 리스트 마커 제거 후 비교
    old_unmarked = strip_list_marker(old_nospace)
    if old_unmarked != old_nospace:
        for child_id in parent_mapping.children:
            child = id_to_mapping.get(child_id)
            if child:
                child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
                if old_unmarked == child_nospace:
                    return child

    return None


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

    for bid, (mapping, item_changes) in containing_changes.items():
        xhtml_text = mapping.xhtml_plain_text
        for old_plain, new_plain in item_changes:
            xhtml_text = transfer_text_changes(
                old_plain, new_plain, xhtml_text)
        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': mapping.xhtml_plain_text,
            'new_plain_text': xhtml_text,
        })
        if used_ids is not None:
            used_ids.add(bid)

    return patches


def split_list_items(content: str) -> List[str]:
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


def build_list_item_patches(
    change: BlockChange,
    mappings: List[BlockMapping],
    used_ids: 'set | None' = None,
    mdx_to_sidecar: Optional[Dict[int, SidecarEntry]] = None,
    xpath_to_mapping: Optional[Dict[str, 'BlockMapping']] = None,
    id_to_mapping: Optional[Dict[str, BlockMapping]] = None,
) -> List[Dict[str, str]]:
    """리스트 블록의 각 항목을 개별 매핑과 대조하여 패치를 생성한다.

    sidecar에서 얻은 parent mapping의 children을 통해 child 매핑을 해석한다.
    """
    old_items = split_list_items(change.old_block.content)
    new_items = split_list_items(change.new_block.content)
    if len(old_items) != len(new_items):
        return []

    # sidecar에서 parent mapping 획득
    parent_mapping = None
    if mdx_to_sidecar is not None and xpath_to_mapping is not None:
        parent_mapping = find_mapping_by_sidecar(
            change.index, mdx_to_sidecar, xpath_to_mapping)

    patches = []
    # 매칭 실패한 항목을 상위 블록 기준으로 그룹화
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    for old_item, new_item in zip(old_items, new_items):
        if old_item == new_item:
            continue
        old_plain = normalize_mdx_to_plain(old_item, 'list')

        # parent mapping의 children에서 child 해석 시도
        mapping = None
        if parent_mapping is not None and parent_mapping.children and id_to_mapping is not None:
            mapping = _resolve_child_mapping(
                old_plain, parent_mapping, id_to_mapping)

        if mapping is not None:
            # child 매칭: 기존 로직대로 패치 생성
            if used_ids is not None:
                used_ids.add(mapping.block_id)
            new_plain = normalize_mdx_to_plain(new_item, 'list')

            xhtml_text = mapping.xhtml_plain_text
            prefix = extract_list_marker_prefix(xhtml_text)
            if prefix and collapse_ws(old_plain) != collapse_ws(xhtml_text):
                xhtml_body = xhtml_text[len(prefix):]
                if collapse_ws(old_plain) != collapse_ws(xhtml_body):
                    new_plain = transfer_text_changes(
                        old_plain, new_plain, xhtml_body)
                new_plain = prefix + new_plain
            elif collapse_ws(old_plain) != collapse_ws(xhtml_text):
                new_plain = transfer_text_changes(
                    old_plain, new_plain, xhtml_text)

            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': xhtml_text,
                'new_plain_text': new_plain,
            })
        else:
            # child 매칭 실패: parent를 containing block으로 사용
            if parent_mapping is not None:
                new_plain = normalize_mdx_to_plain(new_item, 'list')
                bid = parent_mapping.block_id
                if bid not in containing_changes:
                    containing_changes[bid] = (parent_mapping, [])
                containing_changes[bid][1].append((old_plain, new_plain))

    # 상위 블록에 대한 그룹화된 변경 적용
    for bid, (mapping, item_changes) in containing_changes.items():
        xhtml_text = mapping.xhtml_plain_text
        for old_plain, new_plain in item_changes:
            xhtml_text = transfer_text_changes(
                old_plain, new_plain, xhtml_text)
        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': mapping.xhtml_plain_text,
            'new_plain_text': xhtml_text,
        })
        if used_ids is not None:
            used_ids.add(bid)

    return patches


def extract_list_marker_prefix(text: str) -> str:
    """텍스트에서 선행 리스트 마커 prefix를 추출한다."""
    m = re.match(r'^([-*+]\s+|\d+\.\s+)', text)
    return m.group(0) if m else ''
