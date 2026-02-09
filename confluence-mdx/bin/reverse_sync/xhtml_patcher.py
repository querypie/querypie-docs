"""XHTML Patcher — 매핑과 diff를 이용해 XHTML의 텍스트를 패치한다."""
from typing import List, Dict
from bs4 import BeautifulSoup, NavigableString, Tag
import difflib
import re


def patch_xhtml(xhtml: str, patches: List[Dict[str, str]]) -> str:
    """XHTML에 텍스트 패치를 적용한다.

    Args:
        xhtml: 원본 XHTML 문자열
        patches: 패치 목록. 각 패치는 dict:
            - xhtml_xpath: 간이 XPath (예: "p[1]", "h2[3]")
            - old_plain_text: 원본 평문 텍스트 (검증용)
            - new_inner_xhtml: 새 inner HTML (있으면 innerHTML 교체)
            - new_plain_text: 변경할 평문 텍스트 (legacy path)

    Returns:
        패치된 XHTML 문자열
    """
    soup = BeautifulSoup(xhtml, 'html.parser')

    for patch in patches:
        xpath = patch['xhtml_xpath']

        element = _find_element_by_xpath(soup, xpath)
        if element is None:
            continue

        if 'new_inner_xhtml' in patch:
            _replace_inner_html(element, patch['new_inner_xhtml'])
        else:
            old_text = patch['old_plain_text']
            new_text = patch['new_plain_text']

            current_plain = element.get_text()
            if current_plain.strip() != old_text.strip():
                continue

            _apply_text_changes(element, old_text, new_text)

    return str(soup)


def _replace_inner_html(element: Tag, new_inner_xhtml: str):
    """요소의 innerHTML을 통째로 교체한다."""
    element.clear()
    new_content = BeautifulSoup(new_inner_xhtml, 'html.parser')
    for child in list(new_content.children):
        element.append(child.extract())


def _iter_block_children(parent):
    """블록 레벨 자식을 순회한다. ac:layout은 cell 내부로 진입한다."""
    for child in parent.children:
        if isinstance(child, Tag) and child.name == 'ac:layout':
            for section in child.find_all('ac:layout-section', recursive=False):
                for cell in section.find_all('ac:layout-cell', recursive=False):
                    yield from cell.children
        else:
            yield child


def _find_element_by_xpath(soup: BeautifulSoup, xpath: str):
    """간이 XPath (예: "p[1]", "h2[3]")로 요소를 찾는다."""
    match = re.match(r'([a-z0-9:-]+)\[(\d+)\]', xpath)
    if not match:
        return None
    tag_name = match.group(1)
    index = int(match.group(2))  # 1-based

    count = 0
    for child in _iter_block_children(soup):
        if isinstance(child, Tag) and child.name == tag_name:
            count += 1
            if count == index:
                return child
    return None


def _apply_text_changes(element: Tag, old_text: str, new_text: str):
    """text node 단위로 old→new 변경을 적용. 인라인 태그 구조 보존.

    전략: old_text와 new_text 사이의 변경 부분(opcode)을 구하고,
    각 text node에서 해당 변경을 적용한다.
    """
    # 변경 부분 계산
    matcher = difflib.SequenceMatcher(None, old_text.strip(), new_text.strip())
    opcodes = matcher.get_opcodes()

    # text node 목록 수집 (순서대로)
    text_nodes = []
    for desc in element.descendants:
        if isinstance(desc, NavigableString) and not isinstance(desc, Tag):
            if desc.parent.name not in ('script', 'style'):
                text_nodes.append(desc)

    if not text_nodes:
        return

    # 각 text node의 old_text 내 위치 추적
    node_ranges = []  # (start_in_old, end_in_old, node)
    old_stripped = old_text.strip()
    pos = 0
    for node in text_nodes:
        node_str = str(node)
        node_stripped = node_str.strip()
        if not node_stripped:
            node_ranges.append((pos, pos, node))
            continue
        idx = old_stripped.find(node_stripped, pos)
        if idx == -1:
            node_ranges.append((pos, pos, node))
            continue
        node_ranges.append((idx, idx + len(node_stripped), node))
        pos = idx + len(node_stripped)

    # opcode를 적용하여 각 text node의 새 텍스트를 계산
    new_stripped = new_text.strip()
    for i, (node_start, node_end, node) in enumerate(node_ranges):
        if node_start == node_end:
            continue

        new_node_text = _map_text_range(
            old_stripped, new_stripped, opcodes, node_start, node_end
        )

        node_str = str(node)
        # 원본 whitespace 보존
        leading = node_str[:len(node_str) - len(node_str.lstrip())]
        trailing = node_str[len(node_str.rstrip()):]
        node.replace_with(NavigableString(leading + new_node_text + trailing))


def _map_text_range(old_text: str, new_text: str, opcodes, start: int, end: int) -> str:
    """old_text[start:end] 범위에 대응하는 new_text 부분을 추출한다."""
    result_parts = []
    for tag, i1, i2, j1, j2 in opcodes:
        # 이 opcode가 [start, end) 범위와 겹치는지 확인
        overlap_start = max(i1, start)
        overlap_end = min(i2, end)
        if overlap_start >= overlap_end and tag != 'insert':
            continue

        if tag == 'equal':
            if overlap_start < overlap_end:
                # old의 겹치는 부분만큼 new에서도 동일한 텍스트
                offset = overlap_start - i1
                length = overlap_end - overlap_start
                result_parts.append(new_text[j1 + offset:j1 + offset + length])
        elif tag == 'replace':
            if overlap_start < overlap_end:
                # old 범위 중 이 노드에 속하는 비율만큼 new 텍스트 할당
                old_len = i2 - i1
                new_len = j2 - j1
                ratio_start = (overlap_start - i1) / max(old_len, 1)
                ratio_end = (overlap_end - i1) / max(old_len, 1)
                ns = int(j1 + ratio_start * new_len)
                ne = int(j1 + ratio_end * new_len)
                result_parts.append(new_text[ns:ne])
        elif tag == 'insert':
            # insert는 old 텍스트에서 위치 i1 == i2
            # 이 insert가 현재 노드 범위 안에 위치하면 포함
            if start <= i1 <= end:
                result_parts.append(new_text[j1:j2])
        elif tag == 'delete':
            # 삭제된 부분은 new에 아무것도 추가하지 않음
            pass

    return ''.join(result_parts)
