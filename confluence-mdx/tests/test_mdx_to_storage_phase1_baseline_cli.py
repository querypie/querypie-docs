from pathlib import Path
from types import SimpleNamespace

import mdx_to_storage_phase1_baseline_cli as cli


def test_main_runs_and_writes_report(monkeypatch, tmp_path: Path, capsys):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            project_dir=project_dir,
            testcases_dir=Path("tests/testcases"),
            output=Path("docs/out.md"),
            show_diff_limit=0,
        ),
    )

    fake_result = SimpleNamespace(total=21, passed=0, failed=21)
    calls: dict[str, object] = {}

    def _mock_run_batch_verify(project_dir: Path, testcases_dir: Path, show_diff_limit: int):
        calls["run"] = (project_dir, testcases_dir, show_diff_limit)
        return fake_result

    def _mock_render_report(command: str, result, notes):
        calls["render"] = (command, result, notes)
        return "# report\n"

    def _mock_write_report(path: Path, report: str):
        calls["write"] = (path, report)

    monkeypatch.setattr(cli, "run_batch_verify", _mock_run_batch_verify)
    monkeypatch.setattr(cli, "render_report", _mock_render_report)
    monkeypatch.setattr(cli, "write_report", _mock_write_report)

    rc = cli.main()
    assert rc == 0
    assert calls["run"] == (project_dir, Path("tests/testcases"), 0)
    assert calls["write"] == (project_dir / Path("docs/out.md"), "# report\n")

    output = capsys.readouterr().out
    assert "[baseline] total=21 passed=0 failed=21 output=docs/out.md" in output


def test_main_passes_diff_limit_to_runner(monkeypatch, tmp_path: Path):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            project_dir=project_dir,
            testcases_dir=Path("tests/testcases"),
            output=Path("docs/out.md"),
            show_diff_limit=5,
        ),
    )
    def _mock_run_batch_verify(project_dir: Path, testcases_dir: Path, show_diff_limit: int):
        captured["args"] = (project_dir, testcases_dir, show_diff_limit)
        return SimpleNamespace(total=1, passed=1, failed=0)

    monkeypatch.setattr(cli, "run_batch_verify", _mock_run_batch_verify)
    monkeypatch.setattr(cli, "render_report", lambda command, result, notes: "# r\n")
    monkeypatch.setattr(cli, "write_report", lambda path, report: None)

    cli.main()
    assert captured["args"] == (project_dir, Path("tests/testcases"), 5)
