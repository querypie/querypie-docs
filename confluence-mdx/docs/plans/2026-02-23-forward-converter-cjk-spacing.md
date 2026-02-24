# Forward Converter CJK Inline Element Spacing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Forward converter의 `<strong>`/`<em>` → `**`/`*` 변환 시, 불필요한 공백을 제거하고 CommonMark flanking 규칙에 따라 필요할 때만 공백을 삽입합니다.

**Architecture:** `SingleLineParser.convert_recursively()`에서 `<strong>`, `<em>` 처리 시, `markdown_of_children(node).strip()` 결과의 첫/끝 문자가 Unicode punctuation인지 확인하여 delimiter 앞/뒤 공백 삽입 여부를 결정합니다. 내부 텍스트만 검사하면 되므로 sibling 접근이 필요 없습니다.

**Tech Stack:** Python 3, BeautifulSoup4, unicodedata

**핵심 규칙:**

```
닫는 delimiter (**):
  inner_text 끝이 Unicode punct → "** " (공백 유지, flanking 보호)
  inner_text 끝이 punct 아님     → "**"  (공백 제거)

여는 delimiter (**):
  inner_text 시작이 Unicode punct → " **" (공백 유지, flanking 보호)
  inner_text 시작이 punct 아님     → "**"  (공백 제거)
```

**참고:** [CommonMark Spec 0.31.2 Section 6.2](https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis), GitHub Issue #733

---

### Task 1: `_is_unicode_punctuation` 헬퍼 함수 추가 및 테스트

**Files:**
- Create: `tests/test_forward_converter_inline_spacing.py`
- Modify: `bin/converter/core.py:199-211`

**Step 1: 테스트 파일 생성 — `_is_unicode_punctuation` 헬퍼 테스트**

```python
"""forward converter의 inline element CJK 공백 최적화 테스트."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from converter.core import _is_unicode_punctuation


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
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `cd /Users/jk/workspace/querypie-docs/confluence-mdx && python -m pytest tests/test_forward_converter_inline_spacing.py::TestIsUnicodePunctuation -v`
Expected: FAIL — `ImportError: cannot import name '_is_unicode_punctuation'`

**Step 3: `_is_unicode_punctuation` 함수 구현**

`bin/converter/core.py`의 `SingleLineParser` 클래스 앞(모듈 레벨)에 추가:

```python
def _is_unicode_punctuation(ch: str) -> bool:
    """CommonMark spec의 Unicode punctuation 판정.

    Unicode general category가 P(punctuation) 또는 S(symbol)이면 True.
    ASCII punctuation도 포함된다.
    """
    if not ch:
        return False
    cat = unicodedata.category(ch[0])
    return cat.startswith('P') or cat.startswith('S')
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `cd /Users/jk/workspace/querypie-docs/confluence-mdx && python -m pytest tests/test_forward_converter_inline_spacing.py::TestIsUnicodePunctuation -v`
Expected: PASS

**Step 5: 커밋하지 않음 — Task 2와 함께 커밋**

---

### Task 2: `<strong>` 공백 로직 변경 및 테스트

**Files:**
- Modify: `bin/converter/core.py:199-207`
- Modify: `tests/test_forward_converter_inline_spacing.py`

**Step 1: `<strong>` 변환 테스트 추가**

`tests/test_forward_converter_inline_spacing.py`에 추가:

```python
from bs4 import BeautifulSoup
from converter.core import SingleLineParser


def _parse_p(html: str) -> str:
    """HTML <p> 요소를 SingleLineParser로 변환한다."""
    soup = BeautifulSoup(html, 'html.parser')
    p = soup.find('p')
    return SingleLineParser(p).as_markdown


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
        assert '사용법은 **(중요)**' in result

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
        """연속 <strong> — 사이에 공백 삽입."""
        result = _parse_p(
            '<p><strong>AAA</strong><strong>BBB</strong></p>')
        # 두 delimiter가 붙으면 **AAA****BBB** 가 되어 파싱 깨짐.
        # 기존처럼 공백이 들어가는 게 안전.
        assert '**AAA** **BBB**' in result
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `cd /Users/jk/workspace/querypie-docs/confluence-mdx && python -m pytest tests/test_forward_converter_inline_spacing.py::TestStrongSpacing -v`
Expected: FAIL — `test_strong_followed_by_cjk_particle` 등 실패 (현재는 항상 공백 삽입)

**Step 3: `<strong>` 변환 코드 수정**

`bin/converter/core.py` lines 199-207을 수정:

```python
        elif node.name in ['strong']:
            # CORRECTION: <strong> is ignored in headings
            if node.parent.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                for child in node.children:
                    self.convert_recursively(child)
            else:
                inner = self.markdown_of_children(node).strip()
                # CommonMark flanking delimiter 규칙:
                # inner 시작/끝이 Unicode punctuation이면 공백 필요 (flanking 보호)
                open_sp = " " if _is_unicode_punctuation(inner[0]) else ""  if inner else ""
                close_sp = " " if _is_unicode_punctuation(inner[-1]) else "" if inner else ""
                self.markdown_lines.append(f"{open_sp}**")
                self.markdown_lines.append(inner)
                self.markdown_lines.append(f"**{close_sp}")
```

주의: `inner`가 빈 문자열인 경우(실제로는 거의 없음)를 방어해야 합니다.
안전한 구현:

```python
                inner = self.markdown_of_children(node).strip()
                open_sp = " " if inner and _is_unicode_punctuation(inner[0]) else ""
                close_sp = " " if inner and _is_unicode_punctuation(inner[-1]) else ""
                self.markdown_lines.append(f"{open_sp}**")
                self.markdown_lines.append(inner)
                self.markdown_lines.append(f"**{close_sp}")
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `cd /Users/jk/workspace/querypie-docs/confluence-mdx && python -m pytest tests/test_forward_converter_inline_spacing.py::TestStrongSpacing -v`
Expected: PASS

**Step 5: 커밋하지 않음 — Task 3과 함께 커밋**

---

### Task 3: `<em>` 공백 로직 변경 및 테스트

**Files:**
- Modify: `bin/converter/core.py:208-211`
- Modify: `tests/test_forward_converter_inline_spacing.py`

**Step 1: `<em>` 변환 테스트 추가**

`tests/test_forward_converter_inline_spacing.py`에 추가:

```python
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
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `cd /Users/jk/workspace/querypie-docs/confluence-mdx && python -m pytest tests/test_forward_converter_inline_spacing.py::TestEmSpacing -v`
Expected: FAIL

**Step 3: `<em>` 변환 코드 수정**

`bin/converter/core.py` lines 208-211을 수정:

```python
        elif node.name in ['em']:
            inner = self.markdown_of_children(node).strip()
            open_sp = " " if inner and _is_unicode_punctuation(inner[0]) else ""
            close_sp = " " if inner and _is_unicode_punctuation(inner[-1]) else ""
            self.markdown_lines.append(f"{open_sp}*")
            self.markdown_lines.append(inner)
            self.markdown_lines.append(f"*{close_sp}")
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `cd /Users/jk/workspace/querypie-docs/confluence-mdx && python -m pytest tests/test_forward_converter_inline_spacing.py -v`
Expected: 모든 테스트 PASS

**Step 5: 커밋**

```bash
git add bin/converter/core.py tests/test_forward_converter_inline_spacing.py
git commit -m "feat(converter): forward converter의 **/* delimiter CJK 공백 최적화

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: 기존 테스트 확인 및 E2E 검증

**Files:**
- 없음 (검증만)

**Step 1: 기존 테스트 전체 실행**

Run: `cd /Users/jk/workspace/querypie-docs/confluence-mdx && python -m pytest tests/ -v --tb=short`
Expected: 기존 테스트 모두 PASS

**Step 2: 실패한 원본 케이스 재검증**

Run: `cd /Users/jk/workspace/querypie-docs/confluence-mdx && python bin/reverse_sync_cli.py verify split/ko-proofread-20260221-installation:src/content/ko/installation/querypie-acp-community-edition.mdx`
Expected: PASS (또는 trailing newline만 남은 1건 차이)

**Step 3: 실패 시 디버깅**

기존 테스트가 실패하면, 해당 테스트의 기대값이 `" **text** "` 패턴을 하드코딩하고 있을 수 있습니다.
기대값을 새로운 공백 규칙에 맞게 업데이트합니다.

**Step 4: 커밋 (테스트 기대값 수정이 있었을 경우)**

```bash
git add -u
git commit -m "fix(tests): forward converter CJK 공백 변경에 따른 기대값 업데이트

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
