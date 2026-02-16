from pathlib import Path

from reverse_sync.mdx_to_storage_final_verify import (
    FinalVerifyResult,
    render_final_verify_report,
    run_final_verify,
    write_report,
)
from reverse_sync.mdx_to_storage_xhtml_verify import VerificationSummary


def test_render_final_verify_report_includes_goal_status():
    summary = VerificationSummary(
        total=21,
        passed=10,
        failed=11,
        failed_case_ids=["100", "101"],
        by_priority={"P1": 3, "P2": 5, "P3": 3},
        by_reason={"internal_link_unresolved": 2, "other": 9},
        analyses=[],
    )
    result = FinalVerifyResult(summary=summary, target_pass=18)
    report = render_final_verify_report(result)
    assert "goal_met: no" in report
    assert "remaining_to_goal: 8" in report
    assert "Reason Breakdown" in report


def test_write_report_creates_parent_dir(tmp_path: Path):
    output = tmp_path / "nested" / "report.md"
    write_report(output, "# title\n")
    assert output.exists()
    assert output.read_text(encoding="utf-8") == "# title\n"


def test_run_final_verify_empty_testcases(tmp_path: Path):
    result = run_final_verify(tmp_path, target_pass=18)
    assert result.summary.total == 0
    assert result.summary.passed == 0
    assert result.summary.failed == 0
    assert result.goal_met is False
