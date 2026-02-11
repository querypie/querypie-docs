"""Roundtrip Verifier — 패치된 XHTML의 forward 변환 결과와 개선 MDX의 완전 일치를 검증한다."""
from dataclasses import dataclass
import difflib
import re


@dataclass
class VerifyResult:
    passed: bool
    diff_report: str


def _normalize_trailing_ws(text: str) -> str:
    """각 줄 끝의 trailing whitespace를 제거한다."""
    return re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)


_MONTH_KO_TO_EN = {
    '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
    '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
    '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec',
}
_KO_DATE_RE = re.compile(
    r'^(\d{4})년\s*(\d{2})월\s*(\d{2})일[ \t]*$', re.MULTILINE)


def _normalize_dates(text: str) -> str:
    """독립 행의 한국어 날짜를 영문 형식으로 변환한다.

    Forward converter가 Confluence <time> 요소를 영문으로 포맷하므로,
    비교 시 동일한 형식으로 정규화한다.
    """
    def _replace(m):
        y, mo, d = m.group(1), m.group(2), m.group(3)
        return f'{_MONTH_KO_TO_EN.get(mo, mo)} {d}, {y}'
    return _KO_DATE_RE.sub(_replace, text)


def _normalize_table_cell_padding(text: str) -> str:
    """Markdown table 행의 셀 패딩 공백을 정규화한다.

    XHTML→MDX forward 변환 시 테이블 셀의 컬럼 폭 계산이 원본 MDX와
    1~2자 차이날 수 있으므로, 연속 공백을 단일 공백으로 축약한다.
    """
    lines = text.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            line = re.sub(r'  +', ' ', line)
        result.append(line)
    return '\n'.join(result)


def verify_roundtrip(expected_mdx: str, actual_mdx: str) -> VerifyResult:
    """두 MDX 문자열의 일치를 검증한다.

    trailing whitespace, 날짜 형식을 정규화. 그 외 공백, 줄바꿈, 모든 문자가
    동일해야 PASS.

    Args:
        expected_mdx: 개선 MDX (의도한 결과)
        actual_mdx: 패치된 XHTML을 forward 변환한 결과

    Returns:
        VerifyResult: passed=True면 통과, 아니면 diff_report 포함
    """
    expected_mdx = _normalize_trailing_ws(expected_mdx)
    actual_mdx = _normalize_trailing_ws(actual_mdx)
    expected_mdx = _normalize_dates(expected_mdx)
    actual_mdx = _normalize_dates(actual_mdx)
    expected_mdx = _normalize_table_cell_padding(expected_mdx)
    actual_mdx = _normalize_table_cell_padding(actual_mdx)

    if expected_mdx == actual_mdx:
        return VerifyResult(passed=True, diff_report="")

    expected_lines = expected_mdx.splitlines(keepends=True)
    actual_lines = actual_mdx.splitlines(keepends=True)

    diff = difflib.unified_diff(
        expected_lines,
        actual_lines,
        fromfile='expected (improved MDX)',
        tofile='actual (roundtrip MDX)',
        lineterm='',
    )
    report = ''.join(diff)

    return VerifyResult(passed=False, diff_report=report)
