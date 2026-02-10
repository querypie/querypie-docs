import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from reverse_sync_cli import (
    run_verify, main, MdxSource, _resolve_mdx_source,
    _extract_ko_mdx_path, _resolve_page_id, _do_verify, _do_push,
    _get_changed_ko_mdx_files, _do_verify_batch,
    _normalize_mdx_to_plain, _build_patches, _strip_frontmatter,
    _transfer_text_changes, _find_mapping_by_text,
    _align_chars, _find_insert_pos,
)


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
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--json', mdx_arg])
    monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)

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

    mock_batch.assert_called_once_with('proofread/fix-typo', limit=0)
    mock_push.assert_not_called()


def test_main_push_branch(tmp_path, monkeypatch):
    """main() 통합 테스트 — 배치 push (all pass)."""
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--branch', 'proofread/fix-typo'])
    monkeypatch.setattr('reverse_sync_cli._PROJECT_DIR', tmp_path)

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


# --- _normalize_mdx_to_plain tests ---


def test_normalize_mdx_heading():
    """## Title → Title"""
    assert _normalize_mdx_to_plain('## Title', 'heading') == 'Title'
    assert _normalize_mdx_to_plain('### Sub Title', 'heading') == 'Sub Title'


def test_normalize_mdx_paragraph():
    """**bold** and `code` → bold and code"""
    result = _normalize_mdx_to_plain('**bold** and `code`', 'paragraph')
    assert result == 'bold and code'


def test_normalize_mdx_list():
    """리스트 마커, bold, entities 제거 + 연결."""
    content = (
        "1. Administrator &gt; Audit &gt; ... 메뉴로 이동합니다.\n"
        "2. 당월 기준으로...\n"
        "    4.  **Access Control Updated**  : 커넥션 접근 권한 수정이력"
    )
    result = _normalize_mdx_to_plain(content, 'paragraph')
    expected = (
        "Administrator > Audit > ... 메뉴로 이동합니다. "
        "당월 기준으로... "
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
    result = _normalize_mdx_to_plain(content, 'paragraph')
    assert result == '첫 번째 항목 두 번째 항목'


# --- _build_patches index-based mapping tests ---


def test_build_patches_index_mapping():
    """인덱스 기반 매핑으로 올바른 XHTML 노드를 찾는다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping

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

    patches = _build_patches(changes, original_blocks, improved_blocks, mappings)

    assert len(patches) == 1
    assert patches[0]['xhtml_xpath'] == 'p[1]'
    assert patches[0]['old_plain_text'] == 'Old text.'
    assert patches[0]['new_plain_text'] == 'New text.'


def test_build_patches_skips_non_content():
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

    patches = _build_patches(changes, original_blocks, improved_blocks, mappings)
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


# --- _normalize_mdx_to_plain with markdown links ---


def test_normalize_mdx_with_links():
    """마크다운 링크 [text](url) → text로 정규화한다."""
    content = "[Connection Management](/docs/connection) and **bold**"
    result = _normalize_mdx_to_plain(content, 'paragraph')
    assert result == "Connection Management and bold"


# --- verify ignores frontmatter diff ---


def test_verify_ignores_frontmatter_diff(setup_var):
    """roundtrip verify 시 frontmatter 차이는 무시된다."""
    page_id, var_dir = setup_var

    improved_mdx = "---\ntitle: 'Test'\n---\n\n## Title\n\nModified.\n"
    verify_content = "---\ntitle: 'Test'\nconfluenceUrl: 'https://example.com'\n---\n\n## Title\n\nModified.\n"

    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id):
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



# --- _find_mapping_by_text tests ---


def test_find_mapping_spaceless_match():
    """셀 경계 공백 차이가 있는 테이블 블록도 공백 무시 비교로 매핑한다."""
    from reverse_sync.mapping_recorder import BlockMapping

    mdx_plain = '설정 순서 설정 항목 1 Databased Access Control 설정하기'
    mapping = BlockMapping(
        block_id='table-12', type='table', xhtml_xpath='table[2]',
        xhtml_text='...', xhtml_element_index=11,
        xhtml_plain_text='설정 순서설정 항목1Databased Access Control 설정하기',
    )

    result = _find_mapping_by_text(mdx_plain, [mapping])
    assert result is not None
    assert result.xhtml_xpath == 'table[2]'


def test_find_mapping_prefix_prefers_best_length():
    """prefix 매칭 시 길이가 가장 유사한 후보를 선택한다."""
    from reverse_sync.mapping_recorder import BlockMapping

    prefix = 'Administrator > Audit > Databases > Access Control Logs'
    mdx_plain = prefix + ' 메뉴로 이동합니다. 당월 기준으로 내림차순으로 로그가 조회됩니다.'

    caption_mapping = BlockMapping(
        block_id='image-1', type='html_block', xhtml_xpath='ac:image[1]',
        xhtml_text='...', xhtml_element_index=0,
        xhtml_plain_text=prefix,
    )
    list_mapping = BlockMapping(
        block_id='list-2', type='list', xhtml_xpath='ol[1]',
        xhtml_text='...', xhtml_element_index=1,
        xhtml_plain_text=prefix + ' 메뉴로 이동합니다.당월 기준으로 내림차순으로 로그가 조회됩니다.',
    )

    result = _find_mapping_by_text(mdx_plain, [caption_mapping, list_mapping])
    assert result is not None
    assert result.xhtml_xpath == 'ol[1]'


# --- _align_chars tests ---


def test_align_chars_same_text():
    """동일 텍스트는 모든 위치가 매핑된다."""
    mapping = _align_chars('hello', 'hello')
    assert mapping == {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}


def test_align_chars_extra_spaces_in_source():
    """source에 여분 공백이 있으면 건너뛴다."""
    mapping = _align_chars('A B', 'AB')
    assert mapping[0] == 0
    assert mapping[2] == 1
    assert 1 not in mapping


def test_align_chars_extra_spaces_in_target():
    """target에 여분 공백이 있으면 건너뛴다."""
    mapping = _align_chars('AB', 'A B')
    assert mapping[0] == 0
    assert mapping[1] == 2


# --- _transfer_text_changes tests ---


def test_transfer_text_changes_replace():
    """MDX 간 텍스트 변경이 XHTML plain text에 올바르게 전이된다."""
    mdx_old = '설정 순서 설정 항목 1 Databased Access Control 설정하기'
    mdx_new = '설정 순서 설정 항목 1 Database Access Control 설정하기'
    xhtml_text = '설정 순서설정 항목1Databased Access Control 설정하기'

    result = _transfer_text_changes(mdx_old, mdx_new, xhtml_text)
    assert result == '설정 순서설정 항목1Database Access Control 설정하기'


def test_transfer_text_changes_no_change():
    """변경이 없으면 XHTML 원문이 그대로 반환된다."""
    result = _transfer_text_changes('Hello world', 'Hello world', 'Helloworld')
    assert result == 'Helloworld'


def test_transfer_text_changes_insert():
    """insert opcode (공백/문자 삽입)가 올바르게 전이된다."""
    result = _transfer_text_changes(
        '잠금해제 수행자 정보', '잠금 해제 수행자 정보', '잠금해제 수행자 정보')
    assert result == '잠금 해제 수행자 정보'


def test_transfer_text_changes_preserves_unrelated_text():
    """변경되지 않은 텍스트의 공백이 보존된다."""
    result = _transfer_text_changes(
        'Action At : 시점입니다. login ID 입니다.',
        'Action At : 시점입니다. login ID입니다.',
        'Action At : 시점입니다.login ID 입니다.')
    assert 'Action At : ' in result
    assert 'login ID입니다.' in result


def test_transfer_text_changes_multiple_inserts():
    """여러 insert 변경이 동시에 올바르게 전이된다."""
    result = _transfer_text_changes(
        '영향 받은 행수. 볼수 있습니다.',
        '영향을 받은 행 수. 볼 수 있습니다.',
        '영향 받은 행수.볼수 있습니다.')
    assert '영향을 받은' in result
    assert '행 수.' in result
    assert '볼 수 있습니다.' in result


# --- _build_patches with table/list blocks ---


def test_verify_result_includes_xhtml_diff(setup_var):
    """run_verify() 결과에 xhtml_diff_report 필드가 포함된다."""
    page_id, var_dir = setup_var

    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id):
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

    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id):
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


def test_build_patches_table_block():
    """테이블 html_block에서 셀 경계 공백 차이가 있어도 패치가 생성된다."""
    from reverse_sync.mdx_block_parser import MdxBlock
    from reverse_sync.block_diff import BlockChange
    from reverse_sync.mapping_recorder import BlockMapping

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

    patches = _build_patches(changes, original_blocks, improved_blocks, mappings)

    assert len(patches) == 1
    assert patches[0]['xhtml_xpath'] == 'table[1]'
    assert patches[0]['old_plain_text'] == 'Databased Access Control'
    assert patches[0]['new_plain_text'] == 'Database Access Control'
