## Why

Confluence 문서 제목이 바뀌어도 content ID 기반 slug override로 기존 public route를 유지하면 제목 변경이 route에 반영되지 않습니다. 문서 제목을 canonical route의 기준으로 일관되게 사용하면서도, 이전 링크가 즉시 404로 바뀌지 않도록 제한된 기간의 redirect가 필요합니다.

## What Changes

- Confluence content의 canonical route는 현재 영어 제목 번역을 slugify한 경로를 사용합니다.
- 기존 route를 보존하는 content ID 기반 slug override를 제거합니다.
- conversion manifest에서 같은 content ID의 이전·현재 MDX 경로를 비교해 route 변경을 자동 감지합니다.
- 변경된 이전 route에는 생성일과 만료일을 가진 8주 임시 redirect를 생성합니다.
- 만료된 redirect는 runtime route 설정에서 제외하고, 다음 conversion에서 registry에서도 제거합니다.
- 같은 content가 연속해서 이름을 바꾸면 기존 redirect의 목적지를 최신 route로 갱신해 redirect chain을 방지합니다.

## Capabilities

### New Capabilities

- `platform-docs-site-routing`: 제목 변경에 따른 canonical route 이동과 기간 제한 redirect lifecycle을 관리합니다.

### Modified Capabilities

- Confluence MDX conversion은 stable slug override 대신 현재 제목 번역에서 output path를 계산합니다.
- conversion manifest finalization은 content route 이동을 redirect registry에 반영합니다.

## Impact

- `confluence-mdx/bin/fetch/**`: title translation 기반 path 생성 계약을 단순화합니다.
- `confluence-mdx/bin/convert_all.py`: manifest path 변경 감지와 redirect lifecycle 갱신을 추가합니다.
- `src/content-route-redirects.yaml`: content route redirect의 source of truth가 됩니다.
- `next.config.ts`: 유효 기간 안의 content route redirect를 locale별 runtime rule로 확장합니다.
- 기존 `web-client` route와 운영 로그 수집 가이드 route를 새 제목 기반 route로 이동합니다.
