"""reverse_sync/rehydrator.py 유닛 테스트."""

from reverse_sync.rehydrator import (
    rehydrate_xhtml,
    rehydrate_xhtml_from_files,
    sidecar_matches_mdx,
)
from reverse_sync.sidecar import build_sidecar, write_sidecar


def test_sidecar_matches_mdx_true_when_hash_same():
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx = "## Title\n\nBody\n"
    sidecar = build_sidecar(xhtml, mdx)
    assert sidecar_matches_mdx(mdx, sidecar) is True


def test_rehydrate_xhtml_returns_raw_when_hash_matches():
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx = "## Title\n\nBody\n"
    sidecar = build_sidecar(xhtml, mdx)
    assert rehydrate_xhtml(mdx, sidecar) == xhtml


def test_rehydrate_xhtml_fallback_when_hash_mismatch():
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx_original = "## Title\n\nBody\n"
    mdx_changed = "## Changed\n\nBody\n"
    sidecar = build_sidecar(xhtml, mdx_original)

    called = {}

    def _fallback(text: str) -> str:
        called["mdx"] = text
        return "<x-fallback />"

    restored = rehydrate_xhtml(mdx_changed, sidecar, fallback_renderer=_fallback)
    assert restored == "<x-fallback />"
    assert called["mdx"] == mdx_changed


def test_rehydrate_xhtml_from_files(tmp_path):
    mdx_path = tmp_path / "expected.mdx"
    sidecar_path = tmp_path / "expected.roundtrip.json"
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx = "## Title\n\nBody\n"
    mdx_path.write_text(mdx, encoding="utf-8")
    write_sidecar(build_sidecar(xhtml, mdx, page_id="100"), sidecar_path)

    restored = rehydrate_xhtml_from_files(mdx_path, sidecar_path)
    assert restored == xhtml
