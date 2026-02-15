from pathlib import Path

from reverse_sync.mdx_to_storage_xhtml_verify import (
    iter_testcase_dirs,
    mdx_to_storage_xhtml_fragment,
    verify_expected_mdx_against_page_xhtml,
    verify_testcase_dir,
)


def test_mdx_to_storage_xhtml_fragment_for_simple_blocks():
    mdx = "# Title\n\nParagraph text\n\n- Item 1\n- Item 2\n"
    fragment = mdx_to_storage_xhtml_fragment(mdx)
    assert "<h1>Title</h1>" in fragment
    assert "<p>Paragraph text</p>" in fragment
    assert "<ul>" in fragment
    assert "<li><p>Item 1</p></li>" in fragment


def test_verify_expected_mdx_against_page_xhtml_pass():
    mdx = "# Title\n\nParagraph text\n"
    page_xhtml = "<h1>Title</h1><p>Paragraph text</p>"
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(
        mdx, page_xhtml
    )
    assert passed is True
    assert diff_report == ""


def test_iter_testcase_dirs_filters_required_files(tmp_path: Path):
    good = tmp_path / "100"
    good.mkdir()
    (good / "page.xhtml").write_text("<p>x</p>", encoding="utf-8")
    (good / "expected.mdx").write_text("x\n", encoding="utf-8")

    missing_expected = tmp_path / "200"
    missing_expected.mkdir()
    (missing_expected / "page.xhtml").write_text("<p>x</p>", encoding="utf-8")

    dirs = list(iter_testcase_dirs(tmp_path))
    assert dirs == [good]


def test_verify_testcase_dir_writes_generated_file(tmp_path: Path):
    case = tmp_path / "300"
    case.mkdir()
    (case / "expected.mdx").write_text("# Title\n\nParagraph\n", encoding="utf-8")
    (case / "page.xhtml").write_text("<h1>Title</h1><p>Paragraph</p>", encoding="utf-8")

    result = verify_testcase_dir(case, write_generated=True, diff_engine="external")
    assert result.passed is True
    assert (case / "generated.from.expected.xhtml").exists()
