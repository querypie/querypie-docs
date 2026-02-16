from mdx_to_storage import emit_document, parse_mdx
from mdx_to_storage.emitter import emit_block
from mdx_to_storage.parser import Block


def test_emit_heading_level_adjustment():
    blocks = parse_mdx("## Section\n")
    xhtml = emit_document(blocks)
    assert xhtml == "<h1>Section</h1>"


def test_emit_page_title_skip_when_frontmatter_title_matches():
    mdx = """---
title: "Doc Title"
---
# Doc Title
## Keep Me
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<h0>" not in xhtml
    assert "<h1>Doc Title</h1>" not in xhtml
    assert "<h1>Keep Me</h1>" in xhtml


def test_emit_code_block_with_cdata_and_language():
    mdx = """```python
print("hello")
```
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert '<ac:structured-macro ac:name="code">' in xhtml
    assert '<ac:parameter ac:name="language">python</ac:parameter>' in xhtml
    assert "<ac:plain-text-body><![CDATA[print(\"hello\")]]></ac:plain-text-body>" in xhtml


def test_emit_code_block_without_language():
    mdx = """```
some code
```
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert '<ac:structured-macro ac:name="code">' in xhtml
    assert '<ac:parameter ac:name="language">' not in xhtml
    assert "<ac:plain-text-body><![CDATA[some code]]></ac:plain-text-body>" in xhtml


def test_emit_list_ul_and_ol():
    ul = emit_document(parse_mdx("* a\n* b\n"))
    ol = emit_document(parse_mdx("1. a\n2. b\n"))
    assert ul == "<ul><li><p>a</p></li><li><p>b</p></li></ul>"
    assert ol == "<ol><li><p>a</p></li><li><p>b</p></li></ol>"


def test_emit_hr():
    xhtml = emit_document(parse_mdx("______\n"))
    assert xhtml == "<hr />"


def test_emit_paragraph_with_inline():
    mdx = "This is **bold** and `code` text.\n"
    xhtml = emit_document(parse_mdx(mdx))
    assert xhtml == "<p>This is <strong>bold</strong> and <code>code</code> text.</p>"


def test_emit_html_block_passthrough():
    html = '<div class="custom">content</div>'
    block = Block(type="html_block", content=html)
    result = emit_block(block)
    assert result == html


def test_emit_frontmatter_import_empty_skip():
    block_fm = Block(type="frontmatter", content="---\ntitle: Test\n---", attrs={"title": "Test"})
    block_imp = Block(type="import_statement", content="import X from 'y'")
    block_empty = Block(type="empty", content="")
    assert emit_block(block_fm) == ""
    assert emit_block(block_imp) == ""
    assert emit_block(block_empty) == ""


def test_emit_document_mixed_blocks():
    mdx = """---
title: "My Page"
---

import { Callout } from 'nextra/components'

# My Page

## Introduction

Welcome to the **documentation**.

* item one
* item two

```bash
echo hello
```

______
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<h1>Introduction</h1>" in xhtml
    assert "<p>Welcome to the <strong>documentation</strong>.</p>" in xhtml
    assert "<ul><li><p>item one</p></li><li><p>item two</p></li></ul>" in xhtml
    assert '<ac:parameter ac:name="language">bash</ac:parameter>' in xhtml
    assert "<![CDATA[echo hello]]>" in xhtml
    assert "<hr />" in xhtml
    # frontmatter, import, page title(# My Page)은 출력에 미포함
    assert "My Page" not in xhtml
    assert "import" not in xhtml


def test_emit_paragraph_multiline_joins_with_space():
    mdx = "line one\nline two\n"
    xhtml = emit_document(parse_mdx(mdx))
    assert xhtml == "<p>line one line two</p>"


def test_emit_list_with_continuation_line():
    mdx = "* first line\n  continued line\n* second\n"
    xhtml = emit_document(parse_mdx(mdx))
    assert xhtml == "<ul><li><p>first line continued line</p></li><li><p>second</p></li></ul>"


def test_emit_unknown_block_type_returns_empty():
    block = Block(type="unknown", content="x")
    assert emit_block(block) == ""


def test_emit_heading_level1_without_frontmatter_emits_h1():
    """# Heading (level 1) without matching frontmatter title → <h1> (clamped)."""
    mdx = "# NonTitle\n"
    xhtml = emit_document(parse_mdx(mdx))
    assert xhtml == "<h1>NonTitle</h1>"


def test_emit_heading_level6_emits_h5():
    """###### Heading (level 6) → <h5> (level - 1 = 5)."""
    mdx = "###### Deep\n"
    xhtml = emit_document(parse_mdx(mdx))
    assert xhtml == "<h5>Deep</h5>"


def test_emit_callout_type_mapping_default_to_tip():
    mdx = """<Callout type="default">
Tip body
</Callout>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert (
        xhtml
        == '<ac:structured-macro ac:name="tip"><ac:rich-text-body><p>Tip body</p></ac:rich-text-body></ac:structured-macro>'
    )


def test_emit_callout_type_mapping_info_important_error():
    info = emit_document(parse_mdx('<Callout type="info">\nInfo\n</Callout>\n'))
    important = emit_document(parse_mdx('<Callout type="important">\nImportant\n</Callout>\n'))
    error = emit_document(parse_mdx('<Callout type="error">\nError\n</Callout>\n'))
    assert '<ac:structured-macro ac:name="info">' in info
    assert '<ac:structured-macro ac:name="note">' in important
    assert '<ac:structured-macro ac:name="warning">' in error


def test_emit_callout_with_emoji_as_panel():
    mdx = """<Callout type="info" emoji="🌈">
Panel body
</Callout>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert '<ac:structured-macro ac:name="panel">' in xhtml
    assert '<ac:parameter ac:name="panelIcon">🌈</ac:parameter>' in xhtml
    assert "<p>Panel body</p>" in xhtml


def test_emit_callout_body_supports_code_block():
    mdx = """<Callout type="important">
```sql
select 1;
```
</Callout>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert '<ac:structured-macro ac:name="note">' in xhtml
    assert '<ac:structured-macro ac:name="code">' in xhtml
    assert '<ac:parameter ac:name="language">sql</ac:parameter>' in xhtml
    assert "<![CDATA[select 1;]]>" in xhtml
