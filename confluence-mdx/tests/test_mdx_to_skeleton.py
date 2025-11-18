#!/usr/bin/env python3
"""
Unit tests for mdx_to_skeleton.py

This test suite validates all modules and functions in mdx_to_skeleton.py:
- ContentProtector class
- TextProcessor class
- Utility functions (process_yaml_frontmatter, process_text_line, etc.)
- convert_mdx_to_skeleton function

Usage:
    cd confluence-mdx/tests
    python3 -m pytest test_mdx_to_skeleton.py -v
    # or
    python3 test_mdx_to_skeleton.py
"""

import sys
import os
from pathlib import Path

# Add the bin directory to the path so we can import mdx_to_skeleton
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from mdx_to_skeleton import (
    ContentProtector,
    process_yaml_frontmatter,
    convert_mdx_to_skeleton,
)


# ============================================================================
# ContentProtector Tests
# ============================================================================

def test_content_protector_extract_yaml_frontmatter():
    """Test YAML frontmatter extraction"""
    protector = ContentProtector()
    
    # Test with YAML frontmatter
    text = "---\ntitle: 'Hello World'\n---\n\nContent here"
    result, yaml_section = protector.extract_yaml_frontmatter(text)
    
    assert yaml_section is not None
    assert yaml_section.content == "title: 'Hello World'"
    assert yaml_section.placeholder == "__YAML_FRONTMATTER__"
    assert "__YAML_FRONTMATTER__" in result
    assert "title: 'Hello World'" not in result
    
    # Test without YAML frontmatter
    text = "No frontmatter here"
    result, yaml_section = protector.extract_yaml_frontmatter(text)
    assert yaml_section is None
    assert result == text


def test_content_protector_extract_code_blocks():
    """Test code block extraction"""
    # Note: extract_code_blocks method has been removed. Code blocks are now handled
    # directly by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
Some text
```python
print('hello')
```
More text
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """
_TEXT_
```python
print('hello')
```
_TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_content_protector_extract_inline_code():
    """Test inline code extraction"""
    # Note: inline code text is now converted to _TEXT_ (not preserved as-is)
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("Use `print()` function")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """_TEXT_ `_TEXT_` _TEXT_"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_content_protector_extract_urls():
    """Test URL extraction from links and images"""
    # Note: extract_urls method has been removed. URLs are now handled
    # directly by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        # Test regular link
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("Visit [Google](https://google.com)")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """_TEXT_ [_TEXT_](https://google.com)"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_content_protector_extract_image_links():
    """Test image link extraction (now integrated in extract_urls)"""
    # Note: extract_urls method has been removed. Image links are now handled
    # directly by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("![Alt text](/path/to/image.png)")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """![_TEXT_](/path/to/image.png)"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_content_protector_extract_html_entities():
    """Test HTML entity extraction"""
    # Note: extract_html_entities method has been removed. HTML entities are now handled
    # directly by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    # HTML entities are preserved as-is according to the implementation.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("Use &amp; and &lt; symbols")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """_TEXT_ &amp; _TEXT_ &lt; _TEXT_"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_content_protector_restore_all():
    """Test restoration of all protected sections"""
    # Note: extract_inline_code and extract_urls methods have been removed.
    # Test via convert_mdx_to_skeleton to verify code and links are preserved.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("Code: `print()` and link [text](url)")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """_TEXT_ `_TEXT_` _TEXT_ [_TEXT_](url)"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


# ============================================================================
# TextProcessor Tests
# ============================================================================

def test_text_processor_replace_text_in_content_empty():
    """Test text replacement with empty string"""
    # Note: TextProcessor class has been removed. Text processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    # Whitespace-only lines are preserved as-is.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("   ")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = "   "
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_text_processor_preserve_markdown_formatting():
    """Test markdown formatting preservation (now integrated in _replace_text_with_placeholders)"""
    # Note: TextProcessor class has been removed. Text processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""**bold text**

This is *italic text* here

*italic text* at start

text *italic text*

text _italic text_

[link text](url)
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """**_TEXT_**

_TEXT_ *_TEXT_* _TEXT_

*_TEXT_* _TEXT_

_TEXT_ *_TEXT_*

_TEXT_

[_TEXT_](url)
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_text_processor_replace_remaining_text():
    """Test remaining text replacement (now integrated in _replace_text_with_placeholders)"""
    # Note: TextProcessor class has been removed. Text processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""Hello world

Hello, world!

**bold** and more text
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """_TEXT_

_TEXT_

**_TEXT_** _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_text_processor_cleanup_text():
    """Test cleanup of consecutive _TEXT_ placeholders"""
    # Note: TextProcessor class has been removed. Text processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("Multiple words here")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """_TEXT_"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_text_processor_replace_text_in_content_full():
    """Test full text replacement flow"""
    # Note: TextProcessor class has been removed. Text processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""Hello world

This is **bold** text

Hello, world! How are you?
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """_TEXT_

_TEXT_ **_TEXT_** _TEXT_

_TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


# ============================================================================
# YAML Processing Tests
# ============================================================================

def test_process_yaml_frontmatter():
    """Test YAML frontmatter processing"""
    # Single quoted value
    yaml = "title: 'Hello World'"
    result = process_yaml_frontmatter(yaml)
    assert result == ["title: '_TEXT_'"]
    
    # Double quoted value
    yaml = 'title: "Hello World"'
    result = process_yaml_frontmatter(yaml)
    assert result == ['title: "_TEXT_"']
    
    # Unquoted value
    yaml = "title: Hello World"
    result = process_yaml_frontmatter(yaml)
    assert result == ["title: _TEXT_"]
    
    # Multiple lines
    yaml = "title: 'Hello'\ndescription: 'World'"
    result = process_yaml_frontmatter(yaml)
    assert len(result) == 2
    assert result[0] == "title: '_TEXT_'"
    assert result[1] == "description: '_TEXT_'"
    
    # Line without colon
    yaml = "title: 'Hello'\n---\nseparator"
    result = process_yaml_frontmatter(yaml)
    assert len(result) == 3
    assert result[2] == "separator"


# ============================================================================
# Line Processing Tests
# ============================================================================

def test_process_text_line_empty():
    """Test processing empty line"""
    # Note: process_text_line function has been removed. Line processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    # Whitespace-only lines are preserved as-is.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("   ")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = "   "
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_process_text_line_import():
    """Test processing import statement"""
    # Note: process_text_line function has been removed. Line processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    # Import statements are preserved as-is according to the implementation.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("import { Component } from 'react'")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """import { Component } from 'react'"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_process_text_line_code_block():
    """Test processing code block markers"""
    # Note: process_text_line function has been removed. Line processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("```python\ncode here\n```")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """```python
code here
```"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_process_markdown_line_header():
    """Test processing markdown header"""
    # Note: process_markdown_line function has been removed. Line processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Header

## Subheader
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

## _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_process_markdown_line_list():
    """Test processing markdown list"""
    # Note: process_markdown_line function has been removed. Line processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
* Item one
1. Item one
    * Nested item
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """
* _TEXT_
1. _TEXT_
    * _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_process_html_line():
    """Test processing HTML line"""
    # Note: _process_html_line function has been removed. HTML processing is now handled
    # by MarkdownItProcessor using tokens. Test via convert_mdx_to_skeleton.
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
<p>Hello world</p>
<figure><img src='test.png' /></figure>
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """
<p>_TEXT_</p>
<figure><img src='test.png' /> </figure>
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


# ============================================================================
# Integration Tests
# ============================================================================

def test_convert_mdx_to_skeleton_simple():
    """Test converting a simple MDX file"""
    import tempfile
    import shutil
    
    # Create temporary directory
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""---
title: 'Test Title'
---

# Header

Some content here.
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        
        assert output_path.exists()
        assert output_path.name == "test.skel.mdx"
        
        content = output_path.read_text()
        expected = """---
title: '_TEXT_'
---

# _TEXT_

_TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_convert_mdx_to_skeleton_with_code():
    """Test converting MDX file with code blocks"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Code Example

```python
print('hello')
```

Some text.
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

```python
print('hello')
```

_TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_convert_mdx_to_skeleton_with_images():
    """Test converting MDX file with images"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Image Test

![Alt text](/path/to/image.png)

More text.
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

![_TEXT_](/path/to/image.png)

_TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_convert_mdx_to_skeleton_with_links():
    """Test converting MDX file with links"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Link Test

Visit [Google](https://google.com) for search.

More text.
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

_TEXT_ [_TEXT_](https://google.com) _TEXT_

_TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_convert_mdx_to_skeleton_with_formatting():
    """Test converting MDX file with markdown formatting"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Formatting Test

This is **bold** and *italic* text.

More content.
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

_TEXT_ **_TEXT_** _TEXT_ *_TEXT_* _TEXT_

_TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_convert_mdx_to_skeleton_with_lists():
    """Test converting MDX file with lists"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# List Test

* Item one
* Item two
    1. Nested one
    2. Nested two
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

* _TEXT_
* _TEXT_
    1. _TEXT_
    2. _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_convert_mdx_to_skeleton_error_cases():
    """Test error cases"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        # Non-existent file
        non_existent = tmp_dir / "nonexistent.mdx"
        try:
            convert_mdx_to_skeleton(non_existent)
            assert False, "Should raise FileNotFoundError"
        except FileNotFoundError:
            pass
        
        # Wrong extension
        wrong_ext = tmp_dir / "test.txt"
        wrong_ext.write_text("content")
        try:
            convert_mdx_to_skeleton(wrong_ext)
            assert False, "Should raise ValueError"
        except ValueError:
            pass
        
        # Already skeleton file
        skel_file = tmp_dir / "test.skel.mdx"
        skel_file.write_text("content")
        try:
            convert_mdx_to_skeleton(skel_file)
            assert False, "Should raise ValueError"
        except ValueError:
            pass
    finally:
        shutil.rmtree(tmp_dir)


# ============================================================================
# Bug Fix Tests - Tests for actual failures found in test-skeleton
# ============================================================================

def test_list_item_with_period_at_end():
    """Test that list items ending with period do NOT preserve the period"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Test

1. Item one.
2. Item two.
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

1. _TEXT_
2. _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_html_entities_in_text():
    """Test that HTML entities like &gt; are protected and preserved, while text is converted to _TEXT_"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Test

Administrator &gt; Kubernetes &gt; Connection Management
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

_TEXT_ &gt; _TEXT_ &gt; _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_inline_code_in_list_items():
    """Test that inline code in list items has text converted to _TEXT_"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Test

1. Use `get` command
2. Use `list` command
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

1. _TEXT_ `_TEXT_` _TEXT_
2. _TEXT_ `_TEXT_` _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_html_tags_with_text_content():
    """Test that text inside HTML tags like <figcaption> is converted"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Test

<figure>
<img src="test.png" />
<figcaption>
Administrator &gt; General &gt; Company Management
</figcaption>
</figure>
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

<figure>
<img src="test.png" />
<figcaption>
_TEXT_ &gt; _TEXT_ &gt; _TEXT_
</figcaption>
</figure>
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_complex_list_item_with_bold_and_inline_code():
    """Test list items with bold text and inline code"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Test

1. **Request Audit** : 해당 클러스터에 대한 Kubernetes API 호출 이력에 대한 로깅 활성화 옵션으로, Default는 `On`입니다.
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

1. **_TEXT_** _TEXT_ `_TEXT_` _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_separator_line_not_in_yaml():
    """Test that separator lines (---) not in YAML frontmatter are handled correctly"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""---
title: 'Test'
---

# Test

---

## Section

Content here.
---
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """---
title: '_TEXT_'
---

# _TEXT_

---

## _TEXT_

_TEXT_
---
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_callout_component_with_text():
    """Test that text inside Callout components is converted"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""---
title: 'Test'
---

import { Callout } from 'nextra/components'

<Callout type="info">
본 문서는 **10.2.6 또는 그 이상의 버전** 에 적용됩니다.
</Callout>
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """---
title: '_TEXT_'
---

import { Callout } from 'nextra/components'

<Callout type="info">
_TEXT_ **_TEXT_** _TEXT_
</Callout>
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_list_item_with_html_entities_and_text():
    """Test list items containing HTML entities and text that should be converted"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Test

1. Administrator &gt; Kubernetes &gt; Connection Management &gt; Clusters 메뉴로 이동합니다.
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

1. _TEXT_ &gt; _TEXT_ &gt; _TEXT_ &gt; _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_nested_list_items_with_periods():
    """Test nested list items with periods at the end"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Test

1. Item one.
    1. Nested item one.
    2. Nested item two.
2. Item two.
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

1. _TEXT_
    1. _TEXT_
    2. _TEXT_
2. _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_list_item_with_multiple_inline_codes():
    """Test list item with multiple inline code blocks"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""# Test

1. Verb 종류:
    1. `get`
    2. `list`
    3. `watch`
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """# _TEXT_

1. _TEXT_
    1. `_TEXT_`
    2. `_TEXT_`
    3. `_TEXT_`
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_complex_list_with_html_and_figure():
    """Test complex list items with HTML tags, bold text, and figure elements preserving indentation"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
1.  **웹 커넥션 목록 확인** 
    * 사용자 화면 상단 Databases를 클릭합니다. 
    * 좌측 커넥션 목록에서 QueryPie Connections를 클릭하면 접근 권한이 있는 Custom Data Source가 표시됩니다. <br/> 
      <figure data-layout="center" data-align="center">
      ![Screenshot-2025-03-06-at-2.22.22-PM.png](/880181257/output/Screenshot-2025-03-06-at-2.22.22-PM.png)
      </figure>
2.  **접속 불가 안내** 
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """
1. **_TEXT_**
    * _TEXT_
    * _TEXT_ <br/>
      <figure data-layout="center" data-align="center">
      ![_TEXT_](/880181257/output/Screenshot-2025-03-06-at-2.22.22-PM.png)
      </figure>
2. **_TEXT_**
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_callout_with_external_link():
    """Test Callout component with version information, bold text, and links"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""<Callout type="info">
본 문서는  **10.2.6 또는 그 이상의 버전** 에 적용됩니다.
10.2.5 또는 그 이하 버전의 Slack 연동 방법은 [10.1.0 버전 매뉴얼 문서](https://docs.querypie.com/ko/querypie-manual/10.1.0/workflow-configurations)를 참고해주세요.
</Callout>
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """<Callout type="info">
_TEXT_ **_TEXT_** _TEXT_
_TEXT_ [_TEXT_](https://docs.querypie.com/ko/querypie-manual/10.1.0/workflow-configurations) _TEXT_
</Callout>
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_list_items_with_reference_links():
    """Test list items with reference links to external documentation"""
    import tempfile
    import shutil
    
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
* 참고: [kubeconfig 파일 병합](https://kubernetes.io/ko/docs/concepts/configuration/organize-cluster-access-kubeconfig/#kubeconfig-%ED%8C%8C%EC%9D%BC-%EB%B3%91%ED%95%A9)
* 참고: [KUBECONFIG 환경 변수 설정](https://kubernetes.io/ko/docs/tasks/access-application-cluster/configure-access-multiple-clusters/#kubeconfig-%ED%99%98%EA%B2%BD-%EB%B3%80%EC%88%98-%EC%84%A4%EC%A0%95)
""")
        
        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()
        
        expected = """
* _TEXT_ [_TEXT_](https://kubernetes.io/ko/docs/concepts/configuration/organize-cluster-access-kubeconfig/#kubeconfig-%ED%8C%8C%EC%9D%BC-%EB%B3%91%ED%95%A9)
* _TEXT_ [_TEXT_](https://kubernetes.io/ko/docs/tasks/access-application-cluster/configure-access-multiple-clusters/#kubeconfig-%ED%99%98%EA%B2%BD-%EB%B3%80%EC%88%98-%EC%84%A4%EC%A0%95)
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_japanese_text_with_multiple_bold_sections():
    """Test Japanese text with multiple bold sections"""
    import tempfile
    import shutil

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
現在QueryPieは  **データベース、システム、Kubernetesアクセス制御と監査機能** を核心として提供しており、データベース資産を基盤として機密データを自動で識別し分類する**AIデータディスカバリ** 機能も一緒に提供します。
""")

        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()

        expected = """
_TEXT_ **_TEXT_** _TEXT_ **_TEXT_** _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_callout_with_bold_html_entities_and_inline_code():
    """Test Callout component with bold text, HTML entities, and inline code"""
    import tempfile
    import shutil

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
<Callout type="important">
**다운로드 파일에 암호 포함하기**

다운로드 대상 파일은 ‘*.csv 또는 *.json 파일을 압축한 *.zip 파일’입니다.

해당 압축 파일에 대한 암호를 지정하기 위해서는 ‘General Setting &gt; Security’ 메뉴에서 `Export a file with Encryption` 옵션을 ‘Required’로 지정해야 합니다.
</Callout>
""")

        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()

        expected = """
<Callout type="important">
**_TEXT_**

_TEXT_

_TEXT_ &gt; _TEXT_ `_TEXT_` _TEXT_
</Callout>
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_list_item_with_html_br_and_emoji():
    """Test list item with HTML br tag, emoji, and inline code"""
    import tempfile
    import shutil

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
4. Create app from manifest 모달에서 JSON 형식의 App Manifest를 입력합니다. <br/>미리 채워져 있는 내용들을 삭제하고 아래의 App Manifest를 붙여넣은 뒤 다음 단계로 진행합니다.<br/>:light_bulb_on: `{{..}}` 안의 값은 원하는 값으로 변경해 주세요. <br/> 
""")

        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()

        expected = """
4. _TEXT_ <br/> _TEXT_ <br/> _TEXT_ `_TEXT_` _TEXT_ <br/>
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_list_item_with_multiple_inline_codes_and_quotes():
    """Test list item with multiple inline codes and quotes"""
    import tempfile
    import shutil

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
1) KUBECONFIG 환경 변수를 최초 설정하는 경우, 명령 줄 내의 디폴트 "`${KUBECONFIG}`" 값을 사용 전에 "`${HOME}/.kube/config`"로 변경해야 합니다.
""")

        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()

        expected = """
_TEXT_ `_TEXT_` _TEXT_ `_TEXT_` _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_complex_workflow_approval_rules_with_figures():
    """Test complex workflow approval rules with nested lists, HTML entities, figures, and figcaptions"""
    import tempfile
    import shutil

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
사용자 프로필의 특정 Attribute(예: 팀 리더, 부서장)를 기준으로 승인자를 자동으로 지정할 수 있습니다.

* 중요: 
    * 선택된 Attribute의 값으로는 승인자의 QueryPie Login ID가 입력되어 있어야 합니다.
      <figure data-layout="center" data-align="center">
      ![Admin &gt; General &gt; Users &gt; Detail page &gt; Profile 탭<br/>](/544145591/output/Screenshot-2025-06-12-at-1.33.58-PM.png)
      <figcaption>
      Admin &gt; General &gt; Users &gt; Detail page &gt; Profile 탭<br/>
      </figcaption>
      </figure>
* Administrator &gt; General &gt; Workflow Management &gt; Approval Rules 페이지에서 새로운 승인 규칙을 추가하거나 기존 규칙을 수정할 때, 'Assignee for Approval' 항목에 'Allow Assignee selection (Attribute-Based)'를 선택한 뒤 승인자와 매핑하기 위한 Attribute (예: teamLeader)를 지정합니다.<br/>
  <figure data-layout="center" data-align="center">
  ![image-20251110-030113.png](/544145591/output/image-20251110-030113.png)
  </figure>
    * 자가 승인 비활성화 시 연동: 만약 Approval Rules 설정에서 'Self Approval (자가 승인)' 옵션이 비활성화된 경우, Attribute 기반으로 결정된 승인자가 요청자 자신일 경우에는 해당 요청자를 승인자로 자동 지정할 수 없습니다. 이 경우, 워크플로우 설정 또는 시스템 정책에 따라 승인자 지정이 실패하거나 다른 경로로 처리될 수 있으니 주의가 필요합니다.
* Attribute 값 부재 시 알림
    * 만약 상신자 User Profile에 해당 Attribute 값이 비어 있는 경우(즉, 승인자의 Login ID가 지정되지 않은 경우), 워크플로우 상신 시 다음과 같은 내용의 알림 모달이 표시되며 요청 제출이 중단됩니다. 상신자는 관리자에게 문의하여 프로필의 Attribute 값을 설정해야 합니다.
        * 에러 메시지 예시: 
          <figure data-layout="center" data-align="center">
          ![image-20250508-022114.png](/544145591/output/image-20250508-022114.png)
          </figure>
* Attribute 값은 있지만 해당 사용자가 비활성화된 경우
    * 만약 상신자 User Profile에 해당 Attribute 값으로 지정된 승인자가 비활성화된 경우, 워크플로우 상신 시 Approver란에 지정된 승인자가 표기되지 않으며 아래와 같은 내용의 알림 모달이 표시되며 요청 제출이 중단됩니다.
        * 에러 메세지 예시:
          <figure data-layout="center" data-align="center">
          ![Screenshot-2025-06-16-at-10.30.14-AM.png](/544145591/output/Screenshot-2025-06-16-at-10.30.14-AM.png)
          </figure>

""")

        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()

        expected = """
_TEXT_

* _TEXT_
    * _TEXT_
      <figure data-layout="center" data-align="center">
      ![_TEXT_](/544145591/output/Screenshot-2025-06-12-at-1.33.58-PM.png)
      <figcaption>
      _TEXT_ &gt; _TEXT_ &gt; _TEXT_ &gt; _TEXT_ &gt; _TEXT_ <br/>
      </figcaption>
      </figure>
* _TEXT_ &gt; _TEXT_ &gt; _TEXT_ &gt; _TEXT_ <br/>
  <figure data-layout="center" data-align="center">
  ![_TEXT_](/544145591/output/image-20251110-030113.png)
  </figure>
    * _TEXT_
* _TEXT_
    * _TEXT_
        * _TEXT_
          <figure data-layout="center" data-align="center">
          ![_TEXT_](/544145591/output/image-20250508-022114.png)
          </figure>
* _TEXT_
    * _TEXT_
        * _TEXT_
          <figure data-layout="center" data-align="center">
          ![_TEXT_](/544145591/output/Screenshot-2025-06-16-at-10.30.14-AM.png)
          </figure>

"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_japanese_list_item_with_link_and_bold():
    """Test Japanese list item with link and bold text"""
    import tempfile
    import shutil

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
    * 자세한 내용은 [DB Connections](connection-management/db-connections) 내 **Privilege Setting** 문서 참고
    * 詳細内容は[DB Connections](connection-management/db-connections)内 **Privilege Setting** 文書参考
""")

        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()

        expected = """
    * _TEXT_ [_TEXT_](connection-management/db-connections) _TEXT_ **_TEXT_** _TEXT_
    * _TEXT_ [_TEXT_](connection-management/db-connections) _TEXT_ **_TEXT_** _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


def test_list_item_with_dac_and_multiple_inline_codes():
    """Test list items with [DAC] label and multiple inline code blocks in Korean and Japanese"""
    import tempfile
    import shutil

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text("""
* [DAC] MongoDB Atlas Search 관련 `$search`, `$searchMeta` stage 지원
* [DAC] MongoDB Atlas Search関連`$search`、`$searchMeta`stageサポート
* [General] 임시 Login Token 을 통한 웹 &lt;-&gt; 에이전트 간 자동로그인 구현
* [General] 一時Login Tokenを通じたウェブ&lt;-&gt;エージェント間自動ログイン実装
""")

        output_path, _ = convert_mdx_to_skeleton(input_file)
        content = output_path.read_text()

        expected = """
* [_TEXT_] _TEXT_ `_TEXT_` `_TEXT_` _TEXT_
* [_TEXT_] _TEXT_ `_TEXT_` `_TEXT_` _TEXT_
* [_TEXT_] _TEXT_ &lt; _TEXT_ &gt; _TEXT_
* [_TEXT_] _TEXT_ &lt; _TEXT_ &gt; _TEXT_
"""
        assert content == expected, f"Expected:\n{expected!r}\nGot:\n{content!r}"
    finally:
        shutil.rmtree(tmp_dir)


# ============================================================================
# Test Runner
# ============================================================================

def run_all_tests():
    """Run all tests and report results"""
    import traceback
    
    test_functions = [
        # ContentProtector tests
        test_content_protector_extract_yaml_frontmatter,
        test_content_protector_extract_code_blocks,
        test_content_protector_extract_inline_code,
        test_content_protector_extract_urls,
        test_content_protector_extract_image_links,
        test_content_protector_extract_html_entities,
        test_content_protector_restore_all,
        
        # TextProcessor tests
        test_text_processor_replace_text_in_content_empty,
        test_text_processor_preserve_markdown_formatting,
        test_text_processor_replace_remaining_text,
        test_text_processor_cleanup_text,
        test_text_processor_replace_text_in_content_full,
        
        # YAML processing tests
        test_process_yaml_frontmatter,
        
        # Line processing tests
        test_process_text_line_empty,
        test_process_text_line_import,
        test_process_text_line_code_block,
        test_process_markdown_line_header,
        test_process_markdown_line_list,
        test_process_html_line,
        
        # Integration tests
        test_convert_mdx_to_skeleton_simple,
        test_convert_mdx_to_skeleton_with_code,
        test_convert_mdx_to_skeleton_with_images,
        test_convert_mdx_to_skeleton_with_links,
        test_convert_mdx_to_skeleton_with_formatting,
        test_convert_mdx_to_skeleton_with_lists,
        test_convert_mdx_to_skeleton_error_cases,
        
        # Bug fix tests
        test_list_item_with_period_at_end,
        test_html_entities_in_text,
        test_inline_code_in_list_items,
        test_html_tags_with_text_content,
        test_complex_list_item_with_bold_and_inline_code,
        test_separator_line_not_in_yaml,
        test_callout_component_with_text,
        test_list_item_with_html_entities_and_text,
        test_nested_list_items_with_periods,
        test_list_item_with_multiple_inline_codes,
        test_complex_list_with_html_and_figure,
        test_callout_with_external_link,
        test_list_items_with_reference_links,
        test_japanese_text_with_multiple_bold_sections,
        test_callout_with_bold_html_entities_and_inline_code,
        test_list_item_with_html_br_and_emoji,
        test_list_item_with_multiple_inline_codes_and_quotes,
        test_complex_workflow_approval_rules_with_figures,
        test_japanese_list_item_with_link_and_bold,
        test_list_item_with_dac_and_multiple_inline_codes,
    ]
    
    passed = 0
    failed = 0
    
    print("Running unit tests for mdx_to_skeleton.py")
    print("=" * 60)
    
    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__}")
            print(f"  {str(e)}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}")
            print(f"  Unexpected error: {str(e)}")
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"\nTotal: {passed + failed}, Passed: {passed}, Failed: {failed}")
    
    if failed == 0:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed!")
        return 1


if __name__ == "__main__":
    # Check if pytest is available
    try:
        import pytest
        # If pytest is available, use it
        pytest.main([__file__, "-v"])
    except ImportError:
        # Otherwise, run our simple test runner
        # Note: Integration tests require pytest for tmp_path fixture
        sys.exit(run_all_tests())

