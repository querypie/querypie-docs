"""XHTML Patcher — fragment 단위 DOM patch를 적용한다."""
from typing import List, Dict
from bs4 import BeautifulSoup, NavigableString, Tag
import difflib
import re
from reverse_sync.mapping_recorder import get_text_with_emoticons, iter_block_children


def patch_xhtml(xhtml: str, patches: List[Dict[str, str]]) -> str:
    """XHTML에 패치를 적용한다.

    Args:
        xhtml: 원본 XHTML 문자열
        patches: 패치 목록. 각 패치는 dict:
            - action: "modify" (기본) | "delete" | "insert" | "replace_fragment"
            - modify: xhtml_xpath, old_plain_text, new_plain_text 또는 new_inner_xhtml
            - delete: xhtml_xpath
            - insert: after_xpath (None이면 맨 앞), new_element_xhtml
            - replace_fragment: xhtml_xpath, new_element_xhtml

    Returns:
        패치된 XHTML 문자열
    """
    soup = BeautifulSoup(xhtml, 'html.parser')

    # 패치를 action별로 분류
    delete_patches = [p for p in patches if p.get('action') == 'delete']
    insert_patches = [p for p in patches if p.get('action') == 'insert']
    replace_patches = [p for p in patches if p.get('action') == 'replace_fragment']
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

    resolved_replacements = []
    for p in replace_patches:
        el = _find_element_by_xpath(soup, p['xhtml_xpath'])
        if el is not None:
            resolved_replacements.append((el, p))

    # 1단계: delete
    for element in resolved_deletes:
        element.decompose()

    # 2단계: insert
    for anchor, patch in resolved_inserts:
        _insert_element_resolved(soup, anchor, patch['new_element_xhtml'])

    # 3단계: replace fragment
    for element, patch in resolved_replacements:
        _replace_element_resolved(element, patch['new_element_xhtml'])

    # 4단계: modify
    for element, patch in resolved_modifies:
        if 'new_inner_xhtml' in patch:
            old_text = patch.get('old_plain_text', '')
            # mapping_recorder는 top-level list/paragraph에서 get_text() 기준 plain을 기록한다.
            # patch 적용 시에는 기본 비교를 get_text()로 수행하고, 필요 시 emoticon fallback 텍스트 비교를 허용한다.
            current_plain = element.get_text()
            if old_text and current_plain.strip() != old_text.strip():
                current_plain_with_emoticons = get_text_with_emoticons(element)
                if current_plain_with_emoticons.strip() != old_text.strip():
                    continue
            _replace_inner_html(element, patch['new_inner_xhtml'])
            if 'ol_start' in patch and isinstance(element, Tag) and element.name == 'ol':
                new_start = patch['ol_start']
                if new_start == 1:
                    if 'start' in element.attrs:
                        del element['start']
                else:
                    element['start'] = str(new_start)
        else:
            old_text = patch['old_plain_text']
            new_text = patch['new_plain_text']
            # mapping plain(old_text)과의 비교는 get_text() 우선, 실패 시 emoticon fallback 포함 텍스트로 재확인한다.
            current_plain = element.get_text()
            if current_plain.strip() != old_text.strip():
                current_plain_with_emoticons = get_text_with_emoticons(element)
                if current_plain_with_emoticons.strip() != old_text.strip():
                    continue
            _apply_text_changes(element, old_text, new_text)
            if 'ol_start' in patch and isinstance(element, Tag) and element.name == 'ol':
                new_start = patch['ol_start']
                if new_start == 1:
                    if 'start' in element.attrs:
                        del element['start']
                else:
                    element['start'] = str(new_start)
            if 'inline_fixups' in patch:
                _apply_inline_fixups(element, patch['inline_fixups'])

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
    for child in iter_block_children(soup):
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


def _replace_element_resolved(element: Tag, new_html: str):
    """요소 전체를 새 fragment로 교체한다."""
    new_content = BeautifulSoup(new_html, 'html.parser')
    replacements = [child.extract() for child in list(new_content.children)]
    if not replacements:
        element.decompose()
        return

    first = replacements[0]
    element.replace_with(first)
    prev = first
    for child in replacements[1:]:
        prev.insert_after(child)
        prev = child


def _find_element_by_xpath(soup: BeautifulSoup, xpath: str):
    """간이 XPath로 요소를 찾는다.

    단일 xpath: "p[1]", "h2[3]", "macro-info[1]"
    복합 xpath: "macro-info[1]/p[1]", "macro-note[2]/ul[1]"
    다단계 xpath: "ul[3]/li[7]/p[1]"
    """
    parts = xpath.split('/')
    if len(parts) == 1:
        return _find_element_by_simple_xpath(soup, xpath)

    # 복합 xpath: 먼저 부모를 찾고, 내부 컨테이너에서 자식 검색
    current = _find_element_by_simple_xpath(soup, parts[0])
    if current is None:
        return None

    for part in parts[1:]:
        # ac:structured-macro 등은 content container 내부에서 검색
        container = _find_content_container(current)
        if container is None:
            if ':' in (current.name or ''):
                # ac:structured-macro 등 Confluence 요소는 content container 없이
                # 자식 검색 불가 (기존 동작 유지)
                return None
            # 일반 HTML 요소 (ul, ol, li 등)는 직접 자식 검색
            container = current
        current = _find_child_in_element(container, part)
        if current is None:
            return None

    return current


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
    for child in iter_block_children(soup):
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


def _collapse_ws(s: str) -> str:
    """연속 공백을 단일 공백으로 축소한다."""
    return re.sub(r'\s+', ' ', s).strip()


def _has_preserved_markup_ancestor(node: NavigableString, stop: Tag) -> bool:
    """text node가 보존 대상 Confluence 마크업 내부에 있는지 확인한다."""
    parent = node.parent
    while isinstance(parent, Tag) and parent is not stop:
        if (parent.name or '').startswith(('ac:', 'ri:')):
            return True
        parent = parent.parent
    return False


def _strip_trailing_text(tag: Tag, suffix: str) -> bool:
    """태그 내부 trailing text만 제거한다. preserved markup 내부 text는 건드리지 않는다."""
    remaining = suffix
    while remaining:
        last_text = None
        for desc in reversed(list(tag.descendants)):
            if isinstance(desc, NavigableString):
                last_text = desc
                break
        if last_text is None or _has_preserved_markup_ancestor(last_text, tag):
            return False
        node_text = str(last_text)
        remove_len = min(len(node_text), len(remaining))
        expected = remaining[-remove_len:]
        if not node_text.endswith(expected):
            return False
        kept = node_text[:-remove_len]
        if kept:
            last_text.replace_with(NavigableString(kept))
        else:
            last_text.extract()
        remaining = remaining[:-remove_len]
    return True


def _append_text_to_tag(tag: Tag, text: str):
    """태그의 마지막 text node에 텍스트를 덧붙인다."""
    if not text:
        return
    if tag.contents and isinstance(tag.contents[-1], NavigableString):
        last = tag.contents[-1]
        last.replace_with(NavigableString(str(last) + text))
    else:
        tag.append(NavigableString(text))



def _apply_strong_boundary_fixup(p_tag: Tag, new_inner_xhtml: str):
    """<ac:>/<ri:> 보존 시 <strong> 요소만 직접 수정하여 bold 경계를 교정한다.

    innerHTML 전체 교체는 <ac:link> 등 preserved anchor를 파괴하므로,
    new_inner_xhtml에서 목표 <strong> 구조를 추출하고 기존 <p>의 <strong>
    텍스트만 갱신한 뒤, 경계 이동으로 빠져나온 문자를 인접 text node에 반영한다.
    """
    new_soup = BeautifulSoup(new_inner_xhtml, 'html.parser')
    old_strongs = p_tag.find_all('strong')
    new_strongs = new_soup.find_all('strong')

    if len(old_strongs) != len(new_strongs):
        return

    for old_s, new_s in zip(old_strongs, new_strongs):
        old_text = old_s.get_text()
        new_text = new_s.get_text()
        if old_text == new_text:
            continue

        # bold 끝에서 빠져나온 문자를 다음 text node에 반영
        if old_text.startswith(new_text) and len(old_text) > len(new_text):
            removed_end = old_text[len(new_text):]
            if not _strip_trailing_text(old_s, removed_end):
                continue
            nxt = old_s.next_sibling
            if isinstance(nxt, NavigableString):
                nxt.replace_with(NavigableString(removed_end + str(nxt)))
            else:
                old_s.insert_after(NavigableString(removed_end))

        # bold 끝으로 흡수된 문자를 다음 text node에서 제거
        elif new_text.startswith(old_text) and len(new_text) > len(old_text):
            added_end = new_text[len(old_text):]
            nxt = old_s.next_sibling
            if isinstance(nxt, NavigableString):
                ns = str(nxt)
                if ns.startswith(added_end):
                    rest = ns[len(added_end):]
                    if rest:
                        nxt.replace_with(NavigableString(rest))
                    else:
                        nxt.extract()
                    _append_text_to_tag(old_s, added_end)


def _apply_inline_fixups(element: Tag, fixups: list):
    """인라인 마커 경계 변경을 DOM에 적용한다.

    text-level 패치는 인라인 태그(<strong>, <em>) 경계를 변경할 수 없으므로,
    fixup 리스트의 각 항목에 대해 매칭하는 <p> 요소의 innerHTML을 교체한다.
    """
    if not fixups:
        return
    for fixup in fixups:
        old_plain = fixup['old_plain'].strip()
        new_plain = fixup.get('new_plain', old_plain).strip()
        new_inner = fixup['new_inner_xhtml']
        match_index = int(fixup.get('match_index', 0))
        current_match = 0
        if not old_plain:
            continue
        new_plain_collapsed = _collapse_ws(new_plain)
        for p_tag in element.find_all('p'):
            p_text = p_tag.get_text().strip()
            # _apply_text_changes 이후 <p> 텍스트는 new_plain으로 업데이트되므로
            # new_plain 기준으로만 매칭한다. old_plain도 허용하면 미변경 앞 항목을
            # 잘못 수정할 수 있다 (old_plain != new_plain인 경우).
            if _collapse_ws(p_text) != new_plain_collapsed:
                continue
            if current_match != match_index:
                current_match += 1
                continue
            p_html = str(p_tag)
            if '<ac:' in p_html or '<ri:' in p_html:
                _apply_strong_boundary_fixup(p_tag, new_inner)
                break
            _replace_inner_html(p_tag, new_inner)
            break


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

    # 블록 경계 감지: 서로 다른 블록 부모(p, li 등)에 속하는 인접 텍스트 노드 사이에서
    # insert가 잘못된 노드에 할당되는 것을 방지한다.
    # block_boundary_pairs: (left_idx, right_idx) 쌍 - 블록 경계를 이루는 노드 인덱스
    block_boundary_pairs = []
    prev_nonempty_idx = -1
    for j, (ns, ne, nd) in enumerate(node_ranges):
        if ns == ne:
            continue
        if prev_nonempty_idx >= 0:
            prev_node = node_ranges[prev_nonempty_idx][2]
            if _find_block_ancestor(prev_node) is not _find_block_ancestor(nd):
                block_boundary_pairs.append((prev_nonempty_idx, j))
        prev_nonempty_idx = j

    # 블록 경계에서 insert가 right 노드에 기본 할당되는 것을 수정한다.
    # right 노드 내부에 자체 변경(replace/delete/strictly-inside-insert)이 있으면
    # boundary insert는 right의 동반 변경이므로 기본 동작을 유지한다.
    # right 노드에 변경이 없으면 insert는 left 노드에 귀속시킨다.
    # 예: "이모지 깨지는 이슈" + insert(" 해결") + unchanged → left에 할당
    # 예: unchanged + insert("[") + "Authentication]..." → right에 할당
    claim_end_set = set()
    exclude_start_set = set()
    for left_idx, right_idx in block_boundary_pairs:
        right_start, right_end, _ = node_ranges[right_idx]
        has_changes_in_right = any(
            (tag in ('replace', 'delete')
             and max(i1, right_start) < min(i2, right_end))
            or (tag == 'insert' and right_start < i1 < right_end)
            for tag, i1, i2, j1, j2 in opcodes
        )
        if not has_changes_in_right:
            claim_end_set.add(left_idx)
            exclude_start_set.add(right_idx)

    for i, (node_start, node_end, node) in enumerate(node_ranges):
        if node_start == node_end:
            continue

        # _map_text_range는 half-open [start, end)를 사용하므로,
        # 마지막 non-empty 노드에서는 end를 확장하여 trailing insert를 포함한다.
        # 단, 텍스트 노드가 old_text 전체를 커버하지 않는 경우(예: callout 내부
        # 코드 블록이 ac:plain-text-body로 제외된 경우) +1이 비텍스트 영역에
        # 침범하여 잘못된 문자가 포함되는 것을 방지한다.
        effective_end = (node_end + 1
                         if i == last_nonempty_idx and node_end >= len(old_stripped)
                         else node_end)

        node_str = str(node)
        leading = node_str[:len(node_str) - len(node_str.lstrip())]
        trailing = node_str[len(node_str.rstrip()):]

        # 내부 노드의 trailing whitespace가 old_stripped에 존재하면
        # diff 범위를 확장하여 자연스럽게 처리한다.
        # (예: <ac:link-body>text </ac:link-body> 의 trailing space)
        trailing_in_range = False
        if trailing and effective_end < len(old_stripped):
            potential = old_stripped[node_end:node_end + len(trailing)]
            if potential == trailing:
                effective_end = node_end + len(trailing)
                trailing_in_range = True

        # 블록 경계에서는 include_insert_at_end/exclude_insert_at_start로
        # insert를 올바른 노드에 할당한다.
        include_at_end = i in claim_end_set and i != last_nonempty_idx
        exclude_at_start = i in exclude_start_set
        new_node_text = _map_text_range(
            old_stripped, new_stripped, opcodes, node_start, effective_end,
            include_insert_at_end=include_at_end,
            exclude_insert_at_start=exclude_at_start,
        )

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

        if trailing_in_range:
            # diff가 trailing whitespace를 처리했으므로 별도 보존 불필요
            node.replace_with(NavigableString(leading + new_node_text))
        else:
            # 마지막 노드의 edge trailing whitespace가 변경된 경우 반영
            if trailing and i == last_nonempty_idx:
                old_edge_trailing = old_text[len(old_text.rstrip()):]
                new_edge_trailing = new_text[len(new_text.rstrip()):]
                if old_edge_trailing != new_edge_trailing:
                    trailing = new_edge_trailing
            node.replace_with(NavigableString(leading + new_node_text + trailing))


def _find_block_ancestor(node):
    """텍스트 노드의 가장 가까운 블록 레벨 부모 요소를 찾는다."""
    _BLOCK_TAGS = {
        'p', 'li', 'td', 'th', 'div', 'blockquote',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    }
    parent = node.parent
    while parent:
        if isinstance(parent, Tag) and parent.name in _BLOCK_TAGS:
            return parent
        parent = parent.parent
    return None


def _map_text_range(old_text: str, new_text: str, opcodes, start: int, end: int,
                    include_insert_at_end: bool = False,
                    exclude_insert_at_start: bool = False) -> str:
    """old_text[start:end] 범위에 대응하는 new_text 부분을 추출한다.

    Args:
        include_insert_at_end: True이면 i1 == end 위치의 insert도 포함한다.
            블록 경계에서 trailing insert를 현재 노드에 할당할 때 사용.
        exclude_insert_at_start: True이면 i1 == start 위치의 insert를 제외한다.
            이전 노드가 해당 insert를 이미 claim한 경우 중복 방지용.
    """
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
            if exclude_insert_at_start and i1 == start:
                continue
            if start <= i1 < end:
                result_parts.append(new_text[j1:j2])
            elif include_insert_at_end and i1 == end:
                result_parts.append(new_text[j1:j2])
        elif tag == 'delete':
            # 삭제된 부분은 new에 아무것도 추가하지 않음
            pass

    return ''.join(result_parts)
