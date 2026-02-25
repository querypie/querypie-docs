# docs/ 디렉토리

QueryPie 문서 사이트 프로젝트의 지식, 정보, 가이드 문서를 관리합니다.

## 문서 목록

### 프로젝트 가이드

| 문서 | 설명 |
|------|------|
| [DEVELOPMENT.md](DEVELOPMENT.md) | 기술 스택, 로컬 실행, 빌드, 배포 방법 |
| [commit-pr-guide.md](commit-pr-guide.md) | 커밋 메시지 및 PR 작성 컨벤션 |
| [translation.md](translation.md) | 다국어 번역 상세 지침 (ko, en, ja) |
| [ko-writing-style-guide.md](ko-writing-style-guide.md) | 한국어 문장 표현 및 교정/교열 가이드 |
| [api-naming-guide.md](api-naming-guide.md) | QueryPie ACP 제품명 및 API 명칭 지침 |

### 기술 문서

| 문서 | 설명 |
|------|------|
| [plan-to-migrate-openapi-spec.md](plan-to-migrate-openapi-spec.md) | OpenAPI Specification 자동 이관 계획 |

### 작업 결과

| 디렉토리 | 설명 |
|----------|------|
| [proofreading/](proofreading/) | 문서 교정/교열 결과 (`.claude/skills/proofread.md` Skill에서 사용) |

## Skills와의 관계

AI Agent용 Skill 문서는 `.claude/skills/`에 있으며, 상세 지침은 이 디렉토리의 문서를 참조합니다:

- `.claude/skills/translation.md` → `docs/translation.md`
- `.claude/skills/commit.md` → `docs/commit-pr-guide.md`
- `.claude/skills/mdx-skeleton-comparison.md` → `docs/translation.md`
- `.claude/skills/code-review.md` → `docs/DEVELOPMENT.md`
