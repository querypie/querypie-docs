"""typed reverse-sync PatchPlan과 capability/provenance boundary 테스트."""

import json

import pytest

from mdx_to_storage.parser import Block
from reverse_sync.block_diff import BlockChange
from reverse_sync.capabilities import (
    CAPABILITY_REGISTRY,
    SupportLevel,
)
from reverse_sync.models import ReasonCode, sha256_text
from reverse_sync.mapping_recorder import record_mapping
from reverse_sync.operations import (
    ChangeIntent,
    PatchOperation,
    PatchPlan,
    TargetIdentity,
)
from reverse_sync.planner import plan_patches
from reverse_sync.preserving_patcher import (
    PatchApplicationError,
    render_patch_plan_preserving,
)
from reverse_sync.sidecar import (
    DocumentEnvelope,
    RoundtripSidecar,
    SidecarBlock,
    SidecarEntry,
)


def _block(content: str, block_type: str = "paragraph") -> Block:
    return Block(
        type=block_type,
        content=content,
        line_start=1,
        line_end=content.count("\n") + 1,
    )


def _sidecar(xhtml: str, original: Block) -> RoundtripSidecar:
    return RoundtripSidecar(
        page_id="123",
        mdx_sha256=sha256_text(original.content),
        source_xhtml_sha256=sha256_text(xhtml),
        blocks=[
            SidecarBlock(
                block_index=0,
                xhtml_xpath="p[1]" if original.type == "paragraph" else "table[1]",
                xhtml_fragment=xhtml,
                mdx_content_hash=sha256_text(original.content),
                mdx_line_range=(original.line_start, original.line_end),
            )
        ],
        separators=[],
        document_envelope=DocumentEnvelope(),
    )


def test_supported_paragraph_plan_has_capability_and_exact_target_identity():
    old = _block("Before")
    new = _block("After")
    change = BlockChange(0, "modified", old, new)
    xhtml = "<p>Before</p>"

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=_sidecar(xhtml, old),
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is True
    assert plan.issues == ()
    assert len(plan.operations) == 1
    operation = plan.operations[0]
    assert operation.capability_id == "paragraph_visible_edit"
    assert operation.intent_ordinals == (0,)
    assert operation.target.kind == "exact_fragment"
    assert operation.target.xpath == "p[1]"
    assert operation.target.base_fragment_sha256 == sha256_text(xhtml)
    assert "target_identity" in operation.required_proof
    assert plan.to_patch_dicts()[0]["new_inner_xhtml"] == "After"


def test_mdx_owned_link_uses_text_block_capability_not_preserved_anchor():
    old = _block("Before [Link](target)")
    new = _block("After [Link](target)")
    change = BlockChange(0, "modified", old, new)
    xhtml = (
        '<p>Before <ac:link><ri:page ri:content-title="Target"/>'
        '<ac:link-body>Link</ac:link-body></ac:link></p>'
    )
    sidecar = _sidecar(xhtml, old)
    sidecar.blocks[0].reconstruction = {
        "kind": "paragraph",
        "old_plain_text": "Before Link",
        "anchors": [],
    }

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=sidecar,
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is True
    assert plan.issues == ()
    assert plan.operations[0].capability_id == "paragraph_visible_edit"


def test_raw_html_table_is_explicit_unsupported_capability_in_push_plan():
    old = _block(
        "<table><tr><td>Before</td></tr></table>",
        "html_block",
    )
    new = _block(
        "<table><tr><td>After</td></tr></table>",
        "html_block",
    )
    change = BlockChange(0, "modified", old, new)
    xhtml = "<table><tr><td>Before</td></tr></table>"

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=_sidecar(xhtml, old),
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is False
    assert plan.to_patch_dicts() == []
    assert plan.operations[0].capability_id == "raw_html_table_edit"
    assert plan.operations[0].executable is False
    assert plan.operations[0].reason_code == "unsupported_capability"
    assert plan.issues[0].capability_id == "raw_html_table_edit"
    assert plan.issues[0].reason_code == "unsupported_capability"
    assert plan.issues[0].intent_ordinal == 0
    assert json.loads(plan.to_canonical_json())["issues"][0]["reason_code"] == (
        "unsupported_capability"
    )
    assert plan.to_legacy_skipped_changes()[0]["reason"] == (
        "unsupported_capability"
    )


def test_replacing_paragraph_with_raw_html_table_is_blocked():
    old = _block("Before")
    new = _block(
        "<table><tr><td>After</td></tr></table>",
        "html_block",
    )
    change = BlockChange(0, "modified", old, new)
    xhtml = "<p>Before</p>"

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=_sidecar(xhtml, old),
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is False
    assert len(plan.operations) == 1
    assert plan.operations[0].executable is False
    assert plan.operations[0].capability_id == "raw_html_table_edit"
    assert plan.operations[0].reason_code == "unsupported_capability"
    assert plan.issues[0].capability_id == "raw_html_table_edit"


def test_legacy_table_skip_is_one_typed_capability_issue():
    old = _block(
        "<table><tr><td>Before</td></tr></table>",
        "html_block",
    )
    new = _block(
        "<table><tr><td>After</td><td>Added</td></tr></table>",
        "html_block",
    )
    change = BlockChange(0, "modified", old, new)
    xhtml = "<table><tr><td>Before</td></tr></table>"

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=_sidecar(xhtml, old),
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.operations == ()
    assert len(plan.issues) == 1
    issue = plan.issues[0]
    assert issue.reason_code == "unsupported_capability"
    assert issue.capability_id == "raw_html_table_edit"
    assert issue.intent_ordinal == 0
    assert issue.to_legacy_dict()["reason"] == "unsupported_capability"


def test_unknown_preservation_unit_is_blocked_before_text_block_fallback():
    old = _block("Before")
    new = _block("After")
    change = BlockChange(0, "modified", old, new)
    xhtml = (
        '<p><ac:structured-macro ac:name="unknown">'
        '<ac:parameter ac:name="value">Before</ac:parameter>'
        '</ac:structured-macro></p>'
    )

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=_sidecar(xhtml, old),
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.operations == ()
    assert len(plan.issues) == 1
    assert plan.issues[0].reason_code == "unsupported_capability"
    assert plan.issues[0].capability_id == "unknown_macro_mutation"
    assert plan.issues[0].intent_ordinal == 0


def test_mixed_supported_and_unknown_preservation_units_are_blocked():
    old = _block("Before Link")
    new = _block("After Link")
    change = BlockChange(0, "modified", old, new)
    xhtml = (
        '<p><ac:structured-macro ac:name="unknown">'
        "<ac:rich-text-body>"
        '<ac:link><ri:page ri:content-title="Target"></ri:page>'
        "<ac:link-body>Before Link</ac:link-body></ac:link>"
        "</ac:rich-text-body>"
        "</ac:structured-macro></p>"
    )

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=_sidecar(xhtml, old),
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.operations == ()
    assert len(plan.issues) == 1
    assert plan.issues[0].reason_code == "unsupported_capability"
    assert plan.issues[0].capability_id == "unknown_macro_mutation"
    assert plan.issues[0].intent_ordinal == 0


def test_push_plan_blocks_operation_without_sidecar_provenance():
    old = _block("Before")
    new = _block("After")
    change = BlockChange(0, "modified", old, new)

    mappings = record_mapping("<p>Before</p>")
    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        mappings=mappings,
        mdx_to_sidecar={
            0: SidecarEntry(
                xhtml_xpath="p[1]",
                xhtml_type="paragraph",
                mdx_blocks=[0],
            )
        },
        xpath_to_mapping={"p[1]": mappings[0]},
        roundtrip_sidecar=None,
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is False
    assert plan.operations == ()
    assert len(plan.issues) == 1
    assert plan.issues[0].reason_code == "missing_identity"
    assert plan.issues[0].intent_ordinal == 0


def test_hash_mismatched_sidecar_target_is_not_executable():
    old = _block("Before")
    new = _block("After")
    change = BlockChange(0, "modified", old, new)
    xhtml = "<p>Before</p>"
    sidecar = _sidecar(xhtml, old)
    sidecar.blocks[0].mdx_content_hash = sha256_text("Different source")

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=sidecar,
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is False
    assert plan.to_patch_dicts() == []
    assert plan.operations == ()
    assert len(plan.issues) == 1
    assert plan.issues[0].reason_code == "missing_identity"
    assert plan.issues[0].intent_ordinal == 0


def test_push_planner_resolves_exact_provenance_before_renderer_strategy():
    old = _block("Before")
    new = _block("After")
    change = BlockChange(0, "modified", old, new)
    xhtml = "<p>Wrong</p><p>Before</p>"
    sidecar = RoundtripSidecar(
        page_id="123",
        mdx_sha256=sha256_text(old.content),
        source_xhtml_sha256=sha256_text(xhtml),
        blocks=[
            SidecarBlock(
                block_index=1,
                xhtml_xpath="p[2]",
                xhtml_fragment="<p>Before</p>",
                mdx_content_hash=sha256_text(old.content),
                mdx_line_range=(old.line_start, old.line_end),
            ),
            SidecarBlock(
                block_index=0,
                xhtml_xpath="p[1]",
                xhtml_fragment="<p>Wrong</p>",
                mdx_content_hash=sha256_text("Wrong"),
                mdx_line_range=(old.line_start, old.line_end),
            ),
        ],
        separators=[],
        document_envelope=DocumentEnvelope(),
    )

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        # strict mode는 이 legacy caller mapping을 무시해야 합니다.
        mdx_to_sidecar={
            0: SidecarEntry(
                xhtml_xpath="p[1]",
                xhtml_type="paragraph",
                mdx_blocks=[0],
            )
        },
        roundtrip_sidecar=sidecar,
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is True
    assert plan.issues == ()
    assert len(plan.operations) == 1
    assert plan.operations[0].target.xpath == "p[2]"
    assert plan.operations[0].intent_ordinals == (0,)


def test_push_planner_blocks_duplicate_exact_provenance_as_ambiguous():
    old = _block("Repeated")
    new = _block("Changed")
    change = BlockChange(0, "modified", old, new)
    xhtml = "<p>Repeated</p><p>Repeated</p>"
    sidecar = RoundtripSidecar(
        page_id="123",
        mdx_sha256=sha256_text(old.content),
        source_xhtml_sha256=sha256_text(xhtml),
        blocks=[
            SidecarBlock(
                block_index=index,
                xhtml_xpath=f"p[{index + 1}]",
                xhtml_fragment="<p>Repeated</p>",
                mdx_content_hash=sha256_text(old.content),
                mdx_line_range=(old.line_start, old.line_end),
            )
            for index in range(2)
        ],
        separators=[],
        document_envelope=DocumentEnvelope(),
    )

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=sidecar,
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is False
    assert plan.operations == ()
    assert len(plan.issues) == 1
    assert plan.issues[0].reason_code == "ambiguous_target"
    assert plan.issues[0].intent_ordinal == 0


def test_enforce_provenance_disables_legacy_list_text_fallback():
    old = _block("1. Before\n", "list")
    new = _block("1. After\n", "list")
    change = BlockChange(0, "modified", old, new)
    xhtml = "<ul><li><p>Before</p></li></ul>"
    sidecar = _sidecar(xhtml, old)
    sidecar.blocks[0].mdx_content_hash = sha256_text("Different source")

    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=sidecar,
        # allow_text_identity_fallback의 default가 True여도 strict flag가 우선합니다.
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is False
    assert plan.operations == ()
    assert len(plan.issues) == 1
    assert plan.issues[0].reason_code == "missing_identity"


def test_empty_source_line_insert_is_removed_before_typed_renderer_boundary():
    original = _block("Before")
    empty = _block("\n", "empty")
    added = Block(
        type="paragraph",
        content="Added\n",
        line_start=3,
        line_end=3,
    )
    changes = [
        BlockChange(1, "added", None, empty),
        BlockChange(2, "added", None, added),
    ]
    xhtml = "<p>Before</p>"

    plan, _ = plan_patches(
        changes,
        [original],
        [original, empty, added],
        page_xhtml=xhtml,
        alignment={0: 0},
        roundtrip_sidecar=_sidecar(xhtml, original),
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is True
    assert len(plan.operations) == 1
    assert plan.operations[0].intent_ordinals == (1,)
    assert plan.to_patch_dicts()[0]["new_element_xhtml"] == "<p>Added</p>"


def test_insert_skips_added_intent_already_covered_by_replacement():
    original = _block("Before")
    replacement = _block("First")
    inserted = Block(
        type="paragraph",
        content="Second",
        line_start=3,
        line_end=3,
    )
    changes = [
        BlockChange(0, "deleted", original, None),
        BlockChange(0, "added", None, replacement),
        BlockChange(1, "added", None, inserted),
    ]
    xhtml = "<p>Before</p>"

    plan, _ = plan_patches(
        changes,
        [original],
        [replacement, inserted],
        page_xhtml=xhtml,
        alignment={0: 0},
        roundtrip_sidecar=_sidecar(xhtml, original),
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is True
    assert len(plan.operations) == 2
    assert plan.operations[0].intent_ordinals == (0, 1)
    assert plan.operations[1].intent_ordinals == (2,)
    assert plan.to_patch_dicts()[1]["new_element_xhtml"] == "<p>Second</p>"


def test_strict_insert_blocks_when_predecessor_provenance_is_missing():
    original = _block("Before")
    inserted = Block(
        type="paragraph",
        content="Added",
        line_start=3,
        line_end=3,
    )
    xhtml = "<p>Before</p>"
    sidecar = _sidecar(xhtml, original)
    sidecar.blocks[0].mdx_content_hash = sha256_text("Different source")

    plan, _ = plan_patches(
        [BlockChange(1, "added", None, inserted)],
        [original],
        [original, inserted],
        page_xhtml=xhtml,
        alignment={0: 0},
        roundtrip_sidecar=sidecar,
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert plan.intent_complete is False
    assert plan.operations == ()
    assert len(plan.issues) == 1
    assert plan.issues[0].reason_code == "missing_identity"
    assert plan.issues[0].intent_ordinal == 0


def test_plan_serialization_is_deterministic_and_contains_no_untyped_top_level_patch():
    old = _block("Before")
    new = _block("After")
    change = BlockChange(0, "modified", old, new)
    xhtml = "<p>Before</p>"
    kwargs = dict(
        changes=[change],
        original_blocks=[old],
        improved_blocks=[new],
        page_xhtml=xhtml,
        roundtrip_sidecar=_sidecar(xhtml, old),
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    first, _ = plan_patches(**kwargs)
    second, _ = plan_patches(**kwargs)
    value = json.loads(first.to_canonical_json())

    assert first.to_canonical_json() == second.to_canonical_json()
    assert value["schema_version"] == 2
    assert value["adapter"] == "legacy-patch-builder-v2"
    assert "patches" not in value
    assert value["operations"][0]["capability_id"] == "paragraph_visible_edit"
    assert value["operations"][0]["reason_code"] == ""


def test_typed_renderer_revalidates_base_fragment_hash():
    old = _block("Before")
    new = _block("After")
    change = BlockChange(0, "modified", old, new)
    xhtml = "<p>Before</p>"
    sidecar = _sidecar(xhtml, old)
    plan, _ = plan_patches(
        [change],
        [old],
        [new],
        page_xhtml=xhtml,
        roundtrip_sidecar=sidecar,
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )

    assert render_patch_plan_preserving(xhtml, plan, sidecar) == "<p>After</p>"

    target = TargetIdentity(
        kind="exact_fragment",
        xpath="p[1]",
        root_xpath="p[1]",
        base_fragment_sha256="0" * 64,
        mdx_content_sha256=plan.operations[0].target.mdx_content_sha256,
        mdx_line_range=plan.operations[0].target.mdx_line_range,
    )
    tampered_operation = PatchOperation.from_legacy_patch(
        operation_id="op-0001",
        patch=plan.operations[0].to_patch_dict(),
        capability_id=plan.operations[0].capability_id,
        target=target,
        required_proof=plan.operations[0].required_proof,
        intent_ordinals=plan.operations[0].intent_ordinals,
        executable=True,
    )
    tampered_plan = PatchPlan(
        intents=plan.intents,
        operations=(tampered_operation,),
        issues=(),
    )

    with pytest.raises(PatchApplicationError, match="target hash"):
        render_patch_plan_preserving(xhtml, tampered_plan, sidecar)


def test_patch_operation_rejects_renderer_target_mismatch():
    target = TargetIdentity(
        kind="exact_fragment",
        xpath="p[1]",
        root_xpath="p[1]",
        base_fragment_sha256="a" * 64,
    )

    try:
        PatchOperation.from_legacy_patch(
            operation_id="op-0001",
            patch={
                "xhtml_xpath": "p[2]",
                "old_plain_text": "Before",
                "new_plain_text": "After",
            },
            capability_id="paragraph_visible_edit",
            target=target,
            required_proof=("target_identity",),
            intent_ordinals=(0,),
            executable=True,
        )
    except ValueError as exc:
        assert "target" in str(exc)
    else:
        raise AssertionError("target mismatch가 거부되지 않았습니다")


def test_patch_plan_requires_exactly_one_operation_per_intent():
    target = TargetIdentity(
        kind="exact_fragment",
        xpath="p[1]",
        root_xpath="p[1]",
        base_fragment_sha256="a" * 64,
    )
    patch = {
        "xhtml_xpath": "p[1]",
        "old_plain_text": "Before",
        "new_plain_text": "After",
    }
    operation = PatchOperation.from_legacy_patch(
        operation_id="op-0001",
        patch=patch,
        capability_id="paragraph_visible_edit",
        target=target,
        required_proof=("target_identity",),
        intent_ordinals=(0,),
        executable=True,
    )
    duplicate = PatchOperation.from_legacy_patch(
        operation_id="op-0002",
        patch=patch,
        capability_id="paragraph_visible_edit",
        target=target,
        required_proof=("target_identity",),
        intent_ordinals=(0,),
        executable=True,
    )
    intent = ChangeIntent(
        ordinal=0,
        index=0,
        change_type="modified",
        block_type="paragraph",
        old_sha256="b" * 64,
        new_sha256="c" * 64,
        provenance_xpath="p[1]",
    )

    assert PatchPlan((intent,), (operation,), ()).intent_complete is True
    assert PatchPlan((intent,), (operation, duplicate), ()).intent_complete is False


def test_every_registry_entry_declares_owner_proof_and_block_reason():
    assert CAPABILITY_REGISTRY
    for capability in CAPABILITY_REGISTRY.values():
        assert capability.renderer_owner
        assert capability.required_proof
        if capability.support_level is SupportLevel.BLOCKED:
            assert capability.block_reason == "unsupported_capability"
    assert ReasonCode.MISSING_IDENTITY.value == "missing_identity"
    assert ReasonCode.UNSUPPORTED_CAPABILITY.value == "unsupported_capability"
