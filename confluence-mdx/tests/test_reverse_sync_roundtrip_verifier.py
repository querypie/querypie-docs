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


def test_strict_mode_fails_on_trailing_whitespace():
    """엄격 모드(기본): trailing whitespace 차이도 실패한다."""
    result = verify_roundtrip(
        expected_mdx="# Title\n\nParagraph. \n",  # trailing space
        actual_mdx="# Title\n\nParagraph.\n",
    )
    assert result.passed is False


def test_lenient_mode_normalizes_trailing_whitespace():
    """관대 모드: trailing whitespace 차이는 정규화되어 통과한다."""
    result = verify_roundtrip(
        expected_mdx="# Title\n\nParagraph. \n",  # trailing space
        actual_mdx="# Title\n\nParagraph.\n",
        lenient=True,
    )
    assert result.passed is True


def test_diff_report_shows_line_numbers():
    result = verify_roundtrip(
        expected_mdx="line1\nline2\nline3\n",
        actual_mdx="line1\nLINE2\nline3\n",
    )
    assert result.passed is False
    assert "2" in result.diff_report  # 2번째 줄


def test_strict_mode_fails_on_any_diff():
    """엄격 모드(기본): 정규화 없이 모든 차이를 실패로 처리한다."""
    expected = "line1\nline2 changed\nline3\n"
    actual = "line1 differs\nline2 changed\nline3\n"
    result = verify_roundtrip(
        expected_mdx=expected,
        actual_mdx=actual,
    )
    assert result.passed is False


def test_lenient_mode_normalizes_then_compares_all_lines():
    """관대 모드: 정규화 후 전체 행에서 exact match를 수행한다."""
    # 정규화로 해소되지 않는 차이는 관대 모드에서도 실패
    result = verify_roundtrip(
        expected_mdx="line1\nline2\n",
        actual_mdx="line1 differs\nline2\n",
        lenient=True,
    )
    assert result.passed is False


def test_lenient_mode_normalizes_dates():
    """관대 모드: 한국어 날짜 형식 차이는 정규화되어 통과한다."""
    result = verify_roundtrip(
        expected_mdx="2024년 01월 15일\n",
        actual_mdx="Jan 15, 2024\n",
        lenient=True,
    )
    assert result.passed is True


def test_strict_mode_fails_on_date_format():
    """엄격 모드: 한국어 날짜 형식 차이도 실패한다."""
    result = verify_roundtrip(
        expected_mdx="2024년 01월 15일\n",
        actual_mdx="Jan 15, 2024\n",
    )
    assert result.passed is False
