# QueryPie 문서 저장소용 Claude Skills

이 디렉토리는 QueryPie 문서 저장소에서 다양한 작업을 수행하는 데 도움이 되는 Claude skills을 포함합니다.

## 사용 가능한 Skills

### 문서 작성 Skills
- **documentation.md** - MDX 문서 파일 작성 및 편집 가이드라인
- **translation.md** - 다국어 번역 가이드라인 (ko → en, ja)
- **confluence-mdx.md** - Confluence에서 MDX로 변환 워크플로우
- **confluence-pr-update.md** - Confluence MDX PR 수정 워크플로우
- **sync-ko-to-en-ja.md** - 한국어 MDX 변경사항을 영어/일본어에 동기화
- **mdx-skeleton-comparison.md** - 스켈레톤 비교를 통한 번역 일관성 검증

### 개발 Skills
- **code-review.md** - 코드 변경 사항 검토 가이드라인

## Skills과 참조 문서 관계

각 skill은 핵심 원칙과 빠른 시작 가이드를 제공하며, 상세 내용은 프로젝트의 다른 문서를 참조합니다:

| Skill | 참조 문서 |
|-------|----------|
| translation.md | [docs/translation.md](/docs/translation.md) |
| confluence-mdx.md | [confluence-mdx/README.md](/confluence-mdx/README.md) |
| confluence-pr-update.md | confluence-mdx.md, translation.md, mdx-skeleton-comparison.md |
| sync-ko-to-en-ja.md | [docs/translation.md](/docs/translation.md) |
| mdx-skeleton-comparison.md | [docs/translation.md](/docs/translation.md) |
| documentation.md | [docs/DEVELOPMENT.md](/docs/DEVELOPMENT.md) |
| commit.md (commands) | [docs/commit-pr-guide.md](/docs/commit-pr-guide.md) (Commit 및 PR 작성) |

## 사용법

이 skills는 이 저장소에서 작업할 때 Claude에서 자동으로 사용할 수 있습니다. 다음 작업에 대한 상황별 가이드를 제공합니다:

- MDX 문서 작성 및 유지 관리
- 다국어 콘텐츠 번역
- Confluence 변환 스크립트 작업
- 원문과 번역본 MDX 파일 간의 불일치 감지
- 코드 변경 사항 검토

## 프로젝트 구조

이 저장소는 다음을 사용합니다:
- **Next.js 15** + **Nextra 4** - 문서 사이트
- **TypeScript 5** - 타입 안전성
- **React 19** - UI 컴포넌트
- **MDX** - 콘텐츠 파일 형식
- 다국어 지원: 영어 (en), 일본어 (ja), 한국어 (ko)

## 콘텐츠 위치

- 소스 콘텐츠: `src/content/{lang}/`
- Confluence 변환 스크립트: `confluence-mdx/bin/`
- 공용 자산: `public/`
- 프로젝트 문서: `docs/`

