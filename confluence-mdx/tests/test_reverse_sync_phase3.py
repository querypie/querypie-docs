"""Phase 3 inline-anchor/list reconstruction tests (v3 sidecar 경로)."""

from pathlib import Path

import pytest

from reverse_sync.block_diff import diff_blocks
from reverse_sync.mapping_recorder import record_mapping
from mdx_to_storage.parser import parse_mdx_blocks
from reverse_sync.patch_builder import build_patches
from reverse_sync.sidecar import (
    build_sidecar,
    build_xpath_to_mapping,
)
from reverse_sync.xhtml_patcher import patch_xhtml


def _build_patched_xhtml(xhtml: str, original_mdx: str, improved_mdx: str):
    """v3 sidecar 경로로 XHTML 패치를 생성한다 (mdx_to_sidecar 없음)."""
    original_blocks = parse_mdx_blocks(original_mdx)
    improved_blocks = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original_blocks, improved_blocks)

    mappings = record_mapping(xhtml)
    roundtrip_sidecar = build_sidecar(xhtml, original_mdx)
    xpath_to_mapping = build_xpath_to_mapping(mappings)

    patches, *_ = build_patches(
        changes,
        original_blocks,
        improved_blocks,
        mappings,
        xpath_to_mapping=xpath_to_mapping,
        alignment=alignment,
        roundtrip_sidecar=roundtrip_sidecar,
    )
    return patches, patch_xhtml(xhtml, patches)


def test_list_with_inline_image_uses_replace_fragment_reconstruction():
    xhtml = (
        '<ul><li><p><strong>Dry Run :</strong> <ac:image ac:inline="true">'
        '<ri:attachment ri:filename="sample.png"></ri:attachment>'
        '</ac:image>버튼을 클릭합니다.</p></li></ul>'
    )
    original_mdx = '* **Dry Run :** <img src="/sample.png" alt="sample.png" />버튼을 클릭합니다.\n'
    improved_mdx = '* **Dry Run :**  <img src="/sample.png" alt="sample.png" />버튼을 다시 클릭합니다.\n'

    patches, patched = _build_patched_xhtml(xhtml, original_mdx, improved_mdx)

    assert len(patches) == 1
    assert patches[0]["action"] == "replace_fragment"
    assert "<ac:image" in patches[0]["new_element_xhtml"]
    assert '<img src="/sample.png"' not in patches[0]["new_element_xhtml"]
    assert "<ac:image ac:inline=\"true\">" in patched
    assert "버튼을 다시 클릭합니다." in patched


class Test544376004:
    @pytest.fixture(autouse=True)
    def require_fixture(self):
        case_dir = Path(__file__).parent / "reverse-sync" / "544376004"
        if not case_dir.is_dir():
            pytest.skip("reverse-sync/544376004 fixture not found")

    def test_preserves_double_space_and_inline_image(self):
        case_dir = Path(__file__).parent / "reverse-sync" / "544376004"
        xhtml = (case_dir / "page.xhtml").read_text(encoding="utf-8")
        original_mdx = (case_dir / "original.mdx").read_text(encoding="utf-8")
        improved_mdx = (case_dir / "improved.mdx").read_text(encoding="utf-8")

        patches, patched = _build_patched_xhtml(xhtml, original_mdx, improved_mdx)

        replace_patches = [patch for patch in patches if patch.get("action") == "replace_fragment"]
        assert replace_patches, "Phase 3 list reconstruction should emit replace_fragment"
        assert any(patch["xhtml_xpath"] == "ul[3]" for patch in replace_patches)
        assert "<strong>Enable Attribute Synchronization :</strong>  LDAP" in patched
        assert '<ac:image ac:alt="image-20241209-124345.png"' in patched
        assert '<img src="/administrator-manual/general/user-management/authentication/integrating-with-ldap/image-20241209-124345.png"' not in patched
