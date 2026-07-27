---
name: reverse-sync
description: "MDX 변경을 Confluence XHTML로 역반영하는 reverse-sync 작업을 수행하거나 검증할 때 사용합니다."
---

# Reverse Sync 사용 가이드

## 개요

`reverse-sync`는 repository의 original/improved MDX 차이를 기존 Confluence
Storage XHTML에 적용하고, local proof와 원격 compare-and-set/postcondition을
통과한 경우에만 page body를 갱신합니다.

소스는 `confluence-mdx/bin/reverse_sync_cli.py`와
`confluence-mdx/bin/reverse_sync/**`에 있습니다. durable contract는
`openspec/changes/complete-reverse-sync`를 따릅니다.

실제 Confluence PUT은 승인된 page에만 수행합니다. 승인된 canary 검증 전에는
production batch push를 실행하지 않습니다.

## lifecycle

```text
offline diagnostic
  verify/debug ──> pass/fail/blocked (push_eligible=false)

online prepare
  push --dry-run ──> PageSnapshot + PatchPlan + local proof
                  └─> immutable SyncManifest (verified_local)

publish
  push <mdx>       ──> online prepare + confirmation + publisher
  push --manifest ──> explicit verified run + confirmation + publisher
                       └─> preflight → PUT once → postcondition
```

핵심 원칙:

- `verify`와 `debug`는 로컬 `page.xhtml` 기반 진단입니다. 결과가 `pass`여도
  publish 권한을 부여하지 않습니다.
- publish 가능한 검증은 원격 current page를 하나의 `PageSnapshot`으로 읽는
  online prepare에서만 생성됩니다.
- publisher는 flat `reverse-sync.patched.xhtml`을 읽지 않고 explicit
  `manifest.json`이 결합한 candidate만 사용합니다.
- `--yes`는 사용자 confirmation만 생략합니다. artifact, proof, dependency,
  remote preflight, postcondition gate는 생략하지 않습니다.
- remote version/body/title이 verify base와 다르면 최신 version으로 자동
  재시도하지 않습니다. 새 online prepare가 필요합니다.

## 커맨드

| 커맨드 | 설명 |
| --- | --- |
| `verify` | 로컬 XHTML round-trip 진단. `push_eligible`은 항상 false입니다. |
| `debug` | `verify`와 같지만 MDX/XHTML/round-trip diff를 모두 출력합니다. |
| `push --dry-run` | 원격 snapshot으로 online prepare를 수행하고 PUT은 생략합니다. |
| `push <mdx>` | online prepare 후 생성한 manifest를 확인하고 한 page를 발행합니다. |
| `push --manifest <path>` | 이미 검증한 explicit immutable run을 다시 online verify하지 않고 발행합니다. |
| `push --branch <branch>` | 모든 local proof를 먼저 수행한 뒤 page별 독립 transaction으로 발행합니다. |

## 기본 사용법

```bash
cd confluence-mdx

# offline diagnostic
bin/reverse_sync_cli.py verify \
  "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

bin/reverse_sync_cli.py debug \
  "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

# 원격 snapshot 기반 online prepare, PUT 없음
bin/reverse_sync_cli.py push --dry-run \
  "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

# online prepare + 확인 + 단일 page publish
bin/reverse_sync_cli.py push \
  "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

# 이전 prepare의 explicit run publish
bin/reverse_sync_cli.py push --manifest \
  var/<page-id>/reverse-sync/<run-id>/manifest.json

# branch diagnostic
bin/reverse_sync_cli.py verify --branch proofread/fix-typo
```

비대화형 환경에서 PUT을 요청하면 `--yes`가 필요합니다. 이 옵션을 사용하기 전에
page ID, base version, change 수, candidate hash를 별도 로그에서 확인합니다.

## MDX와 page 지정

MDX source는 다음 형식을 사용합니다.

| 형식 | 예시 |
| --- | --- |
| `ref:path` | `proofread/fix-typo:src/content/ko/overview.mdx` |
| local `path` | `src/content/ko/overview.mdx` |

기본 original은 `main:<improved path>`입니다. `--original-mdx`로 명시할 수
있습니다.

page ID는 `src/content/ko/**.mdx` path와
`confluence-mdx/var/pages.qm.yaml`의 유일한 row로 확인합니다.
필요하면 `--page-id`로 명시합니다. offline fixture는 `--page-dir`에
`page.xhtml`과 page metadata가 있는 디렉터리를 지정할 수 있습니다.

branch mode는 page마다 catalog identity를 계산하므로 `--original-mdx`,
`--page-id`, `--page-dir`과 함께 사용하지 않습니다.

## 주요 옵션

| 옵션 | 범위 | 설명 |
| --- | --- | --- |
| `--branch <branch>` | 공통 | 변경된 `src/content/ko/**.mdx`를 batch 처리합니다. |
| `--original-mdx <source>` | 단일 | original MDX를 명시합니다. |
| `--page-id <id>` | 단일 | catalog에서 유도할 page ID를 명시합니다. |
| `--page-dir <path>` | 단일 diagnostic | `var/<page-id>/` 대신 사용할 fixture 디렉터리입니다. |
| `--limit N` | batch | 처리할 최대 file 수입니다. |
| `--failures-only` | batch | 결과 표시만 실패 항목으로 제한합니다. summary는 전체 기준입니다. |
| `--lenient` | diagnostic | 추가 관대 비교를 기록합니다. push eligibility에는 영향이 없습니다. |
| `--no-normalize` | diagnostic | raw 비교를 추가합니다. push eligibility에는 영향이 없습니다. |
| `--dry-run` | push | online prepare까지만 수행합니다. |
| `--manifest <path>` | push | 다른 source/branch/diagnostic 옵션과 함께 쓸 수 없는 explicit run입니다. |
| `--yes` | push | confirmation만 생략합니다. |
| `--json` | 공통 | machine-readable 결과를 출력합니다. |

## 상태

| 상태 | 의미 |
| --- | --- |
| `pass` | offline diagnostic round-trip이 통과했습니다. publish 가능 상태가 아닙니다. |
| `blocked` / `fail` | identity, capability, proof 또는 equivalence가 통과하지 못했습니다. |
| `verified_local` | online prepare의 모든 local gate를 통과한 manifest가 있습니다. |
| `remote_verified` | PUT 후 persisted remote snapshot과 target이 동등합니다. |
| `already_applied` | remote에 target이 이미 적용되어 PUT을 생략했습니다. |
| `no_changes` | source intent가 없어 PUT을 생략합니다. |
| `postcondition_failed` | PUT 뒤 persisted 결과를 증명하지 못했습니다. 후속 batch publish를 중단합니다. |
| `not_attempted` | batch 중단 또는 사용자 취소로 PUT을 시도하지 않았습니다. |

`unsupported_capability`, `missing_identity`, `remote_drift`,
`version_conflict`, `artifact_tampered` 같은 reason code를 상태와 함께
확인합니다. `pass` 문자열만으로 publish 가능 여부를 판단하지 않습니다.

## 실행별 immutable artifact

online prepare가 성공하면 다음 run directory를 생성합니다.

```text
var/<page-id>/reverse-sync/<run-id>/
├── base.xhtml
├── original.mdx
├── improved.mdx
├── patch-plan.json
├── candidate.xhtml
├── local-proof.json
├── manifest.json
└── manifest.sha256
```

publish 후에는 같은 directory에 preflight/post snapshot, provider evidence,
`push-receipt.json`이 추가됩니다. `manifest.json`과 referenced artifact는
검증 후 수정하지 않습니다. 수정되었거나 현재 tool/policy와 schema가 다르면
publisher가 차단합니다.

`var/<page-id>/reverse-sync.*`와 `verify.mdx`는 fixture/debug 호환 출력입니다.
publish payload나 verified evidence로 사용하지 않습니다.

## batch report와 재개

branch `--json`은 raw array가 아니라
`reverse-sync-batch-report` schema v1 object를 반환합니다.

- `outcome`: `success`, `partial_success`, `failed`, `cancelled`
- `exit_code`: success/cancelled는 0, partial/failed는 1
- `summary`: stable status counter
- `results`: page별 `batch_status`와 reason code
- `resume_manifests`: postcondition failure 뒤 아직 PUT하지 않은 explicit run

batch는 page별 독립 transaction입니다. 앞 page의 `remote_verified`를 뒤 page
실패 때문에 rollback된 것처럼 해석하지 않습니다. `resume_manifests`의 각
경로는 별도의 `push --manifest <path>`로 확인 후 재개합니다. conflict 또는
remote drift가 발생한 manifest는 재사용하지 않고 새 online prepare를
수행합니다.

## 검증과 문제 분석

```bash
# machine-readable online prepare
bin/reverse_sync_cli.py push --dry-run --json \
  "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

# branch 실패 결과
bin/reverse_sync_cli.py verify --branch proofread/fix-typo \
  --failures-only --json

# XHTML 의미 diff는 diagnostic compatibility output에만 사용
bin/xhtml_beautify_diff.py \
  var/<page-id>/page.xhtml \
  var/<page-id>/reverse-sync.patched.xhtml
```

`postcondition_failed`에서는 run directory의 base/candidate/post snapshot과
receipt를 보존합니다. remote가 attempted candidate인지 확인하지 않은 자동
restore를 수행하지 않습니다.

## Confluence 인증

online prepare와 publish에는
`~/.config/atlassian/confluence.conf`가 필요합니다.

```text
email:api_token
```

credential과 Authorization header를 manifest, report, log에 기록하지 않습니다.

## 관련 Skill

- [xhtml-beautify-diff](../xhtml-beautify-diff/SKILL.md)
- [confluence-mdx](../confluence-mdx/SKILL.md)
- [reverse-sync-debugging](../reverse-sync-debugging/SKILL.md)
