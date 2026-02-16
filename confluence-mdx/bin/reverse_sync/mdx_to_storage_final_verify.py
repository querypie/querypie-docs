#!/usr/bin/env python3
"""Phase 3 Task 3.5 final verification and report writer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

_SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from reverse_sync.mdx_to_storage_xhtml_verify import (
    VerificationSummary,
    iter_testcase_dirs,
    summarize_results,
    verify_testcase_dir,
)


@dataclass
class FinalVerifyResult:
    summary: VerificationSummary
    target_pass: int

    @property
    def goal_met(self) -> bool:
        return self.summary.passed >= self.target_pass

    @property
    def remaining_to_goal(self) -> int:
        return max(0, self.target_pass - self.summary.passed)


def run_final_verify(
    testcases_dir: Path,
    target_pass: int = 18,
) -> FinalVerifyResult:
    case_dirs = list(iter_testcase_dirs(testcases_dir))
    results = [verify_testcase_dir(case_dir) for case_dir in case_dirs]
    summary = summarize_results(results)
    return FinalVerifyResult(summary=summary, target_pass=target_pass)


def render_final_verify_report(result: FinalVerifyResult) -> str:
    summary = result.summary
    lines = [
        "# Phase 3 Final Verification",
        "",
        "## Summary",
        "",
        f"- total: {summary.total}",
        f"- passed: {summary.passed}",
        f"- failed: {summary.failed}",
        f"- target_pass: {result.target_pass}",
        f"- goal_met: {'yes' if result.goal_met else 'no'}",
        f"- remaining_to_goal: {result.remaining_to_goal}",
        "",
        "## Priority Breakdown",
        "",
        f"- P1: {summary.by_priority.get('P1', 0)}",
        f"- P2: {summary.by_priority.get('P2', 0)}",
        f"- P3: {summary.by_priority.get('P3', 0)}",
        "",
        "## Reason Breakdown",
        "",
    ]
    if not summary.by_reason:
        lines.append("- none")
    else:
        for reason, count in sorted(summary.by_reason.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {reason}: {count}")

    lines.extend(["", "## Failed Cases", ""])
    if not summary.analyses:
        lines.append("- none")
    else:
        for analysis in sorted(summary.analyses, key=lambda item: (item.priority, item.case_id)):
            lines.append(f"- {analysis.case_id}: {analysis.priority} ({', '.join(analysis.reasons)})")

    if not result.goal_met:
        lines.extend(
            [
                "",
                "## Remaining Work",
                "",
                "- Focus P1 first to maximize pass gain.",
                "- Re-run batch-verify after each fix and update this report.",
            ]
        )

    return "\n".join(lines) + "\n"


def write_report(path: Path, report: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run final verify and write markdown report")
    parser.add_argument(
        "--testcases-dir",
        type=Path,
        default=Path("tests/testcases"),
        help="Root directory containing testcase subdirectories",
    )
    parser.add_argument(
        "--target-pass",
        type=int,
        default=18,
        help="Target pass count",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/phase3_final_verify.md"),
        help="Output markdown report path",
    )
    args = parser.parse_args()

    result = run_final_verify(args.testcases_dir, target_pass=args.target_pass)
    report = render_final_verify_report(result)
    write_report(args.output, report)
    print(f"[final-verify] report written: {args.output}")
    print(
        f"[final-verify] total={result.summary.total} passed={result.summary.passed} failed={result.summary.failed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
