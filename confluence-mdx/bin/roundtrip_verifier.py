"""Roundtrip Verifier — 패치된 XHTML의 forward 변환 결과와 개선 MDX의 완전 일치를 검증한다."""
from dataclasses import dataclass
import difflib


@dataclass
class VerifyResult:
    passed: bool
    diff_report: str


def verify_roundtrip(expected_mdx: str, actual_mdx: str) -> VerifyResult:
    """두 MDX 문자열의 완전 일치를 검증한다.

    정규화 없음. 공백, 줄바꿈, 모든 문자가 동일해야 PASS.

    Args:
        expected_mdx: 개선 MDX (의도한 결과)
        actual_mdx: 패치된 XHTML을 forward 변환한 결과

    Returns:
        VerifyResult: passed=True면 통과, 아니면 diff_report 포함
    """
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
