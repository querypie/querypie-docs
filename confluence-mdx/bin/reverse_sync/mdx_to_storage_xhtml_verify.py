"""MDX -> Storage XHTML 검증 유틸리티.

`expected.mdx`를 XHTML fragment로 생성하고 `page.xhtml`과 비교한다.
비교는 BeautifulSoup prettify 기반 정규화를 사용해 포맷 차이를 줄인다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from mdx_to_storage import emit_document, parse_mdx
from xhtml_beautify_diff import beautify_xhtml, xhtml_diff


@dataclass
class CaseVerification:
    case_id: str
    passed: bool
    generated_xhtml: str
    diff_report: str


@dataclass
class FailureAnalysis:
    case_id: str
    priority: str
    reasons: list[str]


@dataclass
class VerificationSummary:
    total: int
    passed: int
    failed: int
    failed_case_ids: list[str]
    by_priority: dict[str, int]
    by_reason: dict[str, int]
    analyses: list[FailureAnalysis]


def mdx_to_storage_xhtml_fragment(mdx_text: str) -> str:
    """MDX 텍스트를 Confluence Storage XHTML fragment로 변환한다."""
    blocks = parse_mdx(mdx_text)
    return emit_document(blocks)


def _normalize_xhtml(xhtml: str) -> str:
    return beautify_xhtml(xhtml).strip()


def verify_expected_mdx_against_page_xhtml(
    expected_mdx: str, page_xhtml: str
) -> tuple[bool, str, str]:
    """expected.mdx로 생성한 XHTML과 page.xhtml을 비교한다."""
    generated = mdx_to_storage_xhtml_fragment(expected_mdx)
    generated_norm = _normalize_xhtml(generated)
    page_norm = _normalize_xhtml(page_xhtml)

    diff_lines = xhtml_diff(
        page_norm,
        generated_norm,
        label_a="page.xhtml",
        label_b="generated-from-expected.mdx.xhtml",
    )
    if not diff_lines:
        return True, generated, ""
    return False, generated, "\n".join(diff_lines)


def iter_testcase_dirs(testcases_dir: Path) -> Iterable[Path]:
    """`page.xhtml`과 `expected.mdx`가 있는 테스트케이스 디렉토리를 순회한다."""
    for child in sorted(testcases_dir.iterdir()):
        if not child.is_dir():
            continue
        if (child / "page.xhtml").exists() and (child / "expected.mdx").exists():
            yield child


def verify_testcase_dir(case_dir: Path) -> CaseVerification:
    """단일 테스트케이스 디렉토리를 검증한다."""
    expected_mdx = (case_dir / "expected.mdx").read_text(encoding="utf-8")
    page_xhtml = (case_dir / "page.xhtml").read_text(encoding="utf-8")
    passed, generated, diff_report = verify_expected_mdx_against_page_xhtml(
        expected_mdx, page_xhtml
    )
    return CaseVerification(
        case_id=case_dir.name,
        passed=passed,
        generated_xhtml=generated,
        diff_report=diff_report,
    )


_REASON_PRIORITY: dict[str, str] = {
    "internal_link_unresolved": "P1",
    "table_cell_structure_mismatch": "P1",
    "blockquote_or_paragraph_grouping": "P1",
    "verify_filter_noise": "P2",
    "non_reversible_macro_noise": "P2",
    "empty_paragraph_style_mismatch": "P2",
    "other": "P3",
}
_PRIORITY_ORDER = {"P1": 1, "P2": 2, "P3": 3}


def classify_failure_reasons(diff_report: str) -> list[str]:
    reasons: list[str] = []

    if any(
        token in diff_report
        for token in (
            "ac:macro-id",
            "ac:local-id",
            "local-id",
            "ri:version-at-save",
            "ac:original-height",
            "ac:original-width",
            "ac:custom-width",
            "data-table-width",
            "ac:breakout-mode",
            "ac:breakout-width",
            "<ac:adf-mark",
        )
    ):
        reasons.append("verify_filter_noise")

    if any(
        token in diff_report
        for token in (
            'ac:name="toc"',
            'ac:name="view-file"',
            "<ac:layout",
            "<ac:layout-section",
            "<ac:layout-cell",
        )
    ):
        reasons.append("non_reversible_macro_noise")

    if any(token in diff_report for token in ("<ri:page", "<ri:space", "href=\"#link-error\"")):
        reasons.append("internal_link_unresolved")

    if "<table" in diff_report and any(token in diff_report for token in ("<th", "<td", "<colgroup")):
        reasons.append("table_cell_structure_mismatch")

    if "<blockquote" in diff_report or "\n-<p>\n+<p />" in diff_report:
        reasons.append("blockquote_or_paragraph_grouping")

    if "<p />" in diff_report and "<p>" in diff_report:
        reasons.append("empty_paragraph_style_mismatch")

    if not reasons:
        reasons.append("other")
    return reasons


def _pick_priority(reasons: list[str]) -> str:
    priorities = [_REASON_PRIORITY.get(reason, "P3") for reason in reasons]
    return sorted(priorities, key=lambda priority: _PRIORITY_ORDER.get(priority, 99))[0]


def analyze_failed_cases(results: list[CaseVerification]) -> list[FailureAnalysis]:
    analyses: list[FailureAnalysis] = []
    for result in results:
        if result.passed:
            continue
        reasons = classify_failure_reasons(result.diff_report)
        analyses.append(
            FailureAnalysis(
                case_id=result.case_id,
                priority=_pick_priority(reasons),
                reasons=reasons,
            )
        )
    return analyses


def summarize_results(results: list[CaseVerification]) -> VerificationSummary:
    failed_case_ids = [result.case_id for result in results if not result.passed]
    analyses = analyze_failed_cases(results)

    by_priority = {"P1": 0, "P2": 0, "P3": 0}
    by_reason: dict[str, int] = {}
    for analysis in analyses:
        by_priority[analysis.priority] = by_priority.get(analysis.priority, 0) + 1
        for reason in analysis.reasons:
            by_reason[reason] = by_reason.get(reason, 0) + 1

    return VerificationSummary(
        total=len(results),
        passed=len(results) - len(failed_case_ids),
        failed=len(failed_case_ids),
        failed_case_ids=failed_case_ids,
        by_priority=by_priority,
        by_reason=by_reason,
        analyses=analyses,
    )
