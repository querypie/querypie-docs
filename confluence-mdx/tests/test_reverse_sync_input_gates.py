"""reverse-sync source identity와 dependency gate 계약 테스트."""

from datetime import datetime, timezone
from pathlib import Path

import yaml

from mdx_to_storage.link_resolver import LinkResolver, PageEntry
from reverse_sync.base_parity import (
    verify_base_parity,
    verify_repository_source_identity,
    verify_source_identity,
)
from reverse_sync.dependencies import verify_dependencies
from reverse_sync.models import (
    AttachmentCatalog,
    AttachmentRecord,
    PageSnapshot,
)
from reverse_sync.patch_builder import _resolve_generated_links


NOW = datetime(2026, 7, 24, tzinfo=timezone.utc).isoformat()


def _snapshot(body: str = "<p>Before</p>") -> PageSnapshot:
    return PageSnapshot(
        page_id="123",
        status="current",
        title="Test page",
        version=7,
        storage_xhtml=body,
        fetched_at=NOW,
        api="fixture",
    )


def _mdx(body: str, *, page_id: str = "123") -> str:
    return (
        "---\n"
        "title: 'Test page'\n"
        f"confluenceUrl: 'https://example.atlassian.net/wiki/pages/{page_id}'\n"
        "---\n\n"
        "# Test page\n\n"
        f"{body}"
    )


def _write_pages(path: Path, rows: list[dict]) -> Path:
    path.write_text(yaml.safe_dump(rows, allow_unicode=True))
    return path


def test_repository_identity_binds_page_url_and_path(tmp_path):
    pages_path = _write_pages(
        tmp_path / "pages.qm.yaml",
        [{"page_id": "123", "title_orig": "Test page", "path": ["guide", "test"]}],
    )

    result = verify_repository_source_identity(
        _snapshot(),
        _mdx("Before\n"),
        _mdx("After\n"),
        original_descriptor="main:src/content/ko/guide/test.mdx",
        improved_descriptor="src/content/ko/guide/test.mdx",
        pages_path=pages_path,
    )

    assert result.passed is True


def test_repository_identity_blocks_wrong_url_or_descriptor_path(tmp_path):
    pages_path = _write_pages(
        tmp_path / "pages.qm.yaml",
        [{"page_id": "123", "title_orig": "Test page", "path": ["guide", "test"]}],
    )

    wrong_url = verify_repository_source_identity(
        _snapshot(),
        _mdx("Before\n"),
        _mdx("After\n", page_id="999"),
        original_descriptor="main:src/content/ko/guide/test.mdx",
        improved_descriptor="src/content/ko/guide/test.mdx",
        pages_path=pages_path,
    )
    wrong_path = verify_repository_source_identity(
        _snapshot(),
        _mdx("Before\n"),
        _mdx("After\n"),
        original_descriptor="main:src/content/ko/guide/test.mdx",
        improved_descriptor="src/content/ko/other.mdx",
        pages_path=pages_path,
    )

    assert wrong_url.reason_code == "page_identity_mismatch"
    assert wrong_path.reason_code == "page_identity_mismatch"


def test_source_identity_blocks_frontmatter_title_and_h1_mismatch(tmp_path):
    pages_path = _write_pages(
        tmp_path / "pages.qm.yaml",
        [{"page_id": "123", "title_orig": "Test page", "path": ["guide", "test"]}],
    )
    inconsistent = _mdx("Before\n").replace("# Test page", "# Different H1")

    result = verify_repository_source_identity(
        _snapshot(),
        inconsistent,
        inconsistent.replace("Before", "After"),
        original_descriptor="main:src/content/ko/guide/test.mdx",
        improved_descriptor="src/content/ko/guide/test.mdx",
        pages_path=pages_path,
    )

    assert result.reason_code == "title_change_unsupported"


def test_strict_source_identity_requires_confluence_url():
    without_url = _mdx("Before\n").replace(
        "confluenceUrl: 'https://example.atlassian.net/wiki/pages/123'\n",
        "",
    )

    result = verify_source_identity(
        _snapshot(),
        _mdx("Before\n"),
        without_url,
        require_confluence_url=True,
    )

    assert result.reason_code == "page_identity_mismatch"


def test_base_parity_classifies_stale_source_and_converter_drift():
    snapshot = _snapshot("<p>Remote</p>")
    original = _mdx("Before\n")
    converted = _mdx("Remote\n")

    stale = verify_base_parity(
        snapshot,
        original,
        converted,
        provenance_storage_xhtml="<p>Before</p>",
    )
    drift = verify_base_parity(
        snapshot,
        original,
        converted,
        provenance_storage_xhtml="<p>Remote</p>",
    )
    unknown = verify_base_parity(snapshot, original, converted)

    assert stale.reason_code == "stale_original_mdx"
    assert drift.reason_code == "forward_converter_drift"
    assert unknown.reason_code == "base_parity_mismatch"


def test_dependency_gate_resolves_new_internal_link_and_renders_ac_link(tmp_path):
    pages_path = _write_pages(
        tmp_path / "pages.qm.yaml",
        [
            {
                "page_id": "123",
                "title_orig": "Test page",
                "path": ["guide", "test"],
            },
            {
                "page_id": "456",
                "title_orig": "Target page",
                "path": ["guide", "target"],
            },
        ],
    )

    result, resolver = verify_dependencies(
        page_id="123",
        original_mdx=_mdx("Before\n"),
        improved_mdx=_mdx("Before\n\n[Target](./target)\n"),
        pages_path=pages_path,
        attachment_catalog=None,
    )
    rendered = _resolve_generated_links(
        '<p><a href="./target">Target</a></p>',
        resolver,
    )

    assert result.passed is True
    assert result.evidence.internal_links[0].page_id == "456"
    assert (
        rendered
        == '<p><ac:link><ri:page ri:content-title="Target page"></ri:page>'
        '<ac:link-body>Target</ac:link-body></ac:link></p>'
    )


def test_dependency_gate_blocks_unresolved_and_ambiguous_internal_links(tmp_path):
    unresolved_pages = _write_pages(
        tmp_path / "unresolved.yaml",
        [
            {
                "page_id": "123",
                "title_orig": "Test page",
                "path": ["guide", "test"],
            }
        ],
    )
    unresolved, _ = verify_dependencies(
        page_id="123",
        original_mdx=_mdx("Before\n"),
        improved_mdx=_mdx("Before\n\n[Missing](./missing)\n"),
        pages_path=unresolved_pages,
        attachment_catalog=None,
    )

    ambiguous_pages = _write_pages(
        tmp_path / "ambiguous.yaml",
        [
            {
                "page_id": "123",
                "title_orig": "Test page",
                "path": ["guide", "test"],
            },
            {
                "page_id": "456",
                "title_orig": "Target A",
                "path": ["guide", "target"],
            },
            {
                "page_id": "789",
                "title_orig": "Target B",
                "path": ["guide", "target"],
            },
        ],
    )
    ambiguous, _ = verify_dependencies(
        page_id="123",
        original_mdx=_mdx("Before\n"),
        improved_mdx=_mdx("Before\n\n[Target](./target)\n"),
        pages_path=ambiguous_pages,
        attachment_catalog=None,
    )

    assert unresolved.reason_code == "internal_link_unresolved"
    assert ambiguous.reason_code == "ambiguous_target"


def test_dependency_gate_uses_attachment_catalog_for_new_image(tmp_path):
    pages_path = _write_pages(
        tmp_path / "pages.qm.yaml",
        [{"page_id": "123", "title_orig": "Test page", "path": ["test"]}],
    )
    catalog = AttachmentCatalog(
        page_id="123",
        attachments=(
            AttachmentRecord(
                attachment_id="att-1",
                page_id="123",
                filename="screen.png",
                version=3,
            ),
        ),
        fetched_at=NOW,
        api="fixture",
    )

    passed, _ = verify_dependencies(
        page_id="123",
        original_mdx=_mdx("Before\n"),
        improved_mdx=_mdx("Before\n\n![screen](./screen.png)\n"),
        pages_path=pages_path,
        attachment_catalog=catalog,
    )
    missing, _ = verify_dependencies(
        page_id="123",
        original_mdx=_mdx("Before\n"),
        improved_mdx=_mdx("Before\n\n![missing](./missing.png)\n"),
        pages_path=pages_path,
        attachment_catalog=catalog,
    )

    assert passed.passed is True
    assert passed.evidence.attachments[0].attachment_id == "att-1"
    assert missing.reason_code == "missing_attachment"


def test_dependency_gate_blocks_new_external_image(tmp_path):
    pages_path = _write_pages(
        tmp_path / "pages.qm.yaml",
        [{"page_id": "123", "title_orig": "Test page", "path": ["test"]}],
    )

    result, _ = verify_dependencies(
        page_id="123",
        original_mdx=_mdx("Before\n"),
        improved_mdx=_mdx(
            "Before\n\n![external](https://cdn.example.com/screen.png)\n"
        ),
        pages_path=pages_path,
        attachment_catalog=None,
    )

    assert result.reason_code == "dependency_failure"
    assert "external image" in result.detail


def test_dependency_gate_blocks_internal_html_link_attributes(tmp_path):
    pages_path = _write_pages(
        tmp_path / "pages.qm.yaml",
        [
            {"page_id": "123", "title_orig": "Test page", "path": ["test"]},
            {"page_id": "456", "title_orig": "Target", "path": ["target"]},
        ],
    )

    result, _ = verify_dependencies(
        page_id="123",
        original_mdx=_mdx("Before\n"),
        improved_mdx=_mdx(
            'Before\n\n<a class="button" href="target">Target</a>\n'
        ),
        pages_path=pages_path,
        attachment_catalog=None,
    )

    assert result.reason_code == "dependency_failure"
    assert "class" in result.detail


def test_attachment_link_renders_as_confluence_attachment_macro():
    resolver = LinkResolver(
        [PageEntry("123", "Test page", ["test"])]
    )

    rendered = _resolve_generated_links(
        '<p><a href="./guide.pdf">Download</a></p>',
        resolver,
        frozenset({"guide.pdf"}),
    )

    assert rendered == (
        '<p><ac:link><ri:attachment ri:filename="guide.pdf"></ri:attachment>'
        '<ac:link-body>Download</ac:link-body></ac:link></p>'
    )


def test_local_anchor_renders_as_confluence_link_macro():
    resolver = LinkResolver(
        [PageEntry("123", "Test page", ["test"])]
    )

    rendered = _resolve_generated_links(
        '<p><a href=".#details">Details</a></p>',
        resolver,
    )

    assert rendered == (
        '<p><ac:link ac:anchor="details">'
        "<ac:link-body>Details</ac:link-body></ac:link></p>"
    )


def test_internal_html_link_with_href_after_other_whitespace_is_resolved():
    resolver = LinkResolver(
        [
            PageEntry("123", "Test page", ["test"]),
            PageEntry("456", "Target", ["target"]),
        ]
    )

    rendered = _resolve_generated_links(
        "<p><a\n href=\"target\">Target</a></p>",
        resolver,
    )

    assert '<ri:page ri:content-title="Target"></ri:page>' in rendered


def test_link_resolver_reports_duplicate_target_as_ambiguous():
    resolver = LinkResolver(
        [
            PageEntry("1", "One", ["guide", "same"]),
            PageEntry("2", "Two", ["guide", "same"]),
        ]
    )

    resolution = resolver.resolve_with_evidence("guide/same", link_text="same")

    assert resolution.status == "ambiguous"
    assert resolution.candidate_page_ids == ("1", "2")


def test_link_resolver_does_not_hide_wrong_path_with_matching_label():
    resolver = LinkResolver(
        [PageEntry("1", "Target", ["guide", "target"])]
    )

    resolution = resolver.resolve_with_evidence(
        "guide/typo",
        link_text="Target",
    )

    assert resolution.status == "unresolved"
