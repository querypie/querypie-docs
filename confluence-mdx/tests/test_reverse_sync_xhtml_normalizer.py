"""Level 0 helper tests for reverse_sync.xhtml_normalizer."""

import json
from pathlib import Path

import pytest

from reverse_sync.xhtml_normalizer import (
    extract_fragment_by_xpath,
    extract_plain_text,
    normalize_fragment,
)


TESTCASES_DIR = Path(__file__).parent / "testcases"


class TestExtractPlainText:
    def test_simple_paragraph(self):
        assert extract_plain_text("<p>Hello world</p>") == "Hello world"

    def test_paragraph_with_bold(self):
        assert extract_plain_text("<p>A <strong>bold</strong> text</p>") == "A bold text"

    def test_paragraph_with_link_body_text(self):
        fragment = '<p>See <a href="http://example.com">example</a> here</p>'
        assert extract_plain_text(fragment) == "See example here"

    def test_paragraph_with_inline_image_excluded(self):
        fragment = (
            '<p>A <ac:image ac:align="center">'
            '<ri:attachment ri:filename="test.png" />'
            "</ac:image> B</p>"
        )
        assert extract_plain_text(fragment) == "A  B"

    def test_paragraph_with_inline_link_excluded(self):
        fragment = (
            '<p>Before <ac:link><ri:page ri:content-title="Page" />'
            "<ac:link-body>Shown</ac:link-body></ac:link> After</p>"
        )
        assert extract_plain_text(fragment) == "Before  After"

    def test_paragraph_with_emoticon(self):
        fragment = (
            '<p><ac:emoticon ac:name="tick" ac:emoji-fallback=":check_mark:" />'
            " Success</p>"
        )
        assert extract_plain_text(fragment) == ":check_mark: Success"

    def test_code_macro_body_excluded(self):
        fragment = (
            '<ac:structured-macro ac:name="code">'
            '<ac:parameter ac:name="language">python</ac:parameter>'
            '<ac:plain-text-body><![CDATA[print("hello")]]></ac:plain-text-body>'
            "</ac:structured-macro>"
        )
        assert extract_plain_text(fragment).strip() == "python"

    def test_adf_extension_callout_joins_child_blocks_with_spaces(self):
        fragment = (
            "<ac:adf-extension>"
            '<ac:adf-node type="panel">'
            '<ac:adf-attribute key="panel-type">note</ac:adf-attribute>'
            "<ac:adf-content><p>First</p><p>Second</p></ac:adf-content>"
            "</ac:adf-node>"
            "</ac:adf-extension>"
        )
        assert extract_plain_text(fragment) == "First Second"

    def test_empty_fragment(self):
        assert extract_plain_text("") == ""
        assert extract_plain_text("<p />") == ""

    def test_callout_joins_child_blocks_with_spaces(self):
        fragment = (
            '<ac:structured-macro ac:name="info">'
            "<ac:rich-text-body><p>First</p><p>Second</p></ac:rich-text-body>"
            "</ac:structured-macro>"
        )
        assert extract_plain_text(fragment) == "First Second"

    def test_emoticon_fallback_inside_layout(self):
        xhtml = (
            "<ac:layout><ac:layout-section><ac:layout-cell>"
            '<p>Hello <ac:emoticon ac:emoji-fallback="🔎"></ac:emoticon></p>'
            "</ac:layout-cell></ac:layout-section></ac:layout>"
        )
        assert extract_plain_text(xhtml) == "Hello 🔎"


class TestExtractPlainTextFromFixtures:
    @pytest.fixture
    def sidecar_blocks(self):
        path = TESTCASES_DIR / "544113141" / "expected.roundtrip.json"
        if not path.exists():
            pytest.skip("testcase fixture not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["blocks"]

    def test_heading_fragment(self, sidecar_blocks):
        block = sidecar_blocks[0]
        assert block["xhtml_xpath"] == "h2[1]"
        assert extract_plain_text(block["xhtml_fragment"]) == "Overview"

    def test_paragraph_fragment(self, sidecar_blocks):
        block = sidecar_blocks[1]
        assert block["xhtml_xpath"] == "p[1]"
        assert "조직에서 관리하는 DB 커넥션" in extract_plain_text(block["xhtml_fragment"])


class TestNormalizeFragment:
    def test_attribute_order_irrelevant(self):
        left = '<p id="x" class="y">text</p>'
        right = '<p class="y" id="x">text</p>'
        assert normalize_fragment(left) == normalize_fragment(right)

    def test_ignored_attributes_stripped(self):
        fragment = (
            '<ac:image ac:macro-id="123" ac:align="center">'
            '<ri:attachment ri:filename="test.png" /></ac:image>'
        )
        result = normalize_fragment(fragment)
        assert "ac:macro-id" not in result
        assert 'ac:align="center"' in result

    def test_layout_sections_unwrapped(self):
        fragment = (
            "<ac:layout><ac:layout-section><ac:layout-cell>"
            "<p>content</p>"
            "</ac:layout-cell></ac:layout-section></ac:layout>"
        )
        result = normalize_fragment(fragment)
        assert "ac:layout" not in result
        assert "content" in result

    def test_nonreversible_macros_removed(self):
        fragment = '<ac:structured-macro ac:name="toc"></ac:structured-macro><p>keep</p>'
        result = normalize_fragment(fragment)
        assert "toc" not in result
        assert "keep" in result

    def test_strip_ignored_attrs_option(self):
        fragment = '<ac:image ac:macro-id="123" ac:align="center" />'
        with_strip = normalize_fragment(fragment, strip_ignored_attrs=True)
        without_strip = normalize_fragment(fragment, strip_ignored_attrs=False)
        assert "ac:macro-id" not in with_strip
        assert "ac:macro-id" in without_strip

    def test_empty_paragraph_is_removed(self):
        assert normalize_fragment("<p />") == ""


class TestExtractFragmentByXpath:
    def test_simple_xpath(self):
        xhtml = "<h2>Title</h2><p>Para 1</p><p>Para 2</p>"
        assert extract_fragment_by_xpath(xhtml, "p[2]") == "<p>Para 2</p>"

    def test_macro_child_xpath(self):
        xhtml = (
            '<ac:structured-macro ac:name="info">'
            "<ac:rich-text-body><p>First</p><p><strong>Second</strong></p></ac:rich-text-body>"
            "</ac:structured-macro>"
        )
        assert extract_fragment_by_xpath(xhtml, "macro-info[1]/p[2]") == "<p><strong>Second</strong></p>"

    def test_missing_xpath_returns_none(self):
        assert extract_fragment_by_xpath("<p>Only</p>", "p[2]") is None

    def test_invalid_xpath_segment_raises_value_error(self):
        with pytest.raises(ValueError, match="invalid xpath segment"):
            extract_fragment_by_xpath("<p>Only</p>", "not-an-index")

    def test_invalid_nested_xpath_segment_raises_value_error(self):
        xhtml = (
            '<ac:structured-macro ac:name="info">'
            "<ac:rich-text-body><p>First</p></ac:rich-text-body>"
            "</ac:structured-macro>"
        )
        with pytest.raises(ValueError, match="invalid xpath segment"):
            extract_fragment_by_xpath(xhtml, "macro-info[1]/bad-segment")
