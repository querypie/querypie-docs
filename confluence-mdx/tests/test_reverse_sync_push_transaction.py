"""검증한 snapshot과 Confluence PUT을 결합하는 transaction 계약 테스트."""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
import yaml

from reverse_sync.confluence_client import (
    ConfluenceConfig,
    ConfluenceGateway,
    InvalidDependencySnapshotError,
    InvalidPageSnapshotError,
    NetworkError,
    PermissionDeniedError,
    VersionConflictError,
    get_active_draft,
    get_attachment_catalog,
    get_page_snapshot,
    update_page,
)
from reverse_sync.base_parity import verify_base_parity, verify_source_identity
from reverse_sync.manifest import (
    ArtifactTamperedError,
    StaleVerificationError,
    create_sync_manifest,
    load_sync_manifest,
)
from reverse_sync.models import (
    AttachmentCatalog,
    AttachmentRecord,
    PageSnapshot,
    SyncStatus,
    VerificationGate,
)
from reverse_sync.publisher import (
    ActiveDraftError,
    DependencyChangedError,
    PostconditionError,
    RemoteDriftError,
    publish_verified_manifest,
)
from reverse_sync.proof import REQUIRED_LOCAL_GATES
from reverse_sync_cli import MdxSource, _do_verify, run_verify


NOW = datetime(2026, 7, 24, tzinfo=timezone.utc)


def _snapshot(
    *,
    page_id: str = "123",
    version: int = 5,
    title: str = "Test page",
    body: str = "<p>Before</p>",
    status: str = "current",
) -> PageSnapshot:
    return PageSnapshot(
        page_id=page_id,
        status=status,
        title=title,
        version=version,
        storage_xhtml=body,
        fetched_at=NOW.isoformat(),
        api="confluence-v2",
    )


def _write_page_catalog(tmp_path: Path, page_id: str = "123") -> None:
    var_dir = tmp_path / "var"
    var_dir.mkdir(parents=True, exist_ok=True)
    (var_dir / "pages.qm.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "page_id": page_id,
                    "title_orig": "Test page",
                    "path": ["test"],
                }
            ],
            allow_unicode=True,
        )
    )


def _source_mdx(body: str, page_id: str = "123") -> str:
    return (
        "---\n"
        "title: 'Test page'\n"
        f"confluenceUrl: 'https://example.atlassian.net/wiki/pages/{page_id}'\n"
        "---\n\n"
        "# Test page\n\n"
        f"{body}"
    )


def _manifest(
    tmp_path: Path,
    base: PageSnapshot | None = None,
    *,
    required_attachment: str = "",
    required_link: tuple[str, str, str] | None = None,
    malformed_attachment_evidence: bool = False,
) -> Path:
    attachments = []
    if required_attachment:
        attachments.append(
            {
                "attachment_id": "att-1",
                "filename": required_attachment,
                "version": 1,
            }
        )
        if malformed_attachment_evidence:
            attachments[0].pop("attachment_id")
    internal_links = []
    if required_link is not None:
        page_id, content_title, href = required_link
        internal_links.append(
            {
                "content_title": content_title,
                "href": href,
                "page_id": page_id,
            }
        )
    local_proof = json.dumps(
        {
            "dependencies": {
                "attachment_catalog_sha256": "0" * 64 if attachments else "",
                "attachments": attachments,
                "internal_links": internal_links,
            },
            "push_eligible": True,
            "status": "verified_local",
        },
        separators=(",", ":"),
        sort_keys=True,
    ) + "\n"
    return create_sync_manifest(
        runs_dir=tmp_path / "reverse-sync",
        base=base or _snapshot(),
        original_mdx="# Test page\n\nBefore\n",
        original_descriptor="main:src/content/ko/test.mdx",
        improved_mdx="# Test page\n\nAfter\n",
        improved_descriptor="src/content/ko/test.mdx",
        patch_plan='{"schema_version":1}\n',
        candidate_xhtml="<p>After</p>",
        local_proof=local_proof,
        verifier_policy="reverse-sync-equivalence-v1",
        tool_version="reverse-sync-cli-v3",
        push_eligible=True,
        gates=tuple(
            VerificationGate(name, True)
            for name in REQUIRED_LOCAL_GATES
        ),
    )


class FakeGateway:
    def __init__(
        self,
        current_snapshots: list[PageSnapshot],
        *,
        draft: PageSnapshot | None = None,
        update_error: Exception | None = None,
        attachment_catalog: AttachmentCatalog | None = None,
        linked_pages: dict[str, PageSnapshot] | None = None,
    ):
        self.current_snapshots = list(current_snapshots)
        self.draft = draft
        self.update_error = update_error
        self.attachment_catalog = attachment_catalog
        self.linked_pages = linked_pages or {}
        self.current_calls = 0
        self.draft_calls = 0
        self.attachment_calls = 0
        self.link_calls: list[str] = []
        self.update_calls: list[dict] = []

    def get_current_page(self, page_id: str) -> PageSnapshot:
        snapshot = self.current_snapshots[self.current_calls]
        self.current_calls += 1
        assert snapshot.page_id == page_id
        return snapshot

    def get_active_draft(self, page_id: str) -> PageSnapshot | None:
        self.draft_calls += 1
        if self.draft is not None:
            assert self.draft.page_id == page_id
        return self.draft

    def get_attachment_catalog(self, page_id: str) -> AttachmentCatalog:
        self.attachment_calls += 1
        assert self.attachment_catalog is not None
        assert self.attachment_catalog.page_id == page_id
        return self.attachment_catalog

    def get_page_identity(self, page_id: str) -> PageSnapshot:
        self.link_calls.append(page_id)
        return self.linked_pages[page_id]

    def update_page(
        self,
        page_id: str,
        *,
        title: str,
        version: int,
        xhtml_body: str,
    ) -> dict:
        self.update_calls.append(
            {
                "page_id": page_id,
                "title": title,
                "version": version,
                "xhtml_body": xhtml_body,
            }
        )
        if self.update_error is not None:
            raise self.update_error
        return {"id": page_id, "version": {"number": version}, "title": title}


def test_manifest_is_deterministic_and_uses_run_scoped_artifacts(tmp_path):
    first = _manifest(tmp_path / "first")
    second = _manifest(tmp_path / "second")

    assert first.parent.name == second.parent.name
    assert first.name == "manifest.json"
    assert first.read_bytes() == second.read_bytes()
    assert (first.parent / "base.xhtml").read_text() == "<p>Before</p>"
    assert (first.parent / "candidate.xhtml").read_text() == "<p>After</p>"


def test_candidate_tampering_blocks_before_remote_read(tmp_path):
    manifest_path = _manifest(tmp_path)
    (manifest_path.parent / "candidate.xhtml").write_text("<p>Tampered</p>")
    gateway = FakeGateway([_snapshot()])

    with pytest.raises(ArtifactTamperedError, match="candidate.xhtml"):
        publish_verified_manifest(manifest_path, gateway)

    assert gateway.current_calls == 0
    assert gateway.update_calls == []


@pytest.mark.parametrize("artifact_name", ["patch-plan.json", "local-proof.json"])
def test_proof_artifact_tampering_blocks_before_remote_read(
    tmp_path, artifact_name
):
    manifest_path = _manifest(tmp_path)
    (manifest_path.parent / artifact_name).write_text('{"tampered":true}\n')
    gateway = FakeGateway([_snapshot()])

    with pytest.raises(ArtifactTamperedError, match=artifact_name):
        publish_verified_manifest(manifest_path, gateway)

    assert gateway.current_calls == 0
    assert gateway.update_calls == []


def test_malformed_dependency_evidence_blocks_before_remote_read(tmp_path):
    manifest_path = _manifest(
        tmp_path,
        required_attachment="screen.png",
        malformed_attachment_evidence=True,
    )
    gateway = FakeGateway([_snapshot()])

    with pytest.raises(ArtifactTamperedError, match="dependency evidence"):
        publish_verified_manifest(manifest_path, gateway)

    assert gateway.current_calls == 0
    assert gateway.update_calls == []


def test_remote_drift_blocks_without_adopting_latest_version(tmp_path):
    manifest_path = _manifest(tmp_path)
    remote_edit = _snapshot(version=6, body="<p>Remote edit</p>")
    gateway = FakeGateway([remote_edit])

    with pytest.raises(RemoteDriftError) as exc_info:
        publish_verified_manifest(manifest_path, gateway)

    assert exc_info.value.reason_code == "remote_drift"
    assert gateway.current_calls == 1
    assert gateway.update_calls == []


def test_title_drift_blocks_even_if_version_and_body_match(tmp_path):
    manifest_path = _manifest(tmp_path)
    renamed = _snapshot(title="Renamed")
    gateway = FakeGateway([renamed])

    with pytest.raises(RemoteDriftError, match="title"):
        publish_verified_manifest(manifest_path, gateway)

    assert gateway.update_calls == []


def test_active_draft_blocks_before_put(tmp_path):
    manifest_path = _manifest(tmp_path)
    draft = _snapshot(version=6, status="draft", body="<p>Draft edit</p>")
    gateway = FakeGateway([_snapshot()], draft=draft)

    with pytest.raises(ActiveDraftError) as exc_info:
        publish_verified_manifest(manifest_path, gateway)

    assert exc_info.value.reason_code == "active_draft"
    assert gateway.update_calls == []


def test_missing_attachment_at_preflight_blocks_before_put(tmp_path):
    manifest_path = _manifest(
        tmp_path,
        required_attachment="screen.png",
    )
    catalog = AttachmentCatalog(
        page_id="123",
        attachments=(),
        fetched_at=NOW.isoformat(),
        api="fixture",
    )
    gateway = FakeGateway(
        [_snapshot()],
        attachment_catalog=catalog,
    )

    with pytest.raises(DependencyChangedError) as exc_info:
        publish_verified_manifest(manifest_path, gateway)

    assert exc_info.value.reason_code == "dependency_failure"
    assert gateway.attachment_calls == 1
    assert gateway.update_calls == []
    assert (manifest_path.parent / "preflight.attachments.json").is_file()


def test_existing_attachment_at_preflight_allows_put(tmp_path):
    manifest_path = _manifest(
        tmp_path,
        required_attachment="screen.png",
    )
    catalog = AttachmentCatalog(
        page_id="123",
        attachments=(
            AttachmentRecord(
                attachment_id="att-1",
                page_id="123",
                filename="screen.png",
                version=2,
            ),
        ),
        fetched_at=NOW.isoformat(),
        api="fixture",
    )
    gateway = FakeGateway(
        [
            _snapshot(),
            _snapshot(version=6, body="<p>After</p>"),
        ],
        attachment_catalog=catalog,
    )

    receipt = publish_verified_manifest(manifest_path, gateway)

    assert receipt.status is SyncStatus.REMOTE_VERIFIED
    assert gateway.attachment_calls == 1
    assert len(gateway.update_calls) == 1


def test_internal_link_target_at_preflight_allows_put(tmp_path):
    manifest_path = _manifest(
        tmp_path,
        required_link=("456", "Target page", "./target"),
    )
    gateway = FakeGateway(
        [
            _snapshot(),
            _snapshot(version=6, body="<p>After</p>"),
        ],
        linked_pages={
            "456": _snapshot(
                page_id="456",
                version=3,
                title="Target page",
                body="<p>Target</p>",
            )
        },
    )

    receipt = publish_verified_manifest(manifest_path, gateway)

    assert receipt.status is SyncStatus.REMOTE_VERIFIED
    assert gateway.link_calls == ["456"]
    assert (manifest_path.parent / "preflight.link-pages.json").is_file()
    assert len(gateway.update_calls) == 1


def test_changed_internal_link_target_blocks_before_put(tmp_path):
    manifest_path = _manifest(
        tmp_path,
        required_link=("456", "Target page", "./target"),
    )
    gateway = FakeGateway(
        [_snapshot()],
        linked_pages={
            "456": _snapshot(
                page_id="456",
                version=4,
                title="Renamed target",
                body="<p>Target</p>",
            )
        },
    )

    with pytest.raises(DependencyChangedError, match="internal link"):
        publish_verified_manifest(manifest_path, gateway)

    assert gateway.link_calls == ["456"]
    assert gateway.update_calls == []
    assert (manifest_path.parent / "preflight.link-pages.json").is_file()


def test_preflight_put_race_is_not_retried_with_latest_version(tmp_path):
    manifest_path = _manifest(tmp_path)
    gateway = FakeGateway(
        [_snapshot()],
        update_error=VersionConflictError("concurrent update"),
    )

    with pytest.raises(VersionConflictError):
        publish_verified_manifest(manifest_path, gateway)

    assert gateway.current_calls == 1
    assert len(gateway.update_calls) == 1
    assert gateway.update_calls[0]["version"] == 6


def test_put_uses_manifest_candidate_and_base_version_plus_one(tmp_path):
    base = _snapshot()
    manifest_path = _manifest(tmp_path, base)
    persisted = replace(base, version=6, storage_xhtml="<p>After</p>")
    gateway = FakeGateway([base, persisted])

    receipt = publish_verified_manifest(manifest_path, gateway)

    assert receipt.status is SyncStatus.REMOTE_VERIFIED
    assert receipt.version == 6
    assert gateway.update_calls == [
        {
            "page_id": "123",
            "title": "Test page",
            "version": 6,
            "xhtml_body": "<p>After</p>",
        }
    ]


def test_postcondition_mismatch_preserves_failure_evidence(tmp_path):
    base = _snapshot()
    manifest_path = _manifest(tmp_path, base)
    persisted = replace(base, version=6, storage_xhtml="<p>Unexpected</p>")
    gateway = FakeGateway([base, persisted])

    with pytest.raises(PostconditionError) as exc_info:
        publish_verified_manifest(manifest_path, gateway)

    assert exc_info.value.reason_code == "postcondition_failed"
    receipt_path = manifest_path.parent / "push-receipt.json"
    post_path = manifest_path.parent / "post.snapshot.json"
    assert receipt_path.exists()
    assert post_path.exists()
    assert (manifest_path.parent / "update.response.json").exists()
    assert '"status":"postcondition_failed"' in receipt_path.read_text()
    assert "<p>Unexpected</p>" in post_path.read_text()


def test_semantically_equivalent_persisted_body_satisfies_postcondition(tmp_path):
    base = _snapshot()
    manifest_path = _manifest(tmp_path, base)
    canonicalized = replace(base, version=6, storage_xhtml="<p>After</p>\n")
    gateway = FakeGateway([base, canonicalized])
    verifier_calls = []

    def semantic_verifier(snapshot, verified_manifest_path):
        verifier_calls.append((snapshot, verified_manifest_path))
        return snapshot.storage_xhtml.strip() == "<p>After</p>"

    receipt = publish_verified_manifest(
        manifest_path,
        gateway,
        semantic_verifier=semantic_verifier,
    )

    assert receipt.status is SyncStatus.REMOTE_VERIFIED
    assert verifier_calls == [(canonicalized, manifest_path)]


def test_already_applied_candidate_skips_put(tmp_path):
    manifest_path = _manifest(tmp_path)
    already_applied = _snapshot(version=6, body="<p>After</p>")
    gateway = FakeGateway([already_applied])

    receipt = publish_verified_manifest(manifest_path, gateway)

    assert receipt.status is SyncStatus.ALREADY_APPLIED
    assert receipt.version == 6
    assert gateway.draft_calls == 1
    assert gateway.update_calls == []


def test_semantically_already_applied_remote_skips_put(tmp_path):
    manifest_path = _manifest(tmp_path)
    already_applied = _snapshot(version=6, body="<p>After</p>\n")
    gateway = FakeGateway([already_applied])

    receipt = publish_verified_manifest(
        manifest_path,
        gateway,
        semantic_verifier=lambda snapshot, _path: snapshot.storage_xhtml.strip()
        == "<p>After</p>",
    )

    assert receipt.status is SyncStatus.ALREADY_APPLIED
    assert gateway.update_calls == []


def test_unverified_manifest_cannot_be_published(tmp_path):
    manifest_path = _manifest(tmp_path)
    manifest = load_sync_manifest(manifest_path)
    unverified = replace(manifest, push_eligible=False)
    manifest_path.write_text(unverified.to_canonical_json())
    gateway = FakeGateway([_snapshot()])

    with pytest.raises(ArtifactTamperedError, match="push eligible"):
        publish_verified_manifest(manifest_path, gateway)

    assert gateway.current_calls == 0


def test_stale_tool_version_requires_reverification(tmp_path):
    manifest_path = _manifest(tmp_path)
    manifest = load_sync_manifest(manifest_path)
    stale = replace(manifest, tool_version="reverse-sync-cli-v0")
    manifest_path.write_text(stale.to_canonical_json())

    with pytest.raises(StaleVerificationError, match="tool version"):
        load_sync_manifest(manifest_path)


def test_manifest_never_contains_credentials(tmp_path):
    manifest_path = _manifest(tmp_path)
    serialized_run = "".join(
        path.read_text()
        for path in manifest_path.parent.iterdir()
        if path.is_file()
    )

    assert "person@example.com" not in serialized_run
    assert "secret-api-token" not in serialized_run
    assert "Authorization" not in serialized_run


def test_push_manifest_requires_all_local_proof_gates(tmp_path):
    with pytest.raises(StaleVerificationError, match="required gate"):
        create_sync_manifest(
            runs_dir=tmp_path / "reverse-sync",
            base=_snapshot(),
            original_mdx="# Test page\n\nBefore\n",
            original_descriptor="main:src/content/ko/test.mdx",
            improved_mdx="# Test page\n\nAfter\n",
            improved_descriptor="src/content/ko/test.mdx",
            patch_plan='{"schema_version":1}\n',
            candidate_xhtml="<p>After</p>",
            local_proof=(
                '{"dependencies":{"attachments":[],"internal_links":[],'
                '"attachment_catalog_sha256":""},"push_eligible":true,'
                '"status":"verified_local"}\n'
            ),
            verifier_policy="reverse-sync-equivalence-v1",
            tool_version="reverse-sync-cli-v3",
            push_eligible=True,
            gates=(VerificationGate("semantic_roundtrip", True),),
        )


def test_v2_snapshot_uses_one_response_for_version_title_and_body():
    response = MagicMock()
    response.json.return_value = {
        "id": "123",
        "status": "current",
        "title": "Test page",
        "version": {"number": 5},
        "body": {
            "storage": {
                "representation": "storage",
                "value": "<p>Before</p>",
            }
        },
    }
    response.raise_for_status.return_value = None

    with patch("reverse_sync.confluence_client.requests.get", return_value=response) as get:
        snapshot = get_page_snapshot(
            ConfluenceConfig(base_url="https://example.atlassian.net/wiki", email="e", api_token="t"),
            "123",
            fetched_at=NOW,
        )

    get.assert_called_once()
    assert get.call_args.args[0] == "https://example.atlassian.net/wiki/api/v2/pages/123"
    assert get.call_args.kwargs["params"] == {
        "body-format": "storage",
        "status": ["current"],
        "include-version": True,
    }
    assert snapshot.version == 5
    assert snapshot.title == "Test page"
    assert snapshot.storage_xhtml == "<p>Before</p>"
    assert len(snapshot.storage_sha256) == 64


def test_v2_attachment_catalog_reads_every_page():
    first = MagicMock()
    first.json.return_value = {
        "results": [
            {
                "id": "a1",
                "status": "current",
                "title": "first.png",
                "pageId": "123",
                "version": {"number": 2},
            }
        ]
    }
    first.raise_for_status.return_value = None
    first.links = {
        "next": {
            "url": (
                "https://example.atlassian.net/wiki/api/v2/pages/"
                "123/attachments?cursor=next"
            )
        }
    }
    second = MagicMock()
    second.json.return_value = {
        "results": [
            {
                "id": "a2",
                "status": "current",
                "title": "second.png",
                "pageId": "123",
                "version": {"number": 1},
            }
        ]
    }
    second.raise_for_status.return_value = None
    second.links = {}

    with patch(
        "reverse_sync.confluence_client.requests.get",
        side_effect=[first, second],
    ) as get:
        catalog = get_attachment_catalog(
            ConfluenceConfig(
                base_url="https://example.atlassian.net/wiki",
                email="e",
                api_token="t",
            ),
            "123",
            fetched_at=NOW,
        )

    assert [item.filename for item in catalog.attachments] == [
        "first.png",
        "second.png",
    ]
    assert get.call_count == 2
    assert get.call_args_list[0].kwargs["params"] == {
        "status": ["current"],
        "limit": 250,
    }
    assert get.call_args_list[1].kwargs["params"] is None


def test_v2_attachment_catalog_rejects_cross_page_item():
    response = MagicMock()
    response.json.return_value = {
        "results": [
            {
                "id": "a1",
                "status": "current",
                "title": "screen.png",
                "pageId": "999",
                "version": {"number": 1},
            }
        ]
    }
    response.raise_for_status.return_value = None
    response.links = {}

    with patch(
        "reverse_sync.confluence_client.requests.get",
        return_value=response,
    ), pytest.raises(InvalidDependencySnapshotError):
        get_attachment_catalog(
            ConfluenceConfig(
                base_url="https://example.atlassian.net/wiki",
                email="e",
                api_token="t",
            ),
            "123",
            fetched_at=NOW,
        )


def test_v2_attachment_catalog_rejects_cross_origin_pagination():
    response = MagicMock()
    response.json.return_value = {"results": []}
    response.raise_for_status.return_value = None
    response.links = {
        "next": {
            "url": "https://attacker.example/api/v2/pages/123/attachments"
        }
    }

    with patch(
        "reverse_sync.confluence_client.requests.get",
        return_value=response,
    ), pytest.raises(InvalidDependencySnapshotError, match="범위를 벗어납니다"):
        get_attachment_catalog(
            ConfluenceConfig(
                base_url="https://example.atlassian.net/wiki",
                email="e",
                api_token="t",
            ),
            "123",
            fetched_at=NOW,
        )


def test_linked_page_not_found_maps_to_dependency_failure():
    response = MagicMock()
    response.status_code = 404
    response.raise_for_status.side_effect = requests.HTTPError(response=response)
    gateway = ConfluenceGateway(
        ConfluenceConfig(
            base_url="https://example.atlassian.net/wiki",
            email="e",
            api_token="t",
        )
    )

    with patch(
        "reverse_sync.confluence_client.requests.get",
        return_value=response,
    ), pytest.raises(InvalidDependencySnapshotError) as exc_info:
        gateway.get_page_identity("456")

    assert exc_info.value.reason_code == "dependency_failure"


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "different", "status": "current", "title": "T", "version": {"number": 1}},
        {"id": "123", "status": "draft", "title": "T", "version": {"number": 1}},
        {
            "id": "123",
            "status": "current",
            "title": "T",
            "version": {"number": True},
            "body": {
                "storage": {
                    "representation": "storage",
                    "value": "<p>x</p>",
                }
            },
        },
        {
            "id": "123",
            "status": "current",
            "title": "T",
            "version": {"number": 1},
            "body": {"storage": {"representation": "view", "value": "<p>x</p>"}},
        },
    ],
)
def test_invalid_v2_snapshot_is_fail_closed(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None

    with patch("reverse_sync.confluence_client.requests.get", return_value=response):
        with pytest.raises(InvalidPageSnapshotError):
            get_page_snapshot(
                ConfluenceConfig(base_url="https://example.atlassian.net/wiki", email="e", api_token="t"),
                "123",
                fetched_at=NOW,
            )


def test_v2_snapshot_maps_conflict_without_retry():
    response = MagicMock()
    response.status_code = 409
    response.raise_for_status.side_effect = requests.HTTPError(response=response)

    with patch("reverse_sync.confluence_client.requests.get", return_value=response) as get:
        with pytest.raises(VersionConflictError):
            get_page_snapshot(
                ConfluenceConfig(base_url="https://example.atlassian.net/wiki", email="e", api_token="t"),
                "123",
                fetched_at=NOW,
            )

    get.assert_called_once()


def test_v2_active_draft_adapter_parses_draft_snapshot():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "id": "123",
        "status": "draft",
        "title": "Test page",
        "version": {"number": 6},
        "body": {
            "storage": {
                "representation": "storage",
                "value": "<p>Draft</p>",
            }
        },
    }
    response.raise_for_status.return_value = None

    with patch("reverse_sync.confluence_client.requests.get", return_value=response) as get:
        snapshot = get_active_draft(
            ConfluenceConfig(base_url="https://example.atlassian.net/wiki", email="e", api_token="t"),
            "123",
            fetched_at=NOW,
        )

    assert snapshot is not None
    assert snapshot.status == "draft"
    assert snapshot.storage_xhtml == "<p>Draft</p>"
    assert get.call_args.kwargs["params"]["get-draft"] is True
    assert get.call_args.kwargs["params"]["status"] == ["draft"]


def test_v2_active_draft_adapter_returns_none_on_not_found():
    response = MagicMock()
    response.status_code = 404

    with patch("reverse_sync.confluence_client.requests.get", return_value=response) as get:
        snapshot = get_active_draft(
            ConfluenceConfig(base_url="https://example.atlassian.net/wiki", email="e", api_token="t"),
            "123",
            fetched_at=NOW,
        )

    assert snapshot is None
    get.assert_called_once()


def test_v2_update_uses_exact_requested_version_and_candidate_once():
    response = MagicMock()
    response.json.return_value = {
        "id": "123",
        "title": "Test page",
        "version": {"number": 6},
    }
    response.raise_for_status.return_value = None
    config = ConfluenceConfig(
        base_url="https://example.atlassian.net/wiki",
        email="e",
        api_token="t",
    )

    with patch(
        "reverse_sync.confluence_client.requests.request",
        return_value=response,
    ) as request:
        update_page(
            config,
            "123",
            title="Test page",
            version=6,
            xhtml_body="<p>After</p>",
        )

    request.assert_called_once()
    assert request.call_args.args[:2] == (
        "PUT",
        "https://example.atlassian.net/wiki/api/v2/pages/123",
    )
    assert request.call_args.kwargs["json"]["version"] == {"number": 6}
    assert request.call_args.kwargs["json"]["body"]["value"] == "<p>After</p>"


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (400, VersionConflictError),
        (409, VersionConflictError),
        (403, PermissionDeniedError),
    ],
)
def test_v2_update_maps_provider_errors(status_code, expected_error):
    response = MagicMock()
    response.status_code = status_code
    response.raise_for_status.side_effect = requests.HTTPError(response=response)
    config = ConfluenceConfig(
        base_url="https://example.atlassian.net/wiki",
        email="e",
        api_token="t",
    )

    with patch(
        "reverse_sync.confluence_client.requests.request",
        return_value=response,
    ) as request:
        with pytest.raises(expected_error):
            update_page(
                config,
                "123",
                title="Test page",
                version=6,
                xhtml_body="<p>After</p>",
            )

    request.assert_called_once()


def test_v2_update_maps_network_error_without_retry():
    config = ConfluenceConfig(
        base_url="https://example.atlassian.net/wiki",
        email="e",
        api_token="t",
    )

    with patch(
        "reverse_sync.confluence_client.requests.request",
        side_effect=requests.Timeout("timeout"),
    ) as request:
        with pytest.raises(NetworkError):
            update_page(
                config,
                "123",
                title="Test page",
                version=6,
                xhtml_body="<p>After</p>",
            )

    request.assert_called_once()


def test_prepare_push_fetches_one_snapshot_and_passes_it_to_verify():
    args = argparse.Namespace(
        improved_mdx="src/content/ko/test.mdx",
        original_mdx=None,
        page_id=None,
        page_dir=None,
        lenient=False,
        no_normalize=False,
    )
    base = _snapshot()
    improved = MdxSource("# Test page\n\nAfter\n", "src/content/ko/test.mdx")
    original = MdxSource("# Test page\n\nBefore\n", "main:src/content/ko/test.mdx")
    expected = {
        "status": "verified_local",
        "page_id": "123",
        "push_eligible": True,
    }

    with patch(
        "reverse_sync_cli._resolve_mdx_source",
        side_effect=[improved, original],
    ), patch(
        "reverse_sync_cli._resolve_page_id",
        return_value="123",
    ), patch(
        "reverse_sync.confluence_client.get_page_snapshot",
        return_value=base,
    ) as get_snapshot, patch(
        "reverse_sync_cli.run_verify",
        return_value=expected,
    ) as verify:
        result = _do_verify(args, config=MagicMock(), prepare_push=True)

    assert result == expected
    get_snapshot.assert_called_once()
    assert verify.call_args.kwargs["base_snapshot"] is base
    assert verify.call_args.kwargs["for_push"] is True


def test_prepare_push_fetches_attachment_catalog_for_new_reference():
    args = argparse.Namespace(
        improved_mdx="src/content/ko/test.mdx",
        original_mdx=None,
        page_id=None,
        page_dir=None,
        lenient=False,
        no_normalize=False,
    )
    base = _snapshot()
    improved = MdxSource(
        "# Test page\n\nBefore\n\n![screen](./screen.png)\n",
        "src/content/ko/test.mdx",
    )
    original = MdxSource(
        "# Test page\n\nBefore\n",
        "main:src/content/ko/test.mdx",
    )
    catalog = AttachmentCatalog(
        page_id="123",
        attachments=(
            AttachmentRecord(
                attachment_id="att-1",
                page_id="123",
                filename="screen.png",
                version=1,
            ),
        ),
        fetched_at=NOW.isoformat(),
        api="fixture",
    )

    with patch(
        "reverse_sync_cli._resolve_mdx_source",
        side_effect=[improved, original],
    ), patch(
        "reverse_sync_cli._resolve_page_id",
        return_value="123",
    ), patch(
        "reverse_sync.confluence_client.get_page_snapshot",
        return_value=base,
    ), patch(
        "reverse_sync.confluence_client.get_attachment_catalog",
        return_value=catalog,
    ) as get_catalog, patch(
        "reverse_sync_cli.run_verify",
        return_value={"status": "verified_local"},
    ) as verify:
        _do_verify(args, config=MagicMock(), prepare_push=True)

    get_catalog.assert_called_once()
    assert verify.call_args.kwargs["attachment_catalog"] is catalog


def test_online_verify_builds_manifest_from_remote_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    _write_page_catalog(tmp_path, page_id)
    base = _snapshot(
        title="Test page",
        body="<h2>Section</h2><p>Before</p>",
    )
    original = _source_mdx("## Section\n\nBefore\n", page_id)
    improved = _source_mdx("## Section\n\nAfter\n", page_id)

    def forward_convert(input_path, output_path, _page_id, **_kwargs):
        content = original if Path(output_path).name == "reverse-sync.base.mdx" else improved
        Path(output_path).write_text(content)
        return content

    with patch("reverse_sync_cli._forward_convert", side_effect=forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(original, "main:src/content/ko/test.mdx"),
            improved_src=MdxSource(improved, "src/content/ko/test.mdx"),
            base_snapshot=base,
            for_push=True,
        )

    assert result["status"] == "verified_local"
    assert result["push_eligible"] is True
    assert result["base_version"] == 5
    assert result["base_storage_sha256"] == base.storage_sha256
    assert len(result["candidate_sha256"]) == 64
    assert any(
        gate["name"] == "semantic_roundtrip" and gate["passed"]
        for gate in result["local_gates"]
    )
    manifest_path = Path(result["manifest_path"])
    assert manifest_path.is_file()
    manifest = load_sync_manifest(manifest_path)
    assert manifest.base_version == 5
    assert manifest.base_storage_sha256 == base.storage_sha256
    assert manifest.verifier_policy == "reverse-sync-equivalence-v1"
    assert manifest.tool_version == "reverse-sync-cli-v3"
    assert (manifest_path.parent / "patch-plan.json").is_file()
    assert (manifest_path.parent / "local-proof.json").is_file()
    assert (manifest_path.parent / "candidate.xhtml").read_text() == (
        tmp_path / "var" / page_id / "reverse-sync.patched.xhtml"
    ).read_text()


def test_online_verify_proves_insert_idempotent_by_replanning(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    _write_page_catalog(tmp_path, page_id)
    base = _snapshot(
        title="Test page",
        body="<h2>Section</h2><p>Before</p>",
    )
    original = _source_mdx("## Section\n\nBefore\n", page_id)
    improved = _source_mdx("## Section\n\nBefore\n\nAdded\n", page_id)

    def forward_convert(input_path, output_path, _page_id, **_kwargs):
        content = original if Path(output_path).name == "reverse-sync.base.mdx" else improved
        Path(output_path).write_text(content)
        return content

    with patch("reverse_sync_cli._forward_convert", side_effect=forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(original, "main:src/content/ko/test.mdx"),
            improved_src=MdxSource(improved, "src/content/ko/test.mdx"),
            base_snapshot=base,
            for_push=True,
        )

    assert result["status"] == "verified_local"
    assert result["push_eligible"] is True
    idempotency = next(
        gate for gate in result["local_gates"] if gate["name"] == "idempotency"
    )
    assert idempotency["passed"] is True


def test_online_verify_renders_new_internal_link_as_confluence_macro(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    _write_page_catalog(tmp_path, page_id)
    pages_path = tmp_path / "var" / "pages.qm.yaml"
    pages = yaml.safe_load(pages_path.read_text())
    pages.append(
        {
            "page_id": "456",
            "title_orig": "Target page",
            "path": ["target"],
        }
    )
    pages_path.write_text(yaml.safe_dump(pages, allow_unicode=True))
    base = _snapshot(
        title="Test page",
        body="<h2>Section</h2><p>Before</p>",
    )
    original = _source_mdx("## Section\n\nBefore\n", page_id)
    improved = _source_mdx(
        "## Section\n\nBefore\n\n[Target](target)\n",
        page_id,
    )

    def forward_convert(_input_path, output_path, _page_id, **_kwargs):
        content = (
            original
            if Path(output_path).name == "reverse-sync.base.mdx"
            else improved
        )
        Path(output_path).write_text(content)
        return content

    with patch("reverse_sync_cli._forward_convert", side_effect=forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(
                original,
                "main:src/content/ko/test.mdx",
            ),
            improved_src=MdxSource(
                improved,
                "src/content/ko/test.mdx",
            ),
            base_snapshot=base,
            for_push=True,
        )

    assert result["status"] == "verified_local"
    candidate = Path(result["manifest_path"]).parent / "candidate.xhtml"
    assert (
        '<ri:page ri:content-title="Target page"></ri:page>'
        in candidate.read_text()
    )


def test_online_verify_renders_existing_attachment_reference(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    _write_page_catalog(tmp_path, page_id)
    base = _snapshot(
        title="Test page",
        body="<h2>Section</h2><p>Before</p>",
    )
    original = _source_mdx("## Section\n\nBefore\n", page_id)
    improved = _source_mdx(
        '## Section\n\nBefore\n\n<figure><img src="./screen.png" /></figure>\n',
        page_id,
    )
    catalog = AttachmentCatalog(
        page_id=page_id,
        attachments=(
            AttachmentRecord(
                attachment_id="att-1",
                page_id=page_id,
                filename="screen.png",
                version=3,
            ),
        ),
        fetched_at=NOW.isoformat(),
        api="fixture",
    )

    def forward_convert(_input_path, output_path, _page_id, **_kwargs):
        content = (
            original
            if Path(output_path).name == "reverse-sync.base.mdx"
            else improved
        )
        Path(output_path).write_text(content)
        return content

    with patch("reverse_sync_cli._forward_convert", side_effect=forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(
                original,
                "main:src/content/ko/test.mdx",
            ),
            improved_src=MdxSource(
                improved,
                "src/content/ko/test.mdx",
            ),
            base_snapshot=base,
            attachment_catalog=catalog,
            for_push=True,
        )

    assert result["status"] == "verified_local"
    run_dir = Path(result["manifest_path"]).parent
    candidate = (run_dir / "candidate.xhtml").read_text()
    proof = json.loads((run_dir / "local-proof.json").read_text())
    assert '<ri:attachment ri:filename="screen.png">' in candidate
    assert proof["dependencies"]["attachments"] == [
        {
            "attachment_id": "att-1",
            "filename": "screen.png",
            "version": 3,
        }
    ]


def test_online_verify_blocks_stale_original_before_patch(tmp_path, monkeypatch):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    _write_page_catalog(tmp_path, page_id)
    base = _snapshot(title="Test page", body="<p>Remote edit</p>")
    original = _source_mdx("Before\n", page_id)
    improved = _source_mdx("After\n", page_id)

    def forward_convert(_input_path, output_path, _page_id, **_kwargs):
        converted = _source_mdx("Remote edit\n", page_id)
        Path(output_path).write_text(converted)
        return converted

    with patch("reverse_sync_cli._forward_convert", side_effect=forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(original, "main:src/content/ko/test.mdx"),
            improved_src=MdxSource(improved, "src/content/ko/test.mdx"),
            base_snapshot=base,
            for_push=True,
        )

    assert result["status"] == "blocked"
    assert result["reason_code"] == "base_parity_mismatch"
    assert result["push_eligible"] is False
    assert not (tmp_path / "var" / page_id / "reverse-sync.patched.xhtml").exists()


def test_push_base_parity_does_not_hide_visible_spacing():
    result = verify_base_parity(
        _snapshot(title="Test page"),
        "# Test page\n\nVisible  spacing\n",
        "# Test page\n\nVisible spacing\n",
    )

    assert result.passed is False
    assert result.reason_code == "base_parity_mismatch"


def test_source_identity_ignores_h1_like_shell_comments():
    original = """---
title: Test page
---

```bash
# old shell comment
```

# Test page
"""
    improved = original.replace("# old shell comment", "# new shell comment")

    result = verify_source_identity(
        _snapshot(title="Test page"),
        original,
        improved,
    )

    assert result.passed is True


def test_online_verify_blocks_title_change(tmp_path, monkeypatch):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    base = _snapshot(title="Test page")

    result = run_verify(
        page_id=page_id,
        original_src=MdxSource("# Test page\n\nBefore\n", "original.mdx"),
        improved_src=MdxSource("# Renamed\n\nBefore\n", "improved.mdx"),
        base_snapshot=base,
        for_push=True,
    )

    assert result["status"] == "blocked"
    assert result["reason_code"] == "title_change_unsupported"
    assert result["push_eligible"] is False


def test_lenient_match_is_diagnostic_and_never_grants_push_eligibility(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    _write_page_catalog(tmp_path, page_id)
    base = _snapshot(
        title="Test page",
        body="<h2>Section</h2><p>Before</p>",
    )
    original = _source_mdx("## Section\n\nBefore\n", page_id)
    improved = _source_mdx("## Section\n\n2024년 01월 15일\n", page_id)
    diagnostic_roundtrip = _source_mdx(
        "## Section\n\nJan 15, 2024\n",
        page_id,
    )

    def forward_convert(_input_path, output_path, _page_id, **_kwargs):
        content = (
            original
            if Path(output_path).name == "reverse-sync.base.mdx"
            else diagnostic_roundtrip
        )
        Path(output_path).write_text(content)
        return content

    with patch("reverse_sync_cli._forward_convert", side_effect=forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(
                original,
                "main:src/content/ko/test.mdx",
            ),
            improved_src=MdxSource(
                improved,
                "src/content/ko/test.mdx",
            ),
            base_snapshot=base,
            for_push=True,
            lenient=True,
        )

    assert result["status"] == "blocked"
    assert result["reason_code"] == "semantic_roundtrip_mismatch"
    assert result["push_eligible"] is False
    assert result["diagnostics"]["lenient"]["passed"] is True
    assert result["diagnostics"]["lenient"]["push_eligible"] is False


def test_online_verify_blocks_missing_attachment(tmp_path, monkeypatch):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    _write_page_catalog(tmp_path, page_id)
    original = _source_mdx("Before\n", page_id)
    improved = _source_mdx("Before\n\n![new](/images/new.png)\n", page_id)

    result = run_verify(
        page_id=page_id,
        original_src=MdxSource(
            original,
            "main:src/content/ko/test.mdx",
        ),
        improved_src=MdxSource(
            improved,
            "src/content/ko/test.mdx",
        ),
        base_snapshot=_snapshot(title="Test page"),
        attachment_catalog=AttachmentCatalog(
            page_id=page_id,
            attachments=(),
            fetched_at=NOW.isoformat(),
            api="fixture",
        ),
        for_push=True,
    )

    assert result["status"] == "blocked"
    assert result["reason_code"] == "missing_attachment"
    assert "new.png" in result["detail"]
