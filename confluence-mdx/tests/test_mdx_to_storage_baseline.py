from pathlib import Path
from subprocess import CompletedProcess

import pytest

from reverse_sync.mdx_to_storage_baseline import (
    BaselineResult,
    parse_failed_cases,
    parse_summary,
    render_report,
    run_batch_verify,
    write_report,
)


def test_parse_summary_ok():
    output = "[mdx->xhtml-verify] total=21 passed=3 failed=18\n"
    assert parse_summary(output) == (21, 3, 18)


def test_parse_summary_raises_when_missing():
    with pytest.raises(ValueError, match="summary line"):
        parse_summary("no summary here")


def test_parse_failed_cases_ok():
    output = "Failed cases: 100, 200, lists\n"
    assert parse_failed_cases(output) == ["100", "200", "lists"]


def test_parse_failed_cases_empty_when_not_present():
    assert parse_failed_cases("nothing") == []


def test_run_batch_verify_parses_cli_output(monkeypatch, tmp_path: Path):
    stdout = (
        "[mdx->xhtml-verify] total=21 passed=1 failed=20\n"
        "Failed cases: 100, 200\n"
    )

    def _mock_run(*_args, **_kwargs):
        return CompletedProcess(args=[], returncode=1, stdout=stdout, stderr="")

    monkeypatch.setattr("reverse_sync.mdx_to_storage_baseline.subprocess.run", _mock_run)

    result = run_batch_verify(tmp_path, Path("tests/testcases"), show_diff_limit=0)
    assert result.total == 21
    assert result.passed == 1
    assert result.failed == 20
    assert result.failed_cases == ["100", "200"]
    assert result.exit_code == 1


def test_render_report_contains_numbers_and_failed_cases():
    result = BaselineResult(
        total=21,
        passed=2,
        failed=19,
        failed_cases=["100", "lists"],
        exit_code=1,
        raw_output="",
    )
    report = render_report(
        command="python3 bin/mdx_to_storage_xhtml_verify_cli.py --testcases-dir tests/testcases --show-diff-limit 0",
        result=result,
        notes=["note-1", "note-2"],
    )
    assert "# Phase 1 Baseline Verify" in report
    assert "- total: 21" in report
    assert "- passed: 2" in report
    assert "- failed: 19" in report
    assert "- note-1" in report
    assert "100, lists" in report


def test_write_report_creates_parent_dir(tmp_path: Path):
    output_path = tmp_path / "docs" / "baseline.md"
    write_report(output_path, "# hi\n")
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == "# hi\n"
