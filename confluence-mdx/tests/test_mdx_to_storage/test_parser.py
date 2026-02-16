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


def test_parse_paragraph_fallback():
    blocks = parse_mdx("one\ntwo\n\n")
    assert blocks[0].type == "paragraph"
    assert blocks[0].content == "one\ntwo\n"


def test_parse_badge_not_html_block():
    blocks = parse_mdx('<Badge color="blue">Active</Badge> status\n')
    assert blocks[0].type == "paragraph"
