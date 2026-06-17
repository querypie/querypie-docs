# OpenSpec

이 디렉토리는 `querypie-docs`의 durable implementation contract를 기록합니다.

OpenSpec spec은 일회성 plan이 아닙니다.
현재와 미래의 documentation site, content workflow, Confluence conversion, reverse sync, deployment-facing behavior가 보존해야 하는 계약을 설명합니다.

## 구조

- `project.md` — 모든 spec에 적용되는 repository-wide context입니다.
- `specs/` — accepted durable requirement를 둡니다.
- `specs/<spec-id>/spec.md` — 하나의 platform, content workflow, data contract, 또는 user-facing capability를 설명합니다.
- `changes/<change-id>/proposal.md` — 제안된 requirement 또는 contract change를 설명합니다.
- `changes/<change-id>/design.md` — trade-off, alternative, migration, risk가 있는 변경의 decision record입니다.
- `changes/<change-id>/tasks.md` — 해당 변경의 implementation 및 verification checklist입니다.
- `changes/<change-id>/specs/<spec-id>/spec.md` — accepted spec을 즉시 수정하지 않아야 할 때 사용하는 change-local spec delta입니다.
- `archive/<date>-<change-id>/` — change가 accepted 및 implemented 상태가 된 뒤 보존하는 완료 이력입니다.

## 작성 규칙

- OpenSpec Markdown 본문은 한국어로 작성합니다.
- spec id, file name, `Requirement`와 `Scenario` 같은 heading, code identifier, route path, API name, modality token은 더 명확하거나 canonical한 경우 영어를 유지합니다.
- Normative requirement에는 `SHALL`, `SHALL NOT`, `MAY`, `SHOULD`, `MUST`를 사용합니다.
- 테스트 가능한 behavior는 `GIVEN` / `WHEN` / `THEN` / `AND` Scenario로 작성합니다.
- Implementation reference는 maintainer가 source를 찾을 수 있을 만큼 구체적으로 쓰되, 큰 code block을 중복하지 않습니다.
- 범위 제외는 금지가 아닙니다. 명시적으로 금지된 behavior가 아니면 `out of scope`, `future scope`, `backlog`로 구분합니다.
- Implementation task checklist는 accepted `openspec/specs/**/spec.md`가 아니라 `openspec/changes/<change-id>/tasks.md`에 둡니다.
- `docs/**`와 `openspec/**`에 같은 Requirement, Scenario, decision table, task checklist를 길게 중복하지 않습니다.

## 작성 흐름

1. 새 durable contract가 필요한지 판단합니다.
   - 구현 PR이 따라야 할 요구사항, route behavior, content workflow, converter behavior, verification 기준이면 OpenSpec 대상입니다.
   - 일회성 작업 메모, 단순 번역 요청, 임시 조사 결과는 OpenSpec 대상이 아닙니다.
2. 기존 accepted spec이 있으면 `openspec/specs/**/spec.md`를 먼저 확인합니다.
3. 새 요구사항 또는 기존 계약 변경이면 `openspec/changes/<change-id>/proposal.md`와 `tasks.md`를 먼저 작성합니다.
4. decision, migration, risk, rejected alternative가 있으면 `design.md`를 추가합니다.
5. 구현과 검증이 완료되면 accepted spec을 갱신하고 완료된 change를 `archive/<date>-<change-id>/`로 이동합니다.

## 검증

OpenSpec 문서만 변경한 경우 기본 검증은 다음입니다.

```bash
git diff --check
rg -n "<핵심 requirement phrase>" openspec docs src confluence-mdx
```

코드 또는 콘텐츠 구현을 포함하는 PR은 해당 change의 `tasks.md`에 적은 focused verification을 추가로 실행합니다.
