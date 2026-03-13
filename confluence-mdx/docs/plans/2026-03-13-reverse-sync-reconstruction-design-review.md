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

---

## 설계 검증 (Claude Code 검토, 2026-03-13)

### 검증 요약

`2026-03-13-reverse-sync-reconstruction-design.md`는 v5 리뷰에서 지적된 세 가지 Critical/High 이슈(paragraph 좌표계 혼란, oracle 출처 불명, lxml 의존성)를 모두 해소하고 구현 착수 가능한 수준으로 재작성됐다. 현재 코드베이스와 정합성도 높다. 다만 설계 내부에 검증이 필요한 가정 몇 가지가 남아 있으며, Phase 3~4에서 현실적 어려움이 예상된다.

---

### 1. 문제 진단의 정확성

코드베이스와 대조한 결과, 설계 문서의 현재 시스템 문제 진단은 실제 코드와 일치한다.

**정확한 진단:**

- `patch_builder.py`의 전략 분기 누적 (`direct` / `containing` / `list` / `table` / `skip`) 및 각 전략마다 별도 fallback이 실제로 존재한다 (patch_builder.py:88-156).
- `transfer_text_changes()` 기반 수정이 중심 경로임을 확인했다. `containing` 전략과 delete+add 쌍 처리 모두 이 함수에 의존한다 (patch_builder.py:76, 221).
- Confluence 전용 요소(`<ac:image>`, `<ac:link>` 등)를 발견하면 재생성 대신 text transfer로 폴백하는 코드가 명시적으로 존재한다 (patch_builder.py:300-309).
- `sidecar.py`의 `SidecarBlock`에 `reconstruction` 필드가 없음을 확인했다. 설계 문서의 "현재 schema v2에 reconstruction metadata가 없다"는 진단이 정확하다.

**추가로 확인한 사항:**

`generate_sidecar_mapping()`(sidecar.py:306)의 4차 prefix 매칭(`[:20]`)은 text similarity가 낮은 경우 false positive를 낼 수 있다. PR 이력(#853)에서 이미 버그가 발생한 패턴이며, 설계 문서가 이 경로를 "더 이상 중심축이 되어서는 안 된다"고 명시한 것은 정확하다.

---

### 2. 목표 달성 가능성

**달성 가능한 목표:**

설계의 세 핵심 전환은 코드베이스 자산을 기반으로 달성 가능하다.

- `convert_inline()` 역변환 가정 제거 → 설계가 명시적으로 "기준 좌표계는 XHTML DOM에서 추출한 normalized plain text"로 전환했다 (§3.1). 현재 `mapping_recorder.py`가 이미 `get_text()` 기반 plain text를 생성하므로 좌표계 기반은 존재한다.
- `expected.roundtrip.json`을 primary oracle로 승격 → 현재 모든 21개 testcase에 `xhtml_fragment` 필드가 존재함을 직접 확인했다. oracle 전환의 전제가 충족된다.
- BeautifulSoup 기반 normalizer 구축 → `mapping_recorder.py`, `xhtml_patcher.py`, `xhtml_beautify_diff.py`가 이미 BeautifulSoup을 사용한다. 공용 `xhtml_normalizer.py`로 통합하는 것은 현실적이다.

**달성이 불확실한 목표:**

- **paragraph + inline anchor 재주입 (§5.4)**: `old_plain_offset` 기반 offset mapping이 핵심이다. anchor가 두 개 이상이거나, 변경으로 인해 앞 anchor의 offset이 뒤 anchor에 영향을 줄 때의 순서 보장 로직이 설계에 명시되지 않았다. 구현 시 edge case가 될 가능성이 높다.
- **list reconstruction의 zip 매칭 (§5.5)**: "sidecar list item sequence와 index 기반 zip"은 MDX와 XHTML의 list item 수가 다를 때(항목 추가/삭제) 어떻게 처리할지 명확하지 않다. 설계가 이 케이스를 암묵적으로 "child slot 수 불일치 → fail"로 처리한다면 실용적 커버리지가 낮아질 수 있다.

---

### 3. 아키텍처 설계의 적절성

**적절한 설계 결정:**

- `replace_fragment` 액션을 `xhtml_patcher.py`에 추가하는 접근은 자연스럽다. 기존 `insert` / `delete` 패턴과 일관되고, DOM 전체 교체라는 의미도 명확하다.
- `reconstruction_planner.py`를 분리하고 `patch_builder.py`를 thin orchestration layer로 만드는 방향은 현재 `patch_builder.py`의 1개 함수가 전략 분기 + fallback + 그룹화를 모두 담당하는 문제를 직접 해결한다.
- block identity에 `hash + line_range + order`를 함께 사용하는 방식은 v5 리뷰의 W-1 지적을 정확히 해소한다.
- `SidecarBlock`에 `reconstruction` 필드를 추가하는 스키마 v3 설계는 테스트 oracle과 runtime metadata를 같은 artifact에 담는 좋은 설계다. 현재 `SidecarBlock.lost_info`가 비슷한 패턴으로 이미 존재하므로 확장이 자연스럽다.

**검토가 필요한 설계 결정:**

- **callout outer wrapper 보존 (§5.6)**: "outer wrapper 보존은 `lost_info_patcher`가 아니라 reconstruction metadata가 책임진다"는 원칙이 맞지만, 현재 `lost_info_patcher.py`가 `_STRUCTURED_MACRO_RE`로 callout macro를 처리하는 코드가 이미 있다. 두 책임 분리 경계를 구현 시 명확히 해야 한다.
- **Opaque block의 fail-closed 정책 (§5.3-D)**: `UnsupportedReconstructionError`로 명시적 실패하는 방향은 올바르지만, 현재 `build_patches()`가 mapping을 찾지 못하면 `skip`으로 조용히 통과한다. fail-closed로 전환하면 현재 pass하던 케이스 일부가 fail로 바뀔 수 있어 Phase 5 전환 시 회귀 위험이 있다.

---

### 4. 위험 요소 및 미검토 에지케이스

**설계에서 명시적으로 언급되지 않은 에지케이스:**

1. **paragraph anchor affinity 충돌**: `affinity: "after"` anchor가 연속으로 나올 때 두 번째 anchor의 `old_plain_offset`이 첫 번째 anchor 삽입 후 shift된 DOM 기준인지 원본 기준인지 명확하지 않다. 구현 시 "모든 offset은 original XHTML 기준"으로 고정해야 한다.

2. **list item 수 불일치 처리**: 설계 §5.5는 "child type과 순서를 기준으로 재귀 reconstruct"한다고 하지만, MDX에서 list item을 추가/삭제한 경우의 처리 방식이 명시되지 않았다. 이것이 실제 reverse-sync에서 가장 흔한 변경 패턴 중 하나임을 감안하면, Level 3 테스트(Phase 3 게이트) 전에 결정이 필요하다.

3. **sidecar v3 빌더의 old_plain_text 생성 시점**: `reconstruction.old_plain_text`는 sidecar 빌드 시(forward convert 시점) 기록된다. 이후 page.xhtml이 Confluence에서 자체 수정되면 `old_plain_text`가 실제 XHTML과 달라질 수 있다. 현재 `source_xhtml_sha256`로 감지 가능하나, 불일치 시 처리 경로가 설계에 없다.

4. **`_parse_list_items()` 및 `_build_list_tree()` public 승격 범위**: 설계가 이 private 함수들을 `parse_list_tree()` public API로 승격하겠다고 밝혔다. 현재 `_parse_list_items`가 continuation line(마커 없는 줄)을 이전 항목에 붙이는 로직(emitter.py:182-183)이 있는데, 이 동작이 reconstruction context에서도 의도된 것인지 확인이 필요하다.

5. **BeautifulSoup `html.parser` 속성 순서**: `xhtml_normalizer.py` 구현 시 BeautifulSoup으로 파싱 후 재직렬화하면 attribute 순서가 바뀔 수 있다. fragment comparison에서 false negative를 방지하려면 attribute 정렬 규칙을 명시해야 한다. 현재 `mdx_to_storage_xhtml_verify.py`에 이 로직이 있을 수 있으나 통합 방법을 확인해야 한다.

---

### 5. 구현 복잡도 vs 기대 효과

**비용 측면:**

- Phase 0-2(normalizer, schema v3, clean block replacement): 비교적 낮은 복잡도. 기존 자산 재사용이 명확하고 test oracle이 이미 준비됐다.
- Phase 3(paragraph/list anchor reconstruction): 중간-높은 복잡도. offset mapping 알고리즘, DOM 삽입 순서 보장, list item 수 불일치 처리 등 새로 작성해야 할 로직이 많다.
- Phase 4(container reconstruction): 높은 복잡도. callout/details/ADF panel이 각각 outer wrapper 구조가 다르고, `lost_info_patcher`와의 책임 분리를 정확히 해야 한다.
- Phase 5(planner 전환): 중간 복잡도. 하지만 fail-closed 전환 시 회귀 위험이 있어 신중한 rollout이 필요하다.

**기대 효과:**

- 현재 시스템의 근본적 취약점(text coordinate를 벗어난 Confluence 요소 손실)을 구조적으로 해소한다.
- `transfer_text_changes()` fallback에 의존하는 silent corruption 경로를 제거한다.
- test oracle이 `mapping.yaml`에서 `expected.roundtrip.json`으로 전환되어 "무엇을 기준으로 테스트하는가"가 명확해진다.

**판단:**

Phase 0-2의 ROI는 높다. Phase 3-4는 복잡도 대비 효과가 여전히 높지만, 에지케이스 처리 결정을 Phase 착수 전에 명확히 해야 낭비 없이 구현할 수 있다.

---

### 종합 판단

v5 리뷰의 3개 Critical/High 이슈가 새 설계 문서에서 모두 명시적으로 해소됐다. 특히 paragraph 좌표계를 "XHTML DOM에서 추출한 normalized plain text"로 확정하고, oracle을 `expected.roundtrip.json.xhtml_fragment`로 명시한 결정이 핵심이다. 현재 코드베이스와의 정합성도 양호하다.

**권고사항:**

1. **Phase 3 착수 전 필수 결정**: list item 수 불일치(추가/삭제) 시 처리 방식을 명시하라. "수 불일치는 항상 fail"이라면 테스트 설계에 해당 케이스를 명시적으로 포함해야 한다.
2. **anchor offset 기준 명문화**: `reconstruction.anchors[].old_plain_offset`이 "원본 XHTML 기준 누적 offset"임을 설계 문서에 명시하라. 구현자가 이 가정을 따르지 않으면 멀티 anchor 케이스에서 버그가 발생한다.
3. **`lost_info_patcher` vs reconstruction metadata 경계 결정**: callout outer wrapper를 어느 쪽이 책임지는지 Phase 4 착수 전에 코드 수준 경계를 설계 문서에 추가하라.
4. **현재 설계 문서 완성도**: 구현 착수 가능 수준이다. Phase 0-2는 즉시 착수 가능하고, Phase 3-4는 위 항목을 보완 후 착수를 권장한다.
