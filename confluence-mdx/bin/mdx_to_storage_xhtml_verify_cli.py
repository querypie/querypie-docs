#!/usr/bin/env python3
"""tests/testcases의 expected.mdx -> page.xhtml 동등성 검증 CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from reverse_sync.mdx_to_storage_xhtml_verify import (
    iter_testcase_dirs,
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
        "--write-generated",
        action="store_true",
        help="Write generated XHTML file for each testcase",
    )
    parser.add_argument(
        "--generated-out-dir",
        type=Path,
        help="Directory to store generated XHTML when --write-generated is enabled",
    )
    parser.add_argument(
        "--diff-engine",
        choices=("internal", "external"),
        default="external",
        help="Diff engine: internal normalizer or external xhtml_beautify_diff.py",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Write verification summary report to a JSON file",
    )
    return parser


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
        case_dirs = [case_dir]
    else:
        case_dirs = list(iter_testcase_dirs(testcases_dir))

    if not case_dirs:
        print("No testcase directories containing page.xhtml + expected.mdx found.")
        return 0

    results = [
        verify_testcase_dir(
            case_dir,
            write_generated=args.write_generated,
            diff_engine=args.diff_engine,
            generated_out_dir=(
                args.generated_out_dir / case_dir.name
                if args.generated_out_dir is not None
                else None
            ),
        )
        for case_dir in case_dirs
    ]
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print(
        f"[mdx->xhtml-verify] total={len(results)} passed={len(passed)} failed={len(failed)}"
    )

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "total": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "failed_cases": [r.case_id for r in failed],
            "diff_engine": args.diff_engine,
            "write_generated": bool(args.write_generated),
        }
        args.report_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Report written: {args.report_json}")

    if failed:
        print("Failed cases:", ", ".join(r.case_id for r in failed))
        limit = max(0, args.show_diff_limit)
        for idx, case in enumerate(failed[:limit], start=1):
            print(f"\n--- diff #{idx}: {case.case_id} ---")
            print(case.diff_report)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
