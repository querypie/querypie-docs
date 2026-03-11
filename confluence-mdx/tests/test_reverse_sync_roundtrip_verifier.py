import pytest
from reverse_sync.roundtrip_verifier import (
    verify_roundtrip,
    VerifyResult,
    _normalize_consecutive_spaces_in_text,
    _normalize_br_space,
)


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


# --- _normalize_consecutive_spaces_in_text 단위 테스트 ---


class TestNormalizeConsecutiveSpaces:
    def test_double_space_collapsed(self):
        """이중 공백이 단일 공백으로 정규화된다."""
        assert _normalize_consecutive_spaces_in_text("**bold**  :") == "**bold** :"

    def test_leading_indent_preserved(self):
        """줄 앞 들여쓰기는 보존된다."""
        assert _normalize_consecutive_spaces_in_text("    * item") == "    * item"

    def test_code_block_preserved(self):
        """코드 블록 내부 연속 공백은 보존된다."""
        text = "```\ncode  with  spaces\n```"
        assert _normalize_consecutive_spaces_in_text(text) == text

    def test_single_space_unchanged(self):
        """단일 공백은 변경되지 않는다."""
        assert _normalize_consecutive_spaces_in_text("a b c") == "a b c"

    def test_three_spaces_collapsed_to_one(self):
        """3개 이상의 공백도 단일 공백으로 정규화된다."""
        assert _normalize_consecutive_spaces_in_text("a   b") == "a b"


# --- _normalize_br_space 단위 테스트 ---


class TestNormalizeBrSpace:
    def test_space_before_br_removed(self):
        """<br/> 앞의 공백이 제거된다."""
        assert _normalize_br_space("text <br/>") == "text<br/>"

    def test_multiple_spaces_before_br_removed(self):
        """<br/> 앞의 여러 공백도 제거된다."""
        assert _normalize_br_space("text   <br/>") == "text<br/>"

    def test_br_with_space_inside_tag(self):
        """<br /> 형식도 처리한다."""
        assert _normalize_br_space("text <br />") == "text<br />"

    def test_no_space_before_br_unchanged(self):
        """<br/> 앞에 공백 없으면 변경하지 않는다."""
        assert _normalize_br_space("text<br/>") == "text<br/>"

    def test_text_after_br_unchanged(self):
        """<br/> 뒤의 텍스트는 영향받지 않는다."""
        assert _normalize_br_space("a <br/>b") == "a<br/>b"


# --- verify_roundtrip에서의 최소 정규화 동작 ---


def test_minimal_norm_double_space_passes():
    """이중 공백 차이는 strict 모드에서도 정규화된다 (forward converter 특성)."""
    result = verify_roundtrip(
        expected_mdx="**bold**  : value\n",
        actual_mdx="**bold** : value\n",
    )
    assert result.passed is True


def test_minimal_norm_br_space_passes():
    """<br/> 앞 공백 차이는 strict 모드에서도 정규화된다."""
    result = verify_roundtrip(
        expected_mdx="item <br/>next\n",
        actual_mdx="item<br/>next\n",
    )
    assert result.passed is True


def test_strict_mode_still_fails_on_trailing_ws():
    """strict 모드: trailing whitespace 차이는 여전히 실패한다 (최소 정규화 대상 아님)."""
    result = verify_roundtrip(
        expected_mdx="Paragraph. \n",
        actual_mdx="Paragraph.\n",
    )
    assert result.passed is False
