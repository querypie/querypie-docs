"""실행별 reverse-sync artifact와 immutable manifest 관리."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

from reverse_sync.models import (
    ArtifactRef,
    PageSnapshot,
    ReasonCode,
    SyncManifest,
    VerificationGate,
    sha256_text,
)


MANIFEST_SCHEMA_VERSION = 2
SUPPORTED_VERIFIER_POLICIES = frozenset({"reverse-sync-equivalence-v1"})
CURRENT_TOOL_VERSION = "reverse-sync-cli-v5"
REQUIRED_PUSH_GATES = frozenset(
    {
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
    }
)
REQUIRED_ARTIFACTS = frozenset(
    {
        "base_xhtml",
        "original_mdx",
        "improved_mdx",
        "patch_plan",
        "candidate_xhtml",
        "local_proof",
    }
)


class ArtifactTamperedError(ValueError):
    """manifest 또는 referenced artifact의 hash가 달라졌습니다."""

    reason_code = ReasonCode.ARTIFACT_TAMPERED.value


class StaleVerificationError(ValueError):
    """현재 publisher가 이해하지 못하는 검증 계약입니다."""

    reason_code = ReasonCode.STALE_VERIFICATION.value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_immutable(path: Path, content: str) -> None:
    """같은 경로에는 같은 bytes만 허용한다."""
    encoded = content.encode("utf-8")
    if path.exists():
        if path.read_bytes() != encoded:
            raise ArtifactTamperedError(f"immutable artifact가 변경되었습니다: {path.name}")
        return
    path.write_bytes(encoded)


def _artifact_ref(run_dir: Path, name: str, filename: str, content: str) -> ArtifactRef:
    path = run_dir / filename
    _write_immutable(path, content)
    return ArtifactRef(name=name, path=filename, sha256=sha256_text(content))


def _derive_run_id(
    *,
    base: PageSnapshot,
    original_mdx: str,
    improved_mdx: str,
    patch_plan: str,
    candidate_xhtml: str,
    local_proof: str,
    verifier_policy: str,
    tool_version: str,
) -> str:
    identity = {
        "base_storage_sha256": base.storage_sha256,
        "base_title": base.title,
        "base_version": base.version,
        "base_fetched_at": base.fetched_at,
        "candidate_sha256": sha256_text(candidate_xhtml),
        "improved_sha256": sha256_text(improved_mdx),
        "local_proof_sha256": sha256_text(local_proof),
        "original_sha256": sha256_text(original_mdx),
        "page_id": base.page_id,
        "patch_plan_sha256": sha256_text(patch_plan),
        "tool_version": tool_version,
        "verifier_policy": verifier_policy,
    }
    canonical = json.dumps(identity, separators=(",", ":"), sort_keys=True)
    return sha256_text(canonical)[:20]


def create_sync_manifest(
    *,
    runs_dir: Path,
    base: PageSnapshot,
    original_mdx: str,
    original_descriptor: str,
    improved_mdx: str,
    improved_descriptor: str,
    patch_plan: str,
    candidate_xhtml: str,
    local_proof: str,
    verifier_policy: str,
    tool_version: str,
    push_eligible: bool,
    gates: Iterable[VerificationGate] = (),
) -> Path:
    """실행별 artifact와 canonical manifest를 생성하고 manifest 경로를 반환한다."""
    if verifier_policy not in SUPPORTED_VERIFIER_POLICIES:
        raise StaleVerificationError(
            f"지원하지 않는 verifier policy입니다: {verifier_policy}"
        )
    if tool_version != CURRENT_TOOL_VERSION:
        raise StaleVerificationError(
            f"지원하지 않는 tool version입니다: {tool_version}"
        )

    run_id = _derive_run_id(
        base=base,
        original_mdx=original_mdx,
        improved_mdx=improved_mdx,
        patch_plan=patch_plan,
        candidate_xhtml=candidate_xhtml,
        local_proof=local_proof,
        verifier_policy=verifier_policy,
        tool_version=tool_version,
    )
    run_dir = Path(runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    gate_results = tuple(gates)
    if push_eligible:
        passed_gates = {gate.name for gate in gate_results if gate.passed}
        if not REQUIRED_PUSH_GATES.issubset(passed_gates):
            missing = sorted(REQUIRED_PUSH_GATES - passed_gates)
            raise StaleVerificationError(
                "push manifest의 required gate가 통과하지 않았습니다: "
                + ", ".join(missing)
            )

    artifacts = (
        _artifact_ref(run_dir, "base_xhtml", "base.xhtml", base.storage_xhtml),
        _artifact_ref(run_dir, "original_mdx", "original.mdx", original_mdx),
        _artifact_ref(run_dir, "improved_mdx", "improved.mdx", improved_mdx),
        _artifact_ref(run_dir, "patch_plan", "patch-plan.json", patch_plan),
        _artifact_ref(run_dir, "candidate_xhtml", "candidate.xhtml", candidate_xhtml),
        _artifact_ref(run_dir, "local_proof", "local-proof.json", local_proof),
    )
    manifest = SyncManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id=run_id,
        page_id=base.page_id,
        base_status=base.status,
        base_title=base.title,
        base_version=base.version,
        base_storage_sha256=base.storage_sha256,
        base_fetched_at=base.fetched_at,
        base_api=base.api,
        original_descriptor=original_descriptor,
        improved_descriptor=improved_descriptor,
        verifier_policy=verifier_policy,
        tool_version=tool_version,
        push_eligible=push_eligible,
        artifacts=artifacts,
        gates=gate_results,
    )
    manifest_path = run_dir / "manifest.json"
    manifest_content = manifest.to_canonical_json()
    _write_immutable(manifest_path, manifest_content)
    _write_immutable(run_dir / "manifest.sha256", sha256_text(manifest_content) + "\n")
    return manifest_path


def load_sync_manifest(path: Path) -> SyncManifest:
    try:
        value = json.loads(Path(path).read_text())
        if type(value.get("push_eligible")) is not bool:
            raise ValueError("push_eligible은 boolean이어야 합니다")
        manifest = SyncManifest.from_dict(value)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ArtifactTamperedError(f"manifest 형식이 올바르지 않습니다: {path}") from exc
    if manifest.schema_version != MANIFEST_SCHEMA_VERSION:
        raise StaleVerificationError(
            f"지원하지 않는 manifest schema입니다: {manifest.schema_version}"
        )
    if manifest.verifier_policy not in SUPPORTED_VERIFIER_POLICIES:
        raise StaleVerificationError(
            f"지원하지 않는 verifier policy입니다: {manifest.verifier_policy}"
        )
    if manifest.tool_version != CURRENT_TOOL_VERSION:
        raise StaleVerificationError(
            f"지원하지 않는 tool version입니다: {manifest.tool_version}"
        )
    return manifest


def _verify_patch_plan_contract(path: Path, manifest: SyncManifest) -> None:
    plan_ref = manifest.artifact("patch_plan")
    try:
        plan = json.loads((path.parent / plan_ref.path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactTamperedError("patch plan JSON을 읽을 수 없습니다") from exc
    if not isinstance(plan, dict):
        raise ArtifactTamperedError("patch plan은 JSON object여야 합니다")
    if plan.get("schema_version") != 2:
        raise StaleVerificationError(
            "push에는 현재 publisher가 지원하는 PatchPlan schema v2가 필요합니다"
        )
    if plan.get("intent_complete") is not True:
        raise ArtifactTamperedError(
            "intent_complete가 아닌 PatchPlan은 발행할 수 없습니다"
        )

    intents = plan.get("intents")
    operations = plan.get("operations")
    issues = plan.get("issues")
    if (
        not isinstance(intents, list)
        or not isinstance(operations, list)
        or not isinstance(issues, list)
    ):
        raise ArtifactTamperedError(
            "PatchPlan intents/operations/issues 형식이 올바르지 않습니다"
        )
    if not intents or not operations or issues:
        raise ArtifactTamperedError(
            "complete PatchPlan은 intent와 operation이 있고 issue가 없어야 합니다"
        )

    intent_ordinals: list[int] = []
    for intent in intents:
        ordinal = intent.get("ordinal") if isinstance(intent, dict) else None
        if (
            not isinstance(ordinal, int)
            or isinstance(ordinal, bool)
            or ordinal < 0
        ):
            raise ArtifactTamperedError(
                "PatchPlan intent ordinal이 올바르지 않습니다"
            )
        intent_ordinals.append(ordinal)
    if len(intent_ordinals) != len(set(intent_ordinals)):
        raise ArtifactTamperedError("PatchPlan intent ordinal이 중복되었습니다")

    operation_ids: list[str] = []
    coverage: Counter[int] = Counter()
    for operation in operations:
        if not isinstance(operation, dict):
            raise ArtifactTamperedError(
                "PatchPlan operation 형식이 올바르지 않습니다"
            )
        operation_id = operation.get("operation_id")
        covered = operation.get("intent_ordinals")
        if not isinstance(operation_id, str) or not operation_id:
            raise ArtifactTamperedError("PatchPlan operation ID가 올바르지 않습니다")
        if operation.get("executable") is not True:
            raise ArtifactTamperedError(
                "complete PatchPlan에 실행 불가능한 operation이 있습니다"
            )
        if not isinstance(covered, list) or not covered:
            raise ArtifactTamperedError(
                "PatchPlan operation의 intent coverage가 비어 있습니다"
            )
        if any(
            not isinstance(ordinal, int)
            or isinstance(ordinal, bool)
            or ordinal < 0
            for ordinal in covered
        ):
            raise ArtifactTamperedError(
                "PatchPlan operation intent ordinal이 올바르지 않습니다"
            )
        operation_ids.append(operation_id)
        coverage.update(covered)
    if len(operation_ids) != len(set(operation_ids)):
        raise ArtifactTamperedError("PatchPlan operation ID가 중복되었습니다")
    if set(coverage) != set(intent_ordinals) or any(
        count != 1 for count in coverage.values()
    ):
        raise ArtifactTamperedError(
            "PatchPlan은 각 intent를 정확히 한 번 실행해야 합니다"
        )


def _verification_gate_map(gates: Iterable[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for gate in gates:
        if not isinstance(gate, dict):
            raise ArtifactTamperedError("local proof gate 형식이 올바르지 않습니다")
        name = gate.get("name")
        passed = gate.get("passed")
        reason_code = gate.get("reason_code", "")
        if (
            not isinstance(name, str)
            or not name
            or type(passed) is not bool
            or not isinstance(reason_code, str)
            or name in result
        ):
            raise ArtifactTamperedError("local proof gate 형식이 올바르지 않습니다")
        normalized = {"name": name, "passed": passed}
        if reason_code:
            normalized["reason_code"] = reason_code
        result[name] = normalized
    return result


def _verify_local_proof_binding(path: Path, manifest: SyncManifest) -> None:
    proof_ref = manifest.artifact("local_proof")
    try:
        proof = json.loads((path.parent / proof_ref.path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactTamperedError("local proof JSON을 읽을 수 없습니다") from exc
    if not isinstance(proof, dict):
        raise ArtifactTamperedError("local proof는 JSON object여야 합니다")
    if (
        proof.get("status") != "verified_local"
        or proof.get("push_eligible") is not True
        or proof.get("blocked_reasons") != []
    ):
        raise ArtifactTamperedError(
            "local proof가 verified_local 발행 계약과 일치하지 않습니다"
        )

    expected_artifacts = {
        "base_sha256": manifest.artifact("base_xhtml").sha256,
        "candidate_sha256": manifest.artifact("candidate_xhtml").sha256,
        "plan_sha256": manifest.artifact("patch_plan").sha256,
    }
    if proof.get("artifacts") != expected_artifacts:
        raise ArtifactTamperedError(
            "local proof artifact hash가 manifest artifact와 일치하지 않습니다"
        )

    proof_gates = proof.get("gates")
    if not isinstance(proof_gates, list):
        raise ArtifactTamperedError("local proof gate 목록이 없습니다")
    actual_gate_map = _verification_gate_map(proof_gates)
    expected_gate_map = {
        gate.name: gate.to_dict()
        for gate in manifest.gates
    }
    if actual_gate_map != expected_gate_map:
        raise ArtifactTamperedError(
            "local proof gate가 manifest gate와 일치하지 않습니다"
        )


def verify_manifest_integrity(path: Path, manifest: SyncManifest) -> None:
    """manifest sidecar와 모든 referenced artifact hash를 재검산한다."""
    path = Path(path)
    expected_manifest_hash_path = path.parent / "manifest.sha256"
    if not expected_manifest_hash_path.is_file():
        raise ArtifactTamperedError("manifest.sha256이 없습니다")
    expected_manifest_hash = expected_manifest_hash_path.read_text().strip()
    actual_manifest_hash = sha256_bytes(path.read_bytes())
    if expected_manifest_hash != actual_manifest_hash:
        raise ArtifactTamperedError("manifest.json hash가 일치하지 않습니다")

    if manifest.run_id != path.parent.name:
        raise ArtifactTamperedError("manifest run_id와 artifact directory가 다릅니다")
    if manifest.base_status != "current":
        raise ArtifactTamperedError("manifest base status가 current가 아닙니다")
    if manifest.base_version < 1:
        raise ArtifactTamperedError("manifest base version이 올바르지 않습니다")

    artifact_names = [artifact.name for artifact in manifest.artifacts]
    if len(artifact_names) != len(set(artifact_names)):
        raise ArtifactTamperedError("manifest artifact name이 중복되었습니다")
    if not REQUIRED_ARTIFACTS.issubset(artifact_names):
        missing = sorted(REQUIRED_ARTIFACTS - set(artifact_names))
        raise ArtifactTamperedError(
            "manifest required artifact가 없습니다: " + ", ".join(missing)
        )
    if manifest.push_eligible:
        gate_names = [gate.name for gate in manifest.gates]
        if len(gate_names) != len(set(gate_names)):
            raise ArtifactTamperedError("manifest verification gate가 중복되었습니다")
        passed_gates = {gate.name for gate in manifest.gates if gate.passed}
        if not REQUIRED_PUSH_GATES.issubset(passed_gates):
            missing = sorted(REQUIRED_PUSH_GATES - passed_gates)
            raise ArtifactTamperedError(
                "manifest required gate가 통과하지 않았습니다: "
                + ", ".join(missing)
            )

    resolved_run_dir = path.parent.resolve()
    for artifact in manifest.artifacts:
        artifact_path = (path.parent / artifact.path).resolve()
        try:
            artifact_path.relative_to(resolved_run_dir)
        except ValueError as exc:
            raise ArtifactTamperedError(
                f"artifact 경로가 run directory를 벗어납니다: {artifact.path}"
            ) from exc
        if not artifact_path.is_file():
            raise ArtifactTamperedError(f"artifact가 없습니다: {artifact.path}")
        actual_hash = sha256_bytes(artifact_path.read_bytes())
        if actual_hash != artifact.sha256:
            raise ArtifactTamperedError(
                f"artifact hash가 일치하지 않습니다: {artifact.path}"
            )

    base_ref = manifest.artifact("base_xhtml")
    if base_ref.sha256 != manifest.base_storage_sha256:
        raise ArtifactTamperedError("base snapshot hash와 base.xhtml hash가 다릅니다")
    if manifest.push_eligible:
        _verify_patch_plan_contract(path, manifest)
        _verify_local_proof_binding(path, manifest)
