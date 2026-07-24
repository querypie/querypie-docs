"""검증된 SyncManifest만 소비하는 transaction-safe Confluence publisher."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from reverse_sync.manifest import (
    ArtifactTamperedError,
    load_sync_manifest,
    sha256_bytes,
    verify_manifest_integrity,
)
from reverse_sync.models import (
    AttachmentCatalog,
    PageSnapshot,
    PushReceipt,
    ReasonCode,
    SyncManifest,
    SyncStatus,
)


class PageGateway(Protocol):
    def get_current_page(self, page_id: str) -> PageSnapshot: ...

    def get_active_draft(self, page_id: str) -> PageSnapshot | None: ...

    def get_page_identity(self, page_id: str) -> PageSnapshot: ...

    def get_attachment_catalog(self, page_id: str) -> AttachmentCatalog: ...

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


class DependencyChangedError(PublishBlockedError):
    reason_code = ReasonCode.DEPENDENCY_FAILURE.value


@dataclass(frozen=True)
class RequiredLink:
    page_id: str
    content_title: str
    href: str


@dataclass(frozen=True)
class RequiredDependencies:
    attachment_filenames: tuple[str, ...] = ()
    links: tuple[RequiredLink, ...] = ()


def _write_snapshot(path: Path, snapshot: PageSnapshot) -> None:
    _write_json(path, snapshot.to_dict(include_body=True))


def _write_json(path: Path, value: dict) -> None:
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


def _required_dependencies(
    path: Path,
    manifest: SyncManifest,
) -> RequiredDependencies:
    proof_ref = manifest.artifact("local_proof")
    try:
        proof = json.loads((path.parent / proof_ref.path).read_text())
        if (
            proof.get("status") != SyncStatus.VERIFIED_LOCAL.value
            or proof.get("push_eligible") is not True
        ):
            raise TypeError("local proof status")
        dependencies = proof["dependencies"]
        catalog_sha256 = dependencies["attachment_catalog_sha256"]
        attachments = dependencies["attachments"]
        internal_links = dependencies["internal_links"]
        if not isinstance(attachments, list) or not isinstance(
            internal_links,
            list,
        ):
            raise TypeError("dependency list")
        filenames = []
        for item in attachments:
            attachment_id = item["attachment_id"]
            filename = item["filename"]
            version = item["version"]
            if (
                not isinstance(attachment_id, str)
                or not attachment_id
                or not isinstance(filename, str)
                or not filename
                or not isinstance(version, int)
                or isinstance(version, bool)
                or version < 1
            ):
                raise TypeError("filename")
            filenames.append(filename)
        links = []
        for item in internal_links:
            page_id = item["page_id"]
            content_title = item["content_title"]
            href = item["href"]
            if (
                not isinstance(page_id, str)
                or not page_id
                or not isinstance(content_title, str)
                or not content_title
                or not isinstance(href, str)
                or not href
            ):
                raise TypeError("internal link")
            links.append(
                RequiredLink(
                    page_id=page_id,
                    content_title=content_title,
                    href=href,
                )
            )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ArtifactTamperedError(
            "local proof dependency evidence 형식이 올바르지 않습니다"
        ) from exc
    if attachments and (
        not isinstance(catalog_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", catalog_sha256) is None
    ):
        raise ArtifactTamperedError(
            "local proof attachment catalog hash가 올바르지 않습니다"
        )
    if not attachments and catalog_sha256 != "":
        raise ArtifactTamperedError(
            "attachment requirement 없이 catalog hash가 기록되었습니다"
        )
    if len(filenames) != len(set(filenames)):
        raise ArtifactTamperedError(
            "local proof attachment requirement가 중복되었습니다"
        )
    unique_links = {
        (link.page_id, link.content_title, link.href): link
        for link in links
    }
    if len(unique_links) != len(links):
        raise ArtifactTamperedError(
            "local proof internal link requirement가 중복되었습니다"
        )
    titles_by_page: dict[str, set[str]] = {}
    for link in links:
        titles_by_page.setdefault(link.page_id, set()).add(link.content_title)
    if any(len(titles) != 1 for titles in titles_by_page.values()):
        raise ArtifactTamperedError(
            "같은 internal page dependency에 여러 title이 기록되었습니다"
        )
    return RequiredDependencies(
        attachment_filenames=tuple(sorted(filenames)),
        links=tuple(
            sorted(
                links,
                key=lambda item: (item.page_id, item.href, item.content_title),
            )
        ),
    )


def _assert_attachment_dependencies(
    required: tuple[str, ...],
    catalog: AttachmentCatalog,
    page_id: str,
) -> None:
    if catalog.page_id != page_id:
        raise DependencyChangedError(
            "preflight attachment catalog page ID가 manifest와 다릅니다"
        )
    available = {attachment.filename for attachment in catalog.attachments}
    missing = sorted(set(required) - available)
    if missing:
        raise DependencyChangedError(
            "verify 이후 attachment dependency가 사라졌습니다: "
            + ", ".join(missing)
        )


def _assert_link_dependency(
    required: RequiredLink,
    snapshot: PageSnapshot,
) -> None:
    if (
        snapshot.page_id != required.page_id
        or snapshot.status != "current"
        or snapshot.title != required.content_title
    ):
        raise DependencyChangedError(
            "verify 이후 internal link target identity가 바뀌었습니다: "
            f"{required.href}"
        )


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
    required_dependencies = _required_dependencies(
        manifest_path,
        manifest,
    )

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
    if required_dependencies.attachment_filenames:
        attachment_catalog = gateway.get_attachment_catalog(manifest.page_id)
        _write_json(
            run_dir / "preflight.attachments.json",
            attachment_catalog.to_dict(),
        )
        _assert_attachment_dependencies(
            required_dependencies.attachment_filenames,
            attachment_catalog,
            manifest.page_id,
        )
    if required_dependencies.links:
        page_snapshots: dict[str, PageSnapshot] = {}
        for required_link in required_dependencies.links:
            if required_link.page_id not in page_snapshots:
                page_snapshots[required_link.page_id] = (
                    gateway.get_page_identity(required_link.page_id)
                )
        _write_json(
            run_dir / "preflight.link-pages.json",
            {
                "pages": [
                    snapshot.to_dict(include_body=False)
                    for snapshot in sorted(
                        page_snapshots.values(),
                        key=lambda item: item.page_id,
                    )
                ]
            },
        )
        for required_link in required_dependencies.links:
            _assert_link_dependency(
                required_link,
                page_snapshots[required_link.page_id],
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
