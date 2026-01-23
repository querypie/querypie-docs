# Commit 및 PR 작성 가이드

이 문서는 querypie-docs 프로젝트의 커밋 로그 및 PR 작성 관습을 정의합니다.

## 제목 형식

### 기본 형식

```
<type>(<scope>): <한국어 설명>
```

또는 도메인 기반 prefix를 사용합니다:

```
<prefix>: <한국어 설명>
```

### Type 종류

| Type | 설명 | 예시 |
|------|------|------|
| `feat` | 새로운 기능 추가 | `feat(tests): Playwright 기반 이미지 렌더링 측정 도구 추가` |
| `refactor` | 코드 리팩토링 | `refactor: QueryPie 로고를 재사용 가능한 컴포넌트로 분리` |
| `fix` | 버그 수정 | `fix(src/lib): useLocale에서 pathname null 체크 추가` |
| `ci` | CI/CD 관련 변경 | `ci(.github/workflows): fetch-openapi-spec 워크플로우 변경` |
| `chore` | 기타 변경 (빌드, 패키지 등) | `chore: 보안 취약점 패치 및 의존성 업데이트` |

### 도메인 기반 Prefix

프로젝트 특성상 도메인 기반 prefix를 사용할 수 있습니다:

| Prefix | 설명 | 예시                                             |
|--------|------|------------------------------------------------|
| `mdx:` | MDX 문서 변경 | `mdx: installation 문서 정리 및 support 분리`         |
| `open-api:` | API Reference 관련 | `open-api: API Reference 동적 라우팅 페이지 구현`        |
| `confluence-mdx:` | Confluence 변환기 관련 | `confluence-mdx: 테이블 변환 시 불필요한 속성 제거`          |
| `skill:` | Claude Skills 관련 | `skill: Claude Skills 한국어 번역 및 docs 참조로 중복 제거` |
| `docs` | 문서 변경 | `docs: 번역 가이드를 재작성`                            |

### Scope 예시

| Scope | 설명 |
|-------|------|
| `src/content` | 소스 콘텐츠 |
| `src/lib`, `src/components` | 라이브러리, 컴포넌트 |
| `.github/workflows` | CI/CD 워크플로우 |
| `confluence-mdx` | Confluence 변환 도구 |
| `tests` | 테스트 |
| `deps` | 의존성 |

## 본문 형식

### 기본 구조

```markdown
## Summary
PR을 작성하게 된 배경, 이유, 목적을 한 문장으로 기술합니다.

- 변경사항을 bullet point로 설명합니다.
- 추가 변경사항을 기술합니다.

## Test plan
- [ ] 테스트 항목 1
- [ ] 테스트 항목 2

## Related tickets & links
- #123
- Closes #456

## Additional notes
- 추가 참고사항을 기술합니다.
```

### 섹션별 설명

| 섹션 | 필수 | 설명 |
|------|------|------|
| `## Summary` 또는 `## Description` | 권장 | 배경/이유/목적 한 문장 + 변경사항 요약 |
| `## Test plan` | 권장 | 테스트 방법 체크리스트 |
| `## Related tickets & links` | 선택 | 관련 이슈/티켓 |
| `## Additional notes` | 선택 | 추가 참고사항 |

## 작성 지침

### 언어 및 톤

1. **한국어로 작성합니다.**
2. **경어체(~합니다)를 사용합니다.**
3. **능동태를 사용하여 주체가 명확한 문장을 작성합니다.**
   - 좋은 예: "캐시 로직을 개선합니다."
   - 피할 예: "캐시 로직이 개선되었습니다."

### 기술 용어

1. **기술 용어는 원어 그대로 사용하되, 동사는 한국어로 작성합니다.**
   - 좋은 예: "buildx를 설치합니다."
   - 피할 예: "buildx install을 수행합니다."

### 간결성

1. **제목은 50자 이내로 간결하게 작성합니다.**
2. **한 문장에 하나의 변경사항만 기술하여 가독성을 높입니다.**
3. **불필요한 수식어나 부연 설명은 생략하고 핵심만 전달합니다.**
   - 좋은 예: "ARM64 빌드 지원을 추가합니다."
   - 피할 예: "더 나은 호환성을 위해 ARM64 아키텍처에 대한 빌드 지원 기능을 새롭게 추가합니다."

### Claude 사용 시

Claude Code를 사용하여 작업한 경우 다음을 포함합니다:

```markdown
🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

## 예시

### feat 예시

```
feat(tests): Playwright 기반 이미지 렌더링 측정 도구 추가 (#530)

## Summary
- Playwright를 사용한 이미지 렌더링 크기 측정 도구 추가
- 단일 페이지 측정 (`measure.js`) 및 두 페이지 비교 (`compare.js`) 기능 제공
- 독립 실행 가능한 프로젝트로 구성 (별도 `package.json`)

## Test plan
- [ ] `cd tests/image-rendering && npm install` 실행
- [ ] `node measure.js <URL>` 실행하여 이미지 측정 확인

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.5 <noreply@anthropic.com>
```

### fix 예시

```
fix(src/lib): useLocale에서 pathname null 체크 추가 (#520)

## Summary
- `usePathname()`이 `null`을 반환할 수 있으므로 null 체크를 추가
- TypeScript 빌드 에러 수정

## Test plan
- [ ] `npm run build` 성공 확인

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.5 <noreply@anthropic.com>
```

### docs 예시

```
docs(src/content): ko MDX 파일의 이미지를 img 태그로 변환합니다

## Description
- #528 에서 수정한 변환 프로그램을 적용하여 한국어 MDX 파일의 이미지를 재변환합니다.
- Markdown 이미지 문법을 HTML `<img>` 태그로 변환하여 width 속성을 명시합니다.

## Related tickets & links
- #528

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### mdx prefix 예시

```
mdx: Confluence 외부링크를 내부 링크로 수정합니다. (#505)

## Description
- identity-providers.mdx의 Okta Confluence edit-v2 URL을 일반 페이지 URL로 수정합니다.
- installation-guide-setupv2sh.mdx의 Confluence 링크를 내부 문서 링크로 수정합니다.
```

### ci 예시

```
ci(.github/workflows): fetch-openapi-spec 워크플로우를 self-hosted runner에서 실행하도록 변경합니다. (#506)

## Summary
- fetch-openapi-spec 워크플로우를 GitHub-hosted runner 대신 self-hosted runner에서 실행하도록 변경합니다.
- `os:ubuntu`, `purpose:ci` 레이블을 사용합니다.

## Test plan
- [ ] workflow_dispatch로 워크플로우 실행하여 self-hosted runner에서 정상 동작 확인

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.5 <noreply@anthropic.com>
```
