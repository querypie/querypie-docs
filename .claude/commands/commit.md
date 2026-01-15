# Commit Log 작성 Skill

querypie-docs 저장소의 commit 관습에 맞게 commit message를 작성합니다.

## 작업 순서

1. `git branch --show-current`로 현재 브랜치 확인
2. **main 브랜치인 경우**: feature branch 생성 후 checkout
3. **main 브랜치가 아닌 경우**: 현재 브랜치에서 작업 계속
4. `git status`와 `git diff --staged`로 변경사항 확인
5. 변경사항이 없으면 사용자에게 알림
6. 변경사항을 분석하여 commit message 초안 작성
7. 사용자에게 확인 후 commit 실행

## 브랜치 관리

### 현재 브랜치 확인

```bash
git branch --show-current
```

### main 브랜치에서 작업 중인 경우

main 브랜치에서 직접 커밋하지 않습니다. feature branch를 생성하고 checkout합니다.

**브랜치 이름 형식:**
```
<username>/<type>-<간단한-설명>
```

**Username 목록:**
- `jk`
- `kelly`
- `dave`
- `jane`

username은 git config user.name 또는 user.email에서 유추합니다.

**Type 종류:**
- `feat-` : 새로운 기능
- `fix-` : 버그 수정
- `refactor-` : 리팩토링
- `chore-` : 기타 작업
- `docs-` : 문서 작업
- `mdx-` : MDX 문서 작업
- `open-api-` : OpenAPI/API Reference 작업

**브랜치 이름 규칙:**
- 영어 소문자와 하이픈(`-`)만 사용
- 간결하고 명확하게 작성 (2-4 단어)
- 공백 대신 하이픈 사용
- `/`는 username 구분에만 1회 사용

**예시:**
- `jk/mdx-update-korean-docs`
- `kelly/fix-build-error`
- `dave/open-api-add-endpoint`
- `jane/confluence-mdx-improve-converter`

**브랜치 생성 및 checkout:**
```bash
git checkout -b <username>/<type>-<간단한-설명>
```

### main 브랜치가 아닌 경우

현재 브랜치에서 그대로 작업을 진행합니다. 별도의 브랜치 생성이 필요하지 않습니다.

## Commit Message 형식

### Title (제목)

querypie-docs는 도메인 기반 prefix를 사용합니다:

```
<type>: <description>
```

또는 scope가 필요한 경우:

```
<type>(<scope>): <description>
```

**Type 종류 (우선순위 순):**
- `mdx`: MDX 문서 추가/수정/번역
- `open-api`: OpenAPI/API Reference 관련 작업
- `confluence-mdx`: Confluence 변환 도구 관련
- `mdx_to_skeleton`: 스켈레톤 변환 도구 관련
- `fix`: 버그 수정
- `refactor`: 코드 리팩토링 (기능 변경 없음)
- `chore`: 빌드, 패키지 등 기타 변경
- `ci`: CI/CD 설정 변경
- `tests`: 테스트 추가/수정

**제목 작성 규칙:**
- 한국어 사용 (영어도 가능)
- 50자 이내 권장
- 마침표 없이 작성
- 명령형으로 작성 (예: "추가", "수정", "개선", "구현")
- PR 번호는 작성하지 않음 (GitHub merge 시 자동 추가됨)

**예시:**
- `mdx: Confluence 한국어 문서 업데이트 (Community Edition 설치 가이드 개선)`
- `mdx: 12월 15일 이후 매뉴얼 업데이트를 일본어로 번역`
- `open-api: API Reference 동적 라우팅 페이지 구현`
- `open-api: Redoc title/description 커스터마이징 및 페이지 레이아웃 개선`
- `confluence-mdx: 테이블 변환 시 불필요한 속성 제거`
- `fix: robots.txt에 Disallow 규칙 추가하여 불필요한 크롤링 차단`
- `fix(ci): Confluence 워크플로우에서 첨부파일도 PR에 포함되도록 수정`
- `refactor: QueryPie 로고를 재사용 가능한 컴포넌트로 분리`
- `chore: 테스트용 sandbox 페이지를 추가`

### Description (본문)

querypie-docs는 **본문을 포함**하는 것이 관습입니다. 변경사항의 맥락과 세부 내용을 상세히 기술합니다.

**기본 형식:**

```markdown
## Description
- 변경 내용의 핵심 요약
- 세부 변경사항 나열
- 필요시 하위 항목으로 상세 설명
  - 세부 항목 1
  - 세부 항목 2

## Additional notes
- 추가 참고사항 (선택사항)
- 후속 작업 안내 등
```

**변경된 파일이 많은 경우:**

```markdown
## Description
- 변경 내용 요약

## Changes
- `path/to/file1.tsx`: 변경 내용 설명
- `path/to/file2.ts`: 변경 내용 설명

## Additional notes
- 추가 참고사항
```

**관련 이슈가 있는 경우:**

```markdown
## Description
- 변경 내용 설명

## Related tickets & links
- Closes #123

## Added/updated tests?
- [x] No, and this is why: 간단한 변경으로 로컬에서 검증 완료
```

**MDX 문서 업데이트의 경우:**

```markdown
## Description
- Confluence에서 최근 수정된 문서 변경사항을 MDX로 업데이트합니다 (한국어)
- 변경된 문서 내용 요약
  - 세부 변경 항목 1
  - 세부 변경 항목 2

### 영어/일본어 번역 추가
- 위 한국어 문서 변경사항에 대응하는 영어(en), 일본어(ja) 번역 수행
- Skeleton MDX 비교를 통해 원문과 번역문의 문서 구조 일치 검증 완료

## Additional notes
- 총 N개 파일 변경 (X줄 추가, Y줄 삭제)
```

**코드 변경의 경우:**

```markdown
## Description
변경 내용에 대한 간략한 설명을 작성합니다.

- 구현 세부사항 1
- 구현 세부사항 2
- 구현 세부사항 3

## Additional Notes
- 아직 개선이 필요한 부분이나 후속 작업 안내
```

**취약점 수정의 경우:**

```markdown
## 취약점
- CVE-XXXX-XXXXX 취약점 설명
- CVE-YYYY-YYYYY 취약점 설명

## 패치 방법
- npx npm-check-updates
- npx npm-check-updates --upgrade
- npm install
- npm audit
```

### 실제 commit 예시

**예시 1: MDX 문서 업데이트**
```
mdx: Confluence 한국어 문서 업데이트 (Community Edition 설치 가이드 개선)

## Description
- Confluence에서 최근 수정된 문서 변경사항을 MDX로 업데이트합니다 (한국어)
- Community Edition 설치 가이드 개선
    - 라이선스 안내 재배치 및 상세화
    - 초기 암호 변경 안내 추가
    - 설치 위치 및 수동 시작/중지 방법 추가
    - 스크린샷 업데이트
- LDAP Identity Providers 문서에 Active Directory 연동 시 Anonymous 설정 주의사항 추가

### 영어/일본어 번역 추가
- 위 한국어 문서 변경사항에 대응하는 영어(en), 일본어(ja) 번역 수행
- Skeleton MDX 비교를 통해 원문과 번역문의 문서 구조 일치 검증 완료

## Additional notes
- 한국어: 5개 파일 변경 (90줄 추가, 24줄 삭제)
- 영어/일본어: 10개 파일 변경 (192줄 추가, 60줄 삭제)
```

**예시 2: 기능 구현**
```
open-api: API Reference 동적 라우팅 페이지 구현

## Description
버전별 API Reference 페이지를 동적 라우팅으로 구현했습니다.
- `[lang]/api-reference/[acpVersion]/[apiVersion]` 경로로 버전별 API Reference 페이지 동적 생성
- OpenApiViewer 컴포넌트를 사용하여 OpenAPI 명세서 표시
- 다국어 지원 (en/ko/ja) 및 generateStaticParams로 정적 생성 지원
- logger 개선: production 환경에서 debug/info 로그 비활성화 및 createModuleLogger export 추가

## Additional notes
- 로고 이미지가 깨어지는 부분, 페이지 상단 설명 문구 영역을 개선하여야 합니다.
- 좌측 Sidebar, 우측 TOC 영역을 모두 사용하는 레이아웃이 적용되었습니다.
```

**예시 3: 버그 수정**
```
fix: robots.txt에 Disallow 규칙 추가하여 불필요한 크롤링 차단

## Description
- Google Search Console에서 보고된 404 오류 해결을 위해 robots.txt에 Disallow 규칙 추가
- `/_next/` 경로 차단: 빌드마다 해시가 변경되는 static 파일(CSS, JS) 크롤링 방지
- `/api/` 경로 차단: API Reference 동적 라우팅 경로 크롤링 방지

## Changes
- `src/app/robots.txt/route.ts`: 프로덕션 환경 robots.txt에 Disallow 규칙 추가

## Related tickets & links
- Closes #488

## Added/updated tests?
- [x] No, and this is why: robots.txt 동적 라우트의 단순 문자열 변경으로, 로컬 dev 서버에서 출력 검증 완료
```

**예시 4: 리팩토링**
```
refactor: QueryPie 로고를 재사용 가능한 컴포넌트로 분리

## Description
QueryPie 로고를 재사용 가능한 컴포넌트로 분리했습니다.
- `QueryPieLogo` 컴포넌트를 새로 생성하여 로고 UI를 재사용 가능하도록 개선
- `QUERYPIE_LOGO_HTML` 상수를 export하여 DOM 조작 시나리오(예: Redoc 로고 교체)에서도 사용 가능하도록 지원
- `layout.tsx`에서 인라인으로 작성된 로고 JSX를 `QueryPieLogo` 컴포넌트로 교체하여 코드 간소화

## Changes
- `src/components/querypie-logo.tsx`: QueryPieLogo 컴포넌트 및 QUERYPIE_LOGO_HTML 상수 추가
- `src/app/[lang]/layout.tsx`: 인라인 로고 JSX를 QueryPieLogo 컴포넌트로 교체
```

**예시 5: 도구 개선**
```
confluence-mdx: 테이블 변환 시 불필요한 속성 제거

## Description
- 테이블 변환 시 Confluence 전용 속성을 제거하도록 `get_html_attributes` 함수를 개선합니다.
- `local-id` 속성 제거 (Confluence 내부 식별자)
- `data-*` 속성 제거 (`data-table-width`, `data-layout`, `data-highlight-colour` 등)
- testcases 의 expected.mdx 를 업데이트합니다.
```

## 주의사항

- **본문은 필수입니다** - 단순한 변경이라도 `## Description` 섹션을 포함합니다
- PR merge 시 GitHub에서 `(#xxx)` 번호가 자동 추가됨
- Co-Authored-By 헤더는 자동으로 추가됨
- 문서 관련 작업은 `mdx:` prefix 사용
- API 관련 작업은 `open-api:` prefix 사용
- 도구 관련 작업은 해당 도구명을 prefix로 사용 (예: `confluence-mdx:`)
- 이미지 첨부가 필요한 경우 GitHub 이미지 링크 형식 사용 가능
