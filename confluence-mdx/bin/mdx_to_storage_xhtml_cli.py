#!/usr/bin/env python3
"""MDX -> Confluence Storage XHTML CLI.

Unified entry point for convert, verify, batch-verify, final-verify, and baseline subcommands.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from mdx_to_storage import emit_document, parse_mdx
from mdx_to_storage.link_resolver import LinkResolver, load_pages_yaml
from reverse_sync.mdx_to_storage_xhtml_verify import (
    VerificationSummary,
    iter_testcase_dirs,
    summarize_results,
    verify_expected_mdx_against_page_xhtml,
    verify_testcase_dir,
)


# ---------------------------------------------------------------------------
# final-verify inlined dataclass / helpers
# ---------------------------------------------------------------------------


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


def _run_final_verify_logic(
    testcases_dir: Path,
    target_pass: int = 18,
) -> FinalVerifyResult:
    case_dirs = list(iter_testcase_dirs(testcases_dir))
    results = [verify_testcase_dir(case_dir) for case_dir in case_dirs]
    summary = summarize_results(results)
    return FinalVerifyResult(summary=summary, target_pass=target_pass)


def _render_final_verify_report(result: FinalVerifyResult) -> str:
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


# ---------------------------------------------------------------------------
# baseline inlined dataclass / helpers
# ---------------------------------------------------------------------------

_SUMMARY_PATTERN = re.compile(
    r"\[mdx->xhtml-verify\]\s+total=(\d+)\s+passed=(\d+)\s+failed=(\d+)"
)
_FAILED_CASES_PATTERN = re.compile(r"^Failed cases:\s*(.+)$", re.MULTILINE)


@dataclass
class BaselineResult:
    total: int
    passed: int
    failed: int
    failed_cases: list[str]
    exit_code: int
    raw_output: str


def _baseline_parse_summary(output: str) -> tuple[int, int, int]:
    """Parse summary line from verify CLI output."""
    match = _SUMMARY_PATTERN.search(output)
    if not match:
        raise ValueError("verify summary line not found in output")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _baseline_parse_failed_cases(output: str) -> list[str]:
    """Parse failed case id list from verify CLI output."""
    match = _FAILED_CASES_PATTERN.search(output)
    if not match:
        return []
    raw = match.group(1).strip()
    if not raw:
        return []
    return [token.strip() for token in raw.split(",") if token.strip()]


def _baseline_run_batch_verify(
    project_dir: Path, testcases_dir: Path, show_diff_limit: int = 0,
) -> BaselineResult:
    """Run batch-verify subcommand as a subprocess and parse baseline summary."""
    command = [
        sys.executable,
        "bin/mdx_to_storage_xhtml_cli.py",
        "batch-verify",
        "--testcases-dir",
        str(testcases_dir),
        "--show-diff-limit",
        str(show_diff_limit),
    ]
    completed = subprocess.run(
        command,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout
    total, passed, failed = _baseline_parse_summary(output)
    return BaselineResult(
        total=total,
        passed=passed,
        failed=failed,
        failed_cases=_baseline_parse_failed_cases(output),
        exit_code=completed.returncode,
        raw_output=output,
    )


def _baseline_render_report(
    command: str, result: BaselineResult, notes: list[str] | None = None,
) -> str:
    """Render markdown report for Phase 1 baseline."""
    lines = [
        "# Phase 1 Baseline Verify",
        "",
        "## Executed command",
        "",
        "```bash",
        command,
        "```",
        "",
        "## Result",
        "",
        f"- total: {result.total}",
        f"- passed: {result.passed}",
        f"- failed: {result.failed}",
        "",
        "## Notes",
        "",
    ]
    if notes:
        lines.extend([f"- {note}" for note in notes])
    else:
        lines.append("- Baseline measured from current mdx_to_storage verify path.")

    if result.failed_cases:
        lines.extend(
            [
                "",
                "## Failed Cases",
                "",
                f"- {', '.join(result.failed_cases)}",
            ]
        )

    return "\n".join(lines) + "\n"


def _write_report(path: Path, report: str) -> None:
    """Write markdown report to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert MDX to Confluence Storage XHTML and verify against testcases",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- convert ---
    convert = sub.add_parser("convert", help="Convert a single MDX file to XHTML")
    convert.add_argument("input_mdx", type=Path, help="Input MDX file")
    convert.add_argument("-o", "--output", type=Path, help="Output XHTML file")

    # --- verify ---
    verify = sub.add_parser("verify", help="Verify a single MDX file against expected XHTML")
    verify.add_argument("input_mdx", type=Path, help="Input MDX file")
    verify.add_argument("--expected", type=Path, required=True, help="Expected page.xhtml file")
    verify.add_argument("--show-diff", action="store_true", help="Print diff when verification fails")

    # --- batch-verify ---
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
    batch.add_argument(
        "--ignore-ri-filename",
        action="store_true",
        help="Ignore ri:filename attribute during XHTML comparison",
    )
    batch.add_argument(
        "--pages-yaml",
        type=Path,
        help="pages.yaml path for internal link resolution",
    )

    # --- final-verify ---
    fv = sub.add_parser("final-verify", help="Run final verification and write markdown report")
    fv.add_argument(
        "--testcases-dir",
        type=Path,
        default=Path("tests/testcases"),
        help="Root directory containing testcase subdirectories",
    )
    fv.add_argument(
        "--target-pass",
        type=int,
        default=18,
        help="Target pass count",
    )
    fv.add_argument(
        "--output",
        type=Path,
        default=Path("reports/phase3_final_verify.md"),
        help="Output markdown report path",
    )

    # --- baseline ---
    bl = sub.add_parser("baseline", help="Run batch verify and write Phase 1 baseline report")
    bl.add_argument(
        "--project-dir",
        type=Path,
        default=Path("."),
        help="confluence-mdx project root",
    )
    bl.add_argument(
        "--testcases-dir",
        type=Path,
        default=Path("tests/testcases"),
        help="testcases directory path (relative to project-dir)",
    )
    bl.add_argument(
        "--output",
        type=Path,
        default=Path("docs/mdx_to_storage_phase1_baseline.md"),
        help="markdown output path (relative to project-dir)",
    )
    bl.add_argument(
        "--show-diff-limit",
        type=int,
        default=0,
        help="verify CLI diff output limit",
    )

    return parser


# ---------------------------------------------------------------------------
# Analysis report (shared by batch-verify)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Subcommand runners
# ---------------------------------------------------------------------------


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

    # Build link_resolver from pages-yaml if provided
    link_resolver = None
    if args.pages_yaml:
        pages = load_pages_yaml(args.pages_yaml)
        link_resolver = LinkResolver(pages)

    results = [
        verify_testcase_dir(
            case_dir,
            ignore_ri_filename=args.ignore_ri_filename,
            link_resolver=link_resolver,
        )
        for case_dir in case_dirs
    ]
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


def _run_final_verify(args: argparse.Namespace) -> int:
    result = _run_final_verify_logic(args.testcases_dir, target_pass=args.target_pass)
    report = _render_final_verify_report(result)
    _write_report(args.output, report)
    print(f"[final-verify] report written: {args.output}")
    print(
        f"[final-verify] total={result.summary.total} passed={result.summary.passed} failed={result.summary.failed}"
    )
    return 0


def _run_baseline(args: argparse.Namespace) -> int:
    project_dir: Path = args.project_dir
    testcases_dir: Path = args.testcases_dir
    output_path: Path = args.output

    result = _baseline_run_batch_verify(
        project_dir=project_dir,
        testcases_dir=testcases_dir,
        show_diff_limit=args.show_diff_limit,
    )
    command = (
        "python3 bin/mdx_to_storage_xhtml_cli.py batch-verify "
        f"--testcases-dir {testcases_dir} "
        f"--show-diff-limit {args.show_diff_limit}"
    )
    notes = [
        "Task 1.4/1.5 범위(heading/paragraph/code/list/hr + verify CLI 전환) 기준선 결과다.",
        "Callout/figure/table/복합 매크로 미지원 항목이 남아 있으면 pass 수가 낮을 수 있다.",
    ]
    report = _baseline_render_report(command=command, result=result, notes=notes)
    _write_report(project_dir / output_path, report)
    print(
        f"[baseline] total={result.total} passed={result.passed} failed={result.failed} "
        f"output={output_path}"
    )
    return 0


# ---------------------------------------------------------------------------
# main dispatch
# ---------------------------------------------------------------------------


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "convert":
        return _run_convert(args)
    if args.command == "verify":
        return _run_verify(args)
    if args.command == "batch-verify":
        return _run_batch_verify(args)
    if args.command == "final-verify":
        return _run_final_verify(args)
    if args.command == "baseline":
        return _run_baseline(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
