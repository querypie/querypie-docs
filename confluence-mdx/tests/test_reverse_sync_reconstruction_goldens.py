"""Phase 2 clean block reconstruction golden 테스트."""
from pathlib import Path

import pytest
import yaml

from reverse_sync.block_diff import diff_blocks
from reverse_sync.mapping_recorder import record_mapping
from mdx_to_storage.parser import parse_mdx_blocks
from reverse_sync.patch_builder import build_patches
from reverse_sync.sidecar import (
    SidecarEntry,
    build_mdx_to_sidecar_index,
    build_sidecar,
    build_xpath_to_mapping,
    generate_sidecar_mapping,
)
from reverse_sync.xhtml_normalizer import normalize_fragment
from reverse_sync.xhtml_patcher import patch_xhtml


TESTCASES = Path(__file__).parent / "testcases"


def _run_pipeline_with_sidecar(xhtml: str, original_mdx: str, improved_mdx: str):
    original_blocks = list(parse_mdx_blocks(original_mdx))
    improved_blocks = list(parse_mdx_blocks(improved_mdx))
    changes, alignment = diff_blocks(original_blocks, improved_blocks)

    mappings = record_mapping(xhtml)
    roundtrip_sidecar = build_sidecar(xhtml, original_mdx)

    sidecar_yaml = generate_sidecar_mapping(xhtml, original_mdx)
    sidecar_data = yaml.safe_load(sidecar_yaml) or {}
    sidecar_entries = [
        SidecarEntry(
            xhtml_xpath=item['xhtml_xpath'],
            xhtml_type=item.get('xhtml_type', ''),
            mdx_blocks=item.get('mdx_blocks', []),
            mdx_line_start=item.get('mdx_line_start', 0),
            mdx_line_end=item.get('mdx_line_end', 0),
        )
        for item in sidecar_data.get('mappings', [])
    ]
    mdx_to_sidecar = build_mdx_to_sidecar_index(sidecar_entries)
    xpath_to_mapping = build_xpath_to_mapping(mappings)

    patches, _ = build_patches(
        changes,
        original_blocks,
        improved_blocks,
        mappings,
        mdx_to_sidecar,
        xpath_to_mapping,
        alignment,
        roundtrip_sidecar=roundtrip_sidecar,
    )
    return patch_xhtml(xhtml, patches)


def _load_testcase(case_id: str):
    case_dir = TESTCASES / case_id
    return {
        'xhtml': (case_dir / 'page.xhtml').read_text(encoding='utf-8'),
        'original_mdx': (case_dir / 'original.mdx').read_text(encoding='utf-8'),
        'improved_mdx': (case_dir / 'improved.mdx').read_text(encoding='utf-8'),
        'expected': (case_dir / 'expected.reverse-sync.patched.xhtml').read_text(
            encoding='utf-8'
        ),
    }


class TestSimpleModifiedGoldens:
    @pytest.fixture(autouse=True)
    def require_testcases(self):
        if not TESTCASES.is_dir():
            pytest.skip("testcases directory not found")

    def test_544211126_paragraph_change(self):
        case = _load_testcase('544211126')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_544178405_paragraph_and_table_change(self):
        case = _load_testcase('544178405')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_1911652402_inline_anchor_paragraph(self):
        case = _load_testcase('1911652402')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_544113141_list_with_trailing_image(self):
        case = _load_testcase('544113141')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_544145591_list_change_with_inline_images(self):
        case = _load_testcase('544145591')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_544377869_paragraph_with_link(self):
        case = _load_testcase('544377869')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_568918170_paragraph_with_link(self):
        case = _load_testcase('568918170')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_692355151_heading_change_with_link_para(self):
        case = _load_testcase('692355151')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_880181257_list_with_nested_image(self):
        case = _load_testcase('880181257')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_883654669_list_with_image(self):
        case = _load_testcase('883654669')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_544112828_list_change(self):
        """544112828: list 아이템 텍스트 변경 (여러개→여러 개, 필요시→필요 시).

        legacy sidecar mapping이 index 80(ul[3])을 커버하지 못할 때
        roundtrip sidecar v3 identity fallback으로 mapping을 복원하고
        replace_fragment로 처리한다.
        """
        case = _load_testcase('544112828')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])

    def test_544379140_callout_and_paragraph_changes(self):
        """544379140: paragraph/list/callout/heading 복합 변경 (시 띄어쓰기 등).

        callout 내부 텍스트 변경 (ADF extension panel) + paragraph/heading 변경.
        """
        case = _load_testcase('544379140')
        result = _run_pipeline_with_sidecar(
            case['xhtml'], case['original_mdx'], case['improved_mdx']
        )
        assert normalize_fragment(result) == normalize_fragment(case['expected'])
