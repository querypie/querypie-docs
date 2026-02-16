from lossless_roundtrip.sidecar import (
    ROUNDTRIP_SCHEMA_VERSION,
    build_sidecar,
    load_sidecar,
    sha256_text,
    write_sidecar,
)


def test_sha256_text_is_stable():
    assert sha256_text("abc") == sha256_text("abc")
    assert sha256_text("abc") != sha256_text("abcd")


def test_build_sidecar_contains_hashes_and_payload():
    mdx = "## Title\n\nBody\n"
    xhtml = "<h1>Title</h1><p>Body</p>"
    sidecar = build_sidecar(mdx, xhtml, page_id="123")
    assert sidecar.roundtrip_schema_version == ROUNDTRIP_SCHEMA_VERSION
    assert sidecar.page_id == "123"
    assert sidecar.raw_xhtml == xhtml
    assert sidecar.mdx_sha256 == sha256_text(mdx)
    assert sidecar.source_xhtml_sha256 == sha256_text(xhtml)


def test_write_and_load_sidecar_roundtrip(tmp_path):
    mdx = "## T\n"
    xhtml = "<h1>T</h1>"
    sidecar = build_sidecar(mdx, xhtml, page_id="case-1")
    path = tmp_path / "expected.roundtrip.json"
    write_sidecar(sidecar, path)

    loaded = load_sidecar(path)
    assert loaded.roundtrip_schema_version == ROUNDTRIP_SCHEMA_VERSION
    assert loaded.page_id == "case-1"
    assert loaded.raw_xhtml == xhtml
    assert loaded.mdx_sha256 == sha256_text(mdx)
