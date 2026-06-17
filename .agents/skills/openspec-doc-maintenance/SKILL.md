# OpenSpec 문서 유지보수

QueryPie 문서 저장소에서 구현, 리뷰, 계획, 디버깅 중 OpenSpec 문서와 실제 계약 사이의 차이를 발견했을 때 사용합니다.
OpenSpec 문제를 대화나 임시 메모에만 남기지 않고, repository의 durable contract로 정리하는 것이 목적입니다.

## 사용 시점

- `openspec/` 아래 문서를 추가, 수정, 정리, 보완할 때
- 구현 또는 테스트에 필요한 Requirement나 Scenario가 OpenSpec에 없을 때
- OpenSpec과 `docs/**`, 코드, 테스트, route behavior가 서로 다른 계약을 말할 때
- stale Scenario, 오래된 route/API/content path, 잘못된 scope exclusion을 발견했을 때
- 코드 구현 중 새 durable contract가 생겼고 `openspec/`에 기록해야 할 때
- 요구사항 변경 또는 스펙 변경이 포함되어 구현 전에 OpenSpec 업데이트가 필요한 때

사용하지 않습니다:

- 처음부터 새 OpenSpec spec이나 change 문서를 작성하는 것이 주 작업이면 `openspec-authoring`을 우선 사용합니다.
- 단순 코드 구현이고 OpenSpec drift 또는 contract 변경이 없으면 사용하지 않습니다.

## 기본 원칙

- 내부 Markdown 본문은 한국어로 작성합니다.
- 파일명, spec id, code identifier, route path, API name, frontmatter key, modality token은 canonical language를 유지합니다.
- OpenSpec은 구현 계약의 source of truth이고, `docs/**`는 workflow, 배경, 예시, 운영 가이드를 보조합니다.
- 현재 사용자의 요청 자체가 OpenSpec 수정이면 같은 작업 PR 안에서 처리합니다.
- 다른 구현/리뷰 작업 중 우연히 발견한 unrelated drift는 별도 OpenSpec PR로 분리합니다.
- 요구사항 변경 또는 스펙 변경이 명확하면 코드 구현 전에 OpenSpec과 후속 task를 먼저 작성합니다.
- 사용자가 명시적으로 implementation-only를 요구하지 않았다면, 새 contract를 코드에만 숨겨 두지 않습니다.

## 유지보수 절차

1. Drift 후보를 분류합니다.
   - 모순: 두 spec 또는 spec과 docs/code가 서로 다른 요구를 말합니다.
   - 오류: 현재 canonical docs나 구현 기준으로 명백히 잘못된 route, field, status, scope가 있습니다.
   - 누락: 구현 또는 검증에 필요한 durable contract가 없습니다.
   - stale: 과거 구현이나 preview-only 상태가 현재 계약처럼 남아 있습니다.
2. 현재 작업 범위와 같은지 판단합니다.
   - 같은 OpenSpec 요청이면 현재 branch에서 수정합니다.
   - unrelated drift면 별도 branch와 PR로 분리합니다.
   - 기존 open PR이 같은 범위를 다루면 새 PR보다 기존 branch 업데이트를 우선 검토합니다.
3. 관련 source를 확인합니다.
   - `AGENTS.md`
   - `openspec/README.md`
   - `openspec/project.md`
   - 관련 `openspec/specs/**/spec.md`
   - 관련 `openspec/changes/**/{proposal.md,design.md,tasks.md}`
   - 관련 `docs/**`, `src/app/**`, `src/content/**`, `src/components/**`, `confluence-mdx/**`, `tests/**`
4. 수정 위치를 고릅니다.
   - accepted durable behavior는 `openspec/specs/<spec-id>/spec.md`
   - proposed requirement change는 `openspec/changes/<change-id>/proposal.md`
   - Decision, alternative, migration, risk는 `openspec/changes/<change-id>/design.md`
   - 후속 구현과 검증 범위는 `openspec/changes/<change-id>/tasks.md`
5. Requirement와 Scenario를 테스트 가능한 계약으로 고칩니다.
   - Requirement는 의무, 금지, 허용, 권고를 modality token으로 표시합니다.
   - Scenario는 `GIVEN`, `WHEN`, `THEN`, `AND`로 관찰 가능한 상태와 결과를 적습니다.
6. 구현 drift 또는 후속 구현이 필요하면 task를 남깁니다.
   - 변경 파일 후보
   - 영향받는 route/page/component/API/content loader/test surface
   - source-level test 또는 browser smoke 검증 방식
   - spec과 implementation drift check 결과 기록 위치
7. 중복 docs를 정리합니다.
   - OpenSpec으로 승격된 Requirement, Scenario, decision table, task checklist는 `docs/**`에 full copy로 유지하지 않습니다.
   - 필요한 docs는 OpenSpec 링크와 짧은 배경 설명으로 축소합니다.
8. PR 설명에는 drift 원인, 수정한 OpenSpec path, 구현 PR과 분리한 이유, 후속 구현 task와 검증 기준을 적습니다.

## PR 분리 기준

별도 PR로 분리합니다:

- 현재 feature 구현과 관계없는 OpenSpec drift
- reviewer가 contract correction만 독립 검토해야 하는 변경
- 코드 구현 전에 합의되어야 하는 요구사항 또는 스펙 변경

같은 PR에 포함할 수 있습니다:

- 사용자가 애초에 OpenSpec 문서 수정을 요청한 경우
- 문서-only PR 자체가 OpenSpec change plan을 수행하는 경우
- 구현 변경의 acceptance criteria를 정확히 반영하기 위해 같은 작은 spec/task 보정이 필요한 경우

## 검증

- `git diff --check`를 실행합니다.
- 핵심 phrase를 `rg`로 검색해 중복 canonical statement가 남지 않았는지 확인합니다.
- 변경한 OpenSpec path와 관련 docs path를 PR body에 적을 수 있을 만큼 scope를 확인합니다.
- 코드 변경 없이 OpenSpec만 수정했다면 build보다 문서 diff, scope, 중복 검색을 우선 검증합니다.

## 흔한 실수

1. 구현 중 발견한 spec 문제를 대화에만 남기고 PR로 정리하지 않는 것
2. unrelated OpenSpec correction을 feature PR에 섞는 것
3. 새 Requirement를 만들고도 후속 implementation task와 verification 범위를 남기지 않는 것
4. `docs/**`와 `openspec/**`에 같은 contract를 길게 중복하는 것
5. 대표 화면 하나만 확인하고 shared route, component, locale, content loader 영향 범위를 검증 task에서 누락하는 것
6. scope exclusion을 금지처럼 작성해 future work를 불필요하게 막는 것
