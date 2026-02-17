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

### 3.3 [삭제 검토] `mdx_to_storage_xhtml_cli.py` — 중복 CLI 래퍼 (194줄)

**위치:** `bin/mdx_to_storage_xhtml_cli.py`

**현황:**
- `convert`, `verify`, `batch-verify` 서브커맨드를 제공합니다.
- `batch-verify`와 `verify` 기능은 `mdx_to_storage_xhtml_verify_cli.py`(173줄)에서도 동일하게 제공합니다.
- 유일한 고유 기능은 `convert` 서브커맨드이나, 이는 `emit_document(parse_mdx(...))`의 단순 래퍼입니다.
- README.md나 문서에서 참조되지 않으며, 테스트 파일(`test_mdx_to_storage_xhtml_cli.py`)만 import합니다.

**권장:** `mdx_to_storage_xhtml_verify_cli.py`가 정규 진입점입니다. `convert` 기능이 필요하면 verify CLI에 서브커맨드로 추가하고, 이 파일을 삭제하는 것을 검토합니다.

**신뢰도:** 높음 | **예상 삭제:** 194줄

### 3.4 [삭제 검토] `reverse_sync/mdx_to_storage_final_verify.py` — 래퍼 모듈 (137줄)

**위치:** `bin/reverse_sync/mdx_to_storage_final_verify.py`

**현황:**
- `mdx_to_storage_xhtml_verify.py`의 핵심 검증 로직을 단순 래핑합니다.
- `run_final_verify()`, `render_final_verify_report()` 등은 `VerificationSummary`의 얇은 래퍼입니다.
- 테스트 파일(`test_mdx_to_storage_final_verify.py`)만 참조합니다.
- Phase 3 Task 3.5에서 생성된 태스크 전용 모듈입니다.

**권장:** 태스크 완료 후 검증 리포트 기능을 `mdx_to_storage_xhtml_verify.py`에 통합하고 삭제를 검토합니다.

**신뢰도:** 중간-높음 | **예상 삭제:** 137줄

### 3.5 [삭제 검토] `reverse_sync/mdx_to_storage_baseline.py` — 래퍼 모듈 (118줄)

**위치:** `bin/reverse_sync/mdx_to_storage_baseline.py`

**현황:**
- `mdx_to_storage_xhtml_verify_cli.py`를 subprocess로 호출하여 결과를 파싱하는 래퍼입니다.
- `mdx_to_storage_phase1_baseline_cli.py`에서만 import됩니다.
- Phase 1 baseline 측정 전용 유틸리티로, Phase 1 완료 후 활용도가 낮습니다.
- CLI 출력을 regex로 파싱하는 취약한 구조입니다.

**권장:** Phase 1 baseline이 더 이상 업데이트되지 않으면 `mdx_to_storage_phase1_baseline_cli.py`와 함께 삭제합니다.

**신뢰도:** 중간 | **예상 삭제:** 118줄 (+ CLI 80줄)

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

### 6.2 통합 후 삭제 가능 (중복 래퍼)

| 항목 | 파일 | 예상 삭제 줄수 | 신뢰도 |
|------|------|---------------|--------|
| 중복 CLI 래퍼 | `mdx_to_storage_xhtml_cli.py` | ~194줄 | 높음 |
| 위치 부적절 CLI 래퍼 | `reverse_sync/test_verify.py` | ~67줄 | 높음 |
| 래퍼 모듈 (final verify) | `reverse_sync/mdx_to_storage_final_verify.py` | ~137줄 | 중간-높음 |
| 래퍼 모듈 (baseline) | `reverse_sync/mdx_to_storage_baseline.py` | ~118줄 | 중간 |
| baseline CLI | `mdx_to_storage_phase1_baseline_cli.py` | ~80줄 | 중간 |
| **소계** | | **~596줄** | |

### 6.3 전체 합계

| 분류 | 예상 삭제 줄수 |
|------|---------------|
| 수동 디버깅용 코드 (유지) | 0줄 (삭제 안 함) |
| 통합 후 삭제 가능 | ~596줄 |
| **총계** | **~596줄** |

## 7. 결론

confluence-mdx 코드베이스는 전반적으로 잘 관리되고 있으며, 완전히 미사용인 모듈은 없습니다.

- **즉시 삭제 가능한 dead code는 없습니다.** `converter/core.py`의 디버그 관련 코드(`_debug_markdown`, `_debug_tags`)는 수동 디버깅용으로 의도적으로 유지됩니다.
- **래퍼 모듈/CLI 통합**을 통해 ~596줄을 정리할 수 있습니다. 이들은 현재 테스트에서 참조되므로, import 경로 업데이트와 함께 진행해야 합니다.
- 코드 품질 개선의 더 큰 효과는 **중복 코드 리팩토링**(별도 문서 `analysis-duplicate-code.md` 참조)에서 얻을 수 있습니다.
