"""reverse_sync/sidecar.py block-level sidecar 스키마 유닛 테스트."""

import json
from pathlib import Path

import pytest

from reverse_sync.sidecar import (
    DocumentEnvelope,
    RoundtripSidecar,
    SidecarBlock,
    build_sidecar,
    load_sidecar,
    sha256_text,
    verify_sidecar_integrity,
    write_sidecar,
)


class TestSidecarSchema:
    def test_create_sidecar(self):
        sidecar = RoundtripSidecar(
            page_id="test",
            blocks=[
                SidecarBlock(
                    block_index=0,
                    xhtml_xpath="h1[1]",
                    xhtml_fragment="<h1>Title</h1>",
                    mdx_content_hash="abc123",
                    mdx_line_range=(1, 1),
                )
            ],
            separators=[],
            document_envelope=DocumentEnvelope(prefix="", suffix="\n"),
        )
        assert sidecar.schema_version == "2"
        assert sidecar.page_id == "test"
        assert len(sidecar.blocks) == 1

    def test_to_dict_roundtrip(self):
        original = RoundtripSidecar(
            page_id="123",
            mdx_sha256="mdx_hash",
            source_xhtml_sha256="xhtml_hash",
            blocks=[
                SidecarBlock(0, "h2[1]", "<h2>A</h2>", "hash_a", (1, 1)),
                SidecarBlock(1, "p[1]", "<p>B</p>", "hash_b", (3, 3)),
            ],
            separators=["\n"],
            document_envelope=DocumentEnvelope(prefix="", suffix="\n"),
        )
        d = original.to_dict()
        restored = RoundtripSidecar.from_dict(d)

        assert restored.schema_version == "2"
        assert restored.page_id == "123"
        assert len(restored.blocks) == 2
        assert restored.blocks[0].xhtml_fragment == "<h2>A</h2>"
        assert restored.blocks[1].mdx_line_range == (3, 3)
        assert restored.separators == ["\n"]
        assert restored.document_envelope.suffix == "\n"

    def test_json_serializable(self):
        sidecar = RoundtripSidecar(
            page_id="test",
            blocks=[
                SidecarBlock(0, "p[1]", "<p>한글</p>", "hash", (1, 1)),
            ],
        )
        json_str = json.dumps(sidecar.to_dict(), ensure_ascii=False)
        data = json.loads(json_str)
        assert data["blocks"][0]["xhtml_fragment"] == "<p>한글</p>"

    def test_reassemble_xhtml(self):
        sidecar = RoundtripSidecar(
            blocks=[
                SidecarBlock(0, "h1[1]", "<h1>A</h1>", "", (1, 1)),
                SidecarBlock(1, "p[1]", "<p>B</p>", "", (3, 3)),
            ],
            separators=["\n"],
            document_envelope=DocumentEnvelope(prefix="", suffix="\n"),
        )
        assert sidecar.reassemble_xhtml() == "<h1>A</h1>\n<p>B</p>\n"


class TestVerifySidecarIntegrity:
    def test_passes_when_equal(self):
        original = "<h1>A</h1>\n<p>B</p>\n"
        sidecar = RoundtripSidecar(
            blocks=[
                SidecarBlock(0, "h1[1]", "<h1>A</h1>", "", (1, 1)),
                SidecarBlock(1, "p[1]", "<p>B</p>", "", (3, 3)),
            ],
            separators=["\n"],
            document_envelope=DocumentEnvelope(prefix="", suffix="\n"),
        )
        verify_sidecar_integrity(sidecar, original)

    def test_fails_when_fragment_wrong(self):
        original = "<h1>A</h1>\n<p>B</p>\n"
        sidecar = RoundtripSidecar(
            blocks=[
                SidecarBlock(0, "h1[1]", "<h1>A</h1>", "", (1, 1)),
                SidecarBlock(1, "p[1]", "<p>WRONG</p>", "", (3, 3)),
            ],
            separators=["\n"],
            document_envelope=DocumentEnvelope(prefix="", suffix="\n"),
        )
        with pytest.raises(ValueError, match="integrity check failed"):
            verify_sidecar_integrity(sidecar, original)

    def test_fails_when_separator_wrong(self):
        original = "<h1>A</h1>\n<p>B</p>"
        sidecar = RoundtripSidecar(
            blocks=[
                SidecarBlock(0, "h1[1]", "<h1>A</h1>", "", (1, 1)),
                SidecarBlock(1, "p[1]", "<p>B</p>", "", (3, 3)),
            ],
            separators=["  "],  # wrong separator
            document_envelope=DocumentEnvelope(prefix="", suffix=""),
        )
        with pytest.raises(ValueError, match="integrity check failed"):
            verify_sidecar_integrity(sidecar, original)


class TestWriteAndLoadSidecar:
    def test_roundtrip(self, tmp_path):
        sidecar = RoundtripSidecar(
            page_id="100",
            mdx_sha256="mhash",
            source_xhtml_sha256="xhash",
            blocks=[
                SidecarBlock(0, "h2[1]", "<h2>Title</h2>", "bhash", (1, 1)),
            ],
            separators=[],
            document_envelope=DocumentEnvelope(prefix="", suffix=""),
        )
        path = tmp_path / "sidecar.json"
        write_sidecar(sidecar, path)

        loaded = load_sidecar(path)
        assert loaded.page_id == "100"
        assert loaded.blocks[0].xhtml_fragment == "<h2>Title</h2>"

    def test_load_rejects_wrong_version(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text('{"schema_version": "1"}', encoding="utf-8")
        with pytest.raises(ValueError, match="expected schema_version=2"):
            load_sidecar(path)


class TestBuildSidecar:
    def test_simple_case(self):
        xhtml = "<h2>Title</h2>\n<p>Body text</p>"
        mdx = "## Title\n\nBody text\n"
        sidecar = build_sidecar(xhtml, mdx, page_id="test")

        assert sidecar.schema_version == "2"
        assert sidecar.page_id == "test"
        assert sidecar.mdx_sha256 == sha256_text(mdx)
        assert sidecar.source_xhtml_sha256 == sha256_text(xhtml)
        assert len(sidecar.blocks) == 2
        assert sidecar.blocks[0].xhtml_fragment == "<h2>Title</h2>"
        assert sidecar.blocks[1].xhtml_fragment == "<p>Body text</p>"
        assert sidecar.separators == ["\n"]


class TestBuildSidecarRealTestcases:
    """실제 testcase 파일에 대한 build + integrity 테스트."""

    @pytest.fixture
    def testcases_dir(self):
        return Path(__file__).parent / "testcases"

    def test_all_testcases_build_and_verify(self, testcases_dir):
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

            assert sidecar.schema_version == "2"
            assert len(sidecar.blocks) > 0
            assert len(sidecar.separators) == len(sidecar.blocks) - 1
            ok += 1

        assert ok >= 21, f"Expected at least 21 testcases, got {ok}"
