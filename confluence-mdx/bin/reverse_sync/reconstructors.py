"""Inline-anchor fragment reconstructors.

Phase 3: paragraph/list item 내부 ac:image anchor 보존 재구성.
anchor offset 매핑 + DOM 삽입 + fragment 재구성 공용 helper.
"""
from __future__ import annotations

import difflib

from bs4 import BeautifulSoup, NavigableString, Tag

from reverse_sync.xhtml_normalizer import extract_plain_text


def map_anchor_offset(old_plain: str, new_plain: str, old_offset: int) -> int:
    """old_plain에서의 anchor offset을 new_plain 기준 offset으로 변환한다.

    difflib SequenceMatcher opcode를 사용해 old 좌표계를 new 좌표계로 매핑한다.
    anchor offset은 해당 위치 앞의 텍스트 바이트 수다 (삽입 지점).

    anchor 앞쪽 텍스트에 적용된 변경만 offset에 반영한다:
    - equal: 그대로 유지
    - replace: new 길이로 비례 매핑
    - insert (i1==i2 <= old_offset): new 텍스트 길이를 더함
    - delete: 삭제된 길이만큼 뺌
    """
    matcher = difflib.SequenceMatcher(None, old_plain, new_plain, autojunk=False)
    new_offset = 0
    consumed_old = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if consumed_old >= old_offset:
            break

        if tag == 'equal':
            take = min(i2, old_offset) - i1
            if take > 0:
                new_offset += take
                consumed_old += take

        elif tag == 'replace':
            old_take = min(i2, old_offset) - i1
            if old_take > 0:
                old_len = i2 - i1
                new_len = j2 - j1
                ratio = old_take / old_len
                new_offset += round(ratio * new_len)
                consumed_old += old_take

        elif tag == 'delete':
            old_take = min(i2, old_offset) - i1
            if old_take > 0:
                consumed_old += old_take

        elif tag == 'insert':
            if i1 <= old_offset:
                new_offset += j2 - j1

    if consumed_old < old_offset:
        new_offset += old_offset - consumed_old

    return new_offset


def insert_anchor_at_offset(p_element: Tag, offset: int, anchor_xhtml: str) -> None:
    """p 요소 내 offset 위치에 anchor_xhtml을 DOM 삽입한다 (in-place).

    offset은 extract_plain_text() 기준의 문자 수다.
    텍스트 노드를 순회하며 올바른 텍스트 노드를 분할하고 anchor를 삽입한다.
    """
    anchor_soup = BeautifulSoup(anchor_xhtml, 'html.parser')
    anchor_nodes = list(anchor_soup.children)
    if not anchor_nodes:
        return

    remaining = offset
    children = list(p_element.children)

    for child in children:
        if isinstance(child, NavigableString):
            text_len = len(str(child))
            if remaining <= text_len:
                text = str(child)
                before_text = text[:remaining]
                after_text = text[remaining:]

                # 직접 참조를 유지하여 before_node 뒤에 순서대로 삽입
                before_node = NavigableString(before_text)
                child.replace_with(before_node)

                pivot = before_node
                for anchor_node in anchor_nodes:
                    cloned = BeautifulSoup(str(anchor_node), 'html.parser')
                    for n in list(cloned.children):
                        extracted = n.extract()
                        pivot.insert_after(extracted)
                        pivot = extracted

                if after_text:
                    pivot.insert_after(NavigableString(after_text))
                return
            else:
                remaining -= text_len
        elif isinstance(child, Tag):
            if child.name != 'ac:image':
                child_text = extract_plain_text(str(child))
                if remaining <= len(child_text):
                    pivot = child
                    for anchor_node in anchor_nodes:
                        cloned = BeautifulSoup(str(anchor_node), 'html.parser')
                        for n in list(cloned.children):
                            extracted = n.extract()
                            pivot.insert_after(extracted)
                            pivot = extracted
                    return
                remaining -= len(child_text)

    # offset이 모든 텍스트를 초과하면 끝에 추가
    for anchor_node in anchor_nodes:
        cloned = BeautifulSoup(str(anchor_node), 'html.parser')
        for n in list(cloned.children):
            p_element.append(n.extract())


def reconstruct_inline_anchor_fragment(
    old_fragment: str,
    anchors: list,
    new_fragment: str,
) -> str:
    """new_fragment에 원본 anchors를 offset 매핑하여 재삽입한다.

    Args:
        old_fragment: 원본 XHTML fragment (anchor 포함)
        anchors: _build_anchor_entries()로 추출된 anchor entry 목록
        new_fragment: emit_block()으로 생성된 새 XHTML fragment (anchor 없음)

    Returns:
        anchor가 재삽입된 new_fragment
    """
    if not anchors:
        return new_fragment

    old_plain = extract_plain_text(old_fragment)
    new_plain = extract_plain_text(new_fragment)

    soup = BeautifulSoup(new_fragment, 'html.parser')
    p = soup.find('p')
    if p is None:
        return new_fragment

    # offset을 역순으로 처리하여 앞쪽 삽입이 뒤쪽 offset에 영향 미치지 않게 함
    for anchor in reversed(anchors):
        new_offset = map_anchor_offset(old_plain, new_plain, anchor['offset'])
        insert_anchor_at_offset(p, new_offset, anchor['raw_xhtml'])

    return str(soup)
