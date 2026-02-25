"""패치 빌더 — MDX diff 변경과 XHTML 매핑을 결합하여 XHTML 패치를 생성."""
import html as html_module
import re
from typing import Dict, List, Optional

from reverse_sync.block_diff import BlockChange, NON_CONTENT_TYPES
from reverse_sync.mapping_recorder import BlockMapping
from mdx_to_storage.parser import Block as MdxBlock
from text_utils import (
    normalize_mdx_to_plain, collapse_ws, strip_list_marker,
    strip_for_compare,
)
from reverse_sync.text_transfer import transfer_text_changes
from reverse_sync.sidecar import find_mapping_by_sidecar, SidecarEntry
from reverse_sync.lost_info_patcher import apply_lost_info
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_xhtml_element, mdx_block_to_inner_xhtml
from mdx_to_storage.inline import convert_inline


# ── Inline format 변경 감지 ──

_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_INLINE_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_INLINE_ITALIC_RE = re.compile(r'(?<!\*)\*([^*]+)\*(?!\*)')
_INLINE_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def _extract_inline_markers(content: str) -> list:
    """MDX content에서 inline 포맷 마커를 위치순으로 추출한다."""
    markers = []
    for m in _INLINE_CODE_RE.finditer(content):
        markers.append(('code', m.start(), m.group(1)))
    for m in _INLINE_BOLD_RE.finditer(content):
        markers.append(('bold', m.start(), m.group(1)))
    for m in _INLINE_ITALIC_RE.finditer(content):
        markers.append(('italic', m.start(), m.group(1)))
    for m in _INLINE_LINK_RE.finditer(content):
        markers.append(('link', m.start(), m.group(1), m.group(2)))
    return sorted(markers, key=lambda x: x[1])


def _strip_positions(markers: list) -> list:
    """마커 리스트에서 위치(index 1)를 제거하여 type+content만 비교 가능하게 한다."""
    return [(m[0],) + m[2:] for m in markers]


def _extract_marker_spans(content: str) -> list:
    """MDX content에서 inline 포맷 마커의 (start, end) 위치 범위를 추출한다."""
    spans = []
    for m in _INLINE_CODE_RE.finditer(content):
        spans.append((m.start(), m.end()))
    for m in _INLINE_BOLD_RE.finditer(content):
        spans.append((m.start(), m.end()))
    for m in _INLINE_ITALIC_RE.finditer(content):
        spans.append((m.start(), m.end()))
    for m in _INLINE_LINK_RE.finditer(content):
        spans.append((m.start(), m.end()))
    return sorted(spans)


def _extract_between_marker_texts(content: str) -> list:
    """연속된 inline 마커 사이의 텍스트를 추출한다."""
    spans = _extract_marker_spans(content)
    between = []
    for i in range(len(spans) - 1):
        between.append(content[spans[i][1]:spans[i + 1][0]])
    return between


def has_inline_format_change(old_content: str, new_content: str) -> bool:
    """old/new MDX 콘텐츠의 inline 포맷 마커가 다른지 감지한다.

    마커 type/content 변경뿐 아니라, 연속된 마커 사이의 텍스트가
    변경된 경우도 inline 변경으로 판단한다 (XHTML code 요소 경계에서
    text-only 패치가 올바르게 동작하지 않기 때문).
    """
    old_markers = _strip_positions(_extract_inline_markers(old_content))
    new_markers = _strip_positions(_extract_inline_markers(new_content))
    if old_markers != new_markers:
        return True

    # 마커가 있을 때, 연속된 마커 사이 텍스트 변경 감지
    if old_markers:
        old_between = _extract_between_marker_texts(old_content)
        new_between = _extract_between_marker_texts(new_content)
        if ([collapse_ws(s) for s in old_between]
                != [collapse_ws(s) for s in new_between]):
            return True

    return False


def has_inline_boundary_change(old_content: str, new_content: str) -> bool:
    """inline 마커의 경계 이동을 감지한다.

    마커 type 추가/제거, 마커 간 텍스트 변경(경계 이동)을 감지한다.
    마커 내부 content만 변경된 경우는 무시한다 (text-only 패치로 처리 가능).
    flat list의 전체 리스트 재생성 판단에 사용한다.
    (has_inline_format_change보다 보수적 — 이미지 등 XHTML 고유 요소 보존)
    """
    old_markers = _extract_inline_markers(old_content)
    new_markers = _extract_inline_markers(new_content)
    old_types = [m[0] for m in old_markers]
    new_types = [m[0] for m in new_markers]
    if old_types != new_types:
        return True

    # 마커가 있을 때, 연속된 마커 사이 텍스트 변경 감지 (경계 이동)
    if old_markers:
        old_between = _extract_between_marker_texts(old_content)
        new_between = _extract_between_marker_texts(new_content)
        if ([collapse_ws(s) for s in old_between]
                != [collapse_ws(s) for s in new_between]):
            return True

    return False


_BLOCK_MARKER_RE = re.compile(r'#{1,6}|\d+\.')


def _strip_block_markers(text: str) -> str:
    """containment 비교를 위해 heading/list 마커를 제거한다."""
    return _BLOCK_MARKER_RE.sub('', text)


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
    # 폴백: heading/list 마커를 제거하고 재시도
    old_stripped = _strip_block_markers(old_nospace)
    for m in mappings:
        if m.block_id in used_ids:
            continue
        m_stripped = _strip_block_markers(strip_for_compare(m.xhtml_plain_text))
        if m_stripped and old_stripped in m_stripped:
            return m
    return None


def _flush_containing_changes(
    containing_changes: dict,
    used_ids: 'set | None' = None,
) -> List[Dict[str, str]]:
    """그룹화된 containing_changes를 패치 목록으로 변환한다.

    containing_changes: block_id → (mapping, [(old_plain, new_plain)])
    각 매핑의 xhtml_plain_text에 transfer_text_changes를 순차 적용하여 패치를 생성한다.
    """
    patches = []
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


def _resolve_mapping_for_change(
    change: BlockChange,
    old_plain: str,
    mappings: List[BlockMapping],
    used_ids: set,
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
    id_to_mapping: Dict[str, BlockMapping],
) -> tuple:
    """변경에 대한 매핑과 처리 전략을 결정한다.

    Returns:
        (strategy, mapping) 튜플.
        strategy: 'direct' | 'containing' | 'list' | 'table' | 'skip'
        mapping: 해당 BlockMapping 또는 None
    """

    # Sidecar 직접 조회 (O(1))
    mapping = find_mapping_by_sidecar(
        change.index, mdx_to_sidecar, xpath_to_mapping)

    # Parent mapping → child 해석 시도
    if mapping is not None and mapping.children:
        child = _resolve_child_mapping(old_plain, mapping, id_to_mapping)
        if child is not None:
            return ('direct', child)
        # 블록 텍스트가 parent에 포함되는지 확인
        _old_ns = strip_for_compare(old_plain)
        _map_ns = strip_for_compare(mapping.xhtml_plain_text)
        if _old_ns and _map_ns and _old_ns not in _map_ns:
            if change.old_block.type == 'list':
                return ('list', mapping)
        return ('containing', mapping)

    if mapping is None:
        # 폴백: 텍스트 포함 검색으로 containing mapping 찾기
        containing = _find_containing_mapping(old_plain, mappings, used_ids)
        if containing is not None:
            return ('containing', containing)
        if change.old_block.type == 'list':
            return ('list', None)
        if is_markdown_table(change.old_block.content):
            return ('table', None)
        return ('skip', None)

    # 매핑 텍스트에 old_plain이 포함되지 않으면 더 나은 매핑 찾기
    if not mapping.children:
        old_nospace = strip_for_compare(old_plain)
        map_nospace = strip_for_compare(mapping.xhtml_plain_text)
        if old_nospace and map_nospace and old_nospace not in map_nospace:
            better = _find_containing_mapping(old_plain, mappings, used_ids)
            if better is not None:
                return ('containing', better)
            if change.old_block.type == 'list':
                return ('list', mapping)

    # list 블록은 list 전략 사용 (direct 교체 시 <ac:image> 등 Confluence 태그 손실 방지)
    if change.old_block.type == 'list':
        return ('list', mapping)

    return ('direct', mapping)


def build_patches(
    changes: List[BlockChange],
    original_blocks: List[MdxBlock],
    improved_blocks: List[MdxBlock],
    mappings: List[BlockMapping],
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
    alignment: Optional[Dict[int, int]] = None,
    page_lost_info: Optional[dict] = None,
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
                mdx_to_sidecar, xpath_to_mapping,
                page_lost_info=page_lost_info)
            if patch:
                patches.append(patch)
            continue

        if change.old_block.type in NON_CONTENT_TYPES:
            continue

        old_plain = normalize_mdx_to_plain(
            change.old_block.content, change.old_block.type)

        strategy, mapping = _resolve_mapping_for_change(
            change, old_plain, mappings, used_ids,
            mdx_to_sidecar, xpath_to_mapping, id_to_mapping)

        if strategy == 'skip':
            continue

        if strategy == 'list':
            patches.extend(
                build_list_item_patches(
                    change, mappings, used_ids,
                    mdx_to_sidecar, xpath_to_mapping, id_to_mapping))
            continue

        if strategy == 'table':
            patches.extend(
                build_table_row_patches(
                    change, mappings, used_ids,
                    mdx_to_sidecar, xpath_to_mapping))
            continue

        new_plain = normalize_mdx_to_plain(
            change.new_block.content, change.new_block.type)

        if strategy == 'containing':
            bid = mapping.block_id
            if bid not in containing_changes:
                containing_changes[bid] = (mapping, [])
            containing_changes[bid][1].append((old_plain, new_plain))
            continue

        # strategy == 'direct'
        _mark_used(mapping.block_id, mapping)

        # inline 포맷 변경 감지 → new_inner_xhtml 패치
        if has_inline_format_change(
                change.old_block.content, change.new_block.content):
            new_inner = mdx_block_to_inner_xhtml(
                change.new_block.content, change.new_block.type)
            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': mapping.xhtml_plain_text,
                'new_inner_xhtml': new_inner,
            })
        else:
            if collapse_ws(old_plain) != collapse_ws(mapping.xhtml_plain_text):
                # XHTML이 이미 원하는 텍스트와 일치하면 변경 건너뛰기
                # (push+fetch 후 verify 재실행 시 멱등성 보장)
                if collapse_ws(new_plain) == collapse_ws(mapping.xhtml_plain_text):
                    continue
                new_plain = transfer_text_changes(
                    old_plain, new_plain, mapping.xhtml_plain_text)

            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': mapping.xhtml_plain_text,
                'new_plain_text': new_plain,
            })

    # 상위 블록에 대한 그룹화된 변경 적용
    patches.extend(_flush_containing_changes(containing_changes, used_ids))
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

    patches.extend(_flush_containing_changes(containing_changes, used_ids))
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
        # 항목 수가 다르면 (삭제/추가) 전체 리스트 inner XHTML 재생성
        parent = None
        if mdx_to_sidecar is not None and xpath_to_mapping is not None:
            parent = find_mapping_by_sidecar(
                change.index, mdx_to_sidecar, xpath_to_mapping)
        if parent is not None:
            new_inner = mdx_block_to_inner_xhtml(
                change.new_block.content, change.new_block.type)
            return [{
                'xhtml_xpath': parent.xhtml_xpath,
                'old_plain_text': parent.xhtml_plain_text,
                'new_inner_xhtml': new_inner,
            }]
        return []

    # sidecar에서 parent mapping 획득
    parent_mapping = None
    if mdx_to_sidecar is not None and xpath_to_mapping is not None:
        parent_mapping = find_mapping_by_sidecar(
            change.index, mdx_to_sidecar, xpath_to_mapping)

    patches = []
    # 매칭 실패한 항목을 상위 블록 기준으로 그룹화
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    # flat list에서 inline 포맷 변경이 감지되면 전체 리스트 inner XHTML 재생성
    _flat_inline_change = False
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
            if used_ids is not None:
                used_ids.add(mapping.block_id)

            # inline 포맷 변경 감지 → new_inner_xhtml 패치
            if has_inline_format_change(old_item, new_item):
                new_item_text = re.sub(r'^[-*+]\s+', '', new_item.strip())
                new_item_text = re.sub(r'^\d+\.\s+', '', new_item_text)
                new_inner = convert_inline(new_item_text)
                patches.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'old_plain_text': mapping.xhtml_plain_text,
                    'new_inner_xhtml': new_inner,
                })
            else:
                new_plain = normalize_mdx_to_plain(new_item, 'list')

                xhtml_text = mapping.xhtml_plain_text
                prefix = extract_list_marker_prefix(xhtml_text)
                if prefix and collapse_ws(old_plain) != collapse_ws(xhtml_text):
                    xhtml_body = xhtml_text[len(prefix):]
                    # XHTML body가 이미 new_plain과 일치하면 건너뛰기
                    if collapse_ws(new_plain) == collapse_ws(xhtml_body):
                        continue
                    if collapse_ws(old_plain) != collapse_ws(xhtml_body):
                        new_plain = transfer_text_changes(
                            old_plain, new_plain, xhtml_body)
                    new_plain = prefix + new_plain
                elif collapse_ws(old_plain) != collapse_ws(xhtml_text):
                    # XHTML이 이미 new_plain과 일치하면 건너뛰기
                    if collapse_ws(new_plain) == collapse_ws(xhtml_text):
                        continue
                    new_plain = transfer_text_changes(
                        old_plain, new_plain, xhtml_text)

                patches.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'old_plain_text': mapping.xhtml_plain_text,
                    'new_plain_text': new_plain,
                })
        else:
            # child 매칭 실패: inline 마커 경계 이동 감지
            # has_inline_boundary_change: type 추가/제거 및 마커 간 텍스트 변경만 감지
            # (마커 내부 content만 변경된 경우는 무시하여 이미지 등 XHTML 고유 요소 보존)
            if has_inline_boundary_change(old_item, new_item):
                _flat_inline_change = True

            # parent 또는 텍스트 포함 매핑을 containing block으로 사용
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

    # flat list에서 inline 포맷 변경이 감지된 경우:
    # containing block 텍스트 패치 대신 전체 리스트 inner XHTML 재생성
    if _flat_inline_change and parent_mapping is not None:
        containing_changes.pop(parent_mapping.block_id, None)
        new_inner = mdx_block_to_inner_xhtml(
            change.new_block.content, change.new_block.type)
        patches.append({
            'xhtml_xpath': parent_mapping.xhtml_xpath,
            'old_plain_text': parent_mapping.xhtml_plain_text,
            'new_inner_xhtml': new_inner,
        })

    # 상위 블록에 대한 그룹화된 변경 적용
    patches.extend(_flush_containing_changes(containing_changes, used_ids))
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
    _SKIP_DELETE_TYPES = frozenset(('frontmatter', 'import_statement'))
    if change.old_block.type in _SKIP_DELETE_TYPES:
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
    page_lost_info: Optional[dict] = None,
) -> Optional[Dict[str, str]]:
    """추가된 블록에 대한 insert 패치를 생성한다."""
    new_block = change.new_block
    _SKIP_INSERT_TYPES = frozenset(('frontmatter', 'import_statement'))
    if new_block.type in _SKIP_INSERT_TYPES:
        return None

    after_xpath = _find_insert_anchor(
        change.index, alignment, mdx_to_sidecar, xpath_to_mapping)
    new_xhtml = mdx_block_to_xhtml_element(new_block)
    # L4: lost_info 적용
    if page_lost_info:
        new_xhtml = apply_lost_info(new_xhtml, page_lost_info)

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
