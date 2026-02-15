"""패치 빌더 — MDX diff 변경과 XHTML 매핑을 결합하여 XHTML 패치를 생성."""
import html as html_module
import re
from typing import Dict, List, Optional

from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.mdx_block_parser import MdxBlock
from reverse_sync.text_normalizer import (
    normalize_mdx_to_plain, collapse_ws, strip_list_marker,
    strip_for_compare,
)
from reverse_sync.text_transfer import transfer_text_changes
from reverse_sync.sidecar_lookup import find_mapping_by_sidecar, SidecarEntry
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_xhtml_element


NON_CONTENT_TYPES = frozenset(('empty', 'frontmatter', 'import_statement'))


def _find_containing_mapping(
    old_plain: str,
    mappings: List[BlockMapping],
    used_ids: set,
) -> Optional[BlockMapping]:
    """old_plain 텍스트를 포함하는 XHTML 매핑을 찾는다 (sidecar 폴백)."""
    old_norm = collapse_ws(old_plain)
    if not old_norm or len(old_norm) < 5:
        return None
    old_nospace = strip_for_compare(old_norm)
    for m in mappings:
        if m.block_id in used_ids:
            continue
        m_nospace = strip_for_compare(m.xhtml_plain_text)
        if m_nospace and old_nospace in m_nospace:
            return m
    return None


def build_patches(
    changes: List[BlockChange],
    original_blocks: List[MdxBlock],
    improved_blocks: List[MdxBlock],
    mappings: List[BlockMapping],
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
    alignment: Optional[Dict[int, int]] = None,
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
        if change.change_type == 'deleted':
            patch = _build_delete_patch(
                change, mdx_to_sidecar, xpath_to_mapping)
            if patch:
                patches.append(patch)
            continue

        if change.change_type == 'added':
            patch = _build_insert_patch(
                change, improved_blocks, alignment,
                mdx_to_sidecar, xpath_to_mapping)
            if patch:
                patches.append(patch)
            continue

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
                # 블록 텍스트가 parent에 포함되는지 확인
                _old_ns = strip_for_compare(old_plain)
                _map_ns = strip_for_compare(mapping.xhtml_plain_text)
                if _old_ns and _map_ns and _old_ns not in _map_ns:
                    # 텍스트 불일치 → list 항목 단위 분리 시도
                    if change.old_block.type == 'list':
                        patches.extend(
                            build_list_item_patches(
                                change, mappings, used_ids,
                                mdx_to_sidecar, xpath_to_mapping,
                                id_to_mapping))
                        continue
                # Child 해석 실패 → parent를 containing block으로 사용
                new_plain = normalize_mdx_to_plain(
                    change.new_block.content, change.new_block.type)
                bid = mapping.block_id
                if bid not in containing_changes:
                    containing_changes[bid] = (mapping, [])
                containing_changes[bid][1].append((old_plain, new_plain))
                continue

        if mapping is None:
            # 폴백: 텍스트 포함 검색으로 containing mapping 찾기
            containing = _find_containing_mapping(old_plain, mappings, used_ids)
            if containing is not None:
                new_plain = normalize_mdx_to_plain(
                    change.new_block.content, change.new_block.type)
                bid = containing.block_id
                if bid not in containing_changes:
                    containing_changes[bid] = (containing, [])
                containing_changes[bid][1].append((old_plain, new_plain))
                continue

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

        # 매핑 텍스트에 old_plain이 포함되지 않으면 더 나은 매핑 찾기
        if not mapping.children:
            old_nospace = strip_for_compare(old_plain)
            map_nospace = strip_for_compare(mapping.xhtml_plain_text)
            if old_nospace and map_nospace and old_nospace not in map_nospace:
                better = _find_containing_mapping(old_plain, mappings, used_ids)
                if better is not None:
                    new_plain = normalize_mdx_to_plain(
                        change.new_block.content, change.new_block.type)
                    bid = better.block_id
                    if bid not in containing_changes:
                        containing_changes[bid] = (better, [])
                    containing_changes[bid][1].append((old_plain, new_plain))
                    continue
                # 전체 텍스트 매칭 불가 → list 항목 단위로 분리 시도
                if change.old_block.type == 'list':
                    patches.extend(
                        build_list_item_patches(
                            change, mappings, used_ids,
                            mdx_to_sidecar, xpath_to_mapping,
                            id_to_mapping))
                    continue

        _mark_used(mapping.block_id, mapping)

        # 리스트 블록: 중첩 항목이 있으면 항목별 패치로 분리하여 텍스트 병합 방지
        if change.old_block.type == 'list':
            item_patches = _build_nested_list_item_patches(change, mapping)
            if item_patches is not None:
                patches.extend(item_patches)
                continue

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


def _split_top_level_items(content: str) -> List[str]:
    """리스트 블록에서 최상위 항목만 분리한다.

    하위 중첩 항목은 부모 항목에 포함된다.
    """
    items = []
    current: List[str] = []
    base_indent: Optional[int] = None

    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped:
            if current:
                current.append(line)
            continue

        indent = len(line) - len(line.lstrip())
        is_marker = bool(
            re.match(r'^[-*+]\s+', stripped) or re.match(r'^\d+\.\s+', stripped))

        if is_marker and base_indent is None:
            base_indent = indent

        # 같은 들여쓰기의 새 리스트 항목이면 새 항목으로 분리
        if is_marker and indent == base_indent and current:
            # 뒤 빈 줄 제거
            while current and not current[-1].strip():
                current.pop()
            items.append('\n'.join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        while current and not current[-1].strip():
            current.pop()
        items.append('\n'.join(current))

    return items


def _extract_first_line(item_mdx: str) -> str:
    """리스트 항목의 첫 번째 줄(top-level text)만 추출한다.

    중첩된 하위 항목이나 figure 등의 블록 요소를 제외한다.
    """
    lines = item_mdx.split('\n')
    if not lines:
        return ''
    first = lines[0].strip()
    # 리스트 마커 제거
    first = re.sub(r'^\d+\.\s+', '', first)
    first = re.sub(r'^[-*+]\s+', '', first)
    return first


def _has_nested_items(item_mdx: str) -> bool:
    """리스트 항목에 중첩된 하위 항목이 있는지 확인한다."""
    lines = item_mdx.split('\n')
    if len(lines) <= 1:
        return False
    first_line = lines[0]
    first_indent = len(first_line) - len(first_line.lstrip())
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        if indent > first_indent and (
            re.match(r'^[-*+]\s+', stripped) or re.match(r'^\d+\.\s+', stripped)
        ):
            return True
    return False


def _nesting_depth(item_mdx: str) -> int:
    """리스트 항목의 최대 중첩 깊이를 반환한다. (1 = 중첩 없음)"""
    lines = item_mdx.split('\n')
    if not lines:
        return 0
    first_line = lines[0]
    base_indent = len(first_line) - len(first_line.lstrip())
    max_depth = 1
    current_depth = 1
    indent_stack = [base_indent]

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        is_marker = bool(
            re.match(r'^[-*+]\s+', stripped) or re.match(r'^\d+\.\s+', stripped))
        if not is_marker:
            continue
        while indent_stack and indent <= indent_stack[-1]:
            indent_stack.pop()
            current_depth -= 1
        if indent > (indent_stack[-1] if indent_stack else base_indent):
            indent_stack.append(indent)
            current_depth += 1
        max_depth = max(max_depth, current_depth)

    return max_depth


def _extract_sub_items(item_mdx: str) -> List[str]:
    """중첩 항목에서 직속 하위 항목들을 추출한다."""
    lines = item_mdx.split('\n')
    if len(lines) <= 1:
        return []

    first_line = lines[0]
    base_indent = len(first_line) - len(first_line.lstrip())

    # 하위 항목의 들여쓰기 수준 결정
    sub_indent: Optional[int] = None
    sub_items: List[str] = []
    current: List[str] = []

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            if current:
                current.append(line)
            continue

        indent = len(line) - len(line.lstrip())
        is_marker = bool(
            re.match(r'^[-*+]\s+', stripped) or re.match(r'^\d+\.\s+', stripped))

        if is_marker and indent > base_indent:
            if sub_indent is None:
                sub_indent = indent

            if indent == sub_indent:
                if current:
                    while current and not current[-1].strip():
                        current.pop()
                    sub_items.append('\n'.join(current))
                current = [line]
                continue

        if current:
            current.append(line)

    if current:
        while current and not current[-1].strip():
            current.pop()
        sub_items.append('\n'.join(current))

    return sub_items


def _build_sub_item_patches(
    old_item: str,
    new_item: str,
    parent_xpath: str,
) -> List[Dict[str, str]]:
    """중첩 항목 내 변경된 하위 항목에 대한 패치를 생성한다."""
    old_subs = _extract_sub_items(old_item)
    new_subs = _extract_sub_items(new_item)
    if len(old_subs) != len(new_subs):
        return []

    patches = []
    # 하위 항목은 ol[1]/li[N] 구조로 매핑
    li_index = 0
    for old_sub, new_sub in zip(old_subs, new_subs):
        li_index += 1
        if old_sub == new_sub:
            continue

        if _has_nested_items(old_sub):
            # 더 깊은 중첩: 첫 줄만 패치 + 재귀
            old_first = _extract_first_line(old_sub)
            new_first = _extract_first_line(new_sub)
            if old_first != new_first:
                old_plain = normalize_mdx_to_plain(old_first, 'paragraph')
                new_plain = normalize_mdx_to_plain(new_first, 'paragraph')
                patches.append({
                    'xhtml_xpath': f'{parent_xpath}/ol[1]/li[{li_index}]/p[1]',
                    'old_plain_text': old_plain,
                    'new_plain_text': new_plain,
                })
            sub_patches = _build_sub_item_patches(
                old_sub, new_sub, f'{parent_xpath}/ol[1]/li[{li_index}]')
            patches.extend(sub_patches)
        else:
            old_first = _extract_first_line(old_sub)
            new_first = _extract_first_line(new_sub)
            if old_first != new_first:
                old_plain = normalize_mdx_to_plain(old_first, 'paragraph')
                new_plain = normalize_mdx_to_plain(new_first, 'paragraph')
                patches.append({
                    'xhtml_xpath': f'{parent_xpath}/ol[1]/li[{li_index}]/p[1]',
                    'old_plain_text': old_plain,
                    'new_plain_text': new_plain,
                })

    return patches


def _build_nested_list_item_patches(
    change: 'BlockChange',
    mapping: 'BlockMapping',
) -> Optional[List[Dict[str, str]]]:
    """중첩 리스트의 변경된 항목만 개별 패치로 생성한다.

    중첩 리스트에서 전체 텍스트를 한꺼번에 패치하면 하위 항목의 텍스트가
    상위 항목으로 병합되는 문제를 방지한다.
    """
    old_items = _split_top_level_items(change.old_block.content)
    new_items = _split_top_level_items(change.new_block.content)
    if len(old_items) != len(new_items):
        return None

    # 중첩 항목의 첫 번째 줄이 변경된 경우에만 항목별 패치 사용.
    # 첫 줄 변경이 없는 경우 monolithic _apply_text_changes로도 안전하게 처리 가능.
    has_first_line_change_in_nested = False
    for old_item, new_item in zip(old_items, new_items):
        if old_item == new_item:
            continue
        if not _has_nested_items(old_item):
            continue
        old_first = _extract_first_line(old_item)
        new_first = _extract_first_line(new_item)
        if old_first != new_first:
            has_first_line_change_in_nested = True
            break

    if not has_first_line_change_in_nested:
        return None

    parent_xpath = mapping.xhtml_xpath
    patches = []
    li_index = 0
    for old_item, new_item in zip(old_items, new_items):
        li_index += 1
        if old_item == new_item:
            continue

        if _has_nested_items(old_item):
            # 중첩 항목: 첫 번째 줄(top-level <p>)만 패치
            old_first = _extract_first_line(old_item)
            new_first = _extract_first_line(new_item)
            if old_first != new_first:
                old_plain = normalize_mdx_to_plain(old_first, 'paragraph')
                new_plain = normalize_mdx_to_plain(new_first, 'paragraph')
                patches.append({
                    'xhtml_xpath': f'{parent_xpath}/li[{li_index}]/p[1]',
                    'old_plain_text': old_plain,
                    'new_plain_text': new_plain,
                })
            # 중첩 하위 항목의 변경도 재귀적으로 처리
            sub_patches = _build_sub_item_patches(
                old_item, new_item, f'{parent_xpath}/li[{li_index}]')
            patches.extend(sub_patches)
        else:
            # 비중첩 항목: 전체 항목 텍스트 패치
            old_plain = normalize_mdx_to_plain(old_item, 'list')
            new_plain = normalize_mdx_to_plain(new_item, 'list')
            patches.append({
                'xhtml_xpath': f'{parent_xpath}/li[{li_index}]/p[1]',
                'old_plain_text': old_plain,
                'new_plain_text': new_plain,
            })

    return patches


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
            # child 매칭 실패: parent 또는 텍스트 포함 매핑을 containing block으로 사용
            container = parent_mapping
            if container is not None and used_ids is not None:
                # parent 텍스트에 항목이 포함되지 않으면 더 나은 매핑 찾기
                _item_ns = strip_for_compare(old_plain)
                _cont_ns = strip_for_compare(container.xhtml_plain_text)
                if _item_ns and _cont_ns and _item_ns not in _cont_ns:
                    better = _find_containing_mapping(
                        old_plain, mappings, used_ids)
                    if better is not None:
                        container = better
            elif used_ids is not None:
                container = _find_containing_mapping(old_plain, mappings, used_ids)
            if container is not None:
                new_plain = normalize_mdx_to_plain(new_item, 'list')
                bid = container.block_id
                if bid not in containing_changes:
                    containing_changes[bid] = (container, [])
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


def _build_delete_patch(
    change: BlockChange,
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
) -> Optional[Dict[str, str]]:
    """삭제된 블록에 대한 delete 패치를 생성한다."""
    if change.old_block.type in NON_CONTENT_TYPES:
        return None
    mapping = find_mapping_by_sidecar(
        change.index, mdx_to_sidecar, xpath_to_mapping)
    if mapping is None:
        return None
    return {'action': 'delete', 'xhtml_xpath': mapping.xhtml_xpath}


def _build_insert_patch(
    change: BlockChange,
    improved_blocks: List[MdxBlock],
    alignment: Optional[Dict[int, int]],
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
) -> Optional[Dict[str, str]]:
    """추가된 블록에 대한 insert 패치를 생성한다."""
    new_block = change.new_block
    if new_block.type in NON_CONTENT_TYPES:
        return None

    after_xpath = _find_insert_anchor(
        change.index, alignment, mdx_to_sidecar, xpath_to_mapping)
    new_xhtml = mdx_block_to_xhtml_element(new_block)

    return {
        'action': 'insert',
        'after_xpath': after_xpath,
        'new_element_xhtml': new_xhtml,
    }


def _find_insert_anchor(
    improved_idx: int,
    alignment: Optional[Dict[int, int]],
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
) -> Optional[str]:
    """추가 블록의 삽입 위치 앵커를 찾는다.

    improved 시퀀스에서 역순으로 탐색하여 alignment에 존재하는
    (= original에 매칭되는) 첫 번째 블록의 xhtml_xpath를 반환한다.
    """
    if alignment is None:
        return None

    for j in range(improved_idx - 1, -1, -1):
        if j in alignment:
            orig_idx = alignment[j]
            mapping = find_mapping_by_sidecar(
                orig_idx, mdx_to_sidecar, xpath_to_mapping)
            if mapping is not None:
                return mapping.xhtml_xpath
    return None
