# 코드 품질 분석 및 개선 현황

> 작성일: 2026-02-17
> 대상: `confluence-mdx/` 아래 reverse-sync, mdx-to-storage, converter 등 전체 모듈

## 1. 분석 개요

confluence-mdx 코드베이스의 불필요한 코드(dead code)와 중복 코드(duplicate code)를 분석하고,
리팩토링 결과를 기록합니다.

**분석 범위:**
- 모듈 수준의 미사용 코드 (전체 파일/디렉토리)
- 함수 수준의 미사용 코드 (개별 함수/클래스)
- 도달 불가능한 코드 경로 (dead code path)
- 모듈 간 중복/유사 구현
- 주석 처리된 코드 블록 및 TODO/FIXME

### 모듈 구조 개요

```
bin/
├── converter/          # Forward: XHTML → MDX (2,498줄)
├── mdx_to_storage/     # Backward: MDX → XHTML (1,139줄)
├── reverse_sync/       # 변경 감지 & 패칭 (2,929줄)
├── fetch/              # Confluence API (1,149줄)
├── skeleton/           # 구조 추출 (2,364줄)
└── (CLI 스크립트들)
```

---

## 2. 불필요 코드 (Dead Code) 분석

### 2.1 모듈 수준 미사용 파일 — 해당 없음

모든 `.py` 모듈에 대해 import 참조를 추적한 결과, 완전히 미사용인 모듈은 없습니다.

| 파일 | 상태 | 근거 |
|------|------|------|
| `reverse_sync/confluence_client.py` | **사용 중** | `reverse_sync_cli.py`, `unused_attachments.py`에서 import |
| `reverse_sync/test_verify.py` | **사용 중** | `tests/run-tests.sh`에서 CLI 래퍼로 호출 |
| `reverse_sync/text_transfer.py` | **사용 중** | `patch_builder.py` 경유, 테스트 115줄 |
| `xhtml_beautify_diff.py` | **사용 중** | `reverse_sync_cli.py`, `run-tests.sh` |
| `restore_alt_from_diff.py` | **사용 중** | 독립 실행 유틸리티 |
| `image_status.py` | **사용 중** | `entrypoint.sh` (Docker) |
| `mdx_to_storage_phase1_baseline_cli.py` | **삭제됨** | `mdx_to_storage_xhtml_cli.py baseline` 서브커맨드로 통합 |
| `mdx_to_storage_xhtml_verify_cli.py` | **삭제됨** | `mdx_to_storage_xhtml_cli.py batch-verify`로 통합 |

참고: `lossless_roundtrip` 디렉토리는 이미 삭제되었습니다.
`roundtrip_verifier.py`가 별도 존재하며, reverse_sync 파이프라인의 검증 단계로 활용 중입니다.

### 2.2 수동 디버깅용 코드 — 유지

아래 항목들은 프로덕션에서 실행되지 않지만, 개발자가 수동으로 활성화하여 디버깅하는 용도로 의도적으로 유지합니다.
(`# Used when debugging manually` 주석 추가됨, c7dd721)

| 항목 | 파일 | 줄수 |
|------|------|------|
| `_debug_markdown` 플래그 및 분기 | `converter/core.py` | ~30줄 |
| `_debug_tags` 빈 집합 및 분기 | `converter/core.py` | ~10줄 |
| 주석 처리된 디버그 코드 (`breakpoint()`) | `converter/core.py:192-195` | ~4줄 |

### 2.3 TODO/FIXME 주석 — 유지

`converter/context.py:567, 570`의 TODO 주석은 의도적 워크어라운드이며, 명확한 사유가 기재되어 있습니다.

### 2.4 미처리 항목

| 항목 | 파일 | 예상 삭제 줄수 | 신뢰도 |
|------|------|---------------|--------|
| 위치 부적절 CLI 래퍼 | `reverse_sync/test_verify.py` | ~67줄 | 높음 |

`run-tests.sh`가 `reverse_sync_cli.py verify`를 직접 호출하도록 변경 후 삭제 가능합니다.

---

## 3. 중복 코드 분석 및 리팩토링

### 3.1 [완료] CLI 통합 — `mdx_to_storage_xhtml_cli.py`를 단일 진입점으로

`mdx_to_storage_xhtml_cli.py`를 단일 CLI 진입점으로 확장하여 `convert`, `verify`, `batch-verify`, `final-verify`, `baseline` 5개 서브커맨드를 제공합니다.

삭제된 파일:
- `mdx_to_storage_xhtml_verify_cli.py` (173줄) → `batch-verify` 서브커맨드로 흡수
- `mdx_to_storage_phase1_baseline_cli.py` (80줄) → `baseline` 서브커맨드로 흡수
- `reverse_sync/mdx_to_storage_final_verify.py` (137줄) → `final-verify` 서브커맨드로 흡수
- `reverse_sync/mdx_to_storage_baseline.py` (118줄) → `baseline` 서브커맨드에 인라인

**삭제 줄수:** ~508줄

### 3.2 [완료] MDX 블록 파서 통합

**중복 파일:**
- `reverse_sync/mdx_block_parser.py` (129줄) — `MdxBlock`, `parse_mdx_blocks()`
- `mdx_to_storage/parser.py` (473줄) — `Block`, `parse_mdx()`

**실행 결과:** `parser.py`의 `Block`에 `line_start`/`line_end` 필드를 추가하고, `parse_mdx_blocks()` 호환 함수를 추가했습니다. `patch_builder.py`, `block_diff.py`, `sidecar.py`, `reverse_sync_cli.py`, `sidecar_mapping.py`의 import를 `mdx_to_storage.parser`로 전환했습니다.

**주의:** `mdx_block_parser.py`는 원본 구현을 유지합니다 — `rehydrator.py`의 splice 경로가 이 파서의 블록 분할에 의존하며, sidecar의 `mdx_content_hash`가 이 파서 기준으로 생성되었기 때문입니다.

### 3.3 [완료] 인라인 변환기 통합

**중복 파일:**
- `reverse_sync/mdx_to_xhtml_inline.py` (270줄) — LinkResolver 통합, heading 전용 처리
- `mdx_to_storage/inline.py` (94줄) — 경량 인라인 변환

**실행 결과:** `mdx_to_xhtml_inline.py`의 자체 `_convert_inline()`을 삭제하고 `mdx_to_storage.inline.convert_inline`을 import하여 사용하도록 변경했습니다. 블록 레벨 함수(`mdx_block_to_inner_xhtml()`, `mdx_block_to_xhtml_element()`)는 유지합니다.

### 3.4 [완료] 텍스트 정규화 유틸리티 통합

**중복 파일:**
- `reverse_sync/text_normalizer.py` (97줄)
- `bin/text_utils.py` (81줄)

**실행 결과:** `text_normalizer.py`의 함수들(`strip_for_compare`, `normalize_mdx_to_plain`, `collapse_ws`, `strip_list_marker`, `EMOJI_RE`)을 `text_utils.py`로 이동했습니다. `text_normalizer.py`는 backward-compat re-export 래퍼로 전환했습니다.

### 3.5 [완료] Regex 패턴 정리

`emitter.py`의 `_HEADING_LINE_PATTERN`을 `parser.py`의 `HEADING_PATTERN`에서 import하도록 변경했습니다.

---

## 4. 미착수 리팩토링 항목

### 4.1 리스트 파싱/렌더링 중복

**중복 파일:**
- `mdx_to_storage/emitter.py:156-223` — `_parse_list_items()`, tree 기반 렌더링
- `reverse_sync/mdx_to_xhtml_inline.py:116-202` — `_parse_list_items()`, 재귀 렌더링

차이점: emitter.py는 `depth = indent // 4` (레벨 단위)와 `_ListNode` 클래스 사용, mdx_to_xhtml_inline.py는 raw indent (공백 수)와 dict 사용.

**예상 절감:** ~50줄

### 4.2 사이드카 매핑 생성 중복

**중복 파일:**
- `converter/sidecar_mapping.py` (160줄) — 순차 1:1 매칭
- `reverse_sync/sidecar.py` (309줄) — 텍스트 기반 lookahead 매칭

매칭 전략이 다르므로(순서 vs 텍스트), 통합 시 두 전략을 모두 보존해야 합니다.

**예상 절감:** ~40줄

### 4.3 데이터 모델 분산

`MdxBlock`, `Block`, `BlockMapping`, `SidecarEntry`, `PageEntry`, `BlockChange`, `_ListNode` 등이 5개 이상의 파일에 분산되어 있습니다.

**예상 절감:** ~20줄

### 4.4 코드 블록 추출 중복

`emitter.py`의 `_extract_code_body`와 `mdx_to_xhtml_inline.py`의 `_extract_code_language`가 유사한 로직을 포함합니다.

**예상 절감:** ~10줄

---

## 5. 전체 현황 요약

### 완료된 작업

| 항목 | 내용 | 절감 |
|------|------|------|
| CLI 통합 | 4개 파일 → `mdx_to_storage_xhtml_cli.py`로 통합 | ~508줄 삭제 |
| MDX 파서 통합 | `parser.py`에 호환 API 추가, import 전환 | 중복 감소 |
| 인라인 변환기 통합 | `_convert_inline()` → `convert_inline` import | ~50줄 |
| 텍스트 유틸리티 통합 | `text_normalizer.py` → `text_utils.py` | ~40줄 |
| Regex 패턴 정리 | `emitter.py` → `parser.py`에서 import | 중복 제거 |

### 미착수 항목

| 우선순위 | 대상 | 예상 절감 |
|---------|------|----------|
| 4 | 리스트 파싱/렌더링 통합 | ~50줄 |
| 5 | 사이드카 매핑 공통 골격 추출 | ~40줄 |
| 6 | 데이터 모델 통합 | ~20줄 |
| 7 | 코드 블록 추출 공통화 | ~10줄 |

### 주의사항

1. **테스트 커버리지:** 310+ 유닛 테스트, 19 E2E 시나리오가 존재합니다. 리팩토링 후 전체 테스트 통과를 반드시 확인해야 합니다.
2. **splice 호환성:** `mdx_block_parser.py`는 `rehydrator.py`의 splice 경로가 의존하므로 원본 구현을 유지해야 합니다.
3. **점진적 진행:** Phase 별로 나누어 진행하고, 각 Phase 완료 후 전체 테스트를 실행하는 것을 권장합니다.
