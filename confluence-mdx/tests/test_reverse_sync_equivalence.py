"""typed push equivalence와 strict local proof 계약 테스트."""

from dataclasses import dataclass

from reverse_sync.dependencies import DependencyResult
from reverse_sync.equivalence import (
    PUSH_EQUIVALENCE_POLICY,
    canonicalize_mdx,
    verify_push_equivalence,
)
from reverse_sync.preserving_patcher import (
    PatchApplicationError,
    patch_xhtml_preserving,
)
from reverse_sync.proof import (
    REQUIRED_LOCAL_GATES,
    build_local_proof,
    canonical_plan_json,
    verify_storage_well_formed,
)
from reverse_sync.sidecar import build_sidecar


def test_typed_equivalence_allows_only_markdown_table_source_padding():
    expected = (
        "# Title\n\n"
        "| Name       | Value |\n"
        "| :--------- | ----: |\n"
        "| QueryPie   |  42   |\n"
    )
    actual = (
        "# Title\n\n"
        "| Name | Value |\n"
        "| :--- | ---: |\n"
        "| QueryPie | 42 |\n"
    )

    result = verify_push_equivalence(expected, actual)

    assert result.passed is True
    assert result.policy == PUSH_EQUIVALENCE_POLICY
    assert result.expected_sha256 == result.actual_sha256


def test_typed_equivalence_preserves_table_alignment_and_cell_content():
    expected = "| Name | Value |\n| :--- | ---: |\n| QueryPie | 42 |\n"
    changed_alignment = "| Name | Value |\n| --- | ---: |\n| QueryPie | 42 |\n"
    changed_content = "| Name | Value |\n| :--- | ---: |\n| QueryPie | 43 |\n"

    assert verify_push_equivalence(expected, changed_alignment).passed is False
    assert verify_push_equivalence(expected, changed_content).passed is False


def test_typed_equivalence_does_not_hide_visible_whitespace_or_title():
    assert verify_push_equivalence("Text  here\n", "Text here\n").passed is False
    assert verify_push_equivalence("# A\n\nText\n", "# B\n\nText\n").passed is False
    assert verify_push_equivalence("- item\n", "-  item\n").passed is False


def test_typed_equivalence_preserves_link_target_and_attachment_filename():
    expected = "[Guide](/guide) ![screen](./image.png)\n"
    changed_link = "[Guide](/other) ![screen](./image.png)\n"
    changed_attachment = "[Guide](/guide) ![screen](./other.png)\n"

    assert verify_push_equivalence(expected, changed_link).passed is False
    assert verify_push_equivalence(expected, changed_attachment).passed is False

    model = canonicalize_mdx(expected).to_dict()
    tokens = model["blocks"][0]["tokens"]
    assert tokens[0]["kind"] == "link"
    assert tokens[0]["target"] == "/guide"
    assert tokens[2]["attachment_filename"] == "image.png"


def test_preserving_patcher_keeps_untouched_entity_bytes():
    base = '<p>Before</p><p>&ldquo;untouched&rdquo;</p>'
    original_mdx = "# Title\n\nBefore\n\n“untouched”\n"
    sidecar = build_sidecar(base, original_mdx, page_id="123")
    patches = [
        {
            "xhtml_xpath": "p[1]",
            "old_plain_text": "Before",
            "new_plain_text": "After",
        }
    ]

    candidate = patch_xhtml_preserving(base, patches, sidecar)

    assert candidate == '<p>After</p><p>&ldquo;untouched&rdquo;</p>'


def test_preserving_patcher_fails_when_exact_target_is_missing():
    base = "<p>Before</p>"
    sidecar = build_sidecar(base, "# Title\n\nBefore\n", page_id="123")

    try:
        patch_xhtml_preserving(
            base,
            [{"xhtml_xpath": "p[2]", "old_plain_text": "Before", "new_plain_text": "After"}],
            sidecar,
        )
    except PatchApplicationError as exc:
        assert exc.reason_code == "missing_identity"
    else:
        raise AssertionError("missing target이 block되지 않았습니다")


def test_preserving_patcher_keeps_envelope_and_separators_across_insert_delete():
    base = " \n<p>First</p>\n<!-- gap -->\n<p>Second</p>\n "
    original_mdx = "# Title\n\nFirst\n\nSecond\n"
    sidecar = build_sidecar(base, original_mdx, page_id="123")
    patches = [
        {"action": "delete", "xhtml_xpath": "p[1]"},
        {
            "action": "insert",
            "after_xpath": "p[2]",
            "new_element_xhtml": "<p>Third</p>",
        },
    ]

    candidate = patch_xhtml_preserving(base, patches, sidecar)

    assert candidate == " \n\n<!-- gap -->\n<p>Second</p><p>Third</p>\n "


def test_preserving_patcher_rebases_nested_macro_xpath():
    base = (
        '<ac:structured-macro ac:name="info">'
        "<ac:rich-text-body><p>Before</p></ac:rich-text-body>"
        "</ac:structured-macro>"
        "<p>&ldquo;untouched&rdquo;</p>"
    )
    original_mdx = (
        "# Title\n\n"
        '<Callout type="info">\nBefore\n</Callout>\n\n'
        "“untouched”\n"
    )
    sidecar = build_sidecar(base, original_mdx, page_id="123")
    patches = [
        {
            "xhtml_xpath": "macro-info[1]/p[1]",
            "old_plain_text": "Before",
            "new_plain_text": "After",
        }
    ]

    candidate = patch_xhtml_preserving(base, patches, sidecar)

    assert "<p>After</p>" in candidate
    assert candidate.endswith("<p>&ldquo;untouched&rdquo;</p>")


def test_storage_well_formed_supports_confluence_namespaces_and_html_entities():
    valid = (
        '<ac:image><ri:attachment ri:filename="screen.png" /></ac:image>'
        "<p>&ldquo;text&rdquo;</p>"
    )
    invalid = "<p>unclosed"

    assert verify_storage_well_formed(valid) == (True, "")
    passed, detail = verify_storage_well_formed(invalid)
    assert passed is False
    assert detail


@dataclass
class _Block:
    content: str


@dataclass
class _Change:
    index: int
    change_type: str
    old_block: _Block | None
    new_block: _Block | None


def _proof_inputs():
    base = '<p>Before</p><p>&ldquo;untouched&rdquo;</p>'
    improved = "# Title\n\nAfter\n\n“untouched”\n"
    roundtrip = improved
    original = "# Title\n\nBefore\n\n“untouched”\n"
    sidecar = build_sidecar(base, original, page_id="123")
    patches = [
        {
            "xhtml_xpath": "p[1]",
            "old_plain_text": "Before",
            "new_plain_text": "After",
        }
    ]
    candidate = patch_xhtml_preserving(base, patches, sidecar)
    changes = [_Change(2, "modified", _Block("Before\n"), _Block("After\n"))]
    plan = canonical_plan_json(changes=changes, patches=patches, skipped_changes=[])
    return base, improved, roundtrip, sidecar, patches, candidate, changes, plan


def test_local_proof_requires_every_gate_and_returns_verified_local():
    base, improved, roundtrip, sidecar, patches, candidate, changes, plan = _proof_inputs()

    proof = build_local_proof(
        base_xhtml=base,
        improved_mdx=improved,
        roundtrip_mdx=roundtrip,
        candidate_xhtml=candidate,
        sidecar=sidecar,
        changes=changes,
        patches=patches,
        skipped_changes=[],
        plan_json=plan,
        deterministic_plan_json=plan,
        deterministic_candidate_xhtml=candidate,
        idempotent_candidate_xhtml=candidate,
        source_identity_passed=True,
        base_parity_passed=True,
        dependency_result=DependencyResult(True),
    )

    assert proof.status == "verified_local"
    assert proof.push_eligible is True
    assert tuple(gate.name for gate in proof.gates) == REQUIRED_LOCAL_GATES
    assert all(gate.passed for gate in proof.gates)


def test_local_proof_blocks_diagnostic_match_skips_and_non_idempotency():
    base, improved, _, sidecar, patches, candidate, changes, plan = _proof_inputs()
    diagnostic_only = improved.replace("After", "After ")

    proof = build_local_proof(
        base_xhtml=base,
        improved_mdx=improved,
        roundtrip_mdx=diagnostic_only,
        candidate_xhtml=candidate,
        sidecar=sidecar,
        changes=changes,
        patches=patches,
        skipped_changes=[{"reason": "unsupported"}],
        plan_json=plan,
        deterministic_plan_json=plan,
        deterministic_candidate_xhtml=candidate,
        idempotent_candidate_xhtml=candidate + "<p>duplicate</p>",
        source_identity_passed=True,
        base_parity_passed=True,
        dependency_result=DependencyResult(True),
    )

    assert proof.status == "blocked"
    assert proof.push_eligible is False
    assert "incomplete_patch_plan" in proof.blocked_reasons
    assert "semantic_roundtrip_mismatch" in proof.blocked_reasons
    assert "non_idempotent_output" in proof.blocked_reasons


def test_insert_operation_is_not_claimed_idempotent_when_it_duplicates():
    base = "<p>Before</p>"
    original = "# Title\n\nBefore\n"
    improved = "# Title\n\nBefore\n\nAdded\n"
    sidecar = build_sidecar(base, original, page_id="123")
    patches = [
        {
            "action": "insert",
            "after_xpath": "p[1]",
            "new_element_xhtml": "<p>Added</p>",
        }
    ]
    candidate = patch_xhtml_preserving(base, patches, sidecar)
    candidate_sidecar = build_sidecar(candidate, improved, page_id="123")
    applied_twice = patch_xhtml_preserving(candidate, patches, candidate_sidecar)
    changes = [_Change(4, "added", None, _Block("Added\n"))]
    plan = canonical_plan_json(changes=changes, patches=patches, skipped_changes=[])

    proof = build_local_proof(
        base_xhtml=base,
        improved_mdx=improved,
        roundtrip_mdx=improved,
        candidate_xhtml=candidate,
        sidecar=sidecar,
        changes=changes,
        patches=patches,
        skipped_changes=[],
        plan_json=plan,
        deterministic_plan_json=plan,
        deterministic_candidate_xhtml=candidate,
        idempotent_candidate_xhtml=applied_twice,
        source_identity_passed=True,
        base_parity_passed=True,
        dependency_result=DependencyResult(True),
    )

    assert proof.push_eligible is False
    assert "non_idempotent_output" in proof.blocked_reasons
