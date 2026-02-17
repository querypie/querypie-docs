"""reverse_sync/byte_verify.py 유닛 테스트."""

from pathlib import Path

import pytest

from reverse_sync.byte_verify import (
    SpliceVerificationResult,
    verify_case_dir,
    verify_case_dir_splice,
)
from reverse_sync.sidecar import build_sidecar, write_sidecar


def test_verify_case_dir_passes_when_sidecar_raw_matches_page(tmp_path):
    case = tmp_path / "100"
    case.mkdir()
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx = "## Title\n\nBody\n"
    (case / "expected.mdx").write_text(mdx, encoding="utf-8")
    (case / "page.xhtml").write_text(xhtml, encoding="utf-8")
    write_sidecar(build_sidecar(xhtml, mdx, page_id="100"), case / "expected.roundtrip.json")

    result = verify_case_dir(case)
    assert result.passed is True
    assert result.reason == "byte_equal"
    assert result.first_mismatch_offset == -1


def test_verify_case_dir_fails_when_sidecar_missing(tmp_path):
    case = tmp_path / "100"
    case.mkdir()
    (case / "expected.mdx").write_text("## T\n", encoding="utf-8")
    (case / "page.xhtml").write_text("<h1>T</h1>", encoding="utf-8")

    result = verify_case_dir(case)
    assert result.passed is False
    assert result.reason.startswith("sidecar_missing")


def test_verify_case_dir_fails_with_mismatch_offset(tmp_path):
    case = tmp_path / "100"
    case.mkdir()
    xhtml_original = "<h1>Title</h1><p>Body</p>"
    xhtml_different = "<h1>Title</h1><p>Body!</p>"
    mdx = "## Title\n\nBody\n"
    (case / "expected.mdx").write_text(mdx, encoding="utf-8")
    (case / "page.xhtml").write_text(xhtml_different, encoding="utf-8")
    write_sidecar(build_sidecar(xhtml_original, mdx, page_id="100"), case / "expected.roundtrip.json")

    result = verify_case_dir(case)
    assert result.passed is False
    assert result.reason == "byte_mismatch"
    assert result.first_mismatch_offset >= 0


# ---------------------------------------------------------------------------
# Forced-splice 검증 테스트
# ---------------------------------------------------------------------------


def test_verify_case_dir_splice_passes(tmp_path):
    case = tmp_path / "100"
    case.mkdir()
    xhtml = "<h1>Title</h1><p>Body</p>"
    mdx = "## Title\n\nBody\n"
    (case / "expected.mdx").write_text(mdx, encoding="utf-8")
    (case / "page.xhtml").write_text(xhtml, encoding="utf-8")
    write_sidecar(build_sidecar(xhtml, mdx, page_id="100"), case / "expected.roundtrip.json")

    result = verify_case_dir_splice(case)
    assert isinstance(result, SpliceVerificationResult)
    assert result.passed is True
    assert result.reason == "byte_equal_splice"
    assert result.matched_count == 2
    assert result.emitted_count == 0


def test_verify_case_dir_splice_fails_when_sidecar_missing(tmp_path):
    case = tmp_path / "100"
    case.mkdir()
    (case / "expected.mdx").write_text("## T\n", encoding="utf-8")
    (case / "page.xhtml").write_text("<h1>T</h1>", encoding="utf-8")

    result = verify_case_dir_splice(case)
    assert result.passed is False
    assert result.reason.startswith("sidecar_missing")


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
            sidecar_path = case_dir / "expected.roundtrip.json"
            if not xhtml_path.exists() or not mdx_path.exists():
                continue
            if not sidecar_path.exists():
                continue

            result = verify_case_dir_splice(case_dir)
            if result.passed:
                ok += 1
            else:
                failures.append(
                    f"{result.case_id}: {result.reason} "
                    f"at offset {result.first_mismatch_offset}, "
                    f"matched={result.matched_count}/{result.total_blocks}"
                )

        assert ok >= 21, (
            f"Expected 21/21 splice byte-equal, got {ok}. "
            f"Failures:\n" + "\n".join(failures)
        )
