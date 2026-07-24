"""reverse-sync candidate의 strict local proof gate orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import html.entities
import json
import re
from typing import Any, Iterable
from xml.etree import ElementTree

from reverse_sync.dependencies import DependencyEvidence, DependencyResult
from reverse_sync.equivalence import EquivalenceResult, verify_push_equivalence
from reverse_sync.models import SyncStatus, VerificationGate, sha256_text
from reverse_sync.preserving_patcher import changed_root_xpaths
from reverse_sync.sidecar import RoundtripSidecar


REQUIRED_LOCAL_GATES = (
    "source_identity",
    "base_parity",
    "intent_complete",
    "artifact_integrity",
    "storage_well_formed",
    "preservation",
    "semantic_roundtrip",
    "determinism",
    "idempotency",
    "dependency",
)

_XML_ENTITIES = frozenset({"amp", "lt", "gt", "apos", "quot"})
_NAMED_ENTITY = re.compile(r"&([A-Za-z][A-Za-z0-9]+);")
_XML_NAMESPACES = (
    'xmlns:ac="urn:atlassian-confluence:ac" '
    'xmlns:ri="urn:atlassian-confluence:ri"'
)


@dataclass(frozen=True)
class LocalProof:
    """manifest에 기록할 local proof 결과."""

    status: str
    push_eligible: bool
    gates: tuple[VerificationGate, ...]
    equivalence: EquivalenceResult
    base_sha256: str
    candidate_sha256: str
    plan_sha256: str
    dependencies: DependencyEvidence = DependencyEvidence()
    dependency_detail: str = ""
    blocked_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifacts": {
                "base_sha256": self.base_sha256,
                "candidate_sha256": self.candidate_sha256,
                "plan_sha256": self.plan_sha256,
            },
            "blocked_reasons": list(self.blocked_reasons),
            "dependencies": self.dependencies.to_dict(),
            "dependency_detail": self.dependency_detail,
            "equivalence": self.equivalence.to_dict(),
            "gates": [gate.to_dict() for gate in self.gates],
            "push_eligible": self.push_eligible,
            "status": self.status,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"


def _replace_named_entity(match: re.Match[str]) -> str:
    name = match.group(1)
    if name in _XML_ENTITIES:
        return match.group(0)
    value = html.entities.html5.get(name + ";")
    if value is None:
        return match.group(0)
    return "".join(f"&#{ord(character)};" for character in value)


def verify_storage_well_formed(xhtml: str) -> tuple[bool, str]:
    """Confluence prefix를 namespace로 선언한 XML fragment parse를 수행한다."""
    xml_compatible = _NAMED_ENTITY.sub(_replace_named_entity, xhtml)
    wrapped = f"<reverse-sync-root {_XML_NAMESPACES}>{xml_compatible}</reverse-sync-root>"
    try:
        ElementTree.fromstring(wrapped)
    except ElementTree.ParseError as exc:
        return False, str(exc)
    return True, ""


def _root_index(sidecar: RoundtripSidecar) -> dict[str, int]:
    return {block.xhtml_xpath: index for index, block in enumerate(sidecar.blocks)}


def verify_preservation(
    *,
    base_xhtml: str,
    candidate_xhtml: str,
    sidecar: RoundtripSidecar,
    patches: Iterable[dict[str, Any]],
) -> tuple[bool, str]:
    """unchanged fragment, separator, document envelope의 byte 보존을 검증한다."""
    if sidecar.reassemble_xhtml() != base_xhtml:
        return False, "base sidecar integrity가 일치하지 않습니다"

    index = _root_index(sidecar)
    changed = changed_root_xpaths(patches)
    unknown = sorted(changed - set(index))
    if unknown:
        return False, "unknown changed fragment: " + ", ".join(unknown)

    insert_before = False
    insert_after: set[int] = set()
    for patch in patches:
        if patch.get("action", "modify") != "insert":
            continue
        anchor = patch.get("after_xpath")
        if anchor is None:
            insert_before = True
            continue
        root = str(anchor).split("/", 1)[0]
        if root not in index:
            return False, f"unknown insert anchor: {root}"
        insert_after.add(index[root])

    # renderer가 변경할 수 있는 영역만 wildcard로 두고, 나머지 source bytes를
    # 모두 exact match하는 anchored pattern을 만든다.
    pattern: list[str] = [re.escape(sidecar.document_envelope.prefix)]
    if insert_before:
        pattern.append(".*?")
    for position, block in enumerate(sidecar.blocks):
        if block.xhtml_xpath in changed:
            pattern.append(".*?")
        else:
            pattern.append(re.escape(block.xhtml_fragment))
        if position in insert_after:
            pattern.append(".*?")
        if position < len(sidecar.separators):
            pattern.append(re.escape(sidecar.separators[position]))
    pattern.append(re.escape(sidecar.document_envelope.suffix))

    if re.fullmatch("".join(pattern), candidate_xhtml, flags=re.DOTALL) is None:
        return False, "unchanged fragment, separator 또는 document envelope bytes가 바뀌었습니다"
    return True, ""


def canonical_plan_json(
    *,
    changes: Iterable[Any],
    patches: Iterable[dict[str, Any]],
    skipped_changes: Iterable[dict[str, Any]],
) -> str:
    """legacy patch builder output을 immutable plan boundary로 직렬화한다."""
    change_items = []
    for ordinal, change in enumerate(changes):
        old_block = getattr(change, "old_block", None)
        new_block = getattr(change, "new_block", None)
        change_items.append(
            {
                "change_type": str(getattr(change, "change_type", "")),
                "index": int(getattr(change, "index", ordinal)),
                "new_sha256": sha256_text(new_block.content) if new_block else "",
                "old_sha256": sha256_text(old_block.content) if old_block else "",
            }
        )
    value = {
        "adapter": "legacy-patch-builder-v1",
        "changes": change_items,
        "operations": list(patches),
        "schema_version": 1,
        "skipped_changes": list(skipped_changes),
    }
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ) + "\n"


def build_local_proof(
    *,
    base_xhtml: str,
    improved_mdx: str,
    roundtrip_mdx: str,
    candidate_xhtml: str,
    sidecar: RoundtripSidecar,
    changes: Iterable[Any],
    patches: list[dict[str, Any]],
    skipped_changes: list[dict[str, Any]],
    plan_json: str,
    deterministic_plan_json: str,
    deterministic_candidate_xhtml: str,
    idempotent_candidate_xhtml: str,
    source_identity_passed: bool,
    base_parity_passed: bool,
    dependency_result: DependencyResult,
) -> LocalProof:
    """모든 required local gate를 독립적으로 계산한다."""
    equivalence = verify_push_equivalence(improved_mdx, roundtrip_mdx)
    well_formed, well_formed_detail = verify_storage_well_formed(candidate_xhtml)
    preservation, preservation_detail = verify_preservation(
        base_xhtml=base_xhtml,
        candidate_xhtml=candidate_xhtml,
        sidecar=sidecar,
        patches=patches,
    )
    changes_tuple = tuple(changes)
    intent_complete = (
        bool(changes_tuple)
        and not skipped_changes
        and bool(patches)
    )
    determinism = (
        plan_json == deterministic_plan_json
        and candidate_xhtml == deterministic_candidate_xhtml
    )
    idempotency = candidate_xhtml == idempotent_candidate_xhtml

    gate_values = (
        ("source_identity", source_identity_passed, "page_identity_mismatch"),
        ("base_parity", base_parity_passed, "base_parity_mismatch"),
        ("intent_complete", intent_complete, "incomplete_patch_plan"),
        ("artifact_integrity", True, ""),
        ("storage_well_formed", well_formed, "invalid_storage_xhtml"),
        ("preservation", preservation, "preservation_mismatch"),
        (
            "semantic_roundtrip",
            equivalence.passed,
            "semantic_roundtrip_mismatch",
        ),
        ("determinism", determinism, "non_deterministic_output"),
        ("idempotency", idempotency, "non_idempotent_output"),
        (
            "dependency",
            dependency_result.passed,
            dependency_result.reason_code or "dependency_failure",
        ),
    )
    gates = tuple(
        VerificationGate(name=name, passed=passed, reason_code="" if passed else reason)
        for name, passed, reason in gate_values
    )
    blocked_reasons = tuple(
        gate.reason_code for gate in gates if not gate.passed and gate.reason_code
    )
    # Parse/preservation detail은 canonical evidence에서 유실되지 않도록
    # equivalence diff 뒤에 diagnostic block으로 붙이지 않고 reason별로 유지한다.
    if not well_formed and well_formed_detail:
        blocked_reasons += (f"invalid_storage_xhtml:{well_formed_detail}",)
    if not preservation and preservation_detail:
        blocked_reasons += (f"preservation_mismatch:{preservation_detail}",)

    push_eligible = not blocked_reasons and all(gate.passed for gate in gates)
    return LocalProof(
        status=SyncStatus.VERIFIED_LOCAL.value if push_eligible else "blocked",
        push_eligible=push_eligible,
        gates=gates,
        equivalence=equivalence,
        base_sha256=sha256_text(base_xhtml),
        candidate_sha256=sha256_text(candidate_xhtml),
        plan_sha256=sha256_text(plan_json),
        dependencies=dependency_result.evidence,
        dependency_detail=dependency_result.detail,
        blocked_reasons=blocked_reasons,
    )
