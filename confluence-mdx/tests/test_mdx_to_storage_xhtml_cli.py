from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace

import pytest

import mdx_to_storage_xhtml_cli as cli


# ---------------------------------------------------------------------------
# convert subcommand
# ---------------------------------------------------------------------------


def test_convert_writes_output_file(monkeypatch, tmp_path, capsys):
    input_mdx = tmp_path / "in.mdx"
    output_xhtml = tmp_path / "out.xhtml"
    input_mdx.write_text("## Title\n\nBody\n", encoding="utf-8")

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(command="convert", input_mdx=input_mdx, output=output_xhtml),
    )

    rc = cli.main()
    assert rc == 0
    assert output_xhtml.exists()
    assert "<h1>Title</h1>" in output_xhtml.read_text(encoding="utf-8")
    assert "[convert] wrote:" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# verify subcommand
# ---------------------------------------------------------------------------


def test_verify_pass_returns_0(monkeypatch, tmp_path, capsys):
    input_mdx = tmp_path / "in.mdx"
    expected = tmp_path / "expected.xhtml"
    input_mdx.write_text("## Title\n\nBody\n", encoding="utf-8")
    expected.write_text("<h1>Title</h1><p>Body</p>", encoding="utf-8")

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="verify",
            input_mdx=input_mdx,
            expected=expected,
            show_diff=False,
        ),
    )
    rc = cli.main()
    assert rc == 0
    assert "[verify] passed" in capsys.readouterr().out


def test_verify_fail_with_diff_returns_1(monkeypatch, tmp_path, capsys):
    input_mdx = tmp_path / "in.mdx"
    expected = tmp_path / "expected.xhtml"
    input_mdx.write_text("## Title\n\nBody changed\n", encoding="utf-8")
    expected.write_text("<h1>Title</h1><p>Body</p>", encoding="utf-8")

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="verify",
            input_mdx=input_mdx,
            expected=expected,
            show_diff=True,
        ),
    )
    rc = cli.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "[verify] failed" in out
    assert "--- page.xhtml" in out


# ---------------------------------------------------------------------------
# batch-verify subcommand
# ---------------------------------------------------------------------------


def test_batch_verify_no_cases_returns_0(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
            pages_yaml=None,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [])
    rc = cli.main()
    assert rc == 0
    assert "No testcase directories containing page.xhtml + expected.mdx found." in capsys.readouterr().out


def test_batch_verify_fail_and_write_report(monkeypatch, tmp_path, capsys):
    case_dir = tmp_path / "101"
    case_dir.mkdir()
    report_path = tmp_path / "analysis.md"

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=1,
            show_analysis=True,
            write_analysis_report=report_path,
            ignore_ri_filename=False,
            pages_yaml=None,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case_dir])

    def _verify(case_dir_param, ignore_ri_filename=False, link_resolver=None):
        return SimpleNamespace(case_id=case_dir_param.name, passed=False, diff_report="diff-101")

    monkeypatch.setattr(cli, "verify_testcase_dir", _verify)
    rc = cli.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "[mdx->xhtml-verify] total=1 passed=0 failed=1" in out
    assert "[analysis] priorities:" in out
    assert report_path.exists()
    assert "Priority Summary" in report_path.read_text(encoding="utf-8")


def test_batch_verify_passes_ignore_ri_filename_option(monkeypatch, tmp_path):
    case_dir = tmp_path / "101"
    case_dir.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=0,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=True,
            pages_yaml=None,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case_dir])

    called = {}

    def _verify(case, ignore_ri_filename=False, link_resolver=None):
        called["case"] = case
        called["ignore"] = ignore_ri_filename
        called["resolver"] = link_resolver
        return SimpleNamespace(case_id="101", passed=True, diff_report="")

    monkeypatch.setattr(cli, "verify_testcase_dir", _verify)
    rc = cli.main()
    assert rc == 0
    assert called["ignore"] is True
    assert called["resolver"] is None


def test_batch_verify_builds_link_resolver_when_pages_yaml_provided(monkeypatch, tmp_path):
    case_dir = tmp_path / "101"
    case_dir.mkdir()
    pages_yaml = tmp_path / "pages.yaml"
    pages_yaml.write_text(
        """
- page_id: "101"
  title_orig: "Example"
  path: ["example"]
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=0,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
            pages_yaml=pages_yaml,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case_dir])

    called = {}

    def _verify(case, ignore_ri_filename=False, link_resolver=None):
        called["case"] = case
        called["ignore"] = ignore_ri_filename
        called["resolver"] = link_resolver
        return SimpleNamespace(case_id="101", passed=True, diff_report="")

    monkeypatch.setattr(cli, "verify_testcase_dir", _verify)
    rc = cli.main()
    assert rc == 0
    assert called["ignore"] is False
    assert called["resolver"] is not None


def test_batch_verify_returns_2_when_testcases_dir_missing(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=Path("/tmp/not-found"),
            case_id=None,
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
            pages_yaml=None,
        ),
    )
    rc = cli.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "Error: testcases dir not found" in captured.err


def test_batch_verify_returns_2_when_case_id_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id="missing",
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
            pages_yaml=None,
        ),
    )
    rc = cli.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "Error: case not found" in captured.err


def test_batch_verify_all_pass_returns_0(monkeypatch, tmp_path, capsys):
    case_dir = tmp_path / "101"
    case_dir.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
            pages_yaml=None,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case_dir])
    monkeypatch.setattr(
        cli,
        "verify_testcase_dir",
        lambda *args, **kwargs: SimpleNamespace(case_id="101", passed=True, diff_report=""),
    )

    rc = cli.main()
    assert rc == 0
    output = capsys.readouterr().out
    assert "[mdx->xhtml-verify] total=1 passed=1 failed=0" in output


def test_batch_verify_case_id_returns_2_when_required_files_missing(monkeypatch, tmp_path, capsys):
    case_dir = tmp_path / "101"
    case_dir.mkdir()
    # directory exists but page.xhtml and expected.mdx are missing
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id="101",
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
            pages_yaml=None,
        ),
    )
    rc = cli.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "not found in" in captured.err


def test_batch_verify_case_id_single_case_pass(monkeypatch, tmp_path, capsys):
    case_dir = tmp_path / "101"
    case_dir.mkdir()
    (case_dir / "expected.mdx").write_text("## Title\n\nBody\n", encoding="utf-8")
    (case_dir / "page.xhtml").write_text("<h1>Title</h1><p>Body</p>", encoding="utf-8")

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id="101",
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
            pages_yaml=None,
        ),
    )
    rc = cli.main()
    assert rc == 0
    output = capsys.readouterr().out
    assert "[mdx->xhtml-verify] total=1 passed=1 failed=0" in output


def test_batch_verify_has_failures_returns_1_and_respects_diff_limit(monkeypatch, tmp_path, capsys):
    case_a = tmp_path / "101"
    case_b = tmp_path / "102"
    case_a.mkdir()
    case_b.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=1,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
            pages_yaml=None,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case_a, case_b])

    results = {
        "101": SimpleNamespace(case_id="101", passed=False, diff_report="diff-101"),
        "102": SimpleNamespace(case_id="102", passed=False, diff_report="diff-102"),
    }
    monkeypatch.setattr(
        cli,
        "verify_testcase_dir",
        lambda case_dir, **kwargs: results[case_dir.name],
    )

    rc = cli.main()
    assert rc == 1
    output = capsys.readouterr().out
    assert "[mdx->xhtml-verify] total=2 passed=0 failed=2" in output
    assert "Failed cases: 101, 102" in output
    assert "--- diff #1: 101 ---" in output
    assert "diff-101" in output
    assert "diff-102" not in output


def test_batch_verify_show_analysis_and_write_report(monkeypatch, tmp_path, capsys):
    case_a = tmp_path / "101"
    case_a.mkdir()
    report_path = tmp_path / "reports" / "verify-analysis.md"

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="batch-verify",
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=0,
            show_analysis=True,
            write_analysis_report=report_path,
            ignore_ri_filename=False,
            pages_yaml=None,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case_a])
    monkeypatch.setattr(
        cli,
        "verify_testcase_dir",
        lambda *args, **kwargs: SimpleNamespace(
            case_id="101",
            passed=False,
            diff_report='-<ac:link><ri:page /></ac:link>\n+<a href="#link-error">x</a>',
        ),
    )

    rc = cli.main()
    assert rc == 1
    output = capsys.readouterr().out
    assert "[analysis] priorities:" in output
    assert "[analysis] top reasons:" in output
    assert "[analysis] report written:" in output
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "Priority Summary" in report
    assert "internal_link_unresolved" in report


# ---------------------------------------------------------------------------
# final-verify subcommand
# ---------------------------------------------------------------------------


def test_final_verify_runs_and_writes_report(monkeypatch, tmp_path, capsys):
    output_path = tmp_path / "reports" / "final.md"

    # Mock the logic function to avoid needing real testcases
    from reverse_sync.mdx_to_storage_xhtml_verify import VerificationSummary

    fake_summary = VerificationSummary(
        total=21,
        passed=20,
        failed=1,
        failed_case_ids=["100"],
        by_priority={"P1": 1},
        by_reason={"other": 1},
        analyses=[],
    )
    fake_result = cli.FinalVerifyResult(summary=fake_summary, target_pass=18)

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="final-verify",
            testcases_dir=tmp_path,
            target_pass=18,
            output=output_path,
        ),
    )
    monkeypatch.setattr(cli, "_run_final_verify_logic", lambda testcases_dir, target_pass: fake_result)

    rc = cli.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "[final-verify] report written:" in out
    assert "[final-verify] total=21 passed=20 failed=1" in out
    assert output_path.exists()
    report = output_path.read_text(encoding="utf-8")
    assert "Phase 3 Final Verification" in report
    assert "goal_met: yes" in report


def test_final_verify_goal_not_met(monkeypatch, tmp_path, capsys):
    output_path = tmp_path / "reports" / "final.md"

    from reverse_sync.mdx_to_storage_xhtml_verify import VerificationSummary

    fake_summary = VerificationSummary(
        total=21,
        passed=10,
        failed=11,
        failed_case_ids=["100", "101"],
        by_priority={"P1": 3, "P2": 5, "P3": 3},
        by_reason={"internal_link_unresolved": 2, "other": 9},
        analyses=[],
    )
    fake_result = cli.FinalVerifyResult(summary=fake_summary, target_pass=18)

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="final-verify",
            testcases_dir=tmp_path,
            target_pass=18,
            output=output_path,
        ),
    )
    monkeypatch.setattr(cli, "_run_final_verify_logic", lambda testcases_dir, target_pass: fake_result)

    rc = cli.main()
    assert rc == 0
    report = output_path.read_text(encoding="utf-8")
    assert "goal_met: no" in report
    assert "remaining_to_goal: 8" in report
    assert "Remaining Work" in report


def test_final_verify_empty_testcases(monkeypatch, tmp_path, capsys):
    output_path = tmp_path / "reports" / "final.md"

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="final-verify",
            testcases_dir=tmp_path,
            target_pass=18,
            output=output_path,
        ),
    )
    # Use actual logic with an empty testcases dir
    rc = cli.main()
    assert rc == 0
    report = output_path.read_text(encoding="utf-8")
    assert "total: 0" in report
    assert "goal_met: no" in report


# ---------------------------------------------------------------------------
# baseline subcommand
# ---------------------------------------------------------------------------


def test_baseline_runs_and_writes_report(monkeypatch, tmp_path, capsys):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="baseline",
            project_dir=project_dir,
            testcases_dir=Path("tests/testcases"),
            output=Path("docs/out.md"),
            show_diff_limit=0,
        ),
    )

    fake_result = cli.BaselineResult(
        total=21, passed=0, failed=21, failed_cases=["100"], exit_code=1, raw_output="",
    )
    calls: dict[str, object] = {}

    def _mock_run_batch_verify(project_dir, testcases_dir, show_diff_limit):
        calls["run"] = (project_dir, testcases_dir, show_diff_limit)
        return fake_result

    monkeypatch.setattr(cli, "_baseline_run_batch_verify", _mock_run_batch_verify)

    rc = cli.main()
    assert rc == 0
    assert calls["run"] == (project_dir, Path("tests/testcases"), 0)

    output = capsys.readouterr().out
    assert "[baseline] total=21 passed=0 failed=21 output=docs/out.md" in output

    report_file = project_dir / "docs" / "out.md"
    assert report_file.exists()
    report = report_file.read_text(encoding="utf-8")
    assert "Phase 1 Baseline Verify" in report
    assert "- total: 21" in report


def test_baseline_passes_diff_limit_to_runner(monkeypatch, tmp_path):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            command="baseline",
            project_dir=project_dir,
            testcases_dir=Path("tests/testcases"),
            output=Path("docs/out.md"),
            show_diff_limit=5,
        ),
    )

    def _mock_run_batch_verify(project_dir, testcases_dir, show_diff_limit):
        captured["args"] = (project_dir, testcases_dir, show_diff_limit)
        return cli.BaselineResult(
            total=1, passed=1, failed=0, failed_cases=[], exit_code=0, raw_output="",
        )

    monkeypatch.setattr(cli, "_baseline_run_batch_verify", _mock_run_batch_verify)

    cli.main()
    assert captured["args"] == (project_dir, Path("tests/testcases"), 5)


# ---------------------------------------------------------------------------
# baseline inlined helpers (ported from test_mdx_to_storage_baseline.py)
# ---------------------------------------------------------------------------


def test_baseline_parse_summary_ok():
    output = "[mdx->xhtml-verify] total=21 passed=3 failed=18\n"
    assert cli._baseline_parse_summary(output) == (21, 3, 18)


def test_baseline_parse_summary_raises_when_missing():
    with pytest.raises(ValueError, match="summary line"):
        cli._baseline_parse_summary("no summary here")


def test_baseline_parse_failed_cases_ok():
    output = "Failed cases: 100, 200, lists\n"
    assert cli._baseline_parse_failed_cases(output) == ["100", "200", "lists"]


def test_baseline_parse_failed_cases_empty_when_not_present():
    assert cli._baseline_parse_failed_cases("nothing") == []


def test_baseline_run_batch_verify_parses_cli_output(monkeypatch, tmp_path):
    stdout = (
        "[mdx->xhtml-verify] total=21 passed=1 failed=20\n"
        "Failed cases: 100, 200\n"
    )

    def _mock_run(*_args, **_kwargs):
        return CompletedProcess(args=[], returncode=1, stdout=stdout, stderr="")

    monkeypatch.setattr(cli.subprocess, "run", _mock_run)

    result = cli._baseline_run_batch_verify(tmp_path, Path("tests/testcases"), show_diff_limit=0)
    assert result.total == 21
    assert result.passed == 1
    assert result.failed == 20
    assert result.failed_cases == ["100", "200"]
    assert result.exit_code == 1


def test_baseline_render_report_contains_numbers_and_failed_cases():
    result = cli.BaselineResult(
        total=21,
        passed=2,
        failed=19,
        failed_cases=["100", "lists"],
        exit_code=1,
        raw_output="",
    )
    report = cli._baseline_render_report(
        command="python3 bin/mdx_to_storage_xhtml_cli.py batch-verify --testcases-dir tests/testcases --show-diff-limit 0",
        result=result,
        notes=["note-1", "note-2"],
    )
    assert "# Phase 1 Baseline Verify" in report
    assert "- total: 21" in report
    assert "- passed: 2" in report
    assert "- failed: 19" in report
    assert "- note-1" in report
    assert "100, lists" in report


def test_baseline_render_report_no_failed_cases_omits_section():
    result = cli.BaselineResult(
        total=5,
        passed=5,
        failed=0,
        failed_cases=[],
        exit_code=0,
        raw_output="",
    )
    report = cli._baseline_render_report(command="cmd", result=result, notes=["all pass"])
    assert "## Failed Cases" not in report
    assert "- all pass" in report


def test_baseline_render_report_default_notes_when_none():
    result = cli.BaselineResult(
        total=1, passed=0, failed=1,
        failed_cases=[], exit_code=1, raw_output="",
    )
    report = cli._baseline_render_report(command="cmd", result=result, notes=None)
    assert "Baseline measured from current" in report


def test_baseline_parse_summary_with_surrounding_output():
    output = (
        "Processing case 100...\n"
        "Processing case 200...\n"
        "[mdx->xhtml-verify] total=2 passed=1 failed=1\n"
        "Failed cases: 200\n"
    )
    assert cli._baseline_parse_summary(output) == (2, 1, 1)
    assert cli._baseline_parse_failed_cases(output) == ["200"]


def test_write_report_creates_parent_dir(tmp_path):
    output_path = tmp_path / "docs" / "baseline.md"
    cli._write_report(output_path, "# hi\n")
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == "# hi\n"


# ---------------------------------------------------------------------------
# final-verify inlined helpers (ported from test_mdx_to_storage_final_verify.py)
# ---------------------------------------------------------------------------


def test_render_final_verify_report_includes_goal_status():
    from reverse_sync.mdx_to_storage_xhtml_verify import VerificationSummary

    summary = VerificationSummary(
        total=21,
        passed=10,
        failed=11,
        failed_case_ids=["100", "101"],
        by_priority={"P1": 3, "P2": 5, "P3": 3},
        by_reason={"internal_link_unresolved": 2, "other": 9},
        analyses=[],
    )
    result = cli.FinalVerifyResult(summary=summary, target_pass=18)
    report = cli._render_final_verify_report(result)
    assert "goal_met: no" in report
    assert "remaining_to_goal: 8" in report
    assert "Reason Breakdown" in report


def test_final_verify_write_report_creates_parent_dir(tmp_path):
    output = tmp_path / "nested" / "report.md"
    cli._write_report(output, "# title\n")
    assert output.exists()
    assert output.read_text(encoding="utf-8") == "# title\n"


def test_run_final_verify_logic_empty_testcases(tmp_path):
    result = cli._run_final_verify_logic(tmp_path, target_pass=18)
    assert result.summary.total == 0
    assert result.summary.passed == 0
    assert result.summary.failed == 0
    assert result.goal_met is False
