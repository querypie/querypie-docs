# Reverse Sync 대체 계획 (2026-04-25)

> 상태: Draft
> 대상: `confluence-mdx/bin/reverse_sync/`, `bin/reverse_sync_cli.py`, `tests/`, `docs/`
> 목적: 기존 reconstruction phase 문서를 현재 코드 기준으로 대체하고, 앞으로의 개선 작업을 "구현 현실"에 맞는 계획으로 다시 정의합니다.

---

## 1. 이 문서가 대체하는 기존 계획 문서

이 문서는 아래 3개 문서를 포괄적으로 대체합니다.

- `2026-03-13-reverse-sync-reconstruction-design.md`
- `2026-03-13-reverse-sync-reconstruction-design-review.md`
- `2026-03-15-reverse-sync-reconstruction-cleanup-scope.md`

기존 문서들은 당시로서는 타당한 문제의식과 설계 방향을 담고 있었지만, 현재 main의 구현 상태와 다음 이유로 어긋납니다.

1. 이미 완료된 작업을 아직 계획 단계처럼 서술하는 부분이 있습니다.
2. 삭제된 모듈(`text_transfer.py`, `list_patcher.py`, `table_patcher.py`)을 전제로 하는 cleanup 항목이 남아 있습니다.
3. `mapping.yaml`과 roundtrip sidecar v3의 실제 역할 분리가 문서 구조에 충분히 반영되지 않았습니다.
4. 현재의 핵심 위험이 "재구성 자체의 부재"보다 "patch_builder 정책 집중 + verifier 결합 + capability 경계 불명확"으로 이동했는데, 예전 문서는 이 상태를 담지 못합니다.

이 문서는 따라서 "예전 계획의 6차 개정판"이 아니라, 현재 구현을 출발점으로 다시 세운 replacement plan입니다.
이 문서를 현재 기준의 주 문서로 삼고, 3월 문서들은 historical record로만 남깁니다.

---

## 2. 현재 기준선

현재 reverse-sync의 사실상 표준 경로는 다음과 같습니다.

1. 원본/교정 MDX 로드
2. `parse_mdx_blocks()` + `diff_blocks()`
3. `record_mapping(page.xhtml)`
4. `generate_sidecar_mapping()` / `mapping.yaml`
5. `build_sidecar()` / `expected.roundtrip.json` schema v3
6. `build_patches()`
7. `patch_xhtml()`
8. patched XHTML 재기록
9. forward converter 재실행
10. `verify_roundtrip()`
11. pass 시에만 push 후보로 취급

현재 구현의 핵심 특성:

- reverse-sync는 text patcher가 아니라 sidecar 기반 fragment-preserving system입니다.
- `patch_builder.py`가 실제 정책 엔진입니다.
- `mapping.yaml`은 lookup/lost_info 계층이고, roundtrip sidecar v3는 identity/reconstruction 계층입니다.
- list, preserved anchor, table, parameter-bearing container는 여전히 별도 capability boundary를 갖습니다.
- verifier와 forward converter의 정규화 특성 변화가 reverse-sync pass/fail에 직접 영향을 줍니다.

이 기준선은 "무엇을 새로 만들 것인가"보다 먼저 "무엇을 더 이상 가정하지 말아야 하는가"를 정해줍니다.

---

## 3. 이번 계획의 목표

### 3.1 최종 목표

reverse-sync를 "모든 MDX 변경을 무조건 Confluence에 반영하는 시스템"으로 만들겠다는 목표는 현실적이지 않습니다. 대신 다음을 목표로 삼습니다.

1. 지원 범위를 capability 단위로 명확히 문서화합니다.
2. 지원 범위 안에서는 roundtrip proof까지 포함해 신뢰할 수 있게 만듭니다.
3. 지원 범위 밖에서는 skip/fail 이유가 코드와 문서에 일관되게 드러나게 만듭니다.
4. `patch_builder.py`의 전략 집중을 완화해 회귀 수정 비용을 줄입니다.
5. verifier/fixture/manifest 체계를 재정리해 "왜 pass/fail인지"를 추적 가능하게 만듭니다.

### 3.2 비목표

이번 계획의 비목표는 다음과 같습니다.

- Confluence XHTML의 모든 구조를 일반 emitter만으로 재생성하기
- skip reason을 전부 제거하기
- 테이블/복합 anchor/container를 단기간에 완전 지원하기
- reverse-sync를 forward converter와 완전히 분리된 서브시스템으로 만들기

즉, 목표는 "전면 자동화"가 아니라 "지원 범위의 명확화 + 구조적 유지보수성 향상"입니다.

---

## 4. 설계 원칙

### 4.1 fail-closed를 유지합니다

지원 범위가 애매한 변경은 계속 skip/fail-closed로 남겨야 합니다. coverage 없이 공격적으로 허용하는 방향은 반복 회귀를 다시 부릅니다.

### 4.2 sidecar를 진실원으로 취급하지 않고, 계약(contract)으로 취급합니다

- `mapping.yaml`은 구조 lookup 계약입니다.
- roundtrip sidecar v3는 fragment identity 계약입니다.
- 둘 중 하나만으로 전체 문제를 해결하려고 하면 문서와 코드가 다시 어긋납니다.

### 4.3 정책과 실행을 분리합니다

현재 `patch_builder.py`에는 다음이 함께 들어 있습니다.

- capability 판별
- fallback 선택
- patch shape 생성
- skip reason 생성
- 일부 list/table 전용 로직

앞으로는 planner와 strategy 실행을 분리해야 합니다.

### 4.4 visible segment를 planning 언어로 승격합니다

현재 `visible_segments.py`는 주로 list 경로의 정밀 판별 보조 모델로만 쓰이지만, 앞으로는 이 개념을 reverse-sync의 planning 언어로 확장하는 방향을 택합니다.

- MDX 쪽 변경은 가능하면 먼저 visible segment model로 정규화합니다.
- XHTML 쪽 원본 fragment도 visible segment model 또는 그에 대응하는 visible node view로 투영합니다.
- planner는 block diff만으로 바로 patch를 만들지 않고, 우선 `visible edit sequence`를 도출합니다.
- strategy는 이 edit sequence를 그대로 DOM에 적용하지 않고, 안전한 XHTML node edit operation으로 lowering합니다.

즉 앞으로의 중심 표현은 `plain-text diff` 자체가 아니라 `visible segment -> edit sequence -> node operation`입니다.

### 4.5 universal emitter를 목표로 하지 않습니다

visible segment 중심 설계는 paragraph / heading / list / 일반 inline text 변경에는 잘 맞지만, preserved anchor / parameter-bearing container / raw HTML table / Confluence macro 구조까지 단일 모델로 무리하게 일반화하면 오히려 안전성이 떨어집니다.

따라서 다음 원칙을 둡니다.

- text-bearing block은 visible segment 기반 planning을 우선합니다.
- 구조 보존이 중요한 block은 sidecar/template-preserving reconstruction을 fallback 또는 authority로 유지합니다.
- 위험 구조는 `replace_fragment` 또는 `skip`으로 남깁니다.

### 4.6 테스트는 "설계 검증"과 "회귀 방지"를 분리합니다

예전 문서는 둘을 한 축에 놓는 경향이 있었고, 그 결과 oracle이 흐려졌습니다. 앞으로는 테스트를 다음으로 분리합니다.

- 계약 테스트(contract tests)
- strategy 단위 회귀 테스트
- page fixture 기반 통합 테스트
- batch manifest 기반 상태 리포트

### 4.7 문서와 코드의 시간축을 분리합니다

현황 문서는 현재 코드가 하는 일을 적고, 계획 문서는 앞으로 바꿀 일을 적어야 합니다. 둘을 한 문서에 섞지 않습니다.

---

## 5. 핵심 문제 재정의

현재 reverse-sync의 가장 큰 문제는 "아직 reconstruction이 덜 구현되었다"가 아닙니다. 현재는 다음 5개가 더 중요합니다.

### P1. capability 경계가 코드에만 있고 문서/테스트 표면에 명시되지 않습니다

예:

- 어떤 table은 replace 가능하고 어떤 table은 skip됩니다.
- 어떤 preserved anchor list는 처리되고 어떤 것은 여전히 위험합니다.
- 어떤 container는 reconstruction 경로를 타지만 parameter-bearing container는 별도 취급됩니다.

하지만 이 차이가 문서/테스트/CLI 결과에서 일관된 capability taxonomy로 드러나지 않습니다.

### P2. `patch_builder.py`가 planner + strategy dispatcher + partial executor 역할을 동시에 수행합니다

이 구조에서는 새 회귀가 나올 때마다 if/elif를 추가하는 방향으로 수렴하기 쉽습니다.

### P3. verifier와 converter 정규화가 reverse-sync 결과 해석을 어렵게 만듭니다

pass/fail이 실제 patch 품질 문제인지, forward converter의 canonicalization 변화인지, verifier normalization 차이인지 즉시 분리되지 않는 경우가 있습니다.

### P4. fixture/reporting 자산은 많지만 taxonomy가 아직 정리되지 않았습니다

- `tests/testcases/`
- `tests/reverse-sync/pages.yaml`
- unit test
- e2e regression fixture

실데이터 기준으로 `pages.yaml`의 역할은 이미 비교적 명확합니다. reverse-sync 입장에서는 참조용 metadata catalog이며, 테스트 구현 과정에서만 추가 필드가 얹혀 있습니다. 문제는 `pages.yaml` 자체보다, capability / expected_status / verifier outcome을 어떤 taxonomy로 읽을지 아직 정리되지 않았다는 점입니다.

### P5. 계획 문서가 실제 main과 엇갈리며, 삭제된/완료된 축을 계속 참조합니다

이 상태에서는 새 작업을 시작할 때마다 먼저 문서를 해석해야 하므로, 문서가 가이드보다 부담이 됩니다.

---

## 6. 목표 아키텍처

이번 계획의 목표 아키텍처는 "새 시스템을 다시 처음부터 만들자"가 아니라, 현재 구조를 다음처럼 재배치하는 것입니다.

### 6.1 Planner / Strategy / Proof 3계층

1. Planner
   - 변경 블록을 capability 단위로 분류
   - 사용 가능한 identity source 결정
   - MDX/XHTML visible model 생성 여부 결정
   - visible edit sequence 도출
   - strategy 후보 결정
   - skip/fail reason 결정

2. Strategy
   - visible edit sequence를 XHTML node edit operation으로 lowering
   - direct edit
   - fragment replacement
   - container reconstruction
   - list strategy
   - table strategy
   - preserved-anchor template rewrite

3. Proof
   - patch 적용
   - forward roundtrip
   - result classification
   - push eligibility

현재는 이 셋이 `patch_builder.py`와 `reverse_sync_cli.py` 사이에 뒤섞여 있습니다. 앞으로는 책임 경계를 명시해야 합니다.

### 6.2 Visible segment planner와 XHTML node operation 계층

이번 replacement plan에서 새로 채택하는 핵심 방향은, `visible_segments.py`를 list 전용 보조 유틸에 머무르게 두지 않고 planner 계층의 공통 표현으로 승격하는 것입니다.

목표 파이프라인은 다음과 같습니다.

1. old/new MDX block -> visible segment model
2. original XHTML fragment -> visible segment model 또는 visible node view
3. 두 model 사이의 `visible edit sequence` 계산
4. `visible edit sequence`를 XHTML node edit operation으로 lowering
5. 기존 `patch_xhtml()` 계층으로 적용
6. roundtrip verifier로 proof

여기서 중요한 점은 다음과 같습니다.

- `visible edit sequence`는 곧바로 DOM mutation이 아닙니다.
- 중간 lowering 단계에서 capability boundary, sidecar identity, template preservation 필요 여부를 함께 판단해야 합니다.
- 결과 operation은 현재 patch 체계와 호환되는 `modify`, `delete`, `insert`, `replace_fragment` 계열로 귀결되어도 됩니다.

즉 이 계획은 apply 계층을 버리는 것이 아니라, patch 생성 전의 정책 언어를 visible segment 중심으로 재구성하는 계획입니다.

### 6.3 Capability registry 도입

다음과 같은 capability 단위를 문서와 코드 양쪽에 명시적으로 도입합니다.

- `paragraph_visible_segment_edit`
- `heading_visible_segment_edit`
- `inline_whitespace_adjustment`
- `clean_block_replace`
- `container_body_reconstruction`
- `preserved_anchor_template_rewrite`
- `list_visible_segment_edit`
- `table_fragment_replace`
- `unsafe_table_edit`
- `unsupported_complex_anchor_structure`

중요한 것은 naming 그 자체보다, 각 capability가 아래를 갖는 것입니다.

- 지원 여부
- strategy owner
- skip/fail reason
- 대표 fixture
- regression test location

### 6.4 Result taxonomy 표준화

현재 `pass/fail/no_changes/skipped_changes`는 존재하지만, 더 세밀한 운영 의미가 필요합니다. 특히 table, whitespace, column-width 같은 formatting 수준 차이를 semantic mismatch와 분리해야 합니다. 계획상 목표 taxonomy는 다음 4계층으로 둡니다.

1. Accept
   - `exact_match`
   - `normalized_match`
   - `formatting_only_match`
2. Review
   - `semantic_diff_needs_review`
   - `reconstruction_needs_review`
   - `preservation_uncertain`
3. Block
   - `capability_boundary_blocked`
   - `missing_identity`
   - `unsafe_edit`
   - `ambiguous_target`
4. Error
   - `patch_generation_error`
   - `roundtrip_verification_error`
   - `reconversion_error`

이 taxonomy는 CLI, result.yaml, 문서, 테스트 설명이 공통으로 써야 합니다. 구현 세부 enum은 더 쪼갤 수 있지만, 문서와 운영 보고는 위 중간 해상도를 기준으로 맞춥니다.

---

## 7. 단계별 실행 계획

### Stage 0. 문서/분류 기준선 확정

목표:

- current-state 문서와 plan 문서의 역할을 분리합니다.
- capability registry 초안을 문서에 먼저 정의합니다.
- 기존 plan 문서를 superseded 상태로 전환합니다.

산출물:

- 현재 구현 상태 문서
- 본 replacement plan
- 기존 plan 문서 superseded 표기

완료 기준:

- 새 작업이 더 이상 3월 phase 문서를 기준으로 시작되지 않습니다.

### Stage 1. capability matrix와 fixture inventory 정리

목표:

- 현재 처리 가능한 변경을 capability 기준으로 표에 정리합니다.
- `pages.yaml`를 실데이터 기준의 reference metadata catalog로 문서화하고, 테스트 전용 부가 필드와 구분해 설명합니다.

작업:

1. `failure_type`, label, severity를 capability/skip reason과 매핑합니다.
2. 각 capability에 대표 fixture를 1~3개씩 지정합니다.
3. `expected_status`와 verifier outcome이 taxonomy 어디에 매핑되는지 문서에서 재정의합니다.
4. unsupported 영역을 명시적으로 목록화합니다.

완료 기준:

- "이 케이스는 왜 아직 안 되나"를 capability 이름으로 설명할 수 있습니다.
- 회귀 이슈가 들어오면 어느 capability에 속하는지 바로 분류할 수 있습니다.

### Stage 2. `patch_builder.py` 분해 1차 — planner 추출

목표:

- `patch_builder.py`에서 정책 판단과 patch 생성 책임을 분리합니다.

작업:

1. planner 입력/출력 구조 정의
   - change
   - mapping source
   - sidecar source
   - mdx visible model
   - xhtml visible model 또는 visible node view
   - visible edit sequence
   - capability
   - chosen strategy
   - skip reason
2. `visible edit sequence`를 표준 planning 산출물로 고정
3. strategy dispatcher 인터페이스 정의
4. 기존 `build_patches()`는 planner + strategy executor orchestration으로 축소

완료 기준:

- 새 회귀 수정 시 `build_patches()` 본체에 직접 if/elif를 추가하지 않고, planner rule 또는 strategy handler 수정으로 끝낼 수 있습니다.
- planner 출력만 보면 "어떤 visible 변화가 어떤 node operation 후보로 내려갔는지"를 설명할 수 있습니다.

초기 모듈 분해 초안:

- `confluence-mdx/bin/reverse_sync/planner_types.py`
  - `VisibleEdit`
  - `VisibleEditSequence`
  - `PlanningContext`
  - `PlanningDecision`
- `confluence-mdx/bin/reverse_sync/visible_planner.py`
  - `plan_visible_edit_sequence(...) -> VisibleEditSequence`
  - `plan_change(...) -> PlanningDecision`
- `confluence-mdx/bin/reverse_sync/node_operations.py`
  - `NodeOperation`
  - `NodeOperationSequence`
- `confluence-mdx/bin/reverse_sync/operation_lowering.py`
  - `lower_visible_edits_to_node_operations(...) -> NodeOperationSequence`
  - `lower_node_operations_to_patches(...) -> list[dict[str, str]]`
- `confluence-mdx/bin/reverse_sync/strategy_dispatcher.py`
  - `choose_strategy(...) -> str`
  - `execute_strategy(...) -> list[dict[str, str]]`
- 전략 하위 모듈
  - `confluence-mdx/bin/reverse_sync/strategies/list_strategy.py`
  - `confluence-mdx/bin/reverse_sync/strategies/text_block_strategy.py`
  - `confluence-mdx/bin/reverse_sync/strategies/preserved_anchor_strategy.py`
  - `confluence-mdx/bin/reverse_sync/strategies/container_strategy.py`
  - `confluence-mdx/bin/reverse_sync/strategies/table_strategy.py`

초기 함수 시그니처 초안:

```python
@dataclass(frozen=True)
class VisibleEdit:
    kind: Literal[
        "keep",
        "insert_text",
        "delete_text",
        "replace_text",
        "split_segment",
        "merge_segment",
        "formatting_only",
    ]
    old_segment_ids: tuple[str, ...] = ()
    new_segment_ids: tuple[str, ...] = ()
    old_text: str = ""
    new_text: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


def plan_visible_edit_sequence(
    *,
    old_mdx: str,
    new_mdx: str,
    xhtml_fragment: str,
    capability: str,
) -> VisibleEditSequence:
    ...


def plan_change(change: BlockChange, context: PlanningContext) -> PlanningDecision:
    ...


def lower_visible_edits_to_node_operations(
    sequence: VisibleEditSequence,
    context: PlanningContext,
) -> NodeOperationSequence:
    ...


def lower_node_operations_to_patches(
    operations: NodeOperationSequence,
    context: PlanningContext,
) -> list[dict[str, str]]:
    ...
```

이 초안의 의도는 다음과 같습니다.

- planner 출력은 patch dict가 아니라 `VisibleEditSequence`입니다.
- lowering 계층은 visible edit와 DOM/node edit를 연결합니다.
- strategy 계층은 capability boundary와 fallback 선택을 담당합니다.
- 최종 apply는 기존 `xhtml_patcher.py`를 계속 사용합니다.

### Stage 3. list / preserved anchor / container 전략 분리

목표:

- 현재 가장 복잡한 capability를 독립 전략 모듈로 분리합니다.

우선순위:

1. list visible-segment 전략
2. preserved-anchor template rewrite 전략
3. parameter-bearing container reconstruction 전략

세부 방향:

- list는 현재 `visible_segments.py`를 그대로 출발점으로 삼되, 결과를 `visible edit sequence`로 명시화합니다.
- paragraph / heading은 새 visible model extractor를 도입해 plain-text transfer보다 planner 기반 lowering을 우선 검토합니다.
- preserved anchor / container는 visible planning 결과만으로 충분하지 않은 경우 template-preserving reconstruction으로 안전하게 내려갑니다.

완료 기준:

- 각 전략이 독립 테스트 파일과 fixture 세트를 가집니다.
- `patch_builder.py`는 분기 지점만 남고 세부 알고리즘을 직접 품지 않습니다.
- text-bearing block에 대해서는 "MDX visible model -> edit sequence -> node operation" 흐름을 설명할 수 있습니다.

### Stage 4. table 경계 명시화

목표:

- table 지원을 넓히기 전에 먼저 boundary를 명확히 하고, verifier가 formatting-level 차이를 과도하게 mismatch로 보지 않도록 정리합니다.

작업:

1. 현재 skip reason을 capability 문서와 1:1로 연결
2. markdown table / raw HTML table / preserved-anchor table을 명확히 분리
3. 어떤 table이 "지원 대상"인지 acceptance contract를 먼저 고정
4. whitespace-only / column-width-only 차이는 `formatting_only_match`로 분류하는 verifier 규칙을 정의

완료 기준:

- table 관련 버그가 들어왔을 때 "미지원"과 "회귀"를 혼동하지 않습니다.
- whitespace-only / column-width-only table diff는 더 이상 semantic mismatch로 집계되지 않습니다.
- 새로운 지원 확대는 capability 추가로 표현합니다.

### Stage 5. verifier contract 정리

목표:

- patch quality 문제와 normalization 문제를 분리하고, proof 계층의 결과 언어를 고정합니다.

작업:

1. `verify_roundtrip()` 결과를 Accept / Review / Block / Error taxonomy로 재분류
2. `--lenient`, `--no-normalize`의 의미를 문서와 테스트에서 고정
3. converter normalization 변화로 인한 false failure를 `normalized_match` 또는 `formatting_only_match`와 구분해 분리
4. proof 계층에서 result classification과 push eligibility를 연결하는 규칙 정의

완료 기준:

- fail 및 review 원인을 `semantic review` / `capability block` / `normalization-driven accept` / `system error`로 구분할 수 있습니다.

### Stage 6. push rollout contract 정리

목표:

- verify pass와 push eligibility를 같은 개념으로 취급하지 않도록 정리합니다.

작업:

1. push safety gate 문서화
2. conflict / remote drift / dry-run / human confirmation 경계 정리
3. CLI 출력과 result.yaml에 push-blocked reason 추가

완료 기준:

- "verify는 통과했지만 왜 push하지 않았는가"가 결과에 명시됩니다.

---

## 8. 테스트 계획

### 8.1 테스트 계층

1. Contract tests
   - sidecar schema
   - planner classification
   - visible edit sequence schema / invariants
   - result taxonomy

2. Strategy tests
   - list visible segment
   - paragraph/heading visible segment lowering
   - preserved anchor rewrite
   - container reconstruction
   - table classification

3. Fixture integration tests
   - `tests/testcases/`
   - `original.mdx` / `improved.mdx` / `expected.reverse-sync.patched.xhtml`

4. Batch manifest tests
   - `tests/reverse-sync/pages.yaml`
   - capability/expected_status/failure_type/result taxonomy alignment 검증

### 8.2 테스트 원칙

- 새 capability를 추가할 때는 representative fixture를 반드시 함께 추가합니다.
- skip reason을 바꿀 때는 result taxonomy 테스트도 함께 갱신합니다.
- verifier normalization 변경은 strategy 테스트가 아니라 verifier contract 테스트로 검증합니다.
- `pages.yaml`은 실데이터 기준 reference metadata catalog이며, 테스트에서는 regression reporting asset으로도 활용합니다.

### 8.3 우선 추가할 테스트

1. planner classification snapshot test
2. table skip reason classification test
3. list visible segment capability fixture set
4. paragraph/heading visible edit sequence snapshot test
5. verifier reason-code split test
6. result.yaml schema test

### 8.4 초기 테스트 파일 배치안

- `confluence-mdx/tests/test_visible_planner.py`
  - planner classification snapshot
  - paragraph/heading visible edit sequence snapshot
- `confluence-mdx/tests/test_operation_lowering.py`
  - visible edit sequence -> node operation lowering
  - node operation -> patch emission
- `confluence-mdx/tests/test_strategy_dispatcher.py`
  - capability별 strategy 선택
  - fallback / skip reason 결정
- `confluence-mdx/tests/test_list_strategy.py`
  - 기존 list visible segment fixture 재사용
- `confluence-mdx/tests/test_text_block_strategy.py`
  - paragraph / heading text-bearing block fixture
- `confluence-mdx/tests/test_preserved_anchor_strategy.py`
  - preserved anchor fallback / reconstruction 경계
- `confluence-mdx/tests/test_container_strategy.py`
  - parameter-bearing container reconstruction 경계
- `confluence-mdx/tests/test_table_strategy.py`
  - table capability boundary / skip reason / formatting-only verifier 연계

fixture 배치 초안:

- `confluence-mdx/tests/testcases/visible-planner/paragraph-*`
- `confluence-mdx/tests/testcases/visible-planner/heading-*`
- `confluence-mdx/tests/testcases/visible-planner/list-*`
- `confluence-mdx/tests/testcases/strategies/preserved-anchor-*`
- `confluence-mdx/tests/testcases/strategies/container-*`
- `confluence-mdx/tests/testcases/strategies/table-*`

이 배치는 planner, lowering, strategy, proof를 테스트 파일 수준에서도 분리하기 위한 최소 단위 제안입니다.

---

## 9. 문서 구조 계획

최종적으로 reverse-sync 문서는 다음 구조를 목표로 합니다.

- `docs/architecture.md`
  - 현재 코드가 실제로 어떻게 동작하는지 설명
- `docs/analysis-reverse-sync-refactoring.md`
  - 현재 구현 상태와 구조적 리스크 분석
- `docs/plans/2026-04-25-reverse-sync-replacement-plan.md`
  - 앞으로의 변경 계획
- (선택) capability matrix 문서
  - 지원/미지원 범위를 표로 관리

즉, 현황 / 분석 / 계획을 분리합니다.

---

## 10. 기존 계획 문서에서 유지할 것과 버릴 것

### 유지할 것

- fail-closed 원칙
- sidecar 기반 identity 보존 방향
- reconstruction 중심 접근
- 테스트 우선 사고
- regression gate를 먼저 세우는 태도

### 버릴 것

- phase 번호 중심 서술
- 이미 삭제된 모듈을 기준으로 한 cleanup 계획
- `mapping.yaml` 단독 설명으로 전체 reverse-sync를 설명하려는 방식
- 구현 완료/미완료 상태와 계획을 한 문서에 섞는 방식

---

## 11. 승인 기준

이 계획은 아래 방향 합의를 기준선으로 삼고 실행합니다.

1. capability registry naming을 유지합니다.
2. planner / strategy / proof 3계층 분리를 코드 정리의 중심축으로 삼습니다.
3. table은 지원 확대보다 boundary 명시와 verifier normalization 보정을 우선합니다.
4. `pages.yaml`는 실데이터 기준 reference metadata catalog로 보고, 이 점을 과도한 설계 쟁점으로 확대하지 않습니다.
5. verifier taxonomy는 세부적으로 분류합니다.
6. visible segment model을 planner 계층의 중심 표현으로 승격하되, apply 계층은 patch/DOM/sidecar 체계를 유지합니다.

즉, 이제 남은 것은 큰 방향의 재논의가 아니라, 위 기준선 아래에서 capability 매핑과 proof taxonomy를 실제 코드/CLI/테스트에 반영하는 일입니다.

---

## 12. 이번 리뷰에서 합의된 방향

이 PR은 Draft이며, 아래 항목은 이번 리뷰에서 방향이 합의된 상태로 간주합니다.

1. capability registry naming은 유지합니다.
2. table은 현 수준의 지원을 유지하되, verifier에서 whitespace-only / column-width-only 차이를 mismatch가 아니라 `formatting_only_match`로 판정하는 쪽을 우선합니다.
3. planner / strategy / proof 3계층 분리는 실제 코드 정리의 중심축으로 채택합니다.
4. `pages.yaml`는 reverse-sync 관점에서 reference metadata catalog로 보고, 테스트 전용 부가 필드 때문에 역할 논의를 과도하게 확대하지 않습니다.
5. verifier taxonomy는 운영 판단에 직접 쓰일 수 있도록 세부적으로 분류합니다.
6. visible segment 기반 `edit sequence -> XHTML node operation` 흐름은 text-bearing block의 목표 설계로 채택하되, sidecar/template-preserving fallback을 함께 유지합니다.

---

## 13. 결론

예전 계획의 핵심 직감은 맞았습니다. reverse-sync는 heuristic patch를 계속 덧대는 방향만으로는 안정화되지 않습니다. 다만 현재 시점에는 이미 많은 reconstruction/sidecar 기반 구현이 main에 들어와 있으므로, 이제 필요한 것은 "새 phase를 더 추가하는 문서"가 아니라 다음입니다.

- 현재 구조를 capability 기준으로 다시 설명하고
- 정책 엔진을 분해할 수 있는 계획을 세우고
- 지원 범위와 한계를 문서/테스트/CLI에서 같은 언어로 표현하는 것

이 문서는 그 전환을 위한 새로운 기준 문서입니다.
