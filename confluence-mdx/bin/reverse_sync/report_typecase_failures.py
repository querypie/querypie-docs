#!/usr/bin/env python3
"""Typecase reverse-sync 결과를 한 번에 요약 출력한다.

Usage:
  python3 bin/reverse_sync/report_typecase_failures.py
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Dict, List

import yaml

# confluence-mdx/bin 을 import path에 추가
SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPT_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPT_DIR))

import reverse_sync_cli  # noqa: E402
from reverse_sync_cli import MdxSource, run_verify  # noqa: E402


def _project_root() -> Path:
    # .../confluence-mdx/bin/reverse_sync/report_typecase_failures.py -> confluence-mdx
    return Path(__file__).resolve().parents[2]


def _discover_typecases(testcases_root: Path) -> List[Path]:
    return sorted(
        p for p in testcases_root.glob("type-*")
        if p.is_dir()
        and (p / "original.mdx").exists()
        and (p / "improved.mdx").exists()
        and (p / "page.xhtml").exists()
    )


def _prepare_pages_yaml(var_dir: Path, case_ids: List[str]) -> None:
    pages = [{"page_id": cid, "path": ["types", cid]} for cid in case_ids]
    (var_dir / "pages.yaml").write_text(
        yaml.dump(pages, allow_unicode=True, default_flow_style=False)
    )


def _short_diff_line(diff_report: str) -> str:
    for line in diff_report.splitlines():
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith(("+", "-")):
            text = line[1:].strip()
            if text:
                return text[:100]
    return ""


def _format_cell(text: str, width: int) -> str:
    s = text.replace("\n", " ")
    if len(s) > width:
        s = s[: width - 1] + "…"
    return s.ljust(width)


def _print_summary(rows: List[Dict[str, str]]) -> None:
    headers = ["case", "status", "exact", "changes", "hint"]
    widths = [30, 8, 6, 8, 100]
    line = " | ".join(_format_cell(h, w) for h, w in zip(headers, widths))
    sep = "-+-".join("-" * w for w in widths)
    print(line)
    print(sep)
    for r in rows:
        print(" | ".join([
            _format_cell(r["case"], widths[0]),
            _format_cell(r["status"], widths[1]),
            _format_cell(r["exact"], widths[2]),
            _format_cell(str(r["changes"]), widths[3]),
            _format_cell(r["hint"], widths[4]),
        ]))


def _print_details(rows: List[Dict[str, str]], max_lines: int) -> None:
    print("\nDetailed diff excerpts")
    print("======================")
    for r in rows:
        if r["status"] != "fail":
            continue
        print(f"\n[{r['case']}]")
        lines = r["diff"].splitlines()
        shown = 0
        for line in lines:
            if line.startswith(("+++", "---")):
                continue
            print(line)
            shown += 1
            if shown >= max_lines:
                break
        if shown == 0:
            print("(no diff lines)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run reverse-sync typecases and print failure summary"
    )
    parser.add_argument(
        "--max-detail-lines",
        type=int,
        default=12,
        help="Max lines per failed case in detailed excerpt",
    )
    args = parser.parse_args()

    root = _project_root()
    testcases_root = root / "tests" / "testcases"
    typecases = _discover_typecases(testcases_root)
    if not typecases:
        raise SystemExit("No type-* testcases found under tests/testcases/")

    rows: List[Dict[str, str]] = []
    original_project_dir = reverse_sync_cli._PROJECT_DIR

    with tempfile.TemporaryDirectory(prefix="reverse-sync-typecases-") as tmp:
        tmp_root = Path(tmp) / "project"
        var_dir = tmp_root / "var"
        var_dir.mkdir(parents=True, exist_ok=True)
        _prepare_pages_yaml(var_dir, [p.name for p in typecases])

        reverse_sync_cli._PROJECT_DIR = tmp_root
        try:
            for case in typecases:
                case_id = case.name
                (var_dir / case_id).mkdir(parents=True, exist_ok=True)
                result = run_verify(
                    page_id=case_id,
                    original_src=MdxSource(
                        content=(case / "original.mdx").read_text(),
                        descriptor=f"tests/testcases/{case_id}/original.mdx",
                    ),
                    improved_src=MdxSource(
                        content=(case / "improved.mdx").read_text(),
                        descriptor=f"tests/testcases/{case_id}/improved.mdx",
                    ),
                    xhtml_path=str(case / "page.xhtml"),
                )
                diff = result.get("verification", {}).get("diff_report", "")
                exact = result.get("verification", {}).get("exact_match")
                rows.append({
                    "case": case_id,
                    "status": str(result.get("status")),
                    "exact": str(exact),
                    "changes": str(result.get("changes_count", "")),
                    "hint": _short_diff_line(diff),
                    "diff": diff,
                })
        finally:
            reverse_sync_cli._PROJECT_DIR = original_project_dir

    _print_summary(rows)
    _print_details(rows, args.max_detail_lines)

    fail_count = sum(1 for r in rows if r["status"] == "fail")
    pass_count = sum(1 for r in rows if r["status"] == "pass")
    print(
        f"\nTotal: {len(rows)} case(s) | fail={fail_count}, pass={pass_count}"
    )


if __name__ == "__main__":
    main()
