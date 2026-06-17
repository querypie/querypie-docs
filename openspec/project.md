# querypie-docs OpenSpec 프로젝트 Context

OpenSpec은 future PR이 따라야 하는 durable implementation contract를 기록합니다.
기존 `docs/**` 문서는 운영 가이드, 배경, 예시, 개발 절차를 설명하고, OpenSpec은 구현과 검증이 보존해야 하는 계약을 설명합니다.

## Repository 역할

`querypie-docs`는 QueryPie 제품 문서를 관리하고 배포하는 repository입니다.
주요 surface는 다음과 같습니다.

- Public documentation site: Next.js, Nextra, React, TypeScript 기반 문서 사이트
- Product content: `src/content/{ko,en,ja}/` 아래 MDX 문서
- Confluence import/conversion: `confluence-mdx/` 아래 Python 기반 변환 도구
- Reverse sync: MDX 교정 결과를 Confluence XHTML로 되돌리는 도구와 테스트
- API reference rendering: 저장된 specification JSON을 문서 사이트에서 렌더링하는 UI
- Search index: build-time 문서 검색 인덱스와 `/mcp` endpoint가 사용하는 generated artifact
- Deployment workflow: GitHub Actions와 Vercel preview/production deployment

## Source of Truth

- Public product documentation의 source of truth는 `src/content/{ko,en,ja}/`입니다.
- `confluence-mdx/target/{ko,en,ja}/`는 `src/content/{ko,en,ja}/`를 가리키는 symlink로 취급합니다.
- Confluence 변환 입력과 intermediate artifact는 `confluence-mdx/var/**`와 관련 tool 문서가 설명합니다.
- Agent skill과 내부 repository 지침은 `.agents/skills/**`, `AGENTS.md`, `CLAUDE.md`, `docs/**`에 둡니다.
- OpenSpec으로 승격된 durable contract는 `openspec/specs/**/spec.md`를 우선합니다.

## Language 정책

- OpenSpec 본문, internal repository guidance, skill 문서는 한국어로 작성합니다.
- `src/content/en/**`와 `src/content/ja/**` 같은 localized public content는 target locale을 따릅니다.
- 파일명, route path, API name, UI label, frontmatter key, code identifier, 외부 고유명사는 canonical language를 유지합니다.

## Contract 우선순위

동일한 behavior에 대해 문서가 충돌하면 다음 순서로 해석합니다.

1. 사용자 또는 reviewer가 현재 PR에서 명시한 최신 요구사항
2. `AGENTS.md`와 관련 repo-local skill
3. `openspec/specs/**/spec.md` accepted spec
4. active `openspec/changes/**` proposal, design, tasks
5. `docs/**`, `README.md`, `CLAUDE.md`
6. 현재 구현

현재 구현이 accepted spec과 다르면 구현을 source of truth로 단정하지 않습니다.
먼저 drift인지, 의도된 contract change인지, stale spec인지 분류합니다.

## OpenSpec 대상

다음 변경은 OpenSpec 작성 또는 갱신 후보입니다.

- public route, navigation, sitemap, canonical, redirect behavior 변경
- content source path, locale sync, skeleton comparison, translation consistency 계약 변경
- Confluence import, MDX conversion, attachment path, reverse sync, XHTML patching behavior 변경
- API reference rendering, stored specification loading, version routing 계약 변경
- search index, MCP endpoint, generated artifact lifecycle 변경
- deployment, preview, validation, CI check contract 변경
- agent workflow, repository skill, durable authoring contract 변경

다음 변경은 일반적으로 OpenSpec 대상이 아닙니다.

- 단순 오탈자 수정
- 기존 계약을 바꾸지 않는 localized copy 갱신
- 일회성 조사 메모
- 기존 accepted spec 또는 docs에 이미 명확히 정의된 작업의 단순 실행

## PR 분리 원칙

- OpenSpec-only 변경과 production implementation 변경은 가능하면 별도 PR로 분리합니다.
- 같은 feature의 requirement와 implementation을 모두 바꿔야 하면 OpenSpec PR을 먼저 만들고, implementation PR은 OpenSpec PR branch를 base로 둔 stacked PR로 만듭니다.
- unrelated OpenSpec drift는 현재 feature PR에 섞지 않습니다.
- OpenSpec PR body에는 기준 spec/change path, 구현 PR과 분리한 이유, 후속 task, 검증 방식을 적습니다.

## Initial Spec 후보

아래 항목은 필요할 때 accepted spec으로 승격할 수 있는 후보입니다.

- `contract-content-source-of-truth`: `src/content/{ko,en,ja}`와 `confluence-mdx/target/**` symlink 계약
- `contract-locale-sync`: 한국어 원문 변경과 영어/일본어 동기화, skeleton comparison 계약
- `contract-confluence-mdx-conversion`: Confluence XHTML에서 MDX로 변환하는 path, attachment, metadata 계약
- `contract-reverse-sync`: MDX 교정 결과를 Confluence XHTML로 반영하는 안전장치와 patching 계약
- `platform-docs-site-routing`: Nextra/Next.js route, metadata, sitemap, canonical 계약
- `contract-api-reference-rendering`: stored API specification JSON loading 및 renderer 계약
- `contract-agent-skill-authoring`: `.agents/skills` skill 작성과 trigger 계약
