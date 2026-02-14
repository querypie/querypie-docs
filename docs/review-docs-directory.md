# docs/ 디렉토리 검토 결과

**검토일시**: 2026-02-14
**검토 수행**: Claude Opus 4.6

## 검토 목적

1. `docs/` 아래 문서의 유효성 점검
2. `.claude/skills/` 문서와의 중복 식별
3. 정리 방안 제시 (삭제, 유지, Skill 취합)

---

## 1. docs/ 파일 전체 목록 및 판정

### 문서 파일

| 파일 | 설명 | 판정 | 사유 |
|------|------|------|------|
| `README.md` | docs/ 디렉토리 설명 | **삭제** | 내용이 빈약하고 outdated (prompt-1-ko.md만 설명, venv 언급) |
| `DEVELOPMENT.md` | 기술 스택, 로컬 실행, 배포 방법 | **유지** | 프로젝트 기본 정보. code-review.md skill에서 참조 |
| `commit-pr-guide.md` | 커밋/PR 컨벤션 상세 가이드 | **유지** | commit.md skill에서 참조하는 상세 문서 |
| `translation.md` | 번역 상세 지침 | **유지** | translation.md, mdx-skeleton-comparison.md skill에서 참조하는 상세 문서 |
| `api-naming-guide.md` | QueryPie ACP 제품명/API 명칭 지침 | **유지** | 프로젝트 지식 문서. Skill에서 참조하지 않지만, 번역/문서 작성 시 참조 필요 |
| `vercel-logging.md` | Vercel Pino 로거 설정 가이드 | **유지** | 기술 문서. 현재 코드 구현에 대한 설명 |
| `plan-to-migrate-openapi-spec.md` | OpenAPI Spec 자동 이관 계획 | **유지** | Phase 1 완료, Phase 2~3 진행 중인 계획 문서 |
| `prompt-1-ko.md` | 초기 Confluence → MDX 변환 프롬프트 | **삭제** | confluence-mdx 자동화 도구로 완전히 대체됨. 히스토리 가치만 있음 |
| `translation-11-3.42e20714.md` | 커밋 42e20714 번역 작업 추적 | **삭제** | 일회성 작업 문서. 체크리스트 미완료이나, 이 방식으로 추적하지 않음 |

### 임시/참조 파일

| 파일 | 설명 | 판정 | 사유 |
|------|------|------|------|
| `compare.txt` | 번역 상태 비교 목록 | **삭제** | 일회성 임시 파일 |
| `diff.en.txt` | 영어 skeleton 비교 결과 | **삭제** | 일회성 임시 파일 |
| `diff.ja.txt` | 일본어 skeleton 비교 결과 | **삭제** | 일회성 임시 파일 |

### 이미지 파일

| 파일 | 설명 | 판정 | 사유 |
|------|------|------|------|
| `deploy-action.png` | 배포 액션 스크린샷 | **유지** | DEVELOPMENT.md에서 참조 |
| `preview-deploy-url.png` | 프리뷰 배포 URL 스크린샷 | **유지** | DEVELOPMENT.md에서 참조 |

### 디렉토리

| 디렉토리 | 설명 | 판정 | 사유 |
|----------|------|------|------|
| `changes-since-250925/` | 2025-09-25 이후 변경사항 diff (59개 파일) | **삭제** | git 명령으로 언제든 재생성 가능. 대량의 일회성 데이터 |
| `latest-ko-confluence/` | .gitignore만 있는 빈 디렉토리 | **삭제** | 목적 불분명. Confluence 데이터 작업 시 임시로 사용한 것으로 추정 |
| `proofreading/` | 교정/교열 결과 저장소 | **유지** | proofread.md skill에서 정의한 결과 저장 위치 |

---

## 2. .claude/skills/ 와의 중복 분석

### 참조 관계 (중복이 아닌 적절한 구조)

현재 Skill 문서들은 docs/ 문서를 참조하는 2계층 구조를 취하고 있습니다:
- **Skill (요약/절차)** → **docs/ (상세 지식/정보)**

| Skill | 참조하는 docs/ 문서 | 관계 |
|-------|---------------------|------|
| `skills/translation.md` | `docs/translation.md` | Skill이 요약, docs가 상세 지침 |
| `skills/commit.md` | `docs/commit-pr-guide.md` | Skill이 요약, docs가 상세 가이드 |
| `skills/mdx-skeleton-comparison.md` | `docs/translation.md` "Skeleton MDX" 섹션 | Skill이 CLI 사용법, docs가 개념 설명 |
| `skills/code-review.md` | `docs/DEVELOPMENT.md` | Skill이 리뷰 기준, docs가 개발 가이드 |
| `skills/proofread.md` | `skills/translation.md` 참조 (간접적으로 `docs/translation.md`) | 적절 |

### 실질적 중복 (대체 관계)

| docs/ 문서 | Skill | 관계 |
|------------|-------|------|
| `prompt-1-ko.md` | `skills/confluence-mdx.md` | prompt-1-ko.md가 **완전히 대체됨** |

### Skill로 취합하는 것이 나은 경우

현재 구조에서 Skill로 취합이 필요한 문서는 **없습니다**. 이유:

- docs/ 문서: 프로젝트 지식, 정보, 상세 설명 (사람도 읽는 문서)
- Skill 문서: AI Agent가 따라야 할 절차, 빠른 참조 가이드

이 구분이 명확하게 유지되고 있으며, Skill 문서가 docs 문서를 참조하는 현재 구조가 적절합니다.

---

## 3. 정리 권고 요약

### 삭제 대상 (10개 파일 + 2개 디렉토리)

```
docs/README.md                      # outdated 디렉토리 설명
docs/prompt-1-ko.md                 # confluence-mdx 도구로 대체됨
docs/translation-11-3.42e20714.md   # 일회성 작업 추적 문서
docs/compare.txt                    # 임시 파일
docs/diff.en.txt                    # 임시 파일
docs/diff.ja.txt                    # 임시 파일
docs/changes-since-250925/          # 59개 파일, git으로 재생성 가능
docs/latest-ko-confluence/          # 빈 디렉토리
```

### 유지 대상 (7개 파일 + 1개 디렉토리)

```
docs/DEVELOPMENT.md                 # 프로젝트 기본 정보
docs/commit-pr-guide.md             # 커밋/PR 컨벤션 (skill에서 참조)
docs/translation.md                 # 번역 상세 지침 (skill에서 참조)
docs/api-naming-guide.md            # 제품명/API 명칭 지침
docs/vercel-logging.md              # Vercel 로깅 기술 문서
docs/plan-to-migrate-openapi-spec.md # OpenAPI 이관 계획
docs/deploy-action.png              # DEVELOPMENT.md 참조 이미지
docs/preview-deploy-url.png         # DEVELOPMENT.md 참조 이미지
docs/proofreading/                  # 교정/교열 결과 (skill에서 사용)
```

---

## 4. 정리 후 docs/ 구조 (예상)

```
docs/
  DEVELOPMENT.md                      # 기술 스택, 로컬 실행, 배포
  commit-pr-guide.md                  # 커밋/PR 컨벤션 상세 가이드
  translation.md                      # 번역 상세 지침
  api-naming-guide.md                 # 제품명/API 명칭 지침
  vercel-logging.md                   # Vercel 로깅 설정 가이드
  plan-to-migrate-openapi-spec.md     # OpenAPI Spec 이관 계획
  deploy-action.png                   # 배포 스크린샷
  preview-deploy-url.png              # 프리뷰 배포 스크린샷
  proofreading/                       # 교정/교열 결과
    ko/...
```

---

## 5. 추가 개선 제안

1. **docs/README.md 재작성**: 삭제 대신, 정리 후 남은 문서들의 목록과 역할을 설명하는 새 README.md를 작성하는 것도 고려할 수 있습니다.

2. **api-naming-guide.md의 Skill 연동**: 현재 어떤 Skill에서도 참조하지 않으므로, `skills/translation.md`나 `skills/proofread.md`에서 참조를 추가하면 AI Agent가 번역/교정 시 명칭 지침을 자연스럽게 따를 수 있습니다.

3. **CLAUDE.md 업데이트**: 정리 후 `CLAUDE.md`의 "프로젝트 문서: `docs/`" 설명을 구체화하면, AI Agent가 docs/ 문서를 더 잘 활용할 수 있습니다.
