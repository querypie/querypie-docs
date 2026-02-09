"""Reverse Sync — MDX 변경사항을 Confluence XHTML에 역반영하는 파이프라인.

중간 파일은 var/<page_id>/ 에 reverse-sync. prefix로 저장된다.
"""
import argparse
import html as html_module
import json
import re
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
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_inner_xhtml


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


def _get_changed_ko_mdx_files(branch: str) -> List[str]:
    """브랜치에서 변경된 src/content/ko/**/*.mdx 파일 목록을 반환한다."""
    if not _is_valid_git_ref(branch):
        raise ValueError(f"Invalid git ref: {branch}")
    result = subprocess.run(
        ['git', 'diff', '--name-only', f'main...{branch}', '--', 'src/content/ko/'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"Failed to get changed files: {result.stderr.strip()}")
    files = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    return [f for f in files if f.startswith('src/content/ko/') and f.endswith('.mdx')]


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


def _resolve_attachment_dir(page_id: str) -> str:
    """page_id에서 pages.yaml의 path를 조회하여 attachment-dir를 반환."""
    pages = yaml.safe_load(Path('var/pages.yaml').read_text())
    for page in pages:
        if page['page_id'] == page_id:
            return '/' + '/'.join(page['path'])
    raise ValueError(f"page_id '{page_id}' not found in var/pages.yaml")


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
    attachment_dir = _resolve_attachment_dir(page_id)
    result = subprocess.run(
        [sys.executable, str(converter), '--log-level', 'warning',
         str(abs_input), str(abs_output),
         '--public-dir', str(var_dir.parent),
         '--attachment-dir', attachment_dir,
         '--skip-image-copy'],
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


_NON_CONTENT_TYPES = frozenset(('empty', 'frontmatter', 'import_statement'))


def _normalize_mdx_to_plain(content: str, block_type: str) -> str:
    """MDX 블록 content를 XHTML plain text와 대응하는 형태로 변환한다."""
    text = content.strip()

    if block_type == 'heading':
        return text.lstrip('#').strip()

    lines = text.split('\n')
    parts = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith('<figure') or s.startswith('<img') or s.startswith('</figure'):
            continue
        s = re.sub(r'^\d+\.\s+', '', s)
        s = re.sub(r'^[-*+]\s+', '', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'`([^`]+)`', r'\1', s)
        s = re.sub(r'<[^>]+/?>', '', s)
        s = html_module.unescape(s)
        s = s.strip()
        if s:
            parts.append(s)
    return ''.join(parts)


def _build_patches(
    changes: List[BlockChange],
    original_blocks: List[MdxBlock],
    improved_blocks: List[MdxBlock],
    mappings: List[BlockMapping],
) -> List[Dict[str, str]]:
    """diff 변경과 매핑을 인덱스 기반으로 결합하여 XHTML 패치 목록을 구성한다.

    MDX content 블록(empty/frontmatter/import 제외)과 XHTML 매핑은
    같은 문서를 순서대로 파싱한 결과이므로 순번이 1:1 대응된다.
    """
    # MDX 블록 index → XHTML mapping index
    content_idx = 0
    block_to_mapping: Dict[int, int] = {}
    for i, block in enumerate(original_blocks):
        if block.type not in _NON_CONTENT_TYPES:
            block_to_mapping[i] = content_idx
            content_idx += 1

    patches = []
    for change in changes:
        if change.old_block.type in _NON_CONTENT_TYPES:
            continue
        mapping_idx = block_to_mapping.get(change.index)
        if mapping_idx is not None and mapping_idx < len(mappings):
            mapping = mappings[mapping_idx]
            new_block = change.new_block
            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': mapping.xhtml_plain_text,
                'new_inner_xhtml': mdx_block_to_inner_xhtml(
                    new_block.content, new_block.type),
            })

    return patches


_USAGE_SUMMARY = """\
reverse-sync — MDX 변경사항을 Confluence XHTML에 역반영

Usage:
  reverse-sync verify <mdx> [--original-mdx <mdx>]
  reverse-sync verify --branch <branch>
  reverse-sync push   <mdx> [--original-mdx <mdx>] [--dry-run]
  reverse-sync push   --branch <branch> [--dry-run]
  reverse-sync -h | --help

Commands:
  push     verify 수행 후 Confluence에 반영 (--dry-run으로 검증만 가능)
  verify   push --dry-run의 alias

Arguments:
  <mdx>
    MDX 소스를 지정한다. 두 가지 형식을 사용할 수 있다:

    ref:path  git ref와 파일 경로를 콜론으로 구분
              예) main:src/content/ko/user-manual/user-agent.mdx
                  proofread/fix-typo:src/content/ko/overview.mdx
                  HEAD~1:src/content/ko/admin/audit.mdx

    path      로컬 파일 시스템 경로
              예) src/content/ko/user-manual/user-agent.mdx
                  /tmp/improved.mdx

    page-id는 경로의 src/content/ko/ 부분에서 var/pages.yaml을 통해
    자동 유도된다.

Options:
  --branch <branch>
    브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 배치 처리한다.
    <mdx>와 동시에 사용할 수 없다.

Examples:
  # 단일 파일 검증
  reverse-sync verify "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 검증
  reverse-sync verify --branch proofread/fix-typo

  # 검증 + Confluence 반영
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 push
  reverse-sync push --branch proofread/fix-typo

  # push --dry-run = verify
  reverse-sync push --dry-run "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

Run 'reverse-sync <command> -h' for command-specific help and more examples.
"""

_PUSH_HELP = """\
MDX 변경사항을 XHTML에 패치하고, round-trip 검증 후 Confluence에 반영한다.

파이프라인:
  1. original / improved MDX를 블록 단위로 파싱
  2. 블록 diff 추출
  3. 원본 XHTML 블록 매핑 생성
  4. XHTML 패치 적용
  5. 패치된 XHTML을 다시 MDX로 forward 변환 (round-trip)
  6. improved MDX와 비교하여 pass/fail 판정
  7. pass인 경우 Confluence API로 업데이트 (--dry-run 시 생략)

중간 산출물은 var/<page-id>/ 에 reverse-sync.* prefix로 저장된다.

MDX 소스 지정 방식:
  ref:path  git ref와 파일 경로를 콜론으로 구분
            예) main:src/content/ko/user-manual/user-agent.mdx
                proofread/fix-typo:src/content/ko/overview.mdx
  path      로컬 파일 시스템 경로
            예) /tmp/improved.mdx

  --branch <branch>
            브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 배치 처리한다.
            <mdx>, --original-mdx, --xhtml과 동시에 사용할 수 없다.

Examples:
  # 검증 + Confluence 반영
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 검증만 수행 (= verify)
  reverse-sync push --dry-run "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 검증
  reverse-sync verify --branch proofread/fix-typo

  # 브랜치 전체 배치 push
  reverse-sync push --branch proofread/fix-typo

  # original을 명시적으로 지정
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx" \\
    --original-mdx "main:src/content/ko/user-manual/user-agent.mdx"

  # 로컬 파일로 검증
  reverse-sync push --dry-run /tmp/improved.mdx \\
    --original-mdx /tmp/original.mdx \\
    --xhtml /tmp/page.xhtml
"""


def _add_common_args(parser: argparse.ArgumentParser):
    """verify/push 공통 인자를 등록한다."""
    parser.add_argument('improved_mdx', nargs='?',
                        help='개선 MDX (ref:path 또는 파일 경로)')
    parser.add_argument('--branch',
                        help='브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 처리')
    parser.add_argument('--original-mdx',
                        help='원본 MDX (ref:path 또는 파일 경로, 기본: main:<improved 경로>)')
    parser.add_argument('--xhtml', help='원본 XHTML 경로 (기본: var/<page-id>/page.xhtml)')


def _do_verify(args) -> dict:
    """공통 verify 로직: MDX 소스 해석 → run_verify() 실행 → 결과 반환."""
    improved_src = _resolve_mdx_source(args.improved_mdx)
    if args.original_mdx:
        original_src = _resolve_mdx_source(args.original_mdx)
    else:
        ko_path = _extract_ko_mdx_path(improved_src.descriptor)
        original_src = _resolve_mdx_source(f'main:{ko_path}')
    page_id = _resolve_page_id(_extract_ko_mdx_path(improved_src.descriptor))
    return run_verify(
        page_id=page_id,
        original_src=original_src,
        improved_src=improved_src,
        xhtml_path=args.xhtml,
    )


def _do_verify_batch(branch: str) -> List[dict]:
    """브랜치의 모든 변경 ko MDX 파일을 배치 verify 처리한다."""
    files = _get_changed_ko_mdx_files(branch)
    if not files:
        return [{'status': 'no_changes', 'branch': branch, 'changes_count': 0}]
    print(f"Processing {len(files)} file(s) from branch {branch}...", file=sys.stderr)
    results = []
    for idx, ko_path in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] {ko_path} ... ", end='', file=sys.stderr, flush=True)
        try:
            args = argparse.Namespace(
                improved_mdx=f"{branch}:{ko_path}",
                original_mdx=None, xhtml=None,
            )
            result = _do_verify(args)
            print(result.get('status', 'unknown'), file=sys.stderr)
            results.append(result)
        except Exception as e:
            print("error", file=sys.stderr)
            results.append({'file': ko_path, 'status': 'error', 'error': str(e)})
    return results


def _do_push(page_id: str):
    """verify 통과 후 Confluence에 push한다."""
    var_dir = Path(f'var/{page_id}')
    patched_path = var_dir / 'reverse-sync.patched.xhtml'
    xhtml_body = patched_path.read_text()

    from reverse_sync.confluence_client import ConfluenceConfig, get_page_version, update_page_body
    config = ConfluenceConfig()
    if not config.email or not config.api_token:
        print('Error: ~/.config/atlassian/confluence.conf 파일을 설정하세요. (형식: email:api_token)',
              file=sys.stderr)
        sys.exit(1)

    page_info = get_page_version(config, page_id)
    new_version = page_info['version'] + 1
    resp = update_page_body(config, page_id,
                            title=page_info['title'],
                            version=new_version,
                            xhtml_body=xhtml_body)
    return {
        'page_id': page_id,
        'title': resp.get('title', page_info['title']),
        'version': resp.get('version', {}).get('number', new_version),
        'url': resp.get('_links', {}).get('webui', ''),
    }


def main():
    # -h/--help 또는 인자 없음 → 사용법 출력 (argparse 자동 생성 우회)
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        print(_USAGE_SUMMARY, file=sys.stderr if len(sys.argv) < 2 else sys.stdout)
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    parser = argparse.ArgumentParser(prog='reverse-sync', add_help=False)
    subparsers = parser.add_subparsers(dest='command')

    # push (primary command)
    push_parser = subparsers.add_parser(
        'push', prog='reverse-sync push',
        description=_PUSH_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(push_parser)
    push_parser.add_argument('--dry-run', action='store_true',
                             help='검증만 수행, Confluence 반영 안 함 (= verify)')

    # verify (= push --dry-run alias)
    verify_parser = subparsers.add_parser(
        'verify', prog='reverse-sync verify',
        description=_PUSH_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(verify_parser)

    args = parser.parse_args()

    if args.command in ('verify', 'push'):
        dry_run = args.command == 'verify' or getattr(args, 'dry_run', False)

        try:
            # 인자 검증
            if not args.improved_mdx and not getattr(args, 'branch', None):
                print('Error: <mdx> 또는 --branch 중 하나를 지정하세요.', file=sys.stderr)
                sys.exit(1)
            if args.improved_mdx and getattr(args, 'branch', None):
                print('Error: <mdx>와 --branch는 동시에 사용할 수 없습니다.', file=sys.stderr)
                sys.exit(1)
            if getattr(args, 'branch', None) and (args.original_mdx or args.xhtml):
                print('Error: --branch와 --original-mdx/--xhtml는 동시에 사용할 수 없습니다.', file=sys.stderr)
                sys.exit(1)

            if getattr(args, 'branch', None):
                # 배치 모드
                results = _do_verify_batch(args.branch)
                print(json.dumps(results, ensure_ascii=False, indent=2))
                has_failure = any(r.get('status') not in ('pass', 'no_changes') for r in results)
                if not dry_run:
                    passed = [r for r in results if r.get('status') == 'pass']
                    if has_failure:
                        print(f"Error: 일부 파일이 검증에 실패했습니다. push하지 않습니다.", file=sys.stderr)
                        sys.exit(1)
                    for r in passed:
                        push_result = _do_push(r['page_id'])
                        print(json.dumps(push_result, ensure_ascii=False, indent=2))
                elif has_failure:
                    sys.exit(1)
            else:
                # 기존 단일 파일 모드
                result = _do_verify(args)
                print(json.dumps(result, ensure_ascii=False, indent=2))

                if not dry_run and result.get('status') == 'pass':
                    page_id = result['page_id']
                    push_result = _do_push(page_id)
                    print(json.dumps(push_result, ensure_ascii=False, indent=2))
                elif not dry_run and result.get('status') != 'pass':
                    print(f"Error: 검증 상태가 '{result.get('status')}'입니다. push하지 않습니다.",
                          file=sys.stderr)
                    sys.exit(1)
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
