"""reverse_sync/sidecar.py schema v3 — reconstruction metadata 및 identity helper 테스트.

Phase 1 게이트:
- SidecarBlock.reconstruction 필드 직렬화/역직렬화
- build_sidecar가 reconstruction metadata를 생성
- v2 파일 하위 호환 로드
- hash + line_range 기반 identity helper
- 기존 21개 testcase build + integrity 유지
"""

import json
from pathlib import Path

import pytest

from reverse_sync.sidecar import (
    DocumentEnvelope,
    ROUNDTRIP_SCHEMA_VERSION,
    RoundtripSidecar,
    SidecarBlock,
    build_block_identity_index,
    build_sidecar,
    find_block_by_identity,
    load_sidecar,
    sha256_text,
    write_sidecar,
)

TESTCASES_DIR = Path(__file__).parent / "testcases"


# ---------------------------------------------------------------------------
# Schema v3 기본 동작
# ---------------------------------------------------------------------------

class TestSchemaV3:
    def test_schema_version_is_3(self):
        assert ROUNDTRIP_SCHEMA_VERSION == "3"

    def test_sidecar_block_reconstruction_field(self):
        block = SidecarBlock(
            block_index=0,
            xhtml_xpath="p[1]",
            xhtml_fragment="<p>text</p>",
            reconstruction={
                "kind": "paragraph",
                "old_plain_text": "text",
                "anchors": [],
            },
        )
        assert block.reconstruction is not None
        assert block.reconstruction["kind"] == "paragraph"

    def test_sidecar_block_reconstruction_none(self):
        block = SidecarBlock(
            block_index=0,
            xhtml_xpath="macro-code[1]",
            xhtml_fragment="<ac:structured-macro ...>",
        )
        assert block.reconstruction is None

    def test_to_dict_includes_reconstruction(self):
        sidecar = RoundtripSidecar(
            page_id="test",
            blocks=[
                SidecarBlock(
                    block_index=0,
                    xhtml_xpath="p[1]",
                    xhtml_fragment="<p>A</p>",
                    reconstruction={"kind": "paragraph", "old_plain_text": "A", "anchors": []},
                ),
            ],
        )
        d = sidecar.to_dict()
        assert "reconstruction" in d["blocks"][0]
        assert d["blocks"][0]["reconstruction"]["kind"] == "paragraph"

    def test_to_dict_omits_reconstruction_when_none(self):
        sidecar = RoundtripSidecar(
            page_id="test",
            blocks=[
                SidecarBlock(
                    block_index=0,
                    xhtml_xpath="macro-code[1]",
                    xhtml_fragment="<code>x</code>",
                ),
            ],
        )
        d = sidecar.to_dict()
        assert "reconstruction" not in d["blocks"][0]

    def test_from_dict_with_reconstruction(self):
        data = {
            "schema_version": "3",
            "page_id": "test",
            "blocks": [
                {
                    "block_index": 0,
                    "xhtml_xpath": "p[1]",
                    "xhtml_fragment": "<p>A</p>",
                    "reconstruction": {
                        "kind": "paragraph",
                        "old_plain_text": "A",
                        "anchors": [
                            {
                                "anchor_id": "p[1]/ac:image[1]",
                                "raw_xhtml": "<ac:image />",
                                "old_plain_offset": 2,
                                "affinity": "after",
                            }
                        ],
                    },
                }
            ],
            "separators": [],
            "document_envelope": {"prefix": "", "suffix": ""},
        }
        sidecar = RoundtripSidecar.from_dict(data)
        block = sidecar.blocks[0]
        assert block.reconstruction is not None
        assert len(block.reconstruction["anchors"]) == 1
        assert block.reconstruction["anchors"][0]["old_plain_offset"] == 2

    def test_from_dict_without_reconstruction(self):
        """v2 형식 데이터는 reconstruction=None으로 로드된다."""
        data = {
            "schema_version": "2",
            "page_id": "test",
            "blocks": [
                {
                    "block_index": 0,
                    "xhtml_xpath": "p[1]",
                    "xhtml_fragment": "<p>A</p>",
                }
            ],
            "separators": [],
            "document_envelope": {"prefix": "", "suffix": ""},
        }
        sidecar = RoundtripSidecar.from_dict(data)
        assert sidecar.blocks[0].reconstruction is None

    def test_json_roundtrip_with_reconstruction(self):
        sidecar = RoundtripSidecar(
            page_id="test",
            blocks=[
                SidecarBlock(
                    block_index=0,
                    xhtml_xpath="ul[1]",
                    xhtml_fragment="<ul><li>X</li></ul>",
                    reconstruction={
                        "kind": "list",
                        "old_plain_text": "X",
                        "items": [{"item_xpath": "ul[1]/li[1]", "old_plain_text": "X"}],
                    },
                ),
            ],
        )
        json_str = json.dumps(sidecar.to_dict(), ensure_ascii=False)
        restored = RoundtripSidecar.from_dict(json.loads(json_str))
        assert restored.blocks[0].reconstruction["kind"] == "list"
        assert len(restored.blocks[0].reconstruction["items"]) == 1


# ---------------------------------------------------------------------------
# v2 하위 호환 로드
# ---------------------------------------------------------------------------

class TestV2Compatibility:
    def test_load_v2_file(self, tmp_path):
        """v2 schema 파일이 정상 로드된다."""
        data = {
            "schema_version": "2",
            "page_id": "compat",
            "blocks": [
                {
                    "block_index": 0,
                    "xhtml_xpath": "p[1]",
                    "xhtml_fragment": "<p>Old</p>",
                    "mdx_content_hash": "h",
                    "mdx_line_range": [1, 1],
                    "lost_info": {},
                }
            ],
            "separators": [],
            "document_envelope": {"prefix": "", "suffix": ""},
        }
        path = tmp_path / "v2.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        sidecar = load_sidecar(path)
        assert sidecar.schema_version == "2"
        assert sidecar.blocks[0].reconstruction is None

    def test_load_v3_file(self, tmp_path):
        """v3 schema 파일이 정상 로드된다."""
        data = {
            "schema_version": "3",
            "page_id": "new",
            "blocks": [
                {
                    "block_index": 0,
                    "xhtml_xpath": "p[1]",
                    "xhtml_fragment": "<p>New</p>",
                    "reconstruction": {"kind": "paragraph", "old_plain_text": "New"},
                }
            ],
            "separators": [],
            "document_envelope": {"prefix": "", "suffix": ""},
        }
        path = tmp_path / "v3.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        sidecar = load_sidecar(path)
        assert sidecar.schema_version == "3"
        assert sidecar.blocks[0].reconstruction is not None

    def test_load_v1_rejected(self, tmp_path):
        """v1은 거부된다."""
        path = tmp_path / "v1.json"
        path.write_text('{"schema_version": "1"}', encoding="utf-8")
        with pytest.raises(ValueError, match="expected schema_version in"):
            load_sidecar(path)

    def test_write_load_roundtrip_v3(self, tmp_path):
        sidecar = RoundtripSidecar(
            page_id="rt",
            blocks=[
                SidecarBlock(
                    block_index=0,
                    xhtml_xpath="p[1]",
                    xhtml_fragment="<p>RT</p>",
                    mdx_content_hash="h",
                    mdx_line_range=(5, 5),
                    reconstruction={"kind": "paragraph", "old_plain_text": "RT", "anchors": []},
                ),
            ],
            separators=[],
            document_envelope=DocumentEnvelope(),
        )
        path = tmp_path / "sidecar.json"
        write_sidecar(sidecar, path)
        loaded = load_sidecar(path)
        assert loaded.blocks[0].reconstruction == {"kind": "paragraph", "old_plain_text": "RT", "anchors": []}


# ---------------------------------------------------------------------------
# Block identity helper
# ---------------------------------------------------------------------------

class TestBlockIdentity:
    @pytest.fixture
    def sidecar_with_duplicates(self):
        return RoundtripSidecar(
            blocks=[
                SidecarBlock(0, "p[1]", "<p>A</p>", "hash_a", (1, 1)),
                SidecarBlock(1, "p[2]", "<p>B</p>", "hash_b", (3, 3)),
                SidecarBlock(2, "p[3]", "<p>A</p>", "hash_a", (5, 5)),  # duplicate hash
                SidecarBlock(3, "p[4]", "<p>C</p>", "hash_c", (7, 7)),
            ],
        )

    def test_unique_hash_found(self, sidecar_with_duplicates):
        index = build_block_identity_index(sidecar_with_duplicates)
        result = find_block_by_identity("hash_b", (3, 3), index)
        assert result is not None
        assert result.block_index == 1

    def test_unique_hash_found_regardless_of_line_range(self, sidecar_with_duplicates):
        """hash가 유일하면 line_range가 달라도 찾는다."""
        index = build_block_identity_index(sidecar_with_duplicates)
        result = find_block_by_identity("hash_b", (999, 999), index)
        assert result is not None
        assert result.block_index == 1

    def test_duplicate_hash_disambiguated_by_line_range(self, sidecar_with_duplicates):
        index = build_block_identity_index(sidecar_with_duplicates)
        result1 = find_block_by_identity("hash_a", (1, 1), index)
        result2 = find_block_by_identity("hash_a", (5, 5), index)
        assert result1 is not None and result1.block_index == 0
        assert result2 is not None and result2.block_index == 2

    def test_duplicate_hash_no_matching_line_range(self, sidecar_with_duplicates):
        index = build_block_identity_index(sidecar_with_duplicates)
        result = find_block_by_identity("hash_a", (99, 99), index)
        assert result is None

    def test_nonexistent_hash(self, sidecar_with_duplicates):
        index = build_block_identity_index(sidecar_with_duplicates)
        result = find_block_by_identity("nonexistent", (1, 1), index)
        assert result is None

    def test_empty_hash_skipped(self):
        sidecar = RoundtripSidecar(
            blocks=[SidecarBlock(0, "p[1]", "<p>A</p>", "", (1, 1))],
        )
        index = build_block_identity_index(sidecar)
        assert len(index) == 0

    def test_identity_index_groups_correctly(self, sidecar_with_duplicates):
        index = build_block_identity_index(sidecar_with_duplicates)
        assert len(index["hash_a"]) == 2
        assert len(index["hash_b"]) == 1
        assert len(index["hash_c"]) == 1


# ---------------------------------------------------------------------------
# build_sidecar reconstruction metadata
# ---------------------------------------------------------------------------

class TestBuildSidecarReconstructionMetadata:
    def test_simple_case_has_reconstruction(self):
        xhtml = "<h2>Title</h2>\n<p>Body text</p>"
        mdx = "## Title\n\nBody text\n"
        sidecar = build_sidecar(xhtml, mdx, page_id="test")

        assert sidecar.schema_version == "3"
        # heading block
        h_block = sidecar.blocks[0]
        assert h_block.reconstruction is not None
        assert h_block.reconstruction["kind"] == "heading"
        assert h_block.reconstruction["old_plain_text"] == "Title"
        assert h_block.reconstruction["anchors"] == []
        # paragraph block
        p_block = sidecar.blocks[1]
        assert p_block.reconstruction is not None
        assert p_block.reconstruction["kind"] == "paragraph"
        assert p_block.reconstruction["old_plain_text"] == "Body text"

    def test_code_block_no_reconstruction(self):
        xhtml = (
            '<ac:structured-macro ac:name="code">'
            '<ac:parameter ac:name="language">python</ac:parameter>'
            '<ac:plain-text-body><![CDATA[x = 1]]></ac:plain-text-body>'
            '</ac:structured-macro>'
        )
        mdx = "```python\nx = 1\n```\n"
        sidecar = build_sidecar(xhtml, mdx, page_id="test")
        assert sidecar.blocks[0].reconstruction is None

    def test_list_block_has_reconstruction(self):
        xhtml = "<ul><li><p>Item 1</p></li><li><p>Item 2</p></li></ul>"
        mdx = "- Item 1\n- Item 2\n"
        sidecar = build_sidecar(xhtml, mdx, page_id="test")
        block = sidecar.blocks[0]
        assert block.reconstruction is not None
        assert block.reconstruction["kind"] == "list"
        assert "items" in block.reconstruction


# ---------------------------------------------------------------------------
# 실제 testcase에서 build + integrity + reconstruction 검증
# ---------------------------------------------------------------------------

class TestBuildSidecarRealTestcasesV3:
    @pytest.fixture
    def testcases_dir(self):
        return TESTCASES_DIR

    def test_all_testcases_build_and_verify(self, testcases_dir):
        """21개 testcase 모두 schema v3로 build + integrity pass."""
        if not testcases_dir.is_dir():
            pytest.skip("testcases directory not found")

        ok = 0
        for case_dir in sorted(testcases_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            xhtml_path = case_dir / "page.xhtml"
            mdx_path = case_dir / "expected.mdx"
            if not xhtml_path.exists() or not mdx_path.exists():
                continue

            xhtml = xhtml_path.read_text(encoding="utf-8")
            mdx = mdx_path.read_text(encoding="utf-8")
            sidecar = build_sidecar(xhtml, mdx, page_id=case_dir.name)

            assert sidecar.schema_version == "3"
            assert len(sidecar.blocks) > 0
            assert len(sidecar.separators) == len(sidecar.blocks) - 1
            ok += 1

        assert ok >= 21, f"Expected at least 21 testcases, got {ok}"

    def test_reconstruction_metadata_present(self, testcases_dir):
        """실제 testcase에서 reconstruction이 생성되는지 확인."""
        case_dir = testcases_dir / "544113141"
        if not case_dir.exists():
            pytest.skip("testcase 544113141 not found")

        xhtml = (case_dir / "page.xhtml").read_text(encoding="utf-8")
        mdx = (case_dir / "expected.mdx").read_text(encoding="utf-8")
        sidecar = build_sidecar(xhtml, mdx, page_id="544113141")

        # heading block은 reconstruction 있어야 함
        heading_blocks = [b for b in sidecar.blocks if b.xhtml_xpath.startswith("h")]
        assert len(heading_blocks) > 0
        for b in heading_blocks:
            assert b.reconstruction is not None
            assert b.reconstruction["kind"] == "heading"
            assert len(b.reconstruction["old_plain_text"]) > 0

    def test_identity_index_from_real_testcase(self, testcases_dir):
        """실제 testcase에서 identity index가 올바르게 구축된다."""
        case_dir = testcases_dir / "544113141"
        if not case_dir.exists():
            pytest.skip("testcase 544113141 not found")

        xhtml = (case_dir / "page.xhtml").read_text(encoding="utf-8")
        mdx = (case_dir / "expected.mdx").read_text(encoding="utf-8")
        sidecar = build_sidecar(xhtml, mdx, page_id="544113141")

        index = build_block_identity_index(sidecar)

        # 모든 hash가 있는 block이 인덱스에 있어야 함
        hashed_blocks = [b for b in sidecar.blocks if b.mdx_content_hash]
        total_in_index = sum(len(v) for v in index.values())
        assert total_in_index == len(hashed_blocks)

        # 각 block을 identity로 다시 찾을 수 있어야 함
        for b in hashed_blocks:
            found = find_block_by_identity(b.mdx_content_hash, b.mdx_line_range, index)
            assert found is not None, f"Failed to find block {b.block_index} by identity"
            assert found.block_index == b.block_index
