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
