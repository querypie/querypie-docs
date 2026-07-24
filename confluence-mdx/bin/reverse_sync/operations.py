"""reverse-sync planning 결과의 immutable typed boundary."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from typing import Any, Iterable


PLAN_SCHEMA_VERSION = 2


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


@dataclass(frozen=True)
class ChangeIntent:
    """original/improved MDX 사이의 content intent."""

    ordinal: int
    index: int
    change_type: str
    block_type: str
    old_sha256: str
    new_sha256: str
    provenance_xpath: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "block_type": self.block_type,
            "change_type": self.change_type,
            "index": self.index,
            "new_sha256": self.new_sha256,
            "old_sha256": self.old_sha256,
            "ordinal": self.ordinal,
        }
        if self.provenance_xpath:
            result["provenance_xpath"] = self.provenance_xpath
        return result


@dataclass(frozen=True)
class TargetIdentity:
    """base snapshot 안에서 operation target을 고정하는 provenance."""

    kind: str
    xpath: str
    root_xpath: str
    base_fragment_sha256: str
    mdx_content_sha256: str = ""
    mdx_line_range: tuple[int, int] = (0, 0)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "base_fragment_sha256": self.base_fragment_sha256,
            "kind": self.kind,
            "root_xpath": self.root_xpath,
            "xpath": self.xpath,
        }
        if self.mdx_content_sha256:
            result["mdx_content_sha256"] = self.mdx_content_sha256
        if self.mdx_line_range != (0, 0):
            result["mdx_line_range"] = list(self.mdx_line_range)
        return result


@dataclass(frozen=True)
class PlanIssue:
    """planner가 fail-closed로 기록하는 typed reason."""

    reason_code: str
    description: str
    block_id: str = ""
    capability_id: str = ""
    intent_ordinal: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "description": self.description,
            "reason_code": self.reason_code,
        }
        if self.block_id:
            result["block_id"] = self.block_id
        if self.capability_id:
            result["capability_id"] = self.capability_id
        if self.intent_ordinal is not None:
            result["intent_ordinal"] = self.intent_ordinal
        return result

    def to_legacy_dict(self) -> dict[str, Any]:
        """기존 CLI skipped_changes schema와의 compatibility boundary."""
        result = self.to_dict()
        result["reason"] = result.pop("reason_code")
        return result


_VALID_ACTIONS = frozenset({"modify", "delete", "insert", "replace_fragment"})


def _validate_legacy_patch(patch: dict[str, Any]) -> tuple[str, str]:
    action = str(patch.get("action", "modify"))
    if action not in _VALID_ACTIONS:
        raise ValueError(f"지원하지 않는 patch action입니다: {action}")

    if action == "insert":
        if "new_element_xhtml" not in patch:
            raise ValueError("insert operation에 new_element_xhtml이 없습니다")
        target = patch.get("after_xpath")
        return action, "$document-start" if target is None else str(target)

    target = patch.get("xhtml_xpath")
    if not target:
        raise ValueError(f"{action} operation에 xhtml_xpath가 없습니다")
    if action == "replace_fragment" and "new_element_xhtml" not in patch:
        raise ValueError("replace_fragment operation에 new_element_xhtml이 없습니다")
    if action == "modify":
        has_inner = "new_inner_xhtml" in patch
        has_text = "old_plain_text" in patch and "new_plain_text" in patch
        if not (has_inner or has_text):
            raise ValueError("modify operation에 renderer input이 없습니다")
    return action, str(target)


@dataclass(frozen=True)
class PatchOperation:
    """capability, target identity, proof 요구사항을 가진 renderer operation."""

    operation_id: str
    action: str
    capability_id: str
    target: TargetIdentity
    required_proof: tuple[str, ...]
    intent_ordinals: tuple[int, ...]
    renderer_input_json: str
    executable: bool
    reason_code: str = ""

    @classmethod
    def from_legacy_patch(
        cls,
        *,
        operation_id: str,
        patch: dict[str, Any],
        capability_id: str,
        target: TargetIdentity,
        required_proof: Iterable[str],
        intent_ordinals: Iterable[int],
        executable: bool,
        reason_code: str = "",
    ) -> "PatchOperation":
        action, patch_target = _validate_legacy_patch(patch)
        if patch_target != target.xpath:
            raise ValueError(
                "operation target과 renderer input target이 다릅니다: "
                f"{target.xpath} != {patch_target}"
            )
        if not capability_id:
            raise ValueError("operation capability_id가 비어 있습니다")
        proof = tuple(dict.fromkeys(str(item) for item in required_proof if item))
        if not proof:
            raise ValueError("operation required_proof가 비어 있습니다")
        if executable and reason_code:
            raise ValueError("실행 가능한 operation에 block reason이 있습니다")
        if not executable and not reason_code:
            raise ValueError("실행 불가능한 operation에 block reason이 없습니다")
        return cls(
            operation_id=operation_id,
            action=action,
            capability_id=capability_id,
            target=target,
            required_proof=proof,
            intent_ordinals=tuple(sorted(set(intent_ordinals))),
            renderer_input_json=_canonical_json(patch),
            executable=executable,
            reason_code=reason_code,
        )

    def to_patch_dict(self) -> dict[str, Any]:
        """validated legacy renderer boundary에서만 raw patch dict를 복원합니다."""
        return json.loads(self.renderer_input_json)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "action": self.action,
            "capability_id": self.capability_id,
            "executable": self.executable,
            "intent_ordinals": list(self.intent_ordinals),
            "operation_id": self.operation_id,
            "reason_code": self.reason_code,
            "renderer_input": self.to_patch_dict(),
            "required_proof": list(self.required_proof),
            "target": self.target.to_dict(),
        }
        return result


@dataclass(frozen=True)
class PatchPlan:
    """MDX intent와 XHTML operation을 결합하는 deterministic plan."""

    intents: tuple[ChangeIntent, ...]
    operations: tuple[PatchOperation, ...]
    issues: tuple[PlanIssue, ...]
    adapter: str = "legacy-patch-builder-v2"
    schema_version: int = PLAN_SCHEMA_VERSION

    @property
    def covered_intent_ordinals(self) -> frozenset[int]:
        return frozenset(
            ordinal
            for operation in self.operations
            if operation.executable
            for ordinal in operation.intent_ordinals
        )

    @property
    def intent_complete(self) -> bool:
        required = {intent.ordinal for intent in self.intents}
        coverage = Counter(
            ordinal
            for operation in self.executable_operations
            for ordinal in operation.intent_ordinals
        )
        return (
            bool(required)
            and not self.issues
            and bool(self.executable_operations)
            and set(coverage) == required
            and all(count == 1 for count in coverage.values())
        )

    @property
    def executable_operations(self) -> tuple[PatchOperation, ...]:
        return tuple(operation for operation in self.operations if operation.executable)

    def to_patch_dicts(self) -> list[dict[str, Any]]:
        """XHTML renderer에 넘길 validated operation만 raw boundary로 변환합니다."""
        return [
            operation.to_patch_dict()
            for operation in self.executable_operations
        ]

    def to_legacy_skipped_changes(self) -> list[dict[str, Any]]:
        return [issue.to_legacy_dict() for issue in self.issues]

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "intent_complete": self.intent_complete,
            "intents": [intent.to_dict() for intent in self.intents],
            "issues": [issue.to_dict() for issue in self.issues],
            "operations": [operation.to_dict() for operation in self.operations],
            "schema_version": self.schema_version,
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict()) + "\n"
