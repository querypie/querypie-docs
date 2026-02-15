#!/usr/bin/env python3
"""run-tests.sh용 thin wrapper — run_verify()를 page_id와 함께 직접 호출한다.

Usage:
    bin/reverse_sync/test_verify.py <page_id> <original_mdx> <improved_mdx> <xhtml>
    bin/reverse_sync/test_verify.py --format=cli <page_id> <original_mdx> <improved_mdx> <xhtml>

--format=cli 를 지정하면 reverse_sync_cli.py verify 와 동일한 형식으로 출력한다.
기본값은 JSON 출력.
"""
import json
import sys
from pathlib import Path

# 스크립트 위치 기반 경로 상수
_SCRIPT_DIR = Path(__file__).resolve().parent.parent  # confluence-mdx/bin/

# Ensure bin/ is on sys.path so local package imports resolve without PYTHONPATH
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from reverse_sync_cli import run_verify, MdxSource, _print_results


def main():
    args = sys.argv[1:]
    output_format = 'json'

    if args and args[0].startswith('--format='):
        output_format = args[0].split('=', 1)[1]
        args = args[1:]

    if len(args) != 4:
        print(f'Usage: {sys.argv[0]} [--format=json|cli] <page_id> <original_mdx> <improved_mdx> <xhtml>',
              file=sys.stderr)
        sys.exit(1)

    page_id, original_path, improved_path, xhtml_path = args

    original_src = MdxSource(
        content=open(original_path).read(),
        descriptor=original_path,
    )
    improved_src = MdxSource(
        content=open(improved_path).read(),
        descriptor=improved_path,
    )

    result = run_verify(
        page_id=page_id,
        original_src=original_src,
        improved_src=improved_src,
        xhtml_path=xhtml_path,
    )

    if output_format == 'cli':
        _print_results([result])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
