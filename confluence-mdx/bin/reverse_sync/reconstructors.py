"""Inline-anchor fragment reconstructors.

Phase 3: paragraph/list item 내부 ac:image anchor 보존 재구성.
anchor offset 매핑 + DOM 삽입 + fragment 재구성 공용 helper.
"""
from __future__ import annotations

import difflib
from typing import TYPE_CHECKING, List, Optional, Tuple

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


# ── container 재구성 헬퍼 ──────────────────────────────────────────────────────

def _has_inline_markup(fragment: str) -> bool:
    """fragment의 <p>에 ac:image 외 인라인 태그가 있으면 True를 반환한다.

    container reconstruction 필요 여부를 결정하는 데 사용한다.
    """
    if not fragment:
        return False
    soup = BeautifulSoup(fragment, 'html.parser')
    p = soup.find('p')
    if p is None:
        return False
    return any(
        isinstance(child, Tag) and child.name != 'ac:image'
        for child in p.children
    )


def _collect_text_nodes_with_offsets(
    element: Tag,
    start_offset: int,
    nodes: List[Tuple],
) -> int:
    """element 내부 텍스트 노드와 old_plain 기준 offset 범위를 수집한다."""
    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child)
            end_offset = start_offset + len(text)
            parent_name = child.parent.name if isinstance(child.parent, Tag) else ''
            nodes.append((child, start_offset, end_offset, parent_name))
            start_offset = end_offset
            continue
        if not isinstance(child, Tag):
            continue
        if child.name == 'ac:emoticon':
            start_offset += len(child.get('ac:emoji-fallback', ''))
            continue
        if child.name == 'ac:image':
            continue
        start_offset = _collect_text_nodes_with_offsets(child, start_offset, nodes)
    return start_offset


def _rewrite_inline_segments_on_template(root: Tag, new_plain: str) -> Optional[str]:
    """direct inline tag 구조를 유지한 채 paragraph 텍스트를 재배치한다.

    inline 태그가 없거나 <br>이 있으면 None을 반환한다 (fallback으로 text node 재배치).
    """
    segments: list = []
    tokens: list = []
    for child in root.children:
        if isinstance(child, NavigableString):
            segments.append(('text', str(child), ''))
            continue
        if not isinstance(child, Tag):
            continue
        if child.name == 'br':
            return None
        raw = str(child)
        plain = extract_plain_text(raw)
        token = f"__RS_INLINE_{len(tokens)}__"
        tokens.append((token, plain))
        segments.append(('tag', raw, token))

    if not tokens:
        return None

    tokenized_new = new_plain
    cursor = 0
    for token, plain in tokens:
        pos = tokenized_new.find(plain, cursor)
        if pos < 0:
            return None
        tokenized_new = tokenized_new[:pos] + token + tokenized_new[pos + len(plain):]
        cursor = pos + len(token)

    text_parts: list = []
    cursor = 0
    for token, _ in tokens:
        pos = tokenized_new.find(token, cursor)
        if pos < 0:
            return None
        text_parts.append(tokenized_new[cursor:pos])
        cursor = pos + len(token)
    text_parts.append(tokenized_new[cursor:])

    rebuilt: list = []
    remaining_text_parts = iter(text_parts)
    for kind, value, _ in segments:
        if kind == 'text':
            rebuilt.append(next(remaining_text_parts, ''))
        else:
            rebuilt.append(value)
    rebuilt.append(''.join(remaining_text_parts))

    return f"<{root.name}>{''.join(rebuilt)}</{root.name}>"


def _rewrite_paragraph_on_template(template_fragment: str, new_fragment: str) -> str:
    """원본 paragraph inline markup을 유지한 채 텍스트만 새 fragment 기준으로 갱신한다.

    1. inline tag 구조가 단순하면 tokenize 방식으로 재배치.
    2. 복잡한 경우 text node별 offset 매핑으로 재배치.
    텍스트가 동일하면 template_fragment를 그대로 반환한다.
    """
    old_plain = extract_plain_text(template_fragment)
    new_plain = extract_plain_text(new_fragment)
    if old_plain == new_plain:
        return template_fragment

    template_soup = BeautifulSoup(template_fragment, 'html.parser')
    root = next((child for child in template_soup.contents if isinstance(child, Tag)), None)
    if root is None:
        return new_fragment

    preserved_inline = _rewrite_inline_segments_on_template(root, new_plain)
    if preserved_inline is not None:
        return preserved_inline

    text_nodes: list = []
    _collect_text_nodes_with_offsets(root, 0, text_nodes)
    if not text_nodes:
        return new_fragment
    if len(text_nodes) == 1:
        text_nodes[0][0].replace_with(NavigableString(new_plain))
        return str(template_soup)

    for node, start_offset, end_offset, parent_name in text_nodes:
        new_start = map_anchor_offset(old_plain, new_plain, start_offset, affinity='before')
        new_end = map_anchor_offset(old_plain, new_plain, end_offset, affinity='after')
        replacement_text = new_plain[new_start:new_end]
        if parent_name == 'code':
            original_text = str(node)
            if replacement_text.replace('`', '') == original_text.replace('`', ''):
                replacement_text = original_text
        node.replace_with(NavigableString(replacement_text))

    return str(template_soup)


def _reconstruct_child_with_anchors(child_frag: str, child_meta: dict) -> str:
    """child fragment에 anchor를 offset 매핑으로 재삽입한다."""
    anchors = child_meta.get('anchors', [])
    if not anchors:
        return child_frag
    soup = BeautifulSoup(child_frag, 'html.parser')
    p = soup.find('p')
    if p is None:
        return child_frag
    old_plain = child_meta.get('plain_text', '')
    new_plain = extract_plain_text(child_frag)
    for anchor in reversed(anchors):
        new_offset = map_anchor_offset(old_plain, new_plain, anchor['offset'])
        insert_anchor_at_offset(p, new_offset, anchor['raw_xhtml'])
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
    if recon.get('kind') == 'container':
        return container_sidecar_requires_reconstruction(sidecar_block)
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
    if kind == 'container':
        return reconstruct_container_fragment(new_fragment, sidecar_block)
    return new_fragment


def container_sidecar_requires_reconstruction(
    sidecar_block: Optional['SidecarBlock'],
) -> bool:
    """container sidecar block에 anchor 재구성이 필요한 child가 있으면 True를 반환한다.

    ac:image anchor 또는 list item anchor가 있는 child가 하나 이상 있어야 True.
    reconstruction이 트리거된 후에는 같은 container 내 inline markup도 함께 보존한다.
    """
    if sidecar_block is None or sidecar_block.reconstruction is None:
        return False
    recon = sidecar_block.reconstruction
    if recon.get('kind') != 'container':
        return False
    return any(
        c.get('anchors') or c.get('items')
        for c in recon.get('children', [])
    )


def reconstruct_container_fragment(
    new_fragment: str,
    sidecar_block: Optional['SidecarBlock'],
) -> str:
    """Container (callout/ADF panel) fragment에 sidecar child 메타데이터로 재구성한다.

    anchor 없는 clean container는 new_fragment를 그대로 반환한다.
    anchor가 있어 재구성이 트리거된 경우 아래 세 단계를 각 child에 적용한다:
    1. inline markup 보존: 원본 fragment를 template으로 bold·italic·link 유지
    2. anchor 재삽입: ac:image를 offset 매핑으로 복원
    3. outer wrapper 보존: sidecar xhtml_fragment를 template으로 macro 속성 유지
    """
    if sidecar_block is None or sidecar_block.reconstruction is None:
        return new_fragment
    recon = sidecar_block.reconstruction
    if recon.get('kind') != 'container':
        return new_fragment
    children_meta = recon.get('children', [])
    if not any(c.get('anchors') or c.get('items') for c in children_meta):
        return new_fragment  # clean container — emit_block result 그대로 사용

    # emitted new_fragment에서 body children 추출
    emitted_soup = BeautifulSoup(new_fragment, 'html.parser')
    emitted_body = emitted_soup.find('ac:rich-text-body') or emitted_soup.find('ac:adf-content')
    if emitted_body is None:
        return new_fragment

    emitted_children = [c for c in emitted_body.children if isinstance(c, Tag)]

    # 각 child 재구성
    rebuilt_fragments = []
    for i, child_tag in enumerate(emitted_children):
        if i >= len(children_meta):
            rebuilt_fragments.append(str(child_tag))
            continue
        child_meta = children_meta[i]
        stored_fragment = child_meta.get('fragment', '')
        child_frag = str(child_tag)

        # Step 1: inline markup 보존 (stored fragment를 template으로 재구성)
        if stored_fragment and _has_inline_markup(stored_fragment):
            child_frag = _rewrite_paragraph_on_template(stored_fragment, child_frag)

        # Step 2: anchor 재삽입
        if child_meta.get('anchors'):
            child_frag = _reconstruct_child_with_anchors(child_frag, child_meta)

        rebuilt_fragments.append(child_frag)

    # Step 3: outer wrapper template (macro 속성 보존)
    outer_template = sidecar_block.xhtml_fragment
    template_soup = BeautifulSoup(outer_template or new_fragment, 'html.parser')
    template_body = (
        template_soup.find('ac:rich-text-body') or template_soup.find('ac:adf-content')
    )
    if template_body is None:
        return new_fragment

    for child in list(template_body.contents):
        child.extract()
    for frag in rebuilt_fragments:
        frag_soup = BeautifulSoup(frag, 'html.parser')
        for node in list(frag_soup.contents):
            template_body.append(node.extract())

    return str(template_soup)


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
