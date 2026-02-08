import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from reverse_sync_cli import (
    run_verify, main, MdxSource, _resolve_mdx_source,
    _extract_ko_mdx_path, _resolve_page_id, _do_verify, _do_push,
    _get_changed_ko_mdx_files, _do_verify_batch,
)


@pytest.fixture
def setup_var(tmp_path, monkeypatch):
    """var/<page_id>/ 구조를 tmp_path에 생성하고 작업 디렉토리를 변경."""
    monkeypatch.chdir(tmp_path)
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
    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id):
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

    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id):
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
    """push 시 verify pass → _do_push 호출."""
    page_id = 'test-page-001'
    mdx_arg = 'src/content/ko/test/page.mdx'
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', mdx_arg])
    monkeypatch.chdir(tmp_path)

    # var 디렉토리에 patched xhtml 준비
    var_dir = tmp_path / 'var' / page_id
    var_dir.mkdir(parents=True)
    (var_dir / 'reverse-sync.patched.xhtml').write_text('<p>Updated</p>')

    pass_result = {'status': 'pass', 'page_id': page_id, 'changes_count': 1}
    push_result = {'page_id': page_id, 'title': 'Test', 'version': 6, 'url': '/test'}

    mock_get_version = MagicMock(return_value={'version': 5, 'title': 'Test'})
    mock_update = MagicMock(return_value={
        'title': 'Test', 'version': {'number': 6},
        '_links': {'webui': '/test'},
    })

    with patch('reverse_sync_cli._do_verify', return_value=pass_result), \
         patch('reverse_sync.confluence_client._load_credentials',
               return_value=('e@x.com', 'tok')), \
         patch('reverse_sync.confluence_client.get_page_version', mock_get_version), \
         patch('reverse_sync.confluence_client.update_page_body', mock_update), \
         patch('builtins.print') as mock_print:
        main()

    # push API 호출 확인
    mock_update.assert_called_once()
    call_args = mock_update.call_args
    assert call_args[0][1] == page_id
    assert call_args[1]['xhtml_body'] == '<p>Updated</p>'

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
    """pages.yaml에서 MDX 경로로 page_id를 유도한다."""
    import yaml
    monkeypatch.chdir(tmp_path)
    var_dir = tmp_path / "var"
    var_dir.mkdir()
    pages = [
        {'page_id': '544112828', 'path': ['user-manual', 'user-agent']},
        {'page_id': '123456789', 'path': ['overview']},
    ]
    (var_dir / 'pages.yaml').write_text(yaml.dump(pages))

    result = _resolve_page_id('src/content/ko/user-manual/user-agent.mdx')
    assert result == '544112828'


def test_resolve_page_id_not_found(tmp_path, monkeypatch):
    """pages.yaml에 없는 경로이면 ValueError를 발생시킨다."""
    import yaml
    monkeypatch.chdir(tmp_path)
    var_dir = tmp_path / "var"
    var_dir.mkdir()
    pages = [{'page_id': '111', 'path': ['other']}]
    (var_dir / 'pages.yaml').write_text(yaml.dump(pages))

    with pytest.raises(ValueError, match="not found in var/pages.yaml"):
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

    mock_batch.assert_called_once_with('proofread/fix-typo')
    mock_push.assert_not_called()


def test_main_push_branch(tmp_path, monkeypatch):
    """main() 통합 테스트 — 배치 push (all pass)."""
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--branch', 'proofread/fix-typo'])
    monkeypatch.chdir(tmp_path)

    batch_results = [
        {'status': 'pass', 'page_id': 'p1', 'changes_count': 1},
        {'status': 'pass', 'page_id': 'p2', 'changes_count': 2},
    ]
    push_result = {'page_id': 'p1', 'title': 'T', 'version': 2, 'url': '/t'}

    with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results), \
         patch('reverse_sync_cli._do_push', return_value=push_result) as mock_push, \
         patch('builtins.print'):
        main()

    assert mock_push.call_count == 2
    mock_push.assert_any_call('p1')
    mock_push.assert_any_call('p2')


def test_main_push_branch_with_failure(monkeypatch):
    """배치 push 시 일부 fail → exit 1, push 안 함."""
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--branch', 'proofread/fix-typo'])
    batch_results = [
        {'status': 'pass', 'page_id': 'p1', 'changes_count': 1},
        {'status': 'fail', 'page_id': 'p2', 'changes_count': 1},
    ]

    with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results), \
         patch('reverse_sync_cli._do_push') as mock_push, \
         patch('builtins.print'):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
    mock_push.assert_not_called()


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

    with patch('reverse_sync_cli._do_verify_batch', return_value=batch_results), \
         patch('builtins.print'):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
