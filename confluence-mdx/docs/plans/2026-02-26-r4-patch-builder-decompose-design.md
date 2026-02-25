# R4: patch_builder.py 구조 분해 설계

> 작성일: 2026-02-26
> 선행 분석: `docs/analysis-reverse-sync-refactoring.md`

## 목표

`patch_builder.py` (719줄)를 책임 단위로 분해하여 유지보수성을 개선한다.
**동작 변경 0** — 함수 이동 + import 변경만 수행한다.

부수 정리로 R7(`_iter_block_children` 중복 제거), R8(`NON_CONTENT_TYPES` 상수 통합)도 포함한다.

## 결정 사항

| 항목 | 결정 |
|------|------|
| 접근법 | Bottom-up (모듈 추출 → 후속 PR에서 전략 전환) |
| 동작 변경 | 없음 (순수 구조 리팩토링) |
| 테스트 | 기존 전체 통과 유지, 매 단계 `make test` 검증 |
| 후속 작업 | R1(재생성 전략 전환)은 별도 PR |

## 모듈 분리 계획

### 새 모듈

| 모듈 | 추출 함수 | 책임 |
|------|-----------|------|
| `inline_detector.py` | `_extract_inline_markers`, `_strip_positions`, `_extract_marker_spans`, `_extract_between_marker_texts`, `has_inline_format_change`, `has_inline_marker_added`, regex 상수 4개 | 인라인 포맷 변경 감지 |
| `list_patcher.py` | `build_list_item_patches`, `split_list_items`, `extract_list_marker_prefix`, `_resolve_child_mapping` | 리스트 블록 패치 생성 |
| `table_patcher.py` | `build_table_row_patches`, `split_table_rows`, `normalize_table_row`, `is_markdown_table` | 테이블 블록 패치 생성 |

### 잔여 patch_builder.py (~330줄)

`build_patches`, `_resolve_mapping_for_change`, `_find_containing_mapping`, `_flush_containing_changes`, `_build_delete_patch`, `_build_insert_patch`, `_find_insert_anchor`

### 부수 정리

| # | 항목 | 내용 |
|---|------|------|
| R7 | `_iter_block_children()` | `xhtml_patcher.py` 로컬 복사본 → `mapping_recorder.py`에서 import |
| R8 | `NON_CONTENT_TYPES` | `block_diff.py`, `patch_builder.py`, `sidecar.py`, `rehydrator.py` 4곳 → 단일 정의 |

## 테스트 영향

- import 경로 변경만 필요 (테스트 로직 수정 불필요)
- 주요 영향 파일: `test_reverse_sync_patch_builder.py` (1,358줄)
- 매 모듈 추출 후 전체 테스트 실행으로 회귀 방지

## 구현 순서

1. R8: `NON_CONTENT_TYPES` 상수를 공용 위치로 추출, 4곳에서 import
2. R7: `xhtml_patcher.py`의 `_iter_block_children` → `mapping_recorder.py` import
3. `inline_detector.py` 추출
4. `list_patcher.py` 추출
5. `table_patcher.py` 추출
6. 전체 테스트 + 최종 검증
