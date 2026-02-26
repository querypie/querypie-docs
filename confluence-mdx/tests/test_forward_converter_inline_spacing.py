"""forward converter의 inline element CJK 공백 최적화 테스트."""
from bs4 import BeautifulSoup
from converter.core import SingleLineParser, _is_unicode_punctuation


def _parse_p(html: str) -> str:
    """HTML <p> 요소를 SingleLineParser로 변환한다."""
    soup = BeautifulSoup(html, 'html.parser')
    p = soup.find('p')
    return SingleLineParser(p).as_markdown


class TestIsUnicodePunctuation:
    """CommonMark spec의 Unicode punctuation 판정 테스트."""

    def test_ascii_punctuation(self):
        for ch in '()[]{}.,;:!?-/':
            assert _is_unicode_punctuation(ch), f'{ch!r} should be punctuation'

    def test_cjk_punctuation(self):
        for ch in '。、「」（）':
            assert _is_unicode_punctuation(ch), f'{ch!r} should be punctuation'

    def test_cjk_not_punctuation(self):
        for ch in '은를이가에서':
            assert not _is_unicode_punctuation(ch), f'{ch!r} should NOT be punctuation'

    def test_ascii_alnum_not_punctuation(self):
        for ch in 'azAZ09':
            assert not _is_unicode_punctuation(ch), f'{ch!r} should NOT be punctuation'

    def test_empty_string(self):
        assert not _is_unicode_punctuation('')


class TestStrongSpacing:
    """<strong> → ** 변환의 공백 처리 테스트."""

    def test_strong_followed_by_cjk_particle(self):
        """내부 끝이 punct 아님 + 외부 CJK → 공백 없음."""
        result = _parse_p('<p><strong>Community Edition</strong>은 좋습니다.</p>')
        assert '**Community Edition**은' in result

    def test_strong_preceded_by_cjk(self):
        """내부 시작이 punct 아님 + 외부 CJK → 공백 없음."""
        result = _parse_p('<p>기능은<strong>QueryPie</strong>에서 제공합니다.</p>')
        assert '기능은**QueryPie**에서' in result

    def test_strong_inner_ends_with_punct(self):
        """내부 끝이 punct → 공백 유지."""
        result = _parse_p('<p><strong>마크다운(Markdown)</strong>은 좋습니다.</p>')
        assert '**마크다운(Markdown)** 은' in result

    def test_strong_inner_starts_with_punct(self):
        """내부 시작이 punct → 공백 유지."""
        result = _parse_p('<p>사용법은<strong>(중요)</strong>입니다.</p>')
        assert '사용법은 **(중요)** 입니다.' in result

    def test_strong_between_spaces(self):
        """양쪽 공백 — 기존 동작 유지."""
        result = _parse_p('<p>이것은 <strong>강조</strong> 텍스트입니다.</p>')
        assert '이것은 **강조** 텍스트입니다.' in result

    def test_strong_at_start_of_paragraph(self):
        """문단 첫 요소 — 선행 공백 없음."""
        result = _parse_p('<p><strong>QueryPie</strong>는 도구입니다.</p>')
        assert result.startswith('**QueryPie**는')

    def test_strong_at_end_of_paragraph(self):
        """문단 끝 요소 — 후행 공백 없음."""
        result = _parse_p('<p>이것은<strong>QueryPie</strong></p>')
        assert result.endswith('**QueryPie**')

    def test_consecutive_strong(self):
        """연속 <strong> — delimiter 충돌 방지를 위해 공백 삽입."""
        result = _parse_p(
            '<p><strong>AAA</strong><strong>BBB</strong></p>')
        assert '**AAA** **BBB**' in result

    def test_strong_inner_ends_with_punct_followed_by_space_and_text(self):
        """내부 끝이 punct이고 다음 텍스트가 이미 공백으로 시작하면 이중 공백 방지.

        재현 시나리오:
          patched XHTML: <strong>보세요.</strong> 🔎
          현상: close_sp(" ") + text node(" 🔎") → **보세요.**  🔎 (이중 공백)
          기대: **보세요.** 🔎 (단일 공백)

        페이지 544375505 reverse-sync verify 실패 원인.
        """
        result = _parse_p('<p><strong>보세요.</strong> 🔎</p>')
        assert '**보세요.** 🔎' in result, f'expected single space, got: {result!r}'
        assert '**보세요.**  🔎' not in result, f'double space found in: {result!r}'


class TestEmSpacing:
    """<em> → * 변환의 공백 처리 테스트."""

    def test_em_followed_by_cjk_particle(self):
        result = _parse_p('<p><em>기울임</em>은 중요합니다.</p>')
        assert '*기울임*은' in result

    def test_em_inner_ends_with_punct(self):
        result = _parse_p('<p><em>참고(note)</em>를 확인하세요.</p>')
        assert '*참고(note)* 를' in result

    def test_em_between_spaces(self):
        result = _parse_p('<p>이것은 <em>기울임</em> 텍스트입니다.</p>')
        assert '이것은 *기울임* 텍스트입니다.' in result
