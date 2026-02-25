"""리스트 블록 패치 — MDX list 블록 변경을 XHTML에 패치한다."""
import re
from typing import Dict, List, Optional

from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.sidecar import SidecarEntry, find_mapping_by_sidecar
from reverse_sync.inline_detector import has_inline_format_change, has_inline_boundary_change
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_inner_xhtml
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


def extract_list_marker_prefix(text: str) -> str:
    """텍스트에서 선행 리스트 마커 prefix를 추출한다."""
    m = re.match(r'^([-*+]\s+|\d+\.\s+)', text)
    return m.group(0) if m else ''


def build_list_item_patches(
    change: BlockChange,
    mappings: List[BlockMapping],
    used_ids: 'set | None' = None,
    mdx_to_sidecar: Optional[Dict[int, SidecarEntry]] = None,
    xpath_to_mapping: Optional[Dict[str, 'BlockMapping']] = None,
    id_to_mapping: Optional[Dict[str, BlockMapping]] = None,
) -> List[Dict[str, str]]:
    """리스트 블록의 각 항목을 개별 매핑과 대조하여 패치를 생성한다.

    sidecar에서 얻은 parent mapping의 children을 통해 child 매핑을 해석한다.
    """
    from reverse_sync.patch_builder import _find_containing_mapping, _flush_containing_changes
    from reverse_sync.text_transfer import transfer_text_changes

    old_items = split_list_items(change.old_block.content)
    new_items = split_list_items(change.new_block.content)
    if len(old_items) != len(new_items):
        # 항목 수가 다르면 (삭제/추가) 전체 리스트 inner XHTML 재생성
        parent = None
        if mdx_to_sidecar is not None and xpath_to_mapping is not None:
            parent = find_mapping_by_sidecar(
                change.index, mdx_to_sidecar, xpath_to_mapping)
        if parent is not None:
            new_inner = mdx_block_to_inner_xhtml(
                change.new_block.content, change.new_block.type)
            return [{
                'xhtml_xpath': parent.xhtml_xpath,
                'old_plain_text': parent.xhtml_plain_text,
                'new_inner_xhtml': new_inner,
            }]
        return []

    # sidecar에서 parent mapping 획득
    parent_mapping = None
    if mdx_to_sidecar is not None and xpath_to_mapping is not None:
        parent_mapping = find_mapping_by_sidecar(
            change.index, mdx_to_sidecar, xpath_to_mapping)

    patches = []
    # 매칭 실패한 항목을 상위 블록 기준으로 그룹화
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    # flat list에서 inline 포맷 변경이 감지되면 전체 리스트 inner XHTML 재생성
    _flat_inline_change = False
    for old_item, new_item in zip(old_items, new_items):
        if old_item == new_item:
            continue
        old_plain = normalize_mdx_to_plain(old_item, 'list')

        # parent mapping의 children에서 child 해석 시도
        mapping = None
        if parent_mapping is not None and parent_mapping.children and id_to_mapping is not None:
            mapping = _resolve_child_mapping(
                old_plain, parent_mapping, id_to_mapping)

        if mapping is not None:
            if used_ids is not None:
                used_ids.add(mapping.block_id)

            # inline 포맷 변경 감지 → new_inner_xhtml 패치
            if has_inline_format_change(old_item, new_item):
                new_item_text = re.sub(r'^[-*+]\s+', '', new_item.strip())
                new_item_text = re.sub(r'^\d+\.\s+', '', new_item_text)
                new_inner = convert_inline(new_item_text)
                patches.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'old_plain_text': mapping.xhtml_plain_text,
                    'new_inner_xhtml': new_inner,
                })
            else:
                new_plain = normalize_mdx_to_plain(new_item, 'list')

                xhtml_text = mapping.xhtml_plain_text
                prefix = extract_list_marker_prefix(xhtml_text)
                if prefix and collapse_ws(old_plain) != collapse_ws(xhtml_text):
                    xhtml_body = xhtml_text[len(prefix):]
                    # XHTML body가 이미 new_plain과 일치하면 건너뛰기
                    if collapse_ws(new_plain) == collapse_ws(xhtml_body):
                        continue
                    if collapse_ws(old_plain) != collapse_ws(xhtml_body):
                        new_plain = transfer_text_changes(
                            old_plain, new_plain, xhtml_body)
                    new_plain = prefix + new_plain
                elif collapse_ws(old_plain) != collapse_ws(xhtml_text):
                    # XHTML이 이미 new_plain과 일치하면 건너뛰기
                    if collapse_ws(new_plain) == collapse_ws(xhtml_text):
                        continue
                    new_plain = transfer_text_changes(
                        old_plain, new_plain, xhtml_text)

                patches.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'old_plain_text': mapping.xhtml_plain_text,
                    'new_plain_text': new_plain,
                })
        else:
            # child 매칭 실패: inline 마커 경계 이동 감지
            # has_inline_boundary_change: type 추가/제거 및 마커 간 텍스트 변경만 감지
            # (마커 내부 content만 변경된 경우는 무시하여 이미지 등 XHTML 고유 요소 보존)
            if has_inline_boundary_change(old_item, new_item):
                _flat_inline_change = True

            # parent 또는 텍스트 포함 매핑을 containing block으로 사용
            container = parent_mapping
            if container is not None and used_ids is not None:
                # parent 텍스트에 항목이 포함되지 않으면 더 나은 매핑 찾기
                _item_ns = strip_for_compare(old_plain)
                _cont_ns = strip_for_compare(container.xhtml_plain_text)
                if _item_ns and _cont_ns and _item_ns not in _cont_ns:
                    better = _find_containing_mapping(
                        old_plain, mappings, used_ids)
                    if better is not None:
                        container = better
            elif used_ids is not None:
                container = _find_containing_mapping(old_plain, mappings, used_ids)
            if container is not None:
                new_plain = normalize_mdx_to_plain(new_item, 'list')
                bid = container.block_id
                if bid not in containing_changes:
                    containing_changes[bid] = (container, [])
                containing_changes[bid][1].append((old_plain, new_plain))

    # flat list에서 inline 포맷 변경이 감지된 경우:
    # containing block 텍스트 패치 대신 전체 리스트 inner XHTML 재생성
    if _flat_inline_change and parent_mapping is not None:
        containing_changes.pop(parent_mapping.block_id, None)
        new_inner = mdx_block_to_inner_xhtml(
            change.new_block.content, change.new_block.type)
        patches.append({
            'xhtml_xpath': parent_mapping.xhtml_xpath,
            'old_plain_text': parent_mapping.xhtml_plain_text,
            'new_inner_xhtml': new_inner,
        })

    # 상위 블록에 대한 그룹화된 변경 적용
    patches.extend(_flush_containing_changes(containing_changes, used_ids))
    return patches
