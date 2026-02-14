# CLAUDE.md

## 프로젝트 개요

QueryPie 제품 문서 사이트 (Next.js 16 + Nextra 4 + MDX)
다국어 지원: 한국어(ko), 영어(en), 일본어(ja)

## Skills

이 프로젝트의 Claude Skills는 `.claude/skills/` 디렉토리에 있습니다.
목록은 `.claude/skills/README.md`를 참조하세요.

## 커밋 및 PR 컨벤션

상세 가이드: `docs/commit-pr-guide.md`

### 핵심 규칙

- `src/content` 아래 MDX 문서 변경 시 `mdx:` prefix를 사용합니다.
- `confluence-mdx/` 변환기 관련 변경 시 `confluence-mdx:` prefix를 사용합니다.
- 그 외 변경은 `feat`, `fix`, `refactor`, `ci`, `chore` 등 conventional commit type을 사용합니다.
- 제목과 본문은 한국어, 경어체(~합니다), 능동태로 작성합니다.
- Claude 사용 시 `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`를 포함합니다.

## 콘텐츠 위치

- 소스 콘텐츠: `src/content/{lang}/` (ko, en, ja)
- Confluence 변환 도구: `confluence-mdx/`
- 공용 이미지: `public/`
- 프로젝트 문서: `docs/`
  - `docs/DEVELOPMENT.md` — 기술 스택, 로컬 실행, 배포
  - `docs/commit-pr-guide.md` — 커밋/PR 컨벤션 상세 가이드
  - `docs/translation.md` — 다국어 번역 상세 지침
  - `docs/api-naming-guide.md` — QueryPie ACP 제품명/API 명칭 지침
