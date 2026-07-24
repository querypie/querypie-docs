"""Table renderer strategy."""

from reverse_sync.strategies.contracts import StrategyRenderContext


def render_table(context: StrategyRenderContext) -> None:
    """table 변경을 source kind에 맞는 안전 경로로 렌더링합니다."""
    mapping = context.mapping
    primitives = context.primitives

    if context.decision.source_kind == "raw_html_table":
        if "<ac:link" in mapping.xhtml_text or "<ri:attachment" in mapping.xhtml_text:
            context.mark_used()
            context.patches.append(
                primitives.build_preserved_template_patch(
                    mapping,
                    context.new_plain,
                    context.mapping_lost_info,
                )
            )
            return

        old_cells = primitives.extract_html_table_cells(context.old_block.content)
        new_cells = primitives.extract_html_table_cells(context.new_block.content)
        if not primitives.is_safe_cell_text_edit(old_cells, new_cells):
            context.skipped_changes.append(
                {
                    "block_id": mapping.block_id,
                    "reason": "unsafe_html_table_edit",
                    "description": (
                        f"블록 {mapping.block_id}: raw HTML 테이블의 셀 구조 변경"
                        f"(셀 수 변경 또는 셀 내용 재배치)은 안전하지 않아 "
                        f"건너뜁니다."
                    ),
                }
            )
            return

        context.mark_used()
        mapping_visible_text = mapping.xhtml_plain_text
        context.patches.append(
            {
                "xhtml_xpath": mapping.xhtml_xpath,
                "old_plain_text": mapping_visible_text,
                "new_plain_text": primitives.apply_mdx_diff_to_xhtml(
                    context.old_plain,
                    context.new_plain,
                    mapping_visible_text,
                ),
            }
        )
        return

    table_skip = primitives.classify_table_fragment_skip(
        context.change,
        mapping,
        context.roundtrip_sidecar,
    )
    if table_skip is not None:
        context.skipped_changes.append(table_skip)
        return

    context.mark_used()
    context.append_replace_fragment()
