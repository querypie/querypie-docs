# Reverse Sync 재구성 후 삭제 대상 범위

> 작성일: 2026-03-15
> 갱신일: 2026-03-16
> 기준 브랜치: `main`
> 기준 커밋: `e40877afec06306bec99b86f15f492f88177c424`
> 선행 문서:
> - `docs/plans/2026-03-13-reverse-sync-reconstruction-design.md`
> - `docs/plans/2026-03-13-reverse-sync-reconstruction-design-review.md`

## 1. 문서 목적

이 문서는 reverse-sync 재구성 경로가 기본 동작이 된 뒤 정리할 legacy 코드와 테스트 범위를 별도로 기록한다.

기존 설계 문서에서 삭제 대상 설명을 분리한 이유는 두 가지다.

1. 설계 본문은 "무엇을 새로 만들 것인가"에 집중하고, 이 문서는 "무엇을 언제 제거할 것인가"를 다룬다.
2. 삭제 범위는 파일 단위, 함수 단위, 테스트 단위까지 내려가므로 별도 추적 문서가 더 적합하다.

이 문서는 즉시 삭제 지시서가 아니다. 아래의 게이트를 통과한 뒤 단계적으로 적용하는 cleanup 범위 문서다.

## 2. 삭제 시작 조건

아래 네 조건이 충족되기 전에는 본 문서의 대상 코드를 기본 경로에서 제거하지 않는다.

1. `tests/testcases` 의 16개 changed golden 이 새 reconstruction 경로로 green 이다.
2. `tests/reverse-sync/pages.yaml` 의 `expected_status: pass` 케이스가 유지된다.
3. unsupported 구조는 silent corruption 없이 명시적 fail 로 전환된다.
4. runtime planning 이 `mapping.yaml` 없이 `RoundtripSidecar v3` 중심으로 동작한다.

조건 충족 전 허용 범위:

- 새 reconstruction 경로 옆에 legacy fallback 을 일시적으로 유지
- debug flag 뒤에서 legacy path 호출
- 비교 실험용 테스트 유지

조건 충족 후 원칙:

- 동일 책임의 구 경로를 기본 동작에 남기지 않는다.
- 삭제가 어렵다면 최소한 import 경로와 CLI 기본 동작에서는 분리한다.
- cleanup 은 기능 PR과 별도 PR 로 분리할 수 있다.

## 3. 대상 분류

정리 대상은 네 묶음이다.

1. heuristic text transfer 계층
2. modified patch planning 계층
3. `mapping.yaml` runtime 계층
4. 관련 테스트와 debug artifact 생성 경로

## 4. 완전 삭제 대상

이 섹션의 항목은 새 reconstruction 경로가 정착하면 역할이 전면 대체되는 코드다.

### 4.1 `bin/reverse_sync/text_transfer.py`

현재 책임:

- `transfer_text_changes(mdx_old, mdx_new, xhtml_text)` 로 MDX plain text 변경을 XHTML plain text에 이식
- 문자 단위 정렬과 부분 치환을 통해 XHTML 구조는 유지하고 텍스트만 바꾸는 전략 제공

삭제 이유:

- 새 설계의 기본 경로는 text transfer 가 아니라 whole-fragment reconstruction 이다.
- inline anchor 보존은 plain-text offset + DOM insertion 으로 대체된다.
- callout, list, table, inline image/link 같이 XHTML 고유 구조가 중요한 블록에서 이 함수는 구조를 이해하지 못한다.

현재 의존 경로:

- `bin/reverse_sync/patch_builder.py`
- `bin/reverse_sync/list_patcher.py`
- `tests/test_reverse_sync_text_transfer.py`
- `tests/test_reverse_sync_cli.py` 의 helper 테스트 일부

함께 삭제 또는 교체할 테스트:

- `tests/test_reverse_sync_text_transfer.py`
- `tests/test_reverse_sync_cli.py` 내 `align_chars`, `find_insert_pos`, `transfer_text_changes` 관련 테스트
- `tests/test_reverse_sync_patch_builder.py` 중 `new_plain_text` 결과를 전제로 하는 케이스 일부

삭제 시점:

- Phase 3 완료 후
- paragraph/list anchor reconstruction 이 도입되고
- `new_plain_text` modify path 가 기본 경로에서 제거된 뒤

### 4.2 `bin/reverse_sync/list_patcher.py`

현재 책임:

- list 변경을 item-level patch 또는 `new_inner_xhtml` 재생성으로 처리
- 부모 list 매핑을 찾은 뒤 경우에 따라 `transfer_text_changes()` 로 폴백
- `build_list_item_patches()` 를 통해 list 전용 patch 생성

삭제 이유:

- 새 설계에서 list 는 list tree + sidecar reconstruction metadata + child order 기반으로 재구성한다.
- 현재 구현은 list 자체를 구조적으로 이해하기보다 flat item patch 와 text transfer 조합에 가깝다.
- nested list, duplicate item, inline image 가 섞인 항목에서 전략이 계속 분기한다.

현재 의존 경로:

- `bin/reverse_sync/patch_builder.py`
- `tests/test_reverse_sync_patch_builder.py`
- `tests/test_reverse_sync_cli.py`

함께 삭제 또는 교체할 테스트:

- `tests/test_reverse_sync_patch_builder.py` 의 `build_list_item_patches` 관련 테스트 전부
- `tests/test_reverse_sync_cli.py` 의 `build_list_item_patches` 직접 호출 테스트

삭제 시점:

- Phase 3 의 nested list reconstruction 완료 후
- list/image 혼합 fixture 가 새 경로에서 green 인 뒤

### 4.3 `bin/reverse_sync/table_patcher.py`

현재 책임:

- table 변경을 row 단위 plain-text patch 로 생성
- `build_table_row_patches()` 와 보조 유틸로 표 변경을 containing patch 로 환원

핵심 함수:

- `build_table_row_patches()`
- `split_table_rows()`
- `normalize_table_row()`
- `is_markdown_table()`

삭제 이유:

- 새 설계에서 table 은 clean block 이며 whole-fragment replacement 대상이다.
- row-level text patch 는 Confluence 링크, macro, attribute 를 보존하는 구조적 방법이 아니다.
- table 은 emitter + lost-info 복원 경로로 처리하는 편이 단순하고 일관적이다.

현재 의존 경로:

- `bin/reverse_sync/patch_builder.py`
- `tests/test_reverse_sync_patch_builder.py`

함께 삭제 또는 교체할 테스트:

- `tests/test_reverse_sync_patch_builder.py` 의 table patch 전용 테스트
- table row normalization 을 전제로 하는 heuristic 검증 테스트

삭제 시점:

- Phase 2 clean block replacement 완료 후
- table golden 이 새 경로에서 green 인 뒤

### 4.4 `bin/reverse_sync/inline_detector.py`

현재 책임:

- inline 마커 변경과 경계 이동을 감지
- legacy patch 경로에서 text patch 와 `new_inner_xhtml` 재생성 간 분기 기준 제공

핵심 함수:

- `has_inline_format_change()`
- `has_inline_boundary_change()`

삭제 이유:

- 새 planner 는 inline marker 변화 자체가 아니라 block kind 와 reconstruction metadata 를 기준으로 분기한다.
- inline code/bold/link 의 변경은 fragment reconstruction 이 직접 처리해야 하며, 별도 heuristic 감지기 없이도 동작해야 한다.

현재 의존 경로:

- `tests/test_reverse_sync_patch_builder.py`
- legacy patch 의사결정 로직

함께 삭제 또는 교체할 테스트:

- `tests/test_reverse_sync_patch_builder.py` 의 `has_inline_format_change` 관련 테스트
- `tests/test_reverse_sync_patch_builder.py` 의 `has_inline_boundary_change` 관련 테스트

삭제 시점:

- Phase 2 이후 direct/list heuristic 분기가 planner 로 대체된 뒤

## 5. 대폭 축소 대상

이 섹션의 항목은 파일 전체 삭제가 아니라, legacy 책임을 덜어내고 일부 핵심만 남길 가능성이 큰 코드다.

### 5.1 `bin/reverse_sync/patch_builder.py`

현재 책임:

- diff 와 mapping 을 결합해 patch 목록 생성
- `direct`, `containing`, `list`, `table`, `skip` 전략 선택
- insert/delete 생성
- 일부 modified block 에 `new_inner_xhtml` 생성
- 나머지는 `new_plain_text` 기반 text patch 생성

삭제 또는 이동 대상 책임:

- `_flush_containing_changes()`
- `_resolve_mapping_for_change()`
- `transfer_text_changes()` 호출 기반 modified path
- list/table 전용 분기
- `find_mapping_by_sidecar()` 중심 mapping lookup 분기

남길 가능성이 있는 책임:

- add/delete orchestration
- alignment 를 이용한 insert anchor 계산

권장 최종 형태:

- `reconstruction_planner.py` 로 전략 판단 이동
- `patch_builder.py` 는 thin wrapper 또는 insert/delete 전용 helper 로 축소
- 축소가 애매하면 파일 삭제 후 planner 내부로 흡수

함께 정리할 테스트:

- `tests/test_reverse_sync_patch_builder.py` 의 heuristic branch 검증 대다수
- `tests/test_reverse_sync_structural.py` 중 구 patch shape 에 의존하는 assertion

### 5.2 `bin/reverse_sync/xhtml_patcher.py`

현재 책임:

- `insert`, `delete`, `modify` patch 적용
- `modify` 에서 두 경로를 지원
  - `old_plain_text` + `new_plain_text`
  - `new_inner_xhtml`
- CDATA 복원

삭제 대상 책임:

- `new_plain_text` 기반 text-only modify path
- `_apply_text_changes()` 와 그에 딸린 text patch helper

남겨야 할 책임:

- XPath resolve
- `insert`
- `delete`
- 새 `replace_fragment`
- CDATA 복원

권장 최종 형태:

- "텍스트 패처"가 아니라 "fragment-level DOM patcher"
- modify 는 `replace_fragment` 중심으로 단순화

함께 정리할 테스트:

- `tests/test_reverse_sync_xhtml_patcher.py` 의 `new_plain_text` 중심 테스트
- `tests/test_reverse_sync_mdx_to_xhtml_inline.py` 에서 patch shape 을 전제하는 일부 테스트

### 5.3 `bin/reverse_sync/mdx_to_xhtml_inline.py`

현재 책임:

- `mdx_block_to_inner_xhtml()`
- `mdx_block_to_xhtml_element()`
- innerHTML 교체에 맞춘 block 변환

삭제 후보 책임:

- `mdx_block_to_inner_xhtml()`
- innerHTML 패치에 최적화된 변환 로직 전반

이유:

- 새 설계의 기본 emitter 는 `mdx_to_storage.emit_block()` 이다.
- innerHTML 단위 치환은 clean block replacement 와 container reconstruction 의 최종 방향과 맞지 않는다.

남길 가능성이 있는 책임:

- migration 기간의 compatibility wrapper
- 특정 테스트에서만 쓰는 임시 adapter

함께 정리할 테스트:

- `tests/test_reverse_sync_mdx_to_xhtml_inline.py` 의 innerHTML 중심 테스트
- `tests/test_reverse_sync_cli.py` 내 `new_inner_xhtml` 생성 전제 테스트

### 5.4 `bin/reverse_sync/sidecar.py` 의 `mapping.yaml` 계층

현재 책임:

- block-level roundtrip sidecar 와 별개로 `mapping.yaml` 계층을 함께 보유
- `SidecarEntry`, `SidecarChildEntry`
- `load_sidecar_mapping()`
- `build_mdx_to_sidecar_index()`
- `build_xpath_to_mapping()`
- `generate_sidecar_mapping()`
- `find_mapping_by_sidecar()`

왜 축소 대상인가:

- `RoundtripSidecar v3` 가 runtime primary artifact 로 올라가면 이 계층은 중복 책임이 된다.
- 현재는 reverse-sync CLI 와 converter 에서 legacy routing artifact 로 사용한다.
- `#917`에서 strict v3 sidecar 정리는 이미 끝났으므로, 남은 cleanup 초점은 v2 호환이 아니라 `mapping.yaml` runtime 계층 제거다.

정리 방향:

- sidecar core 와 mapping layer 를 논리적으로 분리
- 최종적으로 mapping layer 는 debug 전용 또는 optional artifact

함께 정리할 테스트:

- `tests/test_reverse_sync_sidecar.py` 의 mapping.yaml 관련 절반 이상
- `tests/test_lost_info_collector.py` 의 `generate_sidecar_mapping()` 연동 테스트 일부
- `tests/test_reverse_sync_e2e.py` 의 mapping.yaml 생성 전제 경로

## 6. CLI 와 호출 경로 정리 대상

### 6.1 `bin/reverse_sync_cli.py`

현재 legacy 연동:

- `generate_sidecar_mapping()` 호출
- `SidecarEntry`, `SidecarChildEntry` import
- mapping artifact 생성 및 사용
- `patch_builder.py` + `xhtml_patcher.py` 기반 patch 적용

정리 목표:

- runtime 기본 경로에서 `mapping.yaml` 생성 제거
- reconstruction planner + sidecar v3 중심 orchestration 으로 대체
- mapping artifact 는 `--debug-mapping` 같은 명시적 옵션 뒤로 이동 가능

### 6.2 `bin/converter/cli.py`

현재 legacy 연동:

- forward converter 성공 후 `generate_sidecar_mapping()` 호출

정리 목표:

- converter 성공과 mapping.yaml 생성의 결합 해제
- sidecar v3 또는 debug artifact 생성 여부를 옵션으로 분리

## 7. 테스트 정리 대상

cleanup 이후 제거 또는 대체해야 할 테스트 묶음을 명시한다.

### 7.1 제거 대상

- `tests/test_reverse_sync_text_transfer.py`
- `tests/test_reverse_sync_patch_builder.py` 의 heuristic branch 중심 테스트 다수
- `tests/test_reverse_sync_xhtml_patcher.py` 의 `new_plain_text` modify 테스트
- `tests/test_reverse_sync_mdx_to_xhtml_inline.py` 의 innerHTML 중심 테스트 다수
- `tests/test_reverse_sync_cli.py` 의 text-transfer helper 직접 테스트
- `tests/test_reverse_sync_sidecar.py` 의 mapping.yaml 전용 테스트 다수

### 7.2 대체 대상

아래 테스트 묶음으로 대체한다.

- `tests/test_reverse_sync_reconstruction_offsets.py`
- `tests/test_reverse_sync_reconstruction_insert.py`
- `tests/test_reverse_sync_reconstruct_paragraph.py`
- `tests/test_reverse_sync_reconstruct_list.py`
- `tests/test_reverse_sync_reconstruct_container.py`
- `tests/test_reverse_sync_reconstruction_goldens.py`

## 8. 유지 대상

cleanup 이후에도 유지해야 할 코드를 분리해 둔다.

### 8.1 유지: `bin/reverse_sync/mapping_recorder.py`

이유:

- XHTML 분석 도구로는 계속 유용하다.
- callout/ADF child xpath 추출, fixture 분석, debug helper 역할이 남는다.

단, 역할은 runtime truth 가 아니라 analysis/debug helper 로 한정한다.

### 8.2 유지: `bin/reverse_sync/lost_info_patcher.py`

이유:

- link, image, emoticon, filename, ADF extension 복원은 reconstruction 이후에도 필요하다.
- 다만 text patch helper 와 묶이지 않고 fragment post-process 단계로 고정해야 한다.

### 8.3 유지: `bin/reverse_sync/sidecar.py` 의 roundtrip core

유지 범위:

- `RoundtripSidecar`
- `SidecarBlock`
- `build_sidecar()`
- `load_sidecar()`
- `write_sidecar()`
- `verify_sidecar_integrity()`
- `build_sidecar_identity_index()`
- `find_sidecar_block_by_identity()`

즉 sidecar 모듈 전체 삭제가 아니라, 그 안의 legacy mapping 계층 분리가 목표다.

## 9. 실제 정리 순서

권장 순서는 아래와 같다.

1. Phase 2 clean block replacement 구현
2. Phase 3 inline-anchor/list reconstruction 구현
3. Phase 4 container reconstruction 구현
4. changed golden 16개와 `expected_status: pass` 회귀 케이스 green 확보
5. `patch_builder.py` 의 modified path 를 reconstruction planner 로 전환
6. `xhtml_patcher.py` 에서 `new_plain_text` modify path 제거
7. `text_transfer.py`, `inline_detector.py` 삭제
8. `list_patcher.py`, `table_patcher.py` 삭제
9. `mdx_to_xhtml_inline.py` 축소 또는 삭제
10. `mapping.yaml` runtime 계층을 CLI 기본 동작에서 분리
11. 관련 테스트 삭제 및 reconstruction 테스트로 교체

이 순서를 지키는 이유:

- 먼저 새 경로를 green 으로 만든 뒤 구 경로를 제거해야 한다.
- `mapping.yaml` 계층은 가장 마지막까지 남을 가능성이 높다.
- 테스트 삭제가 코드 삭제보다 먼저 오면 회귀 검출 능력을 잃는다.

## 10. 판단

삭제 범위는 넓지만, 모든 항목이 같은 시점에 제거되는 것은 아니다. 실제로는 아래 순서로 흡수된다.

- 가장 먼저 사라질 것: `text_transfer.py`, `inline_detector.py`
- 다음으로 사라질 것: `list_patcher.py`, `table_patcher.py`
- 마지막까지 남을 수 있는 것: `patch_builder.py` 일부, `xhtml_patcher.py` 일부, `mapping.yaml` 계층

즉 cleanup 의 핵심은 "파일 수를 줄이는 것"이 아니라, runtime 기본 경로에서 heuristic text patch 체인을 걷어내고 sidecar v3 + reconstruction 중심 구조로 책임을 재배치하는 것이다.
