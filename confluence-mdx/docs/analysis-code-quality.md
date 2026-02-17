# 코드 품질 분석 및 개선 현황

> 최종 업데이트: 2026-02-17
> 대상: `confluence-mdx/` 전체 모듈

## 1. 분석 개요

confluence-mdx 코드베이스의 불필요 코드(dead code)와 중복 코드(duplicate code)를 분석하고,
리팩토링 결과와 남은 개선 항목을 기록합니다.

### 모듈 구조 및 규모

| 모듈 | 파일 수 | 줄 수 | 역할 |
|------|---------|-------|------|
| `converter/` | 4 | ~2,337 | Forward: XHTML → MDX |
| `mdx_to_storage/` | 5 | ~1,246 | Backward: MDX → XHTML |
| `reverse_sync/` | 14 | ~3,263 | 변경 감지 & 패칭 |
| `fetch/` | 8 | ~1,144 | Confluence API 수집 |
| `skeleton/` | 5 | ~2,364 | 구조 추출 |
| CLI 스크립트 | 17 | ~3,828 | 진입점 |
| **합계** | **53** | **~14,182** | |

테스트: 29개 파일, ~9,475줄

### Backward-compat 래퍼

| 파일 | 줄수 | 용도 | 유지 사유 |
|------|------|------|-----------|
| `reverse_sync/mdx_block_parser.py` | 136 | `MdxBlock` + `parse_mdx_blocks()` 원본 구현 | `rehydrator.py` splice 경로가 이 파서의 블록 분할에 의존, sidecar `mdx_content_hash`가 이 파서 기준으로 생성 |

---

## 2. 완료된 리팩토링

| # | 항목 | 내용 | 절감 |
|---|------|------|------|
| 1 | CLI 통합 | 4개 파일 → `mdx_to_storage_xhtml_cli.py` 5개 서브커맨드로 통합 | ~508줄 |
| 2 | MDX 파서 통합 | `parser.py`에 `parse_mdx_blocks()` 호환 API 추가, import 전환 | 중복 감소 |
| 3 | 인라인 변환기 통합 | `mdx_to_xhtml_inline.py`의 `_convert_inline()` → `mdx_to_storage.inline` import | ~50줄 |
| 4 | 텍스트 유틸리티 통합 | `text_normalizer.py` → `text_utils.py`로 이동, re-export 래퍼 전환 | ~40줄 |
| 5 | Regex 패턴 정리 | `emitter.py` → `parser.py`에서 import | 중복 제거 |
| 6 | Sidecar mapping 통합 | `converter/sidecar_mapping.py` 삭제, `converter/cli.py`가 `reverse_sync/sidecar.py`를 직접 호출 | ~160줄 |
| 7 | test_verify.py 삭제 | `run-tests.sh`가 `reverse_sync_cli.py verify --page-id`를 직접 호출하도록 전환 | ~67줄 |
| 8 | text_normalizer.py 래퍼 삭제 | 외부 참조 없음 확인 후 re-export 래퍼 삭제 | ~8줄 |

---

## 3. 불필요 코드 (Dead Code)

### 3.1 미사용 함수

| # | 파일 | 줄 | 함수 | 설명 |
|---|------|-----|------|------|
| D1 | `reverse_sync/xhtml_patcher.py` | 82-85 | `_xpath_index()` | xpath에서 인덱스 추출 함수. 정의만 존재하고 호출하는 곳 없음. 정렬용으로 설계되었으나 사용되지 않음 |
| D2 | `converter/context.py` | 84-89 | `confluence_url()` | Confluence 페이지 URL 생성 함수. `parse_confluence_url()`과 `convert_confluence_url()`은 사용 중이나 이 함수는 어디서도 호출되지 않음 |
| D3 | `mdx_to_storage/link_resolver.py` | 68-69 | `LinkResolver.has_pages()` | 페이지 로드 여부 확인 메서드. 정의만 존재하고 호출하는 곳 없음 |

### 3.2 미사용 변수

| # | 파일 | 줄 | 변수 | 설명 |
|---|------|-----|------|------|
| D4 | `converter/core.py` | 1072-1073 | `is_header_row` | `convert_table()` 내에서 `True`로 할당되지만 이후 참조되지 않음. header row 판별 로직이 미완성 |

### 3.3 디버그 전용 코드 (의도적 유지)

| 항목 | 파일 | 줄수 | 상세 |
|------|------|------|------|
| `_debug_markdown` 플래그 및 분기 | `converter/core.py:577, 614-630, 722-725, 1356` | ~30줄 | `False`로 하드코딩되어 분기가 절대 실행되지 않음. 개발자 디버깅용으로 유지 |
| `_debug_tags` 빈 집합 및 분기 | `converter/core.py:131-133, 180-181, 385-386` | ~10줄 | 빈 set으로 조건문이 절대 참이 되지 않음. 개발자 디버깅용으로 유지 |
| 주석 처리된 디버그 코드 | `converter/core.py:193-195` | ~4줄 | `DEBUG(JK)` 주석 표기됨 (c7dd721). 개발자 디버깅용으로 유지 |

### 3.4 불필요한 분기 로직

| # | 파일 | 줄 | 설명 |
|---|------|-----|------|
| D5 | `mdx_to_storage/parser.py` | 334-342 | `_parse_badge_block()`에서 if/else 양쪽 모두 `i = start + 1` 할당. if 분기(335-336)가 별도 로직 없이 동일한 값만 설정하여 불필요. else 분기만으로 충분 |

---

## 4. 중복 코드 및 리팩토링 대상

### 4.1 `_iter_block_children()` 함수 중복

**중복 위치:**
- `reverse_sync/mapping_recorder.py:23-31` (정규 구현, `fragment_extractor.py`가 이를 import)
- `reverse_sync/xhtml_patcher.py:141-149` (동일한 로컬 복사본)

**현황:** `fragment_extractor.py`는 `mapping_recorder.py`에서 올바르게 import하지만, `xhtml_patcher.py`는 자체 복사본을 정의하여 사용.

**예상 절감:** ~9줄 | **위험도:** 낮음 — import 전환만 필요

### 4.2 `_BADGE_COLOR_MAP` 사전 중복

**중복 위치:**
- `mdx_to_storage/emitter.py:23-31`
- `mdx_to_storage/inline.py:18-26`

**현황:** 완전히 동일한 `{"green": "Green", "blue": "Blue", ...}` 딕셔너리가 두 파일에 정의됨. 각각 `_emit_badge()`와 `_replace_badge()`에서 사용.

**예상 절감:** ~9줄 | **위험도:** 낮음 — 공유 상수로 추출

### 4.3 리스트 파싱/렌더링 중복

**중복 위치:**
- `mdx_to_storage/emitter.py:162-184` — `_parse_list_items()`, tree 기반 렌더링 (`_ListNode`, `depth = indent // 4`)
- `reverse_sync/mdx_to_xhtml_inline.py:85-127` — `_parse_list_items()`, 재귀 렌더링 (dict, raw indent)
- `reverse_sync/patch_builder.py:361-380` — `split_list_items()`, 항목 분리용

**현황:** 세 함수 모두 MDX 리스트를 줄 단위로 순회하며 마커(`^\d+\.`, `^[-*+]`)를 감지하고 들여쓰기를 계산. 출력 형식(ListNode, dict, str)만 다름.

**예상 절감:** ~50줄 | **위험도:** 중간 — 들여쓰기 해석 방식과 출력 형식이 달라 공통 파서 설계 필요

### 4.4 코드 블록 추출 중복

**중복 위치:**
- `mdx_to_storage/emitter.py:142-150` — `_extract_code_body()`: 펜스 마커 제거, 코드 본문 반환
- `reverse_sync/mdx_to_xhtml_inline.py:58-66` — `_convert_code_block()`: 펜스 마커 제거, 코드 내용 추출
- `reverse_sync/mdx_to_xhtml_inline.py:233-238` — `_extract_code_language()`: 펜스 첫 줄에서 언어 추출

**현황:** `_extract_code_body()`와 `_convert_code_block()`은 동일한 알고리즘(첫/끝 줄 ``` 제거)을 사용. `_extract_code_language()`는 언어 추출이라는 관련 기능.

**예상 절감:** ~15줄 | **위험도:** 낮음

### 4.5 리스트 regex 패턴 중복

**중복 위치:**
- `mdx_to_storage/parser.py:11-12` — `_LIST_ORDERED_PATTERN`, `_LIST_UNORDERED_PATTERN` (마커 감지용, 캡처 없음)
- `mdx_to_storage/emitter.py:14-15` — `_ORDERED_LIST_PATTERN`, `_UNORDERED_LIST_PATTERN` (캡처 그룹 포함)

**현황:** 같은 리스트 마커 regex가 이름과 캡처 그룹만 다르게 두 파일에 정의됨.

**예상 절감:** ~4줄 | **위험도:** 낮음

### 4.6 `load_pages_yaml()` 함수 중복

**중복 위치 (5곳):**

| 파일 | 시그니처 | 반환 타입 |
|------|----------|-----------|
| `convert_all.py:42-48` | `(path: str)` | `List[Dict]` |
| `converter/context.py:179-227` | `(yaml_path, dicts...)` | `None` (dict 채움) |
| `mdx_to_storage/link_resolver.py:25-50` | `(yaml_path: Path)` | `list[PageEntry]` |
| `unused_attachments.py:37-43` | `(var_dir: Path)` | `list[dict]` |
| `find_mdx_with_text.py:98-110` | `(yaml_path: Path)` | `Dict[str, Dict]` |

**현황:** 모두 `pages.yaml`을 로드하되 오류 처리와 반환 형식이 다름. `converter/context.py`는 전역 dict를 채우는 side-effect 방식.

**예상 절감:** ~100줄 | **위험도:** 중간 — 각 호출부의 요구 형식이 달라 통합 설계 필요

### 4.7 인라인 변환 regex 패턴 중복

**중복 위치:**
- `mdx_to_storage/inline.py:9-10` — `_CODE_SPAN_RE`, `_LINK_RE` (컴파일된 패턴)
- `reverse_sync/mdx_to_xhtml_inline.py:71,76` — 동일 패턴을 인라인 문자열로 재사용

**현황:** code span(`` `([^`]+)` ``)과 link(`\[([^\]]+)\]\(([^)]+)\)`) 패턴이 두 모듈에 중복.

**예상 절감:** ~4줄 | **위험도:** 낮음

### 4.8 테이블 행 분리 중복

**유사 위치:**
- `mdx_to_storage/emitter.py:357-359` — `_split_table_row()`: pipe 구분자로 셀 분리
- `reverse_sync/patch_builder.py:283-286` — `normalize_table_row()`: 테이블 행에서 셀 추출
- `text_utils.py:136-138` — `normalize_mdx_to_plain()` 내부 테이블 처리

**예상 절감:** ~10줄 | **위험도:** 낮음

---

## 5. 리팩토링 우선순위 요약

| 우선순위 | 항목 | 유형 | 예상 절감 | 위험도 |
|----------|------|------|-----------|--------|
| **높음** | D1: `_xpath_index()` 삭제 | Dead code | 4줄 | 낮음 |
| **높음** | D2: `confluence_url()` 삭제 | Dead code | 6줄 | 낮음 |
| **높음** | D3: `has_pages()` 삭제 | Dead code | 2줄 | 낮음 |
| **높음** | D4: `is_header_row` 할당 삭제 | Dead code | 2줄 | 낮음 |
| **높음** | D5: `_parse_badge_block()` if 분기 단순화 | Dead code | 2줄 | 낮음 |
| **높음** | 4.1: `_iter_block_children()` import 전환 | 중복 제거 | 9줄 | 낮음 |
| **높음** | 4.2: `_BADGE_COLOR_MAP` 공유 상수화 | 중복 제거 | 9줄 | 낮음 |
| **높음** | 4.4: 코드 블록 추출 통합 | 중복 제거 | 15줄 | 낮음 |
| **높음** | 4.5: 리스트 regex 패턴 통합 | 중복 제거 | 4줄 | 낮음 |
| **중간** | 4.3: 리스트 파싱 통합 | 중복 제거 | 50줄 | 중간 |
| **중간** | 4.6: `load_pages_yaml()` 통합 | 중복 제거 | 100줄 | 중간 |
| **낮음** | 4.7: 인라인 regex 패턴 공유 | 중복 제거 | 4줄 | 낮음 |
| **낮음** | 4.8: 테이블 행 분리 통합 | 중복 제거 | 10줄 | 낮음 |
| | **합계** | | **~217줄** | |

---

## 6. 의도적 유지 항목

### 수동 디버깅용 코드

| 항목 | 파일 | 줄수 |
|------|------|------|
| `_debug_markdown` 플래그 및 분기 | `converter/core.py` | ~30줄 |
| `_debug_tags` 빈 집합 및 분기 | `converter/core.py` | ~10줄 |
| 주석 처리된 디버그 코드 (`breakpoint()`) | `converter/core.py:193-195` | ~4줄 |

`# Used when debugging manually` 주석 표기됨 (c7dd721). 개발자 디버깅용으로 유지.

### TODO 주석

`converter/context.py:567, 570` — 의도적 워크어라운드, 사유 기재됨.

---

## 7. 구조적 이슈

1. **전역 가변 상태**: `converter/context.py`의 모듈 수준 전역 변수 → in-process 병렬화 불가. subprocess 격리로 우회 중.
2. **테이블 rowspan/colspan**: 동시 사용 시 셀 위치 추적 오류 가능.

---

## 8. 주의사항

1. **테스트 커버리지:** 625+ 유닛 테스트, 19 E2E 시나리오. 리팩토링 후 전체 테스트 통과 필수.
2. **splice 호환성:** `mdx_block_parser.py`는 `rehydrator.py`의 splice 경로가 의존하므로 원본 구현 유지.
3. **점진적 진행:** Phase별로 나누어 진행, 각 Phase 완료 후 전체 테스트 실행.
