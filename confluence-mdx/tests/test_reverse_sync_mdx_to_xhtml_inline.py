from mdx_to_storage.inline import convert_inline
from reverse_sync.mdx_to_xhtml_inline import (
    mdx_block_to_inner_xhtml,
    _parse_list_items,
)


# --- convert_inline 단위 테스트 ---


class TestConvertInline:
    def test_plain_text(self):
        assert convert_inline("plain text") == "plain text"

    def test_bold(self):
        assert convert_inline("**bold**") == "<strong>bold</strong>"

    def test_code(self):
        assert convert_inline("`code`") == "<code>code</code>"

    def test_link(self):
        assert convert_inline("[text](url)") == '<a href="url">text</a>'

    def test_entities(self):
        """HTML entities는 그대로 유지."""
        assert convert_inline("A &gt; B") == "A &gt; B"

    def test_mixed(self):
        result = convert_inline("**Company Name** : text")
        assert result == "<strong>Company Name</strong> : text"

    def test_bold_and_code(self):
        result = convert_inline("**bold** and `code`")
        assert result == "<strong>bold</strong> and <code>code</code>"

    def test_code_inside_not_bold(self):
        """code span 내부의 **는 bold 처리되지 않는다."""
        result = convert_inline("`**not bold**`")
        assert result == "<code>**not bold**</code>"

    def test_br_preserved(self):
        """<br/> 태그는 <br />로 정규화되어 유지."""
        result = convert_inline("line1<br/>line2")
        assert result == "line1<br />line2"

    def test_code_with_less_than(self):
        """`a < b` → <code>a &lt; b</code>"""
        assert convert_inline("`a < b`") == "<code>a &lt; b</code>"

    def test_code_with_greater_than(self):
        """`a > b` → <code>a &gt; b</code>"""
        assert convert_inline("`a > b`") == "<code>a &gt; b</code>"

    def test_code_with_ampersand(self):
        """`a & b` → <code>a &amp; b</code>"""
        assert convert_inline("`a & b`") == "<code>a &amp; b</code>"

    def test_code_with_html_tag_like_string(self):
        """`<script>` → <code>&lt;script&gt;</code>"""
        assert convert_inline("`<script>`") == "<code>&lt;script&gt;</code>"


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

    def test_heading_with_badge(self):
        """heading 내부 <Badge>는 ac:structured-macro로 변환."""
        result = mdx_block_to_inner_xhtml(
            '#### K8s API Request <Badge color="grey">10.2.2</Badge>\n',
            "heading",
        )
        assert 'K8s API Request ' in result
        assert '<ac:structured-macro ac:name="status">' in result
        assert '<ac:parameter ac:name="title">10.2.2</ac:parameter>' in result
        assert '<ac:parameter ac:name="colour">Grey</ac:parameter>' in result

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

    def test_paragraph_code_html_escape(self):
        """paragraph 내 code span의 < > 이스케이프"""
        result = mdx_block_to_inner_xhtml("`a < b`\n", "paragraph")
        assert result == "<code>a &lt; b</code>"

    def test_heading_code_html_escape(self):
        """heading 내 code span의 HTML 특수문자 이스케이프"""
        result = mdx_block_to_inner_xhtml("## `SELECT * FROM t WHERE x < 10`\n", "heading")
        assert result == "<code>SELECT * FROM t WHERE x &lt; 10</code>"


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

    def test_skip_when_old_plain_text_mismatch(self):
        """old_plain_text와 요소 텍스트가 불일치하면 패치를 건너뛴다."""
        from reverse_sync.xhtml_patcher import patch_xhtml

        xhtml = '<p>Actual content</p>'
        patches = [{
            'xhtml_xpath': 'p[1]',
            'old_plain_text': 'Different text',
            'new_inner_xhtml': '<strong>Should not appear</strong>',
        }]
        result = patch_xhtml(xhtml, patches)
        assert 'Actual content' in result
        assert 'Should not appear' not in result

    def test_skip_preserves_complex_children(self):
        """검증 가드가 Confluence 전용 자식 요소 파괴를 방지한다."""
        from reverse_sync.xhtml_patcher import patch_xhtml

        xhtml = (
            '<p>Paragraph text</p>'
            '<ac:image><ri:attachment ri:filename="img.png"></ri:attachment></ac:image>'
        )
        patches = [{
            'xhtml_xpath': 'ac:image[1]',
            'old_plain_text': 'Not matching text',
            'new_inner_xhtml': 'Wrong replacement',
        }]
        result = patch_xhtml(xhtml, patches)
        assert 'ri:attachment' in result
        assert 'Wrong replacement' not in result


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
        assert '<li><p>parent</p><ol start="1">' in result
        assert '<li><p>child1</p></li>' in result
        assert '<li><p>child2</p></li>' in result


# --- Phase 2: mdx_block_to_xhtml_element 테스트 ---

from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_xhtml_element
from mdx_to_storage.parser import Block as MdxBlock


class TestMdxBlockToXhtmlElement:
    def test_heading_h2(self):
        block = MdxBlock(type='heading', content='## Section Title\n',
                         line_start=1, line_end=1)
        result = mdx_block_to_xhtml_element(block)
        assert result == '<h2>Section Title</h2>'

    def test_heading_h3_with_code(self):
        block = MdxBlock(type='heading', content='### `config` 설정\n',
                         line_start=1, line_end=1)
        result = mdx_block_to_xhtml_element(block)
        assert result == '<h3><code>config</code> 설정</h3>'

    def test_paragraph(self):
        block = MdxBlock(type='paragraph', content='Hello **world**\n',
                         line_start=1, line_end=1)
        result = mdx_block_to_xhtml_element(block)
        assert result == '<p>Hello <strong>world</strong></p>'

    def test_unordered_list(self):
        block = MdxBlock(type='list', content='- item1\n- item2\n',
                         line_start=1, line_end=2)
        result = mdx_block_to_xhtml_element(block)
        assert '<ul>' in result
        assert '<li><p>item1</p></li>' in result
        assert '</ul>' in result

    def test_ordered_list(self):
        block = MdxBlock(type='list', content='1. first\n2. second\n',
                         line_start=1, line_end=2)
        result = mdx_block_to_xhtml_element(block)
        assert '<ol>' in result
        assert '</ol>' in result

    def test_code_block_with_language(self):
        block = MdxBlock(type='code_block',
                         content='```python\nprint("hi")\n```\n',
                         line_start=1, line_end=3)
        result = mdx_block_to_xhtml_element(block)
        assert 'ac:structured-macro' in result
        assert 'ac:name="code"' in result
        assert 'python' in result
        assert 'print("hi")' in result

    def test_code_block_no_language(self):
        block = MdxBlock(type='code_block',
                         content='```\nsome code\n```\n',
                         line_start=1, line_end=3)
        result = mdx_block_to_xhtml_element(block)
        assert 'ac:structured-macro' in result
        assert 'some code' in result

    def test_html_block_passthrough(self):
        block = MdxBlock(type='html_block',
                         content='<div>custom html</div>\n',
                         line_start=1, line_end=1)
        result = mdx_block_to_xhtml_element(block)
        assert '<div>custom html</div>' in result


# --- Badge roundtrip 테스트 (MDX → XHTML → MDX) ---


from bs4 import BeautifulSoup
from converter.core import SingleLineParser
from mdx_to_storage.emitter import emit_block
from mdx_to_storage.parser import parse_mdx


def _emit_heading_xhtml(mdx_content: str) -> str:
    """MDX heading → XHTML (_emit_replacement_fragment 의 emit_block 단계만 재현).

    실제 reverse-sync 에서는 이후 sidecar reconstruction, lost_info 적용이
    추가로 수행되지만, Badge-only heading 에서는 해당 단계가 개입하지 않는다.
    """
    blocks = [b for b in parse_mdx(mdx_content) if b.type != 'empty']
    assert len(blocks) == 1 and blocks[0].type == 'heading'
    return emit_block(blocks[0])


def _fc_heading_to_mdx(xhtml_heading: str) -> str:
    """FC의 heading 변환을 재현: XHTML <hN>...</hN> → MDX heading line."""
    soup = BeautifulSoup(xhtml_heading, 'html.parser')
    heading = soup.find(True)
    parser = SingleLineParser(heading)
    parser.convert_recursively(heading)
    return ''.join(parser.markdown_lines)


class TestBadgeRoundtrip:
    """Badge 추가/변경/삭제가 XHTML에 반영되고 roundtrip 검증을 통과하는지 확인한다."""

    def test_add_badge(self):
        """Badge가 없던 heading에 Badge 추가 → XHTML에 status macro 생성 → MDX 복원."""
        xhtml = _emit_heading_xhtml(
            '#### K8s API Request <Badge color="grey">10.2.2</Badge>\n')

        # XHTML에 status macro가 생성되었는지 확인
        assert '<ac:structured-macro ac:name="status">' in xhtml
        assert '<ac:parameter ac:name="title">10.2.2</ac:parameter>' in xhtml

        # roundtrip: XHTML → FC → MDX
        mdx = _fc_heading_to_mdx(xhtml)
        assert mdx == '#### K8s API Request <Badge color="grey">10.2.2</Badge>'

    def test_change_badge_color(self):
        """Badge 컬러 변경 (grey → green) → XHTML 반영 → MDX 복원."""
        xhtml = _emit_heading_xhtml(
            '#### Status <Badge color="green">Active</Badge>\n')

        assert '<ac:parameter ac:name="colour">Green</ac:parameter>' in xhtml

        mdx = _fc_heading_to_mdx(xhtml)
        assert mdx == '#### Status <Badge color="green">Active</Badge>'

    def test_change_badge_text(self):
        """Badge 텍스트 변경 (10.2.2 → 11.0.0) → XHTML 반영 → MDX 복원."""
        xhtml = _emit_heading_xhtml(
            '#### Data Access <Badge color="grey">11.0.0</Badge>\n')

        assert '<ac:parameter ac:name="title">11.0.0</ac:parameter>' in xhtml

        mdx = _fc_heading_to_mdx(xhtml)
        assert mdx == '#### Data Access <Badge color="grey">11.0.0</Badge>'

    def test_remove_badge(self):
        """Badge 삭제 → XHTML에 status macro 없음 → MDX에 Badge 없음.

        heading은 _CLEAN_BLOCK_TYPES로 replace_fragment 전략을 사용하므로,
        improved MDX 기준으로 XHTML이 전체 재생성된다. 원본 XHTML에
        status macro가 있었더라도 패치 결과에 영향을 주지 않는다.
        """
        xhtml = _emit_heading_xhtml('#### K8s API Request\n')

        assert 'ac:structured-macro' not in xhtml
        assert '<h3>K8s API Request</h3>' == xhtml

        mdx = _fc_heading_to_mdx(xhtml)
        assert mdx == '#### K8s API Request'
