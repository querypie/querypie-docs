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


def record_mapping(xhtml: str) -> List[BlockMapping]:
    """XHTML에서 블록 레벨 요소를 추출하여 매핑 레코드를 생성한다."""
    soup = BeautifulSoup(xhtml, 'html.parser')
    mappings: List[BlockMapping] = []
    counters: dict = {}

    for child in soup.children:
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
