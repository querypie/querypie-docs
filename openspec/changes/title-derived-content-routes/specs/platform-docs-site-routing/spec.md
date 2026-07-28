# platform-docs-site-routing

## Purpose

Confluence 제목 변경을 public canonical route에 반영하고 이전 route의 제한된 호환 기간을 관리하는 계약을 정의합니다.

## References

- `confluence-mdx/bin/fetch/translation.py`
- `confluence-mdx/bin/convert_all.py`
- `src/content-route-redirects.yaml`
- `next.config.ts`

## Requirements

### Requirement: Title-derived canonical route

Confluence에서 생성하는 content의 canonical route는 현재 문서 제목의 영어 번역을 slugify한 breadcrumb path를 사용해야 합니다(SHALL). 이전 route를 유지하기 위한 content ID 기반 slug override를 적용해서는 안 됩니다(SHALL NOT).

#### Scenario: 문서 제목 변경

- GIVEN 같은 content ID의 문서 제목 번역이 변경되었습니다.
- WHEN Confluence catalog와 MDX를 다시 생성합니다.
- THEN canonical route는 새 제목 번역에서 생성되어야 합니다(SHALL).
- AND 이전 제목에서 생성한 route를 content output으로 보존해서는 안 됩니다(SHALL NOT).

#### Scenario: 상위 문서 제목 변경

- GIVEN 상위 문서 제목 번역이 변경되었습니다.
- WHEN descendant content의 breadcrumb path를 다시 생성합니다.
- THEN 상위 문서와 모든 descendant의 canonical route는 새 breadcrumb path를 사용해야 합니다(SHALL).

### Requirement: Route move detection

Converter는 성공한 conversion의 이전·현재 manifest에서 같은 content ID의 `kind: mdx` path를 비교해 route 이동을 감지해야 합니다(SHALL).

#### Scenario: 같은 content ID의 output path 변경

- GIVEN 이전 manifest에 content ID의 기존 MDX path가 있습니다.
- AND 현재 conversion에 같은 content ID의 다른 MDX path가 있습니다.
- WHEN manifest를 finalization합니다.
- THEN 이전 route에서 현재 route로 redirect record를 생성해야 합니다(SHALL).

#### Scenario: content 삭제

- GIVEN 이전 manifest의 content ID가 현재 conversion에서 사라졌습니다.
- WHEN manifest를 finalization합니다.
- THEN 목적지가 없는 redirect를 생성해서는 안 됩니다(SHALL NOT).

### Requirement: Eight-week redirect lifecycle

새 redirect record는 UTC `created_on`과 기본 56일 뒤의 `expires_on`을 가져야 합니다(SHALL). `current_date >= expires_on`인 redirect는 active rule에서 제거해야 합니다(SHALL).

#### Scenario: redirect 생성

- GIVEN `2026-07-28`에 route 이동을 감지했습니다.
- WHEN redirect record를 생성합니다.
- THEN `created_on`은 `2026-07-28`이어야 합니다(SHALL).
- AND `expires_on`은 `2026-09-22`이어야 합니다(SHALL).

#### Scenario: redirect 만료

- GIVEN redirect의 `expires_on`이 current date와 같거나 이전입니다.
- WHEN Next.js redirect 설정을 생성합니다.
- THEN 해당 redirect를 runtime rule에 포함해서는 안 됩니다(SHALL NOT).
- WHEN 다음 Confluence conversion을 finalization합니다.
- THEN 해당 redirect record를 persisted registry에서 제거해야 합니다(SHALL).

### Requirement: Temporary locale redirects

Active content route redirect는 `ko`, `en`, `ja` locale route와 locale prefix가 없는 route에 적용해야 하며(SHALL), 영구 redirect로 cache해서는 안 됩니다(SHALL NOT).

#### Scenario: locale route 접근

- GIVEN `/support/old-route`에서 `/support/new-route`로 이동한 active redirect가 있습니다.
- WHEN `/ko/support/old-route`, `/en/support/old-route`, `/ja/support/old-route` 중 하나에 접근합니다.
- THEN 같은 locale의 `/support/new-route`로 임시 redirect해야 합니다(SHALL).

#### Scenario: locale prefix 없는 route 접근

- GIVEN active content route redirect가 있습니다.
- WHEN locale prefix 없는 이전 route에 접근합니다.
- THEN locale prefix 없는 새 route로 임시 redirect해야 합니다(SHALL).

### Requirement: Redirect chain prevention

같은 content가 redirect 유지 기간 안에 다시 이동하면 기존 redirect의 목적지를 최신 canonical route로 갱신해야 합니다(SHALL). 새 live route와 source가 같은 과거 redirect는 제거해야 합니다(SHALL).

#### Scenario: 연속 제목 변경

- GIVEN active redirect `/title-a` → `/title-b`가 있습니다.
- WHEN 같은 content가 `/title-b`에서 `/title-c`로 이동합니다.
- THEN `/title-a`의 목적지는 `/title-c`로 갱신되어야 합니다(SHALL).
- AND `/title-b` → `/title-c` redirect를 생성해야 합니다(SHALL).
- AND `/title-a` redirect의 기존 생성일과 만료일을 연장해서는 안 됩니다(SHALL NOT).
