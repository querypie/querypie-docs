# Plan: XHTML Diff 정량적 측정 모델 (Edit Distance Metrics)

## Context

`mdx_to_storage_xhtml_verify_cli.py`는 현재 pass/fail 이진 판정과 unified diff 텍스트만 제공한다.
`xhtml_beautify_diff.py`의 `beautify_xhtml()` + `xhtml_diff()`를 이미 사용하고 있지만,
**정량적 유사도 측정**은 없다.

### 문제

- 21개 testcase가 모두 fail이지만, 각 케이스의 심각도를 구분할 수 없다
- "1줄 차이" vs "50줄 차이"가 동일하게 fail로 분류된다
- 개선 작업의 진척도를 수치로 추적할 수 없다 (pass 수만으로는 불충분)
- 우선순위 판단에 정량적 근거가 부족하다

### 해결 방향

beautified XHTML의 전체 라인 수 대비 diff에서 차이나는 줄 수를 **line-level edit distance**로
간주하여, 두 XHTML 간의 차이를 0.0~1.0 similarity 값으로 정량화한다.

## 측정 모델 설계

### 핵심 공식

```
reference_lines = len(beautify_xhtml(normalized_page_xhtml).splitlines())
changed_lines   = count of (+/-) lines in unified diff  (excluding +++/---/@@ headers)
edit_ratio      = changed_lines / (2 * reference_lines)   # /2: 변경 1건 = -1줄 +1줄
similarity      = clamp(1.0 - edit_ratio, 0.0, 1.0)
```

**왜 `2 * reference_lines`로 나누는가?**
- unified diff에서 한 줄이 변경되면 `-` 1줄 + `+` 1줄 = 2줄이 발생한다
- 순수 삭제(- only)나 순수 추가(+ only)도 있으므로, 이 공식은 근사값이다
- 그러나 라인 수 기반 비교에서 실용적으로 충분한 정밀도를 제공한다

**edge case 처리:**
- `reference_lines == 0 and changed_lines == 0` → similarity = 1.0
- `reference_lines == 0 and changed_lines > 0` → similarity = 0.0
- `edit_ratio > 1.0` (추가가 삭제보다 많은 경우) → clamp to 0.0

### 데이터 모델

```python
@dataclass
class DiffMetrics:
    total_lines: int        # beautified page.xhtml 전체 라인 수 (기준)
    changed_lines: int      # unified diff에서 +/- 라인 수 (헤더 제외)
    edit_distance: int      # = changed_lines (절대 편집 거리)
    edit_ratio: float       # changed_lines / (2 * total_lines)
    similarity: float       # clamp(1.0 - edit_ratio, 0.0, 1.0)
```

### 예시

| 시나리오 | total_lines | changed_lines | edit_ratio | similarity |
|---------|-------------|---------------|------------|------------|
| 완전 일치 | 50 | 0 | 0.000 | 1.000 |
| 속성 1개 차이 | 50 | 2 | 0.020 | 0.980 |
| 테이블 구조 불일치 | 50 | 20 | 0.200 | 0.800 |
| 완전 불일치 | 50 | 100 | 1.000 | 0.000 |

## 변경 대상 파일

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `bin/reverse_sync/mdx_to_storage_xhtml_verify.py` | 수정 | `DiffMetrics` 추가, `CaseVerification`에 metrics 필드 추가, 집계 로직 |
| `bin/mdx_to_storage_xhtml_verify_cli.py` | 수정 | `--show-metrics` 플래그, 메트릭 출력, 분석 리포트에 포함 |
| `tests/test_mdx_to_storage_xhtml_verify.py` | 수정 | metrics 계산/집계 테스트 추가 |

## 구현 상세

### Step 1: `DiffMetrics` 데이터클래스 및 계산 함수

**파일**: `bin/reverse_sync/mdx_to_storage_xhtml_verify.py`

```python
@dataclass
class DiffMetrics:
    total_lines: int
    changed_lines: int
    edit_distance: int
    edit_ratio: float
    similarity: float


def compute_diff_metrics(
    page_norm: str,
    generated_norm: str,
    diff_lines: list[str],
) -> DiffMetrics:
    """beautified/normalized XHTML 간의 정량적 차이를 계산한다."""
    total = len(page_norm.splitlines())

    changed = 0
    for line in diff_lines:
        if line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith(("+", "-")):
            changed += 1

    if total == 0:
        edit_ratio = 0.0 if changed == 0 else 1.0
    else:
        edit_ratio = changed / (2 * total)

    similarity = max(0.0, min(1.0, 1.0 - edit_ratio))

    return DiffMetrics(
        total_lines=total,
        changed_lines=changed,
        edit_distance=changed,
        edit_ratio=round(edit_ratio, 4),
        similarity=round(similarity, 4),
    )
```

### Step 2: `CaseVerification`에 metrics 필드 추가

```python
@dataclass
class CaseVerification:
    case_id: str
    passed: bool
    generated_xhtml: str
    diff_report: str
    metrics: DiffMetrics | None = None   # NEW — 기존 코드 하위호환
```

### Step 3: `verify_expected_mdx_against_page_xhtml()`에서 metrics 반환

현재 시그니처:
```python
def verify_expected_mdx_against_page_xhtml(
    expected_mdx, page_xhtml, ...
) -> tuple[bool, str, str]:
```

변경:
```python
def verify_expected_mdx_against_page_xhtml(
    expected_mdx, page_xhtml, ...
) -> tuple[bool, str, str, DiffMetrics]:
```

내부에서 `compute_diff_metrics(page_norm, generated_norm, diff_lines)` 호출하여 반환.
`verify_testcase_dir()`에서 이를 받아 `CaseVerification.metrics`에 저장.

### Step 4: `VerificationSummary`에 집계 메트릭 추가

```python
@dataclass
class VerificationSummary:
    total: int
    passed: int
    failed: int
    failed_case_ids: list[str]
    by_priority: dict[str, int]
    by_reason: dict[str, int]
    analyses: list[FailureAnalysis]
    # NEW metrics
    avg_similarity: float       # 전체 케이스 평균 similarity
    median_similarity: float    # 중앙값
    min_similarity: float       # 최소 similarity
    max_similarity: float       # 최대 similarity
    weighted_pass_rate: float   # sum(similarity) / total — 가중 합격률
```

`summarize_results()`에서 모든 케이스의 `metrics.similarity`를 모아 계산:
```python
similarities = [r.metrics.similarity for r in results if r.metrics]
summary.avg_similarity = statistics.mean(similarities) if similarities else 0.0
summary.median_similarity = statistics.median(similarities) if similarities else 0.0
summary.min_similarity = min(similarities) if similarities else 0.0
summary.max_similarity = max(similarities) if similarities else 0.0
summary.weighted_pass_rate = sum(similarities) / len(similarities) if similarities else 0.0
```

### Step 5: CLI 출력 확장

**새 플래그**: `--show-metrics`

```python
parser.add_argument(
    "--show-metrics",
    action="store_true",
    help="Show quantitative similarity metrics per case and in aggregate",
)
```

**출력 예시**:
```
[mdx->xhtml-verify] total=21 passed=5 failed=16
[metrics] avg_similarity=0.847 median=0.912 min=0.423 max=1.000
[metrics] weighted_pass_rate=0.891

Case similarity ranking (worst first):
  544375741  similarity=0.423  changed=58/50 lines
  544375859  similarity=0.567  changed=34/40 lines
  ...
  544375123  similarity=1.000  changed=0/30 lines
```

### Step 6: 분석 리포트에 메트릭 포함

`_format_analysis_report()` 확장:

```markdown
# MDX -> Storage XHTML Batch Verify Analysis

- total: 21
- passed: 5
- failed: 16

## Similarity Metrics

- avg_similarity: 0.847
- median_similarity: 0.912
- min_similarity: 0.423
- max_similarity: 1.000
- weighted_pass_rate: 0.891

## Priority Summary
...

## Failed Cases (by similarity, ascending)

- 544375741: P1 (similarity=0.423, changed=58 lines) — internal_link_unresolved
- 544375859: P2 (similarity=0.567, changed=34 lines) — emoticon_representation_mismatch
...
```

## 테스트 계획

### `tests/test_mdx_to_storage_xhtml_verify.py` 추가 (~6개)

| 테스트 | 설명 |
|--------|------|
| `test_compute_diff_metrics_identical` | 동일 XHTML → changed=0, similarity=1.0 |
| `test_compute_diff_metrics_partial_diff` | 일부 차이 → 0 < similarity < 1 |
| `test_compute_diff_metrics_completely_different` | 완전 불일치 → similarity ≈ 0.0 |
| `test_compute_diff_metrics_empty_reference` | 빈 page.xhtml → edge case 처리 |
| `test_case_verification_includes_metrics` | `verify_testcase_dir()` 결과에 metrics 포함 확인 |
| `test_summarize_results_aggregate_metrics` | 집계 메트릭 (avg, median, min, max) 정확성 |

### 기존 테스트 영향

`verify_expected_mdx_against_page_xhtml()` 반환 타입이 3-tuple → 4-tuple로 변경되므로,
기존 호출부 수정 필요:
```python
# 기존
passed, generated, diff_report = verify_expected_mdx_against_page_xhtml(...)
# 변경
passed, generated, diff_report, metrics = verify_expected_mdx_against_page_xhtml(...)
```

## 활용 시나리오

1. **진척도 추적**: `weighted_pass_rate`를 매 iteration마다 기록하여 개선 추이 확인
2. **우선순위 결정**: similarity가 낮은 케이스 = 차이가 큰 케이스 → 구조적 문제 우선 해결
3. **회귀 검출**: similarity가 떨어지면 새 변경이 기존 변환을 깨뜨린 것
4. **완성도 보고**: "21개 케이스 중 가중 합격률 89.1%" 같은 정량적 보고 가능

## 검증 방법

1. **단위 테스트**: `pytest tests/test_mdx_to_storage_xhtml_verify.py -v`
2. **메트릭 확인**:
   ```bash
   python bin/mdx_to_storage_xhtml_verify_cli.py \
     --pages-yaml var/pages.yaml \
     --show-metrics \
     --show-analysis
   ```
3. **리포트 생성**:
   ```bash
   python bin/mdx_to_storage_xhtml_verify_cli.py \
     --pages-yaml var/pages.yaml \
     --show-metrics \
     --write-analysis-report reports/metrics-baseline.md
   ```
4. 각 케이스의 similarity 값이 직관적 기대와 일치하는지 수동 검증
