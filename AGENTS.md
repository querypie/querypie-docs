# 저장소 지침

이 파일은 Codex, Claude Code, Hermes Agent 같은 AI agent와 유사 도구를 위한 `querypie-docs` 작업 지침입니다.

## 공통 원칙

- 변경은 작고 집중되어 있으며 검토하기 쉽게 유지합니다.
- 문서, 구현, 테스트를 서로 일치하게 유지합니다.
- 정확성을 증명할 수 있는 가장 가벼운 명령으로 변경을 검증합니다.
- 모호한 부분이 있으면 요청을 충족하는 가장 작은 변경을 선택합니다.
- 관련 없는 편집이나 기회주의적 리팩터링을 하지 않습니다.
- repository Markdown 문서, repository guidance, skill 문서, PR title, PR description은 사용자가 다른 언어를 명시하지 않는 한 한국어로 작성합니다.
- 내부 Markdown 본문은 한국어로 작성합니다. 파일명, code identifier, frontmatter key, route path, API name, UI label, 외부 source title은 canonical language를 유지합니다.
- `src/content/en/**`, `src/content/ja/**` 같은 localized public content는 target locale을 따릅니다. 이 한국어 원칙은 내부 repository 문서, spec, plan, agent skill에 적용합니다.

## 프로젝트 컨텍스트

- QueryPie 제품 문서 사이트입니다.
- 다국어 지원 언어는 한국어(`ko`), 영어(`en`), 일본어(`ja`)입니다.
- 기술 스택은 Next.js 16, Nextra 4, React 19, TypeScript 5입니다.
- 주요 콘텐츠는 `src/content/{ko,en,ja}/` 아래 MDX입니다.
- Confluence 변환 도구는 `confluence-mdx/` 아래에 있습니다.
- 공용 이미지는 `public/` 아래에 있습니다.
- repository 문서는 `docs/` 아래에 있습니다.

## 커밋 및 PR 컨벤션

상세 가이드: `docs/commit-pr-guide.md`

핵심 규칙:

- `src/content` 아래 MDX 문서 변경 시 `mdx:` prefix를 사용합니다.
- `confluence-mdx/` 변환기 관련 변경 시 `confluence-mdx:` prefix를 사용합니다.
- 그 외 변경은 `feat`, `fix`, `refactor`, `ci`, `chore` 등 conventional commit type을 사용합니다.
- 제목과 본문은 한국어, 경어체(~합니다), 능동태로 작성합니다.
- Claude Code가 직접 커밋을 생성하는 경우 repository의 최신 PR/commit skill 지침을 우선 확인합니다.

## 콘텐츠 위치

- 소스 콘텐츠: `src/content/{lang}/` (ko, en, ja)입니다. 이 경로를 단일 진실 공급원(Source of Truth)으로 취급합니다.
- Confluence 변환 도구: `confluence-mdx/`
- 공용 이미지: `public/`
- 프로젝트 문서: `docs/`
  - `docs/content-structure.md` — repo 구조, symbolic link, Skeleton 비교 경로 규칙
  - `docs/DEVELOPMENT.md` — 기술 스택, 로컬 실행, 배포
  - `docs/commit-pr-guide.md` — 커밋/PR 컨벤션 상세 가이드
  - `docs/translation.md` — 다국어 번역 상세 지침
  - `docs/api-naming-guide.md` — QueryPie ACP 제품명/API 명칭 지침

## Symbolic Link 및 Skeleton 비교 경로

`confluence-mdx/target/{ko,en,ja}/`는 `src/content/{ko,en,ja}/`의 symbolic link입니다.
두 경로는 동일한 파일을 가리킵니다.

Skeleton MDX 비교 시 반드시 `target/{lang}/` 경로를 사용합니다.

```bash
# 올바른 사용
bin/skeleton/cli.py target/ko/path/to/file.mdx

# 작동하지 않음
bin/skeleton/cli.py ../src/content/ko/path/to/file.mdx
```

상세 내용: `docs/content-structure.md`

## Skill 발견

이 repository의 checked-in agent skill은 `.agents/skills/<skill-name>/SKILL.md` 형식으로 둡니다.
호환성을 위해 `.claude`는 `.agents`를 가리키는 symbolic link로 유지합니다.

작업을 시작할 때:

1. `.agents/skills/README.md`에서 사용 가능한 skill을 확인합니다.
2. 작업과 명확히 맞는 가장 좁은 skill 문서만 읽습니다.
3. skill 문서가 참조하는 repository 문서가 있으면 필요한 파일만 추가로 읽습니다.
4. 여러 skill이 일치하면 최소한의 set만 사용하고 실행 순서를 짧게 밝힙니다.
5. 다시 trigger되지 않는 한 skill activation을 turn 사이에 이어가지 않습니다.

## OpenSpec 작업 규칙

- OpenSpec spec 또는 change 문서를 새로 작성하거나 크게 갱신하는 작업이면 `.agents/skills/openspec-authoring/SKILL.md`를 먼저 읽습니다.
- 구현, 리뷰, 계획, 디버깅 중 OpenSpec drift, 모순, 누락된 Requirement, stale Scenario, 또는 `openspec/`에 기록해야 할 durable contract를 발견하면 `.agents/skills/openspec-doc-maintenance/SKILL.md`를 먼저 읽습니다.
- OpenSpec `tasks.md`에 남은 task, 후속 구현, verification 보강, PR-sized execution을 수행하라는 요청이면 `.agents/skills/openspec-task-execution/SKILL.md`를 먼저 읽습니다.
- OpenSpec은 durable implementation contract layer로 취급합니다. 기존 contract 구현이 아니라 requirement 또는 spec을 바꾸는 작업이면 production code를 변경하기 전에 OpenSpec을 먼저 갱신하고 follow-up implementation task를 기록합니다.
- OpenSpec 문서 본문은 한국어로 작성합니다. spec id, file name, `Requirement`와 `Scenario` 같은 heading, code identifier, route path, API name, frontmatter key, modality token은 canonical language를 유지합니다.

## 검증

- 작업 완료로 간주하기 전에 관련 targeted check를 실행합니다.
- 문서 또는 skill만 변경한 경우 `git diff --check`와 관련 경로 검색을 우선합니다.
- 코드 변경은 변경된 동작에 직접 연결되는 테스트를 먼저 실행하고, 위험도에 따라 lint, typecheck, build를 추가합니다.
- 웹 렌더링 또는 브라우저 테스트는 사용자가 visible browser를 명시적으로 요청하지 않는 한 headless mode로 수행합니다.
- 사용자가 명시적으로 요청하지 않는 한 local dev server를 시작하지 않습니다.
