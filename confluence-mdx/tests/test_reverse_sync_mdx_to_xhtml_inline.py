import pytest
from reverse_sync.mdx_to_xhtml_inline import (
    mdx_block_to_inner_xhtml,
    _convert_inline,
    _parse_list_items,
)


# --- _convert_inline 단위 테스트 ---


class TestConvertInline:
    def test_plain_text(self):
        assert _convert_inline("plain text") == "plain text"

    def test_bold(self):
        assert _convert_inline("**bold**") == "<strong>bold</strong>"

    def test_code(self):
        assert _convert_inline("`code`") == "<code>code</code>"

    def test_link(self):
        assert _convert_inline("[text](url)") == '<a href="url">text</a>'

    def test_entities(self):
        """HTML entities는 그대로 유지."""
        assert _convert_inline("A &gt; B") == "A &gt; B"

    def test_mixed(self):
        result = _convert_inline("**Company Name** : text")
        assert result == "<strong>Company Name</strong> : text"

    def test_bold_and_code(self):
        result = _convert_inline("**bold** and `code`")
        assert result == "<strong>bold</strong> and <code>code</code>"

    def test_code_inside_not_bold(self):
        """code span 내부의 **는 bold 처리되지 않는다."""
        result = _convert_inline("`**not bold**`")
        assert result == "<code>**not bold**</code>"

    def test_br_preserved(self):
        """<br/> 태그는 그대로 유지."""
        result = _convert_inline("line1<br/>line2")
        assert result == "line1<br/>line2"


# --- mdx_block_to_inner_xhtml 블록 변환 테스트 ---


class TestBlockConversion:
    def test_heading(self):
        """## Title → Title"""
        result = mdx_block_to_inner_xhtml("## Title\n", "heading")
        assert result == "Title"

    def test_heading_strips_bold(self):
        """heading 내부 **bold**는 마커만 제거."""
        result = mdx_block_to_inner_xhtml("## **Bold Title**\n", "heading")
        assert result == "Bold Title"

    def test_heading_with_code(self):
        """heading 내부 `code`는 변환."""
        result = mdx_block_to_inner_xhtml("## `Config` 설정\n", "heading")
        assert result == "<code>Config</code> 설정"

    def test_paragraph_simple(self):
        result = mdx_block_to_inner_xhtml("Simple paragraph.\n", "paragraph")
        assert result == "Simple paragraph."

    def test_paragraph_with_code(self):
        """`User Attribute` → <code>User Attribute</code>"""
        result = mdx_block_to_inner_xhtml("`User Attribute` 설정\n", "paragraph")
        assert result == "<code>User Attribute</code> 설정"

    def test_paragraph_with_bold(self):
        result = mdx_block_to_inner_xhtml("**bold** text\n", "paragraph")
        assert result == "<strong>bold</strong> text"

    def test_list_bold_items(self):
        """* **Name** : desc → <li><p><strong>Name</strong> : desc</p></li>"""
        content = "* **Name** : desc\n"
        result = mdx_block_to_inner_xhtml(content, "list")
        assert result == "<li><p><strong>Name</strong> : desc</p></li>"

    def test_list_multiple_items(self):
        content = "* item1\n* item2\n"
        result = mdx_block_to_inner_xhtml(content, "list")
        assert result == "<li><p>item1</p></li><li><p>item2</p></li>"

    def test_list_ordered(self):
        content = "1. first\n2. second\n"
        result = mdx_block_to_inner_xhtml(content, "list")
        assert result == "<li><p>first</p></li><li><p>second</p></li>"

    def test_list_with_figure_skip(self):
        """figure 줄은 skip."""
        content = "* item1\n<figure><img src=\"test.png\" /></figure>\n* item2\n"
        result = mdx_block_to_inner_xhtml(content, "list")
        assert result == "<li><p>item1</p></li><li><p>item2</p></li>"

    def test_code_block(self):
        content = "```sql\nSELECT * FROM users;\n```\n"
        result = mdx_block_to_inner_xhtml(content, "code_block")
        assert result == "SELECT * FROM users;"

    def test_code_block_multiline(self):
        content = "```\nline1\nline2\nline3\n```\n"
        result = mdx_block_to_inner_xhtml(content, "code_block")
        assert result == "line1\nline2\nline3"


# --- _parse_list_items 테스트 ---


class TestParseListItems:
    def test_unordered_list(self):
        content = "* item1\n* item2\n"
        items = _parse_list_items(content)
        assert len(items) == 2
        assert items[0]['content'] == 'item1'
        assert items[0]['ordered'] is False
        assert items[1]['content'] == 'item2'

    def test_ordered_list(self):
        content = "1. first\n2. second\n"
        items = _parse_list_items(content)
        assert len(items) == 2
        assert items[0]['content'] == 'first'
        assert items[0]['ordered'] is True

    def test_figure_line_skipped(self):
        content = "* item1\n<figure><img src=\"x.png\" /></figure>\n* item2\n"
        items = _parse_list_items(content)
        assert len(items) == 2

    def test_nested_list(self):
        content = "* parent\n    * child\n"
        items = _parse_list_items(content)
        assert len(items) == 2
        assert items[0]['indent'] == 0
        assert items[1]['indent'] == 4

    def test_dash_marker(self):
        content = "- item1\n- item2\n"
        items = _parse_list_items(content)
        assert len(items) == 2
        assert items[0]['content'] == 'item1'


# --- xhtml_patcher _replace_inner_html 통합 테스트 ---


class TestReplaceInnerHtml:
    def test_patch_with_new_inner_xhtml(self):
        from reverse_sync.xhtml_patcher import patch_xhtml

        xhtml = '<p>Old text</p>'
        patches = [{
            'xhtml_xpath': 'p[1]',
            'old_plain_text': 'Old text',
            'new_inner_xhtml': '<strong>New</strong> text',
        }]
        result = patch_xhtml(xhtml, patches)
        assert '<strong>New</strong> text' in result

    def test_legacy_path_still_works(self):
        from reverse_sync.xhtml_patcher import patch_xhtml

        xhtml = '<p>Old text</p>'
        patches = [{
            'xhtml_xpath': 'p[1]',
            'old_plain_text': 'Old text',
            'new_plain_text': 'New text',
        }]
        result = patch_xhtml(xhtml, patches)
        assert 'New text' in result

    def test_heading_inner_xhtml(self):
        from reverse_sync.xhtml_patcher import patch_xhtml

        xhtml = '<h2>Old Title</h2>'
        patches = [{
            'xhtml_xpath': 'h2[1]',
            'old_plain_text': 'Old Title',
            'new_inner_xhtml': 'New Title',
        }]
        result = patch_xhtml(xhtml, patches)
        assert '<h2>New Title</h2>' in result

    def test_list_inner_xhtml(self):
        from reverse_sync.xhtml_patcher import patch_xhtml

        xhtml = '<ul><li><p>old item</p></li></ul>'
        patches = [{
            'xhtml_xpath': 'ul[1]',
            'old_plain_text': 'old item',
            'new_inner_xhtml': '<li><p>new item1</p></li><li><p>new item2</p></li>',
        }]
        result = patch_xhtml(xhtml, patches)
        assert '<li><p>new item1</p></li>' in result
        assert '<li><p>new item2</p></li>' in result


# --- 중첩 리스트 테스트 ---


class TestNestedList:
    def test_nested_unordered(self):
        content = "* parent\n    * child1\n    * child2\n"
        result = mdx_block_to_inner_xhtml(content, "list")
        assert '<li><p>parent</p><ul>' in result
        assert '<li><p>child1</p></li>' in result
        assert '<li><p>child2</p></li>' in result

    def test_nested_ordered(self):
        content = "1. parent\n    1. child1\n    2. child2\n"
        result = mdx_block_to_inner_xhtml(content, "list")
        assert '<li><p>parent</p><ol>' in result
        assert '<li><p>child1</p></li>' in result
        assert '<li><p>child2</p></li>' in result
