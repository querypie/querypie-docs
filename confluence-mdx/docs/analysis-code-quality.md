# 코드 품질 분석 및 개선 현황

> 최종 업데이트: 2026-02-17
> 대상: `confluence-mdx/` 전체 모듈

## 1. 분석 개요

confluence-mdx 코드베이스의 불필요 코드(dead code)와 중복 코드(duplicate code)를 분석하고,
리팩토링 결과와 남은 개선 항목을 기록합니다.

### 모듈 구조 및 규모

| 모듈 | 파일 수 | 줄 수 | 역할 |
|------|---------|-------|------|
| `converter/` | 4 | ~2,340 | Forward: XHTML → MDX |
| `mdx_to_storage/` | 5 | ~1,170 | Backward: MDX → XHTML |
| `reverse_sync/` | 17 | ~3,290 | 변경 감지 & 패칭 |
| `fetch/` | 9 | ~1,150 | Confluence API 수집 |
| `skeleton/` | 5 | ~2,360 | 구조 추출 |
| CLI 스크립트 | 15 | ~3,870 | 진입점 |
| **합계** | **55** | **~14,180** | |

테스트: 25개 파일, ~8,400줄

### Backward-compat 래퍼

| 파일 | 줄수 | 용도 | 유지 사유 |
|------|------|------|-----------|
| `reverse_sync/text_normalizer.py` | 8 | `text_utils.py` re-export | 외부 참조 호환 |
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

---

## 3. 다음 작업: `converter/sidecar_mapping.py` 삭제

### 배경

`converter/sidecar_mapping.py`(160줄)는 forward converter가 `mapping.yaml`을 생성하는 모듈이다.
그러나 `reverse_sync_cli.py`가 항상 `reverse_sync/sidecar.py`의 `generate_sidecar_mapping()`으로
mapping.yaml을 처음부터 재생성하므로, forward converter가 생성한 mapping.yaml은 프로덕션에서 소비되지 않는다.

| 속성 | `converter/sidecar_mapping.py` | `reverse_sync/sidecar.py` |
|------|-------------------------------|--------------------------|
| 매칭 전략 | 순차 1:1 매칭 | 텍스트 기반 lookahead 매칭 |
| 텍스트 비교 | 없음 (순서만 의존) | `collapse_ws` + `_strip_all_ws` |
| 매칭 정확도 | 이미지/toc 등에서 어긋남 | 정확 |
| 출력 형식 | 파일 직접 쓰기 | YAML 문자열 반환 |

**결론:** `converter/sidecar_mapping.py`는 dead code이며, `reverse_sync/sidecar.py`로 대체 후 삭제한다.

### 수정 대상 파일

| 파일 | 작업 | 영향 범위 |
|------|------|-----------|
| `bin/converter/cli.py` | sidecar 생성을 `reverse_sync/sidecar.py`로 전환 | 10줄 변경 |
| `bin/converter/sidecar_mapping.py` | **삭제** | 160줄 삭제 |
| `docs/architecture.md` | sidecar_mapping.py 관련 설명 업데이트 | 3개 섹션 수정 |

### Step 1: `converter/cli.py` 변경

현재 코드 (196-207줄):

```python
        # Sidecar mapping 생성 (실패해도 변환 자체는 차단하지 않음)
        try:
            from converter.sidecar_mapping import generate_sidecar_mapping
            generate_sidecar_mapping(
                xhtml_content=xhtml_original,
                mdx_content=markdown_content,
                page_id=str(page_v1.get('id')) if page_v1 else None,
                input_dir=input_dir,
                output_file_path=args.output_file,
            )
        except Exception as e:
            logging.warning(f"Sidecar mapping 생성 실패 (변환은 성공): {e}")
```

변경 후:

```python
        # Sidecar mapping 생성 (실패해도 변환 자체는 차단하지 않음)
        try:
            from reverse_sync.sidecar import generate_sidecar_mapping
            page_id = str(page_v1.get('id')) if page_v1 else ''
            sidecar_yaml = generate_sidecar_mapping(xhtml_original, markdown_content, page_id)
            mapping_path = os.path.join(input_dir, 'mapping.yaml')
            with open(mapping_path, 'w', encoding='utf-8') as f:
                f.write(sidecar_yaml)
        except Exception as e:
            logging.warning(f"Sidecar mapping 생성 실패 (변환은 성공): {e}")
```

- `reverse_sync/sidecar.py`의 `generate_sidecar_mapping(xhtml, mdx, page_id)` → YAML 문자열 반환
- 파일 쓰기를 호출측에서 처리
- `page_id` 기본값: `None` → `''` (reverse_sync 버전의 시그니처에 맞춤)

### Step 2: `converter/sidecar_mapping.py` 삭제

삭제되는 함수:

| 함수 | 줄수 | 대체 |
|------|------|------|
| `generate_sidecar_mapping()` | 38줄 | `reverse_sync/sidecar.py:generate_sidecar_mapping()` |
| `_build_mapping_entries()` | 57줄 | `reverse_sync/sidecar.py`의 텍스트 기반 매칭 |
| `_find_callout_range()` | 27줄 | 불필요 (텍스트 매칭이 자동 처리) |
| `_next_index_after()` | 10줄 | 불필요 |

import 참조: `converter/cli.py:198`이 유일한 참조 (Step 1에서 전환 완료).

### Step 3: `architecture.md` 변경

**변환 엔진 모듈 테이블 (109줄):** `converter/sidecar_mapping.py` 행 삭제

**Sidecar 시스템 > Mapping Sidecar 섹션 (396-421줄):** 변경 후:

```markdown
### 1. Mapping Sidecar (`mapping.yaml`)

`reverse_sync/sidecar.py`의 `generate_sidecar_mapping()`이 생성한다.
XHTML 블록과 MDX 블록의 대응 관계를 기록한다.
Forward Converter(`converter/cli.py`)와 Reverse Sync CLI(`reverse_sync_cli.py`) 모두 이 함수를 사용한다.

**생성 과정:**
1. `record_mapping(xhtml)` → XHTML 블록 목록 (`BlockMapping`)
2. `parse_mdx_blocks(mdx)` → MDX 블록 목록
3. 텍스트 기반 lookahead 매칭 → 정규화 텍스트로 XHTML↔MDX 블록 대응
```

**var 디렉토리 mapping.yaml 설명 (563줄):**
`← XHTML↔MDX 매핑 sidecar (Forward Converter 생성)` → `← XHTML↔MDX 매핑 sidecar (reverse_sync/sidecar.py 생성)`

### 검증

1. `cd confluence-mdx && python -m pytest tests/ -x` — 전체 테스트 통과
2. `python bin/converter/cli.py --help` — forward converter 정상 동작
3. `grep -r "sidecar_mapping" bin/` — 참조 없음

### 커밋 계획

커밋 1 — 코드 변경:
```
confluence-mdx: converter/sidecar_mapping.py를 삭제하고 reverse_sync/sidecar.py로 통합합니다
```
- `bin/converter/cli.py` — import 및 호출 변경
- `bin/converter/sidecar_mapping.py` — 삭제

커밋 2 — 문서 업데이트:
```
confluence-mdx: sidecar_mapping.py 삭제를 architecture.md와 code-quality 문서에 반영합니다
```
- `docs/architecture.md` — 3개 섹션 수정
- `docs/analysis-code-quality.md` — 완료 반영

---

## 4. 남은 개선 항목

### 4.1 리스트 파싱/렌더링 중복

**중복 위치:**
- `mdx_to_storage/emitter.py:156-223` — `_parse_list_items()`, tree 기반 렌더링 (`_ListNode`, `depth = indent // 4`)
- `reverse_sync/mdx_to_xhtml_inline.py:116-202` — `_parse_list_items()`, 재귀 렌더링 (dict, raw indent)

**예상 절감:** ~50줄 | **위험도:** 중간 — 들여쓰기 해석 방식이 다름

### 4.2 데이터 모델 분산

`MdxBlock`, `Block`, `BlockMapping`, `SidecarEntry`, `PageEntry`, `BlockChange`, `_ListNode` 등이 5개 이상의 파일에 분산.

**예상 절감:** ~20줄 | **위험도:** 낮음

### 4.3 코드 블록 추출 중복

`emitter.py`의 `_extract_code_body`와 `mdx_to_xhtml_inline.py`의 `_extract_code_language`가 유사 로직 포함.

**예상 절감:** ~10줄 | **위험도:** 낮음

### 4.4 위치 부적절 CLI 래퍼

`reverse_sync/test_verify.py` (~67줄)는 `run-tests.sh`에서만 호출되는 CLI 래퍼.
`run-tests.sh`가 `reverse_sync_cli.py verify`를 직접 호출하도록 변경 후 삭제 가능.

**예상 절감:** ~67줄 | **위험도:** 낮음

---

## 5. 의도적 유지 항목

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

## 6. 구조적 이슈

1. **전역 가변 상태**: `converter/context.py`의 모듈 수준 전역 변수 → in-process 병렬화 불가. subprocess 격리로 우회 중.
2. **테이블 rowspan/colspan**: 동시 사용 시 셀 위치 추적 오류 가능.

---

## 7. 주의사항

1. **테스트 커버리지:** 310+ 유닛 테스트, 19 E2E 시나리오. 리팩토링 후 전체 테스트 통과 필수.
2. **splice 호환성:** `mdx_block_parser.py`는 `rehydrator.py`의 splice 경로가 의존하므로 원본 구현 유지.
3. **점진적 진행:** Phase별로 나누어 진행, 각 Phase 완료 후 전체 테스트 실행.
