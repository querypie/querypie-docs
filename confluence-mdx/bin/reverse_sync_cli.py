#!/usr/bin/env python3
"""Reverse Sync — MDX 변경사항을 Confluence XHTML에 역반영하는 파이프라인.

중간 파일은 var/<page_id>/ 에 reverse-sync. prefix로 저장된다.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List

import yaml
# 스크립트 위치 기반 경로 상수
_SCRIPT_DIR = Path(__file__).resolve().parent   # confluence-mdx/bin/
_PROJECT_DIR = _SCRIPT_DIR.parent               # confluence-mdx/
_REPO_ROOT = _PROJECT_DIR.parent                # 레포 루트

# Ensure bin/ is on sys.path so local package imports resolve without PYTHONPATH
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from reverse_sync.batch_report import BatchReport
from reverse_sync.batch_service import BatchRuntime, run_batch
from reverse_sync.planner import plan_patches
from reverse_sync.equivalence import PUSH_EQUIVALENCE_POLICY
from reverse_sync.prepare_service import (
    PrepareRuntime,
    VerificationRequest,
    prepare_verification,
)
from reverse_sync.publish_service import (
    ManifestPushSummary,
    PublishRuntime,
    PushConflictError,
    load_manifest_push_summary,
    publish_verified_run,
)
from reverse_sync.verification_service import (
    MdxSource,
    VerificationRuntime,
    blocked_result as _blocked_result,
    clean_reverse_sync_artifacts,
    compile_result as _compile_result,
    extract_frontmatter_title as _extract_frontmatter_title,
    find_blockquotes_missing_blank_line as _find_blockquotes_missing_blank_line,
    parse_and_diff as _parse_and_diff,
    run_verification,
    save_diff_yaml as _save_diff_yaml,
    strip_frontmatter as _strip_frontmatter,
    validate_improved_mdx as _validate_improved_mdx,
)

_PUSH_VERIFIER_POLICY = PUSH_EQUIVALENCE_POLICY
_TOOL_VERSION = "reverse-sync-cli-v5"


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
        capture_output=True, text=True, cwd=str(_REPO_ROOT),
    )
    if result.returncode != 0:
        raise ValueError(f"Failed to get changed files: {result.stderr.strip()}")
    files = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    return [f for f in files if f.startswith('src/content/ko/') and f.endswith('.mdx')]


def _resolve_page_id(ko_mdx_path: str) -> str:
    """src/content/ko/...mdx 경로에서 pages.qm.yaml을 이용해 page_id를 유도한다."""
    rel = ko_mdx_path.removeprefix('src/content/ko/').removesuffix('.mdx')
    path_parts = rel.split('/')
    pages_path = _PROJECT_DIR / 'var' / 'pages.qm.yaml'
    if not pages_path.exists():
        raise ValueError("var/pages.qm.yaml not found")
    pages = yaml.safe_load(pages_path.read_text())
    for page in pages:
        if page.get('path') == path_parts:
            if page.get('type', 'page') == 'folder':
                raise ValueError(
                    f"MDX path '{ko_mdx_path}' is a generated Confluence folder "
                    "landing page and cannot be reverse-synced"
                )
            return page['page_id']
    raise ValueError(f"MDX path '{ko_mdx_path}' not found in var/pages.qm.yaml")


def _ensure_reverse_sync_page(page_id: str) -> None:
    """Reject generated folder landing pages even when --page-id is explicit."""
    pages_path = _PROJECT_DIR / 'var' / 'pages.qm.yaml'
    if not pages_path.exists():
        return
    pages = yaml.safe_load(pages_path.read_text()) or []
    for page in pages:
        if str(page.get('page_id')) != str(page_id):
            continue
        if page.get('type', 'page') == 'folder':
            raise ValueError(
                f"Content ID '{page_id}' is a generated Confluence folder "
                "landing page and cannot be reverse-synced"
            )
        return


def _resolve_attachment_dir(page_id: str) -> str:
    """page_id에서 pages.qm.yaml의 path를 조회하여 attachment-dir를 반환."""
    pages = yaml.safe_load((_PROJECT_DIR / 'var' / 'pages.qm.yaml').read_text())
    for page in pages:
        if page['page_id'] == page_id:
            return '/' + '/'.join(page['path'])
    raise ValueError(f"page_id '{page_id}' not found in var/pages.qm.yaml")


def _detect_language(descriptor: str) -> str:
    """descriptor에서 src/content/{lang}/ 의 언어 코드를 추출한다. 기본값: 'ko'."""
    path = descriptor.split(':', 1)[-1] if ':' in descriptor else descriptor
    prefix = 'src/content/'
    if prefix in path:
        idx = path.index(prefix) + len(prefix)
        lang = path[idx:].split('/')[0]
        if lang in ('ko', 'ja', 'en'):
            return lang
    return 'ko'


def _forward_convert(patched_xhtml_path: str, output_mdx_path: str, page_id: str,
                     language: str = 'ko', page_dir: str = None) -> str:
    """patched XHTML 파일을 forward converter로 MDX로 변환한다.

    모든 경로를 절대 경로로 변환하여 cwd에 의존하지 않도록 한다.
    page_dir이 주어지면 converter에 --page-dir로 전달하여 page.v1.yaml을 읽는다.
    """
    bin_dir = Path(__file__).parent
    converter = bin_dir / 'converter' / 'cli.py'
    var_dir = (_PROJECT_DIR / 'var' / page_id).resolve()

    abs_input = Path(patched_xhtml_path).resolve()
    abs_output = Path(output_mdx_path).resolve()
    attachment_dir = _resolve_attachment_dir(page_id)

    cmd = [sys.executable, str(converter), '--log-level', 'warning',
           str(abs_input), str(abs_output),
           '--public-dir', str(var_dir.parent),
           '--attachment-dir', attachment_dir,
           '--skip-image-copy',
           '--language', language]
    if page_dir:
        cmd += ['--page-dir', str(Path(page_dir).resolve())]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Forward converter failed: {result.stderr}")
    return abs_output.read_text()


def _clean_reverse_sync_artifacts(page_id: str) -> Path:
    """현재 CLI project root를 기준으로 이전 검증 산출물을 정리합니다."""

    return clean_reverse_sync_artifacts(_PROJECT_DIR, page_id)


def run_verify(
    page_id: str,
    original_src: MdxSource,
    improved_src: MdxSource,
    xhtml_path: str = None,
    lenient: bool = False,
    no_normalize: bool = False,
    language: str = None,
    page_dir: str = None,
    base_snapshot=None,
    attachment_catalog=None,
    for_push: bool = False,
) -> Dict[str, Any]:
    """CLI 환경을 주입하여 package verification lifecycle을 실행합니다."""

    runtime = VerificationRuntime(
        project_dir=_PROJECT_DIR,
        forward_convert=_forward_convert,
        detect_language=_detect_language,
        planner=plan_patches,
        verifier_policy=_PUSH_VERIFIER_POLICY,
        tool_version=_TOOL_VERSION,
    )
    return run_verification(
        page_id,
        original_src,
        improved_src,
        runtime=runtime,
        xhtml_path=xhtml_path,
        lenient=lenient,
        no_normalize=no_normalize,
        language=language,
        page_dir=page_dir,
        base_snapshot=base_snapshot,
        attachment_catalog=attachment_catalog,
        for_push=for_push,
    )


def _supports_color() -> bool:
    """stdout가 컬러 출력을 지원하는지 확인한다."""
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def _print_diff_block(lines: str, label: str, c, BOLD, CYAN, RED, GREEN, DIM) -> None:
    """컬러 diff 블록 하나를 출력한다."""
    print(c(DIM, '─' * 72))
    print(c(BOLD, f'  {label}'))
    for line in lines.splitlines():
        if line.startswith('---') or line.startswith('+++'):
            print(c(BOLD, line))
        elif line.startswith('@@'):
            print(c(CYAN, line))
        elif line.startswith('-'):
            print(c(RED, line))
        elif line.startswith('+'):
            print(c(GREEN, line))
        else:
            print(line)


def _display_status(result: Dict[str, Any]) -> str:
    """출력/요약용 상태를 계산하며 publish 상태를 local 결과보다 우선합니다."""
    push_status = (result.get('push') or {}).get('status')
    if push_status in ('remote_verified', 'already_applied'):
        return push_status
    if push_status == 'conflict':
        return 'push_conflict'
    if push_status == 'error':
        return 'push_error'
    if push_status == 'postcondition_failed':
        return 'push_postcondition_failed'
    if push_status == 'not_attempted':
        return 'push_not_attempted'
    return result.get('status', 'unknown')


def _is_success_status(status: str) -> bool:
    """offline diagnostic pass와 online verified_local을 성공으로 분류한다."""
    return status in (
        "already_applied",
        "no_changes",
        "pass",
        "remote_verified",
        "verified_local",
    )


def _display_error(result: Dict[str, Any], status: str) -> str:
    """출력용 에러 메시지를 반환한다."""
    if status in (
        'push_conflict',
        'push_error',
        'push_postcondition_failed',
        'push_not_attempted',
    ):
        push = result.get('push') or {}
        return push.get('error') or push.get('reason_code', '')
    return result.get('error', '')


def _print_results(results: List[Dict[str, Any]], *, show_all_diffs: bool = False,
                   failures_only: bool = False) -> None:
    """검증 결과를 컬러 diff 포맷으로 출력한다.

    show_all_diffs=True (debug 모드): MDX diff, XHTML diff, Verify diff 모두 출력.
    show_all_diffs=False (verify 모드): Verify diff만 출력 (FAIL 시).
    failures_only=True: pass/no_changes 결과를 출력에서 제외.
    """
    use_color = _supports_color()

    def c(code: str, text: str) -> str:
        return f'\033[{code}m{text}\033[0m' if use_color else text

    RED, GREEN, CYAN, YELLOW, BOLD, DIM = '31', '32', '36', '33', '1', '2'

    for r in results:
        status = _display_status(r)
        if failures_only and _is_success_status(status):
            continue
        file_path = r.get('file', r.get('page_id', '?'))
        changes = r.get('changes_count', 0)

        # 상태별 컬러 배지
        if status == 'remote_verified':
            badge = c(GREEN, 'REMOTE VERIFIED')
        elif status == 'already_applied':
            badge = c(GREEN, 'ALREADY APPLIED')
        elif status == 'verified_local':
            badge = c(GREEN, 'VERIFIED LOCAL')
        elif status == 'pass':
            badge = c(GREEN, 'PASS')
        elif status == 'no_changes':
            badge = c(DIM, 'NO CHANGES')
        elif status == 'push_conflict':
            badge = c(YELLOW, 'PUSH CONFLICT')
        elif status == 'push_error':
            badge = c(YELLOW, 'PUSH ERROR')
        elif status == 'push_postcondition_failed':
            badge = c(RED, 'POSTCONDITION FAILED')
        elif status == 'push_not_attempted':
            badge = c(YELLOW, 'NOT ATTEMPTED')
        elif status == 'error':
            badge = c(YELLOW, 'ERROR')
        elif status == 'blocked':
            badge = c(RED, 'BLOCKED')
        else:
            badge = c(RED, 'FAIL')

        print(f'\n{c(BOLD, file_path)}  {badge}  ({changes} change(s))')

        # 에러 메시지
        if status in (
            'error',
            'push_conflict',
            'push_error',
            'push_not_attempted',
            'push_postcondition_failed',
        ):
            print(f'  {c(RED, _display_error(r, status))}')
            if status == 'push_not_attempted' and r.get('manifest_path'):
                print(f'  resume manifest: {r["manifest_path"]}')
            continue
        if status == "blocked":
            reason_code = r.get("reason_code", "unknown")
            print(f'  {c(RED, f"reason: {reason_code}")}')

        if show_all_diffs:
            # MDX diff (original → improved)
            mdx_diff_report = r.get('mdx_diff_report', '')
            if mdx_diff_report:
                _print_diff_block(mdx_diff_report,
                                  'MDX diff (original → improved):',
                                  c, BOLD, CYAN, RED, GREEN, DIM)

            # XHTML diff (page.xhtml → patched.xhtml)
            xhtml_diff_report = r.get('xhtml_diff_report', '')
            if xhtml_diff_report:
                _print_diff_block(xhtml_diff_report,
                                  'XHTML diff (page.xhtml → patched.xhtml):',
                                  c, BOLD, CYAN, RED, GREEN, DIM)

            # Verify diff (improved.mdx → verify.mdx)
            diff_report = (r.get('verification') or {}).get('diff_report', '')
            if diff_report:
                _print_diff_block(diff_report,
                                  'Verify diff (improved.mdx → verify.mdx):',
                                  c, BOLD, CYAN, RED, GREEN, DIM)
        else:
            # verify 모드: FAIL 시에만 Verify diff 출력
            diff_report = (r.get('verification') or {}).get('diff_report', '')
            if diff_report:
                _print_diff_block(diff_report,
                                  'Verify diff (improved.mdx → verify.mdx):',
                                  c, BOLD, CYAN, RED, GREEN, DIM)

        # skipped_changes 출력
        skipped = r.get('skipped_changes', [])
        if skipped:
            print(c(DIM, '─' * 72))
            print(c(YELLOW, f'  Skipped changes ({len(skipped)}):'))
            for s in skipped:
                print(f'    [{s["reason"]}] {s["description"]}')

    # 요약
    total = len(results)
    display_statuses = [_display_status(r) for r in results]
    passed = sum(1 for status in display_statuses if status == 'pass')
    remote_verified = sum(
        1 for status in display_statuses if status == 'remote_verified'
    )
    already_applied = sum(
        1 for status in display_statuses if status == 'already_applied'
    )
    verified_local = sum(
        1 for status in display_statuses if status == 'verified_local'
    )
    failed = sum(1 for status in display_statuses if status == 'fail')
    errors = sum(1 for status in display_statuses if status == 'error')
    conflicts = sum(1 for status in display_statuses if status == 'push_conflict')
    push_errors = sum(1 for status in display_statuses if status == 'push_error')
    postcondition_failures = sum(
        1 for status in display_statuses if status == 'push_postcondition_failed'
    )
    not_attempted = sum(
        1 for status in display_statuses if status == 'push_not_attempted'
    )
    no_chg = sum(1 for status in display_statuses if status == 'no_changes')

    parts = []
    if passed:
        parts.append(c(GREEN, f'{passed} passed'))
    if remote_verified:
        parts.append(c(GREEN, f'{remote_verified} remote verified'))
    if already_applied:
        parts.append(c(GREEN, f'{already_applied} already applied'))
    if verified_local:
        parts.append(c(GREEN, f'{verified_local} verified local'))
    if failed:
        parts.append(c(RED, f'{failed} failed'))
    if errors:
        parts.append(c(YELLOW, f'{errors} errors'))
    if conflicts:
        parts.append(c(YELLOW, f'{conflicts} conflicts'))
    if push_errors:
        parts.append(c(YELLOW, f'{push_errors} push errors'))
    if postcondition_failures:
        parts.append(c(RED, f'{postcondition_failures} postcondition failures'))
    if not_attempted:
        parts.append(c(YELLOW, f'{not_attempted} not attempted'))
    if no_chg:
        parts.append(c(DIM, f'{no_chg} no changes'))

    print(f'\n{c(BOLD, "Summary:")} {", ".join(parts)} / {total} total')


_USAGE_SUMMARY = """\
reverse-sync — MDX 변경사항을 Confluence XHTML에 역반영

Usage:
  reverse-sync verify <mdx> [--original-mdx <mdx>] [--lenient] [--no-normalize]
  reverse-sync verify --branch <branch> [--lenient] [--no-normalize]
  reverse-sync debug  <mdx> [--original-mdx <mdx>] [--lenient] [--no-normalize]
  reverse-sync debug  --branch <branch> [--lenient] [--no-normalize]
  reverse-sync push   <mdx> [--original-mdx <mdx>] [--dry-run] [--yes] [--lenient] [--no-normalize]
  reverse-sync push   --branch <branch> [--dry-run] [--yes] [--lenient] [--no-normalize]
  reverse-sync push   --manifest <manifest.json> [--yes]
  reverse-sync -h | --help

Commands:
  push     원격 current snapshot을 기준으로 검증 후 Confluence에 반영
           (--dry-run은 manifest까지만 만들고 PUT을 생략)
           (--manifest는 이미 검증한 explicit run을 online verify 없이 발행)
  verify   로컬 page.xhtml 기반 진단 (push_eligible은 항상 false)
  debug    로컬 verify + MDX diff, XHTML diff, Verify diff 상세 출력

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

    page-id는 경로의 src/content/ko/ 부분에서 var/pages.qm.yaml을 통해
    자동 유도된다.

Options:
  --branch <branch>
    브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 배치 처리한다.
    <mdx>와 동시에 사용할 수 없다.

  --lenient
    관대 모드: trailing whitespace, 날짜 형식 등 XHTML↔MDX 변환기 한계에
    의한 차이를 기본 비교보다 더 넓게 정규화한다.
    진단 결과만 추가하며 online push eligibility에는 영향을 주지 않는다.

Examples:
  # 단일 파일 검증
  reverse-sync verify "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 검증
  reverse-sync verify --branch proofread/fix-typo

  # 검증 + Confluence 반영
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 push
  reverse-sync push --branch proofread/fix-typo

  # 원격 snapshot을 사용하되 PUT은 생략
  reverse-sync push --dry-run "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 이미 검증한 immutable manifest를 명시적으로 발행
  reverse-sync push --manifest \
    var/<page-id>/reverse-sync/<run-id>/manifest.json

Run 'reverse-sync <command> -h' for command-specific help and more examples.
"""

_PUSH_HELP = """\
MDX 변경사항을 검증한 Confluence snapshot에 패치하고, manifest로 결합한 뒤 반영한다.

파이프라인:
  1. version/title/Storage body를 단일 remote PageSnapshot으로 조회
  2. snapshot의 forward conversion과 original MDX base parity 검증
  3. original / improved MDX diff를 snapshot XHTML에 적용
  4. candidate XHTML round-trip과 dependency gate 검증
  5. snapshot/MDX/candidate hash를 immutable SyncManifest로 기록
  6. PUT 직전 remote snapshot과 manifest base를 다시 비교
  7. base version + 1로 한 번만 업데이트하고 persisted snapshot을 재검증

실행별 산출물은 var/<page-id>/reverse-sync/<run-id>/ 에 저장된다.
기존 reverse-sync.* 파일은 진단용 compatibility output이며 push payload가 아니다.

MDX 소스 지정 방식:
  ref:path  git ref와 파일 경로를 콜론으로 구분
            예) main:src/content/ko/user-manual/user-agent.mdx
                proofread/fix-typo:src/content/ko/overview.mdx
  path      로컬 파일 시스템 경로
            예) /tmp/improved.mdx

  --branch <branch>
            브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 배치 처리한다.
            <mdx>, --original-mdx, --page-id, --page-dir과 동시에 사용할 수 없다.

Examples:
  # 검증 + Confluence 반영
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 검증만 수행 (= verify)
  reverse-sync push --dry-run "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

  # 브랜치 전체 배치 검증
  reverse-sync verify --branch proofread/fix-typo

  # 브랜치 전체 배치 push
  reverse-sync push --branch proofread/fix-typo

  # 이전 online verify에서 생성한 explicit run을 발행
  reverse-sync push --manifest \\
    var/<page-id>/reverse-sync/<run-id>/manifest.json

  # original을 명시적으로 지정
  reverse-sync push "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx" \\
    --original-mdx "main:src/content/ko/user-manual/user-agent.mdx"

  # 로컬 MDX로 online prepare
  reverse-sync push --dry-run /tmp/improved.mdx \\
    --original-mdx /tmp/original.mdx \\
    --page-id <page-id>
"""


def _add_common_args(parser: argparse.ArgumentParser):
    """verify/push 공통 인자를 등록한다."""
    parser.add_argument('improved_mdx', nargs='?',
                        help='개선 MDX (ref:path 또는 파일 경로)')
    parser.add_argument('--branch',
                        help='브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 처리')
    parser.add_argument('--original-mdx',
                        help='원본 MDX (ref:path 또는 파일 경로, 기본: main:<improved 경로>)')
    parser.add_argument('--page-dir',
                        help='page.xhtml / page.v1.yaml 등 페이지 데이터 디렉토리 (var/<page-id>/를 대체)')
    parser.add_argument('--page-id',
                        help='page ID를 직접 지정 (기본: improved_mdx 경로에서 자동 유도)')
    parser.add_argument('--limit', type=int, default=0,
                        help='배치 모드에서 최대 처리 파일 수 (기본: 0=전체)')
    parser.add_argument('--failures-only', action='store_true',
                        help='실패한 결과만 출력 (--limit와 함께 사용 시 실패 건수 기준으로 제한)')
    parser.add_argument('--lenient', action='store_true',
                        help='관대 모드: 정규화 후 비교 (기본은 문자 그대로 비교하는 엄격 모드)')
    parser.add_argument('--no-normalize', action='store_true',
                        help='원시 모드: 정규화 없이 비교 (FC/패치 차이의 실제 규모를 확인)')


def _do_verify(args, *, config=None, prepare_push: bool = False) -> dict:
    """CLI 입력을 typed request로 변환하여 prepare lifecycle을 실행합니다."""

    explicit_page_id = getattr(args, "page_id", None)
    if explicit_page_id:
        _ensure_reverse_sync_page(explicit_page_id)

    request = VerificationRequest(
        improved_mdx=args.improved_mdx,
        original_mdx=getattr(args, "original_mdx", None),
        page_id=getattr(args, "page_id", None),
        page_dir=getattr(args, "page_dir", None),
        lenient=getattr(args, "lenient", False),
        no_normalize=getattr(args, "no_normalize", False),
    )
    runtime = PrepareRuntime(
        resolve_mdx_source=_resolve_mdx_source,
        extract_ko_mdx_path=_extract_ko_mdx_path,
        resolve_page_id=_resolve_page_id,
        ensure_config=_ensure_confluence_config,
        run_verification=run_verify,
    )
    return prepare_verification(
        request,
        runtime=runtime,
        config=config,
        prepare_push=prepare_push,
    )


def _confirm(prompt: str) -> bool:
    """터미널에서 y/N 확인을 받는다. 비대화형이면 False."""
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        print(file=sys.stderr)
        return False
    except KeyboardInterrupt:
        print(file=sys.stderr)
        raise
    return answer in ('y', 'yes')


def _emit_batch_progress(
    message: str,
    *,
    end: str = "\n",
    flush: bool = False,
) -> None:
    """batch service event를 CLI stderr에 표시합니다."""

    print(message, end=end, flush=flush, file=sys.stderr)


def _do_verify_batch(
    branch: str,
    limit: int = 0,
    failures_only: bool = False,
    push: bool = False,
    yes: bool = False,
    lenient: bool = False,
    no_normalize: bool = False,
    prepare_push: bool = False,
) -> List[dict]:
    """CLI dependency를 주입하여 branch batch lifecycle을 실행합니다."""

    runtime = BatchRuntime(
        get_changed_files=_get_changed_ko_mdx_files,
        verify_one=_do_verify,
        ensure_config=_ensure_confluence_config,
        publish_one=_do_push,
        confirm=_confirm,
        is_success_status=_is_success_status,
        emit=_emit_batch_progress,
    )
    return run_batch(
        branch,
        runtime=runtime,
        limit=limit,
        failures_only=failures_only,
        push=push,
        yes=yes,
        lenient=lenient,
        no_normalize=no_normalize,
        prepare_push=prepare_push,
    )


def _ensure_confluence_config():
    """Confluence 인증 설정을 확인하고 (config, ) 튜플을 반환한다."""
    from reverse_sync.confluence_client import ConfluenceConfig
    config = ConfluenceConfig()
    if not config.email or not config.api_token:
        print('Error: ~/.config/atlassian/confluence.conf 파일을 설정하세요. (형식: email:api_token)',
              file=sys.stderr)
        sys.exit(1)
    return config


def _load_manifest_push_summary(manifest_path: str) -> ManifestPushSummary:
    """explicit manifest의 발행 identity와 integrity를 검증합니다."""

    return load_manifest_push_summary(manifest_path)


def _do_push(page_id: str, config=None, *, manifest_path: str):
    """CLI 환경을 주입하여 immutable manifest publish lifecycle을 실행합니다."""

    if config is None:
        config = _ensure_confluence_config()
    runtime = PublishRuntime(
        project_dir=_PROJECT_DIR,
        forward_convert=_forward_convert,
        detect_language=_detect_language,
        load_manifest_summary=_load_manifest_push_summary,
    )
    return publish_verified_run(
        page_id,
        config,
        manifest_path=manifest_path,
        runtime=runtime,
    )


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
    push_parser.add_argument(
        '--manifest',
        help='online verify에서 생성한 explicit manifest.json을 발행',
    )
    push_parser.add_argument('--yes', '-y', action='store_true',
                             help='확인 프롬프트 없이 바로 push (CI/자동화용)')
    push_parser.add_argument('--json', action='store_true',
                             help='결과를 JSON 형식으로 출력')

    # verify (= push --dry-run alias)
    verify_parser = subparsers.add_parser(
        'verify', prog='reverse-sync verify',
        description=_PUSH_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(verify_parser)
    verify_parser.add_argument('--json', action='store_true',
                               help='결과를 JSON 형식으로 출력')

    # debug (= verify + 상세 diff 출력)
    debug_parser = subparsers.add_parser(
        'debug', prog='reverse-sync debug',
        description='verify와 동일하되 MDX diff, XHTML diff, Verify diff를 모두 출력한다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(debug_parser)
    debug_parser.add_argument('--json', action='store_true',
                              help='결과를 JSON 형식으로 출력')

    args = parser.parse_args()

    if args.command in ('verify', 'push', 'debug'):
        dry_run = args.command in ('verify', 'debug') or getattr(args, 'dry_run', False)
        show_all_diffs = args.command == 'debug'

        try:
            explicit_manifest = getattr(args, "manifest", None)
            if explicit_manifest:
                conflicting = (
                    args.improved_mdx
                    or getattr(args, "branch", None)
                    or args.original_mdx
                    or getattr(args, "page_dir", None)
                    or getattr(args, "page_id", None)
                    or getattr(args, "limit", 0)
                    or getattr(args, "failures_only", False)
                    or getattr(args, "lenient", False)
                    or getattr(args, "no_normalize", False)
                    or getattr(args, "dry_run", False)
                )
                if conflicting:
                    print(
                        "Error: --manifest는 MDX/branch/diagnostic 옵션과 "
                        "동시에 사용할 수 없습니다.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                auto_yes = getattr(args, "yes", False)
                if not auto_yes and not sys.stdin.isatty():
                    print(
                        "Error: 비대화형 환경에서는 --yes 옵션이 필요합니다.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                summary = _load_manifest_push_summary(explicit_manifest)
                if not auto_yes:
                    prompt = (
                        f"Push verified run {summary.run_id} "
                        f"{summary.title} ({summary.page_id}) "
                        f"v{summary.base_version}→v{summary.base_version + 1}, "
                        f"{summary.change_count} change(s), "
                        f"{summary.operation_count} operation(s), "
                        f"candidate {summary.candidate_sha256[:12]} "
                        "to Confluence? [y/N] "
                    )
                    if not _confirm(prompt):
                        print("Push 취소", file=sys.stderr)
                        sys.exit(0)
                config = _ensure_confluence_config()
                push_result = _do_push(
                    summary.page_id,
                    config=config,
                    manifest_path=str(summary.manifest_path),
                )
                print(json.dumps(push_result, ensure_ascii=False, indent=2))
                return

            # 인자 검증
            if not args.improved_mdx and not getattr(args, 'branch', None):
                print('Error: <mdx> 또는 --branch 중 하나를 지정하세요.', file=sys.stderr)
                sys.exit(1)
            if args.improved_mdx and getattr(args, 'branch', None):
                print('Error: <mdx>와 --branch는 동시에 사용할 수 없습니다.', file=sys.stderr)
                sys.exit(1)
            if getattr(args, 'branch', None) and args.original_mdx:
                print('Error: --branch와 --original-mdx는 동시에 사용할 수 없습니다.', file=sys.stderr)
                sys.exit(1)
            if getattr(args, 'branch', None) and (
                getattr(args, 'page_id', None)
                or getattr(args, 'page_dir', None)
            ):
                print(
                    'Error: --branch와 --page-id/--page-dir는 '
                    '동시에 사용할 수 없습니다.',
                    file=sys.stderr,
                )
                sys.exit(1)

            use_json = getattr(args, 'json', False)
            failures_only = getattr(args, 'failures_only', False)

            auto_yes = getattr(args, 'yes', False)

            if not dry_run and not auto_yes and not sys.stdin.isatty():
                print('Error: 비대화형 환경에서는 --yes 옵션이 필요합니다.', file=sys.stderr)
                sys.exit(1)

            if getattr(args, 'branch', None):
                # 배치 모드
                batch_kwargs = {
                    "limit": getattr(args, "limit", 0),
                    "failures_only": failures_only,
                    "push": not dry_run,
                    "yes": auto_yes,
                    "lenient": getattr(args, "lenient", False),
                    "no_normalize": getattr(args, "no_normalize", False),
                }
                if args.command == "push" and dry_run:
                    batch_kwargs["prepare_push"] = True
                results = _do_verify_batch(args.branch, **batch_kwargs)
                batch_report = BatchReport.from_results(
                    command=args.command,
                    branch=args.branch,
                    results=results,
                )
                if use_json:
                    print(
                        json.dumps(
                            batch_report.to_dict(
                                failures_only=failures_only,
                            ),
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                else:
                    _print_results(results, show_all_diffs=show_all_diffs,
                                   failures_only=failures_only)
                    print(
                        f"Batch outcome: {batch_report.outcome} "
                        f"(exit {batch_report.exit_code})"
                    )
                if batch_report.exit_code:
                    sys.exit(batch_report.exit_code)
            else:
                # 기존 단일 파일 모드
                config = _ensure_confluence_config() if args.command == 'push' else None
                result = _do_verify(
                    args,
                    config=config,
                    prepare_push=args.command == 'push',
                )
                if use_json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    _print_results([result], show_all_diffs=show_all_diffs)

                if (not dry_run
                        and result.get('status') == 'verified_local'
                        and result.get('push_eligible') is True):
                    page_id = result['page_id']
                    title = result.get('title', page_id)
                    if not auto_yes:
                        base_version = result.get("base_version", "?")
                        target_version = (
                            base_version + 1 if isinstance(base_version, int) else "?"
                        )
                        candidate_hash = result.get("candidate_sha256", "unknown")[:12]
                        changes_count = result.get("changes_count", 0)
                        prompt = (
                            f"Push {title} ({page_id}) "
                            f"v{base_version}→v{target_version}, "
                            f"{changes_count} change(s), "
                            f"candidate {candidate_hash} to Confluence? [y/N] "
                        )
                        if not _confirm(prompt):
                            print("Push 취소", file=sys.stderr)
                            sys.exit(0)
                    try:
                        push_result = _do_push(
                            page_id,
                            config=config,
                            manifest_path=result.get("manifest_path"),
                        )
                        print(json.dumps(push_result, ensure_ascii=False, indent=2))
                    except PushConflictError as e:
                        print(f"Error: {e}", file=sys.stderr)
                        sys.exit(1)
                    except Exception as e:
                        reason_code = getattr(e, "reason_code", "push_error")
                        print(f"Error [{reason_code}]: {e}", file=sys.stderr)
                        sys.exit(1)
                elif result.get('status') == 'no_changes':
                    if not dry_run:
                        print(
                            "변경 사항이 없어 Confluence update를 생략합니다.",
                            file=sys.stderr,
                        )
                elif (
                    args.command == "push"
                    and result.get('status') != 'verified_local'
                ):
                    print(f"Error: 검증 상태가 '{result.get('status')}'입니다. push하지 않습니다.",
                          file=sys.stderr)
                    sys.exit(1)
                elif (args.command == "push"
                      and result.get("status") == "verified_local"
                      and result.get("push_eligible") is not True):
                    print("Error: online verify 결과가 push eligible 상태가 아닙니다.",
                          file=sys.stderr)
                    sys.exit(1)
        except PushConflictError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            reason_code = getattr(e, "reason_code", "reverse_sync_error")
            print(f"Error [{reason_code}]: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
