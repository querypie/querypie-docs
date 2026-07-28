## Context

Confluence catalog는 content ID, 현재 제목의 영어 번역, 그리고 그 번역에서 생성한 path를 보관합니다. Conversion manifest는 content ID별로 실제 생성한 MDX path를 보관하므로, 같은 content ID의 manifest path가 달라지면 제목 또는 상위 계층 변경에 따른 public route 이동으로 판별할 수 있습니다.

기존 `content-slug-overrides.yaml`은 표시 제목과 canonical slug를 분리해 route를 고정했습니다. 이 동작은 제목 변경을 public route에도 반영한다는 새 정책과 충돌합니다.

## Goals / Non-Goals

Goals:

- 현재 문서 제목의 영어 번역을 canonical route의 최우선 기준으로 사용합니다.
- route 이동 시 기존 링크에 8주간 임시 redirect를 제공합니다.
- 생성일과 만료일을 review 가능한 repository data로 보존합니다.
- 만료된 redirect가 배포 설정에 남거나 계속 서비스되지 않도록 합니다.
- 연속 rename과 상위 문서 이동에서 redirect chain을 만들지 않습니다.

Non-Goals:

- 과거의 모든 수동 redirect를 같은 registry로 즉시 이전하지 않습니다.
- attachment URL 이동과 cleanup은 이번 변경 범위에 포함하지 않습니다.
- 외부 사이트로 향하는 legacy release note redirect 정책은 변경하지 않습니다.

## Decisions

### Decision: canonical route는 현재 제목 번역에서 생성합니다

Fetcher는 `breadcrumbs_en` 각 항목을 현재 title translation으로 계산하고 `slugify`하여 path를 생성합니다. Content ID 기반 stable slug override는 적용하지 않습니다. 상위 제목이 바뀌면 descendant path도 현재 breadcrumb 계층에 맞게 함께 이동합니다.

### Decision: conversion manifest의 content ID를 route 이동 identity로 사용합니다

`convert_all.py`는 성공한 conversion을 finalization할 때 이전 manifest와 현재 output에서 `kind: mdx`인 항목을 content ID로 비교합니다. 같은 content ID의 `.mdx` path가 달라지면 이전 확장자를 제거한 route에서 새 route로 redirect를 생성합니다.

Navigation `_meta.ts` 변경과 삭제된 content는 redirect 생성 대상이 아닙니다.

### Decision: redirect registry는 locale 독립 exact route를 저장합니다

`src/content-route-redirects.yaml`은 다음 필드를 가진 record 목록을 저장합니다.

- `source`: locale prefix가 없는 이전 exact route
- `destination`: locale prefix가 없는 현재 exact route
- `created_on`: `YYYY-MM-DD` UTC 생성일
- `expires_on`: `created_on`부터 기본 56일 뒤의 `YYYY-MM-DD` 만료일

Next.js loader는 각 active record를 `ko`, `en`, `ja` locale route와 locale 없는 route에 대한 임시 redirect로 확장합니다. Redirect는 영구 cache를 피하기 위해 `permanent: false`를 사용합니다.

### Decision: expiration은 runtime 제외와 persisted cleanup을 함께 적용합니다

`current_date >= expires_on`인 record는 active redirect가 아니며 Next.js route 설정에서 제외합니다. Confluence conversion이 성공해 manifest를 finalization할 때 같은 조건의 record를 registry에서 제거합니다.

따라서 conversion 주기와 무관하게 만료 시점 이후 배포에서는 redirect가 서비스되지 않으며, 다음 conversion에서는 repository record도 삭제됩니다.

### Decision: 연속 rename은 최종 목적지로 접습니다

기존 active redirect의 `destination`이 이번 이동의 이전 route와 같으면 생성일과 만료일을 유지한 채 새 route로 목적지를 갱신합니다. 이번 이동의 이전 route에는 별도 8주 redirect를 생성합니다.

새 live route와 같은 `source`를 가진 과거 redirect는 제거해 실제 content route와 redirect가 충돌하지 않도록 합니다.

## Risks / Trade-offs

- 제목 번역 수정만으로도 public route가 바뀌므로 번역 review가 route review를 포함하게 됩니다.
- 상위 문서 제목 변경은 여러 descendant exact redirect를 만들 수 있습니다. Wildcard redirect보다 record 수는 늘지만, content ID별 이동을 명시적으로 검증할 수 있고 다른 route를 과도하게 포착하지 않습니다.
- Registry cleanup은 conversion에서 persisted data를 갱신합니다. Conversion 사이에도 runtime loader가 만료 record를 제외하므로 만료된 redirect가 계속 서비스되는 문제는 없습니다.

## Migration Plan

1. content ID 기반 slug override 지원과 현재 override data를 제거합니다.
2. 기존 conversion manifest를 기준으로 새 제목 route를 생성합니다.
3. 이번에 이동하는 content별 8주 redirect를 registry에 기록합니다.
4. 한국어 문서를 새 route로 변환하고 영어·일본어 파일도 같은 route로 이동합니다.
5. locale별 이전 route가 새 route로 redirect되고 만료 record가 제외되는지 검증합니다.

## Open Questions

- 없음.
