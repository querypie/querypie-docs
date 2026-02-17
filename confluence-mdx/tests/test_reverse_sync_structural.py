"""구조적 변경 (블록 추가/삭제) E2E 테스트."""
from reverse_sync.mdx_block_parser import parse_mdx_blocks
from reverse_sync.block_diff import diff_blocks
from reverse_sync.mapping_recorder import record_mapping
from reverse_sync.patch_builder import build_patches
from reverse_sync.xhtml_patcher import patch_xhtml
from reverse_sync.sidecar import (
    SidecarEntry, build_mdx_to_sidecar_index, build_xpath_to_mapping,
)


def _run_pipeline(original_mdx, improved_mdx, xhtml, sidecar_entries):
    """테스트용 간이 파이프라인."""
    original_blocks = parse_mdx_blocks(original_mdx)
    improved_blocks = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original_blocks, improved_blocks)

    mappings = record_mapping(xhtml)
    mdx_to_sidecar = build_mdx_to_sidecar_index(sidecar_entries)
    xpath_to_mapping = build_xpath_to_mapping(mappings)

    patches = build_patches(
        changes, original_blocks, improved_blocks,
        mappings, mdx_to_sidecar, xpath_to_mapping, alignment)
    return patch_xhtml(xhtml, patches)


class TestStructuralParagraphAdd:
    def test_paragraph_added_between_existing(self):
        xhtml = '<h1>Title</h1><p>Para one</p>'
        original_mdx = '# Title\n\nPara one\n'
        improved_mdx = '# Title\n\nNew para\n\nPara one\n'
        sidecar = [
            SidecarEntry(xhtml_xpath='h1[1]', xhtml_type='heading',
                         mdx_blocks=[0]),
            SidecarEntry(xhtml_xpath='p[1]', xhtml_type='paragraph',
                         mdx_blocks=[2]),
        ]
        result = _run_pipeline(original_mdx, improved_mdx, xhtml, sidecar)
        assert '<p>New para</p>' in result or 'New para' in result
        assert '<h1>Title</h1>' in result
        assert 'Para one' in result


class TestStructuralParagraphDelete:
    def test_paragraph_deleted(self):
        xhtml = '<h1>Title</h1><p>Para one</p><p>Para two</p>'
        original_mdx = '# Title\n\nPara one\n\nPara two\n'
        improved_mdx = '# Title\n\nPara two\n'
        sidecar = [
            SidecarEntry(xhtml_xpath='h1[1]', xhtml_type='heading',
                         mdx_blocks=[0]),
            SidecarEntry(xhtml_xpath='p[1]', xhtml_type='paragraph',
                         mdx_blocks=[2]),
            SidecarEntry(xhtml_xpath='p[2]', xhtml_type='paragraph',
                         mdx_blocks=[4]),
        ]
        result = _run_pipeline(original_mdx, improved_mdx, xhtml, sidecar)
        assert 'Para one' not in result
        assert 'Para two' in result


class TestStructuralCodeBlockAdd:
    def test_code_block_added(self):
        xhtml = '<h1>Title</h1><p>Description</p>'
        original_mdx = '# Title\n\nDescription\n'
        improved_mdx = '# Title\n\nDescription\n\n```python\nprint("hi")\n```\n'
        sidecar = [
            SidecarEntry(xhtml_xpath='h1[1]', xhtml_type='heading',
                         mdx_blocks=[0]),
            SidecarEntry(xhtml_xpath='p[1]', xhtml_type='paragraph',
                         mdx_blocks=[2]),
        ]
        result = _run_pipeline(original_mdx, improved_mdx, xhtml, sidecar)
        assert 'ac:structured-macro' in result or 'print' in result


class TestStructuralMixedChanges:
    def test_add_delete_modify_combined(self):
        xhtml = '<h1>Title</h1><p>Keep this</p><p>Delete this</p><p>Modify this</p>'
        original_mdx = '# Title\n\nKeep this\n\nDelete this\n\nModify this\n'
        improved_mdx = '# Title\n\nKeep this\n\nNew para\n\nModify THIS\n'
        sidecar = [
            SidecarEntry(xhtml_xpath='h1[1]', xhtml_type='heading',
                         mdx_blocks=[0]),
            SidecarEntry(xhtml_xpath='p[1]', xhtml_type='paragraph',
                         mdx_blocks=[2]),
            SidecarEntry(xhtml_xpath='p[2]', xhtml_type='paragraph',
                         mdx_blocks=[4]),
            SidecarEntry(xhtml_xpath='p[3]', xhtml_type='paragraph',
                         mdx_blocks=[6]),
        ]
        result = _run_pipeline(original_mdx, improved_mdx, xhtml, sidecar)
        assert 'Keep this' in result
        assert 'Delete this' not in result
        assert 'New para' in result
