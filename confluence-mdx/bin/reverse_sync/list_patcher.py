"""리스트 블록 패치 — MDX list 블록 변경을 XHTML에 패치한다."""
import re
from typing import Dict, List, Optional

from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.sidecar import SidecarEntry, find_mapping_by_sidecar
from reverse_sync.lost_info_patcher import apply_lost_info
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_inner_xhtml
from reverse_sync.text_transfer import transfer_text_changes
from mdx_to_storage.inline import convert_inline
from text_utils import normalize_mdx_to_plain, collapse_ws, strip_list_marker, strip_for_compare


def _resolve_child_mapping(
    old_plain: str,
    parent_mapping: BlockMapping,
    id_to_mapping: Dict[str, BlockMapping],
) -> Optional[BlockMapping]:
    """Parent mapping의 children 중에서 old_plain과 일치하는 child를 찾는다."""
    old_norm = collapse_ws(old_plain)
    if not old_norm:
        return None

    # 1차: collapse_ws 완전 일치
    for child_id in parent_mapping.children:
        child = id_to_mapping.get(child_id)
        if child and collapse_ws(child.xhtml_plain_text) == old_norm:
            return child

    # 2차: 공백 무시 완전 일치
    old_nospace = re.sub(r'\s+', '', old_norm)
    for child_id in parent_mapping.children:
        child = id_to_mapping.get(child_id)
        if child:
            child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
            if child_nospace == old_nospace:
                return child

    # 3차: 리스트 마커 제거 후 비교 (XHTML child가 "- text" 형식인 경우)
    for child_id in parent_mapping.children:
        child = id_to_mapping.get(child_id)
        if child:
            child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
            child_unmarked = strip_list_marker(child_nospace)
            if child_unmarked != child_nospace and old_nospace == child_unmarked:
                return child

    # 4차: MDX 쪽 리스트 마커 제거 후 비교
    old_unmarked = strip_list_marker(old_nospace)
    if old_unmarked != old_nospace:
        for child_id in parent_mapping.children:
            child = id_to_mapping.get(child_id)
            if child:
                child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
                if old_unmarked == child_nospace:
                    return child

    # 5차: 앞부분 prefix 일치 (emoticon/lost_info 차이 허용)
    # XHTML에서 ac:emoticon이 텍스트로 치환되지 않는 경우,
    # 전체 문자열 비교가 실패할 수 있으므로 앞부분 20자로 비교한다.
    # 단, old_nospace가 child보다 2배 이상 긴 경우는 잘못된 매칭으로 판단한다
    # (callout 전체 텍스트가 내부 paragraph 첫 줄과 prefix를 공유하는 경우 방지).
    _PREFIX_LEN = 20
    if len(old_nospace) >= _PREFIX_LEN:
        old_prefix = old_nospace[:_PREFIX_LEN]
        for child_id in parent_mapping.children:
            child = id_to_mapping.get(child_id)
            if child:
                child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
                if (len(child_nospace) >= _PREFIX_LEN
                        and child_nospace[:_PREFIX_LEN] == old_prefix
                        and len(old_nospace) <= len(child_nospace) * 2):
                    return child

    return None


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


def _regenerate_list_from_parent(
    change: BlockChange,
    parent: Optional[BlockMapping],
    used_ids: 'set | None' = None,
    mapping_lost_info: Optional[Dict[str, dict]] = None,
) -> List[Dict[str, str]]:
    """parent mapping 기반으로 전체 리스트 inner XHTML을 재생성한다.

    parent XHTML에 <ac:image> 등 MDX로 표현 불가한 요소가 있으면
    텍스트 전이(transfer_text_changes)로 폴백하여 DOM 구조를 보존한다.
    """
    if parent is None:
        return []

    if used_ids is not None:
        used_ids.add(parent.block_id)
        for child_id in parent.children:
            used_ids.add(child_id)

    # 재생성 시 소실되는 XHTML 요소 포함 시 텍스트 전이로 폴백
    if '<ac:image' in parent.xhtml_text or '<span style=' in parent.xhtml_text:
        old_plain = normalize_mdx_to_plain(
            change.old_block.content, change.old_block.type)
        new_plain = normalize_mdx_to_plain(
            change.new_block.content, change.new_block.type)
        xhtml_text = transfer_text_changes(
            old_plain, new_plain, parent.xhtml_plain_text)
        return [{
            'xhtml_xpath': parent.xhtml_xpath,
            'old_plain_text': parent.xhtml_plain_text,
            'new_plain_text': xhtml_text,
        }]

    new_inner = mdx_block_to_inner_xhtml(
        change.new_block.content, change.new_block.type)

    if mapping_lost_info:
        block_lost = mapping_lost_info.get(parent.block_id, {})
        if block_lost:
            new_inner = apply_lost_info(new_inner, block_lost)

    return [{
        'xhtml_xpath': parent.xhtml_xpath,
        'old_plain_text': parent.xhtml_plain_text,
        'new_inner_xhtml': new_inner,
    }]


def build_list_item_patches(
    change: BlockChange,
    mappings: List[BlockMapping],
    used_ids: 'set | None' = None,
    mdx_to_sidecar: Optional[Dict[int, SidecarEntry]] = None,
    xpath_to_mapping: Optional[Dict[str, 'BlockMapping']] = None,
    id_to_mapping: Optional[Dict[str, BlockMapping]] = None,
    mapping_lost_info: Optional[Dict[str, dict]] = None,
) -> List[Dict[str, str]]:
    """리스트 블록의 각 항목을 개별 매핑과 대조하여 패치를 생성한다.

    R2: child 매칭 성공 시 항상 child inner XHTML 재생성,
    child 매칭 실패 시 전체 리스트 inner XHTML 재생성.
    """
    old_items = split_list_items(change.old_block.content)
    new_items = split_list_items(change.new_block.content)

    # sidecar에서 parent mapping 획득
    parent_mapping = None
    if mdx_to_sidecar is not None and xpath_to_mapping is not None:
        parent_mapping = find_mapping_by_sidecar(
            change.index, mdx_to_sidecar, xpath_to_mapping)

    # sidecar에 없으면 텍스트 포함 검색으로 parent 찾기
    if parent_mapping is None:
        from reverse_sync.patch_builder import _find_containing_mapping
        old_plain_all = normalize_mdx_to_plain(
            change.old_block.content, 'list')
        parent_mapping = _find_containing_mapping(
            old_plain_all, mappings, used_ids or set())

    # 항목 수 불일치 → 전체 리스트 재생성
    if len(old_items) != len(new_items):
        return _regenerate_list_from_parent(
            change, parent_mapping, used_ids, mapping_lost_info)

    patches = []
    for old_item, new_item in zip(old_items, new_items):
        if old_item == new_item:
            continue
        old_plain = normalize_mdx_to_plain(old_item, 'list')

        # parent mapping의 children에서 child 해석 시도
        mapping = None
        if parent_mapping is not None and parent_mapping.children and id_to_mapping is not None:
            mapping = _resolve_child_mapping(
                old_plain, parent_mapping, id_to_mapping)

        if mapping is None:
            # R2: child 매칭 실패 → 전체 리스트 재생성
            return _regenerate_list_from_parent(
                change, parent_mapping, used_ids, mapping_lost_info)

        # child 매칭 성공: child inner XHTML 재생성
        new_plain = normalize_mdx_to_plain(new_item, 'list')

        # 멱등성 체크: push 후 XHTML이 이미 업데이트된 경우 건너뜀
        if (collapse_ws(old_plain) != collapse_ws(mapping.xhtml_plain_text)
                and collapse_ws(new_plain) == collapse_ws(mapping.xhtml_plain_text)):
            continue

        if used_ids is not None:
            used_ids.add(mapping.block_id)

        # 재생성 시 소실되는 XHTML 요소 포함 시 텍스트 전이로 폴백
        if '<ac:image' in mapping.xhtml_text or '<span style=' in mapping.xhtml_text:
            xhtml_text = transfer_text_changes(
                old_plain, new_plain, mapping.xhtml_plain_text)
            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': mapping.xhtml_plain_text,
                'new_plain_text': xhtml_text,
            })
            continue

        new_item_text = re.sub(r'^[-*+]\s+', '', new_item.strip())
        new_item_text = re.sub(r'^\d+\.\s+', '', new_item_text)
        new_inner = convert_inline(new_item_text)

        # 블록 레벨 lost_info 적용
        if mapping_lost_info:
            block_lost = mapping_lost_info.get(mapping.block_id, {})
            if block_lost:
                new_inner = apply_lost_info(new_inner, block_lost)

        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': mapping.xhtml_plain_text,
            'new_inner_xhtml': new_inner,
        })

    return patches
