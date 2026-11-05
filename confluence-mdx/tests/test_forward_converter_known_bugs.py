"""forward converter 동작 검증 테스트."""
from bs4 import BeautifulSoup
from converter.core import MultiLineParser, _display_width
from converter.lost_info import LostInfoCollector


def _convert_xhtml(xhtml: str) -> str:
    """XHTML fragment를 MultiLineParser로 변환한다."""
    soup = BeautifulSoup(xhtml, "html.parser")
    return "".join(MultiLineParser(soup, collector=LostInfoCollector()).as_markdown)


class TestTableCjkWidth:
    """테이블 컬럼 폭이 CJK display width 기준으로 계산되어야 한다."""

    def test_display_width_helper(self):
        assert _display_width("abc") == 3
        assert _display_width("모드") == 4
        assert _display_width("Read Only") == 9
        assert _display_width("조회만 가능") == 11  # 5 CJK(x2) + 1 space

    def test_cjk_column_separator_uses_display_width(self):
        xhtml = (
            "<table><tbody>"
            "<tr><th><p><strong>모드</strong></p></th><th><p><strong>설명</strong></p></th></tr>"
            "<tr><td><p>Read Only</p></td><td><p>조회만 가능</p></td></tr>"
            "</tbody></table>"
        )
        result = _convert_xhtml(xhtml)
        lines = result.strip().split("\n")
        assert len(lines) >= 3

        separator = lines[1]
        sep_parts = [p.strip() for p in separator.split("|") if p.strip()]
        # '설명'(display=4) vs '조회만 가능'(display=11) → col_width=11 → 구분선 11자
        col2_sep_len = len(sep_parts[1])
        assert col2_sep_len == 11, f"expected 11 dashes, got {col2_sep_len}"


class TestCalloutMacroParameters:
    """Callout 매크로의 <ac:parameter>는 본문으로 변환되지 않아야 한다."""

    def test_info_macro_parameters_are_not_emitted_as_body(self):
        xhtml = (
            '<ac:structured-macro ac:name="info" ac:schema-version="1">'
            '<ac:parameter ac:name="containerLevel">panel_c1</ac:parameter>'
            '<ac:rich-text-body><p>본문 내용입니다.</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        result = _convert_xhtml(xhtml)
        assert 'containerLevel' not in result
        assert 'panel_c1' not in result
        assert 'Unexpected NavigableString' not in result
        assert '본문 내용입니다.' in result

    def test_info_macro_breakout_parameters_are_not_emitted_as_body(self):
        xhtml = (
            '<ac:structured-macro ac:name="info" ac:schema-version="1">'
            '<ac:parameter ac:name="breakoutMode">wide</ac:parameter>'
            '<ac:parameter ac:name="breakoutWidth">760</ac:parameter>'
            '<ac:rich-text-body><p>본문 내용입니다.</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        result = _convert_xhtml(xhtml)
        assert 'breakoutMode' not in result
        assert 'breakoutWidth' not in result
        assert 'Unexpected NavigableString' not in result
        assert '본문 내용입니다.' in result
