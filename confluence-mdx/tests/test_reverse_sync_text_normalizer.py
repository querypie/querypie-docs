"""text_normalizer 유닛 테스트."""
import pytest
from reverse_sync.text_normalizer import (
    normalize_mdx_to_plain,
    collapse_ws,
    strip_list_marker,
    strip_for_compare,
)


class TestCollapseWs:
    def test_single_space(self):
        assert collapse_ws('hello world') == 'hello world'

    def test_multiple_spaces(self):
        assert collapse_ws('hello   world') == 'hello world'

    def test_tabs_and_newlines(self):
        assert collapse_ws('hello\t\n  world') == 'hello world'

    def test_leading_trailing(self):
        assert collapse_ws('  hello world  ') == 'hello world'

    def test_empty_string(self):
        assert collapse_ws('') == ''


class TestStripListMarker:
    def test_dash_marker(self):
        assert strip_list_marker('-item') == 'item'

    def test_asterisk_marker(self):
        assert strip_list_marker('*item') == 'item'

    def test_plus_marker(self):
        assert strip_list_marker('+item') == 'item'

    def test_numbered_marker(self):
        assert strip_list_marker('1.item') == 'item'

    def test_multi_digit_number(self):
        assert strip_list_marker('12.item') == 'item'

    def test_no_marker(self):
        assert strip_list_marker('item') == 'item'


class TestStripForCompare:
    def test_removes_regular_whitespace(self):
        assert strip_for_compare('hello world') == 'helloworld'

    def test_removes_zwsp(self):
        assert strip_for_compare('hello\u200bworld') == 'helloworld'

    def test_removes_hangul_filler(self):
        assert strip_for_compare('hello\u3164world') == 'helloworld'

    def test_removes_nbsp(self):
        assert strip_for_compare('hello\xa0world') == 'helloworld'

    def test_removes_ideographic_space(self):
        assert strip_for_compare('hello\u3000world') == 'helloworld'

    def test_removes_soft_hyphen(self):
        assert strip_for_compare('hello\u00adworld') == 'helloworld'

    def test_removes_bom(self):
        assert strip_for_compare('\ufeffhello') == 'hello'

    def test_removes_word_joiner(self):
        assert strip_for_compare('hello\u2060world') == 'helloworld'

    def test_removes_mixed_invisible(self):
        text = 'a\u200b \u3164\t\u00adb'
        assert strip_for_compare(text) == 'ab'

    def test_empty_string(self):
        assert strip_for_compare('') == ''

    def test_only_invisible(self):
        assert strip_for_compare('\u200b \u3164') == ''

    def test_preserves_visible_chars(self):
        assert strip_for_compare('abc123') == 'abc123'


class TestNormalizeMdxToPlain:
    def test_heading_strips_hashes(self):
        assert normalize_mdx_to_plain('## Hello', 'heading') == 'Hello'

    def test_heading_strips_bold(self):
        assert normalize_mdx_to_plain('# **Bold Title**', 'heading') == 'Bold Title'

    def test_heading_strips_code(self):
        assert normalize_mdx_to_plain('## `code` Title', 'heading') == 'code Title'

    def test_heading_strips_html_tags(self):
        assert normalize_mdx_to_plain('# Title <br/>', 'heading') == 'Title'

    def test_heading_unescapes_html(self):
        assert normalize_mdx_to_plain('# A &amp; B', 'heading') == 'A & B'

    def test_paragraph_strips_markdown(self):
        result = normalize_mdx_to_plain('**bold** and `code`', 'paragraph')
        assert result == 'bold and code'

    def test_paragraph_strips_link(self):
        result = normalize_mdx_to_plain('[Title](http://example.com)', 'paragraph')
        assert result == 'Title'

    def test_paragraph_confluence_link_with_anchor(self):
        result = normalize_mdx_to_plain(
            '[Title | Anchor](http://example.com)', 'paragraph')
        assert result == 'Title'

    def test_paragraph_strips_italic(self):
        result = normalize_mdx_to_plain('*italic* text', 'paragraph')
        assert result == 'italic text'

    def test_paragraph_skips_figure_lines(self):
        content = '<figure>\n<img src="test.png" />\n</figure>\nText here'
        result = normalize_mdx_to_plain(content, 'paragraph')
        assert result == 'Text here'

    def test_paragraph_skips_empty_lines(self):
        result = normalize_mdx_to_plain('line1\n\nline2', 'paragraph')
        assert result == 'line1 line2'

    def test_list_strips_marker(self):
        result = normalize_mdx_to_plain('- item one\n- item two', 'list')
        assert result == 'item one item two'

    def test_numbered_list_strips_marker(self):
        result = normalize_mdx_to_plain('1. first\n2. second', 'list')
        assert result == 'first second'

    def test_table_row_extracts_cells(self):
        content = '| col1 | col2 |\n| --- | --- |\n| a | b |'
        result = normalize_mdx_to_plain(content, 'paragraph')
        assert result == 'col1 col2 a b'

    def test_unescapes_html_entities(self):
        result = normalize_mdx_to_plain('A &lt; B &amp; C', 'paragraph')
        assert result == 'A < B & C'

    def test_strips_html_tags(self):
        # tag 제거 후 양쪽 공백이 남아 'text  more'가 됨 (join 전 strip으로 정리)
        result = normalize_mdx_to_plain('text <br/> more', 'paragraph')
        assert result == 'text  more'
