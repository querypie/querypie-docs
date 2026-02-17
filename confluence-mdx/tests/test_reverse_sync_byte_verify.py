"""reverse_sync/byte_verify.py 유닛 테스트."""

from reverse_sync.byte_verify import verify_case_dir
from reverse_sync.sidecar import build_sidecar, write_sidecar


def test_verify_case_dir_passes_when_sidecar_raw_matches_page(tmp_path):
    case = tmp_path / "100"
    case.mkdir()
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx = "## Title\n\nBody\n"
    (case / "expected.mdx").write_text(mdx, encoding="utf-8")
    (case / "page.xhtml").write_text(xhtml, encoding="utf-8")
    write_sidecar(build_sidecar(xhtml, mdx, page_id="100"), case / "expected.roundtrip.json")

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
    xhtml_original = "<h1>Title</h1><p>Body</p>"
    xhtml_different = "<h1>Title</h1><p>Body!</p>"
    mdx = "## Title\n\nBody\n"
    (case / "expected.mdx").write_text(mdx, encoding="utf-8")
    (case / "page.xhtml").write_text(xhtml_different, encoding="utf-8")
    write_sidecar(build_sidecar(xhtml_original, mdx, page_id="100"), case / "expected.roundtrip.json")

    result = verify_case_dir(case)
    assert result.passed is False
    assert result.reason == "byte_mismatch"
    assert result.first_mismatch_offset >= 0
