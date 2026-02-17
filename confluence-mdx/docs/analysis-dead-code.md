# 불필요한 구현 분석 및 삭제 범위

> 작성일: 2026-02-17
> 대상: `confluence-mdx/` 아래 reverse-sync, mdx-to-storage 등 전체 모듈

## 1. 분석 개요

confluence-mdx 코드베이스에서 삭제 가능한 불필요한 구현을 탐색합니다.
분석 범위는 다음과 같습니다:

- 모듈 수준의 미사용 코드 (전체 파일/디렉토리)
- 함수 수준의 미사용 코드 (개별 함수/클래스)
- 도달 불가능한 코드 경로 (dead code path)
- 주석 처리된 코드 블록
- 미사용 임포트

## 2. 모듈 수준 분석 결과

### 2.1 lossless_roundtrip 디렉토리 — 이미 삭제됨

프로젝트 스펙(querypie-docs-confluence-mdx.md)에서 "fully delete the `lossless_roundtrip` directory after integration"이 목표로 명시되어 있으나, 현재 코드베이스에 해당 디렉토리는 이미 존재하지 않습니다.
`roundtrip_verifier.py` 모듈이 별도로 존재하며, 이는 reverse_sync 파이프라인의 검증 단계로 활용 중입니다.

### 2.2 모듈 수준 미사용 파일 — 해당 없음

모든 `.py` 모듈에 대해 import 참조를 추적한 결과, 완전히 미사용인 모듈은 없습니다.

| 파일 | 상태 | 근거 |
|------|------|------|
| `reverse_sync/confluence_client.py` | **사용 중** | `reverse_sync_cli.py`, `unused_attachments.py`에서 import |
| `reverse_sync/test_verify.py` | **사용 중** | `tests/run-tests.sh`에서 CLI 래퍼로 호출 |
| `reverse_sync/text_transfer.py` | **사용 중** | `patch_builder.py` 경유, 테스트 115줄 |
| `xhtml_beautify_diff.py` | **사용 중** | `reverse_sync_cli.py`, `run-tests.sh` |
| `restore_alt_from_diff.py` | **사용 중** | 독립 실행 유틸리티 |
| `image_status.py` | **사용 중** | `entrypoint.sh` (Docker) |
| `mdx_to_storage_phase1_baseline_cli.py` | **사용 중** | Task 1.7 baseline CLI, 테스트 존재 |
| `mdx_to_storage_xhtml_verify_cli.py` | **사용 중** | `mdx_to_storage_baseline.py`에서 호출 |

## 3. 함수 수준 불필요 코드

### 3.1 [삭제 대상] `_debug_markdown` 플래그 및 관련 분기 — `converter/core.py`

**위치:**
- `core.py:577` — `MultiLineParser.__init__`에서 `self._debug_markdown = False` 설정
- `core.py:614, 620, 626, 630` — `_debug_markdown` 조건 분기
- `core.py:722, 725` — 추가 조건 분기
- `core.py:1356` — `ConfluenceToMarkdown`에서도 동일 플래그

**문제:** `_debug_markdown`이 항상 `False`로 설정되어, 해당 조건 분기의 코드가 절대 실행되지 않습니다.
외부에서 이 플래그를 변경하는 코드도 없습니다.

**삭제 범위:** `_debug_markdown` 관련 초기화 및 모든 `if self._debug_markdown:` 조건 블록

**영향도:** 낮음 (디버그 전용 코드, 프로덕션 동작 무관)

**주의:** 개발 시 디버깅 용도로 활용될 수 있으므로, 삭제 대신 `logging.debug()`로 전환하는 방법도 고려 가능합니다.

### 3.2 [삭제 대상] `_debug_tags` 빈 집합 — `converter/core.py`

**위치:**
- `core.py:131-133` — `SingleLineParser.__init__`에서 `self._debug_tags = {}` 초기화
- `core.py:180, 385` — `_debug_tags` 검사 조건문

**문제:** 빈 집합으로 초기화되어 있고, 코드 어디에서도 값을 추가하지 않습니다.
`if tag in self._debug_tags:` 조건이 항상 `False`입니다.

**삭제 범위:** `_debug_tags` 관련 초기화 및 모든 조건 블록

**영향도:** 낮음

### 3.3 [검토 대상] CLI 래퍼 통합 가능성

**대상 파일:**
- `mdx_to_storage_phase1_baseline_cli.py` (80줄)
- `mdx_to_storage_xhtml_cli.py` (193줄)
- `mdx_to_storage_xhtml_verify_cli.py` (173줄)

**현황:**
`mdx_to_storage_xhtml_cli.py`는 `convert`, `verify`, `batch-verify` 서브커맨드를 제공합니다.
`mdx_to_storage_phase1_baseline_cli.py`는 `batch-verify`와 유사한 baseline 기록 기능을 제공합니다.
`mdx_to_storage_xhtml_verify_cli.py`는 standalone 검증 도구입니다.

**권장:** 3개의 CLI를 단일 진입점으로 통합하면 약 100줄 절감 가능하나, 각각이 현재 테스트 및 CI 스크립트에서 참조되고 있으므로, 리팩토링 시 import 경로 업데이트가 필요합니다. 당장의 삭제 대상은 아니며, 중복 코드 리팩토링과 함께 진행하는 것을 권장합니다.

## 4. 도달 불가능한 코드 경로

### 4.1 [삭제 대상] 주석 처리된 디버그 코드 — `converter/core.py:192-195`

```python
# DEBUG(JK)
# if tag in self._debug_tags:
#     breakpoint()
```

**권장:** `_debug_tags` 자체를 삭제할 경우 함께 제거합니다.

## 5. TODO/FIXME 주석 정리

### 5.1 [유지] context.py의 TODO 주석

**위치:** `converter/context.py:567, 570`

```python
# TODO(JK): Do not include style attribute of Tag for now.
# Or, npm run build fails.
# TODO(JK): Do not include class attribute of Tag for now.
# class="numberingColumn" might be the cause of broken table rendering.
```

**판단:** 의도적 워크어라운드이며, 명확한 사유가 기재되어 있습니다. 삭제 대상이 아닙니다.

## 6. 삭제 범위 요약

| 항목 | 파일 | 예상 삭제 줄수 | 우선순위 |
|------|------|---------------|---------|
| `_debug_markdown` 플래그 및 분기 | `converter/core.py` | ~30줄 | 낮음 |
| `_debug_tags` 빈 집합 및 분기 | `converter/core.py` | ~10줄 | 낮음 |
| 주석 처리된 디버그 코드 | `converter/core.py` | ~4줄 | 낮음 |
| **합계** | | **~44줄** | |

## 7. 결론

confluence-mdx 코드베이스는 전반적으로 잘 관리되고 있으며, 모듈 수준의 미사용 코드는 없습니다.
함수 수준에서 삭제 가능한 dead code는 `converter/core.py`의 디버그 관련 코드(약 44줄)에 한정됩니다.

코드 품질 개선의 더 큰 효과는 **중복 코드 리팩토링**(별도 문서 `analysis-duplicate-code.md` 참조)에서 얻을 수 있습니다.
