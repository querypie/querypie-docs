import pytest
from reverse_sync.roundtrip_verifier import verify_roundtrip, VerifyResult


def test_identical_mdx_passes():
    result = verify_roundtrip(
        expected_mdx="# Title\n\nParagraph.\n",
        actual_mdx="# Title\n\nParagraph.\n",
    )
    assert result.passed is True
    assert result.diff_report == ""


def test_different_mdx_fails():
    result = verify_roundtrip(
        expected_mdx="# Title\n\nParagraph.\n",
        actual_mdx="# Title\n\nParagraph\n",  # 마침표 누락
    )
    assert result.passed is False
    assert result.diff_report != ""


def test_trailing_whitespace_normalized():
    """trailing whitespace 차이는 정규화되어 통과해야 한다."""
    result = verify_roundtrip(
        expected_mdx="# Title\n\nParagraph. \n",  # trailing space
        actual_mdx="# Title\n\nParagraph.\n",
    )
    assert result.passed is True


def test_diff_report_shows_line_numbers():
    result = verify_roundtrip(
        expected_mdx="line1\nline2\nline3\n",
        actual_mdx="line1\nLINE2\nline3\n",
    )
    assert result.passed is False
    assert "2" in result.diff_report  # 2번째 줄
