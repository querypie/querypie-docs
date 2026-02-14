# Markdown Inline Element의 CJK 문자 인접 공백 규칙 분석

> **작성일:** 2026-02-14
> **목적:** reverse-sync verify에서 발생하는 inline element 주변 공백 차이의 원인 분석 및 정규화 전략 수립
> **관련:** [review-verify-fix-proofread-mdx.md](./review-verify-fix-proofread-mdx.md) 유형 1, 2, 3

## 요약

| 요소 | 문법 | flanking 규칙 | CJK 인접 (구두점 없음) | CJK 인접 (구두점 있음) | 공백 필요 여부 |
|------|------|--------------|----------------------|----------------------|--------------|
| Bold | `**text**` | 있음 | PASS | FAIL | 내부에 구두점이 있을 때만 |
| Bold | `__text__` | 있음 (엄격) | FAIL | FAIL | 항상 필요 |
| Italic | `*text*` | 있음 | PASS | FAIL | 내부에 구두점이 있을 때만 |
| Italic | `_text_` | 있음 (엄격) | FAIL | FAIL | 항상 필요 |
| Code | `` `text` `` | 없음 | PASS | PASS | 불필요 |
| Strikethrough | `~~text~~` | 있음 | PASS | FAIL | 내부에 구두점이 있을 때만 |
| Link | `[text](url)` | 없음 | PASS | PASS | 불필요 |
| Image | `![alt](url)` | 없음 | PASS | PASS | 불필요 |

**핵심 결론:**
- **Code span, Link, Image**: 공백 유무가 렌더링에 영향을 주지 않으므로, 공백 차이는 정규화 가능
- **Bold/Italic (`*`/`**`)**: 순수 CJK 텍스트 사이에서는 공백 없이도 정상 동작. 내부에 구두점이 있을 때만 주의 필요
- **Bold/Italic (`_`/`__`)**: CJK 문서에서는 사용하지 말 것

---

## 1. CommonMark Flanking Delimiter 규칙

[CommonMark Spec 0.31.2, Section 6.2](https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis)에서 정의하는 규칙입니다.

### 용어 정의

- **Unicode punctuation character**: Unicode `P`(punctuation) 또는 `S`(symbol) 카테고리의 문자. ASCII `()[].,;:!?` 및 CJK 구두점 `。、「」` 포함
- **Unicode whitespace**: Unicode `Zs` 카테고리 또는 탭, 줄바꿈 등
- **CJK 문자**: hangul, hanzi, kana 등은 punctuation도 whitespace도 아닌 **일반 문자**로 취급됨

### Left-flanking delimiter run (열기 조건)

delimiter run이 다음을 모두 만족:
1. 뒤에 Unicode whitespace가 **아닌** 문자가 옴
2. (2a) 뒤에 Unicode punctuation이 **아닌** 문자가 옴, **또는** (2b) 뒤에 punctuation이 오되, 앞에 whitespace 또는 punctuation이 있음

### Right-flanking delimiter run (닫기 조건)

delimiter run이 다음을 모두 만족:
1. 앞에 Unicode whitespace가 **아닌** 문자가 옴
2. (2a) 앞에 Unicode punctuation이 **아닌** 문자가 옴, **또는** (2b) 앞에 punctuation이 오되, 뒤에 whitespace 또는 punctuation이 있음

---

## 2. 요소별 상세 분석

### 2.1 Bold — asterisk (`**text**`)

`**`는 left-flanking이면 열리고, right-flanking이면 닫힙니다.

| 패턴 | 결과 | 설명 |
|------|------|------|
| `가**나다**라` | PASS | CJK는 일반 문자이므로 flanking 조건 충족 |
| `이것은**강조된 문장**이 있습니다` | PASS | 동일 |
| `가 **나다** 라` | PASS | 공백이 있으면 trivially flanking |
| `**마크다운(Markdown)**은` | **FAIL** | `)` (punct) + `은` (CJK, not punct) → right-flanking 조건 2b 불충족 |
| `**마크다운(Markdown)** 은` | PASS | 공백으로 해결 |
| `**테스트.**다음` | **FAIL** | `.` + CJK → 동일 실패 |
| `이전**(테스트)**다음` | **FAIL** | CJK + `(` → left-flanking 조건 2b 불충족 |

**실패 조건**: delimiter 내부에 구두점이 있고, 외부에 CJK 문자가 바로 붙을 때

### 2.2 Bold — underscore (`__text__`)

`__`는 asterisk보다 엄격한 추가 규칙이 있습니다:
- 열기: left-flanking이면서 (right-flanking이 아니거나, 앞에 punctuation이 있어야)
- 닫기: right-flanking이면서 (left-flanking이 아니거나, 뒤에 punctuation이 있어야)

| 패턴 | 결과 | 설명 |
|------|------|------|
| `이전__강조__다음` | **FAIL** | CJK 사이에서 동시에 left+right flanking → 닫기 불가 |
| `이전 __강조__ 다음` | PASS | 공백으로 해결 |

**결론**: CJK 문서에서 `__`는 사실상 사용 불가. 항상 `**`를 사용해야 합니다.

### 2.3 Italic (`*text*` / `_text_`)

Bold와 동일한 flanking 규칙이 적용됩니다. `*`는 CJK 인접 시 대부분 동작하고, `_`는 동작하지 않습니다.

### 2.4 Code span (`` `text` ``)

[CommonMark Spec Section 6.1](https://spec.commonmark.org/0.31.2/#code-spans) — **flanking 규칙이 없습니다.**

> A code span begins with a backtick string and ends with a backtick string of equal length.

순수하게 백틱 개수 매칭으로만 동작합니다.

| 패턴 | 결과 |
|------|------|
| `` 한국어`코드`텍스트 `` | PASS |
| `` `코드(test)`다음 `` | PASS |
| `` 는`QueryPie`다 `` | PASS |

**공백 유무와 무관하게 항상 동작합니다.**

### 2.5 Strikethrough (`~~text~~`)

[GFM Spec](https://github.github.com/gfm/#strikethrough-extension-) — emphasis와 동일한 flanking 메커니즘을 사용합니다.

| 패턴 | 결과 |
|------|------|
| `한국어~~취소선~~텍스트` | PASS |
| `~~취소(test)~~이후` | **FAIL** |

bold/italic의 `*`/`**`와 동일한 실패 패턴입니다.

### 2.6 Link / Image

[CommonMark Spec Section 6.3, 6.4](https://spec.commonmark.org/0.31.2/#links) — **flanking 규칙이 없습니다.** 대괄호 매칭으로 동작합니다.

| 패턴 | 결과 |
|------|------|
| `한국어[링크](url)텍스트` | PASS |
| `한국어![이미지](url)텍스트` | PASS |

**공백 유무와 무관하게 항상 동작합니다.**

---

## 3. 실패가 발생하는 정확한 조건

다음 **세 가지가 동시에** 충족될 때 렌더링이 실패합니다:

1. Flanking 규칙을 사용하는 delimiter (`*`, `**`, `~~`)
2. Delimiter **내부** 쪽에 Unicode punctuation 문자가 인접
3. Delimiter **외부** 쪽에 CJK 문자가 공백 없이 인접

```
외부(CJK)  delimiter  내부(punct)
    은     **         )Markdown(마크다운**    ← FAIL: 닫기 불가
    은     **         )Markdown(마크다운** ← 공백 추가하면 PASS
```

---

## 4. CommonMark vs GFM vs MDX 차이

| 측면 | CommonMark | GFM | MDX (Nextra 4 / micromark) |
|------|-----------|-----|---------------------------|
| Emphasis flanking | Spec 6.2 정의 | CommonMark 계승 | CommonMark 동일 |
| Strikethrough | 없음 | 동일 flanking 메커니즘 | gfm-strikethrough 확장 |
| Code span | flanking 없음 | 동일 | 동일 |
| Link/Image | flanking 없음 | 동일 | 동일 |
| CJK 친화 확장 | 제안됨, 미채택 | 미구현 | `remark-cjk-friendly` 플러그인 존재 (미설치) |

이 프로젝트(Nextra 4)는 micromark 기반이며, `remark-cjk-friendly` 플러그인은 설치되어 있지 않습니다. 표준 CommonMark/GFM 파싱 동작을 따릅니다.

---

## 5. reverse-sync verifier 정규화 전략 권고

### 안전하게 정규화 가능한 패턴

| 대상 | 패턴 | 근거 |
|------|------|------|
| Code span 주변 공백 | `` `text` `` ↔ `` `text`  `` | flanking 규칙 없음, 렌더링 동일 |
| Link 주변 공백 | `[text](url)` ↔ `[text](url) ` | flanking 규칙 없음, 렌더링 동일 |
| Image 주변 공백 | `![alt](url)` ↔ `![alt](url) ` | flanking 규칙 없음, 렌더링 동일 |
| Trailing whitespace | 줄 끝 공백 | 렌더링에 영향 없음 |

### 주의가 필요한 패턴

| 대상 | 패턴 | 근거 |
|------|------|------|
| Bold/Italic 주변 공백 | `**text**` ↔ ` **text** ` | 대부분 동일하나, 내부 구두점 시 차이 발생 가능 |
| Strikethrough 주변 공백 | `~~text~~` ↔ ` ~~text~~ ` | 동일 |

Bold/Italic의 경우, 정규화 전에 **delimiter 내부의 첫/마지막 문자가 Unicode punctuation인지** 확인해야 합니다:
- punctuation이 없으면 → 공백 제거해도 안전
- punctuation이 있으면 → 공백 유지 필요

---

## 참고 자료

- [CommonMark Spec 0.31.2 — Emphasis](https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis)
- [CommonMark Spec 0.31.2 — Code Spans](https://spec.commonmark.org/0.31.2/#code-spans)
- [CommonMark Issue #650 — Emphasis with CJK punctuation](https://github.com/commonmark/commonmark-spec/issues/650)
- [CommonMark Discussion — Emphasis and East Asian text](https://talk.commonmark.org/t/emphasis-and-east-asian-text/2491)
- [markdown-cjk-friendly 프로젝트](https://github.com/tats-u/markdown-cjk-friendly)
- [GFM Specification](https://github.github.com/gfm/)
