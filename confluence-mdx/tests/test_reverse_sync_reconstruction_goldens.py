"""Phase 2 clean block reconstruction golden 테스트."""
from pathlib import Path

import pytest
import yaml

from reverse_sync.block_diff import diff_blocks
from reverse_sync.mapping_recorder import record_mapping
from reverse_sync.mdx_block_parser import parse_mdx_blocks
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
    original_blocks = parse_mdx_blocks(original_mdx)
    improved_blocks = parse_mdx_blocks(improved_mdx)
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

    patches = build_patches(
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
