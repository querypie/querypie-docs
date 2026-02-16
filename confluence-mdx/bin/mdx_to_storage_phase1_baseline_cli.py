#!/usr/bin/env python3
"""Task 1.7 baseline recorder CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reverse_sync.mdx_to_storage_baseline import (
    render_report,
    run_batch_verify,
    write_report,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run mdx->xhtml batch verify and write Phase 1 baseline report",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path("."),
        help="confluence-mdx project root",
    )
    parser.add_argument(
        "--testcases-dir",
        type=Path,
        default=Path("tests/testcases"),
        help="testcases directory path (relative to project-dir)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/mdx_to_storage_phase1_baseline.md"),
        help="markdown output path (relative to project-dir)",
    )
    parser.add_argument(
        "--show-diff-limit",
        type=int,
        default=0,
        help="verify CLI diff output limit",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    project_dir: Path = args.project_dir
    testcases_dir: Path = args.testcases_dir
    output_path: Path = args.output

    result = run_batch_verify(
        project_dir=project_dir,
        testcases_dir=testcases_dir,
        show_diff_limit=args.show_diff_limit,
    )
    command = (
        "python3 bin/mdx_to_storage_xhtml_verify_cli.py "
        f"--testcases-dir {testcases_dir} "
        f"--show-diff-limit {args.show_diff_limit}"
    )
    notes = [
        "Task 1.4/1.5 범위(heading/paragraph/code/list/hr + verify CLI 전환) 기준선 결과다.",
        "Callout/figure/table/복합 매크로 미지원 항목이 남아 있으면 pass 수가 낮을 수 있다.",
    ]
    report = render_report(command=command, result=result, notes=notes)
    write_report(project_dir / output_path, report)
    print(
        f"[baseline] total={result.total} passed={result.passed} failed={result.failed} "
        f"output={output_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
