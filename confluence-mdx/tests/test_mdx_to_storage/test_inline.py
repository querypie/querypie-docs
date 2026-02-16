from mdx_to_storage.inline import convert_heading_inline, convert_inline
from mdx_to_storage.link_resolver import LinkResolver


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
    assert got == "a &gt; b and c &lt; d<br />next"


def test_convert_inline_normalizes_br_variants():
    src = "a<br>b<br/>c<BR />d"
    got = convert_inline(src)
    assert got == "a<br />b<br />c<br />d"


def test_convert_inline_bold_italic_combo():
    src = "***bold-italic***"
    got = convert_inline(src)
    assert got == "<strong><em>bold-italic</em></strong>"


def test_convert_heading_inline_strips_bold_marker_and_converts_code_link():
    src = "Heading **Bold** `code` [jump](/path)"
    got = convert_heading_inline(src)
    assert got == 'Heading Bold <code>code</code> <a href="/path">jump</a>'


def test_convert_inline_multiple_code_spans_and_link():
    src = "Use `a` then [go](/docs) and `b`"
    got = convert_inline(src)
    assert got == 'Use <code>a</code> then <a href="/docs">go</a> and <code>b</code>'


def test_convert_heading_inline_keeps_non_bold_markdown_text():
    src = "Heading *italic* **Bold** [jump](/path) `x`"
    got = convert_heading_inline(src)
    assert got == 'Heading *italic* Bold <a href="/path">jump</a> <code>x</code>'


def test_convert_inline_plain_text_passthrough():
    src = "Just plain text without any markdown"
    got = convert_inline(src)
    assert got == src


def test_convert_inline_bold_inside_link():
    src = "[**bold link**](https://example.com)"
    got = convert_inline(src)
    assert got == '<a href="https://example.com"><strong>bold link</strong></a>'


def test_convert_inline_internal_link_to_ac_link(tmp_path):
    pages_yaml = tmp_path / "pages.yaml"
    pages_yaml.write_text(
        """
- page_id: "1"
  title_orig: "My Dashboard"
  path: ["user-manual", "my-dashboard"]
""".strip(),
        encoding="utf-8",
    )
    resolver = LinkResolver(pages_yaml)
    src = "[My Dashboard](user-manual/my-dashboard#overview)"
    got = convert_inline(src, link_resolver=resolver)
    assert (
        got
        == '<ac:link ac:anchor="overview"><ri:page ri:content-title="My Dashboard"></ri:page><ac:link-body>My Dashboard</ac:link-body></ac:link>'
    )


def test_convert_inline_unresolved_link_keeps_anchor(tmp_path):
    pages_yaml = tmp_path / "pages.yaml"
    pages_yaml.write_text("[]", encoding="utf-8")
    resolver = LinkResolver(pages_yaml)
    src = "[Unknown](not/found)"
    got = convert_inline(src, link_resolver=resolver)
    assert got == '<a href="not/found">Unknown</a>'
