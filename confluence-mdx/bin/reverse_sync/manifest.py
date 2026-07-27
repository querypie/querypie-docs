"""실행별 reverse-sync artifact와 immutable manifest 관리."""

from __future__ import annotations

import hashlib
import json
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
