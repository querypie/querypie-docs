#!/usr/bin/env python3
"""type-* 테스트케이스를 reverse-sync verify 단일파일 모드로 실행한다.

핵심:
- reverse_sync_cli.py의 `verify` 명령을 그대로 사용한다.
- 단, verify 단일파일 모드는 `src/content/ko/...` 경로를 요구하므로
  각 testcase의 original/improved를 임시 src/content/ko 경로로 복사해 실행한다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


def _project_root() -> Path:
    # .../confluence-mdx/bin/reverse_sync/report_typecase_failures.py -> confluence-mdx
    return Path(__file__).resolve().parents[2]


def _load_page_path_map(project_root: Path) -> Dict[str, List[str]]:
    pages_yaml = project_root / "var" / "pages.yaml"
    pages = yaml.safe_load(pages_yaml.read_text()) or []
    out: Dict[str, List[str]] = {}
    for p in pages:
        pid = str(p.get("page_id", ""))
        path = p.get("path")
        if pid and isinstance(path, list):
            out[pid] = path
    return out


def _extract_page_id_from_mdx(mdx_text: str) -> str | None:
    # confluenceUrl: .../pages/<id>/...
    m = re.search(r"/pages/(\d+)/", mdx_text)
    return m.group(1) if m else None


def _discover_cases(testcases_root: Path, only_case: str) -> List[Path]:
    all_cases = sorted(
        p for p in testcases_root.glob("type-*")
        if p.is_dir()
        and (p / "original.mdx").exists()
        and (p / "improved.mdx").exists()
        and (p / "page.xhtml").exists()
    )
    if only_case:
        all_cases = [p for p in all_cases if p.name == only_case]
    return all_cases


def _default_log_file(case: str) -> Path:
    ts = dt.datetime.now().strftime("%m%d%H%M")
    suffix = case if case else "all"
    return Path(f"reverse_sync_verify_typecases_{suffix}.{ts}.log")


def _prepare_temp_ko_files(
    case_dir: Path,
    ko_rel_path: str,
    tmp_root: Path,
) -> Tuple[Path, Path]:
    improved_dst = tmp_root / ko_rel_path
    original_dst = tmp_root / ("original_" + improved_dst.name)
    improved_dst.parent.mkdir(parents=True, exist_ok=True)
    improved_dst.write_text((case_dir / "improved.mdx").read_text())
    original_dst.write_text((case_dir / "original.mdx").read_text())
    return improved_dst, original_dst


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run reverse-sync verify for type-* testcases using single-file mode."
    )
    parser.add_argument(
        "--case",
        default="",
        help="Run only one testcase directory name (e.g. type-12-backtick-break)",
    )
    parser.add_argument(
        "--log-file",
        default="",
        help="Output log file path (default: auto-generated)",
    )
    args = parser.parse_args()

    root = _project_root()
    testcases_root = root / "tests" / "testcases"
    page_map = _load_page_path_map(root)
    cases = _discover_cases(testcases_root, args.case)
    if not cases:
        print("No matching type-* testcase found.", file=sys.stderr)
        return 1

    log_file = Path(args.log_file) if args.log_file else _default_log_file(args.case)
    all_output: List[str] = []
    exit_code = 0

    with tempfile.TemporaryDirectory(prefix="reverse-sync-typecase-verify-") as td:
        tmp_root = Path(td)
        for case_dir in cases:
            case_name = case_dir.name
            original_text = (case_dir / "original.mdx").read_text()
            page_id = _extract_page_id_from_mdx(original_text)
            if not page_id or page_id not in page_map:
                msg = f"[{case_name}] skip: page_id mapping not found"
                print(msg, file=sys.stderr)
                all_output.append(msg + "\n")
                exit_code = 1
                continue

            ko_rel = "src/content/ko/" + "/".join(page_map[page_id]) + ".mdx"
            improved_tmp, original_tmp = _prepare_temp_ko_files(case_dir, ko_rel, tmp_root)
            xhtml_path = case_dir / "page.xhtml"

            cmd = [
                sys.executable,
                str(root / "bin" / "reverse_sync_cli.py"),
                "verify",
                str(improved_tmp),
                "--original-mdx",
                str(original_tmp),
                "--xhtml",
                str(xhtml_path),
            ]

            header = f"\n=== {case_name} ===\n[cmd] {' '.join(cmd)}\n"
            print(header, end="")
            all_output.append(header)

            proc = subprocess.run(
                cmd,
                cwd=str(root),
                text=True,
                capture_output=True,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            print(out, end="")
            all_output.append(out)

            if proc.returncode != 0:
                exit_code = 1

    log_file.write_text("".join(all_output))
    print(f"\n[log] {log_file}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
