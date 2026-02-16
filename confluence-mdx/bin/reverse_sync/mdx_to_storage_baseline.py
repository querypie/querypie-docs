"""Utilities for Task 1.7 baseline measurement/reporting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys


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


def parse_summary(output: str) -> tuple[int, int, int]:
    """Parse summary line from verify CLI output."""
    match = _SUMMARY_PATTERN.search(output)
    if not match:
        raise ValueError("verify summary line not found in output")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def parse_failed_cases(output: str) -> list[str]:
    """Parse failed case id list from verify CLI output."""
    match = _FAILED_CASES_PATTERN.search(output)
    if not match:
        return []
    raw = match.group(1).strip()
    if not raw:
        return []
    return [token.strip() for token in raw.split(",") if token.strip()]


def run_batch_verify(project_dir: Path, testcases_dir: Path, show_diff_limit: int = 0) -> BaselineResult:
    """Run mdx_to_storage_xhtml_verify_cli.py and parse baseline summary."""
    command = [
        sys.executable,
        "bin/mdx_to_storage_xhtml_verify_cli.py",
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
    total, passed, failed = parse_summary(output)
    return BaselineResult(
        total=total,
        passed=passed,
        failed=failed,
        failed_cases=parse_failed_cases(output),
        exit_code=completed.returncode,
        raw_output=output,
    )


def render_report(command: str, result: BaselineResult, notes: list[str] | None = None) -> str:
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


def write_report(output_path: Path, report: str) -> None:
    """Write markdown report to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
