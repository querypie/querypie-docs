"""Reverse Sync — MDX 변경사항을 Confluence XHTML에 역반영하는 파이프라인.

중간 파일은 var/<page_id>/rsync/ 하위에 저장된다.

Usage:
    python reverse_sync.py verify --page-id <id> --original-mdx <path> --improved-mdx <path>
    python reverse_sync.py push --page-id <id>
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import yaml
from mdx_block_parser import parse_mdx_blocks, MdxBlock
from block_diff import diff_blocks, BlockChange
from mapping_recorder import record_mapping, BlockMapping
from xhtml_patcher import patch_xhtml
from roundtrip_verifier import verify_roundtrip


def _forward_convert(patched_xhtml: str, output_mdx_path: str, page_id: str) -> str:
    """patched XHTML을 forward converter로 MDX로 변환한다.

    converter는 {input_dir}/page.v1.yaml 을 자동 로드하므로,
    var/<page_id>/ 에 임시 XHTML 파일을 작성하여 기존 메타데이터를 활용한다.
    모든 경로를 절대 경로로 변환하여 cwd에 의존하지 않도록 한다.
    """
    bin_dir = Path(__file__).parent
    converter = bin_dir / 'confluence_xhtml_to_markdown.py'
    var_dir = Path(f'var/{page_id}').resolve()

    tmp_input = var_dir / '_verify_input.xhtml'
    tmp_input.write_text(patched_xhtml)
    abs_output = Path(output_mdx_path).resolve()
    try:
        result = subprocess.run(
            [sys.executable, str(converter), '--log-level', 'warning',
             str(tmp_input), str(abs_output),
             '--public-dir', str(var_dir.parent),
             '--attachment-dir', f'/{page_id}/rsync'],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Forward converter failed: {result.stderr}")
        return abs_output.read_text()
    finally:
        tmp_input.unlink(missing_ok=True)


def _rsync_dir(page_id: str) -> Path:
    """var/<page_id>/rsync/ 경로를 반환하고, 디렉토리를 초기화한다."""
    d = Path(f'var/{page_id}/rsync')
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_verify(
    page_id: str,
    original_mdx_path: str,
    improved_mdx_path: str,
    xhtml_path: str = None,
) -> Dict[str, Any]:
    """로컬 검증 파이프라인을 실행한다.

    모든 중간 파일을 var/<page_id>/rsync/ 에 저장한다.
    """
    now = datetime.now(timezone.utc).isoformat()
    rsync = _rsync_dir(page_id)

    original_mdx = Path(original_mdx_path).read_text()
    improved_mdx = Path(improved_mdx_path).read_text()
    if not xhtml_path:
        xhtml_path = f'var/{page_id}/page.xhtml'
    xhtml = Path(xhtml_path).read_text()

    # Step 1: MDX 블록 파싱 + Step 2: 블록 Diff 추출
    original_blocks = parse_mdx_blocks(original_mdx)
    improved_blocks = parse_mdx_blocks(improved_mdx)
    changes = diff_blocks(original_blocks, improved_blocks)

    if not changes:
        result = {'page_id': page_id, 'created_at': now,
                  'status': 'no_changes', 'changes_count': 0}
        (rsync / 'result.yaml').write_text(
            yaml.dump(result, allow_unicode=True, default_flow_style=False))
        return result

    # diff.yaml 저장
    diff_data = {
        'page_id': page_id, 'created_at': now,
        'original_mdx': original_mdx_path, 'improved_mdx': improved_mdx_path,
        'changes': [
            {'index': c.index, 'block_id': f'{c.old_block.type}-{c.index}',
             'change_type': c.change_type,
             'old_content': c.old_block.content, 'new_content': c.new_block.content}
            for c in changes
        ],
    }
    (rsync / 'diff.yaml').write_text(
        yaml.dump(diff_data, allow_unicode=True, default_flow_style=False))

    # Step 3: 원본 매핑 생성 → mapping.original.yaml 저장
    original_mappings = record_mapping(xhtml)
    original_mapping_data = {
        'page_id': page_id, 'created_at': now, 'source_xhtml': 'page.xhtml',
        'blocks': [m.__dict__ for m in original_mappings],
    }
    (rsync / 'mapping.original.yaml').write_text(
        yaml.dump(original_mapping_data, allow_unicode=True, default_flow_style=False))

    # Step 4: XHTML 패치 → patched.xhtml 저장
    patches = _build_patches(changes, original_blocks, improved_blocks, original_mappings)
    patched_xhtml = patch_xhtml(xhtml, patches)
    (rsync / 'patched.xhtml').write_text(patched_xhtml)

    # Step 5: 검증 매핑 생성 → mapping.verify.yaml 저장
    verify_mappings = record_mapping(patched_xhtml)
    verify_mapping_data = {
        'page_id': page_id, 'created_at': now, 'source_xhtml': 'patched.xhtml',
        'blocks': [m.__dict__ for m in verify_mappings],
    }
    (rsync / 'mapping.verify.yaml').write_text(
        yaml.dump(verify_mapping_data, allow_unicode=True, default_flow_style=False))

    # Step 6: Forward 변환 → verify.mdx 저장
    verify_mdx_path = str(rsync / 'verify.mdx')
    verify_mdx = _forward_convert(patched_xhtml, verify_mdx_path, page_id)

    # Step 7: 완전 일치 검증 → result.yaml 저장
    verify_result = verify_roundtrip(expected_mdx=improved_mdx, actual_mdx=verify_mdx)
    status = 'pass' if verify_result.passed else 'fail'
    result = {
        'page_id': page_id, 'created_at': now,
        'status': status,
        'changes_count': len(changes),
        'verification': {
            'exact_match': verify_result.passed,
            'diff_report': verify_result.diff_report,
        },
    }
    (rsync / 'result.yaml').write_text(
        yaml.dump(result, allow_unicode=True, default_flow_style=False))

    return result


def _build_patches(
    changes: List[BlockChange],
    original_blocks: List[MdxBlock],
    improved_blocks: List[MdxBlock],
    mappings: List[BlockMapping],
) -> List[Dict[str, str]]:
    """diff 변경과 매핑을 결합하여 XHTML 패치 목록을 구성한다."""
    patches = []

    for change in changes:
        old_block = change.old_block
        if old_block.type in ('empty', 'frontmatter', 'import_statement'):
            continue

        old_plain = old_block.content.strip()
        if old_block.type == 'heading':
            old_plain = old_plain.lstrip('#').strip()

        for mapping in mappings:
            if mapping.xhtml_plain_text.strip() == old_plain:
                new_block = change.new_block
                new_plain = new_block.content.strip()
                if new_block.type == 'heading':
                    new_plain = new_plain.lstrip('#').strip()

                patches.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'old_plain_text': mapping.xhtml_plain_text,
                    'new_plain_text': new_plain,
                })
                break

    return patches


def main():
    parser = argparse.ArgumentParser(description='Reverse Sync: MDX → Confluence XHTML')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # verify
    verify_parser = subparsers.add_parser('verify', help='로컬 검증')
    verify_parser.add_argument('--page-id', required=True, help='Confluence page ID')
    verify_parser.add_argument('--original-mdx', required=True, help='원본 MDX 경로')
    verify_parser.add_argument('--improved-mdx', required=True, help='개선 MDX 경로')
    verify_parser.add_argument('--xhtml', help='원본 XHTML 경로 (기본: var/<page-id>/page.xhtml)')

    # push
    push_parser = subparsers.add_parser('push', help='Confluence 반영')
    push_parser.add_argument('--page-id', required=True, help='Confluence page ID')

    args = parser.parse_args()

    if args.command == 'verify':
        result = run_verify(
            page_id=args.page_id,
            original_mdx_path=args.original_mdx,
            improved_mdx_path=args.improved_mdx,
            xhtml_path=args.xhtml,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == 'push':
        rsync = Path(f'var/{args.page_id}/rsync')
        result_path = rsync / 'result.yaml'
        if not result_path.exists():
            print('Error: verify를 먼저 실행하세요.')
            sys.exit(1)
        result = yaml.safe_load(result_path.read_text())
        if result.get('status') != 'pass':
            print(f"Error: 검증 상태가 '{result.get('status')}'입니다. pass만 push 가능.")
            sys.exit(1)
        patched_path = rsync / 'patched.xhtml'
        print(f"Push {patched_path} to Confluence page {args.page_id} — not yet implemented")
        sys.exit(1)


if __name__ == '__main__':
    main()
