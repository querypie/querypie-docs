"""Roundtrip Verifier — 패치된 XHTML의 forward 변환 결과와 개선 MDX의 완전 일치를 검증한다."""
from dataclasses import dataclass
import difflib
import html as html_module
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


def _strip_first_heading(text: str) -> str:
    """첫 번째 h1 heading을 제거한다.

    h1 heading은 Confluence page title에 대응하며,
    XHTML body 패치로는 변경할 수 없으므로 비교에서 제외한다.
    """
    return re.sub(r'^# .+$', '', text, count=1, flags=re.MULTILINE)


def _normalize_table_cell_lines(text: str) -> str:
    """HTML <td> 내의 연속 텍스트 행을 한 줄로 결합한다.

    Forward converter가 <p> 내의 문장을 줄바꿈으로 분리할 수 있으므로,
    <td>...</td> 블록 내 연속된 순수 텍스트 행을 공백으로 결합하여
    비교 시 동일하게 취급한다.
    """
    lines = text.split('\n')
    result: list = []
    in_td = False

    for line in lines:
        stripped = line.strip()

        if not in_td:
            if stripped.startswith('<td'):
                in_td = True
            result.append(line)
            continue

        # <td> 블록 내부
        if '</td>' in stripped:
            in_td = False
            # 닫는 태그 직전의 텍스트 행이면 이전 행과 결합
            before_close = stripped.split('</td>')[0].strip()
            if before_close and result:
                prev = result[-1].strip()
                if prev and not prev.startswith('<') and not prev.startswith('```'):
                    result[-1] = result[-1].rstrip() + ' ' + before_close
                    result.append(line[line.index('</td>'):])
                    continue
            result.append(line)
            continue

        # 태그·코드·리스트 행은 결합하지 않음
        if (not stripped
                or stripped.startswith('<') or stripped.startswith('```')
                or stripped.startswith('*') or stripped.startswith('-')
                or re.match(r'^\d+\.', stripped)):
            result.append(line)
            continue

        # 순수 텍스트 행: 직전 행이 텍스트이면 결합
        if result:
            prev = result[-1].strip()
            if (prev and not prev.startswith('<') and not prev.startswith('```')
                    and not prev.startswith('*') and not prev.startswith('-')
                    and not re.match(r'^\d+\.', prev)):
                result[-1] = result[-1].rstrip() + ' ' + stripped
                continue

        result.append(line)

    return '\n'.join(result)


def _normalize_html_entities_in_code(text: str) -> str:
    """코드 블록 내의 HTML 엔티티를 일반 문자로 변환한다.

    XHTML 패치 시 코드 본문의 <, >, & 등이 엔티티로 변환될 수 있으므로,
    코드 블록 내에서 이를 원래 문자로 복원하여 비교한다.
    """
    def _unescape_block(m):
        return '```' + m.group(1) + html_module.unescape(m.group(2)) + '```'
    return re.sub(r'```(\w*\n)(.*?)```', _unescape_block, text, flags=re.DOTALL)


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
    expected_mdx = _strip_first_heading(expected_mdx)
    actual_mdx = _strip_first_heading(actual_mdx)
    expected_mdx = _normalize_table_cell_lines(expected_mdx)
    actual_mdx = _normalize_table_cell_lines(actual_mdx)
    expected_mdx = _normalize_html_entities_in_code(expected_mdx)
    actual_mdx = _normalize_html_entities_in_code(actual_mdx)

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
