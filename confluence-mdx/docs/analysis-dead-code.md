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
| `mdx_to_storage_phase1_baseline_cli.py` | **삭제됨** | `mdx_to_storage_xhtml_cli.py baseline` 서브커맨드로 통합 |
| `mdx_to_storage_xhtml_verify_cli.py` | **삭제됨** | `mdx_to_storage_xhtml_cli.py batch-verify`로 통합 |

## 3. 함수 수준 불필요 코드

### 3.1 [유지] `_debug_markdown` 플래그 및 관련 분기 — `converter/core.py`

**위치:**
- `core.py:577` — `MultiLineParser.__init__`에서 `self._debug_markdown = False` 설정
- `core.py:614, 620, 626, 630` — `_debug_markdown` 조건 분기
- `core.py:722, 725` — 추가 조건 분기
- `core.py:1356` — `ConfluenceToMarkdown`에서도 동일 플래그

**현황:** `_debug_markdown`이 항상 `False`로 설정되어 프로덕션에서는 실행되지 않으나,
개발자가 수동으로 `True`로 변경하여 디버깅하는 용도로 의도적으로 유지됩니다.
(`# Used when debugging manually` 주석 추가됨, c7dd721)

**판단:** 삭제 대상이 아닙니다.

### 3.2 [유지] `_debug_tags` 빈 집합 — `converter/core.py`

**위치:**
- `core.py:131-133` — `SingleLineParser.__init__`에서 `self._debug_tags = {}` 초기화
- `core.py:180, 385` — `_debug_tags` 검사 조건문

**현황:** 빈 집합으로 초기화되어 있고 프로덕션에서는 조건이 항상 `False`이나,
개발자가 수동으로 태그명을 추가하여 특정 태그의 파싱 과정을 디버깅하는 용도입니다.
`_debug_markdown`과 동일한 패턴의 수동 디버깅 도구입니다.

**판단:** 삭제 대상이 아닙니다.

### 3.3 [완료] CLI 통합 — `mdx_to_storage_xhtml_cli.py`를 단일 진입점으로

**실행 결과:**
- `mdx_to_storage_xhtml_cli.py`를 단일 CLI 진입점으로 확장했습니다.
- `convert`, `verify`, `batch-verify`, `final-verify`, `baseline` 5개 서브커맨드를 제공합니다.
- 다음 파일들을 흡수 후 삭제했습니다:
  - `mdx_to_storage_xhtml_verify_cli.py` (173줄) → `batch-verify` 서브커맨드로 흡수
  - `mdx_to_storage_phase1_baseline_cli.py` (80줄) → `baseline` 서브커맨드로 흡수
  - `reverse_sync/mdx_to_storage_final_verify.py` (137줄) → `final-verify` 서브커맨드로 흡수
  - `reverse_sync/mdx_to_storage_baseline.py` (118줄) → `baseline` 서브커맨드에 인라인

**삭제 줄수:** ~508줄 (4개 파일 + 관련 테스트 파일 삭제)

### 3.6 [삭제 검토] `reverse_sync/test_verify.py` — 위치 부적절한 CLI 래퍼 (67줄)

**위치:** `bin/reverse_sync/test_verify.py`

**현황:**
- `reverse_sync_cli.py`의 `run_verify()`를 호출하는 얇은 래퍼입니다.
- 패키지 디렉토리(`reverse_sync/`) 안에 위치한 CLI 스크립트로, 위치가 부적절합니다.
- `tests/run-tests.sh`에서 호출되지만, `reverse_sync_cli.py verify` 커맨드로 대체 가능합니다.

**권장:** `run-tests.sh`가 `reverse_sync_cli.py verify`를 직접 호출하도록 변경 후 삭제합니다.

**신뢰도:** 높음 | **예상 삭제:** 67줄

## 4. 도달 불가능한 코드 경로

### 4.1 [유지] 주석 처리된 디버그 코드 — `converter/core.py:192-195`

```python
# DEBUG(JK)
# if tag in self._debug_tags:
#     breakpoint()
```

**판단:** `_debug_tags`와 함께 수동 디버깅용으로 유지합니다.

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

### 6.1 수동 디버깅용 코드 (유지)

아래 항목들은 프로덕션에서 실행되지 않지만, 개발자가 수동으로 활성화하여 디버깅하는 용도로 의도적으로 유지합니다. (`# Used when debugging manually`, c7dd721)

| 항목 | 파일 | 줄수 | 판단 |
|------|------|------|------|
| `_debug_markdown` 플래그 및 분기 | `converter/core.py` | ~30줄 | 유지 |
| `_debug_tags` 빈 집합 및 분기 | `converter/core.py` | ~10줄 | 유지 |
| 주석 처리된 디버그 코드 | `converter/core.py` | ~4줄 | 유지 |

### 6.2 통합 완료 (삭제됨)

| 항목 | 파일 | 상태 |
|------|------|------|
| CLI 통합 | `mdx_to_storage_xhtml_verify_cli.py` | **삭제** → `batch-verify` 서브커맨드로 흡수 |
| CLI 통합 | `mdx_to_storage_phase1_baseline_cli.py` | **삭제** → `baseline` 서브커맨드로 흡수 |
| 래퍼 모듈 | `reverse_sync/mdx_to_storage_final_verify.py` | **삭제** → `final-verify` 서브커맨드로 흡수 |
| 래퍼 모듈 | `reverse_sync/mdx_to_storage_baseline.py` | **삭제** → `baseline` 서브커맨드에 인라인 |

### 6.3 미처리 항목

| 항목 | 파일 | 예상 삭제 줄수 | 신뢰도 |
|------|------|---------------|--------|
| 위치 부적절 CLI 래퍼 | `reverse_sync/test_verify.py` | ~67줄 | 높음 |

### 6.4 전체 합계

| 분류 | 줄수 |
|------|------|
| 수동 디버깅용 코드 (유지) | 0줄 (삭제 안 함) |
| 통합 완료 (삭제됨) | ~508줄 |
| 미처리 | ~67줄 |

## 7. 결론

confluence-mdx 코드베이스는 전반적으로 잘 관리되고 있으며, 완전히 미사용인 모듈은 없습니다.

- **즉시 삭제 가능한 dead code는 없습니다.** `converter/core.py`의 디버그 관련 코드(`_debug_markdown`, `_debug_tags`)는 수동 디버깅용으로 의도적으로 유지됩니다.
- **래퍼 모듈/CLI 통합**을 통해 ~508줄을 정리했습니다 (4개 파일 삭제, `mdx_to_storage_xhtml_cli.py`로 통합).
- 남은 미처리 항목은 `reverse_sync/test_verify.py` (~67줄)입니다.
- 코드 품질 개선의 더 큰 효과는 **중복 코드 리팩토링**(별도 문서 `analysis-duplicate-code.md` 참조)에서 얻을 수 있습니다.
