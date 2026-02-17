"""reverse_sync/fragment_extractor.py 유닛 테스트."""

import pytest

from reverse_sync.fragment_extractor import (
    FragmentExtractionResult,
    extract_block_fragments,
    _find_element_end,
    _find_tag_close_gt,
    _find_tag_start,
)


class TestFindTagStart:
    def test_finds_simple_tag(self):
        assert _find_tag_start("<h1>Title</h1>", "h1", 0) == 0

    def test_skips_prefix_match(self):
        text = "<pre>code</pre><p>text</p>"
        assert _find_tag_start(text, "p", 0) == 15

    def test_finds_from_offset(self):
        text = "<p>first</p><p>second</p>"
        assert _find_tag_start(text, "p", 12) == 12

    def test_returns_neg1_when_not_found(self):
        assert _find_tag_start("<div>text</div>", "p", 0) == -1

    def test_finds_namespace_tag(self):
        text = '<ac:structured-macro ac:name="info">body</ac:structured-macro>'
        assert _find_tag_start(text, "ac:structured-macro", 0) == 0

    def test_self_closing_tag(self):
        assert _find_tag_start("<hr />", "hr", 0) == 0

    def test_tag_with_attrs(self):
        text = '<p style="color:red">text</p>'
        assert _find_tag_start(text, "p", 0) == 0


class TestFindTagCloseGt:
    def test_simple(self):
        assert _find_tag_close_gt("<p>", 0) == 2

    def test_with_attrs(self):
        text = '<p class="x">'
        assert _find_tag_close_gt(text, 0) == 12

    def test_skips_gt_in_quotes(self):
        text = '<p attr="a>b">text</p>'
        assert _find_tag_close_gt(text, 0) == 13

    def test_returns_neg1(self):
        assert _find_tag_close_gt("<p no closing", 0) == -1


class TestFindElementEnd:
    def test_simple_element(self):
        text = "<p>hello</p>"
        assert _find_element_end(text, "p", 0) == len(text)

    def test_self_closing(self):
        text = "<hr />"
        assert _find_element_end(text, "hr", 0) == 6

    def test_self_closing_no_space(self):
        text = "<br/>"
        assert _find_element_end(text, "br", 0) == 5

    def test_nested_same_tag(self):
        text = "<div><div>inner</div></div>"
        assert _find_element_end(text, "div", 0) == len(text)

    def test_namespace_tag(self):
        text = (
            '<ac:structured-macro ac:name="info">'
            "<ac:rich-text-body><p>hi</p></ac:rich-text-body>"
            "</ac:structured-macro>"
        )
        assert _find_element_end(text, "ac:structured-macro", 0) == len(text)

    def test_raises_on_unclosed(self):
        with pytest.raises(ValueError, match="Unclosed"):
            _find_element_end("<p>no close tag", "p", 0)


class TestExtractBlockFragments:
    def test_simple_blocks(self):
        xhtml = "<h1>Title</h1>\n<p>Body</p>"
        result = extract_block_fragments(xhtml)

        assert len(result.fragments) == 2
        assert result.fragments[0] == "<h1>Title</h1>"
        assert result.fragments[1] == "<p>Body</p>"
        assert result.prefix == ""
        assert result.suffix == ""
        assert result.separators == ["\n"]
        assert _reassemble(result) == xhtml

    def test_no_separator(self):
        xhtml = "<h2>A</h2><p>B</p>"
        result = extract_block_fragments(xhtml)

        assert len(result.fragments) == 2
        assert result.separators == [""]
        assert _reassemble(result) == xhtml

    def test_self_closing_tags(self):
        xhtml = "<p>Done.</p><p />"
        result = extract_block_fragments(xhtml)

        assert len(result.fragments) == 2
        assert result.fragments[0] == "<p>Done.</p>"
        assert result.fragments[1] == "<p />"
        assert _reassemble(result) == xhtml

    def test_empty_input(self):
        result = extract_block_fragments("")
        assert result.fragments == []
        assert result.prefix == ""
        assert result.suffix == ""

    def test_macro_block(self):
        xhtml = (
            '<ac:structured-macro ac:name="info" ac:schema-version="1">'
            "<ac:rich-text-body><p>Info text</p></ac:rich-text-body>"
            "</ac:structured-macro>"
        )
        result = extract_block_fragments(xhtml)
        assert len(result.fragments) == 1
        assert result.fragments[0] == xhtml
        assert _reassemble(result) == xhtml

    def test_hr_between_blocks(self):
        xhtml = "<p>A</p><hr /><p>B</p>"
        result = extract_block_fragments(xhtml)

        assert len(result.fragments) == 3
        assert result.fragments[0] == "<p>A</p>"
        assert result.fragments[1] == "<hr />"
        assert result.fragments[2] == "<p>B</p>"
        assert _reassemble(result) == xhtml


class TestExtractBlockFragmentsRealTestcases:
    """실제 testcase 파일에 대한 integrity 테스트."""

    @pytest.fixture
    def testcases_dir(self):
        from pathlib import Path

        return Path(__file__).parent / "testcases"

    def test_all_testcases_integrity(self, testcases_dir):
        if not testcases_dir.is_dir():
            pytest.skip("testcases directory not found")

        ok = 0
        for case_dir in sorted(testcases_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            xhtml_path = case_dir / "page.xhtml"
            if not xhtml_path.exists():
                continue

            xhtml = xhtml_path.read_text(encoding="utf-8")
            result = extract_block_fragments(xhtml)
            reassembled = _reassemble(result)
            assert reassembled == xhtml, f"Integrity failed for {case_dir.name}"
            ok += 1

        assert ok >= 21, f"Expected at least 21 testcases, got {ok}"


def _reassemble(result: FragmentExtractionResult) -> str:
    """Fragment extraction result를 재조립한다."""
    text = result.prefix
    for i, frag in enumerate(result.fragments):
        text += frag
        if i < len(result.separators):
            text += result.separators[i]
    text += result.suffix
    return text
