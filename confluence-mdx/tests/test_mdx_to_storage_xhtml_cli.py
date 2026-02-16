from pathlib import Path
from types import SimpleNamespace

import mdx_to_storage_xhtml_cli as cli


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
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case_dir])

    def _verify(case_dir_param):
        return SimpleNamespace(case_id=case_dir_param.name, passed=False, diff_report="diff-101")

    monkeypatch.setattr(cli, "verify_testcase_dir", _verify)
    rc = cli.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "[mdx->xhtml-verify] total=1 passed=0 failed=1" in out
    assert "[analysis] priorities:" in out
    assert report_path.exists()
    assert "Priority Summary" in report_path.read_text(encoding="utf-8")
