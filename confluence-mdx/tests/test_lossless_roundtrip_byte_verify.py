from lossless_roundtrip.byte_verify import verify_case_dir
from lossless_roundtrip.sidecar import build_sidecar, write_sidecar


def test_verify_case_dir_passes_when_sidecar_raw_matches_page(tmp_path):
    case = tmp_path / "100"
    case.mkdir()
    mdx = "## Title\n\nBody\n"
    xhtml = "<h1>Title</h1><p>Body</p>"
    (case / "expected.mdx").write_text(mdx, encoding="utf-8")
    (case / "page.xhtml").write_text(xhtml, encoding="utf-8")
    write_sidecar(build_sidecar(mdx, xhtml, page_id="100"), case / "expected.roundtrip.json")

    result = verify_case_dir(case)
    assert result.passed is True
    assert result.reason == "byte_equal"
    assert result.first_mismatch_offset == -1


def test_verify_case_dir_fails_when_sidecar_missing(tmp_path):
    case = tmp_path / "100"
    case.mkdir()
    (case / "expected.mdx").write_text("## T\n", encoding="utf-8")
    (case / "page.xhtml").write_text("<h1>T</h1>", encoding="utf-8")

    result = verify_case_dir(case)
    assert result.passed is False
    assert result.reason.startswith("sidecar_missing")


def test_verify_case_dir_fails_with_mismatch_offset(tmp_path):
    case = tmp_path / "100"
    case.mkdir()
    mdx = "## Title\n\nBody\n"
    (case / "expected.mdx").write_text(mdx, encoding="utf-8")
    (case / "page.xhtml").write_text("<h1>Title</h1><p>Body!</p>", encoding="utf-8")
    write_sidecar(
        build_sidecar(mdx, "<h1>Title</h1><p>Body</p>", page_id="100"),
        case / "expected.roundtrip.json",
    )

    result = verify_case_dir(case)
    assert result.passed is False
    assert result.reason == "byte_mismatch"
    assert result.first_mismatch_offset >= 0
