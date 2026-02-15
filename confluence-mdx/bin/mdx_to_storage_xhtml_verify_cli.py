#!/usr/bin/env python3
"""tests/testcases의 expected.mdx -> page.xhtml 동등성 검증 CLI."""

from __future__ import annotations

import argparse
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

    results = [verify_testcase_dir(case_dir) for case_dir in case_dirs]
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print(
        f"[mdx->xhtml-verify] total={len(results)} passed={len(passed)} failed={len(failed)}"
    )

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

