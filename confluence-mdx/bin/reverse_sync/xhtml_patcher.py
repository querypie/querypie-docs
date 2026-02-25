"""XHTML Patcher — 매핑과 diff를 이용해 XHTML의 텍스트를 패치한다."""
from typing import List, Dict
from bs4 import BeautifulSoup, NavigableString, Tag
import difflib
import re


def patch_xhtml(xhtml: str, patches: List[Dict[str, str]]) -> str:
    """XHTML에 패치를 적용한다.

    Args:
        xhtml: 원본 XHTML 문자열
        patches: 패치 목록. 각 패치는 dict:
            - action: "modify" (기본) | "delete" | "insert"
            - modify: xhtml_xpath, old_plain_text, new_plain_text 또는 new_inner_xhtml
            - delete: xhtml_xpath
            - insert: after_xpath (None이면 맨 앞), new_element_xhtml

    Returns:
        패치된 XHTML 문자열
    """
    soup = BeautifulSoup(xhtml, 'html.parser')

    # 패치를 action별로 분류
    delete_patches = [p for p in patches if p.get('action') == 'delete']
    insert_patches = [p for p in patches if p.get('action') == 'insert']
    modify_patches = [p for p in patches
                      if p.get('action', 'modify') == 'modify']

    # 모든 xpath를 DOM 변경 전에 미리 resolve (인덱스 shift 방지)
    resolved_deletes = []
    for p in delete_patches:
        el = _find_element_by_xpath(soup, p['xhtml_xpath'])
        if el is not None:
            resolved_deletes.append(el)

    resolved_inserts = []
    for p in insert_patches:
        after_xpath = p.get('after_xpath')
        anchor = None
        if after_xpath is not None:
            anchor = _find_element_by_xpath(soup, after_xpath)
            if anchor is None:
                continue  # anchor를 못 찾으면 skip
        resolved_inserts.append((anchor, p))

    resolved_modifies = []
    for p in modify_patches:
        el = _find_element_by_xpath(soup, p['xhtml_xpath'])
        if el is not None:
            resolved_modifies.append((el, p))

    # 1단계: delete
    for element in resolved_deletes:
        element.decompose()

    # 2단계: insert
    for anchor, patch in resolved_inserts:
        _insert_element_resolved(soup, anchor, patch['new_element_xhtml'])

    # 3단계: modify
    for element, patch in resolved_modifies:
        if 'new_inner_xhtml' in patch:
            old_text = patch.get('old_plain_text', '')
            current_plain = element.get_text()
            if old_text and current_plain.strip() != old_text.strip():
                continue
            _replace_inner_html(element, patch['new_inner_xhtml'])
        else:
            old_text = patch['old_plain_text']
            new_text = patch['new_plain_text']
            current_plain = element.get_text()
            if current_plain.strip() != old_text.strip():
                continue
            _apply_text_changes(element, old_text, new_text)

    result = str(soup)
    result = _restore_cdata(result)
    return result


def _xpath_index(xpath: str) -> int:
    """xpath에서 인덱스 부분을 추출한다 (정렬용)."""
    match = re.search(r'\[(\d+)\]', xpath)
    return int(match.group(1)) if match else 0


def _insert_element_resolved(soup: BeautifulSoup, anchor, new_html: str):
    """미리 resolve된 anchor를 사용하여 새 요소를 삽입한다."""
    new_parsed = BeautifulSoup(new_html, 'html.parser')

    if anchor is None:
        # 첫 번째 블록 요소 앞에 삽입
        first_block = _find_first_block_element(soup)
        if first_block:
            for child in reversed(list(new_parsed.children)):
                first_block.insert_before(child.extract())
        else:
            for child in list(new_parsed.children):
                soup.append(child.extract())
    else:
        children = list(new_parsed.children)
        for child in reversed(children):
            anchor.insert_after(child.extract())


def _find_first_block_element(soup: BeautifulSoup):
    """soup의 첫 번째 블록 레벨 요소를 찾는다."""
    for child in _iter_block_children(soup):
        if isinstance(child, Tag):
            return child
    return None


def _restore_cdata(xhtml: str) -> str:
    """BeautifulSoup가 제거한 CDATA 래핑을 ac:plain-text-body에 복원한다."""
    def _wrap_cdata(m):
        tag_open = m.group(1)
        content = m.group(2)
        tag_close = m.group(3)
        # 이미 CDATA 래핑이 있으면 건드리지 않음
        if '<![CDATA[' in content:
            return m.group(0)
        return f'{tag_open}<![CDATA[{content.strip()}]]>{tag_close}'
    return re.sub(
        r'(<ac:plain-text-body[^>]*>)(.*?)(</ac:plain-text-body>)',
        _wrap_cdata,
        xhtml,
        flags=re.DOTALL,
    )


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
    """간이 XPath로 요소를 찾는다.

    단일 xpath: "p[1]", "h2[3]", "macro-info[1]"
    복합 xpath: "macro-info[1]/p[1]", "macro-note[2]/ul[1]"
    """
    parts = xpath.split('/')
    if len(parts) == 1:
        return _find_element_by_simple_xpath(soup, xpath)

    # 복합 xpath: 먼저 부모를 찾고, 내부 컨테이너에서 자식 검색
    parent = _find_element_by_simple_xpath(soup, parts[0])
    if parent is None:
        return None

    container = _find_content_container(parent)
    if container is None:
        return None

    return _find_child_in_element(container, parts[1])


def _find_element_by_simple_xpath(soup: BeautifulSoup, xpath: str):
    """간이 XPath (예: "p[1]", "h2[3]", "macro-info[1]")로 요소를 찾는다.

    macro-* 패턴은 ac:structured-macro[ac:name="*"]로 해석한다.
    """
    match = re.match(r'([a-z0-9:-]+)\[(\d+)\]', xpath)
    if not match:
        return None
    tag_name = match.group(1)
    index = int(match.group(2))  # 1-based

    # macro-{name} → ac:structured-macro[ac:name="{name}"] 매핑
    macro_name = None
    if tag_name.startswith('macro-'):
        macro_name = tag_name[len('macro-'):]

    count = 0
    for child in _iter_block_children(soup):
        if not isinstance(child, Tag):
            continue
        if macro_name:
            if child.name == 'ac:structured-macro' and child.get('ac:name') == macro_name:
                count += 1
                if count == index:
                    return child
        elif child.name == tag_name:
            count += 1
            if count == index:
                return child
    return None


def _find_content_container(parent: Tag):
    """복합 xpath의 부모 요소에서 자식 콘텐츠 컨테이너를 찾는다.

    ac:structured-macro → ac:rich-text-body
    ac:adf-extension → ac:adf-node > ac:adf-content
    """
    rich_body = parent.find('ac:rich-text-body')
    if rich_body is not None:
        return rich_body
    node = parent.find('ac:adf-node')
    if node is not None:
        content = node.find('ac:adf-content')
        if content is not None:
            return content
    return None


def _find_child_in_element(parent: Tag, xpath_part: str):
    """부모 요소 내에서 간이 xpath로 직접 자식을 찾는다."""
    match = re.match(r'([a-z0-9:-]+)\[(\d+)\]', xpath_part)
    if not match:
        return None
    tag_name = match.group(1)
    index = int(match.group(2))

    count = 0
    for child in parent.children:
        if not isinstance(child, Tag):
            continue
        if child.name == tag_name:
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
    # autojunk=False: 한국어 등 반복 문자가 많은 텍스트에서
    # autojunk이 로컬 매칭을 건너뛰어 대규모 insert/delete를 생성하는 것을 방지
    matcher = difflib.SequenceMatcher(None, old_text.strip(), new_text.strip(), autojunk=False)
    opcodes = matcher.get_opcodes()

    # text node 목록 수집 (순서대로)
    # ac:plain-text-body 내부의 텍스트는 CDATA로 보호되는 코드 본문이므로 제외
    text_nodes = []
    for desc in element.descendants:
        if isinstance(desc, NavigableString) and not isinstance(desc, Tag):
            if desc.parent.name not in ('script', 'style', 'ac:plain-text-body'):
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
    # 마지막 non-empty 노드 인덱스 (trailing insert 포함용)
    last_nonempty_idx = -1
    for j in range(len(node_ranges) - 1, -1, -1):
        if node_ranges[j][0] != node_ranges[j][1]:
            last_nonempty_idx = j
            break

    for i, (node_start, node_end, node) in enumerate(node_ranges):
        if node_start == node_end:
            continue

        # _map_text_range는 half-open [start, end)를 사용하므로,
        # 마지막 non-empty 노드에서는 end를 확장하여 trailing insert를 포함한다.
        effective_end = node_end + 1 if i == last_nonempty_idx else node_end
        new_node_text = _map_text_range(
            old_stripped, new_stripped, opcodes, node_start, effective_end
        )

        node_str = str(node)
        # 원본 whitespace 보존 (단, diff에서 삭제된 선행 공백은 제거)
        leading = node_str[:len(node_str) - len(node_str.lstrip())]
        trailing = node_str[len(node_str.rstrip()):]

        # 직전 노드 범위와 현재 노드 범위 사이의 gap이 diff로 삭제된 경우,
        # leading whitespace를 제거한다.
        # 예: <strong>IDENTIFIER</strong> 조사 → IDENTIFIER조사 (공백 교정)
        if leading and i > 0:
            prev_end = node_ranges[i - 1][1]
            if prev_end < node_start:
                gap_new = _map_text_range(
                    old_stripped, new_stripped, opcodes, prev_end, node_start
                )
                if not gap_new:
                    leading = ''

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
            # 이 insert가 현재 노드 범위 [start, end) 안에 위치하면 포함
            # half-open range를 사용하여 인접 노드 경계에서 중복 삽입 방지
            if start <= i1 < end:
                result_parts.append(new_text[j1:j2])
        elif tag == 'delete':
            # 삭제된 부분은 new에 아무것도 추가하지 않음
            pass

    return ''.join(result_parts)
