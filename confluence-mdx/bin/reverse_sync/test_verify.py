"""run-tests.sh용 thin wrapper — run_verify()를 page_id와 함께 직접 호출한다.

Usage:
    python3 -m reverse_sync.test_verify <page_id> <original_mdx_path> <improved_mdx_path> <xhtml_path>
"""
import json
import sys

from reverse_sync_cli import run_verify, MdxSource


def main():
    if len(sys.argv) != 5:
        print(f'Usage: {sys.argv[0]} <page_id> <original_mdx> <improved_mdx> <xhtml>',
              file=sys.stderr)
        sys.exit(1)

    page_id, original_path, improved_path, xhtml_path = sys.argv[1:5]

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
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
