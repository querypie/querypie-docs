# Forward Converter CJK Inline Element Spacing

**Goal:** Forward converter의 `<strong>`/`<em>` → `**`/`*` 변환 시, 불필요한 공백을 제거하고 CommonMark flanking 규칙에 따라 필요할 때만 공백을 삽입합니다.

**Status:** 구현 완료 — PR [#839](https://github.com/querypie/querypie-docs/pull/839)

## 핵심 규칙

```
닫는 delimiter (**):
  inner_text 끝이 Unicode punct → "** " (공백 유지, flanking 보호)
  inner_text 끝이 punct 아님     → "**"  (공백 제거)

여는 delimiter (**):
  inner_text 시작이 Unicode punct → " **" (공백 유지, flanking 보호)
  inner_text 시작이 punct 아님     → "**"  (공백 제거)

연속 emphasis delimiter:
  next_sibling이 <strong> 또는 <em> → "** " (충돌 방지)
```

**참고:** [CommonMark Spec 0.31.2 Section 6.2](https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis), GitHub Issue [#733](https://github.com/querypie/querypie-docs/issues/733)

## 구현

- **헬퍼 함수:** [`_is_unicode_punctuation()`](../bin/converter/core.py#L119-L128) — Unicode category P(punctuation) / S(symbol) 판정
- **`<strong>` 핸들러:** [`convert_recursively()` L211-L225](../bin/converter/core.py#L211-L225) — inner text 경계 문자 기반 조건부 공백 삽입
- **`<em>` 핸들러:** [`convert_recursively()` L226-L235](../bin/converter/core.py#L226-L235) — `<strong>`과 동일 로직, `*` delimiter 사용

## 테스트

[`tests/test_forward_converter_inline_spacing.py`](../tests/test_forward_converter_inline_spacing.py) — 16개 테스트

| 클래스 | 테스트 | 검증 내용 |
|--------|--------|-----------|
| `TestIsUnicodePunctuation` | 5건 | ASCII/CJK punct, 한글 조사, 알파벳, 빈 문자열 |
| `TestStrongSpacing` | 8건 | CJK 조사 뒤/앞, 내부 punct, 양쪽 공백, 문단 시작/끝, 연속 strong |
| `TestEmSpacing` | 3건 | CJK 조사 뒤, 내부 punct, 양쪽 공백 |

## E2E 검증 결과

`reverse-sync verify` 원본 실패 케이스(`querypie-acp-community-edition.mdx`)에서:
- `**text** 은` → `**text**은` 문제 **해결** ✅
- 남은 diff: 이중 공백→단일 공백, em/link 주변 공백 감소, trailing newline — 모두 렌더링 무관한 cosmetic 차이 (Issue #733 1단계 verifier 정규화에서 처리)
