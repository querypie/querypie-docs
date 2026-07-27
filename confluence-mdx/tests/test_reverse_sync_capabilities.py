"""typed renderer strategy와 capability 분류 경계 테스트."""

import pytest

from reverse_sync.capabilities import (
    RendererStrategy,
    StrategyDecision,
    capability_for_legacy_skip,
    classify_capability,
)
from reverse_sync.mapping_recorder import record_mapping


def _mapping(xhtml: str):
    return record_mapping(xhtml)[0]


def test_text_block_strategy_classifies_mdx_owned_link_as_paragraph():
    mapping = _mapping(
        '<p>Before <ac:link><ri:page ri:content-title="Target"/>'
        '<ac:link-body>Link</ac:link-body></ac:link></p>'
    )

    capability = classify_capability(
        action="modify",
        strategy=StrategyDecision(RendererStrategy.TEXT_BLOCK, "paragraph"),
        mapping=mapping,
        block_type="paragraph",
    )

    assert capability.capability_id == "paragraph_visible_edit"


def test_preserved_anchor_strategy_classifies_supported_template_rewrite():
    mapping = _mapping(
        '<p><ac:link><ri:page ri:content-title="Target"/>'
        '<ac:link-body>Before</ac:link-body></ac:link></p>'
    )

    capability = classify_capability(
        action="modify",
        strategy=StrategyDecision(
            RendererStrategy.PRESERVED_ANCHOR,
            "paragraph",
        ),
        mapping=mapping,
        block_type="paragraph",
    )

    assert capability.capability_id == "preserved_anchor_template_rewrite"


def test_preserved_anchor_strategy_blocks_unknown_macro():
    mapping = _mapping(
        '<p><ac:structured-macro ac:name="unknown">'
        '<ac:parameter ac:name="value">Before</ac:parameter>'
        '</ac:structured-macro></p>'
    )

    capability = classify_capability(
        action="modify",
        strategy=StrategyDecision(
            RendererStrategy.PRESERVED_ANCHOR,
            "paragraph",
        ),
        mapping=mapping,
        block_type="paragraph",
    )

    assert capability.capability_id == "unknown_macro_mutation"
    assert capability.block_reason == "unsupported_capability"


def test_raw_html_table_source_is_blocked_independently_of_patch_shape():
    mapping = _mapping("<table><tbody><tr><td>Before</td></tr></tbody></table>")

    capability = classify_capability(
        action="modify",
        strategy=StrategyDecision(RendererStrategy.TABLE, "raw_html_table"),
        mapping=mapping,
        block_type="html_block",
    )

    assert capability.capability_id == "raw_html_table_edit"
    assert capability.block_reason == "unsupported_capability"


def test_markdown_table_with_preserved_unit_is_unknown_macro_capability():
    mapping = _mapping(
        '<table><tbody><tr><td><ac:structured-macro ac:name="status"/>'
        '</td></tr></tbody></table>'
    )

    capability = classify_capability(
        action="modify",
        strategy=StrategyDecision(RendererStrategy.TABLE, "table"),
        mapping=mapping,
        block_type="paragraph",
    )

    assert capability.capability_id == "unknown_macro_mutation"
    assert capability.block_reason == "unsupported_capability"


def test_list_with_preserved_attachment_uses_preserved_anchor_capability():
    mapping = _mapping(
        '<ul><li><p>Before <ac:image>'
        '<ri:attachment ri:filename="screen.png"/></ac:image></p></li></ul>'
    )

    capability = classify_capability(
        action="modify",
        strategy=StrategyDecision(RendererStrategy.LIST, "list"),
        mapping=mapping,
        block_type="list",
    )

    assert capability.capability_id == "preserved_anchor_template_rewrite"


@pytest.mark.parametrize(
    ("reason_code", "capability_id"),
    [
        ("unsafe_html_table_edit", "raw_html_table_edit"),
        ("preserved_anchor_table", "unknown_macro_mutation"),
        ("unknown_preservation_unit", "unknown_macro_mutation"),
    ],
)
def test_legacy_skip_reason_uses_canonical_capability_registry(
    reason_code,
    capability_id,
):
    capability = capability_for_legacy_skip(reason_code)

    assert capability is not None
    assert capability.capability_id == capability_id
