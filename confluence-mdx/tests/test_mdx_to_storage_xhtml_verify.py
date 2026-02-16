from pathlib import Path

from reverse_sync.mdx_to_storage_xhtml_verify import (
    iter_testcase_dirs,
    mdx_to_storage_xhtml_fragment,
    verify_expected_mdx_against_page_xhtml,
    verify_testcase_dir,
)


def test_mdx_to_storage_xhtml_fragment_smoke():
    mdx = "## Section\n\nParagraph with **bold** and `code`\n"
    generated = mdx_to_storage_xhtml_fragment(mdx)
    assert "<h1>Section</h1>" in generated
    assert "<p>Paragraph with <strong>bold</strong> and <code>code</code></p>" in generated


def test_verify_expected_mdx_against_page_xhtml_pass():
    mdx = "## Title\n\nBody\n"
    page = "<h1>Title</h1><p>Body</p>"
    passed, generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is True
    assert generated == "<h1>Title</h1><p>Body</p>"
    assert diff_report == ""


def test_verify_expected_mdx_against_page_xhtml_fail_has_diff():
    mdx = "## Title\n\nBody changed\n"
    page = "<h1>Title</h1><p>Body</p>"
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is False
    assert "--- page.xhtml" in diff_report
    assert "+++ generated-from-expected.mdx.xhtml" in diff_report


def test_iter_testcase_dirs_filters_required_files(tmp_path: Path):
    valid = tmp_path / "100"
    valid.mkdir()
    (valid / "page.xhtml").write_text("<p>ok</p>", encoding="utf-8")
    (valid / "expected.mdx").write_text("text", encoding="utf-8")

    missing_mdx = tmp_path / "200"
    missing_mdx.mkdir()
    (missing_mdx / "page.xhtml").write_text("<p>only</p>", encoding="utf-8")

    missing_page = tmp_path / "300"
    missing_page.mkdir()
    (missing_page / "expected.mdx").write_text("only", encoding="utf-8")

    found = list(iter_testcase_dirs(tmp_path))
    assert found == [valid]


def test_verify_testcase_dir_reads_and_returns_case_result(tmp_path: Path):
    case_dir = tmp_path / "544375741"
    case_dir.mkdir()
    (case_dir / "expected.mdx").write_text("## Heading\n\nBody\n", encoding="utf-8")
    (case_dir / "page.xhtml").write_text("<h1>Heading</h1><p>Body</p>", encoding="utf-8")

    result = verify_testcase_dir(case_dir)
    assert result.case_id == "544375741"
    assert result.passed is True
    assert result.generated_xhtml == "<h1>Heading</h1><p>Body</p>"
    assert result.diff_report == ""
