"""reverse_sync/rehydrator.py 유닛 테스트."""

from pathlib import Path

import pytest

from reverse_sync.rehydrator import (
    SpliceResult,
    rehydrate_xhtml,
    rehydrate_xhtml_from_files,
    sidecar_matches_mdx,
    splice_rehydrate_xhtml,
)
from reverse_sync.sidecar import build_sidecar, write_sidecar


def test_sidecar_matches_mdx_true_when_hash_same():
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx = "## Title\n\nBody\n"
    sidecar = build_sidecar(xhtml, mdx)
    assert sidecar_matches_mdx(mdx, sidecar) is True


def test_rehydrate_xhtml_returns_raw_when_hash_matches():
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx = "## Title\n\nBody\n"
    sidecar = build_sidecar(xhtml, mdx)
    assert rehydrate_xhtml(mdx, sidecar) == xhtml


def test_rehydrate_xhtml_fallback_when_hash_mismatch():
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx_original = "## Title\n\nBody\n"
    mdx_changed = "## Changed\n\nBody\n"
    sidecar = build_sidecar(xhtml, mdx_original)

    called = {}

    def _fallback(text: str) -> str:
        called["mdx"] = text
        return "<x-fallback />"

    restored = rehydrate_xhtml(mdx_changed, sidecar, fallback_renderer=_fallback)
    assert restored == "<x-fallback />"
    assert called["mdx"] == mdx_changed


def test_rehydrate_xhtml_from_files(tmp_path):
    mdx_path = tmp_path / "expected.mdx"
    sidecar_path = tmp_path / "expected.roundtrip.json"
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx = "## Title\n\nBody\n"
    mdx_path.write_text(mdx, encoding="utf-8")
    write_sidecar(build_sidecar(xhtml, mdx, page_id="100"), sidecar_path)

    restored = rehydrate_xhtml_from_files(mdx_path, sidecar_path)
    assert restored == xhtml


# ---------------------------------------------------------------------------
# Splice rehydrator 테스트
# ---------------------------------------------------------------------------


class TestSpliceRehydrateXhtml:
    def test_all_blocks_matched_returns_byte_equal(self):
        xhtml = "<h1>Title</h1>\n<p>Body</p>"
        mdx = "## Title\n\nBody\n"
        sidecar = build_sidecar(xhtml, mdx)

        result = splice_rehydrate_xhtml(mdx, sidecar)

        assert result.xhtml == xhtml
        assert result.matched_count == 2
        assert result.emitted_count == 0
        assert result.total_blocks == 2

    def test_returns_splice_result_type(self):
        xhtml = "<h1>A</h1>"
        mdx = "## A\n"
        sidecar = build_sidecar(xhtml, mdx)

        result = splice_rehydrate_xhtml(mdx, sidecar)
        assert isinstance(result, SpliceResult)

    def test_block_details_contain_sidecar_method(self):
        xhtml = "<h1>Title</h1>\n<p>Body</p>"
        mdx = "## Title\n\nBody\n"
        sidecar = build_sidecar(xhtml, mdx)

        result = splice_rehydrate_xhtml(mdx, sidecar)

        assert len(result.block_details) == 2
        assert all(d["method"] == "sidecar" for d in result.block_details)

    def test_changed_block_uses_emitter(self):
        xhtml = "<h1>Title</h1>\n<p>Body</p>"
        mdx_original = "## Title\n\nBody\n"
        mdx_changed = "## Changed\n\nBody\n"
        sidecar = build_sidecar(xhtml, mdx_original)

        result = splice_rehydrate_xhtml(mdx_changed, sidecar)

        assert result.matched_count == 1  # "Body" 블록만 매칭
        assert result.emitted_count == 1  # "Changed" 블록은 emitter
        assert result.block_details[0]["method"] == "emitter"
        assert result.block_details[1]["method"] == "sidecar"

    def test_preserves_envelope(self):
        xhtml = "<h1>Only</h1>\n"
        mdx = "## Only\n"
        sidecar = build_sidecar(xhtml, mdx)

        result = splice_rehydrate_xhtml(mdx, sidecar)
        assert result.xhtml == xhtml


class TestSpliceRealTestcases:
    """실제 testcase에 대한 forced-splice byte-equal 검증."""

    @pytest.fixture
    def testcases_dir(self):
        return Path(__file__).parent / "testcases"

    def test_all_testcases_splice_byte_equal(self, testcases_dir):
        if not testcases_dir.is_dir():
            pytest.skip("testcases directory not found")

        ok = 0
        failures = []
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

            result = splice_rehydrate_xhtml(mdx, sidecar)

            if result.xhtml == xhtml:
                ok += 1
            else:
                # 최초 불일치 위치 진단
                for j, (c1, c2) in enumerate(zip(result.xhtml, xhtml)):
                    if c1 != c2:
                        failures.append(
                            f"{case_dir.name}: mismatch at offset {j}, "
                            f"matched={result.matched_count}/{result.total_blocks}, "
                            f"emitted={result.emitted_count}"
                        )
                        break
                else:
                    failures.append(
                        f"{case_dir.name}: length diff "
                        f"(got {len(result.xhtml)}, expected {len(xhtml)})"
                    )

        assert ok >= 21, (
            f"Expected 21/21 splice byte-equal, got {ok}. "
            f"Failures:\n" + "\n".join(failures)
        )
