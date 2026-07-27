"""List renderer strategy."""

from __future__ import annotations

import re
from typing import Any, Dict

from reverse_sync.reconstructors import sidecar_block_requires_reconstruction
from reverse_sync.strategies.contracts import StrategyRenderContext
from reverse_sync.visible_segments import (
    extract_visible_model_from_mdx,
    extract_visible_model_from_xhtml,
)


def render_list(context: StrategyRenderContext) -> None:
    """list 변경을 fragment 재구성 또는 누적 text patch로 렌더링합니다."""
    mapping = context.mapping
    old_block = context.old_block
    new_block = context.new_block
    primitives = context.primitives
    list_sidecar = context.sidecar_block

    old_list_model = extract_visible_model_from_mdx(
        old_block.content,
        "list",
    )
    new_list_model = extract_visible_model_from_mdx(
        new_block.content,
        "list",
    )
    xhtml_list_model = extract_visible_model_from_xhtml(
        mapping.xhtml_text,
        "list",
    )
    has_content_change = (
        old_list_model.visible_text != new_list_model.visible_text
    )
    has_structure_change = (
        old_list_model.structural_fingerprint
        != new_list_model.structural_fingerprint
    )
    old_visible = old_list_model.visible_text
    new_visible = new_list_model.visible_text

    old_start = re.match(r"^\s*(\d+)\.", old_block.content)
    new_start = re.match(r"^\s*(\d+)\.", new_block.content)
    has_ol_start_change = bool(
        old_start
        and new_start
        and int(old_start.group(1)) != int(new_start.group(1))
    )
    inline_fixups = primitives.build_inline_fixups(
        old_block.content,
        new_block.content,
        block_type=old_block.type,
    )
    has_inline_boundary = bool(inline_fixups)
    has_patchable_text_change = (
        has_content_change or has_ol_start_change or has_inline_boundary
    )
    has_rebuild_change = has_patchable_text_change or has_structure_change
    requires_anchor_rebuild = sidecar_block_requires_reconstruction(
        list_sidecar,
    )
    has_preserved_anchor = primitives.contains_preserved_anchor_markup(
        mapping.xhtml_text
    )
    should_replace_clean_list = (
        not has_preserved_anchor
        and (context.roundtrip_sidecar is not None or has_rebuild_change)
        and (
            list_sidecar is None
            or context.mapping_via_v3_fallback
            or has_rebuild_change
        )
    )

    if has_preserved_anchor:
        merge_patch = primitives.build_list_item_merge_patch(
            mapping,
            old_block.content,
            new_block.content,
            old_visible,
            new_visible,
        )
        if merge_patch is not None:
            context.mark_used()
            context.patches.append(merge_patch)
            return

    if requires_anchor_rebuild or should_replace_clean_list:
        context.mark_used()
        context.append_replace_fragment(sidecar_block=list_sidecar)
        return

    if not has_patchable_text_change:
        return

    block_id = mapping.block_id
    if block_id not in context.text_change_patches:
        patch_entry: Dict[str, Any] = {
            "xhtml_xpath": mapping.xhtml_xpath,
            "old_plain_text": xhtml_list_model.visible_text,
            "new_plain_text": xhtml_list_model.visible_text,
        }
        context.patches.append(patch_entry)
        context.text_change_patches[block_id] = patch_entry

    patch_entry = context.text_change_patches[block_id]
    if has_content_change:
        patch_entry["new_plain_text"] = primitives.apply_mdx_diff_to_xhtml(
            old_visible,
            new_visible,
            patch_entry["new_plain_text"],
        )
    if has_ol_start_change and new_start is not None:
        patch_entry["ol_start"] = int(new_start.group(1))
    if has_inline_boundary:
        existing = patch_entry.get("inline_fixups", [])
        existing.extend(inline_fixups)
        patch_entry["inline_fixups"] = existing
    context.mark_used()
