"""mdx_to_storage_xhtml_byte_verify_cli.py 유닛 테스트."""

from pathlib import Path
from types import SimpleNamespace

import mdx_to_storage_xhtml_byte_verify_cli as cli


def test_main_returns_2_when_testcases_dir_missing(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=Path("/tmp/not-found"),
            case_id=None,
            sidecar_name="expected.roundtrip.json",
            show_fail_limit=10,
        ),
    )
    rc = cli.main()
    assert rc == 2
    assert "Error: testcases dir not found" in capsys.readouterr().err


def test_main_returns_0_when_all_pass(monkeypatch, tmp_path, capsys):
    case = tmp_path / "100"
    case.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id=None,
            sidecar_name="expected.roundtrip.json",
            show_fail_limit=10,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case])
    monkeypatch.setattr(
        cli,
        "verify_case_dir",
        lambda *args, **kwargs: SimpleNamespace(
            case_id="100",
            passed=True,
            reason="byte_equal",
            first_mismatch_offset=-1,
        ),
    )

    rc = cli.main()
    assert rc == 0
    assert "total=1 passed=1 failed=0" in capsys.readouterr().out


def test_main_returns_1_when_failures(monkeypatch, tmp_path, capsys):
    case1 = tmp_path / "100"
    case2 = tmp_path / "101"
    case1.mkdir()
    case2.mkdir()

    monkeypatch.setattr(
        cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            testcases_dir=tmp_path,
            case_id=None,
            sidecar_name="expected.roundtrip.json",
            show_fail_limit=1,
        ),
    )
    monkeypatch.setattr(cli, "iter_testcase_dirs", lambda _: [case1, case2])

    results = {
        "100": SimpleNamespace(
            case_id="100",
            passed=False,
            reason="byte_mismatch",
            first_mismatch_offset=123,
        ),
        "101": SimpleNamespace(
            case_id="101",
            passed=False,
            reason="sidecar_missing:expected.roundtrip.json",
            first_mismatch_offset=-1,
        ),
    }

    monkeypatch.setattr(cli, "verify_case_dir", lambda case_dir, sidecar_name=None: results[case_dir.name])

    rc = cli.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "total=2 passed=0 failed=2" in out
    assert "mismatch_offset=123" in out
