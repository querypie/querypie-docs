---
name: openspec-task-execution
description: "OpenSpec tasks.md의 남은 구현, 검증 보강, PR-sized 후속 작업을 수행할 때 사용합니다."
---

# OpenSpec Task Execution

QueryPie 문서 저장소에서 OpenSpec changes/specs에 남은 `tasks.md` 항목, 후속 구현, verification 보강, PR-sized 작업 수행을 요청받았을 때 사용합니다.
목표는 OpenSpec을 source of truth로 삼아 남은 작업을 우선순위와 PR-sized 단위로 나누고, 기존 Open PR과 구현 drift를 먼저 확인한 뒤, 준비된 작업은 PR로 만들고 막힌 작업은 blocker report로 모으는 것입니다.

## 함께 읽을 skill

- 작업 시작 시 `.agents/skills/README.md`, `openspec/README.md`, `openspec/project.md`를 읽습니다.
- OpenSpec 문서의 모순, 누락, stale Scenario, 구현과의 drift가 확인되면 `.agents/skills/openspec-doc-maintenance/SKILL.md`를 읽고 OpenSpec 수정 작업을 분리합니다.
- 새 spec, proposal, design, tasks를 작성하거나 큰 요구사항 변경을 기록해야 하면 `.agents/skills/openspec-authoring/SKILL.md`를 읽습니다.
- PR 생성 전에는 active runtime에 `create-pr` skill이 있으면 읽고, 없으면 `AGENTS.md`와 `docs/commit-pr-guide.md`를 따릅니다.

## 사용 시점

- `openspec/changes/<change-id>/tasks.md`에 남은 항목을 실행해야 할 때
- Accepted spec의 Scenario 또는 Requirement를 기준으로 구현 또는 검증 gap을 메워야 할 때
- 특정 OpenSpec change, PR, branch 작업을 이어받아 task 완료 여부를 검증해야 할 때
- OpenSpec은 존재하지만 현재 코드와 맞는지 확신이 없어 drift 검사부터 필요한 때
- 준비된 작업과 blocker를 분리해 PR, PR 본문, GitHub Issue 또는 최종 보고로 남겨야 할 때

사용하지 않습니다:

- OpenSpec 문서만 새로 작성하거나 정리하는 작업은 `openspec-authoring` 또는 `openspec-doc-maintenance`를 우선합니다.
- 단순 MDX 번역/교정 작업은 번역/교정 skill을 우선합니다.
- Confluence 변환 또는 reverse sync 작업은 관련 Confluence/reverse sync skill을 우선합니다.
- 단순 code review는 code-review workflow나 일반 review 지침을 우선합니다.

## 우선순위 수행 규칙

OpenSpec task와 backlog 항목은 가능하면 `P1`, `P2`, `P3`, `Backlog` 네 단계 우선순위를 사용합니다.
명시 우선순위가 없는 과제는 기본 `P3`로 간주하되, 사용자의 최신 지시나 해당 OpenSpec change의 priority table이 있으면 그것을 우선합니다.

수행 순서는 다음을 따릅니다.

1. `P1` 과제를 먼저 수행합니다.
2. `P1` 과제 중 `blocked`와 `Backlog`가 아닌 과제를 모두 처리한 뒤 `P2`로 넘어갑니다.
3. `P2` 과제 중 `blocked`와 `Backlog`가 아닌 과제를 모두 처리한 뒤 `P3`로 넘어갑니다.
4. `P3` 과제 중 `blocked`와 `Backlog`가 아닌 과제를 모두 처리하면 남은 `Backlog`와 blocker를 보고합니다.

우선순위 등급의 완료 범위는 `blocked`와 `Backlog`를 제외한 task만 포함합니다.
Product Owner 또는 stakeholder 결정, 외부 credential/session/production 권한, irreversible operation, acceptance criteria 부재, 사용자의 명시 승인 없이는 할 수 없는 PR approve/merge/close 같은 blocker로 막힌 task는 해당 등급의 완료 판단에서 제외합니다.

한 우선순위 등급에서 다음 등급으로 넘어갈 수 있는 조건은 다음 중 하나입니다.

- 해당 등급의 non-blocked task가 최신 `origin/main` 기준으로 이미 완료되어 있습니다.
- agent가 해당 task를 PR-sized 범위로 구현/문서화/검증하고 branch를 push했으며 PR 본문, focused verification, 필요한 GitHub check 상태를 보고했습니다.
- 이미 열린 PR이 해당 task를 실제 diff와 검증 evidence로 커버하고 있어 `already-covered-by-open-pr`로 분류됩니다.
- 남은 미처리 항목은 `blocked` 또는 `Backlog`로 분류되어 blocker report나 완료 보고에 기록되어 있습니다.

열린 PR이 merge되지 않았다는 사실만으로 다음 우선순위 등급 진입을 막지 않습니다.
다만 그 PR이 conflict, failing required check, missing focused verification, 잘못된 base/head, 불명확한 coverage를 가진 경우에는 `already-covered-by-open-pr`로 보지 말고 현재 우선순위에서 repair 또는 follow-up을 먼저 수행합니다.

`Backlog` 우선순위는 구현 대상이 아닙니다.
사용자의 명시적인 지시와 Product Owner/stakeholder 결정 또는 OpenSpec change를 통한 `P1`, `P2`, `P3` 승격이 모두 있어야 작업 대상으로 삼습니다.

## 실행 절차

1. Open PR의 구현 내용을 먼저 파악합니다.
   - `gh pr list --state open`으로 현재 열린 PR 목록을 확인합니다.
   - 관련 후보 PR은 `gh pr view <number> --json title,body,author,headRefName,baseRefName,files,commits,url`과 `gh pr diff <number>` 또는 `gh pr diff <number> --name-only`로 구현 의도, 변경 파일, 실제 diff, 검증 흔적을 확인합니다.
   - Open PR에서 이미 진행 중인 작업을 `in-flight work inventory`로 기록하고, OpenSpec 문서만 보고 새 작업을 먼저 시작하지 않습니다.
2. 기준 OpenSpec을 찾습니다.
   - `openspec/changes/<change-id>/tasks.md`, `proposal.md`, `design.md`, `specs/**/spec.md`를 우선 확인합니다.
   - 이미 archive된 change라면 현재 `openspec/specs/**/spec.md`와 관련 문서에서 active 계약을 확인합니다.
   - 기준 change가 둘 이상이면 task와 PR을 change 단위로 분리합니다.
3. task inventory를 만들고 Open PR과 매핑합니다.
   - unchecked task, follow-up task, Scenario, Requirement, affected code path, 필요한 검증 명령을 한 묶음으로 정리합니다.
   - 각 task의 우선순위를 `P1`, `P2`, `P3`, `Backlog` 중 하나로 기록합니다.
   - task에 우선순위가 명시되어 있지 않으면 `P3`로 기록합니다.
   - `Backlog` task는 Product Owner/stakeholder 결정 또는 OpenSpec change로 승격되기 전까지 실행 inventory에서 제외하고 backlog/report inventory에만 기록합니다.
   - task가 너무 크면 하나의 검증 가능한 사용자 가치 또는 OpenSpec requirement 단위로 쪼갭니다.
   - 각 task마다 매핑되는 Open PR 번호, 매핑 근거, coverage 상태를 기록합니다.
   - coverage 상태는 `covered`, `partially-covered`, `not-covered`, `unclear` 중 하나로 둡니다.
   - Open PR이 해당 작업을 실제로 수행했는지 PR 제목이나 설명만으로 판단하지 말고 diff와 affected path를 확인합니다.
   - 다른 사람 또는 다른 agent가 해당 작업에 적합한 Open PR을 이미 작성했다면 같은 작업을 새로 수행하지 않습니다.
4. 각 task를 분류합니다.
   - `ready-implementation`: OpenSpec이 유효하고, 해당 작업에 적합한 Open PR이 없으며, 코드 구현이 부족합니다.
   - `ready-openspec-maintenance`: 코드 또는 제품 결정은 명확하지만 OpenSpec이 stale이거나 누락되어 먼저 문서 PR이 필요합니다.
   - `ready-verification`: 구현과 OpenSpec은 맞고 검증 증거만 보강하면 됩니다.
   - `already-covered-by-open-pr`: 해당 task를 처리하기에 적합한 Open PR이 이미 있어 중복 수행하지 않고 PR 링크와 확인 결과만 보고합니다.
   - `partially-covered-by-open-pr`: Open PR이 task 일부만 처리했으므로 남은 범위를 명시하고 별도 task 또는 follow-up으로 분리합니다.
   - `blocked`: 의사결정, 추가 정보, 외부 권한, 상충 요구사항 때문에 작업을 안전하게 확정할 수 없습니다.
5. OpenSpec과 코드 구현의 drift를 판정합니다.
   - OpenSpec이 현재 의도와 다르면 OpenSpec 수정 PR을 먼저 만듭니다.
   - OpenSpec이 맞고 코드가 뒤처져 있으면 구현 PR을 만듭니다.
   - OpenSpec과 코드가 모두 바뀌어야 하면 OpenSpec PR을 먼저 만들고, 구현 PR은 그 PR branch를 base로 둔 stacked PR로 분리합니다.
   - Open PR의 구현 내용이 OpenSpec task에 매핑되는지 확인한 뒤, 매핑되지 않은 잔여 task만 새로 수행할 작업으로 판정합니다.
   - drift 판정 결과와 Open PR 매핑 결과를 PR 본문 또는 blocker report에 남깁니다.
6. 과제 단위로 PR을 분리합니다.
   - 서로 독립적인 OpenSpec task를 한 PR에 묶지 않습니다.
   - spec-only, implementation, verification/docs evidence PR은 원자성이 없으면 분리합니다.
   - 각 PR은 하나의 명확한 완료 조건과 검증 명령을 가져야 합니다.
   - 구현 완료 후 focused local verification을 실행하고 commit/push/PR 생성 또는 업데이트를 먼저 완료합니다.
   - 추가 GitHub checks, browser rendering 검증은 PR 생성 또는 업데이트 이후 bounded 방식으로 확인합니다.
7. blocker를 모아서 보고합니다.
   - blocker는 chat에만 남기지 말고 PR 본문, 최종 보고, 또는 GitHub Issue에 모읍니다.
   - GitHub Issue가 필요하고 인증이 가능하면 `gh issue create` 또는 `gh issue comment`를 사용합니다.
   - issue는 자동 종료 keyword를 사용하지 않습니다.
8. 검증합니다.
   - 문서 변경은 `git diff --check`와 관련 경로 검색으로 검증합니다.
   - 코드 변경은 task에 직접 연결되는 테스트를 먼저 실행하고, 위험도에 따라 lint, typecheck, build, e2e를 추가합니다.
   - GitHub check는 bounded 확인만 수행하고, 오래 걸리면 latest known state와 미확인 범위를 보고합니다.
9. 완료 보고를 작성합니다.
   - 생성한 PR, task 출처, Open PR 구현 매핑 결과, 중복 방지 확인 결과, drift 판정, blocker report, 검증 결과, 남은 위험을 요약합니다.
   - 우선순위 전환이 있었다면 해당 우선순위의 non-blocked task 처리 결과와 완료 범위에서 제외한 blocker 목록을 구분해 적습니다.
   - 사용자의 명시적 승인 없이 PR approve, merge, close 또는 `main` 직접 push를 하지 않습니다.

## Blocker 판정 기준

다음은 blocker로 분류합니다.

- Product Owner 또는 stakeholder의 scope, UX, 용어, 우선순위, 정책 결정이 필요한 경우
- OpenSpec Requirement 또는 Scenario끼리 충돌해 구현 기준을 하나로 고를 수 없는 경우
- 외부 계정, credential, production 권한, 제3자 서비스 상태가 필요하고 agent가 안전하게 대체할 수 없는 경우
- data migration, 삭제, irreversible operation처럼 안전 경계가 필요한 경우
- acceptance criteria가 없어 선택지별 구현 결과가 사용자 행동이나 데이터 계약을 바꾸는 경우
- agent가 PR branch를 push하고 필요한 검증을 보고했지만 사용자의 명시 승인 없이는 PR approve, merge, close, direct `main` push를 할 수 없는 경우

다음은 blocker로 분류하지 않습니다.

- 일반적인 코드 검색, 영향 범위 조사, 테스트 실패 원인 분석
- OpenSpec에서 합리적으로 추론 가능한 작은 구현 세부사항
- 단순 lint, typecheck, formatting 실패

## Blocker report 템플릿

```md
## 요약

- 기준 OpenSpec: `<change-id 또는 spec path>`
- 실행하려던 작업 범위: `<task 범위>`
- 현재 진행 상태: `<완료, 진행 중, 중단된 항목 요약>`

## Blocker 목록

| Task | 수행하려던 작업 | Blocker인 이유 | 고민 중인 선택지 | 필요한 의사결정 또는 정보 | 영향 범위 | 제안 next action |
| --- | --- | --- | --- | --- | --- | --- |
| `<task id>` | `<구체적 작업>` | `<왜 안전하게 진행할 수 없는지>` | `<option A / option B>` | `<누가 무엇을 결정 또는 제공해야 하는지>` | `<spec/code/test path>` | `<추천 후속 조치>` |

## 계속 진행 가능한 작업

- `<blocker 없이 PR로 진행 가능한 task>`

## 관련 링크

- PR: `<url>`
- Branch: `<branch>`
- 검증: `<command/status>`
```

## PR 본문에 포함할 내용

- 기준 OpenSpec change 또는 spec path
- 수행한 task와 제외한 task
- Open PR 구현 매핑 및 중복 방지 확인 결과
- OpenSpec과 코드 구현 drift 판정
- blocker report 또는 GitHub Issue 링크가 있다면 해당 링크
- 검증 명령과 결과
- UI 변경이 있으면 screenshot, DOM geometry, computed-style evidence 또는 headless verification 결과

## 흔한 실수

- OpenSpec 확인 없이 이전 chat 맥락만 보고 구현하지 않습니다.
- 하나의 PR에 독립적인 여러 task를 몰아넣지 않습니다.
- Open PR 확인 없이 다른 사람 또는 다른 agent가 이미 다루는 작업을 중복 수행하지 않습니다.
- blocker를 발견할 때마다 사용자에게 단발 질문으로 넘기지 않습니다.
- stale OpenSpec 수정을 구현 PR에 섞지 않습니다.
- 실패한 테스트를 원인 분석 없이 blocker로 선언하지 않습니다.
- CI trigger만을 위한 empty commit 또는 날짜 amend를 만들지 않습니다.
- 사용자의 명시적 승인 없이 PR을 approve, merge, close하지 않습니다.
