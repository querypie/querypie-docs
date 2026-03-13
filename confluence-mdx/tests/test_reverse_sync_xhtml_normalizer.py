from reverse_sync.xhtml_normalizer import (
    extract_fragment_by_xpath,
    extract_plain_text,
    normalize_fragment,
)


def test_extract_plain_text_uses_emoticon_fallback_inside_layout():
    xhtml = (
        "<ac:layout>"
        "<ac:layout-section>"
        "<ac:layout-cell>"
        '<p>Hello <ac:emoticon ac:emoji-fallback="🔎"></ac:emoticon></p>'
        "</ac:layout-cell>"
        "</ac:layout-section>"
        "</ac:layout>"
    )

    assert extract_plain_text(xhtml) == "Hello 🔎"


def test_normalize_fragment_ignores_layout_and_ignored_attributes():
    left = (
        "<ac:layout><ac:layout-section><ac:layout-cell>"
        '<p ac:local-id="1" class="ak-renderer-document">Body</p>'
        "</ac:layout-cell></ac:layout-section></ac:layout>"
    )
    right = "<p>Body</p>"

    assert normalize_fragment(left) == normalize_fragment(right)


def test_extract_fragment_by_xpath_returns_top_level_fragment():
    xhtml = "<h2>Title</h2><p><strong>Body</strong></p>"

    assert extract_fragment_by_xpath(xhtml, "p[1]") == "<p><strong>Body</strong></p>"


def test_extract_fragment_by_xpath_returns_nested_callout_child():
    xhtml = (
        '<ac:structured-macro ac:name="info">'
        "<ac:rich-text-body>"
        "<p>First</p>"
        "<p><strong>Second</strong></p>"
        "</ac:rich-text-body>"
        "</ac:structured-macro>"
    )

    assert (
        extract_fragment_by_xpath(xhtml, "macro-info[1]/p[2]")
        == "<p><strong>Second</strong></p>"
    )
