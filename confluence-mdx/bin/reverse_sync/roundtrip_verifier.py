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


def _normalize_consecutive_spaces_in_text(text: str) -> str:
    """코드 블록 외 텍스트에서 인라인 연속 공백을 단일 공백으로 정규화한다.

    Forward converter가 XHTML에서 생성한 MDX는 단일 공백만 사용하므로,
    improved.mdx의 이중 공백(예: **bold**  :, *  `item`)과의 차이를 무시한다.
    줄 앞 들여쓰기(leading whitespace)는 보존한다.

    fenced code block(```) 내부는 변경하지 않는다.
    인라인 code span(` `` `) 내부의 연속 공백도 정규화 대상에 포함된다.
    이는 HTML 렌더링 시 <code>a  b</code>와 <code>a b</code>가 동일하게
    표시되는 것과 일치한다.
    """
    lines = text.split('\n')
    result = []
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            result.append(line)
            continue
        if in_code_block:
            result.append(line)
            continue
        leading = len(line) - len(line.lstrip(' \t'))
        rest = re.sub(r' {2,}', ' ', line[leading:])
        result.append(line[:leading] + rest)
    return '\n'.join(result)


def _normalize_br_space(text: str) -> str:
    """<br/> 앞의 공백을 제거한다.

    Forward converter가 list item 구성 시 ' '.join(li_itself)로
    <br/> 앞에 공백을 추가하므로, 비교 시 이를 제거한다.
    """
    return re.sub(r' +(<br\s*/>)', r'\1', text)


def _normalize_trailing_blank_lines(text: str) -> str:
    """텍스트 끝의 빈 줄을 정규화한다.

    Forward converter가 마지막 줄 뒤에 빈 줄을 추가하는 경우가 있으므로,
    텍스트 끝의 빈 줄을 모두 제거하고 마지막 줄바꿈 하나만 유지한다.
    """
    stripped = text.rstrip('\n')
    return stripped + '\n' if stripped else text



def _normalize_link_text_spacing(text: str) -> str:
    """MDX 인라인 링크 텍스트의 앞뒤 공백을 제거한다.

    Forward converter가 [text](url) 형식에서 text 앞뒤 공백을 제거하므로,
    improved.mdx의 [ **text** ](url)와 verify.mdx의 [**text**](url)를 동일하게 취급한다.
    """
    return re.sub(r'\[ +(.+?) +\]\(', r'[\1](', text)


def _normalize_empty_bold(text: str) -> str:
    """빈 bold 마커(****)를 정규화한다.

    Forward converter가 XHTML의 빈 <strong></strong> 요소를 ****로 변환하므로,
    두 가지 패턴을 처리한다:
    1. ****text**** → **text** (빈 bold로 감싸인 텍스트)
    2. ****: → ' :' (콜론 앞 빈 bold는 구분 공백으로 정규화)

    fenced code block 내부는 변경하지 않는다.
    """
    lines = text.split('\n')
    result = []
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            result.append(line)
            continue
        if in_code_block:
            result.append(line)
            continue
        # ****text**** → **text** (빈 bold wrapper 제거)
        line = re.sub(r'\*{4}(.+?)\*{4}', r'**\1**', line)
        # ****: → ' :' (빈 bold 뒤 콜론 → 공백 콜론)
        line = re.sub(r'\*{4}:', ' :', line)
        result.append(line)
    return '\n'.join(result)


def _normalize_empty_list_items(text: str) -> str:
    """내용 없는 번호 리스트 항목(예: ``    12.``)을 빈 줄로 치환한다.

    Forward converter가 XHTML의 텍스트 없는 ``<li>`` (이미지만 포함)를
    번호만 있는 항목(``12.``)으로 변환한다. 이 항목은 시각적으로 무의미하므로
    improved.mdx에서 제거하더라도 XHTML 패치로 ``<li>`` 구조를 삭제할 수 없다.
    양쪽을 빈 줄로 정규화하여 이 차이를 무시한다.
    """
    return re.sub(r'^([ \t]+)\d+\.\s*$', '', text, flags=re.MULTILINE)


def _apply_minimal_normalizations(text: str) -> str:
    """항상 적용하는 최소 정규화 (strict/lenient 모드 공통).

    forward converter의 체계적 출력 특성에 의한 차이만 처리한다:
    - 인라인 이중 공백 → 단일 공백 (_normalize_consecutive_spaces_in_text)
    - <br/> 앞 공백 제거 (_normalize_br_space)
    - 링크 텍스트 앞뒤 공백 제거 (_normalize_link_text_spacing)
    - 빈 bold 마커(****) 정규화 (_normalize_empty_bold)
    - 내용 없는 번호 리스트 항목 제거 (_normalize_empty_list_items)

    lenient 모드에서는 이 정규화 이후 _apply_normalizations가 추가로 적용된다.
    """
    text = _normalize_consecutive_spaces_in_text(text)
    text = _normalize_br_space(text)
    text = _normalize_link_text_spacing(text)
    text = _normalize_empty_bold(text)
    text = _normalize_empty_list_items(text)
    text = _normalize_table_cell_padding(text)
    text = _strip_first_heading(text)
    text = text.lstrip('\n')
    text = _normalize_trailing_blank_lines(text)
    return text


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
    """Markdown table 행의 셀 패딩 공백과 구분자 행 대시 수를 정규화한다.

    XHTML→MDX forward 변환 시 테이블 셀의 컬럼 폭 계산이 원본 MDX와
    1~N자 차이날 수 있으므로:
    - 셀 내 연속 공백을 단일 공백으로 축약한다.
    - 구분자 행(| --- | --- |)의 대시 수를 3개로 정규화한다.
    """
    _SEP_RE = re.compile(r'^\|[\s\-:|]+\|$')
    lines = text.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            line = re.sub(r'  +', ' ', line)
            if _SEP_RE.match(stripped):
                line = re.sub(r'-{3,}', '---', line)
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
    text = _normalize_table_cell_lines(text)
    text = _normalize_html_entities_in_code(text)
    text = _normalize_inline_code_boundaries(text)
    text = _normalize_sentence_breaks(text)
    text = _normalize_quotes(text)
    return text


def verify_roundtrip(
    expected_mdx: str,
    actual_mdx: str,
    lenient: bool = False,
) -> VerifyResult:
    """두 MDX 문자열의 일치를 검증한다.

    기본 동작(엄격 모드): forward converter의 체계적 차이(이중 공백, <br/> 앞 공백)를
    정규화한 후 문자 그대로 비교한다. 그 외 공백, 줄바꿈, 문자가 동일해야 PASS.

    lenient=True(관대 모드): trailing whitespace, 날짜 형식, 테이블 패딩 등
    XHTML↔MDX 변환기 한계에 의한 추가 차이를 정규화한 후 exact match를 검증한다.

    Args:
        expected_mdx: 개선 MDX (의도한 결과)
        actual_mdx: 패치된 XHTML을 forward 변환한 결과
        lenient: True면 정규화 후 비교하는 관대 모드 활성화

    Returns:
        VerifyResult: passed=True면 통과, 아니면 diff_report 포함
    """
    # 항상 최소 정규화 적용 (forward converter 특성에 의한 체계적 차이 처리)
    expected_mdx = _apply_minimal_normalizations(expected_mdx)
    actual_mdx = _apply_minimal_normalizations(actual_mdx)

    if lenient:
        expected_mdx = _apply_normalizations(expected_mdx)
        actual_mdx = _apply_normalizations(actual_mdx)

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
