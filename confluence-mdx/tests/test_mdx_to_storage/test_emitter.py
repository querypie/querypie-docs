from mdx_to_storage import emit_document, parse_mdx


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


def test_emit_list_ul_and_ol():
    ul = emit_document(parse_mdx("* a\n* b\n"))
    ol = emit_document(parse_mdx("1. a\n2. b\n"))
    assert ul == "<ul><li><p>a</p></li><li><p>b</p></li></ul>"
    assert ol == "<ol><li><p>a</p></li><li><p>b</p></li></ol>"


def test_emit_hr():
    xhtml = emit_document(parse_mdx("______\n"))
    assert xhtml == "<hr />"
