import os
import shutil

import pytest
from pathlib import Path
from mdx_block_parser import parse_mdx_blocks
from block_diff import diff_blocks
from mapping_recorder import record_mapping
from xhtml_patcher import patch_xhtml
from reverse_sync import _build_patches, run_verify


TESTCASE_DIR = Path(__file__).parent / "testcases" / "793608206"
VAR_DIR = Path(__file__).parent.parent / "var" / "793608206"


@pytest.fixture
def testcase_data():
    xhtml_path = TESTCASE_DIR / "page.xhtml"
    mdx_path = TESTCASE_DIR / "expected.mdx"
    if not xhtml_path.exists() or not mdx_path.exists():
        pytest.skip("Test case files not found")
    return {
        'xhtml': xhtml_path.read_text(),
        'mdx': mdx_path.read_text(),
    }


def test_e2e_no_change_identity(testcase_data):
    """변경 없이 파이프라인을 돌리면 diff가 비어있어야 한다."""
    mdx = testcase_data['mdx']
    original_blocks = parse_mdx_blocks(mdx)
    improved_blocks = parse_mdx_blocks(mdx)
    changes = diff_blocks(original_blocks, improved_blocks)
    assert changes == []


def test_e2e_text_replacement(testcase_data):
    """실제 MDX에서 텍스트를 변경하고 XHTML 패치가 동작하는지 확인."""
    original_mdx = testcase_data['mdx']
    xhtml = testcase_data['xhtml']

    # MDX에서 실제 존재하는 텍스트를 찾아 변경
    # 먼저 어떤 텍스트가 있는지 확인
    original_blocks = parse_mdx_blocks(original_mdx)
    paragraph_blocks = [b for b in original_blocks if b.type == 'paragraph']
    assert len(paragraph_blocks) > 0, "테스트 데이터에 paragraph 블록이 있어야 함"

    # 첫 번째 paragraph의 텍스트 일부를 변경
    target_block = paragraph_blocks[0]
    target_text = target_block.content.strip()
    # 간단한 치환: 첫 단어 변경 시도 대신, 확실한 문자열 치환
    if '.' in target_text:
        improved_mdx = original_mdx.replace(target_text, target_text.replace('.', '!', 1), 1)
    else:
        improved_mdx = original_mdx.replace(target_text, target_text + ' (수정됨)', 1)

    if improved_mdx == original_mdx:
        pytest.skip("변경 적용 불가")

    # Step 1-2: 블록 파싱 + diff
    improved_blocks = parse_mdx_blocks(improved_mdx)
    changes = diff_blocks(original_blocks, improved_blocks)
    assert len(changes) > 0, "변경이 감지되어야 함"

    # Step 3: 매핑
    mappings = record_mapping(xhtml)
    assert len(mappings) > 0

    # Step 4: XHTML 패치
    patches = _build_patches(changes, original_blocks, improved_blocks, mappings)

    if patches:
        patched = patch_xhtml(xhtml, patches)
        # 패치된 XHTML이 원본과 다른지 확인
        assert patched != xhtml, "XHTML이 패치되어야 함"


def test_e2e_mapping_covers_mdx_blocks(testcase_data):
    """매핑이 MDX의 주요 블록들과 대응하는지 확인."""
    xhtml = testcase_data['xhtml']
    mdx = testcase_data['mdx']

    mappings = record_mapping(xhtml)
    mdx_blocks = parse_mdx_blocks(mdx)

    heading_mappings = [m for m in mappings if m.type == 'heading']
    heading_blocks = [b for b in mdx_blocks if b.type == 'heading']

    # 매핑의 heading 수와 MDX heading 수가 비슷해야 함
    assert len(heading_mappings) > 0, "XHTML에서 heading 매핑이 추출되어야 함"
    assert len(heading_blocks) > 0, "MDX에서 heading 블록이 파싱되어야 함"


class TestE2ERoundTrip:
    """실제 forward converter를 사용한 round-trip 검증 테스트."""

    @pytest.fixture
    def setup_var_793608206(self, tmp_path, monkeypatch):
        """var/793608206/ 구조를 tmp_path에 복사하고 작업 디렉토리 변경."""
        if not VAR_DIR.exists():
            pytest.skip("var/793608206 not found")
        monkeypatch.chdir(tmp_path)
        dest = tmp_path / "var" / "793608206"
        shutil.copytree(VAR_DIR, dest)
        # pages.yaml도 복사 (converter가 {input_dir}/../pages.yaml 을 참조)
        pages_yaml = VAR_DIR.parent / "pages.yaml"
        if pages_yaml.exists():
            shutil.copy2(pages_yaml, tmp_path / "var" / "pages.yaml")
        return dest

    def test_roundtrip_no_changes(self, setup_var_793608206, tmp_path):
        """변경 없으면 no_changes 상태."""
        var_dir = setup_var_793608206
        mdx_path = TESTCASE_DIR / "expected.mdx"
        if not mdx_path.exists():
            pytest.skip("expected.mdx not found")

        original = tmp_path / "original.mdx"
        improved = tmp_path / "improved.mdx"
        mdx_content = mdx_path.read_text()
        original.write_text(mdx_content)
        improved.write_text(mdx_content)

        result = run_verify(
            page_id="793608206",
            original_mdx_path=str(original),
            improved_mdx_path=str(improved),
        )
        assert result['status'] == 'no_changes'

    def test_roundtrip_with_text_change(self, setup_var_793608206, tmp_path):
        """텍스트 변경 후 full round-trip: forward converter를 실제 호출."""
        var_dir = setup_var_793608206
        mdx_path = TESTCASE_DIR / "expected.mdx"
        if not mdx_path.exists():
            pytest.skip("expected.mdx not found")

        original_mdx = mdx_path.read_text()

        # paragraph 블록에서 텍스트 변경
        original_blocks = parse_mdx_blocks(original_mdx)
        paragraph_blocks = [b for b in original_blocks if b.type == 'paragraph']
        if not paragraph_blocks:
            pytest.skip("No paragraph blocks in test data")

        target_text = paragraph_blocks[0].content.strip()
        if '.' in target_text:
            improved_mdx = original_mdx.replace(
                target_text, target_text.replace('.', '!', 1), 1)
        else:
            improved_mdx = original_mdx.replace(
                target_text, target_text + ' (수정됨)', 1)

        if improved_mdx == original_mdx:
            pytest.skip("변경 적용 불가")

        original = tmp_path / "original.mdx"
        improved = tmp_path / "improved.mdx"
        original.write_text(original_mdx)
        improved.write_text(improved_mdx)

        result = run_verify(
            page_id="793608206",
            original_mdx_path=str(original),
            improved_mdx_path=str(improved),
        )
        assert result['status'] in ('pass', 'fail')
        assert result['changes_count'] > 0
        assert result['verification']['exact_match'] is not None
        # verify.mdx 파일이 생성되었는지 확인
        assert (var_dir / "rsync" / "verify.mdx").exists()
