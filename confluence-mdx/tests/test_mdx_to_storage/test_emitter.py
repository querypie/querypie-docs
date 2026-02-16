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


def test_emit_callout_no_type_defaults_to_tip():
    """<Callout> without type attribute → defaults to 'default' → 'tip' macro."""
    mdx = "<Callout>\nBody\n</Callout>\n"
    xhtml = emit_document(parse_mdx(mdx))
    assert '<ac:structured-macro ac:name="tip">' in xhtml
    assert "<p>Body</p>" in xhtml


def test_emit_callout_unknown_type_defaults_to_tip():
    """<Callout type="custom"> with unmapped type → fallback to 'tip'."""
    mdx = '<Callout type="custom">\nBody\n</Callout>\n'
    xhtml = emit_document(parse_mdx(mdx))
    assert '<ac:structured-macro ac:name="tip">' in xhtml


def test_emit_callout_body_with_inline_markup():
    mdx = '<Callout type="info">\nThis is **bold** and `code`.\n</Callout>\n'
    xhtml = emit_document(parse_mdx(mdx))
    assert "<p>This is <strong>bold</strong> and <code>code</code>.</p>" in xhtml


def test_emit_callout_body_multiple_paragraphs():
    mdx = """<Callout type="info">
First paragraph.

Second paragraph.
</Callout>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<p>First paragraph.</p>" in xhtml
    assert "<p>Second paragraph.</p>" in xhtml
    assert '<ac:structured-macro ac:name="info">' in xhtml


def test_emit_figure_to_ac_image_with_width():
    mdx = """<figure>
  <img src="/images/path/sample.png" alt="Sample" width="700" data-layout="center">
</figure>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert (
        xhtml
        == '<ac:image ac:align="center" ac:width="700"><ri:attachment ri:filename="sample.png"></ri:attachment></ac:image>'
    )


def test_emit_figure_with_caption():
    mdx = """<figure>
  <img src="/images/path/sample.png" alt="Sample">
  <figcaption>This is **caption**</figcaption>
</figure>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert '<ac:image ac:align="center">' in xhtml
    assert '<ri:attachment ri:filename="sample.png"></ri:attachment>' in xhtml
    assert "<ac:caption><p>This is <strong>caption</strong></p></ac:caption>" in xhtml


def test_emit_figure_without_src_is_skipped():
    block = Block(type="figure", content="<figure></figure>", attrs={})
    assert emit_block(block) == ""


def test_emit_figure_without_width_minimal():
    """Figure with src only (no width, no caption) → ac:image without ac:width."""
    mdx = """<figure>
  <img src="/images/sample.png" alt="Alt">
</figure>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert (
        xhtml
        == '<ac:image ac:align="center"><ri:attachment ri:filename="sample.png"></ri:attachment></ac:image>'
    )
    assert "ac:width" not in xhtml


def test_emit_figure_in_mixed_document():
    """Figure block integrated with other blocks in a full document."""
    mdx = """---
title: "Page"
---

# Page

## Overview

Some text.

<figure>
  <img src="/images/path/diagram.png" alt="Diagram" width="600">
  <figcaption>Architecture diagram</figcaption>
</figure>

More text after image.
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<h1>Overview</h1>" in xhtml
    assert "<p>Some text.</p>" in xhtml
    assert '<ac:image ac:align="center" ac:width="600">' in xhtml
    assert '<ri:attachment ri:filename="diagram.png">' in xhtml
    assert "<ac:caption><p>Architecture diagram</p></ac:caption>" in xhtml
    assert "<p>More text after image.</p>" in xhtml
    # frontmatter and page title should be excluded
    assert "Page" not in xhtml


def test_emit_nested_unordered_list():
    mdx = """* parent
    * child
    * child-2
* parent-2
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert (
        xhtml
        == "<ul><li><p>parent</p><ul><li><p>child</p></li><li><p>child-2</p></li></ul></li><li><p>parent-2</p></li></ul>"
    )


def test_emit_nested_mixed_ordered_unordered_list():
    mdx = """1. step one
    * detail a
    * detail b
2. step two
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert (
        xhtml
        == "<ol><li><p>step one</p><ul><li><p>detail a</p></li><li><p>detail b</p></li></ul></li><li><p>step two</p></li></ol>"
    )


def test_emit_same_depth_mixed_marker_splits_lists():
    mdx = """* bullet
1. ordered
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert xhtml == "<ul><li><p>bullet</p></li></ul><ol><li><p>ordered</p></li></ol>"


def test_emit_nested_three_levels_deep():
    """Three-level nesting: root → child → grandchild."""
    mdx = """* root
    * child
        * grandchild
    * child-2
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<ul><li><p>root</p>" in xhtml
    assert "<ul><li><p>child</p><ul><li><p>grandchild</p></li></ul></li>" in xhtml
    assert "<li><p>child-2</p></li></ul></li></ul>" in xhtml


def test_emit_nested_list_continuation_line():
    """Continuation line in a nested list item appends to parent item text."""
    mdx = """* parent
    * child first line
      continued line
    * child-2
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<p>child first line continued line</p>" in xhtml
    assert "<p>child-2</p>" in xhtml


def test_emit_nested_list_with_inline_markup():
    """Inline bold/code in nested list items are converted."""
    mdx = """* **bold** parent
    * child with `code`
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<p><strong>bold</strong> parent</p>" in xhtml
    assert "<p>child with <code>code</code></p>" in xhtml


def test_emit_markdown_table_to_xhtml_table():
    mdx = """| Name | Desc |
| --- | --- |
| A | **bold** |
| C | `code` |
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert xhtml.startswith("<table><tbody><tr>")
    assert "<th><p>Name</p></th>" in xhtml
    assert "<td><p>A</p></td>" in xhtml
    assert "<td><p><strong>bold</strong></p></td>" in xhtml
    assert "<td><p><code>code</code></p></td>" in xhtml
    assert xhtml.endswith("</tbody></table>")


def test_emit_html_table_applies_inline_conversion_in_cells():
    mdx = """<table>
<tbody>
<tr><td>**bold** and `code`</td><td>plain</td></tr>
</tbody>
</table>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<table>" in xhtml
    assert "<td><strong>bold</strong> and <code>code</code></td>" in xhtml
    assert "<td>plain</td>" in xhtml


def test_emit_html_table_keeps_nested_html_in_cells():
    mdx = """<table>
<tbody>
<tr><td><p>**not converted here**</p></td></tr>
</tbody>
</table>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<td><p>**not converted here**</p></td>" in xhtml


def test_emit_markdown_table_with_empty_cells():
    mdx = """| Name | Version |
| --- | --- |
| A | 1.0 |
| B |  |
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<td><p>A</p></td>" in xhtml
    assert "<td><p></p></td>" in xhtml


def test_emit_markdown_table_with_alignment_markers():
    mdx = """| Left | Center | Right |
| :--- | :---: | ---: |
| a | b | c |
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<th><p>Left</p></th>" in xhtml
    assert "<td><p>a</p></td>" in xhtml
    assert "<td><p>c</p></td>" in xhtml


def test_emit_markdown_table_with_bold_headers():
    """Confluence header cells use <strong> — MDX bold markers should convert."""
    mdx = """| **Name** | **Desc** |
| --- | --- |
| A | B |
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<th><p><strong>Name</strong></p></th>" in xhtml
    assert "<th><p><strong>Desc</strong></p></th>" in xhtml


def test_emit_paragraph_then_markdown_table():
    mdx = """Intro paragraph.

| A | B |
| --- | --- |
| 1 | 2 |
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert "<p>Intro paragraph.</p>" in xhtml
    assert "<table><tbody>" in xhtml
    assert "<td><p>1</p></td>" in xhtml
