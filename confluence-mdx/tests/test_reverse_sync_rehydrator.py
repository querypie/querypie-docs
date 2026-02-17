"""reverse_sync/rehydrator.py 유닛 테스트."""

from reverse_sync.rehydrator import (
    rehydrate_xhtml,
    rehydrate_xhtml_from_files,
    sidecar_matches_mdx,
)
from reverse_sync.sidecar import build_sidecar, write_sidecar


def test_sidecar_matches_mdx_true_when_hash_same():
    mdx = "## Title\n\nBody\n"
    sidecar = build_sidecar(mdx, "<h1>Title</h1><p>Body</p>")
    assert sidecar_matches_mdx(mdx, sidecar) is True


def test_rehydrate_xhtml_returns_raw_when_hash_matches():
    mdx = "## Title\n\nBody\n"
    raw = "<h1>Title</h1><p>Body</p>"
    sidecar = build_sidecar(mdx, raw)
    assert rehydrate_xhtml(mdx, sidecar) == raw


def test_rehydrate_xhtml_fallback_when_hash_mismatch():
    mdx = "## Changed\n\nBody\n"
    sidecar = build_sidecar("## Title\n\nBody\n", "<h1>Title</h1><p>Body</p>")

    called = {}

    def _fallback(text: str) -> str:
        called["mdx"] = text
        return "<x-fallback />"

    restored = rehydrate_xhtml(mdx, sidecar, fallback_renderer=_fallback)
    assert restored == "<x-fallback />"
    assert called["mdx"] == mdx


def test_rehydrate_xhtml_from_files(tmp_path):
    mdx_path = tmp_path / "expected.mdx"
    sidecar_path = tmp_path / "expected.roundtrip.json"
    mdx = "## Title\n\nBody\n"
    raw = "<h1>Title</h1><p>Body</p>"
    mdx_path.write_text(mdx, encoding="utf-8")
    write_sidecar(build_sidecar(mdx, raw, page_id="100"), sidecar_path)

    restored = rehydrate_xhtml_from_files(mdx_path, sidecar_path)
    assert restored == raw
