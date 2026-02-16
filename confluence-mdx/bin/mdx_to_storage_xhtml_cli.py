#!/usr/bin/env python3
"""MDX -> Confluence Storage XHTML CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mdx_to_storage import emit_document, parse_mdx
from reverse_sync.mdx_to_storage_xhtml_verify import (
    VerificationSummary,
    iter_testcase_dirs,
    summarize_results,
    verify_expected_mdx_against_page_xhtml,
    verify_testcase_dir,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert MDX to Confluence Storage XHTML and verify against testcases",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    convert = sub.add_parser("convert", help="Convert a single MDX file to XHTML")
    convert.add_argument("input_mdx", type=Path, help="Input MDX file")
    convert.add_argument("-o", "--output", type=Path, help="Output XHTML file")

    verify = sub.add_parser("verify", help="Verify a single MDX file against expected XHTML")
    verify.add_argument("input_mdx", type=Path, help="Input MDX file")
    verify.add_argument("--expected", type=Path, required=True, help="Expected page.xhtml file")
    verify.add_argument("--show-diff", action="store_true", help="Print diff when verification fails")

    batch = sub.add_parser("batch-verify", help="Run batch verification for testcase directories")
    batch.add_argument(
        "--testcases-dir",
        type=Path,
        default=Path("tests/testcases"),
        help="Root directory containing testcase subdirectories",
    )
    batch.add_argument("--case-id", help="Only run a specific testcase directory name")
    batch.add_argument("--show-diff-limit", type=int, default=3, help="Max number of failing case diffs to print")
    batch.add_argument("--show-analysis", action="store_true", help="Print reason/priority summary")
    batch.add_argument("--write-analysis-report", type=Path, help="Write markdown analysis report")

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


def _run_convert(args: argparse.Namespace) -> int:
    if not args.input_mdx.exists():
        print(f"Error: input file not found: {args.input_mdx}", file=sys.stderr)
        return 2
    mdx_text = args.input_mdx.read_text(encoding="utf-8")
    xhtml = emit_document(parse_mdx(mdx_text))
    if args.output:
        args.output.write_text(xhtml, encoding="utf-8")
        print(f"[convert] wrote: {args.output}")
    else:
        print(xhtml)
    return 0


def _run_verify(args: argparse.Namespace) -> int:
    if not args.input_mdx.exists():
        print(f"Error: input file not found: {args.input_mdx}", file=sys.stderr)
        return 2
    if not args.expected.exists():
        print(f"Error: expected file not found: {args.expected}", file=sys.stderr)
        return 2

    mdx_text = args.input_mdx.read_text(encoding="utf-8")
    page_xhtml = args.expected.read_text(encoding="utf-8")
    passed, _generated, diff_report = verify_expected_mdx_against_page_xhtml(mdx_text, page_xhtml)
    if passed:
        print("[verify] passed")
        return 0
    print("[verify] failed")
    if args.show_diff:
        print(diff_report)
    return 1


def _resolve_case_dirs(testcases_dir: Path, case_id: str | None) -> tuple[int, list[Path]]:
    if not testcases_dir.is_dir():
        print(f"Error: testcases dir not found: {testcases_dir}", file=sys.stderr)
        return 2, []

    if case_id:
        case_dir = testcases_dir / case_id
        if not case_dir.is_dir():
            print(f"Error: case not found: {case_dir}", file=sys.stderr)
            return 2, []
        for required in ("page.xhtml", "expected.mdx"):
            if not (case_dir / required).exists():
                print(f"Error: {required} not found in {case_dir}", file=sys.stderr)
                return 2, []
        return 0, [case_dir]

    case_dirs = list(iter_testcase_dirs(testcases_dir))
    if not case_dirs:
        print("No testcase directories containing page.xhtml + expected.mdx found.")
    return 0, case_dirs


def _run_batch_verify(args: argparse.Namespace) -> int:
    rc, case_dirs = _resolve_case_dirs(args.testcases_dir, args.case_id)
    if rc != 0:
        return rc
    if not case_dirs:
        return 0

    results = [verify_testcase_dir(case_dir) for case_dir in case_dirs]
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
            top = sorted(summary.by_reason.items(), key=lambda item: (-item[1], item[0]))
            print("[analysis] top reasons:", ", ".join(f"{k}={v}" for k, v in top))

    if args.write_analysis_report:
        report = _format_analysis_report(summary)
        args.write_analysis_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_analysis_report.write_text(report, encoding="utf-8")
        print(f"[analysis] report written: {args.write_analysis_report}")

    return 1 if failed else 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "convert":
        return _run_convert(args)
    if args.command == "verify":
        return _run_verify(args)
    if args.command == "batch-verify":
        return _run_batch_verify(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
