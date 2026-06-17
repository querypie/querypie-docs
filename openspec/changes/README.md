# OpenSpec Changes

이 디렉토리는 proposed requirement 또는 contract change를 보관합니다.
현재 active change는 없습니다.

## Change 구조

일반적인 change는 다음 구조를 사용합니다.

```text
openspec/changes/<change-id>/
  proposal.md
  design.md
  tasks.md
  specs/<spec-id>/spec.md
```

- `proposal.md`는 왜 변경이 필요한지와 어떤 capability가 바뀌는지 설명합니다.
- `design.md`는 decision, rejected alternative, migration, risk가 있을 때 작성합니다.
- `tasks.md`는 implementation, verification, drift check, cleanup checklist를 기록합니다.
- `specs/<spec-id>/spec.md`는 accepted spec을 즉시 바꾸기 어려울 때 사용하는 change-local spec delta입니다.

## Proposal 최소 형식

```md
## Why

## What Changes

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact
```

## Tasks 최소 형식

```md
## 1. Contract

## 2. Implementation

## 3. Verification

## 4. Spec / 구현 drift 확인

## 5. OpenSpec Cleanup
```

## 운영 규칙

- 하나의 change는 하나의 reviewable contract change를 다룹니다.
- 서로 독립적인 product area 또는 workflow는 별도 change로 분리합니다.
- Backlog 항목은 Product Owner 또는 reviewer가 우선순위를 명시하기 전까지 구현 task로 취급하지 않습니다.
- 구현이 완료된 change는 accepted spec 정리 후 `openspec/archive/<date>-<change-id>/`로 이동합니다.
