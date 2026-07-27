"""검증된 immutable manifest를 Confluence에 발행하는 lifecycle service."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from reverse_sync.equivalence import verify_push_equivalence
from reverse_sync.verification_service import strip_frontmatter


@dataclass(frozen=True)
class ManifestPushSummary:
    """explicit manifest 발행 전 확인에 필요한 immutable identity."""

    manifest_path: Path
    run_id: str
    page_id: str
    title: str
    base_version: int
    candidate_sha256: str
    change_count: int
    operation_count: int


class PushConflictError(Exception):
    """Confluence page가 preflight 이후 변경된 경우 발생합니다."""


@dataclass(frozen=True)
class PublishRuntime:
    """CLI 환경 의존성을 publish lifecycle에 주입합니다."""

    project_dir: Path
    forward_convert: Callable[..., str]
    detect_language: Callable[[str], str]
    load_manifest_summary: Callable[[str], ManifestPushSummary]


def load_manifest_push_summary(manifest_path: str) -> ManifestPushSummary:
    """explicit manifest의 integrity와 typed plan schema를 PUT 전에 검증합니다."""

    from reverse_sync.manifest import (
        ArtifactTamperedError,
        load_sync_manifest,
        verify_manifest_integrity,
    )

    resolved_path = Path(manifest_path).expanduser().resolve()
    manifest = load_sync_manifest(resolved_path)
    verify_manifest_integrity(resolved_path, manifest)
    if not manifest.push_eligible:
        raise ValueError("push eligible이 아닌 manifest는 발행할 수 없습니다")

    plan_ref = manifest.artifact("patch_plan")
    try:
        plan = json.loads((resolved_path.parent / plan_ref.path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactTamperedError("patch plan JSON을 읽을 수 없습니다") from exc
    if not isinstance(plan, dict) or plan.get("schema_version") != 2:
        raise ArtifactTamperedError("explicit push는 PatchPlan schema v2가 필요합니다")
    if plan.get("intent_complete") is not True:
        raise ArtifactTamperedError(
            "intent_complete가 아닌 PatchPlan은 발행할 수 없습니다"
        )
    intents = plan.get("intents")
    operations = plan.get("operations")
    if not isinstance(intents, list) or not isinstance(operations, list):
        raise ArtifactTamperedError(
            "PatchPlan intents/operations 형식이 올바르지 않습니다"
        )
    operation_count = sum(
        1
        for operation in operations
        if isinstance(operation, dict) and operation.get("executable") is True
    )
    if operation_count < 1:
        raise ArtifactTamperedError("PatchPlan에 executable operation이 없습니다")

    candidate_ref = manifest.artifact("candidate_xhtml")
    return ManifestPushSummary(
        manifest_path=resolved_path,
        run_id=manifest.run_id,
        page_id=manifest.page_id,
        title=manifest.base_title,
        base_version=manifest.base_version,
        candidate_sha256=candidate_ref.sha256,
        change_count=len(intents),
        operation_count=operation_count,
    )


def publish_verified_run(
    page_id: str,
    config,
    *,
    manifest_path: str,
    runtime: PublishRuntime,
) -> dict:
    """검증된 manifest에 결합된 candidate를 한 번만 발행하고 재검증합니다."""

    from reverse_sync.confluence_client import (
        ConfluenceGateway,
        VersionConflictError,
    )
    from reverse_sync.manifest import load_sync_manifest
    from reverse_sync.publisher import publish_verified_manifest

    if not manifest_path:
        raise ValueError("push에는 explicit manifest_path가 필요합니다")

    var_dir = runtime.project_dir / "var" / page_id
    summary = runtime.load_manifest_summary(manifest_path)
    resolved_manifest_path = summary.manifest_path
    manifest = load_sync_manifest(resolved_manifest_path)
    if manifest.page_id != str(page_id):
        raise ValueError(
            f"manifest page ID({manifest.page_id})와 요청 page ID({page_id})가 다릅니다."
        )

    def semantic_verifier(snapshot, verified_manifest_path: Path) -> bool:
        improved_ref = manifest.artifact("improved_mdx")
        expected_mdx = (
            verified_manifest_path.parent / improved_ref.path
        ).read_text()
        persisted_xhtml_path = (
            verified_manifest_path.parent / "postcondition.xhtml"
        )
        persisted_mdx_path = verified_manifest_path.parent / "postcondition.mdx"
        persisted_xhtml_path.write_text(snapshot.storage_xhtml)
        runtime.forward_convert(
            str(persisted_xhtml_path),
            str(persisted_mdx_path),
            page_id,
            language=runtime.detect_language(manifest.improved_descriptor),
            page_dir=str(var_dir),
        )
        actual_mdx = persisted_mdx_path.read_text()

        from reverse_sync.base_parity import verify_source_identity

        identity = verify_source_identity(
            snapshot,
            expected_mdx,
            actual_mdx,
            require_confluence_url=True,
        )
        if not identity.passed:
            return False
        return verify_push_equivalence(
            strip_frontmatter(expected_mdx),
            strip_frontmatter(actual_mdx),
        ).passed

    try:
        receipt = publish_verified_manifest(
            resolved_manifest_path,
            ConfluenceGateway(config),
            semantic_verifier=semantic_verifier,
        )
    except VersionConflictError as exc:
        raise PushConflictError(
            f"페이지 {page_id} ({manifest.base_title})가 preflight 이후 변경되었습니다. "
            "최신 snapshot으로 online verify를 다시 실행하세요."
        ) from exc

    backup_path = var_dir / "reverse-sync.backup.xhtml"
    var_dir.mkdir(parents=True, exist_ok=True)
    base_ref = manifest.artifact("base_xhtml")
    shutil.copy2(resolved_manifest_path.parent / base_ref.path, backup_path)

    return {
        "page_id": page_id,
        "status": receipt.status.value,
        "title": receipt.title,
        "version": receipt.version,
        "url": "",
        "backup": str(backup_path),
        "manifest_path": str(resolved_manifest_path),
        "manifest_sha256": receipt.manifest_sha256,
    }
