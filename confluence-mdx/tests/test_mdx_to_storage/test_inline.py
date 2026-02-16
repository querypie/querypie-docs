from mdx_to_storage.inline import convert_heading_inline, convert_inline


def test_convert_inline_bold_italic_code_link():
    src = "**bold** *italic* `code` [docs](https://example.com)"
    got = convert_inline(src)
    assert got == (
        '<strong>bold</strong> <em>italic</em> '
        '<code>code</code> <a href="https://example.com">docs</a>'
    )


def test_convert_inline_code_span_protects_markdown_tokens():
    src = "`**not-bold** and [not-link](x)` and **bold**"
    got = convert_inline(src)
    assert got == "<code>**not-bold** and [not-link](x)</code> and <strong>bold</strong>"


def test_convert_inline_preserves_html_entities_and_br():
    src = "a &gt; b and c &lt; d<br/>next"
    got = convert_inline(src)
    assert got == "a &gt; b and c &lt; d<br/>next"


def test_convert_inline_bold_italic_combo():
    src = "***bold-italic***"
    got = convert_inline(src)
    assert got == "<strong><em>bold-italic</em></strong>"


def test_convert_heading_inline_strips_bold_marker_and_converts_code_link():
    src = "Heading **Bold** `code` [jump](/path)"
    got = convert_heading_inline(src)
    assert got == 'Heading Bold <code>code</code> <a href="/path">jump</a>'
