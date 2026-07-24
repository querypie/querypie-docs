"""검증된 SyncManifest만 소비하는 transaction-safe Confluence publisher."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from reverse_sync.manifest import (
    ArtifactTamperedError,
    load_sync_manifest,
    sha256_bytes,
    verify_manifest_integrity,
)
from reverse_sync.models import (
    PageSnapshot,
    PushReceipt,
    ReasonCode,
    SyncManifest,
    SyncStatus,
)


class PageGateway(Protocol):
    def get_current_page(self, page_id: str) -> PageSnapshot: ...

    def get_active_draft(self, page_id: str) -> PageSnapshot | None: ...

    def update_page(
        self,
        page_id: str,
        *,
        title: str,
        version: int,
        xhtml_body: str,
    ) -> dict: ...


class PublishBlockedError(RuntimeError):
    reason_code = ""


class RemoteDriftError(PublishBlockedError):
    reason_code = ReasonCode.REMOTE_DRIFT.value


class ActiveDraftError(PublishBlockedError):
    reason_code = ReasonCode.ACTIVE_DRAFT.value


class PostconditionError(PublishBlockedError):
    reason_code = ReasonCode.POSTCONDITION_FAILED.value


def _write_snapshot(path: Path, snapshot: PageSnapshot) -> None:
    _write_json(path, snapshot.to_dict(include_body=True))


def _write_json(path: Path, value: dict) -> None:
    import json

    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    )


def _write_receipt(path: Path, receipt: PushReceipt) -> None:
    path.write_text(receipt.to_canonical_json())


def _manifest_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _candidate_body(path: Path, manifest: SyncManifest) -> str:
    candidate = manifest.artifact("candidate_xhtml")
    return (path.parent / candidate.path).read_text()


def _assert_remote_identity(manifest: SyncManifest, remote: PageSnapshot) -> None:
    mismatches: list[str] = []
    if remote.page_id != manifest.page_id:
        mismatches.append("page_id")
    if remote.status != manifest.base_status:
        mismatches.append("status")
    if remote.title != manifest.base_title:
        mismatches.append("title")
    if mismatches:
        raise RemoteDriftError(
            f"원격 page identity가 검증 base와 다릅니다: {', '.join(mismatches)}"
        )


def _assert_remote_base(manifest: SyncManifest, remote: PageSnapshot) -> None:
    mismatches: list[str] = []
    if remote.version != manifest.base_version:
        mismatches.append("version")
    if remote.storage_sha256 != manifest.base_storage_sha256:
        mismatches.append("storage_xhtml")
    if mismatches:
        raise RemoteDriftError(
            f"원격 page가 검증 base 이후 변경되었습니다: {', '.join(mismatches)}"
        )


def _response_version(response: dict) -> int | None:
    version = response.get("version")
    if isinstance(version, dict) and isinstance(version.get("number"), int):
        return version["number"]
    return None


def publish_verified_manifest(
    manifest_path: Path,
    gateway: PageGateway,
    *,
    semantic_verifier: Callable[[PageSnapshot, Path], bool] | None = None,
) -> PushReceipt:
    """verified manifest에 대해 preflight → PUT → postcondition을 수행한다.

    conflict가 발생해도 최신 version을 새 base로 채택하거나 PUT을 재시도하지 않는다.
    """
    manifest_path = Path(manifest_path)
    manifest = load_sync_manifest(manifest_path)
    if not manifest.push_eligible:
        raise ArtifactTamperedError("manifest가 push eligible 상태가 아닙니다")
    verify_manifest_integrity(manifest_path, manifest)

    candidate_body = _candidate_body(manifest_path, manifest)
    candidate_hash = manifest.artifact("candidate_xhtml").sha256
    manifest_hash = _manifest_hash(manifest_path)

    preflight = gateway.get_current_page(manifest.page_id)
    run_dir = manifest_path.parent
    _write_snapshot(run_dir / "preflight.snapshot.json", preflight)
    _assert_remote_identity(manifest, preflight)
    draft = gateway.get_active_draft(manifest.page_id)
    if draft is not None:
        _write_snapshot(run_dir / "draft.snapshot.json", draft)
        raise ActiveDraftError(
            f"페이지 {manifest.page_id}에 active draft가 있어 push를 중단합니다"
        )

    if preflight.storage_sha256 == candidate_hash:
        receipt = PushReceipt(
            status=SyncStatus.ALREADY_APPLIED,
            page_id=manifest.page_id,
            version=preflight.version,
            title=preflight.title,
            manifest_sha256=manifest_hash,
            base_version=manifest.base_version,
            candidate_sha256=candidate_hash,
            persisted_sha256=preflight.storage_sha256,
        )
        _write_snapshot(run_dir / "post.snapshot.json", preflight)
        _write_receipt(run_dir / "push-receipt.json", receipt)
        return receipt

    try:
        _assert_remote_base(manifest, preflight)
    except RemoteDriftError:
        semantically_applied = False
        if semantic_verifier is not None:
            try:
                semantically_applied = semantic_verifier(preflight, manifest_path)
            except Exception:
                semantically_applied = False
        if not semantically_applied:
            raise
        receipt = PushReceipt(
            status=SyncStatus.ALREADY_APPLIED,
            page_id=manifest.page_id,
            version=preflight.version,
            title=preflight.title,
            manifest_sha256=manifest_hash,
            base_version=manifest.base_version,
            candidate_sha256=candidate_hash,
            persisted_sha256=preflight.storage_sha256,
        )
        _write_snapshot(run_dir / "post.snapshot.json", preflight)
        _write_receipt(run_dir / "push-receipt.json", receipt)
        return receipt

    expected_version = manifest.base_version + 1
    response = gateway.update_page(
        manifest.page_id,
        title=manifest.base_title,
        version=expected_version,
        xhtml_body=candidate_body,
    )
    _write_json(run_dir / "update.response.json", response)

    persisted = gateway.get_current_page(manifest.page_id)
    _write_snapshot(run_dir / "post.snapshot.json", persisted)
    response_version = _response_version(response)
    identity_and_version_ok = (
        persisted.page_id == manifest.page_id
        and persisted.status == manifest.base_status
        and persisted.title == manifest.base_title
        and persisted.version == expected_version
    )
    semantic_ok = persisted.storage_sha256 == candidate_hash
    if not semantic_ok and semantic_verifier is not None:
        try:
            semantic_ok = semantic_verifier(persisted, manifest_path)
        except Exception:
            semantic_ok = False
    postcondition_ok = identity_and_version_ok and semantic_ok
    if not postcondition_ok:
        receipt = PushReceipt(
            status=SyncStatus.POSTCONDITION_FAILED,
            page_id=manifest.page_id,
            version=persisted.version,
            title=persisted.title,
            manifest_sha256=manifest_hash,
            base_version=manifest.base_version,
            candidate_sha256=candidate_hash,
            persisted_sha256=persisted.storage_sha256,
            response_version=response_version,
            reason_code=ReasonCode.POSTCONDITION_FAILED.value,
        )
        _write_receipt(run_dir / "push-receipt.json", receipt)
        raise PostconditionError(
            f"페이지 {manifest.page_id}의 persisted snapshot이 target과 다릅니다"
        )

    receipt = PushReceipt(
        status=SyncStatus.REMOTE_VERIFIED,
        page_id=manifest.page_id,
        version=persisted.version,
        title=persisted.title,
        manifest_sha256=manifest_hash,
        base_version=manifest.base_version,
        candidate_sha256=candidate_hash,
        persisted_sha256=persisted.storage_sha256,
        response_version=response_version,
    )
    _write_receipt(run_dir / "push-receipt.json", receipt)
    return receipt
