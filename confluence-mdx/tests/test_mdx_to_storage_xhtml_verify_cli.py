from pathlib import Path
from types import SimpleNamespace

import mdx_to_storage_xhtml_verify_cli as cli


def test_main_returns_2_when_testcases_dir_missing(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=Path("/tmp/not-found"),
            case_id=None,
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
        ),
    )
    rc = cli.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "Error: testcases dir not found" in captured.err


def test_main_returns_2_when_case_id_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id="missing",
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
        ),
    )
    rc = cli.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "Error: case not found" in captured.err


def test_main_returns_0_when_no_case_dirs(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [])

    rc = cli.main()
    assert rc == 0
    assert "No testcase directories containing page.xhtml + expected.mdx found." in capsys.readouterr().out


def test_main_all_pass_returns_0(monkeypatch, tmp_path, capsys):
    case_dir = tmp_path / "101"
    case_dir.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
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


def test_main_case_id_returns_2_when_required_files_missing(monkeypatch, tmp_path, capsys):
    case_dir = tmp_path / "101"
    case_dir.mkdir()
    # directory exists but page.xhtml and expected.mdx are missing
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id="101",
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
        ),
    )
    rc = cli.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "not found in" in captured.err


def test_main_case_id_single_case_pass(monkeypatch, tmp_path, capsys):
    case_dir = tmp_path / "101"
    case_dir.mkdir()
    (case_dir / "expected.mdx").write_text("## Title\n\nBody\n", encoding="utf-8")
    (case_dir / "page.xhtml").write_text("<h1>Title</h1><p>Body</p>", encoding="utf-8")

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id="101",
            show_diff_limit=3,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
        ),
    )
    rc = cli.main()
    assert rc == 0
    output = capsys.readouterr().out
    assert "[mdx->xhtml-verify] total=1 passed=1 failed=0" in output


def test_main_has_failures_returns_1_and_respects_diff_limit(monkeypatch, tmp_path, capsys):
    case_a = tmp_path / "101"
    case_b = tmp_path / "102"
    case_a.mkdir()
    case_b.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=1,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=False,
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


def test_main_show_analysis_and_write_report(monkeypatch, tmp_path, capsys):
    case_a = tmp_path / "101"
    case_a.mkdir()
    report_path = tmp_path / "reports" / "verify-analysis.md"

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=0,
            show_analysis=True,
            write_analysis_report=report_path,
            ignore_ri_filename=False,
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


def test_main_passes_ignore_ri_filename_option(monkeypatch, tmp_path):
    case_dir = tmp_path / "101"
    case_dir.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id=None,
            show_diff_limit=0,
            show_analysis=False,
            write_analysis_report=None,
            ignore_ri_filename=True,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case_dir])

    called = {}

    def _verify(case, ignore_ri_filename=False):
        called["case"] = case
        called["ignore"] = ignore_ri_filename
        return SimpleNamespace(case_id="101", passed=True, diff_report="")

    monkeypatch.setattr(cli, "verify_testcase_dir", _verify)
    rc = cli.main()
    assert rc == 0
    assert called["ignore"] is True
