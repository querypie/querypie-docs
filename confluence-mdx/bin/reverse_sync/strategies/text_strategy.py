"""Text block와 preserved anchor renderer strategy."""

from reverse_sync.lost_info_patcher import apply_lost_info
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_inner_xhtml
from reverse_sync.reconstructors import sidecar_block_requires_reconstruction
from reverse_sync.strategies.contracts import StrategyRenderContext
from text_utils import collapse_ws


def _already_applied(context: StrategyRenderContext, mapping_visible_text: str) -> bool:
    return (
        collapse_ws(context.old_plain) != collapse_ws(mapping_visible_text)
        and collapse_ws(context.new_plain) == collapse_ws(mapping_visible_text)
    )


def render_preserved_anchor(context: StrategyRenderContext) -> None:
    """알려진 preservation unit만 보존 template 또는 sidecar로 재구성합니다."""
    mapping = context.mapping
    mapping_visible_text = context.primitives.xhtml_visible_text(
        mapping,
        context.old_block.type,
    )
    context.mark_used()
    if _already_applied(context, mapping_visible_text):
        return

    if sidecar_block_requires_reconstruction(context.sidecar_block):
        context.append_replace_fragment(sidecar_block=context.sidecar_block)
        return

    if not context.primitives.contains_only_supported_preservation_units(
        mapping.xhtml_text
    ):
        context.skipped_changes.append(
            {
                "block_id": mapping.block_id,
                "reason": "unknown_preservation_unit",
                "description": (
                    f"블록 {mapping.block_id}: 지원 계약이 없는 Confluence "
                    f"preservation unit을 변경할 수 없어 건너뜁니다."
                ),
            }
        )
        return

    if "<ac:link" in mapping.xhtml_text or "<ri:attachment" in mapping.xhtml_text:
        context.patches.append(
            context.primitives.build_preserved_template_patch(
                mapping,
                context.new_plain,
                context.mapping_lost_info,
            )
        )
        return

    context.skipped_changes.append(
        {
            "block_id": mapping.block_id,
            "reason": "unknown_preservation_unit",
            "description": (
                f"블록 {mapping.block_id}: 지원 계약이 없는 Confluence "
                f"preservation unit을 변경할 수 없어 건너뜁니다."
            ),
        }
    )


def render_text_block(context: StrategyRenderContext) -> None:
    """일반 text block을 fragment 또는 inner XHTML patch로 렌더링합니다."""
    mapping = context.mapping
    mapping_visible_text = context.primitives.xhtml_visible_text(
        mapping,
        context.old_block.type,
    )
    context.mark_used()
    if _already_applied(context, mapping_visible_text):
        return

    if context.primitives.is_clean_block(
        context.old_block.type,
        mapping,
        context.sidecar_block,
    ):
        context.append_replace_fragment(sidecar_block=context.sidecar_block)
        return

    if sidecar_block_requires_reconstruction(context.sidecar_block):
        context.append_replace_fragment(sidecar_block=context.sidecar_block)
        return

    new_inner = mdx_block_to_inner_xhtml(
        context.new_block.content,
        context.new_block.type,
    )
    block_lost = context.mapping_lost_info.get(mapping.block_id, {})
    if block_lost:
        new_inner = apply_lost_info(new_inner, block_lost)

    context.patches.append(
        {
            "xhtml_xpath": mapping.xhtml_xpath,
            "old_plain_text": mapping_visible_text,
            "new_inner_xhtml": new_inner,
        }
    )
