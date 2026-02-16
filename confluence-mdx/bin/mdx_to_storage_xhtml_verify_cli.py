#!/usr/bin/env python3
"""tests/testcases의 expected.mdx -> page.xhtml 동등성 검증 CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mdx_to_storage.link_resolver import LinkResolver, load_pages_yaml
from reverse_sync.mdx_to_storage_xhtml_verify import (
    VerificationSummary,
    iter_testcase_dirs,
    summarize_results,
    verify_testcase_dir,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate expected.mdx can generate XHTML equivalent to page.xhtml"
    )
    parser.add_argument(
        "--testcases-dir",
        type=Path,
        default=Path("tests/testcases"),
        help="Root directory containing testcase subdirectories",
    )
    parser.add_argument(
        "--case-id",
        help="Only run a specific testcase directory name",
    )
    parser.add_argument(
        "--show-diff-limit",
        type=int,
        default=3,
        help="Max number of failing case diffs to print",
    )
    parser.add_argument(
        "--show-analysis",
        action="store_true",
        help="Print failure reason/priority summary for Task 2.7 tracking",
    )
    parser.add_argument(
        "--write-analysis-report",
        type=Path,
        help="Write markdown failure analysis report to file",
    )
    parser.add_argument(
        "--ignore-ri-filename",
        action="store_true",
        help="Ignore ri:filename attribute during XHTML comparison",
    )
    parser.add_argument(
        "--pages-yaml",
        type=Path,
        help="pages.yaml path for internal link resolution",
    )
    return parser


def _format_analysis_report(summary: VerificationSummary) -> str:
    lines = [
        "# MDX -> Storage XHTML Batch Verify Analysis",
        "",
        f"- total: {summary.total}",
        f"- passed: {summary.passed}",
        f"- failed: {summary.failed}",
        "",
        "## Priority Summary",
        "",
        f"- P1: {summary.by_priority.get('P1', 0)}",
        f"- P2: {summary.by_priority.get('P2', 0)}",
        f"- P3: {summary.by_priority.get('P3', 0)}",
        "",
        "## Reason Summary",
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
            lines.append(
                f"- {analysis.case_id}: {analysis.priority} ({', '.join(analysis.reasons)})"
            )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    testcases_dir: Path = args.testcases_dir
    if not testcases_dir.is_dir():
        print(f"Error: testcases dir not found: {testcases_dir}", file=sys.stderr)
        return 2

    if args.case_id:
        case_dir = testcases_dir / args.case_id
        if not case_dir.is_dir():
            print(f"Error: case not found: {case_dir}", file=sys.stderr)
            return 2
        for required in ("page.xhtml", "expected.mdx"):
            if not (case_dir / required).exists():
                print(f"Error: {required} not found in {case_dir}", file=sys.stderr)
                return 2
        case_dirs = [case_dir]
    else:
        case_dirs = list(iter_testcase_dirs(testcases_dir))

    if not case_dirs:
        print("No testcase directories containing page.xhtml + expected.mdx found.")
        return 0

    link_resolver = None
    if args.pages_yaml:
        pages = load_pages_yaml(args.pages_yaml)
        link_resolver = LinkResolver(pages)

    results = []
    for case_dir in case_dirs:
        results.append(
            verify_testcase_dir(
                case_dir,
                ignore_ri_filename=args.ignore_ri_filename,
                link_resolver=link_resolver,
            )
        )
    summary = summarize_results(results)
    failed = [r for r in results if not r.passed]

    print(
        f"[mdx->xhtml-verify] total={summary.total} passed={summary.passed} failed={summary.failed}"
    )

    if failed:
        print("Failed cases:", ", ".join(r.case_id for r in failed))
        limit = max(0, args.show_diff_limit)
        for idx, case in enumerate(failed[:limit], start=1):
            print(f"\n--- diff #{idx}: {case.case_id} ---")
            print(case.diff_report)
    if args.show_analysis:
        print(
            "[analysis] priorities:",
            ", ".join(f"{k}={v}" for k, v in sorted(summary.by_priority.items())),
        )
        if summary.by_reason:
            top_reasons = sorted(summary.by_reason.items(), key=lambda item: (-item[1], item[0]))
            print(
                "[analysis] top reasons:",
                ", ".join(f"{reason}={count}" for reason, count in top_reasons),
            )
    if args.write_analysis_report:
        report = _format_analysis_report(summary)
        args.write_analysis_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_analysis_report.write_text(report, encoding="utf-8")
        print(f"[analysis] report written: {args.write_analysis_report}")

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
