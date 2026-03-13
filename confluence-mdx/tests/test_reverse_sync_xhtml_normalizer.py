"""Level 0 helper tests — xhtml_normalizer 모듈 검증.

Phase 0 게이트:
- extract_plain_text: 다양한 XHTML fragment에서 plain text 추출
- normalize_fragment: fragment 비교 정규화
- extract_fragment_by_xpath: 간이 XPath 기반 fragment 추출
"""

import json
from pathlib import Path

import pytest

from reverse_sync.xhtml_normalizer import (
    extract_fragment_by_xpath,
    extract_plain_text,
    normalize_fragment,
)

TESTCASES_DIR = Path(__file__).parent / "testcases"


# ---------------------------------------------------------------------------
# extract_plain_text
# ---------------------------------------------------------------------------

class TestExtractPlainText:
    """extract_plain_text() 기본 동작 검증."""

    def test_simple_paragraph(self):
        fragment = "<p>Hello world</p>"
        assert extract_plain_text(fragment) == "Hello world"

    def test_paragraph_with_bold(self):
        fragment = "<p>A <strong>bold</strong> text</p>"
        assert extract_plain_text(fragment) == "A bold text"

    def test_paragraph_with_link(self):
        fragment = '<p>See <a href="http://example.com">example</a> here</p>'
        assert extract_plain_text(fragment) == "See example here"

    def test_paragraph_with_inline_image_excluded(self):
        """ac:image는 preservation unit이므로 plain text에서 제외된다."""
        fragment = (
            '<p>A '
            '<ac:image ac:align="center"><ri:attachment ri:filename="test.png" /></ac:image>'
            ' B</p>'
        )
        assert extract_plain_text(fragment) == "A  B"

    def test_paragraph_with_inline_link_no_body(self):
        """ac:link에 link-body가 없으면 텍스트가 비어있다."""
        fragment = (
            '<p>Before '
            '<ac:link><ri:page ri:content-title="Page" /></ac:link>'
            ' After</p>'
        )
        assert extract_plain_text(fragment) == "Before  After"

    def test_paragraph_with_inline_link_with_body(self):
        """ac:link에 link-body가 있으면 visible label이 plain text에 포함된다."""
        fragment = (
            '<p>참조: '
            '<ac:link><ri:page ri:content-title="Page" />'
            '<ac:link-body>Click here</ac:link-body></ac:link></p>'
        )
        assert extract_plain_text(fragment) == "참조: Click here"

    def test_paragraph_with_emoticon(self):
        """ac:emoticon의 fallback 텍스트가 포함된다."""
        fragment = (
            '<p>'
            '<ac:emoticon ac:name="tick" ac:emoji-fallback=":check_mark:" />'
            ' Success</p>'
        )
        assert extract_plain_text(fragment) == ":check_mark: Success"

    def test_code_macro_body_included(self):
        """코드 블록 본문(ac:plain-text-body)이 plain text에 포함된다."""
        fragment = (
            '<ac:structured-macro ac:name="code">'
            '<ac:parameter ac:name="language">python</ac:parameter>'
            '<ac:plain-text-body><![CDATA[print("hello")]]></ac:plain-text-body>'
            '</ac:structured-macro>'
        )
        text = extract_plain_text(fragment)
        assert 'print("hello")' in text

    def test_list_plain_text(self):
        fragment = "<ul><li><p>Item 1</p></li><li><p>Item 2</p></li></ul>"
        text = extract_plain_text(fragment)
        assert "Item 1" in text
        assert "Item 2" in text

    def test_heading(self):
        fragment = "<h2>Section Title</h2>"
        assert extract_plain_text(fragment) == "Section Title"

    def test_nested_formatting(self):
        fragment = "<p>A <strong><em>bold italic</em></strong> text</p>"
        assert extract_plain_text(fragment) == "A bold italic text"

    def test_empty_fragment(self):
        assert extract_plain_text("") == ""
        assert extract_plain_text("<p />") == ""

    def test_callout_with_rich_body(self):
        """callout macro 내부의 rich-text-body에서 텍스트를 추출한다."""
        fragment = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body><p>Info text</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        text = extract_plain_text(fragment)
        assert "Info text" in text


# ---------------------------------------------------------------------------
# extract_plain_text — real testcase fixtures
# ---------------------------------------------------------------------------

class TestExtractPlainTextFromFixtures:
    """실제 testcase fixture에서 extract_plain_text 동작 검증."""

    @pytest.fixture
    def sidecar_blocks(self):
        """544113141 testcase의 sidecar blocks를 로드한다."""
        path = TESTCASES_DIR / "544113141" / "expected.roundtrip.json"
        if not path.exists():
            pytest.skip("testcase fixture not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["blocks"]

    def test_heading_fragment(self, sidecar_blocks):
        """heading fragment의 plain text가 정확히 추출된다."""
        block = sidecar_blocks[0]  # h2[1] "Overview"
        assert block["xhtml_xpath"] == "h2[1]"
        text = extract_plain_text(block["xhtml_fragment"])
        assert text == "Overview"

    def test_paragraph_fragment(self, sidecar_blocks):
        """paragraph fragment의 plain text가 정확히 추출된다."""
        block = sidecar_blocks[1]  # p[1]
        assert block["xhtml_xpath"] == "p[1]"
        text = extract_plain_text(block["xhtml_fragment"])
        assert "조직에서 관리하는 DB 커넥션" in text

    def test_list_with_image_fragment(self, sidecar_blocks):
        """list + inline image fragment에서 image가 제외된다."""
        block = sidecar_blocks[4]  # ol[1]
        assert block["xhtml_xpath"] == "ol[1]"
        text = extract_plain_text(block["xhtml_fragment"])
        # ac:image는 제외되므로 파일명이 없어야 함
        assert "image-20240730" not in text
        # 텍스트 내용은 포함
        assert "DB Access History" in text


# ---------------------------------------------------------------------------
# normalize_fragment
# ---------------------------------------------------------------------------

class TestNormalizeFragment:
    """normalize_fragment() 정규화 검증."""

    def test_attribute_order_irrelevant(self):
        """속성 순서가 달라도 정규화 결과가 같다."""
        a = '<p id="x" class="y">text</p>'
        b = '<p class="y" id="x">text</p>'
        # class는 ignored attribute이므로 제거됨
        norm_a = normalize_fragment(a)
        norm_b = normalize_fragment(b)
        assert norm_a == norm_b

    def test_ignored_attributes_stripped(self):
        """IGNORED_ATTRIBUTES에 해당하는 속성이 제거된다."""
        fragment = '<ac:image ac:macro-id="123" ac:align="center"><ri:attachment ri:filename="test.png" /></ac:image>'
        result = normalize_fragment(fragment)
        assert "ac:macro-id" not in result
        assert 'ac:align="center"' in result

    def test_layout_sections_unwrapped(self):
        fragment = '<ac:layout><ac:layout-section><ac:layout-cell><p>content</p></ac:layout-cell></ac:layout-section></ac:layout>'
        result = normalize_fragment(fragment)
        assert "ac:layout" not in result
        assert "content" in result

    def test_nonreversible_macros_removed(self):
        fragment = '<ac:structured-macro ac:name="toc"></ac:structured-macro><p>keep</p>'
        result = normalize_fragment(fragment)
        assert "toc" not in result
        assert "keep" in result

    def test_decorations_unwrapped(self):
        fragment = '<p><ac:inline-comment-marker ac:ref="x">text</ac:inline-comment-marker></p>'
        result = normalize_fragment(fragment)
        assert "ac:inline-comment-marker" not in result
        assert "text" in result

    def test_same_content_normalizes_equal(self):
        """내용이 동일한 두 fragment는 정규화 후 동일하다."""
        a = "<p>Hello   <strong>world</strong></p>"
        b = "<p>Hello   <strong>world</strong></p>"
        assert normalize_fragment(a) == normalize_fragment(b)

    def test_strip_ignored_attrs_option(self):
        """strip_ignored_attrs=False면 속성을 유지한다."""
        fragment = '<ac:image ac:macro-id="123" ac:align="center" />'
        with_strip = normalize_fragment(fragment, strip_ignored_attrs=True)
        without_strip = normalize_fragment(fragment, strip_ignored_attrs=False)
        assert "ac:macro-id" not in with_strip
        assert "ac:macro-id" in without_strip

    def test_ignore_ri_filename_option(self):
        """ignore_ri_filename=True면 ri:filename 속성도 제거된다."""
        fragment = '<ri:attachment ri:filename="test.png" />'
        normal = normalize_fragment(fragment)
        ignored = normalize_fragment(fragment, ignore_ri_filename=True)
        assert 'ri:filename' in normal
        assert 'ri:filename' not in ignored

    def test_empty_paragraph_removed(self):
        """빈 <p> 요소가 decoration unwrap 후 제거된다."""
        fragment = '<p><ac:inline-comment-marker ac:ref="x"></ac:inline-comment-marker></p><p>keep</p>'
        result = normalize_fragment(fragment)
        # 빈 <p>는 제거되고 keep만 남음
        assert "keep" in result


# ---------------------------------------------------------------------------
# normalize_fragment — real testcase round-trip
# ---------------------------------------------------------------------------

class TestNormalizeFragmentRoundtrip:
    """실제 testcase의 fragment를 정규화해서 자기 자신과 비교."""

    @pytest.mark.parametrize("case_id", [
        "544113141", "544381877", "544112828",
    ])
    def test_fragment_self_normalize_equal(self, case_id):
        """같은 fragment를 두 번 정규화하면 결과가 동일하다 (idempotent)."""
        path = TESTCASES_DIR / case_id / "expected.roundtrip.json"
        if not path.exists():
            pytest.skip(f"testcase {case_id} not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        for block in data["blocks"]:
            frag = block["xhtml_fragment"]
            first = normalize_fragment(frag)
            second = normalize_fragment(first)
            assert first == second, (
                f"normalize_fragment is not idempotent for "
                f"{case_id} block {block['block_index']} ({block['xhtml_xpath']})"
            )


# ---------------------------------------------------------------------------
# extract_fragment_by_xpath
# ---------------------------------------------------------------------------

class TestExtractFragmentByXpath:
    """extract_fragment_by_xpath() 검증."""

    def test_simple_xpath(self):
        xhtml = "<h2>Title</h2><p>Para 1</p><p>Para 2</p>"
        result = extract_fragment_by_xpath(xhtml, "p[2]")
        assert result is not None
        assert "Para 2" in result

    def test_heading_xpath(self):
        xhtml = "<h2>First</h2><h2>Second</h2>"
        result = extract_fragment_by_xpath(xhtml, "h2[2]")
        assert result is not None
        assert "Second" in result

    def test_list_xpath(self):
        xhtml = "<p>text</p><ul><li><p>item</p></li></ul>"
        result = extract_fragment_by_xpath(xhtml, "ul[1]")
        assert result is not None
        assert "item" in result

    def test_macro_xpath(self):
        xhtml = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body><p>info body</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        result = extract_fragment_by_xpath(xhtml, "macro-info[1]")
        assert result is not None
        assert "info body" in result

    def test_compound_xpath(self):
        xhtml = (
            '<ac:structured-macro ac:name="note">'
            '<ac:rich-text-body><p>P1</p><p>P2</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        result = extract_fragment_by_xpath(xhtml, "macro-note[1]/p[2]")
        assert result is not None
        assert "P2" in result

    def test_nonexistent_xpath_returns_none(self):
        xhtml = "<p>only one</p>"
        assert extract_fragment_by_xpath(xhtml, "p[2]") is None
        assert extract_fragment_by_xpath(xhtml, "h2[1]") is None

    def test_multi_level_xpath(self):
        """ul[1]/li[2] 같은 다단계 xpath."""
        xhtml = "<ul><li><p>A</p></li><li><p>B</p></li></ul>"
        result = extract_fragment_by_xpath(xhtml, "ul[1]/li[2]")
        assert result is not None
        assert "B" in result


# ---------------------------------------------------------------------------
# extract_fragment_by_xpath — real testcase fixtures
# ---------------------------------------------------------------------------

class TestExtractFragmentByXpathFromFixtures:
    """실제 testcase page.xhtml에서 xpath 추출 검증."""

    @pytest.mark.parametrize("case_id", [
        "544113141", "544381877",
    ])
    def test_sidecar_xpath_matches_page(self, case_id):
        """sidecar의 xhtml_xpath로 page.xhtml에서 fragment를 추출할 수 있다."""
        sidecar_path = TESTCASES_DIR / case_id / "expected.roundtrip.json"
        page_path = TESTCASES_DIR / case_id / "page.xhtml"
        if not sidecar_path.exists() or not page_path.exists():
            pytest.skip(f"testcase {case_id} not found")

        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        page_xhtml = page_path.read_text(encoding="utf-8")

        for block in data["blocks"]:
            xpath = block["xhtml_xpath"]
            # compound xpath(child xpath)는 top-level만 테스트
            if "/" in xpath:
                continue
            extracted = extract_fragment_by_xpath(page_xhtml, xpath)
            assert extracted is not None, (
                f"Failed to extract {xpath} from {case_id}"
            )
            # 추출된 fragment의 plain text가 sidecar fragment와 일치
            expected_text = extract_plain_text(block["xhtml_fragment"])
            actual_text = extract_plain_text(extracted)
            assert expected_text.strip() == actual_text.strip(), (
                f"Plain text mismatch for {case_id} {xpath}"
            )
