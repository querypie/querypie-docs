# OpenSpec Specs Inventory

이 디렉토리는 accepted durable requirement를 보관합니다.
현재 repository에는 아직 accepted OpenSpec spec이 없습니다.

## Inventory 규칙

새 accepted spec을 추가할 때 이 파일에 다음 정보를 함께 기록합니다.

| Spec | 책임 | 관련 surface | 상태 |
| --- | --- | --- | --- |
| `<spec-id>` | `<durable contract 책임>` | `<docs/src/confluence-mdx/tests 등>` | accepted |

## Spec ID 규칙

- 사용자-facing documentation workflow: `uc-*`
- site foundation, authoring platform, reviewer/debugging capability: `platform-*`
- data, loader, metadata, validation, route resolution, content workflow contract: `contract-*`
- deployment, runtime, observability, operations: `infra-*`

## Accepted Spec 작성 규칙

- Accepted spec은 구현자가 보존해야 할 계약을 설명합니다.
- Accepted spec에 task checklist를 넣지 않습니다.
- 새 구현 순서, 검증 checklist, migration step은 `openspec/changes/<change-id>/tasks.md`에 둡니다.
- Requirement는 `SHALL`, `SHALL NOT`, `MAY`, `SHOULD`, `MUST` 같은 modality token을 사용합니다.
- Scenario는 `GIVEN`, `WHEN`, `THEN`, `AND`로 관찰 가능한 조건과 결과를 적습니다.

## 후보 Backlog

아래 후보는 필요할 때 별도 OpenSpec change로 승격합니다.

- `contract-content-source-of-truth`
- `contract-locale-sync`
- `contract-confluence-mdx-conversion`
- `contract-reverse-sync`
- `platform-docs-site-routing`
- `contract-api-reference-rendering`
- `contract-agent-skill-authoring`
