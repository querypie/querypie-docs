"""패치 빌더 — MDX diff 변경과 XHTML 매핑을 결합하여 XHTML 패치를 생성."""
import html as html_module
import re
from typing import Dict, List

from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.mdx_block_parser import MdxBlock
from reverse_sync.text_normalizer import normalize_mdx_to_plain, collapse_ws
from reverse_sync.text_transfer import transfer_text_changes
from reverse_sync.block_matcher import find_mapping_by_text, find_containing_mapping


NON_CONTENT_TYPES = frozenset(('empty', 'frontmatter', 'import_statement'))


def build_patches(
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
    # child → parent 역참조 맵 (부모-자식 간 중복 매칭 방지)
    child_to_parent: dict = {}
    for m in mappings:
        for child_id in m.children:
            child_to_parent[child_id] = m.block_id

    def _mark_used(block_id: str, m: BlockMapping):
        """매핑 사용 시 부모/자식도 함께 사용 완료로 표시."""
        used_ids.add(block_id)
        for child_id in m.children:
            used_ids.add(child_id)
        parent_id = child_to_parent.get(block_id)
        if parent_id:
            used_ids.add(parent_id)

    # 상위 블록에 대한 그룹화된 변경 (substring 매칭 fallback)
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    for change in changes:
        if change.old_block.type in NON_CONTENT_TYPES:
            continue

        old_plain = normalize_mdx_to_plain(
            change.old_block.content, change.old_block.type)
        mapping = find_mapping_by_text(old_plain, mappings, exclude=used_ids)

        if mapping is None:
            # 리스트 블록: 항목별로 분리하여 개별 매핑 시도
            if change.old_block.type == 'list':
                patches.extend(
                    build_list_item_patches(change, mappings, used_ids))
                continue

            # Markdown table이 paragraph로 파싱된 경우: 행별 분리 매칭
            if is_markdown_table(change.old_block.content):
                patches.extend(
                    build_table_row_patches(change, mappings, used_ids))
                continue

            # html_block 등: substring 매칭으로 상위 블록 탐색
            new_plain = normalize_mdx_to_plain(
                change.new_block.content, change.new_block.type)
            container = find_containing_mapping(
                old_plain, mappings, exclude=used_ids)
            if container is not None:
                bid = container.block_id
                if bid not in containing_changes:
                    containing_changes[bid] = (container, [])
                containing_changes[bid][1].append((old_plain, new_plain))
            continue

        _mark_used(mapping.block_id, mapping)
        new_block = change.new_block
        new_plain = normalize_mdx_to_plain(new_block.content, new_block.type)

        # MDX와 XHTML의 공백 구조가 같으면 (paragraph/heading 등)
        # MDX normalized text를 직접 사용.
        # 다르면 (table/html_block/list 등 셀/항목 경계 공백 차이)
        # XHTML 공백 구조를 보존하면서 콘텐츠 변경만 전이.
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
) -> List[Dict[str, str]]:
    """Markdown table 블록의 변경된 행을 XHTML table에 substring 매칭으로 패치한다."""
    old_rows = split_table_rows(change.old_block.content)
    new_rows = split_table_rows(change.new_block.content)
    if len(old_rows) != len(new_rows):
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
        container = find_containing_mapping(
            old_plain, mappings, exclude=used_ids)
        if container is not None:
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
) -> List[Dict[str, str]]:
    """리스트 블록의 각 항목을 개별 매핑과 대조하여 패치를 생성한다."""
    old_items = split_list_items(change.old_block.content)
    new_items = split_list_items(change.new_block.content)
    if len(old_items) != len(new_items):
        return []

    patches = []
    # 매칭 실패한 항목을 상위 블록 기준으로 그룹화
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    for old_item, new_item in zip(old_items, new_items):
        if old_item == new_item:
            continue
        old_plain = normalize_mdx_to_plain(old_item, 'list')
        mapping = find_mapping_by_text(old_plain, mappings, exclude=used_ids)

        if mapping is not None:
            # 정확 매칭: 기존 로직대로 패치 생성
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
            # 정확 매칭 실패: substring 매칭으로 상위 블록 탐색
            new_plain = normalize_mdx_to_plain(new_item, 'list')
            container = find_containing_mapping(
                old_plain, mappings, exclude=used_ids)
            if container is not None:
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
