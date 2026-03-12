"""리스트 블록 패치 — MDX list 블록 변경을 XHTML에 패치한다."""
import re
from typing import Dict, List, Optional

from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.sidecar import SidecarEntry, find_mapping_by_sidecar
from reverse_sync.lost_info_patcher import apply_lost_info
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_inner_xhtml
from reverse_sync.text_transfer import transfer_text_changes
from text_utils import normalize_mdx_to_plain



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


def _get_ordered_list_start(content: str) -> Optional[int]:
    """MDX 리스트 콘텐츠에서 첫 번째 순서 번호를 반환한다."""
    for line in content.split('\n'):
        m = re.match(r'^\s*(\d+)\.\s+', line)
        if m:
            return int(m.group(1))
    return None


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
        fallback_patch: Dict[str, object] = {
            'xhtml_xpath': parent.xhtml_xpath,
            'old_plain_text': parent.xhtml_plain_text,
            'new_plain_text': xhtml_text,
        }
        old_start = _get_ordered_list_start(change.old_block.content)
        new_start = _get_ordered_list_start(change.new_block.content)
        if old_start is not None and new_start is not None and old_start != new_start:
            fallback_patch['ol_start'] = new_start
        return [fallback_patch]

    new_inner = mdx_block_to_inner_xhtml(
        change.new_block.content, change.new_block.type)

    if mapping_lost_info:
        block_lost = mapping_lost_info.get(parent.block_id, {})
        if block_lost:
            new_inner = apply_lost_info(new_inner, block_lost)

    patch: Dict[str, object] = {
        'xhtml_xpath': parent.xhtml_xpath,
        'old_plain_text': parent.xhtml_plain_text,
        'new_inner_xhtml': new_inner,
    }
    old_start = _get_ordered_list_start(change.old_block.content)
    new_start = _get_ordered_list_start(change.new_block.content)
    if old_start is not None and new_start is not None and old_start != new_start:
        patch['ol_start'] = new_start
    return [patch]


def build_list_item_patches(
    change: BlockChange,
    mappings: List[BlockMapping],
    used_ids: 'set | None' = None,
    mdx_to_sidecar: Optional[Dict[int, SidecarEntry]] = None,
    xpath_to_mapping: Optional[Dict[str, 'BlockMapping']] = None,
    id_to_mapping: Optional[Dict[str, BlockMapping]] = None,
    mapping_lost_info: Optional[Dict[str, dict]] = None,
) -> List[Dict[str, str]]:
    """리스트 블록 변경을 XHTML에 패치한다.

    sidecar에서 parent mapping을 찾아 전체 리스트 inner XHTML을 재생성한다.
    """
    old_items = split_list_items(change.old_block.content)
    new_items = split_list_items(change.new_block.content)

    # sidecar에서 parent mapping 획득
    parent_mapping = None
    if mdx_to_sidecar is not None and xpath_to_mapping is not None:
        parent_mapping = find_mapping_by_sidecar(
            change.index, mdx_to_sidecar, xpath_to_mapping)

    # 항목 수 불일치 또는 내용 변경 → 전체 리스트 재생성
    if len(old_items) != len(new_items):
        return _regenerate_list_from_parent(
            change, parent_mapping, used_ids, mapping_lost_info)

    for old_item, new_item in zip(old_items, new_items):
        if old_item != new_item:
            return _regenerate_list_from_parent(
                change, parent_mapping, used_ids, mapping_lost_info)

    return []
