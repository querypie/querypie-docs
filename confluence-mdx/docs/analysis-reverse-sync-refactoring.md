# Reverse Sync 리팩토링 분석

> 작성일: 2026-02-26
> 대상: `confluence-mdx/bin/reverse_sync/` + `reverse_sync_cli.py`

## 1. 분석 목적

최근 reverse-sync 관련 커밋 12건 중 **10건이 버그 수정**이다. 이 빈도는 단순한 구현 실수가 아니라 **설계 수준의 구조적 문제**에서 비롯되었을 가능성이 높다. 이 문서는 반복 버그의 근본 원인을 디자인 결함 관점에서 분석하고, 리팩토링 대상을 도출한다.

---

## 2. 최근 버그 패턴 분류

최근 커밋에서 수정된 버그를 원인별로 분류한다.

### 2.1 텍스트 위치 매핑 오류 (4건)

| 커밋 | 증상 | 근본 원인 |
|------|------|-----------|
| `2e9de1a` | `find_insert_pos(char_map, 0)`이 `char_map[0]` 존재 시에도 0 반환 | `text_transfer.py`의 문자 단위 정렬에서 경계 조건 누락 |
| `fb7efeec` | 인접 text node 경계에서 insert opcode 양쪽 적용 | `xhtml_patcher.py`의 `_map_text_range`에서 half-open range 미적용 |
| `60c5390` | `<strong>` 뒤 조사 앞 공백 미제거 | `_apply_text_changes`에서 인라인 태그 경계 gap 처리 누락 |
| `1e4dd43` | 재실행 시 "네이티브로 네이티브로" 중복 | `transfer_text_changes`가 이미 적용된 텍스트를 재매핑 |

### 2.2 인라인 포맷 변경 감지 실패 (3건)

| 커밋 | 증상 | 근본 원인 |
|------|------|-----------|
| `6438a16` | 연속 인라인 마커 사이 텍스트 변경(쉼표 등) 미감지 | `has_inline_format_change`가 마커 간 텍스트를 검사하지 않음 |
| `ea28d65` | flat list에서 backtick 변경 누락 | `_resolve_child_mapping` 실패 시 inline 변경 추적 경로 없음 |
| `7ebaf87` | inline format 변경이 text-only 패치로 처리됨 | inline 변경 감지 로직 자체가 부재 (이 커밋에서 신규 구현) |

### 2.3 리스트 처리 실패 (2건)

| 커밋 | 증상 | 근본 원인 |
|------|------|-----------|
| `f5f307f` | 리스트 항목 수 변경 시 빈 패치 반환 | `build_list_item_patches`에 항목 수 불일치 분기 없음 |
| `acf4e3c` | 중첩 리스트 텍스트 붕괴 | `SequenceMatcher`의 `autojunk` 기본값이 CJK에 부적합 |

### 2.4 정규화/검증 불일치 (2건)

| 커밋 | 증상 | 근본 원인 |
|------|------|-----------|
| `29cdc9f` | 날짜 locale 불일치로 verify 실패 | forward converter의 locale이 reverse-sync 파이프라인과 불일치 |
| `18679d0` | callout 매핑 불완전으로 verify 실패 | `roundtrip_verifier`의 정규화 함수 부족 |

---

## 3. 디자인 결함 분석

### 3.1 근본 원인: "텍스트 패칭" 전략의 본질적 취약성

현재 reverse-sync의 핵심 전략은 다음과 같다:

```
MDX diff → 텍스트 변경 추출 → XHTML 내 텍스트 위치 매핑 → 문자 단위 치환
```

이 전략은 **XHTML의 DOM 구조를 보존하면서 텍스트만 교체**하는 것이 목표이지만, 근본적인 한계가 있다:

**문제 1: 두 개의 독립된 좌표계 사이의 매핑**

MDX의 텍스트 위치와 XHTML의 텍스트 위치는 서로 다른 좌표계이다. 이 둘을 문자 단위로 정렬(`align_chars`)하는 것은 본질적으로 불안정하다.

- MDX에서 `**bold**`는 8글자, XHTML에서 `<strong>bold</strong>`는 23글자
- Markdown의 인라인 마커, HTML 엔티티, Confluence 전용 태그 등이 좌표를 왜곡
- `text_transfer.py`의 `align_chars()`는 비공백 문자만 정렬하므로, 공백 위치의 미묘한 차이에서 오류 발생

**이것이 2.1의 4건의 버그가 모두 "위치 매핑"에서 발생한 이유이다.**

**문제 2: "텍스트 변경"과 "구조 변경"의 구분 불가능**

현재 파이프라인은 모든 변경을 "텍스트 변경"으로 시작하되, 특정 조건에서 "구조 변경"(inner XHTML 재생성)으로 전환한다. 이 전환 조건이 `has_inline_format_change()` 등의 휴리스틱에 의존하므로:

- 감지하지 못하는 edge case가 계속 발견된다 (2.2의 3건)
- 감지 로직 추가 → 새로운 edge case 발견 → 또 추가, 의 무한 루프

**문제 3: 리스트의 이중 구조**

MDX 리스트는 단일 블록(`type: 'list'`)이지만, XHTML에서는 `<ul>` 안에 여러 `<li>` 요소로 분해된다. 이 1:N 매핑은 다음과 같은 복잡성을 초래한다:

- `build_list_item_patches`: 항목별 매칭 시도 → 실패 시 containing block 폴백
- `_resolve_child_mapping`: 4단계 폴백 (collapse_ws → 공백 제거 → 마커 제거 → 역방향)
- 항목 수 변경 시 별도 분기 필요 (`f5f307f`)
- flat list vs nested list 구분 필요 (`ea28d65`)

**이 복잡성은 "하나의 MDX 블록 = 하나의 XHTML 요소" 가정이 리스트에서 무너지기 때문이다.**

### 3.2 코드 냄새: patch_builder.py의 God Function

`build_patches()` (719줄 파일)는 다음을 모두 담당한다:

1. 변경 유형 판별 (modified / added / deleted)
2. 매핑 전략 결정 (direct / containing / list / table / skip)
3. 인라인 포맷 변경 감지
4. 텍스트 정규화 및 비교
5. 패치 dict 생성
6. 멱등성 보장 (이미 적용된 변경 스킵)

**최근 버그 수정 10건 중 7건이 이 파일을 수정했다.** 이는 단일 모듈에 과도한 책임이 집중되어 있음을 보여준다.

분기 구조를 보면:

```
build_patches()
  ├── deleted → _build_delete_patch()
  ├── added → _build_insert_patch()
  └── modified
      ├── NON_CONTENT → skip
      └── _resolve_mapping_for_change()
          ├── skip → continue
          ├── list → build_list_item_patches()
          │     ├── 항목 수 동일
          │     │   ├── child 매칭 성공
          │     │   │   ├── inline 변경 → new_inner_xhtml
          │     │   │   └── text 변경
          │     │   │       ├── prefix 있음 → transfer + prefix 복원
          │     │   │       └── prefix 없음 → transfer
          │     │   └── child 매칭 실패
          │     │       ├── inline marker 추가 → 전체 재생성
          │     │       └── containing block 폴백
          │     └── 항목 수 다름 → 전체 inner XHTML 재생성
          ├── table → build_table_row_patches()
          ├── containing → 그룹화 후 일괄 transfer
          └── direct
              ├── inline 변경 → new_inner_xhtml
              └── text 변경
                  ├── 이미 적용됨 → skip (멱등성)
                  ├── old ≠ xhtml → transfer_text_changes
                  └── old == xhtml → 직접 교체
```

이 분기 트리는 14단계 깊이에 6가지 전략을 포함한다. 새로운 edge case가 발견될 때마다 분기가 추가되는 구조이다.

### 3.3 코드 냄새: 다단계 폴백 체인

`_resolve_mapping_for_change()`는 매핑을 찾기 위해 다음 순서로 시도한다:

1. sidecar 직접 조회 (`find_mapping_by_sidecar`)
2. parent mapping → child 해석 (`_resolve_child_mapping`)
3. 텍스트 포함 검색 (`_find_containing_mapping`)
4. 리스트/테이블 전략으로 전환

`_resolve_child_mapping()`도 내부적으로 4단계 폴백:

1. `collapse_ws` 완전 일치
2. 공백 제거 완전 일치
3. XHTML 리스트 마커 제거 후 비교
4. MDX 리스트 마커 제거 후 비교

이 폴백 체인은 매핑의 정확성에 대한 **자신감 부족**을 코드로 표현한 것이다. sidecar mapping이 정확하다면 폴백이 불필요하다.

### 3.4 코드 냄새: 정규화 함수의 폭발적 증가

텍스트 비교를 위한 정규화 함수가 여러 모듈에 분산되어 있다:

| 모듈 | 함수 | 용도 |
|------|------|------|
| `text_utils.py` | `normalize_mdx_to_plain()` | MDX → plain text |
| `text_utils.py` | `collapse_ws()` | 공백 축약 |
| `text_utils.py` | `strip_for_compare()` | 불가시 문자 제거 |
| `text_utils.py` | `strip_list_marker()` | 리스트 마커 제거 |
| `patch_builder.py` | `normalize_table_row()` | 테이블 행 정규화 |
| `patch_builder.py` | `_strip_block_markers()` | heading/list 마커 제거 |
| `roundtrip_verifier.py` | 9개 `_normalize_*` 함수 | 검증 시 정규화 |

**총 15개 이상의 정규화 함수**가 존재하며, 각각 미묘하게 다른 규칙을 적용한다. 이는 "어느 수준의 동일성이면 같다고 볼 것인가"에 대한 일관된 정의가 없음을 의미한다.

### 3.5 코드 냄새: xhtml_patcher.py의 취약한 텍스트 위치 추적

`_apply_text_changes()`는 다음 알고리즘을 사용한다:

1. `old_text.strip()`에서 각 DOM text node의 위치를 `str.find()`로 추적
2. `SequenceMatcher`로 old→new 변경(opcode)을 계산
3. 각 text node의 [start, end) 범위에 해당하는 opcode를 적용

이 알고리즘의 문제점:

- **`str.find()`는 "첫 번째 일치"만 반환**: 동일한 텍스트가 반복되면 위치가 틀려진다
- **text node의 경계가 opcode의 경계와 일치하지 않을 때**: `replace` opcode를 비율(`ratio`)로 분배하는데, 이는 근사치이며 CJK 문자에서 부정확
- **인라인 태그 사이의 gap 처리**: `<strong>A</strong> B`에서 gap(" ")이 삭제될 때의 처리를 별도 로직으로 해결 (`60c5390`)

---

## 4. 구조적 개선 제안

### 4.1 전략 전환: "텍스트 패칭" → "선택적 재생성" 중심으로

현재는 **텍스트 패칭이 기본**, 실패 시 재생성으로 폴백하지만, 이를 역전시킨다:

| 현재 | 개선 후 |
|------|---------|
| text transfer가 기본 | inner XHTML 재생성이 기본 |
| `has_inline_format_change` → 재생성 | 단순 텍스트만 text transfer |
| edge case마다 분기 추가 | 재생성이 기본이므로 분기 축소 |

**기대 효과:**
- `text_transfer.py`, `_apply_text_changes()`의 복잡한 위치 매핑 로직의 사용 빈도 감소
- `has_inline_format_change()` 같은 감지 휴리스틱 불필요
- patch_builder.py의 분기 트리 대폭 단순화

**trade-off:**
- 재생성 시 Confluence 전용 태그(`<ac:emoticon>`, `<ac:link>` 등)가 손실될 수 있음
- `lost_info_patcher.py`의 복원 범위를 확대해야 함
- 일부 케이스에서 XHTML 포맷(공백, 속성 순서 등)이 변경될 수 있음

### 4.2 patch_builder.py 분해

현재 719줄 단일 파일을 책임 단위로 분리한다:

| 새 모듈 | 책임 | 현재 위치 |
|---------|------|-----------|
| `strategy_resolver.py` | 변경 유형별 전략 결정 | `_resolve_mapping_for_change` |
| `list_patcher.py` | 리스트 블록 전용 패치 로직 | `build_list_item_patches`, `split_list_items` |
| `table_patcher.py` | 테이블 전용 패치 로직 | `build_table_row_patches`, `split_table_rows` |
| `inline_detector.py` | 인라인 포맷 변경 감지 | `has_inline_format_change`, `_extract_inline_markers` |
| `patch_builder.py` | 오케스트레이션만 담당 | `build_patches` (축소) |

### 4.3 매핑 정확성 개선

현재 `generate_sidecar_mapping()`의 텍스트 기반 매칭을 개선하여 폴백 체인의 필요성을 줄인다:

- forward converter가 mapping.yaml을 생성할 때 **확정적인 MDX 블록 인덱스**를 기록
- `_resolve_child_mapping()`의 4단계 폴백 → sidecar가 child 매핑도 포함하도록 확장
- `_find_containing_mapping()`의 텍스트 포함 검색 → sidecar에서 parent-child 관계를 명시

### 4.4 정규화 전략 통합

15개 이상의 정규화 함수를 **비교 수준(level)** 기반으로 체계화한다:

| Level | 적용 | 용도 |
|-------|------|------|
| L0: exact | 변환 없음 | 엄격 검증 |
| L1: whitespace | `collapse_ws` + trailing ws 제거 | 매핑 조회 |
| L2: markup | L1 + 인라인 마커 제거 + HTML unescape | 블록 매칭 |
| L3: structural | L2 + 리스트 마커 + heading 마커 제거 | 폴백 매칭 |

현재는 각 호출부에서 임의로 정규화 수준을 선택하고 있어, 동일한 비교에서도 정규화 수준이 불일치하는 경우가 있다.

### 4.5 xhtml_patcher.py의 알고리즘 개선

`_apply_text_changes()`의 `str.find()` 기반 위치 추적을 개선한다:

- text node 순회 시 DOM 순서를 기반으로 위치를 누적 계산 (str.find 제거)
- `replace` opcode의 비율 분배 대신, opcode 경계를 text node 경계에 맞춰 분할
- 대안: `_apply_text_changes` 전체를 `_replace_inner_html`로 대체하는 것을 기본으로 고려

---

## 5. 리팩토링 대상 요약

### 5.1 높은 우선순위 (버그 재발 방지)

| # | 대상 | 유형 | 기대 효과 |
|---|------|------|-----------|
| R1 | `build_patches` direct 경로: text transfer → inner XHTML 재생성 기본 전환 | 전략 변경 | 2.1 위치 매핑 + 2.2 인라인 감지 버그 근본 해결 |
| R2 | `build_list_item_patches` 단순화: child 매칭 실패 시 즉시 재생성 | 전략 변경 | 리스트 관련 버그 근본 해결, `_resolve_child_mapping` 4단계 폴백 제거 |
| R3 | `_apply_text_changes`의 str.find() → DOM 순서 기반 위치 추적 | 알고리즘 | 위치 매핑 정확성 향상 |

### 5.2 중간 우선순위 (유지보수성 개선)

| # | 대상 | 유형 | 기대 효과 |
|---|------|------|-----------|
| R4 | `patch_builder.py` 분해 (719줄 → 5개 모듈) | 구조 | 변경 영향 범위 축소, 테스트 용이성 |
| R5 | 정규화 함수 체계화 (Level 기반) | 설계 | 비교 일관성, 새 정규화 추가 시 혼란 방지 |
| R6 | `generate_sidecar_mapping()`에 child 매핑 포함 | 데이터 | 폴백 체인 축소, 매핑 정확성 향상 |

### 5.3 낮은 우선순위 (코드 품질)

| # | 대상 | 유형 | 기대 효과 |
|---|------|------|-----------|
| R7 | `_iter_block_children()` 중복 제거 (mapping_recorder ↔ xhtml_patcher) | 중복 제거 | 기존 분석(4.1)과 동일 |
| R8 | `NON_CONTENT_TYPES` 상수 중복 (block_diff, patch_builder, sidecar, rehydrator) | 중복 제거 | 4곳에서 독립 정의 → 단일 정의 |
| R9 | `reverse_sync_cli.py`의 sidecar 조립 인라인 코드 → 함수 추출 | 추출 | run_verify() 285~302행의 인라인 조립 → 전용 함수 |

---

## 6. 주요 수치

| 지표 | 값 |
|------|-----|
| reverse_sync/ 총 줄 수 | ~3,263 |
| patch_builder.py 줄 수 | 719 (전체의 22%) |
| 최근 12 커밋 중 버그 수정 | 10건 (83%) |
| patch_builder.py 수정 커밋 | 7/10건 (70%) |
| 정규화 함수 수 | 15+ |
| `_resolve_child_mapping` 폴백 단계 | 4 |
| `_resolve_mapping_for_change` 전략 수 | 5 (direct, containing, list, table, skip) |

---

## 8. 구현 진행 상황

### 8.1 R1: direct 경로 inner XHTML 재생성 — 완료

- **PR**: #858 (merged)
- `build_patches`의 direct 경로에서 text transfer 대신 `mdx_block_to_inner_xhtml` 재생성을 기본으로 전환
- `lost_info_patcher.py`의 `apply_lost_info`로 `<ac:*>` 요소 보존

### 8.2 R2: list_patcher 재생성 — 완료 (후속 과제 있음)

- **PR**: #859
- `build_list_item_patches`에서 child 매칭 실패 시 전체 리스트 inner XHTML 재생성
- containing block 제거 폴백 완전 제거
- `<ac:image>` 포함 리스트는 `transfer_text_changes`로 폴백하는 가드 추가

#### R2 구현 후 발견된 후속 과제

R2 구현 중 3개 테스트 케이스(544112828, 544379140, 544384417)에서 round-trip 검증이 `pass → fail`로 변경됨. 원인 분석 결과 2가지 후속 과제가 도출됨.

**F1. `<span style>` 가드 추가 (우선순위: 높음)**

| 항목 | 내용 |
|------|------|
| 위치 | `list_patcher.py` — `_regenerate_list_from_parent` 및 per-child 경로 |
| 증상 | 리스트 항목 내 `<span style="color: ...">` 인라인 스타일이 재생성 시 소실 |
| 예시 | 544379140: `<span style="color: rgb(76,154,255);">See Log Template...</span>` → 일반 텍스트 |
| 해결 방향 | `<ac:image>` 가드와 동일한 패턴으로 `<span style=` 포함 시 `transfer_text_changes`로 폴백 |
| 영향 | Confluence에서 색상이 적용된 텍스트가 일반 텍스트로 변경되는 **실제 시각적 변화** |

**F2. `<ol start="1">` 보존 (우선순위: 낮음)**

| 항목 | 내용 |
|------|------|
| 위치 | `mdx_to_xhtml_inline.py` — `_render_nested_list` |
| 증상 | 재생성 시 `<ol start="1">` → `<ol>`로 변경 (HTML 기본값이므로 기능 동일) |
| 예시 | 544379140: 4건, 544384417: 8건의 `start` 속성 제거 |
| 해결 방향 | `_render_nested_list`에서 ordered list 생성 시 `start="1"` 속성 출력 |
| 영향 | 기능적 영향 없음 (Confluence 렌더링 동일), 불필요한 XHTML 변경 최소화 |

### 8.3 F1+F2: `<span style>` 가드 + `<ol start="1">` 보존 — 완료

- **PR**: #862 (merged)
- `list_patcher.py`에서 `<span style=` 포함 시 `transfer_text_changes`로 폴백하는 가드 추가
- `mdx_to_xhtml_inline.py`에서 ordered list 생성 시 `start="1"` 속성 출력

### 8.4 F3: direct 경로 `<ac:link>` 가드 — 완료

- **PR**: #864 (예정)
- `build_patches`의 direct 경로에서 매핑 XHTML에 `<ac:link>` 포함 시 inner XHTML 재생성 대신 `transfer_text_changes`로 폴백
- HTML table 블록 내 `<ac:link>` 요소가 `<a href>`로 소실되는 문제 해결
- 544178405 테스트케이스 `status: fail → pass` 전환 (16/16 전체 pass 달성)

---

## 7. 결론

reverse-sync의 반복적인 버그는 **"텍스트 패칭이 기본, 재생성이 폴백"이라는 설계 전략**에서 비롯된다. 텍스트 패칭은 두 좌표계(MDX ↔ XHTML) 사이의 문자 단위 정렬을 요구하며, 이는 인라인 마커, 공백 차이, DOM 구조 경계에서 본질적으로 불안정하다.

이 전략을 **"재생성이 기본, 텍스트 패칭이 최적화"**로 역전시키면, 대부분의 edge case 분기가 불필요해지고, patch_builder.py의 복잡도를 대폭 줄일 수 있다.

단, 재생성 전략으로의 전환에는 Confluence 전용 요소(`<ac:*>`) 보존이라는 별도의 과제가 있으므로, `lost_info_patcher.py`의 확장이 선행되어야 한다.
