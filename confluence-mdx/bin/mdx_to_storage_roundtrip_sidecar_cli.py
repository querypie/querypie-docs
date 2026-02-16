#!/usr/bin/env python3
"""Generate roundtrip sidecar files for lossless restore."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lossless_roundtrip.sidecar import build_sidecar, write_sidecar
from reverse_sync.mdx_to_storage_xhtml_verify import iter_testcase_dirs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate expected.roundtrip.json files")
    sub = parser.add_subparsers(dest="command", required=True)

    single = sub.add_parser("generate", help="Generate sidecar from single mdx/xhtml pair")
    single.add_argument("--mdx", type=Path, required=True, help="expected.mdx path")
    single.add_argument("--xhtml", type=Path, required=True, help="page.xhtml path")
    single.add_argument("--output", type=Path, required=True, help="output sidecar path")
    single.add_argument("--page-id", default="", help="page id for metadata")

    batch = sub.add_parser("batch-generate", help="Generate sidecars for testcase directories")
    batch.add_argument(
        "--testcases-dir",
        type=Path,
        default=Path("tests/testcases"),
        help="root dir containing testcase folders",
    )
    batch.add_argument(
        "--output-name",
        default="expected.roundtrip.json",
        help="sidecar filename per testcase",
    )
    return parser


def _run_generate(args: argparse.Namespace) -> int:
    if not args.mdx.exists() or not args.xhtml.exists():
        print("Error: --mdx and --xhtml must exist", file=sys.stderr)
        return 2

    mdx_text = args.mdx.read_text(encoding="utf-8")
    xhtml_text = args.xhtml.read_text(encoding="utf-8")
    sidecar = build_sidecar(mdx_text, xhtml_text, page_id=args.page_id)
    write_sidecar(sidecar, args.output)
    print(f"[sidecar] wrote: {args.output}")
    return 0


def _run_batch_generate(args: argparse.Namespace) -> int:
    if not args.testcases_dir.is_dir():
        print(f"Error: testcases dir not found: {args.testcases_dir}", file=sys.stderr)
        return 2

    case_dirs = list(iter_testcase_dirs(args.testcases_dir))
    if not case_dirs:
        print("No testcase directories containing page.xhtml + expected.mdx found.")
        return 0

    count = 0
    for case_dir in case_dirs:
        mdx_text = (case_dir / "expected.mdx").read_text(encoding="utf-8")
        xhtml_text = (case_dir / "page.xhtml").read_text(encoding="utf-8")
        output = case_dir / args.output_name
        sidecar = build_sidecar(mdx_text, xhtml_text, page_id=case_dir.name)
        write_sidecar(sidecar, output)
        count += 1

    print(f"[sidecar] generated {count} files (name={args.output_name})")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "generate":
        return _run_generate(args)
    if args.command == "batch-generate":
        return _run_batch_generate(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
