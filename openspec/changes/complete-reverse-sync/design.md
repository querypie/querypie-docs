## Context

### 현재 구현 기준선

현재 reverse-sync의 표준 경로는 `confluence-mdx/bin/reverse_sync_cli.py::run_verify()`입니다.

1. original/improved MDX를 파싱하고 block diff를 계산합니다.
2. 로컬 `var/<page_id>/page.xhtml`에서 mapping과 roundtrip sidecar를 생성합니다.
3. `patch_builder.py`가 변경별 patch strategy를 선택합니다.
4. `xhtml_patcher.py`가 patch를 적용하여 `reverse-sync.patched.xhtml`을 만듭니다.
5. patched XHTML을 forward converter로 다시 MDX로 변환합니다.
6. `roundtrip_verifier.py`가 improved MDX와 비교합니다.
7. `pass`이면 `_do_push()`가 Confluence REST API로 page body를 갱신합니다.

2026-07-24에 최신 `origin/main`에서 확인한 검증 기준선은 다음과 같습니다.

| 검증 | 결과 | 증명하는 범위 |
| --- | ---: | --- |
| reverse-sync Python unit test | 676 passed | parser, mapping, patch, reconstruction, verifier, CLI의 로컬 동작 |
| 정밀 reverse-sync golden fixture | 16 passed | expected patched XHTML과 중간 artifact |
| 실제 회귀 page fixture | 43 passed | 과거 verify 실패 page의 현재 round-trip |
| byte-equal fast path | 21/21 passed | 미변경 document 재조립 |
| byte-equal forced splice | 21/21 passed | 미변경 fragment와 separator 보존 |

이 기준선은 기존 fragment-preserving 접근을 버릴 이유가 없음을 보여줍니다. 반면 emitter 단독 전체 재생성은 `confluence-mdx/docs/architecture.md`에 기록된 normalize-diff 기준으로 1/21만 통과합니다. MDX가 Confluence Storage XHTML의 모든 macro parameter, local ID, attachment metadata, layout, preservation unit을 표현하지 않기 때문입니다.

### 현재 구현의 correctness gap

| ID | 현재 작동 | 위험 |
| --- | --- | --- |
| C1 | original MDX는 기본적으로 `main:<path>`, XHTML은 로컬 `var/<page_id>/page.xhtml`을 사용합니다. | 두 입력이 같은 Confluence version에서 생성되었다는 보장이 없습니다. |
| C2 | push 직전에 원격 최신 version을 읽고 그 값에 `+1`을 적용합니다. | stale 로컬 XHTML로 만든 body도 최신 version에 덮어쓸 수 있습니다. |
| C3 | version과 body를 별도 GET으로 조회합니다. | 두 응답 사이에 page가 바뀌면 backup과 version이 서로 다른 snapshot일 수 있습니다. |
| C4 | verifier는 title을 제거하고 여러 공백·빈 list item·문장 경계·table padding을 정규화합니다. | 사람이 볼 수 있는 변경 또는 실제 미반영을 `pass`로 분류할 수 있습니다. |
| C5 | block identity가 line range, content hash, normalized text fallback에 분산되어 있습니다. | 중복 문단, block reorder, 구조 변경에서 잘못된 fragment를 고를 수 있습니다. |
| C6 | push는 `var/<page_id>/reverse-sync.patched.xhtml`을 직접 읽습니다. | verify 후 artifact가 바뀌어도 검증 결과와 push payload의 결합을 확인하지 않습니다. |
| C7 | PUT 성공 후 원격 body를 다시 검증하지 않습니다. | Confluence canonicalization, draft reconciliation, 잘못된 payload를 발견하지 못합니다. |
| C8 | Confluence Cloud는 current page update를 draft와 reconciliation할 수 있습니다. | active draft의 편집 의도와 충돌하거나 draft를 덮을 수 있습니다. |
| C9 | title 변경과 새 attachment 참조가 body round-trip에서 별도 mutation으로 검증되지 않습니다. | title 변경이 조용히 무시되거나 존재하지 않는 attachment를 참조할 수 있습니다. |

가장 치명적인 문제는 C2입니다. 현재 `_do_push()`는 원격 latest version을 읽은 뒤, 그 version에서 가져온 body가 아니라 과거 로컬 snapshot에서 만든 body를 PUT합니다. 이는 optimistic locking처럼 보이지만 실제로는 “검증한 base와 update base가 동일하다”는 compare-and-set 조건을 만족하지 않습니다.

### 외부 API 제약

[Confluence Cloud REST API v2 Page](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/)는 Storage representation과 version을 포함한 page 조회 및 version을 포함한 page update를 제공합니다. 또한 current version update가 draft에 reconciliation될 수 있고, 두 content가 크게 다르면 제공한 current body가 draft를 덮을 수 있음을 명시합니다.

[Confluence Cloud REST API v2 Attachment](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-attachment/)는 page attachment 목록과 cursor pagination을 제공합니다. reverse-sync는 모든 page를 조회한 current attachment catalog를 새 attachment reference의 dependency snapshot으로 사용합니다.

따라서 version number만 확인해서는 충분하지 않습니다.

- 검증에 사용한 body와 원격 current body가 같은지 확인해야 합니다.
- current와 active draft의 충돌 가능성을 별도 gate로 다뤄야 합니다.
- PUT 성공을 최종 성공으로 보지 말고 저장된 body를 다시 검증해야 합니다.

## Goals / Non-Goals

### Goals

1. MDX 변경 의도만 현재 Confluence page의 검증된 snapshot에 적용합니다.
2. MDX로 표현되지 않는 기존 Storage XHTML 정보를 보존합니다.
3. source snapshot, patch artifact, push payload, persisted result를 hash로 연결합니다.
4. stale base, ambiguous mapping, unsupported capability, active draft를 fail-closed로 차단합니다.
5. push 전 local proof와 push 후 remote proof를 구분하고 모두 추적합니다.
6. 각 실패가 input drift, capability boundary, patch error, verifier mismatch, remote conflict 중 무엇인지 reason code로 드러나게 합니다.
7. 기존 676개 unit test와 59개 page fixture, 21개 byte-equal fixture를 migration safety net으로 유지합니다.

### Non-Goals

- 임의의 Confluence Storage XHTML을 MDX만으로 완전 재생성하지 않습니다.
- 첫 구현에서 서로 다른 원격 편집과 MDX 변경을 자동 three-way merge하지 않습니다.
- 첫 구현에서 새 attachment upload, attachment 삭제, page title 변경을 지원하지 않습니다.
- batch push에 all-or-nothing 분산 transaction을 제공하지 않습니다.
- active draft를 자동 merge하거나 강제로 덮지 않습니다.
- 구현 PR에서 모든 기존 heuristic을 한 번에 제거하지 않습니다.

## First Principles

### 원칙 1: MDX는 완전한 Confluence source가 아닙니다

MDX는 public documentation의 source of truth이지만, Confluence Storage XHTML의 byte-level source of truth는 아닙니다. forward conversion에서 의도적으로 사라지는 정보가 있으므로 다음 식은 성립하지 않습니다.

```text
emit(parse(forward(storage_xhtml))) == storage_xhtml
```

따라서 reverse-sync는 full regeneration이 아니라 검증된 base XHTML에 대한 intent-preserving transformation이어야 합니다.

### 원칙 2: 성공은 “생성”이 아니라 “불변조건 증명”입니다

XHTML을 생성했다는 사실은 성공 조건이 아닙니다. 최소한 다음을 함께 증명해야 합니다.

- base snapshot이 original MDX와 대응합니다.
- 모든 MDX intent가 계획되었고 skip이 없습니다.
- unchanged source fragment가 보존됩니다.
- candidate XHTML을 forward conversion한 결과가 target MDX와 동등합니다.
- push 시점의 remote snapshot이 base snapshot과 같습니다.
- 저장된 remote 결과가 target과 동등합니다.

### 원칙 3: version과 body는 하나의 snapshot입니다

`version`, `title`, `storage_xhtml`을 독립적으로 조회하고 조합하지 않습니다. 하나의 API response 또는 같은 version을 명시한 조회 결과를 `PageSnapshot`으로 고정해야 합니다.

### 원칙 4: 모호한 자동 merge보다 명시적 중단이 안전합니다

base 이후 Confluence에서 변경이 발생하면 사용자는 먼저 fetch → forward conversion → MDX merge를 수행해야 합니다. reverse-sync가 원격 변경과 MDX 변경을 임의로 합치지 않습니다.

### 원칙 5: diagnostic equivalence와 push equivalence를 분리합니다

`--lenient` 또는 광범위한 regex normalization은 분석에는 유용하지만 publish proof로 사용할 수 없습니다. push equivalence는 versioned canonical model과 명시적으로 승인된 formatting-only 차이만 허용해야 합니다.

## Decisions

### Decision: snapshot-bound three-way transformation을 채택합니다

입력을 세 개의 명시적 값으로 정의합니다.

- `B` — Confluence에서 획득한 base `PageSnapshot`
- `O` — `B`를 forward conversion하여 얻었거나 base parity를 통과한 original MDX
- `I` — 사용자가 변경한 improved MDX

출력은 `C = apply(plan(diff(O, I), B), B)`인 candidate Storage XHTML입니다.

```text
                 one remote read
                       │
                       ▼
              B: PageSnapshot
        version + title + body + hash
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  forward_convert(B)             preserve(B)
          │                         │
          ▼                         │
   base parity(O)                   │
          │                         │
O ───────┴──── diff ───── I         │
                  │                  │
                  ▼                  │
            intent planner           │
                  │                  │
                  ▼                  ▼
            patch renderer ────────> C
                  │
                  ▼
        local proof + SyncManifest
                  │
                  ▼
       remote preflight: R == B
                  │
                  ▼
          PUT version B+1
                  │
                  ▼
       remote postcondition proof
```

이 모델에서 로컬 `page.xhtml`은 snapshot metadata 없이 push source가 될 수 없습니다. offline verify에는 사용할 수 있지만 결과는 `push_eligible: false`입니다.

### Decision: `PageSnapshot`을 원격 일관성의 최소 단위로 둡니다

`PageSnapshot`은 최소한 다음 필드를 가집니다.

```yaml
page_id: "544112828"
status: current
title: User Agent
version: 42
storage_sha256: "..."
storage_xhtml: "<p>...</p>"
fetched_at: "2026-07-24T00:00:00Z"
api: confluence-v2
active_draft: false
```

규칙:

- body와 version을 가능한 한 단일 v2 GET으로 조회합니다.
- adapter는 response에서 `page_id`, `status`, `version`, body representation을 검증합니다.
- body hash는 UTF-8 bytes의 SHA-256으로 계산합니다.
- snapshot은 실행별 artifact directory에 immutable하게 저장합니다.
- `page.v1.yaml`, `page.v2.yaml`, `page.xhtml`을 조합하여 원격 snapshot처럼 취급하지 않습니다.

### Decision: base parity를 patch 전에 검증합니다

`forward_convert(B.storage_xhtml)`과 `O`의 content가 push equivalence 기준으로 일치해야 합니다.

불일치 시 다음 중 하나로 분류합니다.

- `stale_original_mdx` — base snapshot이 main MDX보다 새롭습니다.
- `stale_page_snapshot` — original MDX가 base snapshot보다 새롭거나 다른 page에서 왔습니다.
- `forward_converter_drift` — converter 변경으로 동일 snapshot의 canonical MDX가 바뀌었습니다.
- `page_identity_mismatch` — page ID, path, `confluenceUrl`이 일치하지 않습니다.

base parity 실패 상태에서 patch를 계속 만들 수는 있지만 결과는 diagnostic이며 push할 수 없습니다. 기본 CLI는 즉시 block합니다.

구현은 `page.v1.yaml`의 page ID와 Storage body를 classification-only provenance로
사용합니다. 이 provenance body가 현재 remote body와 같으면 converter drift,
다르면 stale original로 분류합니다. provenance는 실패 사유만 세분화하며
push eligibility를 부여하지 않습니다.

source identity는 다음 세 값을 하나로 결합합니다.

- current `PageSnapshot.page_id`
- original/improved frontmatter의 `confluenceUrl` page ID
- original/improved descriptor의 동일한 `src/content/ko/**.mdx` path와
  `pages.qm.yaml`의 유일한 page ID/path row

frontmatter title과 첫 H1도 각 문서 안에서 같아야 하며 original/improved 사이에서
변경되지 않아야 합니다.

### Decision: block identity는 provenance-first로 해결합니다

우선순위는 다음과 같습니다.

1. base snapshot에서 forward conversion 시 생성한 sidecar block identity
2. exact fragment path + source fragment hash
3. MDX block hash + source line range + block family
4. 명시적으로 단일 후보임이 증명된 structural match

normalized text prefix는 push-eligible path에서 identity source로 사용하지 않습니다. 중복 block 또는 다중 후보가 있으면 `ambiguous_target`으로 block합니다.

현재 migration adapter는 offline diagnostic fixture 호환성을 위해 list의 normalized
text prefix fallback을 유지합니다. online verify는
`allow_text_identity_fallback=false`를 모든 최초·determinism·idempotency planning
호출에 강제하고, provenance mapping을 찾지 못하면 `no_mapping`으로 기록하여
`intent_complete` gate에서 block합니다.

`legacy-patch-builder-v2` adapter는 `build_patches()`가 선택한 target을 그대로
신뢰하지 않습니다. online plan에서 MDX content hash와 line range가 모두 일치하는
유일한 sidecar provenance를 `ChangeIntent`에 기록하고, renderer operation의 root
fragment와 대응하지 않으면 operation을 `missing_identity`로 non-executable
처리합니다. 따라서 migration 중에는 legacy builder가 잘못된 candidate를
제안하더라도 strict proof의 `intent_complete`를 얻을 수 없습니다.

추가/삭제/reorder는 stable neighbor identity를 기준으로 계획합니다.

- insert는 `before_block_id`와 `after_block_id` 중 하나 이상을 가져야 합니다.
- delete는 exact base fragment identity를 가져야 합니다.
- reorder는 source와 target order가 명시적으로 증명되지 않으면 첫 구현에서 block합니다.

### Decision: unchanged fragment는 byte-preserving, changed fragment는 capability-driven으로 처리합니다

document envelope, separator, unchanged top-level fragment는 base snapshot의 bytes를 그대로 사용합니다.

changed fragment는 capability registry에 따라 다음 전략 중 하나를 택합니다.

| 전략 | 조건 | 처리 |
| --- | --- | --- |
| `template_rewrite` | 원본 wrapper/macro를 보존하며 visible segment만 안전하게 바꿀 수 있음 | 원본 fragment template 위에서 typed segment를 변경 |
| `owned_replace` | emitter가 block 구조를 완전히 소유하고 preservation unit이 없음 | canonical fragment를 새로 emit |
| `container_reconstruct` | sidecar reconstruction metadata가 충분함 | outer wrapper를 보존하고 body를 재구성 |
| `insert_owned_block` | 새 block type과 link/attachment dependency가 지원됨 | canonical fragment 삽입 |
| `delete_exact_fragment` | 삭제 대상 identity가 exact하고 보호 metadata 정책을 충족함 | fragment 삭제 |
| `blocked` | identity 또는 preservation proof가 부족함 | XHTML을 만들지 않고 reason code 반환 |

기존 `visible_segments.py`의 개념은 paragraph, heading, list 등 text-bearing block의 planning model로 확장합니다. 다만 arbitrary Confluence macro를 universal visible model로 일반화하지 않습니다.

### Decision: capability registry를 code와 test의 공통 언어로 둡니다

초기 registry는 다음과 같이 정의합니다.

| Capability | 초기 상태 | 비고 |
| --- | --- | --- |
| `paragraph_visible_edit` | supported | link/inline preservation unit은 template proof 필요 |
| `heading_visible_edit` | supported | page title에 대응하는 H1은 제외 |
| `code_block_replace` | supported | language와 CDATA 안전성 검증 필요 |
| `clean_list_reconstruct` | supported | visible/structural model 일치 필요 |
| `preserved_anchor_template_rewrite` | conditional | anchor target 변경은 별도 capability |
| `container_body_reconstruct` | conditional | parameter-bearing outer wrapper 보존 |
| `simple_markdown_table_replace` | conditional | cell 구조와 preserved anchor 없음 |
| `raw_html_table_edit` | blocked | 명시적으로 승인된 cell text-only 전략 전까지 차단 |
| `unknown_macro_mutation` | blocked | unchanged macro는 byte-preserving |
| `page_title_change` | blocked | 별도 page mutation contract 필요 |
| `existing_attachment_reference` | conditional | current catalog에 유일한 filename이 있어야 함 |
| `new_attachment_lifecycle` | blocked | attachment upload/update/delete contract 필요 |
| `active_draft_reconciliation` | blocked | 자동 merge하지 않음 |

registry entry는 다음을 가져야 합니다.

- capability ID와 support level
- planner/renderer owner
- required evidence
- block reason
- representative unit test와 page fixture

현재 `reverse_sync/capabilities.py`는 이 registry를 코드로 고정하고,
`reverse_sync/operations.py`는 immutable `ChangeIntent`, `TargetIdentity`,
`PatchOperation`, `PatchPlan`을 제공합니다. `PatchOperation`은 capability ID,
base fragment hash를 포함한 target identity, required proof, executable 여부와
block reason을 항상 기록합니다. raw patch dict는 canonical
`renderer_input_json` 안에 격리하고 `PatchPlan.to_patch_dicts()`에서 validated
XHTML renderer boundary로만 복원합니다.

`reverse_sync/planner.py`는 첫 migration 단계로 기존 `build_patches()`를
`legacy-patch-builder-v2` adapter 뒤에서 호출합니다. push path의
`raw_html_table_edit`와 `unknown_macro_mutation`은
`unsupported_capability`로 non-executable 처리하며, source formatting을 나타내는
empty block insert가 `<p></p>` mutation으로 바뀌지 않도록 plan에서 제거합니다.
capability별 renderer strategy 자체를 `patch_builder.py`에서 추출하는 작업은
계속 남아 있습니다.

`render_patch_plan_preserving()`은 executable operation을 raw renderer input으로
복원하기 직전에 target root fragment hash, sidecar MDX hash, line range를 base
sidecar와 다시 비교합니다. CLI와 proof는 raw patch dict를 직접 소비하지 않으며,
typed target identity가 바뀌었거나 다른 base에 plan을 적용하려 하면
`PatchApplicationError`로 중단합니다.

### Decision: local proof를 여러 독립 gate로 분해합니다

`verified` 상태는 다음 gate를 모두 통과해야 합니다.

1. `source_identity`
   - page ID, path, `confluenceUrl`이 일치합니다.
2. `base_parity`
   - `forward(B)`와 `O`가 push equivalence 기준으로 동등합니다.
3. `intent_complete`
   - `diff(O, I)`의 모든 change가 정확히 하나의 plan operation에 대응합니다.
   - `skipped_changes`가 0입니다.
4. `artifact_integrity`
   - plan과 candidate body hash가 manifest와 일치합니다.
5. `storage_well_formed`
   - namespace-aware parser로 Storage XHTML fragment가 parse됩니다.
6. `preservation`
   - unchanged fragments, envelope, separator가 byte-equal입니다.
7. `semantic_roundtrip`
   - `forward(C)`와 `I`가 push equivalence 기준으로 동등합니다.
8. `determinism`
   - 같은 B/O/I/tool version으로 같은 plan/candidate hash가 생성됩니다.
9. `idempotency`
   - candidate를 새 base로 보았을 때 같은 intent가 추가 mutation을 만들지 않습니다.
10. `dependency`
   - referenced page와 attachment가 존재하고 resolver error가 없습니다.

`--lenient` 결과, manual review 결과, formatting-only diagnostic은 이 gate를 대신할 수 없습니다.

### Decision: push equivalence는 versioned typed canonical model로 정의합니다

현재 `roundtrip_verifier.py`의 regex normalization을 세 종류로 분류합니다.

1. source formatting only
   - 예: Markdown table cell padding
   - typed model이 content와 structure를 보존함을 증명하면 push equivalence에서 허용할 수 있습니다.
2. rendered-visible
   - 예: list marker 뒤 공백, inline boundary, 빈 list item
   - push equivalence에서 제거하지 않습니다.
3. unsupported/lossy converter behavior
   - 예: title 제거, 임의 문장 merge
   - normalization으로 숨기지 않고 capability 또는 converter defect로 block합니다.

canonical model은 block type, nesting, inline token, visible whitespace policy, link target, attachment filename, macro preservation marker를 포함합니다. policy version을 manifest에 기록하여 verifier 변경 후 과거 artifact를 잘못 재사용하지 않도록 합니다.

기존 `--no-normalize`는 raw diagnosis, `--lenient`는 triage 용도로 유지할 수 있지만 둘 다 push eligibility와 분리합니다.

`reverse-sync-equivalence-v1`의 초기 허용 범위는 Markdown table의 바깥 cell
padding, separator dash 길이, body block 사이의 빈 source line으로 제한합니다.
table alignment와 cell content, 연속 공백, list marker 뒤 공백, inline boundary,
link target, attachment filename, H1은 canonical model에 남겨 비교합니다.
해석하지 못하는 MDX JSX와 raw HTML은 marker와 source를 exact token으로 보존하여
equivalence를 임의로 확대하지 않습니다.

### Decision: `SyncManifest`를 verify와 push 사이의 계약으로 둡니다

manifest는 최소한 다음을 기록합니다.

```yaml
schema_version: 2
run_id: "..."
tool:
  git_sha: "..."
  verifier_policy: "reverse-sync-equivalence-v1"
page:
  page_id: "544112828"
base:
  version: 42
  title: User Agent
  storage_sha256: "..."
original_mdx:
  descriptor: "main:src/content/ko/..."
  sha256: "..."
improved_mdx:
  descriptor: "branch:src/content/ko/..."
  sha256: "..."
plan:
  sha256: "..."
  operation_count: 3
candidate:
  storage_sha256: "..."
verification:
  status: verified_local
  gates:
    base_parity: pass
    intent_complete: pass
    preservation: pass
    semantic_roundtrip: pass
push:
  eligible: true
  blocked_reasons: []
```

push는 file name이 아니라 manifest가 가리키는 candidate hash를 읽습니다. 다음 중 하나라도 다르면 `artifact_tampered`로 차단합니다.

- manifest hash
- base snapshot hash
- original/improved MDX hash
- plan hash
- candidate body hash
- verifier policy/tool version

artifact는 `var/<page_id>/reverse-sync/<run_id>/`에 실행별로 저장합니다. “최근 파일”을 덮어쓰는 방식은 호환 bridge로만 유지합니다.
publisher는 local proof manifest를 수정하지 않고, manifest hash를 참조하는 별도 `PushReceipt`와 post-snapshot을 기록합니다.

### Decision: push는 preflight compare-and-set과 postcondition으로 구성합니다

publisher의 순서는 다음과 같습니다.

1. verified manifest와 candidate hash를 검증합니다.
2. 원격 current `PageSnapshot R`을 단일 조회로 가져옵니다.
3. `R.page_id`, `R.status`, `R.version`, `R.title`, `R.storage_sha256`를 base `B`와 비교합니다.
4. active draft가 확인되면 `active_draft`로 차단합니다.
5. local proof가 요구한 attachment filename과 internal page ID/title을 원격에서 다시 확인합니다.
6. `R`이 base와 다르지만 이미 improved MDX와 동등하면 PUT을 생략하고 `already_applied`로 기록합니다.
7. base와 다른 나머지 경우는 `remote_drift`로 차단하고 PUT을 호출하지 않습니다.
8. `version = B.version + 1`, `title = B.title`, `body = C`로 update합니다.
9. API conflict는 HTTP 409만 가정하지 않고 adapter가 version conflict response를 표준 reason으로 변환합니다.
10. 성공 응답 후 원격 `PageSnapshot P`를 다시 가져옵니다.
11. `P.version == B.version + 1`이고 `forward(P.body) == I`인지 검증합니다.
12. 통과하면 `remote_verified`, 실패하면 `postcondition_failed`로 기록합니다.

preflight와 PUT 사이의 race는 API version compare-and-set이 방어합니다. preflight에서 latest version을 읽어 새 base로 채택하지 않습니다.

active draft 감지 방식은 Confluence v2 adapter contract test와 canary에서 확정합니다. API가 안정적으로 draft 존재 여부를 제공하지 못하면 push를 허용하는 조건과 운영 절차를 별도 승인하기 전까지 자동 push rollout을 중단합니다.

### Decision: title과 dependency를 조용히 무시하지 않습니다

첫 구현에서 다음은 block reason입니다.

- original/improved frontmatter title 또는 첫 H1이 변경됨
- 각 문서의 frontmatter title과 첫 H1이 일치하지 않음
- improved MDX가 current attachment catalog에 없는 filename을 새로 참조함
- link resolver가 target을 resolve하지 못하거나 여러 page가 일치함
- verify 이후 push preflight에서 attachment가 사라지거나 linked page ID/title이 바뀜

이미 page에 존재하는 attachment의 새 reference는 catalog identity를 local proof에
기록하고 push 직전에 filename 존재를 다시 확인한 경우에만 허용합니다. Markdown
internal link는 catalog path로 유일하게 resolve하여 Confluence `ac:link`/`ri:page`
macro로 렌더링하고, target page ID/status/title을 push 직전에 재검증합니다.

향후 title update와 attachment upload/update/delete는 별도 capability와 별도 API
transaction으로 추가합니다. body update에 암묵적으로 섞지 않습니다.

### Decision: batch push는 page별 독립 transaction입니다

batch는 다음 순서로 동작합니다.

1. 모든 page의 plan과 local proof를 먼저 생성합니다.
2. verified manifest 목록과 blocked 목록을 출력합니다.
3. 확인 후 verified page만 page별 preflight → update → postcondition을 수행합니다.
4. 한 page가 conflict 또는 error여도 이미 push된 page를 자동 rollback하지 않습니다.
5. 최종 결과는 page별 상태와 전체 partial success를 모두 반환합니다.

`--all-or-nothing`처럼 보이는 표현을 사용하지 않습니다. 진정한 원자성이 필요하면 별도의 staging/publishing architecture가 필요합니다.

### Decision: 상태와 reason code를 분리합니다

상태는 workflow lifecycle을 표현합니다.

```text
planned
  ├─ blocked
  └─ verified_local
        ├─ stale_remote
        ├─ push_failed
        └─ pushed
              ├─ remote_verified
              └─ postcondition_failed
```

대표 reason code:

- input: `page_identity_mismatch`, `stale_original_mdx`, `base_parity_mismatch`
- planning: `missing_identity`, `ambiguous_target`, `unsupported_capability`
- proof: `skipped_change`, `preservation_mismatch`, `semantic_mismatch`, `artifact_tampered`
- dependency: `missing_attachment`, `internal_link_unresolved`, `ambiguous_target`, `title_change_unsupported`
- publish: `active_draft`, `remote_drift`, `version_conflict`, `permission_denied`
- postcondition: `persisted_body_mismatch`, `persisted_version_mismatch`
- system: `network_error`, `parse_error`, `converter_error`

상태와 reason code를 섞지 않으면 “local proof는 통과했지만 remote가 stale”인 경우를 `fail` 한 단어로 뭉개지 않을 수 있습니다.

### Decision: 자동 rollback은 첫 구현 범위에서 제외하고 recovery evidence를 강화합니다

Confluence update는 외부 side effect이며 postcondition 실패 후 완전한 원자적 rollback을 보장할 수 없습니다. 자동 restore가 또 다른 version을 만들고 concurrent edit와 충돌할 수 있기 때문입니다.

대신 다음을 보장합니다.

- base snapshot과 pushed candidate를 실행별로 보존합니다.
- response version, remote post-snapshot, error를 manifest에 기록합니다.
- postcondition 실패 시 추가 push를 중단합니다.
- current remote가 방금 쓴 candidate와 동일한 경우에만 수행할 수 있는 conditional restore 절차를 출력합니다.
- 자동 compensating rollback은 별도 OpenSpec change와 canary 검증 후 도입합니다.

### Decision: 구현 책임을 planner / renderer / proof / publisher로 분리합니다

목표 module boundary는 다음과 같습니다.

| 책임 | 모듈 후보 |
| --- | --- |
| immutable model/state/reason | `reverse_sync/models.py` |
| Confluence snapshot adapter | `reverse_sync/confluence_client.py`, `reverse_sync/snapshot.py` |
| base parity | `reverse_sync/base_parity.py` |
| attachment/link dependency gate | `reverse_sync/dependencies.py` |
| capability/identity/edit planning | `reverse_sync/planner.py`, `reverse_sync/capabilities.py` |
| visible edit/node operation | `reverse_sync/visible_model.py`, `reverse_sync/operations.py` |
| capability별 render | `reverse_sync/strategies/**` |
| patch apply | 기존 `xhtml_patcher.py` |
| local proof/equivalence | `reverse_sync/proof.py`, `roundtrip_verifier.py` |
| manifest read/write/integrity | `reverse_sync/manifest.py` |
| preflight/update/postcondition | `reverse_sync/publisher.py` |
| CLI orchestration/display | `reverse_sync_cli.py` |

분리는 한 번에 수행하지 않습니다. 먼저 snapshot/manifest/publisher safety seam을
추가한 뒤 기존 `build_patches()`를 typed `PatchPlan` adapter로 감싸고,
capability별 planner와 strategy를 점진적으로 추출합니다. CLI와 local proof는
schema v2 plan을 소비하며 raw patch dict는 validated renderer boundary 밖으로
노출하지 않습니다.

## Push Eligibility Matrix

| Local result | Remote preflight | Push 가능 | 설명 |
| --- | --- | --- | --- |
| `verified_local` | base와 version/body/title 동일, draft 없음 | 가능 | 정상 경로 |
| `no_changes` | remote가 target과 semantic equivalent | update 생략 | `already_applied` |
| `verified_local` | version 또는 body hash 다름 | 불가 | `remote_drift` |
| normalized/lenient match | 무관 | 불가 | diagnostic only |
| skipped/unsupported 존재 | 무관 | 불가 | `intent_complete` 실패 |
| title 변경 | 무관 | 불가 | 첫 구현 범위 밖 |
| 기존 attachment 새 참조 | catalog와 preflight에서 filename 존재 | 가능 | upload는 수행하지 않음 |
| 존재하지 않는 attachment 참조 | 무관 | 불가 | `missing_attachment` |
| active draft | 무관 | 불가 | draft reconciliation 자동화 없음 |
| artifact hash 불일치 | 무관 | 불가 | 검증 payload와 push payload 불일치 |

## Alternatives Considered

### Alternative: improved MDX 전체를 Storage XHTML로 새로 emit

기각합니다.

- MDX는 macro parameter, local ID, attachment version, layout, extension metadata를 모두 담지 않습니다.
- emitter 단독 normalize-diff 기준선은 1/21입니다.
- 지원하지 않는 XHTML이 있는 page에서 기존 정보를 광범위하게 손실할 수 있습니다.

full emitter는 `owned_replace` 가능한 clean fragment와 insert에만 사용합니다.

### Alternative: 현재 patch pipeline을 유지하고 409 conflict만 처리

기각합니다.

- 현재 코드는 push 직전에 latest version을 읽으므로 stale local body도 latest version에 맞춰 보낼 수 있습니다.
- version/body를 별도 GET으로 읽어 snapshot 일관성도 없습니다.
- Confluence v2 update가 문서화한 draft reconciliation 위험을 다루지 못합니다.

### Alternative: 원격 drift를 자동 three-way merge

첫 구현에서는 기각합니다.

- MDX와 Storage XHTML은 정보량이 다르므로 일반적인 text merge가 아닙니다.
- 같은 block, macro, attachment를 동시에 수정한 경우 conflict 판정이 어렵습니다.
- 잘못된 자동 merge보다 fetch/convert/MDX merge 후 재실행이 안전합니다.

향후 provenance identity와 capability별 merge semantics가 충분해지면 별도 change로 검토할 수 있습니다.

### Alternative: ADF를 canonical write format으로 전환

이번 change에서는 기각합니다.

- 현재 forward converter와 fixture, sidecar, public workflow는 Storage XHTML에 기반합니다.
- ADF 전환은 converter, lost_info, macro, attachment, API adapter 전체의 별도 migration입니다.
- snapshot/manifest/compare-and-set 계약은 write representation과 독립적으로 먼저 필요합니다.

### Alternative: verifier normalization을 더 늘려 pass 비율을 높임

기각합니다.

- pass 비율은 correctness가 아닙니다.
- visible whitespace나 구조 미반영을 숨길 수 있습니다.
- formatting-only equivalence는 typed canonical model에서 명시적으로 정의해야 합니다.

## Migration Plan

### Phase 0: contract와 regression red test

- stale local body가 최신 remote version으로 overwrite되는 현재 동작을 재현합니다.
- split GET snapshot inconsistency, artifact tampering, active draft, postcondition failure를 contract test로 추가합니다.
- push eligibility와 reason code schema를 고정합니다.

### Phase 1: snapshot/manifest safety foundation

- Confluence v2 single-snapshot read adapter를 추가합니다.
- `PageSnapshot`, `SyncManifest`, artifact hash 검증을 구현합니다.
- 기존 verify 결과를 manifest로 감싸되 push는 아직 비활성화합니다.

### Phase 2: base parity와 strict proof

- page identity, base parity, dependency gate를 추가합니다.
- existing attachment와 internal page dependency evidence를 manifest에 결합하고
  publisher preflight에서 다시 확인합니다.
- verifier normalization을 typed equivalence로 분류합니다.
- skipped change와 diagnostic match가 push eligibility를 얻지 못하도록 합니다.

### Phase 3: transaction-safe publisher

- manifest-bound payload read, remote preflight, compare-and-set update, postcondition을 구현합니다.
- active draft를 감지하고 차단합니다.
- batch partial success와 recovery artifact를 구현합니다.
- 기존 `_do_push()` 직접 artifact read 경로를 제거합니다.

### Phase 4: planner/strategy 분해

- 기존 `patch_builder.py`를 capability planner와 renderer strategy로 점진 분해합니다.
- text prefix fallback을 push-eligible path에서 제거합니다.
- visible segment model을 paragraph/heading/list planning에 확장합니다.
- unsupported table/macro 구조를 explicit block으로 전환합니다.

### Phase 5: rollout

1. fixture와 offline verify만 수행합니다.
2. 실제 branch를 대상으로 remote snapshot read + dry-run을 shadow mode로 수행합니다.
3. 전용 canary page에서 단일 update와 postcondition을 검증합니다.
4. 사람 확인이 있는 단일 page push를 활성화합니다.
5. 충분한 telemetry 후 batch push를 활성화합니다.

각 단계는 이전 단계의 artifact와 reason code를 수집한 뒤 진행합니다.

## Risks / Trade-offs

### 더 많은 작업이 block될 수 있습니다

base parity, active draft, attachment gate가 추가되면 기존에 우연히 통과하던 작업이 중단됩니다. 이는 기능 후퇴가 아니라 unsafe success를 명시적 block으로 바꾸는 것입니다.

### remote read가 늘어납니다

page마다 prepare snapshot, push preflight, postcondition read가 필요합니다. correctness를 위해 필요한 비용이며 batch에서는 bounded concurrency와 retry/backoff를 사용합니다.

### typed equivalence 구현 비용이 큽니다

regex normalization보다 설계와 테스트 비용이 큽니다. 대신 무엇을 의미 없는 formatting 차이로 간주하는지 명시할 수 있고, 새로운 converter 변화가 silent acceptance를 만들지 않습니다.

### active draft API 동작이 환경에 따라 다를 수 있습니다

Atlassian API 문서와 실제 QueryPie space의 동작을 canary로 확인해야 합니다. 안정적으로 감지할 수 없으면 자동 push rollout 범위를 축소합니다.

### postcondition 실패 후 완전 원자성은 없습니다

외부 API가 transaction을 제공하지 않으므로 conditional recovery만 가능합니다. 이 한계를 숨기지 않고 상태와 artifact로 드러냅니다.

### 기존 patch_builder 분해가 장기화될 수 있습니다

P0 push safety를 planner refactor와 분리하여 먼저 적용합니다. 기존 patch engine은 local proof를 통과하는 동안 adapter 뒤에서 사용할 수 있습니다.

## Open Questions

1. QueryPie Confluence space에서 v2 `get-draft`가 active draft를 안정적으로 식별하는지 canary로 확인해야 합니다.
2. push equivalence v1에서 허용할 formatting-only 차이를 table padding 외에 어디까지 둘지 reviewer 합의가 필요합니다.
3. page title update를 별도 capability로 언제 도입할지 결정해야 합니다.
4. 새 attachment upload와 기존 attachment version 변경을 별도 transaction으로 지원할지 결정해야 합니다.
5. postcondition 실패 시 conditional automatic restore를 도입할지 별도 safety review가 필요합니다.
6. 실행 artifact 보존 기간과 민감 정보 redaction 정책을 정해야 합니다.
7. Confluence v1 client를 즉시 제거할지, v2 adapter 안정화 기간 동안 fallback으로 유지할지 결정해야 합니다.
