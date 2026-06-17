---
name: openspec-authoring
description: "QueryPie 문서 저장소의 OpenSpec spec, proposal, design, tasks를 새로 작성하거나 크게 갱신할 때 사용합니다."
---

# OpenSpec Authoring

QueryPie 문서 저장소에서 OpenSpec spec, proposal, design, tasks를 새로 작성하거나 크게 갱신할 때 사용합니다.
목표는 `openspec/`를 일회성 계획이 아니라 구현자가 따라야 하는 durable contract layer로 유지하는 것입니다.

## 사용 시점

- 새 `openspec/specs/<spec-id>/spec.md`를 작성할 때
- 기존 OpenSpec spec의 Requirement 또는 Scenario를 크게 바꿀 때
- 요구사항 변경을 `openspec/changes/<change-id>/` 아래 proposal, design, tasks, spec delta로 기록할 때
- 기존 `docs/**`, 현재 구현, 테스트 evidence를 OpenSpec 계약으로 승격할 때
- 구현 PR 전에 요구사항 또는 검증 범위를 먼저 확정해야 할 때

사용하지 않습니다:

- 구현 중 우연히 drift, 모순, stale Scenario를 발견한 경우에는 `openspec-doc-maintenance`를 우선 사용합니다.
- 단순 MDX 번역/교정 작업은 `translation`, `proofread`, `sync-ko-to-en-ja`를 우선 사용합니다.
- Confluence 변환 또는 reverse sync 작업은 관련 Confluence/reverse sync skill을 우선 사용합니다.

## 사전 확인

1. `AGENTS.md`와 `.agents/skills/README.md`를 읽고 현재 repository 규칙을 확인합니다.
2. `openspec/`가 존재하는지 확인합니다.
   - 존재하면 `openspec/README.md`, `openspec/project.md`, `openspec/specs/README.md`를 읽습니다.
   - 존재하지 않으면 이번 요청이 OpenSpec 도입 또는 새 OpenSpec 작성 요청인지 확인하고, 필요한 경우 최소 scaffold를 먼저 작성합니다.
3. 관련 active spec과 change 문서를 확인합니다.
   - `openspec/specs/**/spec.md`
   - `openspec/changes/**/{proposal.md,design.md,tasks.md}`
4. 관련 repository 문서를 찾습니다.
   - 프로젝트 개발 지침: `docs/DEVELOPMENT.md`
   - 번역 지침: `docs/translation.md`
   - API 명칭 지침: `docs/api-naming-guide.md`
   - Confluence 변환 문서: `confluence-mdx/README.md`
   - 기존 구현 계획: `docs/plans/**`, `docs/superpowers/**`
5. 관련 구현 evidence를 찾습니다.
   - 문서 콘텐츠: `src/content/**`
   - 문서 UI와 렌더링: `src/app/**`, `src/components/**`
   - Confluence 변환기: `confluence-mdx/bin/**`
   - 테스트와 check: `tests/**`, `confluence-mdx/tests/**`, `src/**/*.test.*`, `scripts/**`

## 작성 규칙

- 내부 Markdown 본문은 한국어로 작성합니다.
- 파일명, spec id, frontmatter key, route path, API name, code identifier, UI label, 외부 고유명사는 canonical language를 유지합니다.
- Accepted spec은 구현 계약을 설명하고, task checklist를 포함하지 않습니다.
- 후속 구현 순서와 검증 checklist는 `openspec/changes/<change-id>/tasks.md`에 둡니다.
- 제품/기술/운영 의사결정은 필요한 경우 `openspec/changes/<change-id>/design.md`를 canonical decision record로 둡니다.
- Requirement 문장은 가능한 한 `SHALL`, `SHALL NOT`, `MAY`, `SHOULD`, `MUST`를 명시합니다.
- `SHALL NOT`과 `MUST NOT`은 실제 금지, safety guard, security guard, compatibility guard에만 사용합니다.
- 단순 범위 제외는 금지가 아닙니다. `out of scope`, `future scope`, `backlog`로 구분합니다.
- Scenario는 agent가 테스트나 smoke로 바꿀 수 있도록 `GIVEN`, `WHEN`, `THEN`, `AND`를 사용합니다.
- `docs/**`와 OpenSpec에 같은 Requirement, Scenario, decision table, task checklist를 중복으로 길게 유지하지 않습니다.

## 문서 형태

Accepted spec 형식:

```md
# <spec-id>

## Purpose

## References

## Requirements

### Requirement: <name>

<한국어 계약 문장>(SHALL).

#### Scenario: <observable case>

- GIVEN ...
- WHEN ...
- THEN ...(SHALL).
```

Proposal 형식:

```md
## Why

## What Changes

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact
```

Design 형식:

```md
## Context

## Goals / Non-Goals

## Decisions

### Decision: ...

## Risks / Trade-offs

## Migration Plan

## Open Questions
```

Tasks 형식:

```md
## 1. Contract

## 2. Implementation

## 3. Verification

## 4. Spec / 구현 drift 확인

## 5. OpenSpec Cleanup
```

## 작성 절차

1. 변경 대상이 accepted spec 수정인지, 새 change proposal인지 분류합니다.
2. 넓은 요구사항 변경이면 `openspec/changes/<change-id>/proposal.md`와 `tasks.md`부터 작성합니다.
3. decision, alternative, migration, risk가 있으면 `design.md`를 추가합니다.
4. 기존 accepted spec을 즉시 바꾸면 구현과 충돌할 수 있을 때는 `changes/<change-id>/specs/<spec-id>/spec.md`에 delta를 둡니다.
5. 새 spec id는 장기 책임을 기준으로 고릅니다.
   - 사용자-facing workflow: `uc-*`
   - app foundation 또는 reviewer/debugging capability: `platform-*`
   - data, loader, metadata, validation, route resolution contract: `contract-*`
   - deployment, runtime, observability, operations: `infra-*`
6. 후속 구현 task에는 파일 후보, 영향받는 route/page/component/API/test surface, 검증 명령, browser smoke 필요 여부를 적습니다.
7. Verification task는 구현 PR 범위보다 넓게 잡습니다. Cross-page UI, route, component, copy, content loader 계약은 같은 패턴을 쓰는 관련 surface를 source scan, regression test, browser smoke 중 하나 이상으로 확인하도록 적습니다.
8. 새 OpenSpec이 기존 docs 내용을 대체하면 기존 docs는 짧은 bridge link로 축소하거나 중복 내용을 제거합니다.

## 검증

- `git diff --check`로 Markdown whitespace 문제를 확인합니다.
- 핵심 Requirement 또는 decision phrase를 `rg`로 검색해 중복 canonical statement가 생기지 않았는지 확인합니다.
- 새 파일과 수정 파일이 `openspec/README.md`의 layout과 writing rules를 따르는지 확인합니다.
- 코드 변경이 없으면 build를 실행하지 않습니다. 문서 변경 검증과 scope check를 우선합니다.

## 흔한 실수

1. 현재 코드 동작을 제품 의도라고 단정해 stale implementation을 spec으로 고정하는 것
2. accepted spec에 구현 task checklist를 넣어 contract와 실행 계획을 섞는 것
3. `SHALL NOT`을 단순 out-of-scope 항목에 사용해 future scope를 영구 금지처럼 만드는 것
4. `docs/**`와 `openspec/**`에 같은 Requirement를 길게 중복해 drift source를 늘리는 것
5. 후속 구현 범위를 좁게 나눈 것을 이유로 verification 범위까지 좁혀 관련 route, component, locale, loader 회귀를 놓치는 것
