import pytest
from reverse_sync.roundtrip_verifier import (
    verify_roundtrip,
    VerifyResult,
    _normalize_consecutive_spaces_in_text,
    _normalize_br_space,
    _normalize_link_text_spacing,
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

    def test_code_block_with_surrounding_text(self):
        """코드 블록 전후 일반 텍스트의 이중 공백은 정규화되고, 블록 내부는 보존된다."""
        text = "**bold**  before\n```\ncode  inside\n```\n**bold**  after"
        expected = "**bold** before\n```\ncode  inside\n```\n**bold** after"
        assert _normalize_consecutive_spaces_in_text(text) == expected

    def test_inline_code_span_spaces_collapsed(self):
        """인라인 code span 내부 연속 공백도 정규화 대상이다 (HTML 렌더링과 일치)."""
        assert _normalize_consecutive_spaces_in_text("`code  here`") == "`code here`"

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


# --- _normalize_link_text_spacing 단위 테스트 ---


class TestNormalizeLinkTextSpacing:
    def test_spaces_inside_brackets_removed(self):
        """링크 텍스트 앞뒤 공백이 제거된다."""
        assert _normalize_link_text_spacing(
            "[ **General** ](url)") == "[**General**](url)"

    def test_bold_link_with_spaces_normalized(self):
        """* [ **text** ](url) 패턴이 정규화된다."""
        assert _normalize_link_text_spacing(
            "* [ **Security** ](company-management/security) : desc") == \
            "* [**Security**](company-management/security) : desc"

    def test_no_spaces_unchanged(self):
        """공백 없는 링크는 변경되지 않는다."""
        assert _normalize_link_text_spacing(
            "[**General**](url)") == "[**General**](url)"

    def test_regular_link_unchanged(self):
        """일반 텍스트 링크는 변경되지 않는다."""
        assert _normalize_link_text_spacing(
            "[some text](url)") == "[some text](url)"

    def test_multiple_links_all_normalized(self):
        """여러 링크가 모두 정규화된다."""
        result = _normalize_link_text_spacing(
            "* [ **A** ](a) and [ **B** ](b)")
        assert result == "* [**A**](a) and [**B**](b)"


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


def test_minimal_norm_link_spacing_passes():
    """링크 텍스트 공백 차이는 strict 모드에서도 정규화된다.

    재현: CI 543948978 패턴 — improved.mdx의 [ **General** ](url)와
    FC가 생성한 verify.mdx의 [**General**](url)가 동일하게 취급된다.
    """
    result = verify_roundtrip(
        expected_mdx="* [ **General** ](company-management/general) : desc\n",
        actual_mdx="* [**General**](company-management/general) : desc\n",
    )
    assert result.passed is True


def test_minimal_norm_link_spacing_multiple_items():
    """여러 링크 항목의 공백이 정규화된다."""
    result = verify_roundtrip(
        expected_mdx=(
            "* [ **General** ](url1) : desc1\n"
            "* [ **Security** ](url2) : desc2\n"
        ),
        actual_mdx=(
            "* [**General**](url1) : desc1\n"
            "* [**Security**](url2) : desc2\n"
        ),
    )
    assert result.passed is True


def test_strict_mode_still_fails_on_trailing_ws():
    """strict 모드: trailing whitespace 차이는 여전히 실패한다 (최소 정규화 대상 아님)."""
    result = verify_roundtrip(
        expected_mdx="Paragraph. \n",
        actual_mdx="Paragraph.\n",
    )
    assert result.passed is False


def test_minimal_norm_sentence_breaks_passes_for_plain_paragraph():
    """FC가 같은 문단의 문장을 두 줄로 나눠도 strict 비교에서 허용한다.

    재현: reverse-sync 544382659
    XHTML patch 결과는 의미상 맞지만 verify.mdx가 split_into_sentences()로
    한 문단을 두 줄로 분리해 strict verify가 실패했다.
    """
    result = verify_roundtrip(
        expected_mdx=(
            "관리자는 apiGroups, resources, namespace, name을 통해 사용자가 접근할 수 있는 "
            "리소스 범위를 지정하고 verb를 통해 어떤 API를 호출할 수 있는지 지정합니다. "
            "리소스 범위를 잘 설정했더라도 verb 묶음을 제대로 설정하지 않으면 Tool 사용이 어렵습니다.\n"
        ),
        actual_mdx=(
            "관리자는 apiGroups, resources, namespace, name을 통해 사용자가 접근할 수 있는 "
            "리소스 범위를 지정하고 verb를 통해 어떤 API를 호출할 수 있는지 지정합니다.\n"
            "리소스 범위를 잘 설정했더라도 verb 묶음을 제대로 설정하지 않으면 Tool 사용이 어렵습니다.\n"
        ),
    )
    assert result.passed is True


def test_minimal_norm_internal_confluence_link_variants_pass():
    """같은 QueryPie Confluence 페이지에 대한 URL 표기 차이를 strict 비교에서 허용한다.

    재현: reverse-sync 862093313
    reverse-sync는 <ac:link>의 Confluence page identity를 보존하지만,
    forward convert 결과는 `/spaces/<space>/overview` 형식으로 canonicalize된다.
    """
    result = verify_roundtrip(
        expected_mdx=(
            "(이후 `3rd Party Tool` 이라고 표기합니다.) "
            "구체적인 사례는 이 문서를 참조하세요: "
            "[Supported 3rd Party Tools (KO)]"
            "(https://querypie.atlassian.net/wiki/spaces/QCP/pages/919404587)\n"
        ),
        actual_mdx=(
            "(이후 `3rd Party Tool` 이라고 표기합니다.) "
            "구체적인 사례는 이 문서를 참조하세요: "
            "[Supported 3rd Party Tools (KO)]"
            "(https://querypie.atlassian.net/wiki/spaces/QCP/overview)\n"
        ),
    )
    assert result.passed is True


def test_minimal_norm_sentence_breaks_passes_after_closing_paren():
    """문장이 `.)`로 끝나도 다음 일반 텍스트 줄과 결합한다."""
    result = verify_roundtrip(
        expected_mdx=(
            "(이후 `3rd Party Tool` 이라고 표기합니다.) "
            "구체적인 사례는 이 문서를 참조하세요: "
            "[Supported 3rd Party Tools (KO)]"
            "(https://querypie.atlassian.net/wiki/spaces/QCP/overview)\n"
        ),
        actual_mdx=(
            "(이후 `3rd Party Tool` 이라고 표기합니다.)\n"
            "구체적인 사례는 이 문서를 참조하세요: "
            "[Supported 3rd Party Tools (KO)]"
            "(https://querypie.atlassian.net/wiki/spaces/QCP/overview)\n"
        ),
    )
    assert result.passed is True
