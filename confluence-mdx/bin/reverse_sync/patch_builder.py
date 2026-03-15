"""패치 빌더 — MDX diff 변경과 XHTML 매핑을 결합하여 XHTML 패치를 생성."""
from typing import Dict, List, Optional

from mdx_to_storage.emitter import emit_block
from mdx_to_storage.parser import parse_mdx
from reverse_sync.block_diff import BlockChange, NON_CONTENT_TYPES
from reverse_sync.mapping_recorder import BlockMapping
from mdx_to_storage.parser import Block as MdxBlock
from text_utils import (
    normalize_mdx_to_plain, collapse_ws,
)
from reverse_sync.text_transfer import transfer_text_changes
from reverse_sync.sidecar import (
    RoundtripSidecar,
    SidecarBlock,
    find_mapping_by_sidecar,
    find_sidecar_block_by_identity,
    sha256_text,
    SidecarEntry,
)
from reverse_sync.lost_info_patcher import apply_lost_info, distribute_lost_info_to_mappings
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_xhtml_element, mdx_block_to_inner_xhtml
from reverse_sync.reconstructors import (
    sidecar_block_requires_reconstruction,
    reconstruct_fragment_with_sidecar,
)
from reverse_sync.list_patcher import (
    build_list_item_patches,
)
from reverse_sync.table_patcher import (
    build_table_row_patches,
    split_table_rows,
    normalize_table_row,
    is_markdown_table,
)


_CLEAN_BLOCK_TYPES = frozenset(("heading", "code_block", "hr"))


def _contains_preserved_anchor_markup(xhtml_text: str) -> bool:
    """preservation unit이 있으면 clean whole-fragment replacement 대상이 아니다."""
    return "<ac:" in xhtml_text or "<ri:" in xhtml_text


def _is_clean_block(
    block_type: str,
    mapping: Optional[BlockMapping],
    sidecar_block: Optional[SidecarBlock],
) -> bool:
    """Phase 2 clean block 여부를 판별한다."""
    if mapping is None:
        return False

    if block_type in _CLEAN_BLOCK_TYPES:
        return True

    if sidecar_block is not None:
        recon = sidecar_block.reconstruction
        if recon is None:
            return False
        if recon.get("kind") == "paragraph":
            return len(recon.get("anchors", [])) == 0
        return False

    return block_type == "paragraph" and not _contains_preserved_anchor_markup(
        mapping.xhtml_text
    )


def _can_replace_table_fragment(
    change: BlockChange,
    mapping: Optional[BlockMapping],
    roundtrip_sidecar: Optional[RoundtripSidecar],
) -> bool:
    """table 계열을 whole-fragment replacement로 처리할 수 있는지 판별한다."""
    if roundtrip_sidecar is None or mapping is None:
        return False
    if _contains_preserved_anchor_markup(mapping.xhtml_text):
        return False
    block = change.new_block or change.old_block
    return (
        (block.type == "html_block" and block.content.lstrip().startswith("<table"))
        or is_markdown_table(change.old_block.content)
    )


def _emit_replacement_fragment(block: MdxBlock) -> str:
    """Block content를 현재 forward emitter 기준 fragment로 변환한다."""
    parsed_blocks = [parsed for parsed in parse_mdx(block.content) if parsed.type != "empty"]
    if len(parsed_blocks) == 1:
        return emit_block(parsed_blocks[0])
    return mdx_block_to_xhtml_element(block)


def _build_replace_fragment_patch(
    mapping: BlockMapping,
    new_block: MdxBlock,
    sidecar_block: Optional[SidecarBlock] = None,
    mapping_lost_info: Optional[dict] = None,
) -> Dict[str, str]:
    """whole-fragment replacement patch를 생성한다."""
    new_element = _emit_replacement_fragment(new_block)
    if sidecar_block_requires_reconstruction(sidecar_block):
        new_element = reconstruct_fragment_with_sidecar(new_element, sidecar_block)
    block_lost = (mapping_lost_info or {}).get(mapping.block_id, {})
    if block_lost:
        new_element = apply_lost_info(new_element, block_lost)
    return {
        "action": "replace_fragment",
        "xhtml_xpath": mapping.xhtml_xpath,
        "new_element_xhtml": new_element,
    }


def _find_roundtrip_sidecar_block(
    change: BlockChange,
    mapping: Optional[BlockMapping],
    roundtrip_sidecar: Optional[RoundtripSidecar],
    xpath_to_sidecar_block: Dict[str, SidecarBlock],
) -> Optional[SidecarBlock]:
    """xpath → identity hash 순으로 roundtrip sidecar block을 탐색한다.

    1. xpath로 빠른 조회
    2. mdx_content_hash + mdx_line_range로 검증 → 일치하면 확정 반환
    3. 검증 실패 시 find_sidecar_block_by_identity로 더 정확한 블록 탐색
    4. identity도 없으면 xpath 결과를 fallback으로 반환
    """
    if roundtrip_sidecar is None:
        return None

    identity_block = change.old_block or change.new_block

    # xpath 조회
    xpath_match: Optional[SidecarBlock] = None
    if mapping is not None:
        xpath_match = xpath_to_sidecar_block.get(mapping.xhtml_xpath)

    # hash + line range 검증 → 확정 일치
    if xpath_match is not None and identity_block is not None:
        expected_hash = sha256_text(identity_block.content) if identity_block.content else ""
        expected_range = (identity_block.line_start, identity_block.line_end)
        if (
            xpath_match.mdx_content_hash == expected_hash
            and tuple(xpath_match.mdx_line_range) == expected_range
        ):
            return xpath_match

    # identity fallback: mapping.yaml이 어긋난 경우 hash 기반으로 재탐색
    # block family(paragraph/list/table 등)가 일치하는 경우에만 반환하여 cross-type 오매칭 방지
    if identity_block is not None and identity_block.content:
        identity_match = find_sidecar_block_by_identity(
            roundtrip_sidecar.blocks,
            sha256_text(identity_block.content),
            (identity_block.line_start, identity_block.line_end),
        )
        if identity_match is not None:
            if mapping is None or _mapping_block_family(mapping) == _xpath_block_family(identity_match.xhtml_xpath):
                return identity_match

    # xpath 결과를 마지막 fallback으로 반환 (hash 불일치라도 없는 것보다 나음)
    return xpath_match


def _xpath_root_tag(xpath: str) -> str:
    """Extract the top-level tag portion from an xpath-like storage path."""
    head = xpath.split("/", 1)[0]
    return head.split("[", 1)[0]


def _xpath_block_family(xpath: str) -> str:
    root_tag = _xpath_root_tag(xpath)
    if root_tag == "p":
        return "paragraph"
    if root_tag in {"ul", "ol"}:
        return "list"
    if root_tag == "table":
        return "table"
    if root_tag.startswith("h") and root_tag[1:].isdigit():
        return "heading"
    return root_tag


def _mapping_block_family(mapping: BlockMapping) -> str:
    if mapping.type in {"paragraph", "list", "heading", "table"}:
        return mapping.type
    return _xpath_block_family(mapping.xhtml_xpath)


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

    if mapping is None:
        if change.old_block.type == 'list':
            return ('list', None)
        if is_markdown_table(change.old_block.content):
            return ('table', None)
        return ('skip', None)

    # callout 블록은 항상 containing 전략 사용
    # (_convert_callout_inner가 <li><p> 구조를 생성할 수 없으므로)
    if change.old_block.type == 'callout':
        return ('containing', mapping)

    # Parent mapping이 children을 가지면 containing 전략으로 위임
    if mapping.children:
        if change.old_block.type == 'list':
            return ('list', mapping)
        return ('containing', mapping)

    # list 블록은 list 전략 사용 (direct 교체 시 <ac:image> 등 Confluence 태그 손실 방지)
    if change.old_block.type == 'list':
        return ('list', mapping)

    # table 블록은 table 전략 사용 (direct 교체 시 <ac:link> 등 Confluence 태그 손실 방지)
    if is_markdown_table(change.old_block.content):
        return ('table', mapping)

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
    roundtrip_sidecar: Optional[RoundtripSidecar] = None,
) -> List[Dict[str, str]]:
    """diff 변경과 매핑을 결합하여 XHTML 패치 목록을 구성한다.

    sidecar 인덱스를 사용하여 O(1) 직접 조회를 수행한다.
    """
    patches = []
    xpath_to_sidecar_block: Dict[str, SidecarBlock] = {}
    if roundtrip_sidecar is not None:
        xpath_to_sidecar_block = {
            block.xhtml_xpath: block for block in roundtrip_sidecar.blocks
        }
    used_ids: set = set()  # 이미 매칭된 mapping block_id (중복 매칭 방지)
    # child → parent 역참조 맵 (부모-자식 간 중복 매칭 방지)
    child_to_parent: dict = {}
    for m in mappings:
        for child_id in m.children:
            child_to_parent[child_id] = m.block_id

    # block_id → BlockMapping 인덱스 (child 해석용)
    id_to_mapping: Dict[str, BlockMapping] = {m.block_id: m for m in mappings}

    # 블록 레벨 lost_info 분배
    mapping_lost_info = distribute_lost_info_to_mappings(
        mappings, page_lost_info or {})

    def _mark_used(block_id: str, m: BlockMapping):
        """매핑 사용 시 부모/자식도 함께 사용 완료로 표시."""
        used_ids.add(block_id)
        for child_id in m.children:
            used_ids.add(child_id)
        parent_id = child_to_parent.get(block_id)
        if parent_id:
            used_ids.add(parent_id)

    # delete + add 쌍 탐지: 같은 인덱스에서 삭제 후 추가된 블록은
    # 구조 변경 없이 텍스트 전이로 처리 (callout 등 복합 블록의 DOM 파괴 방지)
    _delete_by_idx: dict = {}
    _add_by_idx: dict = {}
    for change in changes:
        if change.change_type == 'deleted':
            _delete_by_idx[change.index] = change
        elif change.change_type == 'added':
            _add_by_idx[change.index] = change
    _paired_indices: set = set()
    for idx, del_change in _delete_by_idx.items():
        if idx not in _add_by_idx:
            continue
        add_change = _add_by_idx[idx]
        if del_change.old_block.type in NON_CONTENT_TYPES:
            continue
        mapping = find_mapping_by_sidecar(
            idx, mdx_to_sidecar, xpath_to_mapping)
        if mapping is None:
            continue
        sidecar_block = xpath_to_sidecar_block.get(mapping.xhtml_xpath)
        if _is_clean_block(
            add_change.new_block.type,
            mapping,
            sidecar_block,
        ) or _can_replace_table_fragment(del_change, mapping, roundtrip_sidecar):
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    add_change.new_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
            _paired_indices.add(idx)
            _mark_used(mapping.block_id, mapping)
            continue
        old_plain = normalize_mdx_to_plain(
            del_change.old_block.content, del_change.old_block.type)
        new_plain = normalize_mdx_to_plain(
            add_change.new_block.content, add_change.new_block.type)
        xhtml_text = transfer_text_changes(
            old_plain, new_plain, mapping.xhtml_plain_text)
        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': mapping.xhtml_plain_text,
            'new_plain_text': xhtml_text,
        })
        _paired_indices.add(idx)
        _mark_used(mapping.block_id, mapping)

    # 상위 블록에 대한 그룹화된 변경
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    for change in changes:
        if change.index in _paired_indices:
            continue
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
            mdx_to_sidecar, xpath_to_mapping)

        if strategy == 'skip':
            continue

        if strategy == 'list':
            list_sidecar = _find_roundtrip_sidecar_block(
                change, mapping, roundtrip_sidecar, xpath_to_sidecar_block,
            )
            if (mapping is not None
                    and not _contains_preserved_anchor_markup(mapping.xhtml_text)
                    and sidecar_block_requires_reconstruction(list_sidecar)):
                _mark_used(mapping.block_id, mapping)
                patches.append(
                    _build_replace_fragment_patch(
                        mapping,
                        change.new_block,
                        sidecar_block=list_sidecar,
                        mapping_lost_info=mapping_lost_info,
                    )
                )
                continue
            patches.extend(
                build_list_item_patches(
                    change, mappings, used_ids,
                    mdx_to_sidecar, xpath_to_mapping, id_to_mapping,
                    mapping_lost_info=mapping_lost_info))
            continue

        if strategy == 'table':
            if _can_replace_table_fragment(change, mapping, roundtrip_sidecar):
                _mark_used(mapping.block_id, mapping)
                patches.append(
                    _build_replace_fragment_patch(
                        mapping,
                        change.new_block,
                        mapping_lost_info=mapping_lost_info,
                    )
                )
            else:
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

        # 멱등성 체크: push 후 XHTML이 이미 업데이트된 경우 건너뜀
        # (old != xhtml 이고 new == xhtml → 이미 적용된 변경)
        if (collapse_ws(old_plain) != collapse_ws(mapping.xhtml_plain_text)
                and collapse_ws(new_plain) == collapse_ws(mapping.xhtml_plain_text)):
            continue

        sidecar_block = _find_roundtrip_sidecar_block(
            change, mapping, roundtrip_sidecar, xpath_to_sidecar_block,
        )
        if _can_replace_table_fragment(change, mapping, roundtrip_sidecar):
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    change.new_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
            continue

        if _is_clean_block(change.old_block.type, mapping, sidecar_block):
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    change.new_block,
                    sidecar_block=sidecar_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
            continue

        if sidecar_block_requires_reconstruction(sidecar_block):
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    change.new_block,
                    sidecar_block=sidecar_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
            continue

        # 재생성 시 소실되는 XHTML 요소 포함 시 텍스트 전이로 폴백
        if ('<ac:link' in mapping.xhtml_text
                or '<ri:attachment' in mapping.xhtml_text):
            xhtml_text = transfer_text_changes(
                old_plain, new_plain, mapping.xhtml_plain_text)
            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': mapping.xhtml_plain_text,
                'new_plain_text': xhtml_text,
            })
            continue

        # inner XHTML 재생성 + 블록 레벨 lost_info 적용
        new_inner = mdx_block_to_inner_xhtml(
            change.new_block.content, change.new_block.type)
        block_lost = mapping_lost_info.get(mapping.block_id, {})
        if block_lost:
            new_inner = apply_lost_info(new_inner, block_lost)

        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': mapping.xhtml_plain_text,
            'new_inner_xhtml': new_inner,
        })

    # 상위 블록에 대한 그룹화된 변경 적용
    patches.extend(_flush_containing_changes(containing_changes, used_ids))
    return patches


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
