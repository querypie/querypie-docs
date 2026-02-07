import pytest
from reverse_sync.mdx_block_parser import MdxBlock, parse_mdx_blocks


def test_parse_simple_document():
    mdx = """---
title: 'Test'
---

# Test Title

First paragraph.

## Section

Second paragraph.
"""
    blocks = parse_mdx_blocks(mdx)

    assert blocks[0].type == "frontmatter"
    assert blocks[0].line_start == 1
    assert blocks[0].line_end == 3

    # empty line after frontmatter
    assert blocks[1].type == "empty"

    assert blocks[2].type == "heading"
    assert blocks[2].content == "# Test Title\n"

    assert blocks[3].type == "empty"

    assert blocks[4].type == "paragraph"
    assert blocks[4].content == "First paragraph.\n"

    assert blocks[5].type == "empty"

    assert blocks[6].type == "heading"
    assert blocks[6].content == "## Section\n"

    assert blocks[7].type == "empty"

    assert blocks[8].type == "paragraph"
    assert blocks[8].content == "Second paragraph.\n"


def test_parse_code_block():
    mdx = """## Example

```python
def hello():
    print("world")
```

Next paragraph.
"""
    blocks = parse_mdx_blocks(mdx)
    code = [b for b in blocks if b.type == "code_block"][0]
    assert "def hello():" in code.content
    assert code.type == "code_block"


def test_parse_html_table():
    mdx = """## Table

<table>
<tbody>
<tr>
<td>cell</td>
</tr>
</tbody>
</table>

After table.
"""
    blocks = parse_mdx_blocks(mdx)
    html = [b for b in blocks if b.type == "html_block"][0]
    assert "<table>" in html.content
    assert "</table>" in html.content


def test_parse_list():
    mdx = """## Items

* item 1
* item 2
    * nested

After list.
"""
    blocks = parse_mdx_blocks(mdx)
    lst = [b for b in blocks if b.type == "list"][0]
    assert "* item 1" in lst.content
    assert "    * nested" in lst.content


def test_roundtrip_content():
    """파싱한 블록의 content를 합치면 원본과 동일해야 한다."""
    mdx = """---
title: 'Test'
---

# Title

Paragraph one.

## Section

* list item

```python
code
```

<table>
<tr><td>cell</td></tr>
</table>

End.
"""
    blocks = parse_mdx_blocks(mdx)
    reconstructed = ''.join(b.content for b in blocks)
    assert reconstructed == mdx


from pathlib import Path

def test_parse_real_testcase_793608206():
    """실제 expected.mdx 파일로 roundtrip 검증."""
    mdx_path = Path(__file__).parent / "testcases" / "793608206" / "expected.mdx"
    if not mdx_path.exists():
        pytest.skip("Test case file not found")
    mdx = mdx_path.read_text()
    blocks = parse_mdx_blocks(mdx)
    reconstructed = ''.join(b.content for b in blocks)
    assert reconstructed == mdx
