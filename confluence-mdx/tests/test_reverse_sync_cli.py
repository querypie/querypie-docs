import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from reverse_sync_cli import (
    run_verify, main, MdxSource, _resolve_mdx_source,
    _extract_ko_mdx_path, _resolve_page_id, _do_verify, _do_push,
    _get_changed_ko_mdx_files, _do_verify_batch, _strip_frontmatter,
    _parse_and_diff, _save_diff_yaml, _compile_result, _print_results,
    _USAGE_SUMMARY,
    _detect_language, _validate_improved_mdx,
    _find_blockquotes_missing_blank_line,
    PushConflictError, _confirm,
)
from text_utils import normalize_mdx_to_plain
from reverse_sync.patch_builder import build_patches


@pytest.fixture
def setup_var(tmp_path, monkeypatch):
    """var/<page_id>/ 구조를 tmp_path에 생성하고 _PROJECT_DIR을 패치."""
    monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)
    page_id = "test-page-001"
    var_dir = tmp_path / "var" / page_id
    var_dir.mkdir(parents=True)
    # 간단한 XHTML 원본
    (var_dir / "page.xhtml").write_text("<h2>Title</h2><p>Paragraph.</p>")
    return page_id, var_dir


def test_verify_no_changes(setup_var, tmp_path):
    """변경 없으면 no_changes, rsync/result.yaml 생성."""
    page_id, var_dir = setup_var
    mdx_content = "## Title\n\nParagraph.\n"

    result = run_verify(
        page_id=page_id,
        original_src=MdxSource(content=mdx_content, descriptor="original.mdx"),
        improved_src=MdxSource(content=mdx_content, descriptor="improved.mdx"),
    )
    assert result['status'] == 'no_changes'
    assert (var_dir / "reverse-sync.result.yaml").exists()


def test_verify_detects_changes(setup_var, tmp_path):
    """텍스트 변경 감지 + forward 변환 mock으로 roundtrip 검증."""
    page_id, var_dir = setup_var

    # forward converter를 mock: verify.mdx에 improved_mdx 내용을 그대로 써서 pass 유도
    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id, **kwargs):
        Path(output_mdx_path).write_text("## Title\n\nModified.\n")
        return "## Title\n\nModified.\n"

    with patch('reverse_sync_cli._forward_convert', side_effect=mock_forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(content="## Title\n\nParagraph.\n", descriptor="original.mdx"),
            improved_src=MdxSource(content="## Title\n\nModified.\n", descriptor="improved.mdx"),
        )
    assert result['changes_count'] == 1
    assert result['status'] == 'pass'
    assert result['verification']['exact_match'] is True
    assert (var_dir / "reverse-sync.diff.yaml").exists()
    assert (var_dir / "reverse-sync.mapping.original.yaml").exists()
    assert (var_dir / "reverse-sync.mapping.patched.yaml").exists()
    assert (var_dir / "reverse-sync.patched.xhtml").exists()
    assert (var_dir / "verify.mdx").exists()
    assert (var_dir / "reverse-sync.result.yaml").exists()


def test_verify_roundtrip_fail(setup_var):
    """forward 변환 결과가 다르면 status=fail."""
    page_id, var_dir = setup_var

    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id, **kwargs):
        # 다른 내용을 반환하여 roundtrip 실패 유도
        content = "## Title\n\nDifferent output.\n"
        Path(output_mdx_path).write_text(content)
        return content

    with patch('reverse_sync_cli._forward_convert', side_effect=mock_forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(content="## Title\n\nParagraph.\n", descriptor="original.mdx"),
            improved_src=MdxSource(content="## Title\n\nModified.\n", descriptor="improved.mdx"),
        )
    assert result['status'] == 'fail'
    assert result['verification']['exact_match'] is False
    assert result['verification']['diff_report'] != ''


# --- push command tests ---


def test_push_verify_fail_exits(monkeypatch):
    """push 시 verify가 fail이면 exit 1."""
    mdx_arg = 'src/content/ko/test/page.mdx'
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', mdx_arg])
    fail_result = {'status': 'fail', 'page_id': 'test-page-001'}
    with patch('reverse_sync_cli._do_verify', return_value=fail_result), \
         patch('builtins.print'):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


def test_push_verify_pass_then_pushes(tmp_path, monkeypatch):
    """push --yes 시 verify pass → _do_push 호출."""
    page_id = 'test-page-001'
    mdx_arg = 'src/content/ko/test/page.mdx'
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--yes', '--json', mdx_arg])
    monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)

    # var 디렉토리에 patched xhtml 준비
    var_dir = tmp_path / 'var' / page_id
    var_dir.mkdir(parents=True)
    (var_dir / 'reverse-sync.patched.xhtml').write_text('<p>Updated</p>')

    pass_result = {'status': 'pass', 'page_id': page_id, 'changes_count': 1}

    mock_get_version = MagicMock(return_value={'version': 5, 'title': 'Test'})
    mock_get_body = MagicMock(return_value='<p>Original</p>')
    mock_update = MagicMock(return_value={
        'title': 'Test', 'version': {'number': 6},
        '_links': {'webui': '/test'},
    })

    with patch('reverse_sync_cli._do_verify', return_value=pass_result), \
         patch('reverse_sync.confluence_client._load_credentials',
               return_value=('e@x.com', 'tok')), \
         patch('reverse_sync.confluence_client.get_page_version', mock_get_version), \
         patch('reverse_sync.confluence_client.get_page_body', mock_get_body), \
         patch('reverse_sync.confluence_client.update_page_body', mock_update), \
         patch('builtins.print') as mock_print:
        main()

    # push API 호출 확인
    mock_update.assert_called_once()
    call_args = mock_update.call_args
    assert call_args[0][1] == page_id
    assert call_args[1]['xhtml_body'] == '<p>Updated</p>'

    # 백업 파일 생성 확인
    backup_path = var_dir / 'reverse-sync.backup.xhtml'
    assert backup_path.exists()
    assert backup_path.read_text() == '<p>Original</p>'

    # 출력 확인: verify 결과 + push 결과 2번 출력
    assert mock_print.call_count == 2
    push_output = json.loads(mock_print.call_args_list[1][0][0])
    assert push_output['page_id'] == page_id
    assert push_output['version'] == 6


def test_push_dry_run_skips_push(monkeypatch):
    """push --dry-run은 verify만 수행하고 push하지 않는다."""
    mdx_arg = 'src/content/ko/test/page.mdx'
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--dry-run', mdx_arg])
    pass_result = {'status': 'pass', 'page_id': 'test-page-001', 'changes_count': 1}

    with patch('reverse_sync_cli._do_verify', return_value=pass_result) as mock_verify, \
         patch('reverse_sync_cli._do_push') as mock_push, \
         patch('builtins.print'):
        main()

    mock_verify.assert_called_once()
    mock_push.assert_not_called()


def test_verify_is_dry_run_alias(monkeypatch):
    """verify 커맨드는 push --dry-run과 동일하게 동작한다."""
    mdx_arg = 'src/content/ko/test/page.mdx'
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'verify', mdx_arg])
    pass_result = {'status': 'pass', 'page_id': 'test-page-001', 'changes_count': 1}

    with patch('reverse_sync_cli._do_verify', return_value=pass_result) as mock_verify, \
         patch('reverse_sync_cli._do_push') as mock_push, \
         patch('builtins.print'):
        main()

    mock_verify.assert_called_once()
    mock_push.assert_not_called()


# --- _resolve_mdx_source tests ---


def test_resolve_mdx_source_file_path(tmp_path):
    """파일 경로로 MdxSource를 생성한다."""
    mdx_file = tmp_path / "test.mdx"
    mdx_file.write_text("## Hello\n")
    src = _resolve_mdx_source(str(mdx_file))
    assert src.content == "## Hello\n"
    assert src.descriptor == str(mdx_file)


def test_resolve_mdx_source_ref_path():
    """ref:path 형식으로 MdxSource를 생성한다."""
    with patch('reverse_sync_cli._is_valid_git_ref', return_value=True), \
         patch('reverse_sync_cli._get_file_from_git', return_value="## From Git\n"):
        src = _resolve_mdx_source("main:src/content/ko/test.mdx")
    assert src.content == "## From Git\n"
    assert src.descriptor == "main:src/content/ko/test.mdx"


def test_resolve_mdx_source_invalid():
    """유효하지 않은 인자는 ValueError를 발생시킨다."""
    with patch('reverse_sync_cli._is_valid_git_ref', return_value=False), \
         patch('pathlib.Path.is_file', return_value=False):
        with pytest.raises(ValueError, match="Cannot resolve MDX source"):
            _resolve_mdx_source("nonexistent")


# --- _extract_ko_mdx_path tests ---


def test_extract_ko_mdx_path_from_ref_path():
    """ref:path descriptor에서 ko MDX 경로를 추출한다."""
    result = _extract_ko_mdx_path("main:src/content/ko/user-manual/user-agent.mdx")
    assert result == "src/content/ko/user-manual/user-agent.mdx"


def test_extract_ko_mdx_path_from_file_path():
    """파일 경로 descriptor에서 ko MDX 경로를 추출한다."""
    result = _extract_ko_mdx_path("src/content/ko/user-manual/user-agent.mdx")
    assert result == "src/content/ko/user-manual/user-agent.mdx"


def test_extract_ko_mdx_path_invalid():
    """ko MDX 경로가 없으면 ValueError를 발생시킨다."""
    with pytest.raises(ValueError, match="Cannot extract ko MDX path"):
        _extract_ko_mdx_path("some/other/path.txt")


# --- _resolve_page_id tests ---


def test_resolve_page_id(tmp_path, monkeypatch):
    """pages.qm.yaml에서 MDX 경로로 page_id를 유도한다."""
    import yaml
    monkeypatch.chdir(tmp_path)
    var_dir = tmp_path / "var"
    var_dir.mkdir()
    pages = [
        {'page_id': '544112828', 'path': ['user-manual', 'user-agent']},
        {'page_id': '123456789', 'path': ['overview']},
    ]
    (var_dir / 'pages.qm.yaml').write_text(yaml.dump(pages))

    result = _resolve_page_id('src/content/ko/user-manual/user-agent.mdx')
    assert result == '544112828'


def test_resolve_page_id_not_found(tmp_path, monkeypatch):
    """pages.qm.yaml에 없는 경로이면 ValueError를 발생시킨다."""
    import yaml
    monkeypatch.chdir(tmp_path)
    var_dir = tmp_path / "var"
    var_dir.mkdir()
    pages = [{'page_id': '111', 'path': ['other']}]
    (var_dir / 'pages.qm.yaml').write_text(yaml.dump(pages))

    with pytest.raises(ValueError, match="not found in var/pages.qm.yaml"):
        _resolve_page_id('src/content/ko/nonexistent/page.mdx')


# --- _get_changed_ko_mdx_files tests ---


def test_get_changed_ko_mdx_files():
    """git diff mock → 변경된 ko MDX 파일 목록을 반환한다."""
    git_output = (
        "src/content/ko/user-manual/user-agent.mdx\n"
        "src/content/ko/overview.mdx\n"
        "src/content/ko/admin/audit.mdx\n"
    )
    mock_diff = MagicMock(returncode=0, stdout=git_output, stderr='')
    with patch('reverse_sync_cli._is_valid_git_ref', return_value=True), \
         patch('reverse_sync_cli.subprocess.run', return_value=mock_diff):
        files = _get_changed_ko_mdx_files('proofread/fix-typo')
    assert files == [
        'src/content/ko/user-manual/user-agent.mdx',
        'src/content/ko/overview.mdx',
        'src/content/ko/admin/audit.mdx',
    ]


def test_get_changed_ko_mdx_files_filters_non_mdx():
    """MDX가 아닌 파일은 필터링된다."""
    git_output = (
        "src/content/ko/overview.mdx\n"
        "src/content/ko/images/logo.png\n"
        "src/content/en/other.mdx\n"
    )
    mock_diff = MagicMock(returncode=0, stdout=git_output, stderr='')
    with patch('reverse_sync_cli._is_valid_git_ref', return_value=True), \
         patch('reverse_sync_cli.subprocess.run', return_value=mock_diff):
        files = _get_changed_ko_mdx_files('proofread/fix-typo')
    assert files == ['src/content/ko/overview.mdx']


def test_get_changed_ko_mdx_files_invalid_ref():
    """잘못된 git ref → ValueError."""
    with patch('reverse_sync_cli._is_valid_git_ref', return_value=False):
        with pytest.raises(ValueError, match="Invalid git ref"):
            _get_changed_ko_mdx_files('nonexistent-branch')


# --- _do_verify_batch tests ---


def test_do_verify_batch_all_pass():
    """3파일 모두 pass."""
    files = [
        'src/content/ko/a.mdx',
        'src/content/ko/b.mdx',
        'src/content/ko/c.mdx',
    ]
    pass_result = {'status': 'pass', 'page_id': 'p1', 'changes_count': 1}

    with patch('reverse_sync_cli._get_changed_ko_mdx_files', return_value=files), \
         patch('reverse_sync_cli._do_verify', return_value=pass_result), \
         patch('builtins.print'):
        results = _do_verify_batch('proofread/fix-typo')

    assert len(results) == 3
    assert all(r['status'] == 'pass' for r in results)


def test_do_verify_batch_with_error():
    """1파일 에러, 나머지 계속 처리."""
    files = [
        'src/content/ko/a.mdx',
        'src/content/ko/b.mdx',
        'src/content/ko/c.mdx',
    ]
    pass_result = {'status': 'pass', 'page_id': 'p1', 'changes_count': 1}
    call_count = 0

    def mock_do_verify(args):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ValueError("page not found")
        return pass_result

    with patch('reverse_sync_cli._get_changed_ko_mdx_files', return_value=files), \
         patch('reverse_sync_cli._do_verify', side_effect=mock_do_verify), \
         patch('builtins.print'):
        results = _do_verify_batch('proofread/fix-typo')

    assert len(results) == 3
    assert results[0]['status'] == 'pass'
    assert results[1]['status'] == 'error'
    assert 'page not found' in results[1]['error']
    assert results[2]['status'] == 'pass'


def test_do_verify_batch_no_changes():
    """변경 파일 없으면 no_changes 반환."""
    with patch('reverse_sync_cli._get_changed_ko_mdx_files', return_value=[]):
        results = _do_verify_batch('proofread/fix-typo')

    assert len(results) == 1
    assert results[0]['status'] == 'no_changes'
    assert results[0]['branch'] == 'proofread/fix-typo'


# --- main() batch tests ---


def test_main_verify_branch(monkeypatch):
    """main() 통합 테스트 — 배치 verify."""
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'verify', '--branch', 'proofread/fix-typo'])
    batch_results = [
        {'status': 'pass', 'page_id': 'p1', 'changes_count': 1},
        {'status': 'pass', 'page_id': 'p2', 'changes_count': 2},
    ]

    with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results) as mock_batch, \
         patch('reverse_sync_cli._do_push') as mock_push, \
         patch('builtins.print'):
        main()

    mock_batch.assert_called_once_with('proofread/fix-typo', limit=0, failures_only=False, push=False, yes=False, lenient=False, no_normalize=False)
    mock_push.assert_not_called()


def test_main_push_branch(tmp_path, monkeypatch):
    """main() 통합 테스트 — 배치 push (all pass, push=True)."""
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--yes', '--branch', 'proofread/fix-typo'])
    monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)

    batch_results = [
        {'status': 'pass', 'page_id': 'p1', 'changes_count': 1,
         'push': {'page_id': 'p1', 'title': 'T1', 'version': 2, 'url': '/t1'}},
        {'status': 'pass', 'page_id': 'p2', 'changes_count': 2,
         'push': {'page_id': 'p2', 'title': 'T2', 'version': 3, 'url': '/t2'}},
    ]

    with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results) as mock_batch, \
         patch('builtins.print'):
        main()

    mock_batch.assert_called_once_with('proofread/fix-typo', limit=0, failures_only=False, push=True, yes=True, lenient=False, no_normalize=False)


def test_main_push_branch_with_failure(monkeypatch):
    """배치 push 시 일부 fail → exit 1 (pass한 문서는 이미 push됨)."""
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--yes', '--branch', 'proofread/fix-typo'])
    batch_results = [
        {'status': 'pass', 'page_id': 'p1', 'changes_count': 1,
         'push': {'page_id': 'p1', 'title': 'T', 'version': 2, 'url': '/t'}},
        {'status': 'fail', 'page_id': 'p2', 'changes_count': 1},
    ]

    with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results) as mock_batch, \
         patch('builtins.print'):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
    mock_batch.assert_called_once_with('proofread/fix-typo', limit=0, failures_only=False, push=True, yes=True, lenient=False, no_normalize=False)


def test_main_branch_mutual_exclusive(monkeypatch):
    """<mdx> + --branch 동시 사용 → exit 1."""
    monkeypatch.setattr('sys.argv', [
        'reverse_sync_cli.py', 'verify',
        'src/content/ko/test/page.mdx',
        '--branch', 'proofread/fix-typo',
    ])

    with patch('builtins.print'):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1


def test_main_branch_no_input(monkeypatch):
    """<mdx>도 --branch도 없음 → exit 1."""
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'verify'])

    with patch('builtins.print'):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1


def test_main_verify_branch_with_failure_exits(monkeypatch):
    """verify --branch에서 fail 있으면 exit 1."""
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'verify', '--branch', 'proofread/fix-typo'])
    batch_results = [
        {'status': 'pass', 'page_id': 'p1', 'changes_count': 1},
        {'status': 'error', 'file': 'src/content/ko/b.mdx', 'error': 'not found'},
    ]

    with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results) as mock_batch, \
         patch('builtins.print'):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
    mock_batch.assert_called_once_with('proofread/fix-typo', limit=0, failures_only=False, push=False, yes=False, lenient=False, no_normalize=False)


def test_main_verify_branch_lenient(monkeypatch):
    """--lenient 플래그가 _do_verify_batch에 전달된다."""
    monkeypatch.setattr('sys.argv', [
        'reverse_sync_cli.py', 'verify', '--branch', 'proofread/fix-typo', '--lenient'])
    batch_results = [
        {'status': 'pass', 'page_id': 'p1', 'changes_count': 1},
    ]

    with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results) as mock_batch, \
         patch('builtins.print'):
        main()

    mock_batch.assert_called_once_with('proofread/fix-typo', limit=0, failures_only=False, push=False, yes=False, lenient=True, no_normalize=False)


def test_main_verify_branch_no_normalize(monkeypatch):
    """--no-normalize 플래그가 _do_verify_batch에 전달된다."""
    monkeypatch.setattr('sys.argv', [
        'reverse_sync_cli.py', 'verify', '--branch', 'proofread/fix-typo', '--no-normalize'])
    batch_results = [
        {'status': 'pass', 'page_id': 'p1', 'changes_count': 1},
    ]

    with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results) as mock_batch, \
         patch('builtins.print'):
        main()

    mock_batch.assert_called_once_with('proofread/fix-typo', limit=0, failures_only=False, push=False, yes=False, lenient=False, no_normalize=True)


def test_usage_summary_includes_push_no_normalize():
    """push usage도 --no-normalize 지원과 일치해야 한다."""
    assert 'reverse-sync push   <mdx> [--original-mdx <mdx>] [--dry-run] [--yes] [--lenient] [--no-normalize]' in _USAGE_SUMMARY
    assert 'reverse-sync push   --branch <branch> [--dry-run] [--yes] [--lenient] [--no-normalize]' in _USAGE_SUMMARY


# --- normalize_mdx_to_plain tests ---


def test_normalize_mdx_heading():
    """## Title → Title"""
    assert normalize_mdx_to_plain('## Title', 'heading') == 'Title'
    assert normalize_mdx_to_plain('### Sub Title', 'heading') == 'Sub Title'


def test_normalize_mdx_paragraph():
    """**bold** and `code` → bold and code"""
    result = normalize_mdx_to_plain('**bold** and `code`', 'paragraph')
    assert result == 'bold and code'


def test_normalize_mdx_list():
    """리스트 마커, bold, entities 제거 + 연결."""
    content = (
        "1. Administrator &gt; Audit &gt; ... 메뉴로 이동합니다.\n"
        "2. 당월 기준으로...\n"
        "    4.  **Access Control Updated**  : 커넥션 접근 권한 수정이력"
    )
    result = normalize_mdx_to_plain(content, 'paragraph')
    expected = (
        "Administrator > Audit > ... 메뉴로 이동합니다.\n"
        "당월 기준으로...\n"
        "Access Control Updated  : 커넥션 접근 권한 수정이력"
    )
    assert result == expected


def test_normalize_mdx_list_with_figure():
    """figure/img 라인은 스킵된다."""
    content = (
        "1. 첫 번째 항목\n"
        '<figure><img src="test.png" /></figure>\n'
        "2. 두 번째 항목"
    )
    result = normalize_mdx_to_plain(content, 'paragraph')
    assert result == '첫 번째 항목\n두 번째 항목'


# --- build_patches index-based mapping tests ---


def testbuild_patches_index_mapping():
    """인덱스 기반 매핑으로 올바른 XHTML 노드를 찾는다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping
    from reverse_sync.sidecar import SidecarEntry

    original_blocks = [
        MdxBlock('frontmatter', '---\ntitle: T\n---\n', 1, 3),
        MdxBlock('empty', '\n', 4, 4),
        MdxBlock('heading', '## Title\n', 5, 5),       # content idx 0
        MdxBlock('empty', '\n', 6, 6),
        MdxBlock('paragraph', 'Old text.\n', 7, 7),    # content idx 1
    ]
    improved_blocks = [
        MdxBlock('frontmatter', '---\ntitle: T\n---\n', 1, 3),
        MdxBlock('empty', '\n', 4, 4),
        MdxBlock('heading', '## Title\n', 5, 5),
        MdxBlock('empty', '\n', 6, 6),
        MdxBlock('paragraph', 'New text.\n', 7, 7),
    ]
    changes = [
        BlockChange(index=4, change_type='modified',
                    old_block=original_blocks[4],
                    new_block=improved_blocks[4]),
    ]
    mappings = [
        BlockMapping(block_id='heading-1', type='heading', xhtml_xpath='h2[1]',
                     xhtml_text='Title', xhtml_plain_text='Title',
                     xhtml_element_index=0),
        BlockMapping(block_id='paragraph-2', type='paragraph', xhtml_xpath='p[1]',
                     xhtml_text='Old text.', xhtml_plain_text='Old text.',
                     xhtml_element_index=1),
    ]
    # MDX block index 4 → p[1] sidecar 엔트리
    mdx_to_sidecar = {
        4: SidecarEntry(xhtml_xpath='p[1]', xhtml_type='paragraph', mdx_blocks=[4]),
    }
    xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

    patches, *_ = build_patches(changes, original_blocks, improved_blocks, mappings,
                            mdx_to_sidecar, xpath_to_mapping)

    assert len(patches) == 1
    assert patches[0]['xhtml_xpath'] == 'p[1]'
    assert patches[0]['action'] == 'replace_fragment'
    assert patches[0]['new_element_xhtml'] == '<p>New text.</p>'


def testbuild_patches_skips_non_content():
    """empty/frontmatter/import 블록은 패치하지 않는다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping

    original_blocks = [
        MdxBlock('empty', '\n', 1, 1),
        MdxBlock('paragraph', 'Text.\n', 2, 2),
    ]
    improved_blocks = [
        MdxBlock('empty', '\n\n', 1, 1),
        MdxBlock('paragraph', 'Text.\n', 2, 2),
    ]
    changes = [
        BlockChange(index=0, change_type='modified',
                    old_block=original_blocks[0],
                    new_block=improved_blocks[0]),
    ]
    mappings = [
        BlockMapping(block_id='paragraph-1', type='paragraph', xhtml_xpath='p[1]',
                     xhtml_text='Text.', xhtml_plain_text='Text.',
                     xhtml_element_index=0),
    ]

    patches, *_ = build_patches(changes, original_blocks, improved_blocks, mappings,
                            {}, {})
    assert len(patches) == 0


# --- _strip_frontmatter tests ---


def test_strip_frontmatter():
    """frontmatter 블록을 제거한다."""
    mdx = "---\ntitle: '관리자 매뉴얼'\nconfluenceUrl: 'https://example.com'\n---\n\n## Title\n"
    result = _strip_frontmatter(mdx)
    assert result == "\n## Title\n"


def test_strip_frontmatter_no_frontmatter():
    """frontmatter가 없으면 원문을 그대로 반환한다."""
    mdx = "## Title\n\nParagraph.\n"
    assert _strip_frontmatter(mdx) == mdx


# --- normalize_mdx_to_plain with markdown links ---


def test_normalize_mdx_with_links():
    """마크다운 링크 [text](url) → text로 정규화한다."""
    content = "[Connection Management](/docs/connection) and **bold**"
    result = normalize_mdx_to_plain(content, 'paragraph')
    assert result == "Connection Management and bold"


# --- verify ignores frontmatter diff ---


def test_verify_ignores_frontmatter_diff(setup_var):
    """roundtrip verify 시 frontmatter 차이는 무시된다."""
    page_id, var_dir = setup_var

    improved_mdx = "---\ntitle: 'Test'\n---\n\n## Title\n\nModified.\n"
    verify_content = "---\ntitle: 'Test'\nconfluenceUrl: 'https://example.com'\n---\n\n## Title\n\nModified.\n"

    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id, **kwargs):
        Path(output_mdx_path).write_text(verify_content)
        return verify_content

    with patch('reverse_sync_cli._forward_convert', side_effect=mock_forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(content="---\ntitle: 'Test'\n---\n\n## Title\n\nParagraph.\n", descriptor="original.mdx"),
            improved_src=MdxSource(content=improved_mdx, descriptor="improved.mdx"),
        )
    assert result['status'] == 'pass'
    assert result['verification']['exact_match'] is True


# --- build_patches with table/list blocks ---


def test_verify_result_includes_xhtml_diff(setup_var):
    """run_verify() 결과에 xhtml_diff_report 필드가 포함된다."""
    page_id, var_dir = setup_var

    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id, **kwargs):
        Path(output_mdx_path).write_text("## Title\n\nModified.\n")
        return "## Title\n\nModified.\n"

    with patch('reverse_sync_cli._forward_convert', side_effect=mock_forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(content="## Title\n\nParagraph.\n", descriptor="original.mdx"),
            improved_src=MdxSource(content="## Title\n\nModified.\n", descriptor="improved.mdx"),
        )
    assert 'xhtml_diff_report' in result
    assert isinstance(result['xhtml_diff_report'], str)
    # 패치가 적용되었으므로 XHTML diff가 비어있지 않아야 한다
    assert result['xhtml_diff_report'] != ''


def test_verify_result_includes_mdx_diff(setup_var):
    """run_verify() 결과에 mdx_diff_report (original→improved) 필드가 포함된다."""
    page_id, var_dir = setup_var

    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id, **kwargs):
        Path(output_mdx_path).write_text("## Title\n\nModified.\n")
        return "## Title\n\nModified.\n"

    with patch('reverse_sync_cli._forward_convert', side_effect=mock_forward_convert):
        result = run_verify(
            page_id=page_id,
            original_src=MdxSource(content="## Title\n\nParagraph.\n", descriptor="original.mdx"),
            improved_src=MdxSource(content="## Title\n\nModified.\n", descriptor="improved.mdx"),
        )
    assert 'mdx_diff_report' in result
    assert isinstance(result['mdx_diff_report'], str)
    assert result['mdx_diff_report'] != ''
    # diff에 변경 내용이 포함되어야 한다
    assert 'Paragraph.' in result['mdx_diff_report']
    assert 'Modified.' in result['mdx_diff_report']


def test_verify_no_changes_has_empty_diffs(setup_var):
    """변경 없으면 mdx_diff_report, xhtml_diff_report 모두 빈 문자열이다."""
    page_id, var_dir = setup_var
    mdx_content = "## Title\n\nParagraph.\n"

    result = run_verify(
        page_id=page_id,
        original_src=MdxSource(content=mdx_content, descriptor="original.mdx"),
        improved_src=MdxSource(content=mdx_content, descriptor="improved.mdx"),
    )
    assert result['mdx_diff_report'] == ''
    assert result['xhtml_diff_report'] == ''


def testbuild_patches_table_block():
    """테이블 html_block에서 셀 경계 공백 차이가 있어도 패치가 생성된다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping
    from reverse_sync.sidecar import (
        DocumentEnvelope,
        RoundtripSidecar,
        SidecarBlock,
        SidecarEntry,
    )

    old_table = '<table>\n<th>\n**Databased Access Control**\n</th>\n</table>\n'
    new_table = '<table>\n<th>\n**Database Access Control**\n</th>\n</table>\n'

    original_blocks = [MdxBlock('html_block', old_table, 1, 5)]
    improved_blocks = [MdxBlock('html_block', new_table, 1, 5)]
    changes = [
        BlockChange(index=0, change_type='modified',
                    old_block=original_blocks[0],
                    new_block=improved_blocks[0]),
    ]
    mappings = [
        BlockMapping(block_id='table-1', type='table', xhtml_xpath='table[1]',
                     xhtml_text='<table>...</table>',
                     xhtml_plain_text='Databased Access Control',
                     xhtml_element_index=0),
    ]
    # MDX block index 0 → table[1] sidecar 엔트리
    mdx_to_sidecar = {
        0: SidecarEntry(xhtml_xpath='table[1]', xhtml_type='table', mdx_blocks=[0]),
    }
    roundtrip_sidecar = RoundtripSidecar(
        page_id='test',
        blocks=[SidecarBlock(0, 'table[1]', '<table>...</table>', 'hash1', (1, 5))],
        separators=[],
        document_envelope=DocumentEnvelope(prefix='', suffix='\n'),
    )
    xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

    patches, *_ = build_patches(changes, original_blocks, improved_blocks, mappings,
                            mdx_to_sidecar, xpath_to_mapping,
                            roundtrip_sidecar=roundtrip_sidecar)

    assert len(patches) == 1
    assert patches[0]['xhtml_xpath'] == 'table[1]'
    # raw HTML table은 text-level 패치로 처리 (XHTML 구조 보존)
    assert 'old_plain_text' in patches[0]
    assert 'new_plain_text' in patches[0]
    assert 'Database Access Control' in patches[0]['new_plain_text']


def testbuild_patches_html_table_structural_change_skipped():
    """raw HTML table에서 행 수가 변경되면 패치를 생성하지 않는다 (silent corruption 방지)."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping
    from reverse_sync.sidecar import (
        DocumentEnvelope,
        RoundtripSidecar,
        SidecarBlock,
        SidecarEntry,
    )

    old_table = '<table>\n<tr><td>Row 1</td></tr>\n</table>\n'
    new_table = '<table>\n<tr><td>Row 1</td></tr>\n<tr><td>Row 2</td></tr>\n</table>\n'

    original_blocks = [MdxBlock('html_block', old_table, 1, 3)]
    improved_blocks = [MdxBlock('html_block', new_table, 1, 4)]
    changes = [
        BlockChange(index=0, change_type='modified',
                    old_block=original_blocks[0],
                    new_block=improved_blocks[0]),
    ]
    mappings = [
        BlockMapping(block_id='table-1', type='table', xhtml_xpath='table[1]',
                     xhtml_text='<table><tr><td>Row 1</td></tr></table>',
                     xhtml_plain_text='Row 1',
                     xhtml_element_index=0),
    ]
    mdx_to_sidecar = {
        0: SidecarEntry(xhtml_xpath='table[1]', xhtml_type='table', mdx_blocks=[0]),
    }
    roundtrip_sidecar = RoundtripSidecar(
        page_id='test',
        blocks=[SidecarBlock(0, 'table[1]', '<table><tr><td>Row 1</td></tr></table>', 'hash1', (1, 3))],
        separators=[],
        document_envelope=DocumentEnvelope(prefix='', suffix='\n'),
    )
    xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

    patches, *_ = build_patches(changes, original_blocks, improved_blocks, mappings,
                            mdx_to_sidecar, xpath_to_mapping,
                            roundtrip_sidecar=roundtrip_sidecar)

    # 구조 변경(행 추가)이므로 패치가 생성되지 않아야 한다
    assert len(patches) == 0


def testbuild_patches_html_table_column_change_skipped():
    """raw HTML table에서 셀 수가 변경되면 패치를 생성하지 않는다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping
    from reverse_sync.sidecar import (
        DocumentEnvelope, RoundtripSidecar, SidecarBlock, SidecarEntry,
    )

    old_table = '<table>\n<tr><td>A</td></tr>\n</table>\n'
    new_table = '<table>\n<tr><td>A</td><td>B</td></tr>\n</table>\n'

    original_blocks = [MdxBlock('html_block', old_table, 1, 3)]
    improved_blocks = [MdxBlock('html_block', new_table, 1, 3)]
    changes = [
        BlockChange(index=0, change_type='modified',
                    old_block=original_blocks[0],
                    new_block=improved_blocks[0]),
    ]
    mappings = [
        BlockMapping(block_id='table-1', type='table', xhtml_xpath='table[1]',
                     xhtml_text='<table><tr><td>A</td></tr></table>',
                     xhtml_plain_text='A',
                     xhtml_element_index=0),
    ]
    mdx_to_sidecar = {
        0: SidecarEntry(xhtml_xpath='table[1]', xhtml_type='table', mdx_blocks=[0]),
    }
    roundtrip_sidecar = RoundtripSidecar(
        page_id='test',
        blocks=[SidecarBlock(0, 'table[1]', '<table><tr><td>A</td></tr></table>', 'hash1', (1, 3))],
        separators=[],
        document_envelope=DocumentEnvelope(prefix='', suffix='\n'),
    )
    xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

    patches, *_ = build_patches(changes, original_blocks, improved_blocks, mappings,
                            mdx_to_sidecar, xpath_to_mapping,
                            roundtrip_sidecar=roundtrip_sidecar)

    # 구조 변경(열 추가)이므로 패치가 생성되지 않아야 한다
    assert len(patches) == 0


def testbuild_patches_html_table_cell_swap_skipped():
    """raw HTML table에서 셀 내용이 재배치되면 패치를 생성하지 않는다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping
    from reverse_sync.sidecar import (
        DocumentEnvelope, RoundtripSidecar, SidecarBlock, SidecarEntry,
    )

    old_table = '<table>\n<tr><td>A</td><td>B</td></tr>\n</table>\n'
    new_table = '<table>\n<tr><td>B</td><td>A</td></tr>\n</table>\n'

    original_blocks = [MdxBlock('html_block', old_table, 1, 3)]
    improved_blocks = [MdxBlock('html_block', new_table, 1, 3)]
    changes = [
        BlockChange(index=0, change_type='modified',
                    old_block=original_blocks[0],
                    new_block=improved_blocks[0]),
    ]
    mappings = [
        BlockMapping(block_id='table-1', type='table', xhtml_xpath='table[1]',
                     xhtml_text='<table><tr><td>A</td><td>B</td></tr></table>',
                     xhtml_plain_text='AB',
                     xhtml_element_index=0),
    ]
    mdx_to_sidecar = {
        0: SidecarEntry(xhtml_xpath='table[1]', xhtml_type='table', mdx_blocks=[0]),
    }
    roundtrip_sidecar = RoundtripSidecar(
        page_id='test',
        blocks=[SidecarBlock(0, 'table[1]', '<table><tr><td>A</td><td>B</td></tr></table>', 'hash1', (1, 3))],
        separators=[],
        document_envelope=DocumentEnvelope(prefix='', suffix='\n'),
    )
    xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

    patches, *_ = build_patches(changes, original_blocks, improved_blocks, mappings,
                            mdx_to_sidecar, xpath_to_mapping,
                            roundtrip_sidecar=roundtrip_sidecar)

    # 셀 재배치(같은 수지만 위치 변경)이므로 패치가 생성되지 않아야 한다
    assert len(patches) == 0


# --- sidecar 전용 매칭 코드 경로 테스트 ---


def testbuild_patches_child_resolved():
    """parent+children 매핑에서 containing 전략으로 parent xpath로 패치한다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping
    from reverse_sync.sidecar import SidecarEntry

    original_blocks = [
        MdxBlock('paragraph', 'Old child text.\n', 1, 1),
    ]
    improved_blocks = [
        MdxBlock('paragraph', 'New child text.\n', 1, 1),
    ]
    changes = [
        BlockChange(index=0, change_type='modified',
                    old_block=original_blocks[0],
                    new_block=improved_blocks[0]),
    ]
    parent = BlockMapping(
        block_id='callout-1', type='html_block',
        xhtml_xpath='macro-info[1]',
        xhtml_text='<p>Old child text.</p>',
        xhtml_plain_text='Old child text.',
        xhtml_element_index=0,
        children=['paragraph-2'],
    )
    child = BlockMapping(
        block_id='paragraph-2', type='paragraph',
        xhtml_xpath='macro-info[1]/p[1]',
        xhtml_text='Old child text.',
        xhtml_plain_text='Old child text.',
        xhtml_element_index=1,
    )
    mappings = [parent, child]
    mdx_to_sidecar = {
        0: SidecarEntry(xhtml_xpath='macro-info[1]', xhtml_type='html_block',
                        mdx_blocks=[0]),
    }
    xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

    patches, *_ = build_patches(changes, original_blocks, improved_blocks, mappings,
                            mdx_to_sidecar, xpath_to_mapping)

    # containing 전략 → text-level 패치 (sidecar 없으므로 원본 XHTML 구조 보존)
    assert len(patches) == 1
    assert patches[0]['xhtml_xpath'] == 'macro-info[1]'
    assert 'New child text.' in patches[0]['new_plain_text']


def testbuild_patches_child_fallback_to_parent_containing():
    """child 해석 실패 시 parent를 containing block으로 사용하여 패치한다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping
    from reverse_sync.sidecar import SidecarEntry

    original_blocks = [
        MdxBlock('paragraph', 'Unresolvable old text.\n', 1, 1),
    ]
    improved_blocks = [
        MdxBlock('paragraph', 'Unresolvable new text.\n', 1, 1),
    ]
    changes = [
        BlockChange(index=0, change_type='modified',
                    old_block=original_blocks[0],
                    new_block=improved_blocks[0]),
    ]
    parent = BlockMapping(
        block_id='callout-1', type='html_block',
        xhtml_xpath='macro-info[1]',
        xhtml_text='...',
        xhtml_plain_text='Prefix. Unresolvable old text. Suffix.',
        xhtml_element_index=0,
        children=['paragraph-2'],
    )
    child = BlockMapping(
        block_id='paragraph-2', type='paragraph',
        xhtml_xpath='macro-info[1]/p[1]',
        xhtml_text='Completely different.',
        xhtml_plain_text='Completely different.',
        xhtml_element_index=1,
    )
    mappings = [parent, child]
    mdx_to_sidecar = {
        0: SidecarEntry(xhtml_xpath='macro-info[1]', xhtml_type='html_block',
                        mdx_blocks=[0]),
    }
    xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

    patches, *_ = build_patches(changes, original_blocks, improved_blocks, mappings,
                            mdx_to_sidecar, xpath_to_mapping)

    assert len(patches) == 1
    assert patches[0]['xhtml_xpath'] == 'macro-info[1]'
    assert 'Unresolvable new text.' in patches[0]['new_plain_text']


def testbuild_patches_unmapped_block_skipped():
    """sidecar에 없고 list/table도 아닌 블록은 skip된다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping
    from reverse_sync.sidecar import SidecarEntry

    original_blocks = [
        MdxBlock('paragraph', 'Mapped text.\n', 1, 1),
        MdxBlock('html_block', '<div>Old html</div>\n', 2, 2),
    ]
    improved_blocks = [
        MdxBlock('paragraph', 'Mapped text.\n', 1, 1),
        MdxBlock('html_block', '<div>New html</div>\n', 2, 2),
    ]
    changes = [
        BlockChange(index=1, change_type='modified',
                    old_block=original_blocks[1],
                    new_block=improved_blocks[1]),
    ]
    mappings = [
        BlockMapping(block_id='paragraph-1', type='paragraph', xhtml_xpath='p[1]',
                     xhtml_text='Mapped text.', xhtml_plain_text='Mapped text.',
                     xhtml_element_index=0),
    ]
    # sidecar에 index 1 엔트리 없음
    mdx_to_sidecar = {
        0: SidecarEntry(xhtml_xpath='p[1]', xhtml_type='paragraph', mdx_blocks=[0]),
    }
    xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

    patches, *_ = build_patches(changes, original_blocks, improved_blocks, mappings,
                            mdx_to_sidecar, xpath_to_mapping)

    assert len(patches) == 0


class TestParseAndDiff:
    """_parse_and_diff 함수 테스트."""

    def test_no_changes(self):
        mdx = "# Title\n\nSome text"
        changes, alignment, orig_blocks, impr_blocks = _parse_and_diff(mdx, mdx)
        assert changes == []
        assert len(orig_blocks) > 0

    def test_detects_changes(self):
        original = "# Title\n\nOriginal text"
        improved = "# Title\n\nImproved text"
        changes, alignment, orig_blocks, impr_blocks = _parse_and_diff(
            original, improved)
        assert len(changes) > 0


class TestSaveDiffYaml:
    """_save_diff_yaml 함수 테스트."""

    def test_writes_yaml_file(self, tmp_path):
        from reverse_sync.block_diff import BlockChange
        from mdx_to_storage.parser import parse_mdx_blocks

        original = "# Title\n\nOriginal"
        improved = "# Title\n\nImproved"
        orig_blocks = parse_mdx_blocks(original)
        impr_blocks = parse_mdx_blocks(improved)

        old_b = [b for b in orig_blocks if b.content.strip() == 'Original'][0]
        new_b = [b for b in impr_blocks if b.content.strip() == 'Improved'][0]
        changes = [BlockChange(index=1, change_type='modified',
                               old_block=old_b, new_block=new_b)]

        _save_diff_yaml(
            var_dir=tmp_path,
            page_id='test123',
            now='2026-01-01T00:00:00Z',
            original_descriptor='main:test.mdx',
            improved_descriptor='branch:test.mdx',
            changes=changes,
        )
        assert (tmp_path / 'reverse-sync.diff.yaml').exists()


class TestCompileResult:
    """_compile_result 함수 테스트."""

    def test_pass_result(self, tmp_path):
        from unittest.mock import MagicMock
        verify_result = MagicMock()
        verify_result.passed = True
        result = _compile_result(
            var_dir=tmp_path,
            page_id='test123',
            now='2026-01-01T00:00:00Z',
            changes_count=2,
            mdx_diff_report='some diff',
            xhtml_diff_report='xhtml diff',
            verify_result=verify_result,
            roundtrip_diff_report='',
        )
        assert result['status'] == 'pass'
        assert result['changes_count'] == 2
        assert (tmp_path / 'reverse-sync.result.yaml').exists()

    def test_fail_result(self, tmp_path):
        from unittest.mock import MagicMock
        verify_result = MagicMock()
        verify_result.passed = False
        result = _compile_result(
            var_dir=tmp_path,
            page_id='test123',
            now='2026-01-01T00:00:00Z',
            changes_count=1,
            mdx_diff_report='',
            xhtml_diff_report='',
            verify_result=verify_result,
            roundtrip_diff_report='diff here',
        )
        assert result['status'] == 'fail'


# --- _detect_language tests ---


def test_detect_language_ko_from_ref_path():
    assert _detect_language('split/ko-proofread:src/content/ko/installation/page.mdx') == 'ko'


def test_detect_language_en_from_ref_path():
    assert _detect_language('main:src/content/en/installation/page.mdx') == 'en'


def test_detect_language_ja_from_ref_path():
    assert _detect_language('main:src/content/ja/installation/page.mdx') == 'ja'


def test_detect_language_ko_from_file_path():
    assert _detect_language('src/content/ko/overview.mdx') == 'ko'


def test_detect_language_defaults_to_ko():
    """src/content/{lang}/ 패턴이 없으면 기본값 'ko'를 반환한다."""
    assert _detect_language('/tmp/improved.mdx') == 'ko'
    assert _detect_language('original.mdx') == 'ko'


class TestFindBlockquotesMissingBlankLine:
    def test_no_blockquote(self):
        assert _find_blockquotes_missing_blank_line("paragraph\n\nanother\n") == []

    def test_blockquote_followed_by_blank_line(self):
        text = "> quote\n\nnext paragraph\n"
        assert _find_blockquotes_missing_blank_line(text) == []

    def test_blockquote_at_end_of_file(self):
        """파일 마지막 줄 blockquote 는 다음 줄이 없으므로 위반 아님."""
        text = "> quote\n"
        assert _find_blockquotes_missing_blank_line(text) == []

    def test_blockquote_not_followed_by_blank_line(self):
        text = "> quote\nnext paragraph\n"
        result = _find_blockquotes_missing_blank_line(text)
        assert result == [(1, "> quote")]

    def test_multi_line_blockquote_only_last_line_checked(self):
        """연속된 blockquote 줄에서는 마지막 줄만 검사한다."""
        text = "> line1\n> line2\nnext paragraph\n"
        result = _find_blockquotes_missing_blank_line(text)
        assert len(result) == 1
        assert result[0][1] == "> line2"

    def test_multi_line_blockquote_with_blank_after_last(self):
        text = "> line1\n> line2\n\nnext paragraph\n"
        assert _find_blockquotes_missing_blank_line(text) == []

    def test_blockquote_inside_fenced_code_block_ignored(self):
        text = "```\n> not a blockquote\n```\n"
        assert _find_blockquotes_missing_blank_line(text) == []

    def test_multiple_violations(self):
        text = "> quote1\nnext1\n\n> quote2\nnext2\n"
        result = _find_blockquotes_missing_blank_line(text)
        assert len(result) == 2
        assert result[0] == (1, "> quote1")
        assert result[1] == (4, "> quote2")


class TestValidateImprovedMdxBlockquote:
    def test_passes_when_blank_line_after_blockquote(self):
        """blockquote 이후 빈 줄이 있으면 검증 통과."""
        _validate_improved_mdx("> quote\n\nparagraph\n", "test.mdx")

    def test_raises_when_no_blank_line_after_blockquote(self):
        """blockquote 이후 빈 줄이 없으면 ValueError."""
        with pytest.raises(ValueError, match="Blockquote not followed by a blank line"):
            _validate_improved_mdx("> quote\nparagraph\n", "test.mdx")

    def test_error_message_includes_descriptor(self):
        with pytest.raises(ValueError, match="my_file.mdx"):
            _validate_improved_mdx("> quote\nparagraph\n", "my_file.mdx")

    def test_error_message_includes_line_number(self):
        with pytest.raises(ValueError, match="line 1"):
            _validate_improved_mdx("> quote\nparagraph\n", "test.mdx")


# ── Push 안전장치 테스트 ──────────────────────────────────────────

class TestPushConflictError:
    """409 버전 충돌 시 PushConflictError 발생."""

    def test_conflict_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)
        page_id = 'conflict-page'
        var_dir = tmp_path / 'var' / page_id
        var_dir.mkdir(parents=True)
        (var_dir / 'reverse-sync.patched.xhtml').write_text('<p>New</p>')

        mock_response = MagicMock()
        mock_response.status_code = 409
        http_error = __import__('requests').HTTPError(response=mock_response)

        with patch('reverse_sync.confluence_client._load_credentials',
                   return_value=('e@x.com', 'tok')), \
             patch('reverse_sync.confluence_client.get_page_version',
                   return_value={'version': 5, 'title': 'Test'}), \
             patch('reverse_sync.confluence_client.get_page_body',
                   return_value='<p>Old</p>'), \
             patch('reverse_sync.confluence_client.update_page_body',
                   side_effect=http_error):
            with pytest.raises(PushConflictError, match="Confluence에서 변경"):
                _do_push(page_id)

    def test_non_409_reraises(self, tmp_path, monkeypatch):
        monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)
        page_id = 'error-page'
        var_dir = tmp_path / 'var' / page_id
        var_dir.mkdir(parents=True)
        (var_dir / 'reverse-sync.patched.xhtml').write_text('<p>New</p>')

        mock_response = MagicMock()
        mock_response.status_code = 500
        http_error = __import__('requests').HTTPError(response=mock_response)

        with patch('reverse_sync.confluence_client._load_credentials',
                   return_value=('e@x.com', 'tok')), \
             patch('reverse_sync.confluence_client.get_page_version',
                   return_value={'version': 5, 'title': 'Test'}), \
             patch('reverse_sync.confluence_client.get_page_body',
                   return_value='<p>Old</p>'), \
             patch('reverse_sync.confluence_client.update_page_body',
                   side_effect=http_error):
            with pytest.raises(__import__('requests').HTTPError):
                _do_push(page_id)


class TestPushBackup:
    """push 시 backup.xhtml 생성 확인."""

    def test_backup_created(self, tmp_path, monkeypatch):
        monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)
        page_id = 'backup-page'
        var_dir = tmp_path / 'var' / page_id
        var_dir.mkdir(parents=True)
        (var_dir / 'reverse-sync.patched.xhtml').write_text('<p>New</p>')

        with patch('reverse_sync.confluence_client._load_credentials',
                   return_value=('e@x.com', 'tok')), \
             patch('reverse_sync.confluence_client.get_page_version',
                   return_value={'version': 5, 'title': 'Test'}), \
             patch('reverse_sync.confluence_client.get_page_body',
                   return_value='<p>Before Push</p>'), \
             patch('reverse_sync.confluence_client.update_page_body',
                   return_value={'title': 'Test', 'version': {'number': 6},
                                 '_links': {'webui': '/t'}}):
            result = _do_push(page_id)

        backup = var_dir / 'reverse-sync.backup.xhtml'
        assert backup.exists()
        assert backup.read_text() == '<p>Before Push</p>'
        assert result['version'] == 6


class TestPushConfirmPrompt:
    """확인 프롬프트 동작 테스트."""

    def test_confirm_no_aborts_single(self, monkeypatch):
        """단일 push 시 확인 거부 → push 안 함."""
        mdx_arg = 'src/content/ko/test/page.mdx'
        monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', mdx_arg])
        pass_result = {'status': 'pass', 'page_id': 'p1', 'title': 'Test', 'changes_count': 1}

        with patch('reverse_sync_cli._do_verify', return_value=pass_result), \
             patch('reverse_sync_cli.sys.stdin') as mock_stdin, \
             patch('reverse_sync_cli._confirm', return_value=False), \
             patch('reverse_sync_cli._do_push') as mock_push, \
             patch('builtins.print'):
            mock_stdin.isatty.return_value = True
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        mock_push.assert_not_called()

    def test_yes_flag_skips_confirm_single(self, tmp_path, monkeypatch):
        """--yes 시 확인 프롬프트 없이 push."""
        page_id = 'yes-page'
        mdx_arg = 'src/content/ko/test/page.mdx'
        monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--yes', '--json', mdx_arg])
        monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)

        var_dir = tmp_path / 'var' / page_id
        var_dir.mkdir(parents=True)
        (var_dir / 'reverse-sync.patched.xhtml').write_text('<p>New</p>')

        pass_result = {'status': 'pass', 'page_id': page_id, 'changes_count': 1}

        with patch('reverse_sync_cli._do_verify', return_value=pass_result), \
             patch('reverse_sync.confluence_client._load_credentials',
                   return_value=('e@x.com', 'tok')), \
             patch('reverse_sync.confluence_client.get_page_version',
                   return_value={'version': 5, 'title': 'Test'}), \
             patch('reverse_sync.confluence_client.get_page_body',
                   return_value='<p>Old</p>'), \
             patch('reverse_sync.confluence_client.update_page_body',
                   return_value={'title': 'Test', 'version': {'number': 6},
                                 '_links': {'webui': '/t'}}), \
             patch('reverse_sync_cli._confirm') as mock_confirm, \
             patch('builtins.print'):
            main()

        mock_confirm.assert_not_called()

    def test_batch_confirm_no_aborts(self, monkeypatch):
        """배치 push 시 확인 거부 → push 안 함."""
        files = ['src/content/ko/a.mdx']
        verify_result = {'status': 'pass', 'page_id': 'p1', 'changes_count': 1}

        with patch('reverse_sync_cli._get_changed_ko_mdx_files', return_value=files), \
             patch('reverse_sync_cli._do_verify', return_value=verify_result), \
             patch('reverse_sync_cli._confirm', return_value=False), \
             patch('reverse_sync_cli._do_push') as mock_push, \
             patch('builtins.print'):
            results = _do_verify_batch('test-branch', push=True, yes=False)

        mock_push.assert_not_called()
        assert 'push' not in results[0]

    def test_batch_yes_skips_confirm(self, tmp_path, monkeypatch):
        """배치 push --yes 시 확인 없이 push."""
        monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)
        page_id = 'batch-yes-page'
        var_dir = tmp_path / 'var' / page_id
        var_dir.mkdir(parents=True)
        (var_dir / 'reverse-sync.patched.xhtml').write_text('<p>New</p>')

        files = ['src/content/ko/a.mdx']
        verify_result = {'status': 'pass', 'page_id': page_id, 'changes_count': 1}
        push_result = {'page_id': page_id, 'title': 'T', 'version': 2, 'url': '/t', 'backup': str(var_dir / 'reverse-sync.backup.xhtml')}

        with patch('reverse_sync_cli._get_changed_ko_mdx_files', return_value=files), \
             patch('reverse_sync_cli._do_verify', return_value=verify_result), \
             patch('reverse_sync_cli._do_push', return_value=push_result) as mock_push, \
             patch('reverse_sync_cli._ensure_confluence_config', return_value=MagicMock()), \
             patch('reverse_sync_cli._confirm') as mock_confirm, \
             patch('builtins.print'):
            results = _do_verify_batch('test-branch', push=True, yes=True)

        mock_confirm.assert_not_called()
        mock_push.assert_called_once()
        assert results[0]['push']['version'] == 2


class TestPushNonTtyRequiresYes:
    """비대화형 환경에서 --yes 없이 push 시 에러."""

    def test_non_tty_without_yes_exits(self, monkeypatch):
        mdx_arg = 'src/content/ko/test/page.mdx'
        monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', mdx_arg])

        with patch('reverse_sync_cli.sys.stdin') as mock_stdin, \
             patch('builtins.print'):
            mock_stdin.isatty.return_value = False
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_non_tty_with_yes_proceeds(self, tmp_path, monkeypatch):
        mdx_arg = 'src/content/ko/test/page.mdx'
        monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--yes', '--json', mdx_arg])
        monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)
        page_id = 'nontty-page'
        var_dir = tmp_path / 'var' / page_id
        var_dir.mkdir(parents=True)
        (var_dir / 'reverse-sync.patched.xhtml').write_text('<p>New</p>')

        pass_result = {'status': 'pass', 'page_id': page_id, 'changes_count': 1}

        with patch('reverse_sync_cli._do_verify', return_value=pass_result), \
             patch('reverse_sync.confluence_client._load_credentials',
                   return_value=('e@x.com', 'tok')), \
             patch('reverse_sync.confluence_client.get_page_version',
                   return_value={'version': 5, 'title': 'Test'}), \
             patch('reverse_sync.confluence_client.get_page_body',
                   return_value='<p>Old</p>'), \
             patch('reverse_sync.confluence_client.update_page_body',
                   return_value={'title': 'Test', 'version': {'number': 6},
                                 '_links': {'webui': '/t'}}), \
             patch('builtins.print'):
            main()  # Should not exit with error


class TestPushExitCode:
    """배치 push conflict/error 시 exit code 테스트."""

    def test_batch_push_conflict_exits_nonzero(self, monkeypatch):
        """배치에서 push conflict 발생 시 exit 1."""
        monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--branch', 'b', '--yes'])
        batch_results = [
            {'status': 'pass', 'page_id': 'p1', 'changes_count': 1,
             'push': {'status': 'conflict', 'error': 'conflict'}},
        ]

        with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results), \
             patch('builtins.print'):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_batch_push_all_success_exits_zero(self, monkeypatch):
        """배치에서 모든 push 성공 시 exit 0."""
        monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--branch', 'b', '--yes'])
        batch_results = [
            {'status': 'pass', 'page_id': 'p1', 'changes_count': 1,
             'push': {'page_id': 'p1', 'title': 'T', 'version': 2, 'url': '/t'}},
        ]

        with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results), \
             patch('builtins.print'):
            main()  # exit 0 (no exception)


class TestPrintResultsPushStatus:
    """텍스트 출력이 push 실패 상태를 반영하는지 확인."""

    def test_failures_only_shows_push_conflict(self, monkeypatch, capsys):
        monkeypatch.setattr('reverse_sync_cli._supports_color', lambda: False)

        _print_results([
            {
                'file': 'src/content/ko/a.mdx',
                'status': 'pass',
                'changes_count': 1,
                'push': {'status': 'conflict', 'error': 'version conflict'},
            }
        ], failures_only=True)

        out = capsys.readouterr().out
        assert 'src/content/ko/a.mdx' in out
        assert 'PUSH CONFLICT' in out
        assert 'version conflict' in out
        assert '1 conflicts' in out
        assert '1 passed' not in out

    def test_summary_counts_push_error_as_failure(self, monkeypatch, capsys):
        monkeypatch.setattr('reverse_sync_cli._supports_color', lambda: False)

        _print_results([
            {
                'file': 'src/content/ko/b.mdx',
                'status': 'pass',
                'changes_count': 1,
                'push': {'status': 'error', 'error': 'network error'},
            }
        ])

        out = capsys.readouterr().out
        assert 'src/content/ko/b.mdx' in out
        assert 'PUSH ERROR' in out
        assert 'network error' in out
        assert '1 push errors' in out
        assert '1 passed' not in out


class TestCleanArtifactsPreservesBackup:
    """_clean_reverse_sync_artifacts가 backup을 보존하는지 확인."""

    def test_backup_preserved(self, tmp_path, monkeypatch):
        monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)
        page_id = 'preserve-backup'
        var_dir = tmp_path / 'var' / page_id
        var_dir.mkdir(parents=True)

        # 여러 reverse-sync 아티팩트 생성
        (var_dir / 'reverse-sync.diff.yaml').write_text('diff')
        (var_dir / 'reverse-sync.patched.xhtml').write_text('patched')
        (var_dir / 'reverse-sync.backup.xhtml').write_text('backup')

        from reverse_sync_cli import _clean_reverse_sync_artifacts
        _clean_reverse_sync_artifacts(page_id)

        # backup만 남아야 함
        assert (var_dir / 'reverse-sync.backup.xhtml').exists()
        assert not (var_dir / 'reverse-sync.diff.yaml').exists()
        assert not (var_dir / 'reverse-sync.patched.xhtml').exists()
