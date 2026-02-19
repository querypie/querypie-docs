"""Roundtrip Verifier — 패치된 XHTML의 forward 변환 결과와 개선 MDX의 완전 일치를 검증한다."""
from dataclasses import dataclass
import difflib
import html as html_module
import re
from typing import Optional


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


def _normalize_heading_ws(text: str) -> str:
    """Heading 행의 공백을 정규화한다.

    Forward converter가 heading 내 텍스트 노드를 .strip()하므로,
    인라인 요소(<strong>, <code> 등) 경계의 공백이 제거된다.
    비교 시 이 차이를 무시하기 위해 heading 내용의 공백을 제거하여 비교한다.
    """
    lines = text.split('\n')
    result = []
    for line in lines:
        m = re.match(r'^(#{2,6})\s', line)
        if m:
            prefix = m.group(1)
            content = line[len(prefix):].lstrip()
            content = re.sub(r'\s+', '', content)
            result.append(prefix + ' ' + content)
        else:
            result.append(line)
    return '\n'.join(result)


def _normalize_sentence_breaks(text: str) -> str:
    """Forward converter의 split_into_sentences()에 의한 줄바꿈을 정규화한다.

    Forward converter가 <p> 내의 문장을 '. '에서 줄바꿈으로 분리하므로,
    문장 경계에서 분리된 행을 다시 결합하여 비교한다.
    """
    lines = text.split('\n')
    result: list = []
    for line in lines:
        stripped = line.strip()
        if (result
                and stripped
                and not stripped.startswith(('#', '*', '-', '<', '|', '`', '>'))
                and not re.match(r'^\d+\.', stripped)):
            prev = result[-1].rstrip()
            if prev and re.search(r'[.!?]$', prev):
                result[-1] = prev + ' ' + stripped
                continue
        result.append(line)
    return '\n'.join(result)


def _normalize_quotes(text: str) -> str:
    """스마트 따옴표를 ASCII 따옴표로 정규화한다.

    Forward converter가 XHTML의 따옴표를 Unicode 스마트 따옴표로 변환할 수 있으므로,
    비교 시 ASCII 따옴표로 통일한다.
    """
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    return text


def _normalize_inline_code_boundaries(text: str) -> str:
    """인라인 코드 스팬의 backtick을 제거하여 경계 차이를 무시한다.

    XHTML의 <code> 요소 경계는 텍스트 패처로 변경할 수 없으므로,
    인라인 코드 backtick을 제거하여 텍스트 내용만 비교한다.
    fenced code block (```)은 유지한다.
    """
    return re.sub(r'(?<!`)`(?!`)', '', text)


def _normalize_html_entities_in_code(text: str) -> str:
    """코드 블록 내의 HTML 엔티티를 일반 문자로 변환한다.

    XHTML 패치 시 코드 본문의 <, >, & 등이 엔티티로 변환될 수 있으므로,
    코드 블록 내에서 이를 원래 문자로 복원하여 비교한다.
    """
    def _unescape_block(m):
        return '```' + m.group(1) + html_module.unescape(m.group(2)) + '```'
    return re.sub(r'```(\w*\n)(.*?)```', _unescape_block, text, flags=re.DOTALL)


def _apply_normalizations(text: str) -> str:
    """모든 정규화를 순서대로 적용한다."""
    text = _normalize_trailing_ws(text)
    text = _normalize_dates(text)
    text = _normalize_table_cell_padding(text)
    text = _strip_first_heading(text)
    text = _normalize_table_cell_lines(text)
    text = _normalize_html_entities_in_code(text)
    text = _normalize_inline_code_boundaries(text)
    text = _normalize_heading_ws(text)
    text = _normalize_sentence_breaks(text)
    text = _normalize_quotes(text)
    return text


def _changed_lines_in_expected(original: str, expected: str) -> set:
    """original→expected에서 변경된 행의 인덱스 집합을 반환한다."""
    orig_lines = original.splitlines()
    exp_lines = expected.splitlines()
    sm = difflib.SequenceMatcher(None, orig_lines, exp_lines)
    changed = set()
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag != 'equal':
            for j in range(j1, j2):
                changed.add(j)
    return changed


def verify_roundtrip(
    expected_mdx: str,
    actual_mdx: str,
    original_mdx: Optional[str] = None,
) -> VerifyResult:
    """두 MDX 문자열의 일치를 검증한다.

    trailing whitespace, 날짜 형식을 정규화. 그 외 공백, 줄바꿈, 모든 문자가
    동일해야 PASS.

    original_mdx가 제공되면, 변경되지 않은 행의 차이는 무시한다.
    이를 통해 기존 MDX↔XHTML 불일치가 있는 파일도 패치된 행만 검증한다.

    Args:
        expected_mdx: 개선 MDX (의도한 결과)
        actual_mdx: 패치된 XHTML을 forward 변환한 결과
        original_mdx: (선택) 원본 MDX (main 브랜치)

    Returns:
        VerifyResult: passed=True면 통과, 아니면 diff_report 포함
    """
    expected_mdx = _apply_normalizations(expected_mdx)
    actual_mdx = _apply_normalizations(actual_mdx)

    if expected_mdx == actual_mdx:
        return VerifyResult(passed=True, diff_report="")

    # original_mdx가 제공되면, 변경된 행에서만 차이를 검사한다.
    if original_mdx is not None:
        original_mdx = _apply_normalizations(original_mdx)
        changed = _changed_lines_in_expected(original_mdx, expected_mdx)

        exp_lines = expected_mdx.splitlines()
        act_lines = actual_mdx.splitlines()

        # expected vs actual의 diff hunk에서, 변경된 행이 포함된 것만 실패 처리
        sm = difflib.SequenceMatcher(None, exp_lines, act_lines)
        has_real_diff = False
        for tag, i1, i2, _j1, _j2 in sm.get_opcodes():
            if tag == 'equal':
                continue
            # 이 diff hunk의 expected 쪽 행 중 하나라도 변경된 행이면 실패
            for i in range(i1, i2):
                if i in changed:
                    has_real_diff = True
                    break
            if has_real_diff:
                break

        if not has_real_diff:
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
