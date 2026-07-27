"""Container renderer strategy."""

from typing import Any, Dict

from mdx_to_storage.parser import Block as MdxBlock
from reverse_sync.reconstructors import sidecar_block_requires_reconstruction
from reverse_sync.strategies.contracts import StrategyRenderContext


def render_container(context: StrategyRenderContext) -> None:
    """container 본문 변경과 child list 변경을 보존적으로 렌더링합니다."""
    mapping = context.mapping
    primitives = context.primitives
    block_id = mapping.block_id
    first_visit = block_id not in context.used_ids
    context.mark_used()

    if sidecar_block_requires_reconstruction(context.sidecar_block):
        if first_visit:
            context.append_replace_fragment(sidecar_block=context.sidecar_block)
    else:
        if block_id not in context.text_change_patches:
            patch_entry: Dict[str, Any] = {
                "xhtml_xpath": mapping.xhtml_xpath,
                "old_plain_text": mapping.xhtml_plain_text,
                "new_plain_text": mapping.xhtml_plain_text,
            }
            context.patches.append(patch_entry)
            context.text_change_patches[block_id] = patch_entry

        patch_entry = context.text_change_patches[block_id]
        patch_entry["new_plain_text"] = primitives.apply_mdx_diff_to_xhtml(
            context.old_plain,
            context.new_plain,
            patch_entry["new_plain_text"],
        )
        inline_fixups = primitives.build_inline_fixups(
            context.old_block.content,
            context.new_block.content,
            block_type=context.old_block.type,
        )
        if inline_fixups:
            existing = patch_entry.get("inline_fixups", [])
            existing.extend(
                primitives.offset_inline_fixup_match_indexes(
                    existing,
                    inline_fixups,
                    parent_xpath=mapping.xhtml_xpath,
                    change_index=context.change.index,
                    improved_blocks=context.improved_blocks,
                    mdx_to_sidecar=context.mdx_to_sidecar,
                )
            )
            patch_entry["inline_fixups"] = existing

    if (
        context.old_block.type != "callout"
        or not hasattr(context.old_block, "children")
        or not hasattr(context.new_block, "children")
    ):
        return

    old_lists = [
        child for child in context.old_block.children if child.type == "list"
    ]
    new_lists = [
        child for child in context.new_block.children if child.type == "list"
    ]
    child_list_mappings = [
        context.id_to_mapping[child_id]
        for child_id in mapping.children
        if child_id in context.id_to_mapping
        and context.id_to_mapping[child_id].type == "list"
    ]
    for old_child, new_child, child_mapping in zip(
        old_lists,
        new_lists,
        child_list_mappings,
    ):
        if not primitives.detect_list_item_space_change(
            old_child.content,
            new_child.content,
        ):
            continue
        if primitives.contains_preserved_anchor_markup(child_mapping.xhtml_text):
            continue
        child_block = MdxBlock(
            type="list",
            content=new_child.content,
            line_start=0,
            line_end=0,
        )
        context.append_replace_fragment(
            mapping=child_mapping,
            block=child_block,
        )
