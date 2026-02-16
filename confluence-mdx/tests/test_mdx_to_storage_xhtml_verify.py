from pathlib import Path

from reverse_sync.mdx_to_storage_xhtml_verify import (
    CaseVerification,
    analyze_failed_cases,
    classify_failure_reasons,
    iter_testcase_dirs,
    mdx_to_storage_xhtml_fragment,
    summarize_results,
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


def test_verify_expected_mdx_ignore_ri_filename_option():
    mdx = "<figure>\n<img src=\"/images/a.png\" alt=\"a\">\n</figure>\n"
    page = '<ac:image ac:align="center"><ri:attachment ri:filename="b.png"></ri:attachment></ac:image>'
    passed, _generated, _diff_report = verify_expected_mdx_against_page_xhtml(
        mdx, page, ignore_ri_filename=True
    )
    assert passed is True


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


def test_verify_ignores_confluence_auto_attributes():
    mdx = "## Title\n\nBody\n"
    page = '<h1 local-id="x">Title</h1><p ac:local-id="y" class="media-group">Body</p>'
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is True
    assert diff_report == ""


def test_verify_strips_layout_wrappers():
    mdx = "Body\n"
    page = (
        "<ac:layout><ac:layout-section><ac:layout-cell>"
        "<p>Body</p>"
        "</ac:layout-cell></ac:layout-section></ac:layout>"
    )
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is True
    assert diff_report == ""


def test_verify_strips_nonreversible_macros():
    mdx = "Body\n"
    page = (
        '<ac:structured-macro ac:name="toc"></ac:structured-macro>'
        '<ac:structured-macro ac:name="view-file"></ac:structured-macro>'
        "<p>Body</p>"
    )
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is True
    assert diff_report == ""


def test_verify_strips_decorations_but_keeps_inner_text():
    mdx = "Text\n"
    page = '<p><ac:inline-comment-marker>Text</ac:inline-comment-marker></p>'
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is True
    assert diff_report == ""


def test_verify_strips_colgroup_from_tables():
    """Confluence tables have <colgroup> for column widths; generated tables don't."""
    mdx = """| A | B |
| --- | --- |
| 1 | 2 |
"""
    page = (
        "<table><colgroup><col /><col /></colgroup>"
        "<tbody><tr><th><p>A</p></th><th><p>B</p></th></tr>"
        "<tr><td><p>1</p></td><td><p>2</p></td></tr></tbody></table>"
    )
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is True
    assert diff_report == ""


def test_verify_strips_highlight_colour_and_space_key():
    """data-highlight-colour on th and ri:space-key on links should be ignored."""
    mdx = "## Title\n"
    page = '<h1 data-highlight-colour="#eee" ri:space-key="DOCS">Title</h1>'
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is True
    assert diff_report == ""


def test_verify_strips_image_auto_attributes():
    """ac:alt, ac:layout, data-card-appearance should be ignored."""
    mdx = """<figure>
  <img src="/images/sample.png" alt="Sample" width="700">
</figure>
"""
    page = (
        '<ac:image ac:align="center" ac:alt="sample.png" ac:layout="center" ac:width="700">'
        '<ri:attachment ri:filename="sample.png"></ri:attachment></ac:image>'
    )
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is True
    assert diff_report == ""


def test_verify_strips_empty_paragraphs():
    """Trailing empty <p></p> in page.xhtml should be stripped."""
    mdx = "## Title\n"
    page = "<h1>Title</h1><p></p>"
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx, page)
    assert passed is True
    assert diff_report == ""


def test_classify_failure_reasons_detects_verify_filter_noise():
    diff_report = '-<p ac:local-id="x">A</p>\n+<p>A</p>\n-<ri:attachment ri:version-at-save="1" />'
    reasons = classify_failure_reasons(diff_report)
    assert "verify_filter_noise" in reasons


def test_classify_failure_reasons_detects_internal_link_unresolved():
    diff_report = "-<ac:link><ri:page ri:content-title=\"Doc\" /></ac:link>\n+<a href=\"#link-error\">Doc</a>"
    reasons = classify_failure_reasons(diff_report)
    assert "internal_link_unresolved" in reasons


def test_analyze_and_summarize_results_prioritize_p1():
    results = [
        CaseVerification(case_id="100", passed=True, generated_xhtml="<p>ok</p>", diff_report=""),
        CaseVerification(
            case_id="200",
            passed=False,
            generated_xhtml="<p>bad</p>",
            diff_report="-<ac:link><ri:page /></ac:link>\n+<a href=\"#link-error\">x</a>",
        ),
        CaseVerification(
            case_id="300",
            passed=False,
            generated_xhtml="<p>bad</p>",
            diff_report='-<p ac:local-id="x">A</p>\n+<p>A</p>',
        ),
    ]

    analyses = analyze_failed_cases(results)
    assert len(analyses) == 2
    assert analyses[0].case_id == "200"
    assert analyses[0].priority == "P1"

    summary = summarize_results(results)
    assert summary.total == 3
    assert summary.passed == 1
    assert summary.failed == 2
    assert summary.by_priority["P1"] == 1
    assert summary.by_priority["P2"] == 1
