"""Reverse Sync — MDX 변경사항을 Confluence XHTML에 역반영하는 파이프라인.

중간 파일은 var/<page_id>/ 에 reverse-sync. prefix로 저장된다.

Usage:
    python reverse_sync_cli.py verify --improved-mdx <ref:path|path> [--original-mdx <ref:path|path>]
    python reverse_sync_cli.py push --mdx-path <src/content/ko/...mdx>
"""
import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import yaml
from reverse_sync.mdx_block_parser import parse_mdx_blocks, MdxBlock
from reverse_sync.block_diff import diff_blocks, BlockChange
from reverse_sync.mapping_recorder import record_mapping, BlockMapping
from reverse_sync.xhtml_patcher import patch_xhtml
from reverse_sync.roundtrip_verifier import verify_roundtrip


@dataclass
class MdxSource:
    """MDX 파일의 내용과 출처 정보."""
    content: str        # MDX 파일 내용
    descriptor: str     # 출처 표시 (예: "main:src/content/ko/...", 파일 경로 등)


def _is_valid_git_ref(ref: str) -> bool:
    """ref가 유효한 git ref인지 확인한다."""
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', ref],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def _get_file_from_git(ref: str, path: str) -> str:
    """git show <ref>:<path>로 파일 내용을 반환한다."""
    result = subprocess.run(
        ['git', 'show', f'{ref}:{path}'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"Failed to get {path} at ref {ref}: {result.stderr.strip()}")
    return result.stdout


def _resolve_mdx_source(arg: str) -> MdxSource:
    """2-tier MDX 소스 해석: ref:path → 파일 경로."""
    # 1. ref:path 형식
    if ':' in arg:
        ref, path = arg.split(':', 1)
        if _is_valid_git_ref(ref):
            content = _get_file_from_git(ref, path)
            return MdxSource(content=content, descriptor=f'{ref}:{path}')

    # 2. 파일 경로
    if Path(arg).is_file():
        return MdxSource(content=Path(arg).read_text(), descriptor=arg)

    raise ValueError(f"Cannot resolve MDX source '{arg}': not a file path or ref:path")


def _extract_ko_mdx_path(descriptor: str) -> str:
    """descriptor에서 src/content/ko/...mdx 경로를 추출한다."""
    path = descriptor.split(':', 1)[-1] if ':' in descriptor else descriptor
    prefix = 'src/content/ko/'
    if prefix in path and path.endswith('.mdx'):
        idx = path.index(prefix)
        return path[idx:]
    raise ValueError(f"Cannot extract ko MDX path from '{descriptor}'")


def _resolve_page_id(ko_mdx_path: str) -> str:
    """src/content/ko/...mdx 경로에서 pages.yaml을 이용해 page_id를 유도한다."""
    rel = ko_mdx_path.removeprefix('src/content/ko/').removesuffix('.mdx')
    path_parts = rel.split('/')
    pages_path = Path('var/pages.yaml')
    if not pages_path.exists():
        raise ValueError("var/pages.yaml not found")
    pages = yaml.safe_load(pages_path.read_text())
    for page in pages:
        if page.get('path') == path_parts:
            return page['page_id']
    raise ValueError(f"MDX path '{ko_mdx_path}' not found in var/pages.yaml")


def _forward_convert(patched_xhtml_path: str, output_mdx_path: str, page_id: str) -> str:
    """patched XHTML 파일을 forward converter로 MDX로 변환한다.

    입력 파일이 var/<page_id>/ 에 직접 있으므로 메타데이터를 자동 발견한다.
    모든 경로를 절대 경로로 변환하여 cwd에 의존하지 않도록 한다.
    """
    bin_dir = Path(__file__).parent
    converter = bin_dir / 'confluence_xhtml_to_markdown.py'
    var_dir = Path(f'var/{page_id}').resolve()

    abs_input = Path(patched_xhtml_path).resolve()
    abs_output = Path(output_mdx_path).resolve()
    result = subprocess.run(
        [sys.executable, str(converter), '--log-level', 'warning',
         str(abs_input), str(abs_output),
         '--public-dir', str(var_dir.parent),
         '--attachment-dir', f'/{page_id}/verify'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Forward converter failed: {result.stderr}")
    return abs_output.read_text()


def _clean_reverse_sync_artifacts(page_id: str) -> Path:
    """var/<page_id>/ 내의 이전 reverse-sync 산출물을 정리하고 var_dir을 반환한다."""
    var_dir = Path(f'var/{page_id}')
    for f in var_dir.glob('reverse-sync.*'):
        f.unlink()
    verify_mdx = var_dir / 'verify.mdx'
    if verify_mdx.exists():
        verify_mdx.unlink()
    verify_dir = var_dir / 'verify'
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    return var_dir


def run_verify(
    page_id: str,
    original_src: MdxSource,
    improved_src: MdxSource,
    xhtml_path: str = None,
) -> Dict[str, Any]:
    """로컬 검증 파이프라인을 실행한다.

    모든 중간 파일을 var/<page_id>/ 에 reverse-sync. prefix로 저장한다.
    """
    now = datetime.now(timezone.utc).isoformat()
    var_dir = _clean_reverse_sync_artifacts(page_id)

    original_mdx = original_src.content
    improved_mdx = improved_src.content
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
        (var_dir / 'reverse-sync.result.yaml').write_text(
            yaml.dump(result, allow_unicode=True, default_flow_style=False))
        return result

    # diff.yaml 저장
    diff_data = {
        'page_id': page_id, 'created_at': now,
        'original_mdx': original_src.descriptor, 'improved_mdx': improved_src.descriptor,
        'changes': [
            {'index': c.index, 'block_id': f'{c.old_block.type}-{c.index}',
             'change_type': c.change_type,
             'old_content': c.old_block.content, 'new_content': c.new_block.content}
            for c in changes
        ],
    }
    (var_dir / 'reverse-sync.diff.yaml').write_text(
        yaml.dump(diff_data, allow_unicode=True, default_flow_style=False))

    # Step 3: 원본 매핑 생성 → mapping.original.yaml 저장
    original_mappings = record_mapping(xhtml)
    original_mapping_data = {
        'page_id': page_id, 'created_at': now, 'source_xhtml': 'page.xhtml',
        'blocks': [m.__dict__ for m in original_mappings],
    }
    (var_dir / 'reverse-sync.mapping.original.yaml').write_text(
        yaml.dump(original_mapping_data, allow_unicode=True, default_flow_style=False))

    # Step 4: XHTML 패치 → patched.xhtml 저장
    patches = _build_patches(changes, original_blocks, improved_blocks, original_mappings)
    patched_xhtml = patch_xhtml(xhtml, patches)
    (var_dir / 'reverse-sync.patched.xhtml').write_text(patched_xhtml)

    # Step 5: 검증 매핑 생성 → mapping.patched.yaml 저장
    verify_mappings = record_mapping(patched_xhtml)
    verify_mapping_data = {
        'page_id': page_id, 'created_at': now, 'source_xhtml': 'patched.xhtml',
        'blocks': [m.__dict__ for m in verify_mappings],
    }
    (var_dir / 'reverse-sync.mapping.patched.yaml').write_text(
        yaml.dump(verify_mapping_data, allow_unicode=True, default_flow_style=False))

    # Step 6: Forward 변환 → verify.mdx 저장
    _forward_convert(
        str(var_dir / 'reverse-sync.patched.xhtml'),
        str(var_dir / 'verify.mdx'),
        page_id,
    )
    verify_mdx = (var_dir / 'verify.mdx').read_text()

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
    (var_dir / 'reverse-sync.result.yaml').write_text(
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
    verify_parser.add_argument('--improved-mdx', required=True,
                               help='개선 MDX (ref:path 또는 파일 경로)')
    verify_parser.add_argument('--original-mdx',
                               help='원본 MDX (ref:path 또는 파일 경로, 기본: main:<improved 경로>)')
    verify_parser.add_argument('--xhtml', help='원본 XHTML 경로 (기본: var/<page-id>/page.xhtml)')

    # push
    push_parser = subparsers.add_parser('push', help='Confluence 반영')
    push_parser.add_argument('--mdx-path', required=True,
                             help='ko MDX 경로 (예: src/content/ko/user-manual/user-agent.mdx)')

    args = parser.parse_args()

    if args.command == 'verify':
        try:
            improved_src = _resolve_mdx_source(args.improved_mdx)
            if args.original_mdx:
                original_src = _resolve_mdx_source(args.original_mdx)
            else:
                ko_path = _extract_ko_mdx_path(improved_src.descriptor)
                original_src = _resolve_mdx_source(f'main:{ko_path}')
            page_id = _resolve_page_id(_extract_ko_mdx_path(improved_src.descriptor))
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)
        result = run_verify(
            page_id=page_id,
            original_src=original_src,
            improved_src=improved_src,
            xhtml_path=args.xhtml,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == 'push':
        try:
            page_id = _resolve_page_id(args.mdx_path)
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)

        var_dir = Path(f'var/{page_id}')
        result_path = var_dir / 'reverse-sync.result.yaml'
        if not result_path.exists():
            print('Error: verify를 먼저 실행하세요.')
            sys.exit(1)
        result = yaml.safe_load(result_path.read_text())
        if result.get('status') != 'pass':
            print(f"Error: 검증 상태가 '{result.get('status')}'입니다. pass만 push 가능.")
            sys.exit(1)

        patched_path = var_dir / 'reverse-sync.patched.xhtml'
        xhtml_body = patched_path.read_text()

        from reverse_sync.confluence_client import ConfluenceConfig, get_page_version, update_page_body
        config = ConfluenceConfig()
        if not config.email or not config.api_token:
            print('Error: ~/.config/atlassian/confluence.conf 파일을 설정하세요. (형식: email:api_token)')
            sys.exit(1)

        # 최신 버전 조회
        page_info = get_page_version(config, page_id)
        new_version = page_info['version'] + 1

        # 업데이트
        resp = update_page_body(config, page_id,
                                title=page_info['title'],
                                version=new_version,
                                xhtml_body=xhtml_body)
        print(json.dumps({
            'page_id': page_id,
            'title': resp.get('title', page_info['title']),
            'version': resp.get('version', {}).get('number', new_version),
            'url': resp.get('_links', {}).get('webui', ''),
        }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
