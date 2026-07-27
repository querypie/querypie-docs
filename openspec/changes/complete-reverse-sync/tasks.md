## 1. Contract

- [x] 현재 `main`의 reverse-sync CLI, patch engine, sidecar, verifier, Confluence client를 조사합니다.
- [x] local verify와 remote page update 사이의 correctness gap을 식별합니다.
- [x] `contract-reverse-sync` change-local spec을 작성합니다.
- [x] snapshot-bound transformation, base parity, manifest, compare-and-set, postcondition을 design decision으로 기록합니다.
- [ ] reviewer와 다음 contract boundary를 확정합니다.
  - push equivalence v1의 formatting-only 허용 범위
  - active draft 감지 방식과 rollout 조건
  - title/attachment capability의 별도 change 필요 여부
  - artifact 보존 기간과 redaction 정책

## 2. Implementation

### 2.1 P0 — 현재 unsafe push를 red test로 고정

- [x] `confluence-mdx/tests/test_reverse_sync_push_transaction.py`를 추가합니다.
- [x] stale local `page.xhtml` + latest remote version 조합이 PUT으로 이어지는 현재 문제를 재현합니다.
- [x] version과 body를 별도 GET으로 읽을 때 서로 다른 snapshot이 될 수 있는 문제를 재현합니다.
- [x] preflight 이후 concurrent update가 발생하면 자동 retry하지 않는 계약을 테스트합니다.
- [x] verify 후 candidate body가 바뀌면 push를 차단하는 테스트를 추가합니다.
- [x] PUT 성공 후 remote body가 target과 다르면 `postcondition_failed`가 되는 테스트를 추가합니다.
- [x] active draft, title 변경, missing attachment, lenient-only pass가 push blocked인지 테스트합니다.

완료 gate:

- 새 contract test가 현재 구현에서 의도한 이유로 실패합니다.
- 기존 unit/page/byte-equal fixture 결과는 그대로 유지됩니다.

### 2.2 P0 — immutable model과 artifact layout

- [x] `confluence-mdx/bin/reverse_sync/models.py`를 추가합니다.
  - `PageSnapshot`
  - `SyncManifest`
  - `VerificationGate`
  - `SyncStatus`
  - `ReasonCode`
  - `PushReceipt`
- [x] `confluence-mdx/bin/reverse_sync/manifest.py`를 추가합니다.
  - canonical serialization
  - SHA-256 계산
  - referenced artifact integrity 검사
  - schema version 및 verifier policy 검사
- [x] artifact를 `var/<page_id>/reverse-sync/<run_id>/`에 실행별로 저장합니다.
- [x] 기존 run-backed `reverse-sync.*` 경로는 최신 immutable run을 가리키는
  read-only compatibility output으로 제한합니다.
  - online prepare의 patched XHTML, patch plan, local proof, manifest는
    run directory artifact를 가리키는 상대 symlink로만 노출합니다.
  - publisher는 compatibility output을 입력으로 사용하지 않으며 폐기된
    `reverse-sync.manifest.path` pointer를 생성하지 않습니다.
  - offline diagnostic의 diff/result/mapping/verify output은 push 비대상
    compatibility artifact로 유지합니다.
- [x] email, token, Authorization header redaction test를 추가합니다.

완료 gate:

- 같은 입력과 tool version에서 manifest/candidate hash가 deterministic합니다.
- candidate 또는 manifest를 수정하면 publisher 이전에 `artifact_tampered`가 발생합니다.

### 2.3 P0 — consistent Confluence snapshot adapter

- [x] `confluence-mdx/bin/reverse_sync/confluence_client.py`에 v2 page snapshot 조회를 추가합니다.
- [x] `GET /wiki/api/v2/pages/{id}`에서 Storage body와 version을 한 snapshot으로 획득합니다.
- [x] `page_id`, `status=current`, body representation, title, version 필수 필드를 검증합니다.
- [x] active draft 조회/감지 adapter를 분리하고 실제 API 응답 fixture를 추가합니다.
- [x] HTTP 400/409 등 provider response를 `version_conflict`, `permission_denied`, `network_error`로 변환합니다.
- [x] 기존 `get_page_version()` + `get_page_body()` 조합을 push 경로에서 제거합니다.

완료 gate:

- publisher가 서로 다른 GET의 version/body를 조합할 수 없습니다.
- v2 response contract와 error mapping unit test가 통과합니다.
- QueryPie canary page에서 current/draft 응답 shape를 read-only로 확인합니다.

### 2.4 P0 — base parity와 dependency gate

- [x] `confluence-mdx/bin/reverse_sync/base_parity.py`를 추가합니다.
- [x] remote snapshot의 forward conversion 결과와 original MDX를 비교합니다.
- [x] page ID, `confluenceUrl`, repository MDX path를 함께 검증합니다.
- [x] `stale_original_mdx`, `forward_converter_drift`, `page_identity_mismatch`를 구분합니다.
- [x] original/improved title과 첫 H1 invariant를 검증하고 title change를 block합니다.
- [x] attachment catalog에서 improved MDX의 attachment reference를 검증합니다.
- [x] internal link resolver error와 ambiguous target을 dependency failure로 변환합니다.
- [x] snapshot metadata가 없는 offline verify는 `push_eligible: false`로 표시합니다.

완료 gate:

- base parity를 통과하지 않은 입력으로 patch/push가 진행되지 않습니다.
- title, attachment, link dependency가 조용히 무시되지 않습니다.

### 2.5 P0 — strict proof와 push eligibility

- [x] `confluence-mdx/bin/reverse_sync/proof.py`를 추가하여 필수 gate를 orchestration합니다.
- [x] `roundtrip_verifier.py` normalization을 source formatting, rendered-visible, unsupported/lossy로 분류합니다.
- [x] push equivalence v1 typed canonical model을 구현합니다.
- [x] `skipped_changes > 0`이면 `intent_complete`를 실패시킵니다.
- [x] `--lenient`와 `--no-normalize` 결과를 diagnostic field로 이동합니다.
- [x] unchanged fragment, separator, document envelope byte-equal을 proof에 포함합니다.
- [x] well-formed Storage XHTML, determinism, idempotency 검사를 추가합니다.
- [x] 기존 `pass`를 `verified_local`과 분리합니다.

완료 gate:

- 모든 required gate를 통과한 manifest만 `push_eligible: true`입니다.
- visible whitespace 또는 title 차이가 normalization으로 숨지 않습니다.
- 기존 fixture 중 policy 변경으로 block되는 case는 reason code와 reviewer 결정을 함께 기록합니다.

### 2.6 P0 — transaction-safe publisher

- [x] `confluence-mdx/bin/reverse_sync/publisher.py`를 추가합니다.
- [x] verified manifest와 candidate artifact hash를 다시 검증합니다.
- [x] remote preflight snapshot의 page ID/status/version/title/body hash를 base와 비교합니다.
- [x] active draft가 있으면 PUT 전에 block합니다.
- [x] base version + 1과 base title, manifest candidate body로 update합니다.
- [x] conflict 시 latest version으로 자동 retry하지 않습니다.
- [x] update 후 persisted snapshot을 다시 조회합니다.
- [x] persisted version과 target MDX semantic postcondition을 검증합니다.
- [x] base, candidate, response, post-snapshot을 recovery evidence로 저장합니다.
- [x] postcondition failure 시 batch 후속 push를 기본 중단합니다.
- [x] 현재 `_do_push()`가 `reverse-sync.patched.xhtml`을 직접 읽는 경로를 제거합니다.

완료 gate:

- stale remote에서 PUT 호출이 0회입니다.
- preflight/PUT race는 `version_conflict`로 종료됩니다.
- API 성공만으로 `remote_verified`가 되지 않습니다.

### 2.7 P1 — CLI와 batch state 전환

- [x] `reverse_sync_cli.py`를 prepare/verify/push lifecycle orchestration으로 축소합니다.
  - [x] candidate 준비, roundtrip 검증, local proof/manifest 생성을
    `reverse_sync/verification_service.py`로 분리하고 CLI는 runtime dependency를
    주입하는 호환 adapter만 유지합니다.
  - [x] explicit manifest integrity/identity 검증, publisher 호출, semantic
    postcondition, backup 생성을 `reverse_sync/publish_service.py`로 분리합니다.
  - [x] source/page identity와 online snapshot 준비를
    `reverse_sync/prepare_service.py`로, batch 대상 선택과 publish 중단 정책을
    `reverse_sync/batch_service.py`로 분리합니다. CLI에는 argument parsing,
    stderr event adapter, confirmation, display, service orchestration만 유지합니다.
- [x] online verify(`push --dry-run`) 출력에 run ID, base version/hash, local gates,
  push eligibility, reason code를 표시합니다.
- [x] `push`가 explicit run/manifest를 받도록 합니다.
  - `push --manifest <manifest.json>`은 online verify를 다시 실행하지 않고 해당
    immutable run만 publisher에 전달합니다.
  - `_do_push()`의 `reverse-sync.manifest.path` pointer fallback을 제거합니다.
  - MDX/branch/diagnostic 옵션과의 상호 배제 및 confirmation identity를
    contract test로 고정합니다.
  - publisher 진입 전에 PatchPlan intent coverage를 재계산하고 local proof의
    base/candidate/plan hash와 gate를 manifest에 교차 검증합니다.
- [x] interactive confirmation에 page ID, base version, target version, change count, candidate hash를 표시합니다.
- [x] batch는 모든 local proof 후 page별 transaction을 실행합니다.
- [x] batch partial success, conflict, postcondition failure exit code와 JSON schema를 정의합니다.
  - branch `--json`은 `reverse-sync-batch-report` schema v1 envelope를
    반환합니다.
  - `outcome`, `exit_code`, stable summary, page별 `batch_status`와 reason
    code를 함께 기록합니다.
  - partial/failed는 exit 1, success와 사용자 cancellation은 exit 0입니다.
- [x] resume는 `remote_verified`/blocked 상태를 재해석하지 않고 명시적 manifest 목록으로 수행합니다.
  - postcondition failure 뒤 미시도 page는
    `batch_halted_after_postcondition_failure`로 표시합니다.
  - batch report의 `resume_manifests`에는 이 미시도 run만 포함하고 각 run은
    `push --manifest`로 명시적으로 재개합니다.
- [x] `--yes`가 safety gate를 우회하지 못하도록 테스트합니다.

완료 gate:

- human confirmation과 `--yes`는 사용자 확인만 제어하고 base/proof/preflight gate를 건너뛰지 않습니다.
- batch가 all-or-nothing처럼 출력되지 않습니다.

### 2.8 P1 — planner / renderer 책임 분리

- [x] `patch_builder.py`의 capability 판별을 `capabilities.py`와 planner로 추출합니다.
  - `classify_capability()`은 raw patch payload shape를 재해석하지 않고 typed
    `StrategyDecision`, MDX block type, canonical action을 입력으로 capability를
    결정합니다.
  - planner는 operation에 대응하는 `ChangeIntent` ordinal에서 capability를
    계산하고 여러 intent가 서로 다른 capability로 분류되면 fail-closed합니다.
  - legacy renderer skip reason과 blocked capability의 대응표도
    `capabilities.py`의 registry boundary로 이동합니다.
  - MDX-owned link의 text block operation을 preservation capability로 잘못
    분류하지 않도록 integration test를 고정합니다.
- [x] `build_patches()`의 strategy handler를 `reverse_sync/strategies/**`로
  추출하고 typed strategy dispatch만 남깁니다.
  - `StrategyRenderContext`와 `StrategyPrimitives`가 기존 patch primitive를
    handler에 주입하며 handler는 `patch_builder.py`를 역참조하지 않습니다.
  - text block, list, preserved anchor, container, table은 독립 handler와
    registry를 가지며 `blocked` 또는 미등록 strategy는 dispatch 경계에서
    fail-closed합니다.
- [x] planning output을 typed `PatchPlan`/operation으로 바꾸고 raw patch dict를 boundary 안에 가둡니다.
  - `legacy-patch-builder-v2` adapter가 `ChangeIntent`, `TargetIdentity`,
    capability, required proof, reason code를 canonical schema v2 plan에 기록합니다.
  - push path는 exact sidecar provenance와 intent가 대응하지 않는 operation을
    `missing_identity`로 non-executable 처리합니다.
  - capability별 renderer strategy 추출은 아래 task에 계속 남습니다.
- [x] block identity를 provenance-first 순서로 바꿉니다.
  - strict planner는 caller의 legacy mapping 대신 MDX content hash와 line range가
    유일하게 일치하는 sidecar provenance index를 renderer strategy 전에
    구축합니다.
  - exact 후보가 없으면 `missing_identity`, 중복되면 `ambiguous_target`으로
    operation 생성 전에 block합니다.
- [x] normalized text prefix fallback을 push-eligible path에서 제거합니다.
- [x] visible segment model을 paragraph, heading, list에 확장합니다.
  - paragraph와 heading은 실제 inline emitter 결과에서 visible whitespace와
    link/attachment/macro preservation unit metadata를 추출합니다.
  - list는 기존 item path, marker, ordered start, anchor fingerprint를 같은 공통
    dispatcher로 제공합니다.
  - arbitrary macro/container는 기존 capability 경계에 남기고 일반화하지 않습니다.
- [x] strategy를 text block, list, preserved anchor, container, table로 분리합니다.
  - `capabilities.py`의 typed `RendererStrategy`와 `StrategyDecision`이 exact
    mapping 이후 renderer category를 한 곳에서 결정합니다.
  - raw HTML table 처리를 generic text block에서 table strategy로 이동하고,
    preserved anchor와 raw table의 link 보존 분기는 공통 template rewrite
    helper를 사용합니다.
  - 계약이 없는 `ac:`/`ri:` preservation unit은 text fallback으로 흘리지 않고
    `unknown_macro_mutation` capability로 fail-closed 처리합니다.
  - strategy handler는 `reverse_sync/strategies/**`의 typed registry로
    추출되어 `build_patches()` 본체에 category별 분기를 추가하지 않습니다.
- [x] unsupported table/macro 구조를 explicit block reason으로 전환합니다.
  - operation 생성 전 legacy skip도 원래 intent에 연결합니다.
  - table/macro 내부 분기 reason은 `unsupported_capability`와
    `raw_html_table_edit`/`unknown_macro_mutation` capability ID로 정규화합니다.
  - mapping/sidecar 부재는 `missing_identity`로 정규화하고 같은 intent의 중복
    issue를 제거합니다.
- [x] 기존 `xhtml_patcher.py`는 validated operation 적용에 집중하도록 축소합니다.
  - typed preserving renderer는 boolean mode가 없는
    `apply_validated_patches()`를 호출하여 unresolved target, source text
    mismatch, unknown action을 `PatchApplicationError`로 전환합니다.
  - offline diagnostic과 raw patch regression fixture는 별도
    `legacy_xhtml_patcher.patch_xhtml()` 호환 API를 사용하며 publish candidate
    생성 경로에서는 이 API를 참조하지 않습니다.

완료 gate:

- 새 capability 추가가 `build_patches()` 본체의 heuristic branch 추가를 요구하지 않습니다.
- 모든 operation은 capability, target identity, required proof, reason code를 가집니다.

### 2.9 P2 — capability 확대

- [x] page title update를 body update와 분리된 capability/change로 설계합니다.
  - version precondition이 없는 title 전용 endpoint는 사용하지 않고, 후속
    capability가 title/body/version을 하나의 page postcondition으로 증명합니다.
- [x] attachment upload/version update/delete transaction을 별도 capability/change로 설계합니다.
  - create/update/delete intent와 catalog precondition을 분리하고, page PUT과
    원자적이지 않은 side effect 및 manual recovery evidence를 명시합니다.
  - 기존 attachment version update는 old binary를 page CAS 성공 시점까지
    보존하는 staging/body-switch 전략을 별도 change에서 증명하기 전까지
    `new_attachment_lifecycle`로 block합니다.
- [x] preserved anchor target 변경을 지원할지 결정합니다.
  - generic template rewrite에서는 지원하지 않으며 target fingerprint가 바뀌면
    `unsupported_capability`로 block합니다.
- [x] raw HTML table cell text-only mutation의 typed proof를 설계합니다.
  - table/cell/text-node identity, 구조 및 preservation fingerprint, byte
    preservation과 semantic proof를 진입 조건으로 정의합니다.
- [x] active draft reconciliation 또는 draft-aware publish를 별도 capability/change로 설계합니다.
  - 첫 단계는 read-only reconciliation evidence이며, 자동 merge/overwrite는
    공식 API와 canary에서 versioned draft write를 증명하기 전까지 제외합니다.
- [x] remote drift three-way merge는 provenance와 conflict semantics가 준비된 뒤 별도 change로 검토합니다.
  - capability별 commute/conflict semantics가 준비될 때까지 `remote_drift`에서
    PUT 0회와 manual MDX merge workflow를 유지합니다.

## 3. Verification

### 3.1 Focused contract test

- [x] 다음 명령으로 현재 구현된 snapshot, manifest, publisher contract test를 실행합니다.

```bash
cd confluence-mdx/tests
../venv/bin/python3 -m pytest -q test_reverse_sync_push_transaction.py
```

strict proof와 typed equivalence는 다음 test module과 golden shadow fixture로 검증합니다.

```bash
cd confluence-mdx/tests
../venv/bin/python3 -m pytest -q \
  test_reverse_sync_input_gates.py \
  test_reverse_sync_equivalence.py \
  test_reverse_sync_online_proof_fixture.py \
  test_reverse_sync_push_transaction.py
```

### 3.2 Existing reverse-sync unit regression

- [x] 기존 reverse-sync unit suite를 실행합니다.

```bash
cd confluence-mdx/tests
../venv/bin/python3 -m pytest -q \
  test_reverse_sync*.py \
  test_lost_info_patcher.py
```

기준선: 2026-07-24 `origin/main`에서 676 passed입니다.

lifecycle guide 변경 결과: 794 passed입니다.

### 3.3 Page fixture regression

- [x] 정밀 golden fixture와 실제 회귀 fixture를 실행합니다.

```bash
cd confluence-mdx/tests
make test-reverse-sync
```

기준선:

- `tests/testcases/**`: 16 passed
- `tests/reverse-sync/**`: 43 passed

### 3.4 Byte preservation

- [x] fast path와 forced splice byte-equal을 실행합니다.

```bash
cd confluence-mdx/tests
make test-byte-verify
```

기준선:

- fast path: 21/21 passed
- forced splice: 21/21 passed

### 3.5 Broader converter regression

- [x] verifier/equivalence 또는 emitter를 변경한 PR은 다음을 추가로 실행합니다.

```bash
cd confluence-mdx/tests
make test-convert
make test-reverse-sync
make test-byte-verify
```

strict proof 구현 branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- 전체 Python test: 1086 passed, 2 skipped
- 16개 golden page shadow online verify: 4개 `verified_local`, 나머지는
  visible whitespace, unresolved link, raw HTML table mutation 등에서 fail-closed

typed plan branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- 전체 Python test: 1096 passed, 2 skipped

explicit manifest branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- 전체 Python test: 1106 passed, 2 skipped

batch report branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- 전체 Python test: 1113 passed, 2 skipped

capability reason branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- 전체 Python test: 1114 passed, 2 skipped

lifecycle guide branch 검증 결과:

- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- 전체 Python test: 1117 passed, 2 skipped

provenance-first branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- reverse-sync Python test: 797 passed
- 전체 Python test: 1120 passed, 2 skipped

visible segment branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- reverse-sync Python test: 801 passed
- 전체 Python test: 1124 passed, 2 skipped

strict renderer branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- reverse-sync Python test: 805 passed
- 전체 Python test: 1128 passed, 2 skipped

typed renderer strategy branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- `test_reverse_sync*.py`: 779 passed
- 전체 Python test: 1132 passed, 2 skipped
- `openspec validate complete-reverse-sync --strict`: passed

typed capability planning branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- `test_reverse_sync*.py`: 789 passed
- 전체 Python test: 1142 passed, 2 skipped
- `openspec validate complete-reverse-sync --strict`: passed

strategy handler extraction branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- `test_reverse_sync*.py`: 791 passed
- 전체 Python test: 1144 passed, 2 skipped
- `openspec validate complete-reverse-sync --strict`: passed

validated patcher boundary branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- `test_reverse_sync*.py`: 792 passed
- 전체 Python test: 1145 passed, 2 skipped
- `openspec validate complete-reverse-sync --strict`: passed

run-backed compatibility artifact branch 검증 결과:

- `make test-convert`: 21 passed
- `make test-reverse-sync`: golden 16 passed, regression 43 passed
- `make test-byte-verify`: fast/splice 각각 21/21 passed
- `test_reverse_sync*.py`: 793 passed
- 전체 Python test: 1146 passed, 2 skipped
- `openspec validate complete-reverse-sync --strict`: passed

- [x] 영향도에 따라 전체 Python test와 render test를 실행합니다.

이번 변경은 Python renderer 범위이므로 전체 Python test
(`1146 passed, 2 skipped`)를 실행했고 frontend render test는 영향 범위에서
제외했습니다.

```bash
cd confluence-mdx/tests
../venv/bin/python3 -m pytest -q
make test-render
```

### 3.6 Remote canary

- [ ] 별도로 승인된 Confluence canary page에서 current/draft snapshot response를 read-only로 수집합니다.
- [ ] canary page의 version/body hash를 고정한 dry-run manifest를 생성합니다.
- [ ] 사람 확인 후 단일 trivial text edit를 push합니다.
- [ ] post-snapshot version, body hash, forward round-trip, Confluence UI 표시를 확인합니다.
- [ ] 같은 manifest 재실행이 PUT 없이 `already_applied` 또는 stale manifest로 종료되는지 확인합니다.
- [ ] canary 검증 전에는 production batch push를 활성화하지 않습니다.

## 4. Spec / 구현 drift 확인

- [x] `PageSnapshot` 구현이 version/body를 하나의 논리적 response에서 가져오는지 source scan합니다.
- [x] publisher가 latest remote version을 새 base로 채택하는 fallback이 없는지 검색합니다.
- [x] `skipped_changes`, `--lenient`, title strip이 push eligibility를 부여하지 않는지 확인합니다.
- [x] push가 filename이 아니라 manifest candidate hash를 소비하는지 확인합니다.
- [x] 모든 PUT 호출 경로가 preflight와 postcondition을 거치는지 확인합니다.
- [x] batch output이 page별 상태와 partial success를 노출하는지 확인합니다.
- [x] credential이 manifest/log/fixture에 포함되지 않았는지 검색합니다.

```bash
rg -n "update_page|requests\\.put|method.?=.?(PUT|put)" confluence-mdx/bin
rg -n "get_page_version|get_page_body|latest.*version|version.*\\+ *1" confluence-mdx/bin/reverse_sync*
rg -n "skipped_changes|lenient|strip_first_heading|push_eligible" confluence-mdx/bin/reverse_sync*
rg -n "api_token|Authorization|confluence\\.conf" confluence-mdx/var confluence-mdx/tests \
  --glob 'reverse-sync/**' --glob '!*.py'
```

## 5. OpenSpec Cleanup

- [ ] P0/P1 구현과 canary가 완료되면 change-local `contract-reverse-sync`를 accepted spec으로 승격합니다.
- [ ] `openspec/specs/README.md` inventory에 `contract-reverse-sync`를 추가합니다.
- [ ] `docs/architecture.md`의 current-state 설명을 최종 module/state 이름과 동기화합니다.
- [x] `.agents/skills/reverse-sync/SKILL.md`의 CLI와 artifact 경로를 새 lifecycle에 맞게 갱신합니다.
  - offline diagnostic과 online prepare/publish를 구분합니다.
  - explicit manifest, immutable run artifact, batch partial/resume 계약과
    현재 `pages.qm.yaml`/CLI option을 반영합니다.
- [ ] 중복된 historical plan은 짧은 bridge link만 남기거나 archive합니다.
- [ ] 완료된 change를 `openspec/archive/<date>-complete-reverse-sync/`로 이동합니다.
