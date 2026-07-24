"""검증한 snapshot과 Confluence PUT을 결합하는 transaction 계약 테스트."""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from reverse_sync.confluence_client import (
    ConfluenceConfig,
    InvalidPageSnapshotError,
    NetworkError,
    PermissionDeniedError,
    VersionConflictError,
    get_active_draft,
    get_page_snapshot,
    update_page,
)
from reverse_sync.base_parity import verify_base_parity
from reverse_sync.manifest import (
    ArtifactTamperedError,
    StaleVerificationError,
    create_sync_manifest,
    load_sync_manifest,
)
from reverse_sync.models import PageSnapshot, SyncStatus, VerificationGate
from reverse_sync.publisher import (
    ActiveDraftError,
    PostconditionError,
    RemoteDriftError,
    publish_verified_manifest,
)
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


def _manifest(tmp_path: Path, base: PageSnapshot | None = None) -> Path:
    return create_sync_manifest(
        runs_dir=tmp_path / "reverse-sync",
        base=base or _snapshot(),
        original_mdx="# Test page\n\nBefore\n",
        original_descriptor="main:src/content/ko/test.mdx",
        improved_mdx="# Test page\n\nAfter\n",
        improved_descriptor="src/content/ko/test.mdx",
        candidate_xhtml="<p>After</p>",
        verifier_policy="reverse-sync-push-v1",
        tool_version="reverse-sync-cli-v1",
        push_eligible=True,
        gates=tuple(
            VerificationGate(name, True)
            for name in (
                "source_identity",
                "base_parity",
                "intent_complete",
                "semantic_roundtrip",
                "artifact_integrity",
            )
        ),
    )


class FakeGateway:
    def __init__(
        self,
        current_snapshots: list[PageSnapshot],
        *,
        draft: PageSnapshot | None = None,
        update_error: Exception | None = None,
    ):
        self.current_snapshots = list(current_snapshots)
        self.draft = draft
        self.update_error = update_error
        self.current_calls = 0
        self.draft_calls = 0
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
            candidate_xhtml="<p>After</p>",
            verifier_policy="reverse-sync-push-v1",
            tool_version="reverse-sync-cli-v1",
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


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "different", "status": "current", "title": "T", "version": {"number": 1}},
        {"id": "123", "status": "draft", "title": "T", "version": {"number": 1}},
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
    expected = {"status": "pass", "page_id": "123", "push_eligible": True}

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


def test_online_verify_builds_manifest_from_remote_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    base = _snapshot(
        title="Test page",
        body="<h2>Section</h2><p>Before</p>",
    )
    original = "# Test page\n\n## Section\n\nBefore\n"
    improved = "# Test page\n\n## Section\n\nAfter\n"

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

    assert result["status"] == "pass"
    assert result["push_eligible"] is True
    assert result["base_version"] == 5
    assert result["base_storage_sha256"] == base.storage_sha256
    assert len(result["candidate_sha256"]) == 64
    assert "semantic_roundtrip" in result["local_gates"]
    manifest_path = Path(result["manifest_path"])
    assert manifest_path.is_file()
    manifest = load_sync_manifest(manifest_path)
    assert manifest.base_version == 5
    assert manifest.base_storage_sha256 == base.storage_sha256
    assert (manifest_path.parent / "candidate.xhtml").read_text() == (
        tmp_path / "var" / page_id / "reverse-sync.patched.xhtml"
    ).read_text()


def test_online_verify_blocks_stale_original_before_patch(tmp_path, monkeypatch):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)
    base = _snapshot(title="Test page", body="<p>Remote edit</p>")
    original = "# Test page\n\nBefore\n"
    improved = "# Test page\n\nAfter\n"

    def forward_convert(_input_path, output_path, _page_id, **_kwargs):
        Path(output_path).write_text("# Test page\n\nRemote edit\n")
        return "# Test page\n\nRemote edit\n"

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


def test_lenient_verify_is_never_push_eligible(tmp_path, monkeypatch):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)

    result = run_verify(
        page_id=page_id,
        original_src=MdxSource("# Test page\n\nBefore\n", "original.mdx"),
        improved_src=MdxSource("# Test page\n\nAfter\n", "improved.mdx"),
        base_snapshot=_snapshot(title="Test page"),
        for_push=True,
        lenient=True,
    )

    assert result["status"] == "blocked"
    assert result["reason_code"] == "lenient_verification_not_pushable"
    assert result["push_eligible"] is False


def test_online_verify_blocks_missing_attachment(tmp_path, monkeypatch):
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    page_id = "123"
    (tmp_path / "var" / page_id).mkdir(parents=True)

    result = run_verify(
        page_id=page_id,
        original_src=MdxSource("# Test page\n\nBefore\n", "original.mdx"),
        improved_src=MdxSource(
            "# Test page\n\nBefore\n\n![new](/images/new.png)\n",
            "improved.mdx",
        ),
        base_snapshot=_snapshot(title="Test page"),
        for_push=True,
    )

    assert result["status"] == "blocked"
    assert result["reason_code"] == "missing_attachment"
    assert "new.png" in result["detail"]
