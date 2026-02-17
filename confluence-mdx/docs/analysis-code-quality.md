# 코드 품질 분석 및 개선 현황

> 최종 업데이트: 2026-02-17
> 대상: `confluence-mdx/` 전체 모듈

## 1. 분석 개요

confluence-mdx 코드베이스의 불필요 코드(dead code)와 중복 코드(duplicate code)를 분석하고,
리팩토링 결과와 남은 개선 항목을 기록합니다.

### 모듈 구조 및 규모

| 모듈 | 파일 수 | 줄 수 | 역할 |
|------|---------|-------|------|
| `converter/` | 3 | ~2,180 | Forward: XHTML → MDX |
| `mdx_to_storage/` | 5 | ~1,170 | Backward: MDX → XHTML |
| `reverse_sync/` | 15 | ~3,220 | 변경 감지 & 패칭 |
| `fetch/` | 9 | ~1,150 | Confluence API 수집 |
| `skeleton/` | 5 | ~2,360 | 구조 추출 |
| CLI 스크립트 | 14 | ~3,800 | 진입점 |
| **합계** | **51** | **~13,880** | |

테스트: 25개 파일, ~8,400줄

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

## 3. 남은 개선 항목

### 3.1 리스트 파싱/렌더링 중복

**중복 위치:**
- `mdx_to_storage/emitter.py:156-223` — `_parse_list_items()`, tree 기반 렌더링 (`_ListNode`, `depth = indent // 4`)
- `reverse_sync/mdx_to_xhtml_inline.py:116-202` — `_parse_list_items()`, 재귀 렌더링 (dict, raw indent)

**예상 절감:** ~50줄 | **위험도:** 중간 — 들여쓰기 해석 방식이 다름

### 3.2 데이터 모델 분산

`MdxBlock`, `Block`, `BlockMapping`, `SidecarEntry`, `PageEntry`, `BlockChange`, `_ListNode` 등이 5개 이상의 파일에 분산.

**예상 절감:** ~20줄 | **위험도:** 낮음

### 3.3 코드 블록 추출 중복

`emitter.py`의 `_extract_code_body`와 `mdx_to_xhtml_inline.py`의 `_extract_code_language`가 유사 로직 포함.

**예상 절감:** ~10줄 | **위험도:** 낮음

---

## 4. 의도적 유지 항목

### 수동 디버깅용 코드

| 항목 | 파일 | 줄수 |
|------|------|------|
| `_debug_markdown` 플래그 및 분기 | `converter/core.py` | ~30줄 |
| `_debug_tags` 빈 집합 및 분기 | `converter/core.py` | ~10줄 |
| 주석 처리된 디버그 코드 (`breakpoint()`) | `converter/core.py:192-195` | ~4줄 |

`# Used when debugging manually` 주석 표기됨 (c7dd721). 개발자 디버깅용으로 유지.

### TODO 주석

`converter/context.py:567, 570` — 의도적 워크어라운드, 사유 기재됨.

---

## 5. 구조적 이슈

1. **전역 가변 상태**: `converter/context.py`의 모듈 수준 전역 변수 → in-process 병렬화 불가. subprocess 격리로 우회 중.
2. **테이블 rowspan/colspan**: 동시 사용 시 셀 위치 추적 오류 가능.

---

## 6. 주의사항

1. **테스트 커버리지:** 310+ 유닛 테스트, 19 E2E 시나리오. 리팩토링 후 전체 테스트 통과 필수.
2. **splice 호환성:** `mdx_block_parser.py`는 `rehydrator.py`의 splice 경로가 의존하므로 원본 구현 유지.
3. **점진적 진행:** Phase별로 나누어 진행, 각 Phase 완료 후 전체 테스트 실행.
