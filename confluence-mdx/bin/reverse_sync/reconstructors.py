"""Inline-anchor fragment reconstructors.

Phase 3: paragraph/list item 내부 ac:image anchor 보존 재구성.
anchor offset 매핑 + DOM 삽입 + fragment 재구성 공용 helper.
"""
from __future__ import annotations

import difflib
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from reverse_sync.xhtml_normalizer import extract_plain_text

if TYPE_CHECKING:
    from reverse_sync.sidecar import SidecarBlock


def map_anchor_offset(
    old_plain: str,
    new_plain: str,
    old_offset: int,
    affinity: str = 'before',
) -> int:
    """old_plain에서의 anchor offset을 new_plain 기준 offset으로 변환한다.

    difflib SequenceMatcher opcode를 사용해 old 좌표계를 new 좌표계로 매핑한다.
    anchor offset은 해당 위치 앞의 텍스트 바이트 수다 (삽입 지점).

    anchor 앞쪽 텍스트에 적용된 변경만 offset에 반영한다:
    - equal: 그대로 유지
    - replace: new 길이로 비례 매핑
    - insert at boundary: affinity='before'이면 삽입 포함, 'after'이면 제외
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
            # 경계(i1 == old_offset)에서 affinity로 배치 방향 결정:
            # 'before': anchor가 삽입된 텍스트 뒤에 위치 (삽입 포함)
            # 'after': anchor가 삽입된 텍스트 앞에 위치 (삽입 제외)
            if i1 < old_offset or (i1 == old_offset and affinity == 'before'):
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


def _find_list_item_by_path(root: Tag, path: list) -> Optional[Tag]:
    """path 인덱스 경로를 따라 li 요소를 탐색한다."""
    current_list: Optional[Tag] = root
    current_li: Optional[Tag] = None
    for index in path:
        if current_list is None:
            return None
        items = [c for c in current_list.children if isinstance(c, Tag) and c.name == 'li']
        if index < 0 or index >= len(items):
            return None
        current_li = items[index]
        current_list = next(
            (c for c in current_li.children if isinstance(c, Tag) and c.name in ('ul', 'ol')),
            None,
        )
    return current_li


def _find_direct_list_item_paragraph(li: Tag) -> Tag:
    """li의 직접 자식 p 요소를 반환한다. 없으면 li 자체를 반환."""
    for child in li.children:
        if isinstance(child, Tag) and child.name == 'p':
            return child
    return li


def _rebuild_list_fragment(new_fragment: str, recon: dict) -> str:
    """list fragment에 sidecar anchor entries를 경로 기반으로 재주입한다."""
    soup = BeautifulSoup(new_fragment, 'html.parser')
    root = soup.find(['ul', 'ol'])
    if root is None:
        return new_fragment

    old_plain = recon.get('old_plain_text', '')
    for entry in recon.get('items', []):
        if not entry.get('raw_xhtml') or 'offset' not in entry:
            continue
        path = entry.get('path', [])
        li = _find_list_item_by_path(root, path)
        if li is None:
            continue
        p = _find_direct_list_item_paragraph(li)
        new_p_plain = extract_plain_text(str(p))
        new_offset = map_anchor_offset(old_plain, new_p_plain, entry['offset'])
        insert_anchor_at_offset(p, new_offset, entry['raw_xhtml'])

    return str(soup)


def sidecar_block_requires_reconstruction(
    sidecar_block: Optional['SidecarBlock'],
) -> bool:
    """sidecar block에 Phase 3 재구성이 필요한 metadata가 있으면 True를 반환한다.

    offset + raw_xhtml이 모두 있는 유효한 anchor가 하나 이상 있어야 True를 반환한다.
    """
    if sidecar_block is None or sidecar_block.reconstruction is None:
        return False
    recon = sidecar_block.reconstruction
    if recon.get('kind') == 'paragraph':
        return any(
            'offset' in a and 'raw_xhtml' in a
            for a in recon.get('anchors', [])
        )
    if recon.get('kind') == 'list':
        return any(
            'offset' in item and 'raw_xhtml' in item
            for item in recon.get('items', [])
        )
    return False


def reconstruct_fragment_with_sidecar(
    new_fragment: str,
    sidecar_block: Optional['SidecarBlock'],
) -> str:
    """new_fragment에 sidecar block의 anchor metadata를 재주입한다."""
    if sidecar_block is None or sidecar_block.reconstruction is None:
        return new_fragment
    recon = sidecar_block.reconstruction
    kind = recon.get('kind')
    if kind == 'paragraph':
        anchors = recon.get('anchors', [])
        valid_anchors = [a for a in anchors if 'offset' in a and 'raw_xhtml' in a]
        if valid_anchors:
            old_plain = recon.get('old_plain_text', '')
            return reconstruct_inline_anchor_fragment(old_plain, valid_anchors, new_fragment)
    if kind == 'list':
        return _rebuild_list_fragment(new_fragment, recon)
    return new_fragment


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
