import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from reverse_sync_cli import run_verify, main


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
    original = tmp_path / "original.mdx"
    improved = tmp_path / "improved.mdx"
    original.write_text(mdx_content)
    improved.write_text(mdx_content)

    result = run_verify(
        page_id=page_id,
        original_mdx_path=str(original),
        improved_mdx_path=str(improved),
    )
    assert result['status'] == 'no_changes'
    assert (var_dir / "reverse-sync.result.yaml").exists()


def test_verify_detects_changes(setup_var, tmp_path):
    """텍스트 변경 감지 + forward 변환 mock으로 roundtrip 검증."""
    page_id, var_dir = setup_var
    original = tmp_path / "original.mdx"
    improved = tmp_path / "improved.mdx"
    original.write_text("## Title\n\nParagraph.\n")
    improved.write_text("## Title\n\nModified.\n")

    # forward converter를 mock: verify.mdx에 improved_mdx 내용을 그대로 써서 pass 유도
    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id):
        Path(output_mdx_path).write_text("## Title\n\nModified.\n")
        return "## Title\n\nModified.\n"

    with patch('reverse_sync_cli._forward_convert', side_effect=mock_forward_convert):
        result = run_verify(
            page_id=page_id,
            original_mdx_path=str(original),
            improved_mdx_path=str(improved),
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


def test_verify_roundtrip_fail(setup_var, tmp_path):
    """forward 변환 결과가 다르면 status=fail."""
    page_id, var_dir = setup_var
    original = tmp_path / "original.mdx"
    improved = tmp_path / "improved.mdx"
    original.write_text("## Title\n\nParagraph.\n")
    improved.write_text("## Title\n\nModified.\n")

    def mock_forward_convert(patched_xhtml_path, output_mdx_path, page_id):
        # 다른 내용을 반환하여 roundtrip 실패 유도
        content = "## Title\n\nDifferent output.\n"
        Path(output_mdx_path).write_text(content)
        return content

    with patch('reverse_sync_cli._forward_convert', side_effect=mock_forward_convert):
        result = run_verify(
            page_id=page_id,
            original_mdx_path=str(original),
            improved_mdx_path=str(improved),
        )
    assert result['status'] == 'fail'
    assert result['verification']['exact_match'] is False
    assert result['verification']['diff_report'] != ''


# --- push command tests ---


@pytest.fixture
def setup_push_var(tmp_path, monkeypatch):
    """push 테스트용 var/<page_id>/ 구조 생성."""
    monkeypatch.chdir(tmp_path)
    page_id = "test-page-001"
    var_dir = tmp_path / "var" / page_id
    var_dir.mkdir(parents=True)
    return page_id, var_dir


def test_push_requires_verify_first(setup_push_var, monkeypatch):
    """result.yaml 없으면 에러."""
    page_id, var_dir = setup_push_var
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--page-id', page_id])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_push_rejects_non_pass(setup_push_var, monkeypatch):
    """status가 pass가 아니면 에러."""
    page_id, var_dir = setup_push_var
    import yaml
    (var_dir / 'reverse-sync.result.yaml').write_text(
        yaml.dump({'status': 'fail', 'page_id': page_id}))
    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--page-id', page_id])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_push_success(setup_push_var, monkeypatch):
    """mock API로 정상 push 확인."""
    page_id, var_dir = setup_push_var
    import yaml

    # verify pass 결과 + patched xhtml 준비
    (var_dir / 'reverse-sync.result.yaml').write_text(
        yaml.dump({'status': 'pass', 'page_id': page_id}))
    (var_dir / 'reverse-sync.patched.xhtml').write_text('<p>Updated content</p>')

    monkeypatch.setattr('sys.argv', ['reverse_sync_cli.py', 'push', '--page-id', page_id])

    mock_get_version = MagicMock(return_value={'version': 5, 'title': 'Test Page'})
    mock_update = MagicMock(return_value={
        'title': 'Test Page',
        'version': {'number': 6},
        '_links': {'webui': '/spaces/QP/pages/test-page-001'},
    })
    mock_load = MagicMock(return_value=('test@example.com', 'test-token'))

    with patch('reverse_sync.confluence_client._load_credentials', mock_load), \
         patch('reverse_sync.confluence_client.get_page_version', mock_get_version), \
         patch('reverse_sync.confluence_client.update_page_body', mock_update), \
         patch('builtins.print') as mock_print:
        main()

    # get_page_version 호출 확인
    mock_get_version.assert_called_once()
    call_args = mock_get_version.call_args
    assert call_args[0][1] == page_id

    # update_page_body 호출 확인
    mock_update.assert_called_once()
    call_args = mock_update.call_args
    assert call_args[0][1] == page_id
    assert call_args[1]['title'] == 'Test Page'
    assert call_args[1]['version'] == 6
    assert call_args[1]['xhtml_body'] == '<p>Updated content</p>'

    # 출력 JSON 확인
    output = mock_print.call_args[0][0]
    result = json.loads(output)
    assert result['page_id'] == page_id
    assert result['version'] == 6
    assert result['title'] == 'Test Page'
