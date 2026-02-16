from mdx_to_storage.parser import parse_mdx


def test_parse_frontmatter_extracts_title():
    text = """---
title: \"Doc Title\"
owner: docs
---

Paragraph
"""
    blocks = parse_mdx(text)
    assert blocks[0].type == "frontmatter"
    assert blocks[0].attrs.get("title") == "Doc Title"


def test_parse_heading_level_detection():
    blocks = parse_mdx("### Heading\n")
    assert blocks[0].type == "heading"
    assert blocks[0].level == 3


def test_parse_code_block_language():
    text = """```python
print('hello')
```
"""
    blocks = parse_mdx(text)
    assert blocks[0].type == "code_block"
    assert blocks[0].language == "python"


def test_parse_hr_block():
    blocks = parse_mdx("______\n")
    assert blocks[0].type == "hr"


def test_parse_callout_block_and_attrs():
    text = """<Callout type=\"info\" emoji=\"🌈\">
Body
</Callout>
"""
    blocks = parse_mdx(text)
    assert blocks[0].type == "callout"
    assert blocks[0].attrs == {"type": "info", "emoji": "🌈"}
    assert len(blocks[0].children) == 1
    assert blocks[0].children[0].type == "paragraph"
    assert blocks[0].children[0].content == "Body\n"


def test_parse_figure_block_and_img_attrs():
    text = """<figure>
  <img src=\"/images/sample.png\" alt=\"Sample\" width=\"700\" data-layout=\"center\">
</figure>
"""
    blocks = parse_mdx(text)
    assert blocks[0].type == "figure"
    assert blocks[0].attrs == {
        "src": "/images/sample.png",
        "alt": "Sample",
        "width": "700",
        "data-layout": "center",
    }


def test_parse_figure_with_caption():
    text = """<figure>
  <img src="/images/sample.png" alt="Sample" width="700" data-layout="center">
  <figcaption>Caption <strong>text</strong></figcaption>
</figure>
"""
    blocks = parse_mdx(text)
    assert blocks[0].type == "figure"
    assert blocks[0].attrs["caption"] == "Caption text"


def test_parse_figure_self_closing_img():
    """Self-closing <img ... /> tag should parse identically."""
    text = """<figure>
  <img src="/images/sample.png" alt="Sample" width="500" />
</figure>
"""
    blocks = parse_mdx(text)
    assert blocks[0].type == "figure"
    assert blocks[0].attrs["src"] == "/images/sample.png"
    assert blocks[0].attrs["width"] == "500"


def test_parse_paragraph_fallback():
    blocks = parse_mdx("one\ntwo\n\n")
    assert blocks[0].type == "paragraph"
    assert blocks[0].content == "one\ntwo\n"


def test_parse_badge_not_html_block():
    blocks = parse_mdx('<Badge color="blue">Active</Badge> status\n')
    assert blocks[0].type == "paragraph"


def test_parse_import_and_empty_blocks():
    text = "import X from 'x'\n\nParagraph\n"
    blocks = parse_mdx(text)
    assert blocks[0].type == "import_statement"
    assert blocks[1].type == "empty"
    assert blocks[2].type == "paragraph"


def test_parse_list_with_continuation_and_blank_line():
    text = "* item1\n  continuation\n\n* item2\n"
    blocks = parse_mdx(text)
    assert blocks[0].type == "list"
    assert "continuation" in blocks[0].content


def test_parse_html_block_stops_before_heading():
    text = "<div>line1\nline2\n## Heading\n"
    blocks = parse_mdx(text)
    assert blocks[0].type == "html_block"
    assert "line2" in blocks[0].content
    assert blocks[1].type == "heading"


def test_parse_callout_children_multiple_blocks():
    text = """<Callout type="important">
first paragraph

```bash
echo hi
```
</Callout>
"""
    blocks = parse_mdx(text)
    callout = blocks[0]
    assert callout.type == "callout"
    assert callout.attrs == {"type": "important"}
    assert [child.type for child in callout.children] == ["paragraph", "empty", "code_block"]


def test_parse_frontmatter_unclosed_falls_through():
    text = "---\ntitle: X\nNo closing\n"
    blocks = parse_mdx(text)
    # 닫히지 않은 frontmatter는 파싱되지 않고 다른 타입으로 처리
    assert blocks[0].type != "frontmatter"


def test_parse_code_block_unclosed_collects_to_end():
    text = "```python\nline1\nline2\n"
    blocks = parse_mdx(text)
    assert blocks[0].type == "code_block"
    assert blocks[0].language == "python"
    assert "line1" in blocks[0].content
    assert "line2" in blocks[0].content


def test_parse_ordered_list_detected():
    text = "1. first\n2. second\n"
    blocks = parse_mdx(text)
    assert blocks[0].type == "list"
    assert "first" in blocks[0].content
    assert "second" in blocks[0].content
