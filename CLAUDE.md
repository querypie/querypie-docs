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

- 소스 콘텐츠: `src/content/{lang}/` (ko, en, ja) ← **단일 진실 공급원 (Source of Truth)**
- Confluence 변환 도구: `confluence-mdx/`
- 공용 이미지: `public/`
- 프로젝트 문서: `docs/`
  - `docs/content-structure.md` — **repo 구조, 심볼릭 링크, Skeleton 비교 경로 규칙** (필독)
  - `docs/DEVELOPMENT.md` — 기술 스택, 로컬 실행, 배포
  - `docs/commit-pr-guide.md` — 커밋/PR 컨벤션 상세 가이드
  - `docs/translation.md` — 다국어 번역 상세 지침
  - `docs/api-naming-guide.md` — QueryPie ACP 제품명/API 명칭 지침

## 심볼릭 링크 및 Skeleton 비교 경로

`confluence-mdx/target/{ko,en,ja}/`는 `src/content/{ko,en,ja}/`의 **심볼릭 링크**입니다.
두 경로는 동일한 파일을 가리킵니다.

Skeleton MDX 비교 시 반드시 `target/{lang}/` 경로를 사용하세요:
```bash
# ✅ 올바른 사용
python3 bin/skeleton/cli.py target/ko/path/to/file.mdx

# ❌ 작동하지 않음
python3 bin/skeleton/cli.py ../src/content/ko/path/to/file.mdx
```

상세 내용: `docs/content-structure.md`
