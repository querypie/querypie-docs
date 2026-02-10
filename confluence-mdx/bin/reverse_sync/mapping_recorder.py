"""Mapping Recorder — XHTML 블록 요소를 추출하여 매핑 레코드를 생성한다."""
from dataclasses import dataclass, field
from typing import List, Optional
from bs4 import BeautifulSoup, NavigableString, Tag


@dataclass
class BlockMapping:
    block_id: str
    type: str               # heading | paragraph | list | code | table | html_block
    xhtml_xpath: str        # 간이 XPath (예: "h2[1]", "p[3]")
    xhtml_text: str         # 서식 태그 포함 원본
    xhtml_plain_text: str   # 평문 텍스트
    xhtml_element_index: int  # soup.children 내 인덱스
    children: List[str] = field(default_factory=list)


HEADING_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}

_CALLOUT_MACRO_NAMES = frozenset({'tip', 'info', 'note', 'warning', 'panel'})


def _iter_block_children(parent):
    """블록 레벨 자식을 순회한다. ac:layout은 cell 내부로 진입한다."""
    for child in parent.children:
        if isinstance(child, Tag) and child.name == 'ac:layout':
            for section in child.find_all('ac:layout-section', recursive=False):
                for cell in section.find_all('ac:layout-cell', recursive=False):
                    yield from cell.children
        else:
            yield child


def record_mapping(xhtml: str) -> List[BlockMapping]:
    """XHTML에서 블록 레벨 요소를 추출하여 매핑 레코드를 생성한다."""
    soup = BeautifulSoup(xhtml, 'html.parser')
    mappings: List[BlockMapping] = []
    counters: dict = {}

    for child in _iter_block_children(soup):
        if isinstance(child, NavigableString):
            if child.strip():
                _add_mapping(mappings, counters, 'p', child.strip(), child.strip())
            continue
        if not isinstance(child, Tag):
            continue

        tag_name = child.name
        if tag_name in HEADING_TAGS:
            plain = child.get_text()
            inner = ''.join(str(c) for c in child.children)
            _add_mapping(mappings, counters, tag_name, inner, plain, block_type='heading')
        elif tag_name == 'p':
            plain = child.get_text()
            inner = ''.join(str(c) for c in child.children)
            _add_mapping(mappings, counters, 'p', inner, plain, block_type='paragraph')
        elif tag_name in ('ul', 'ol'):
            plain = child.get_text()
            inner = str(child)
            _add_mapping(mappings, counters, tag_name, inner, plain, block_type='list')
        elif tag_name == 'table':
            plain = child.get_text()
            inner = str(child)
            _add_mapping(mappings, counters, 'table', inner, plain, block_type='table')
        elif tag_name == 'ac:structured-macro':
            macro_name = child.get('ac:name', '')
            if macro_name == 'code':
                plain_body = child.find('ac:plain-text-body')
                plain = plain_body.get_text() if plain_body else ''
                _add_mapping(mappings, counters, f'macro-{macro_name}', str(child), plain,
                             block_type='code')
            else:
                plain = child.get_text()
                _add_mapping(mappings, counters, f'macro-{macro_name}', str(child), plain,
                             block_type='html_block')
                # Callout 매크로: 자식 요소 개별 매핑 추가
                if macro_name in _CALLOUT_MACRO_NAMES:
                    parent_mapping = mappings[-1]
                    _add_rich_text_body_children(
                        child, parent_mapping, mappings, counters)
        elif tag_name == 'ac:adf-extension':
            panel_type = _get_adf_panel_type(child)
            plain = child.get_text()
            _add_mapping(mappings, counters, tag_name, str(child), plain,
                         block_type='html_block')
            if panel_type in _CALLOUT_MACRO_NAMES:
                parent_mapping = mappings[-1]
                _add_adf_content_children(
                    child, parent_mapping, mappings, counters)
        else:
            plain = child.get_text() if hasattr(child, 'get_text') else str(child)
            inner = str(child)
            _add_mapping(mappings, counters, tag_name, inner, plain, block_type='html_block')

    return mappings


def _add_mapping(
    mappings: List[BlockMapping],
    counters: dict,
    tag_name: str,
    xhtml_text: str,
    xhtml_plain_text: str,
    block_type: Optional[str] = None,
):
    if block_type is None:
        block_type = tag_name
    counters[tag_name] = counters.get(tag_name, 0) + 1
    idx = counters[tag_name]
    block_id = f"{block_type}-{len(mappings) + 1}"
    xpath = f"{tag_name}[{idx}]"
    mappings.append(BlockMapping(
        block_id=block_id,
        type=block_type,
        xhtml_xpath=xpath,
        xhtml_text=xhtml_text.strip(),
        xhtml_plain_text=xhtml_plain_text.strip(),
        xhtml_element_index=len(mappings),
    ))


def _add_rich_text_body_children(
    macro_element: Tag,
    parent_mapping: BlockMapping,
    mappings: List[BlockMapping],
    counters: dict,
):
    """Callout 매크로의 ac:rich-text-body 내 자식 요소를 개별 매핑으로 추가한다."""
    rich_body = macro_element.find('ac:rich-text-body')
    if rich_body is None:
        return

    child_counters: dict = {}  # 매크로 내부 전용 카운터
    parent_xpath = parent_mapping.xhtml_xpath  # 예: "macro-info[1]"

    for child in rich_body.children:
        if not isinstance(child, Tag):
            continue
        tag = child.name
        if tag not in ('p', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table'):
            continue

        child_counters[tag] = child_counters.get(tag, 0) + 1
        child_xpath = f"{parent_xpath}/{tag}[{child_counters[tag]}]"

        plain = child.get_text()
        if tag in ('ul', 'ol', 'table'):
            inner = str(child)
        else:
            inner = ''.join(str(c) for c in child.children)

        block_type = 'heading' if tag in HEADING_TAGS else (
            'list' if tag in ('ul', 'ol') else (
            'table' if tag == 'table' else 'paragraph'))

        block_id = f"{block_type}-{len(mappings) + 1}"
        child_mapping = BlockMapping(
            block_id=block_id,
            type=block_type,
            xhtml_xpath=child_xpath,
            xhtml_text=inner.strip(),
            xhtml_plain_text=plain.strip(),
            xhtml_element_index=len(mappings),
        )
        mappings.append(child_mapping)
        parent_mapping.children.append(block_id)


def _get_adf_panel_type(element: Tag) -> str:
    """ac:adf-extension 요소에서 panel-type을 추출한다."""
    node = element.find('ac:adf-node')
    if node is None:
        return ''
    attr = node.find('ac:adf-attribute', attrs={'key': 'panel-type'})
    if attr is None:
        return ''
    return attr.get_text().strip()


def _get_adf_content_body(element: Tag):
    """ac:adf-extension 요소에서 ac:adf-content를 찾는다."""
    node = element.find('ac:adf-node')
    if node is None:
        return None
    return node.find('ac:adf-content')


def _add_adf_content_children(
    adf_element: Tag,
    parent_mapping: BlockMapping,
    mappings: List[BlockMapping],
    counters: dict,
):
    """ac:adf-extension의 ac:adf-content 내 자식 요소를 개별 매핑으로 추가한다."""
    content_body = _get_adf_content_body(adf_element)
    if content_body is None:
        return

    child_counters: dict = {}
    parent_xpath = parent_mapping.xhtml_xpath

    for child in content_body.children:
        if not isinstance(child, Tag):
            continue
        tag = child.name
        if tag not in ('p', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table'):
            continue

        child_counters[tag] = child_counters.get(tag, 0) + 1
        child_xpath = f"{parent_xpath}/{tag}[{child_counters[tag]}]"

        plain = child.get_text()
        if tag in ('ul', 'ol', 'table'):
            inner = str(child)
        else:
            inner = ''.join(str(c) for c in child.children)

        block_type = 'heading' if tag in HEADING_TAGS else (
            'list' if tag in ('ul', 'ol') else (
            'table' if tag == 'table' else 'paragraph'))

        block_id = f"{block_type}-{len(mappings) + 1}"
        child_mapping = BlockMapping(
            block_id=block_id,
            type=block_type,
            xhtml_xpath=child_xpath,
            xhtml_text=inner.strip(),
            xhtml_plain_text=plain.strip(),
            xhtml_element_index=len(mappings),
        )
        mappings.append(child_mapping)
        parent_mapping.children.append(block_id)
