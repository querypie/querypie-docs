# 문서 작성 가이드라인

## 개요

이 skill은 QueryPie 문서 저장소에서 MDX 문서 파일을 작성하고 편집하기 위한 가이드라인을 제공합니다.

## 프로젝트 컨텍스트

- **프레임워크**: Next.js 15 + Nextra 4
- **콘텐츠 형식**: MDX (Markdown with JSX)
- **언어**: 영어 (en), 일본어 (ja), 한국어 (ko)
- **콘텐츠 위치**: `src/content/{lang}/`

## MDX 파일 구조

### Frontmatter

모든 MDX 파일은 frontmatter로 시작해야 합니다:

```yaml
---
title: '페이지 제목'
---
```

### 일반적인 Imports

Nextra 컴포넌트용:

```jsx
import { Callout } from 'nextra/components'
```

## 작성 가이드라인

### 언어별 고려사항

1. **영어 (en)**: 기본 언어, 명확하고 전문적이어야 함
2. **한국어 (ko)**: 영어 버전과 일관성 유지
3. **일본어 (ja)**: 영어 버전과 일관성 유지

### 콘텐츠 구조

- 명확한 제목 사용 (H1은 메인 제목, H2는 주요 섹션, H3은 하위 섹션)
- 적절한 경우 개요 섹션 포함
- 중요한 정보에는 Callout 컴포넌트 사용:
  ```jsx
  <Callout type="info">
    중요한 정보를 여기에 작성
  </Callout>
  ```

### 이미지

- 이미지는 `public/` 디렉토리에 저장
- 상대 경로로 참조: `/user-manual/workflow/screenshot.png`
- 캡션이 있는 이미지에는 figure 컴포넌트 사용:
  ```jsx
  <figure data-layout="center" data-align="center">
    ![이미지 설명](/path/to/image.png)
    <figcaption>
      캡션 텍스트
    </figcaption>
  </figure>
  ```

### 테이블

- 표준 마크다운 테이블 사용
- 테이블에 스타일링을 위한 data 속성 포함 가능:
  ```markdown
  <table data-table-width="760" data-layout="default">
  ```

### 링크

- 내부 링크에는 상대 경로 사용
- 형식: `[링크 텍스트](relative/path/to/page)`
- 다국어 링크의 경우 동일한 구조 유지

## 파일 네이밍 규칙

- 파일 이름에 kebab-case 사용
- 모든 언어에서 동일한 구조 유지
- 예: `user-manual/workflow.mdx`는 `en/`, `ja/`, `ko/`에 존재

## 모범 사례

1. **일관성**: 모든 언어 버전에서 동일한 구조 유지
2. **명확성**: 명확하고 간결한 문서 작성
3. **완전성**: 세 가지 언어 버전 모두 업데이트 확인
4. **테스트**: `npm run dev`로 MDX 파일이 올바르게 렌더링되는지 확인
5. **접근성**: 이미지에 설명적인 alt 텍스트 사용
6. **코드 주석**: 코드 주석은 영어로 작성 (프로젝트 규칙)

## 일반적인 작업

### 새 페이지 추가

1. 각 언어에 대해 `src/content/{lang}/`에 MDX 파일 생성
2. 제목이 있는 frontmatter 추가
3. 구조 가이드라인에 따라 콘텐츠 작성
4. 필요시 네비게이션 항목 추가
5. `npm run dev`로 로컬 테스트

### 기존 콘텐츠 편집

1. 해당 언어 디렉토리에서 파일 찾기
2. 다른 언어 버전과 일관성을 유지하며 변경
3. 변경이 구조에 영향을 미치면 세 가지 언어 버전 모두 업데이트
4. 변경 사항을 로컬에서 테스트

### 이미지 추가

1. 적절한 `public/` 하위 디렉토리에 이미지 배치
2. 루트에서 절대 경로로 참조: `/path/to/image.png`
3. 더 나은 표현을 위해 figure 컴포넌트 사용

## 코드 예시

코드 예시를 포함할 때:

- 적절한 언어 태그 사용
- 예시를 간단하고 관련성 있게 유지
- 명확성을 위해 주석 포함 (영어로)

```bash
npm run dev
```

```typescript
// Example TypeScript code
const example: string = "value";
```

## 검토 체크리스트

문서 변경 사항을 커밋하기 전:

- [ ] Frontmatter가 올바름
- [ ] 세 가지 언어 버전 모두 업데이트됨 (해당되는 경우)
- [ ] 이미지가 올바르게 참조됨
- [ ] 링크가 작동함
- [ ] 로컬 개발 서버에서 콘텐츠가 올바르게 렌더링됨
- [ ] 코드 예시가 정확함
- [ ] 깨진 마크다운 구문 없음

