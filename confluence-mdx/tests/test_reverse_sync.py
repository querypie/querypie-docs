import os
import pytest
from pathlib import Path
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
    """텍스트 변경 감지, rsync/ 하위에 중간 파일 생성."""
    page_id, var_dir = setup_var
    original = tmp_path / "original.mdx"
    improved = tmp_path / "improved.mdx"
    original.write_text("## Title\n\nParagraph.\n")
    improved.write_text("## Title\n\nModified.\n")

    result = run_verify(
        page_id=page_id,
        original_mdx_path=str(original),
        improved_mdx_path=str(improved),
    )
    assert result['changes_count'] == 1
    rsync_dir = var_dir / "rsync"
    assert (rsync_dir / "diff.yaml").exists()
    assert (rsync_dir / "mapping.original.yaml").exists()
    assert (rsync_dir / "mapping.verify.yaml").exists()
    assert (rsync_dir / "patched.xhtml").exists()
    assert (rsync_dir / "result.yaml").exists()
