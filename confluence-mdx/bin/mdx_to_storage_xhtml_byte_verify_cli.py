#!/usr/bin/env python3
"""Byte-equal verify CLI for lossless roundtrip."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lossless_roundtrip.byte_verify import iter_case_dirs, verify_case_dir


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Byte-equal verify for MDX -> XHTML restore")
    parser.add_argument(
        "--testcases-dir",
        type=Path,
        default=Path("tests/testcases"),
        help="Root directory containing testcase subdirectories",
    )
    parser.add_argument("--case-id", help="Only run one case directory")
    parser.add_argument(
        "--sidecar-name",
        default="expected.roundtrip.json",
        help="Sidecar file name inside each case dir",
    )
    parser.add_argument(
        "--show-fail-limit",
        type=int,
        default=10,
        help="Number of failed cases to print in detail",
    )
    return parser


def _resolve_case_dirs(testcases_dir: Path, case_id: str | None) -> tuple[int, list[Path]]:
    if not testcases_dir.is_dir():
        print(f"Error: testcases dir not found: {testcases_dir}", file=sys.stderr)
        return 2, []

    if case_id:
        case_dir = testcases_dir / case_id
        if not case_dir.is_dir():
            print(f"Error: case not found: {case_dir}", file=sys.stderr)
            return 2, []
        return 0, [case_dir]

    case_dirs = list(iter_case_dirs(testcases_dir))
    if not case_dirs:
        print("No testcase directories containing page.xhtml + expected.mdx found.")
    return 0, case_dirs


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    rc, case_dirs = _resolve_case_dirs(args.testcases_dir, args.case_id)
    if rc != 0:
        return rc
    if not case_dirs:
        return 0

    results = [verify_case_dir(case_dir, sidecar_name=args.sidecar_name) for case_dir in case_dirs]
    failed = [r for r in results if not r.passed]

    print(
        f"[mdx->xhtml-byte-verify] total={len(results)} passed={len(results)-len(failed)} failed={len(failed)}"
    )

    if failed:
        print("Failed cases:", ", ".join(r.case_id for r in failed))
        limit = max(0, args.show_fail_limit)
        for idx, result in enumerate(failed[:limit], start=1):
            print(
                f"- fail#{idx} case={result.case_id} reason={result.reason} mismatch_offset={result.first_mismatch_offset}"
            )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
