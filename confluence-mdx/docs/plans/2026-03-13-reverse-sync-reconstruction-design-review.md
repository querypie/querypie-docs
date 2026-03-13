# Reverse Sync 전면 재구성 설계 — 검토 평가 결과 (v5)

> 검토 대상: `2026-03-13-reverse-sync-reconstruction-design.md`
> 검토일: 2026-03-13
> 검토 기준 버전: PR #913 head `33fa095e56cb26766995b3930d3616a58559685e`
> 검토 관점: 설계 타당성, 코드베이스 정합성, TDD 관점의 테스트 확보 가능성

---

## 결론

문서가 제시하는 **큰 방향**은 타당하다.

- patch heuristic을 계속 누적하는 대신 MDX → XHTML 재구성 경로로 수렴시키려는 방향은 맞다
- list를 sidecar flat entry + `children` ref 구조로 재설계한 점도 기존 `list_items` 계열 설계보다 낫다
- callout 내부를 paragraph fallback이 아니라 재귀 파싱으로 처리하겠다는 판단도 적절하다

하지만 현재 문서는 **최종 설계 승인 가능 상태는 아니다**.

핵심 이유는 두 가지다.

1. paragraph 재구성의 핵심 불변식 하나가 현재 코드베이스 기준으로 성립하지 않는다
2. 테스트 설계가 일부 레벨에서 실제 fixture/loader/API와 맞지 않아, TDD 게이트로 바로 작동하지 않는다

즉, 방향은 맞지만 아직 "구현 전에 바로 들어가도 되는 설계" 수준은 아니다.

---

## 주요 지적사항

### C-1. ParagraphEditSequence의 핵심 불변식이 현재 설계대로는 성립하지 않는다

**심각도:** Critical

**문서 위치:**

- Section 3.1.1 `_process_paragraph()`
- Section 3.1.1 `reconstruct_paragraph()`

**문서의 주장:**

- XHTML 조각을 누적한 뒤 `convert_inline()`을 적용하면 `TextSegment.text`가 MDX 텍스트 조각이 된다
- 따라서 `TextSegments`를 이어 붙인 값이 `old_mdx_text`와 정확히 일치한다
- 그 결과 `old_text == old_mdx_text`를 강한 불변식으로 둘 수 있다

**문제:**

현재 코드베이스의 `convert_inline()`은 **MDX → XHTML 변환기**다. XHTML 조각을 넣었을 때 XHTML을 MDX로 역변환해주지 않는다.

예를 들어:

```python
convert_inline("<strong>bold</strong>") == "<strong>bold</strong>"
```

즉 `_process_paragraph()`가 아래처럼 동작하면:

```python
cursor_xhtml += str(child)   # "<strong>bold</strong>"
children.append({
    "kind": "text",
    "text": convert_inline(cursor_xhtml),
})
```

`TextSegment.text`는 `"**bold**"`가 아니라 `"<strong>bold</strong>"`로 남는다.

그러면 문서가 전제한:

```python
old_text == old_mdx_text
```

는 서식이 포함된 paragraph에서 곧바로 깨진다.

**왜 중요한가:**

이 불변식이 깨지면 `map_anchor_positions()` 이전 단계에서 좌표계가 이미 무너진다. 즉 paragraph 설계의 중심축이 성립하지 않는다.

**필요한 수정 방향:**

둘 중 하나를 명확히 선택해야 한다.

1. `TextSegment.text`를 "MDX 텍스트"가 아니라 "XHTML/normalized plain 기준 텍스트"로 바꾸고, `reconstruct_paragraph()` 비교식도 그 좌표계에 맞게 다시 설계한다
2. XHTML inline fragment를 실제로 MDX inline text로 역변환하는 별도 함수/규칙을 설계하고, 그 함수의 지원 범위를 테스트로 고정한다

현재 문서는 2번을 이미 해결된 것처럼 쓰고 있지만, 실제로는 해결되지 않았다.

---

### C-2. Level 1 / Level 2 테스트의 oracle 정의가 현재 fixture와 맞지 않는다

**심각도:** High

**문서 위치:**

- Section 8.4 Level 1
- Section 8.5 Level 2

**문서의 주장:**

- `mapping.yaml`에서 각 블록의 `xhtml_text`를 읽어 재구성 결과와 비교할 수 있다
- `load_mapping()`으로 이를 로드할 수 있다

**문제:**

현재 실제 `mapping.yaml`은 `xhtml_xpath`, `xhtml_type`, `mdx_blocks` 중심이며, 문서가 예제로 사용하는 `entry.xhtml_text`는 존재하지 않는다. 실제 loader인 `load_sidecar_mapping()`도 그 필드를 읽지 않는다.

즉 문서의 예제:

```python
mapping = load_mapping(...)
assert normalize_xhtml(reconstructed) == normalize_xhtml(entry.xhtml_text)
```

는 현재 리포지토리 기준으로 성립하지 않는다.

**왜 중요한가:**

TDD에서 가장 중요한 것은 "무엇을 expected로 비교할 것인가"다. 그런데 Level 1/2의 expected source가 현재 정의되지 않았다.

이 상태에서는:

- 테스트 파일 이름은 정할 수 있어도
- 실제 assertion이 무엇을 비교해야 하는지
- 어느 loader를 쓸지
- 원본 fragment를 어디서 읽어올지

가 정해지지 않은 셈이다.

**필요한 수정 방향:**

둘 중 하나를 선택해야 한다.

1. `mapping.yaml` 스키마를 확장해 테스트 oracle로 쓸 원본 XHTML fragment를 명시적으로 넣는다
2. Level 1/2의 oracle을 `mapping.yaml`이 아니라 `page.xhtml` 또는 `expected.roundtrip.json`에서 xpath 기반으로 추출하는 방식으로 다시 설계한다

현재 리포지토리 자산을 고려하면 2번이 더 현실적이다.

---

### C-3. `normalize_xhtml()` 설계가 현재 저장소 전제와 맞지 않는다

**심각도:** High

**문서 위치:**

- Section 8.4 `normalize_xhtml()`

**문서의 주장:**

- `lxml.etree.fromstring()`으로 fragment를 파싱해 정규화한다

**문제 1: 의존성 누락**

현재 저장소의 `requirements.txt`에는 `lxml`이 없다.

**문제 2: Confluence fragment 파싱 전제 미정의**

문서의 테스트 대상에는 `ac:image`, `ri:attachment` 같은 namespace prefix가 포함된 XHTML fragment가 많다. 이들은 namespace 선언 없이 XML parser에 그대로 넣으면 실패할 가능성이 높다.

이는 단순 구현 디테일이 아니라, Level 1/2 비교 함수가 실제 테스트 데이터에 적용 가능한지 여부를 가르는 전제다.

**왜 중요한가:**

비교 함수가 실제 fragment를 파싱하지 못하면 Level 1/2는 시작 자체가 안 된다.

**필요한 수정 방향:**

다음 중 하나를 문서에 명시해야 한다.

1. `lxml`을 새 테스트 의존성으로 도입하고, Confluence namespace wrapper를 어떻게 붙일지 명확히 규정한다
2. XML 정규화 대신 BeautifulSoup 기반 canonicalization 혹은 byte/string comparison 규칙으로 축소한다

현재 문서는 이 전제를 해결하지 않은 채 테스트가 가능한 것처럼 서술하고 있다.

---

## Warning

### W-1. Level 3의 `mdx_content_hash` 단독 매칭은 중복 content 페이지에서 오검증 위험이 있다

**문서 위치:**

- Section 8.6 Level 3

문서는 아래 방식으로 MDX 블록을 찾는다.

```python
hash_to_block = {sha256_text(b.content): b for b in mdx_blocks if b.content}
mdx_block = hash_to_block.get(sb.mdx_content_hash)
```

하지만 실제 testcase에는 **동일한 non-empty content를 가진 블록이 반복되는 페이지가 이미 존재한다**.

예:

- `tests/testcases/1454342158`
- `tests/testcases/544375741`
- `tests/testcases/544145591`

이 경우 dict comprehension은 마지막 블록으로 덮어쓰므로, 다른 위치의 동일 content 블록과 잘못 매칭될 수 있다.

**영향:**

- 테스트가 실패해야 할 케이스를 통과시키거나
- 반대로 맞는 구현을 오검증으로 실패시킬 수 있다

**권장 수정:**

- key를 `mdx_content_hash` 단독이 아니라 `(mdx_content_hash, mdx_line_range)` 또는 "hash -> list of candidate blocks"로 바꾸고
- sidecar block의 순서나 line range를 함께 사용해 disambiguation 하도록 문서화해야 한다

---

### W-2. 테스트 실행 순서가 Level 0를 건너뛰고 있어 TDD 루프가 약하다

**문서 위치:**

- Section 8.3
- Section 8.8

문서는 테스트 수준 구조에서 Level 0를 가장 먼저 둔다.

```text
Level 0 -> Level 1 -> Level 2 -> Level 3 -> Level 4
```

그런데 실제 실행 순서 섹션은 Step 1을 Level 1부터 시작한다.

이렇게 되면 helper 단위의 red/green이 빠지고, 실패 원인이:

- helper 버그인지
- block renderer 버그인지
- document assembly 버그인지

를 뒤늦게 분리하게 된다.

**권장 수정:**

Section 8.8의 Step 1은 Level 0여야 한다.

```bash
python3 -m pytest tests/test_reconstruction_helpers.py -v --tb=short
```

그 다음에 Level 1로 넘어가야 문서가 말하는 TDD 순서와 실제 실행 절차가 일치한다.

---

### W-3. "새로운 테스트 입력 파일이 필요 없다"는 표현은 과도하다

**문서 위치:**

- Section 8.1

기존 testcase를 최대한 재사용하겠다는 방향은 좋다. 다만 현재 확인된 공백을 메우려면 최소한 다음 중 일부는 새 fixture 또는 기존 fixture 파생 샘플이 필요할 가능성이 높다.

- formatted paragraph + inline image 혼합 unit fixture
- namespace-bearing XHTML fragment normalization fixture
- duplicate-content Level 3 disambiguation fixture

즉 "대부분 기존 fixture 재사용"은 맞지만, "새로운 테스트 입력 파일이 전혀 필요 없다"는 문장은 너무 강하다.

---

## Suggestion

### S-1. Section 8을 "설계 검증 테스트"와 "회귀 방지 테스트"로 분리하면 더 명확하다

현재 Section 8은 unit/integration/e2e를 모두 포함하지만, 성격이 다른 두 가지 테스트가 섞여 있다.

- 설계 자체의 타당성을 입증하는 테스트
- 구현 후 회귀를 막는 테스트

다음을 분리하면 읽는 사람이 덜 헷갈린다.

- Part A: 설계 검증 테스트
  - ParagraphEditSequence
  - list children ref
  - callout recursive parsing
- Part B: 회귀 방지 테스트
  - reconstruction coverage
  - lossless fragment compare
  - reverse-sync-verify

---

### S-2. 승인 기준을 "Phase 진입 가능"과 "구현 완료 가능"으로 나누는 편이 낫다

현재 문서는 구현 계획과 테스트 계획은 자세하지만, "지금 당장 Phase 1에 착수 가능한가"를 가르는 gate가 약하다.

다음처럼 나누면 더 실용적이다.

- Phase 1 착수 전 필수 해소
  - C-1 paragraph invariant
  - C-2 Level 1/2 oracle
  - C-3 normalization strategy
- Phase 3 머지 전 필수 해소
  - W-1 Level 3 duplicate hash
  - W-2 실행 순서 정합성

---

## TDD 관점 평가

### 좋은 점

- 실제 testcase 기반 설계 원칙을 명시한 점은 좋다
- helper → block → document → byte-equal → E2E로 내려가는 계층적 테스트 구조는 적절하다
- E2E `reverse-sync-verify`를 최종 회귀 게이트로 유지한 판단도 맞다

### 부족한 점

- 가장 위험한 설계 가정(paragraph 좌표계)이 unit red test로 먼저 고정되어 있지 않다
- Level 1/2 expected source가 불명확해 테스트를 바로 쓸 수 없다
- Level 3 block identity가 불안정해 "pass = correct"라는 신뢰를 주지 못한다

### 현재 판단

**"문제 해결을 위해 충분한 테스트케이스를 확보하는 방안이 도출되어 있는가?"**라는 질문에 대한 답은:

**아직 충분하지 않다.**

테스트 레벨의 개수는 충분하지만, 최소 3개의 핵심 전제가 미정이다.

1. paragraph sidecar의 좌표계
2. Level 1/2의 oracle source
3. Level 3의 block identity

이 셋이 해결되어야 비로소 TDD 계획이 실제 문제 해결을 보장하는 체계가 된다.

---

## 권장 후속 조치

### 1. 설계 문서 우선 수정

다음 항목을 먼저 문서에서 확정해야 한다.

- paragraph `TextSegment.text`의 기준 좌표계
- `normalize_xhtml()` 구현 전략 또는 대체 비교 전략
- Level 1/2에서 원본 fragment를 어디서 읽을지
- Level 3에서 duplicate content를 어떻게 disambiguate할지

### 2. TDD 진입용 최소 red test 정의

구현 전에 아래 4개를 먼저 failing test로 고정하는 것이 좋다.

1. formatted paragraph + inline image
2. nested list + `inline_trailing_html`
3. callout + nested list + code block
4. duplicate MDX content page에서 Level 3 fragment identity 유지

### 3. 승인 기준 재정의

현재 문서는 "방향은 맞음" 수준이다.

다음 기준을 만족하면 구현 착수 가능으로 볼 수 있다.

- C-1, C-2, C-3 해소
- Level 0를 포함한 실행 순서 재정의
- Level 3 identity 전략 확정

---

## 평가 요약

| 항목 | 평가 |
|------|------|
| 재구성 중심 방향성 | ✅ 적절 |
| list flat mapping + `children` ref | ✅ 적절 |
| callout 재귀 파싱 방향 | ✅ 적절 |
| paragraph 설계 완결성 | ❌ Critical |
| Level 1/2 테스트 oracle 정의 | ❌ High |
| XHTML normalization 전략 | ❌ High |
| Level 3 hash 기반 block 식별 | ⚠️ Warning |
| TDD 실행 순서 일관성 | ⚠️ Warning |
| "기존 fixture만으로 충분" 주장 | ⚠️ Warning |

최종 판단:

- **설계 방향:** 승인 가능
- **설계 문서의 현재 완성도:** 수정 필요
- **TDD 관점의 테스트 확보 방안:** 보강 필요
