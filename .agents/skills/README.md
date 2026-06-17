# QueryPie 문서 저장소용 Agent Skills

이 디렉토리는 QueryPie 문서 저장소에서 다양한 작업을 수행하는 데 도움이 되는 Agent skills를 포함합니다.

표준 layout:

```text
.agents/skills/<skill-name>/SKILL.md
```

## 사용 가능한 Skills

### 번역/교정 Skills
- **translation** - 다국어 번역 가이드라인 (ko → en, ja)
- **proofread** - 문서 교정/교열 가이드
- **sync-ko-to-en-ja** - 한국어 MDX 변경사항을 영어/일본어에 동기화
- **mdx-skeleton-comparison** - 스켈레톤 비교를 통한 번역 일관성 검증

### Confluence 워크플로우 Skills
- **confluence-mdx** - Confluence에서 MDX로 변환 워크플로우
- **confluence-pr-update** - Confluence MDX PR 수정 워크플로우
- **confluence-mdx-testcase** - XHTML 변환 테스트케이스 추가 가이드

### Reverse Sync / XHTML Skills
- **reverse-sync** - Reverse Sync (MDX → Confluence XHTML 역반영) 사용 가이드
- **reverse-sync-debugging** - Reverse Sync 디버깅 워크플로우 (verify 실패 원인 분석 및 수정)
- **xhtml-beautify-diff** - XHTML Beautify-Diff Viewer 사용 가이드

### 유틸리티 Skills
- **sync-confluence-url** - ko→en/ja confluenceUrl frontmatter 동기화

### 프로세스 Skills
- **commit** - Commit 및 PR 작성 가이드
- **code-review** - 코드 변경 사항 검토 가이드라인

### OpenSpec Skills
- **openspec-authoring** - OpenSpec spec, proposal, design, task 문서 작성
- **openspec-doc-maintenance** - OpenSpec drift, 모순, stale scenario, contract 유지보수
- **openspec-task-execution** - OpenSpec `tasks.md`의 남은 구현, 검증, PR-sized 후속 작업 수행

## Skills과 참조 문서 관계

각 skill은 핵심 원칙과 빠른 시작 가이드를 제공하며, 상세 내용은 프로젝트의 다른 문서를 참조합니다:

| Skill | 참조 문서 |
|-------|----------|
| translation | [docs/translation.md](/docs/translation.md), [docs/api-naming-guide.md](/docs/api-naming-guide.md) |
| confluence-mdx | [confluence-mdx/README.md](/confluence-mdx/README.md) |
| confluence-pr-update | confluence-mdx, translation, mdx-skeleton-comparison |
| confluence-mdx-testcase | [confluence-mdx/README.md](/confluence-mdx/README.md) |
| sync-ko-to-en-ja | [docs/translation.md](/docs/translation.md) |
| mdx-skeleton-comparison | [docs/translation.md](/docs/translation.md) |
| reverse-sync | [confluence-mdx/bin/reverse_sync_cli.py](/confluence-mdx/bin/reverse_sync_cli.py) |
| reverse-sync-debugging | reverse-sync, [confluence-mdx/bin/reverse_sync_cli.py](/confluence-mdx/bin/reverse_sync_cli.py) |
| sync-confluence-url | [confluence-mdx/bin/sync_confluence_url.py](/confluence-mdx/bin/sync_confluence_url.py) |
| xhtml-beautify-diff | [confluence-mdx/bin/xhtml_beautify_diff.py](/confluence-mdx/bin/xhtml_beautify_diff.py) |
| commit | [docs/commit-pr-guide.md](/docs/commit-pr-guide.md) (Commit 및 PR 작성) |
| proofread | [docs/api-naming-guide.md](/docs/api-naming-guide.md) |
| openspec-authoring | [AGENTS.md](/AGENTS.md), `openspec/README.md` (OpenSpec 도입 후) |
| openspec-doc-maintenance | [AGENTS.md](/AGENTS.md), `openspec/project.md` (OpenSpec 도입 후) |
| openspec-task-execution | [AGENTS.md](/AGENTS.md), `openspec/changes/**/tasks.md` |

## 사용법

이 skills는 이 저장소에서 작업할 때 agent가 사용할 수 있습니다. 다음 작업에 대한 상황별 가이드를 제공합니다:

- MDX 문서 작성 및 유지 관리
- 다국어 콘텐츠 번역
- Confluence 변환 스크립트 작업
- 원문과 번역본 MDX 파일 간의 불일치 감지
- OpenSpec 기반 요구사항, 구현 계약, 후속 task 관리
- 코드 변경 사항 검토

## 프로젝트 구조

이 저장소는 다음을 사용합니다:
- **Next.js 16** + **Nextra 4** - 문서 사이트
- **TypeScript 5** - 타입 안전성
- **React 19** - UI 컴포넌트
- **MDX** - 콘텐츠 파일 형식
- 다국어 지원: 영어 (en), 일본어 (ja), 한국어 (ko)

## 콘텐츠 위치

- 소스 콘텐츠: `src/content/{lang}/`
- Confluence 변환 스크립트: `confluence-mdx/bin/`
- 공용 자산: `public/`
- 프로젝트 문서: `docs/`
