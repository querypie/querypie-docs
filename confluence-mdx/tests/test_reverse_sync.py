import os
import pytest
from pathlib import Path
from unittest.mock import patch
from reverse_sync import run_verify


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
    assert (var_dir / "rsync" / "result.yaml").exists()


def test_verify_detects_changes(setup_var, tmp_path):
    """텍스트 변경 감지 + forward 변환 mock으로 roundtrip 검증."""
    page_id, var_dir = setup_var
    original = tmp_path / "original.mdx"
    improved = tmp_path / "improved.mdx"
    original.write_text("## Title\n\nParagraph.\n")
    improved.write_text("## Title\n\nModified.\n")

    # forward converter를 mock: verify.mdx에 improved_mdx 내용을 그대로 써서 pass 유도
    def mock_forward_convert(patched_xhtml, output_mdx_path, page_id):
        Path(output_mdx_path).write_text("## Title\n\nModified.\n")
        return "## Title\n\nModified.\n"

    with patch('reverse_sync._forward_convert', side_effect=mock_forward_convert):
        result = run_verify(
            page_id=page_id,
            original_mdx_path=str(original),
            improved_mdx_path=str(improved),
        )
    assert result['changes_count'] == 1
    assert result['status'] == 'pass'
    assert result['verification']['exact_match'] is True
    rsync_dir = var_dir / "rsync"
    assert (rsync_dir / "diff.yaml").exists()
    assert (rsync_dir / "mapping.original.yaml").exists()
    assert (rsync_dir / "mapping.verify.yaml").exists()
    assert (rsync_dir / "patched.xhtml").exists()
    assert (rsync_dir / "verify.mdx").exists()
    assert (rsync_dir / "result.yaml").exists()


def test_verify_roundtrip_fail(setup_var, tmp_path):
    """forward 변환 결과가 다르면 status=fail."""
    page_id, var_dir = setup_var
    original = tmp_path / "original.mdx"
    improved = tmp_path / "improved.mdx"
    original.write_text("## Title\n\nParagraph.\n")
    improved.write_text("## Title\n\nModified.\n")

    def mock_forward_convert(patched_xhtml, output_mdx_path, page_id):
        # 다른 내용을 반환하여 roundtrip 실패 유도
        content = "## Title\n\nDifferent output.\n"
        Path(output_mdx_path).write_text(content)
        return content

    with patch('reverse_sync._forward_convert', side_effect=mock_forward_convert):
        result = run_verify(
            page_id=page_id,
            original_mdx_path=str(original),
            improved_mdx_path=str(improved),
        )
    assert result['status'] == 'fail'
    assert result['verification']['exact_match'] is False
    assert result['verification']['diff_report'] != ''
