# 번역 가이드라인

## 개요

이 skill은 QueryPie 문서 저장소에서 콘텐츠를 번역하기 위한 가이드라인을 제공합니다.

**상세 번역 지침**: [docs/translation.md](/docs/translation.md)를 반드시 참조하세요.

## 핵심 원칙

### 소스 언어

- **소스 언어**: 한국어 (ko) - `src/content/ko/`
- **대상 언어**: 영어 (en), 일본어 (ja)
- **번역 방향**: ko → en, ko → ja

### 파일 구조

```
src/content/
├── ko/          # 한국어 (소스/원본)
├── en/          # 영어 (한국어에서 번역)
└── ja/          # 일본어 (한국어에서 번역)
```

모든 언어에서 동일한 파일 경로와 이름을 사용해야 합니다.

## 번역 프로세스 가이드라인

1. **일괄 처리**: 한 번에 50개 문서 번역 또는 검토 후 리뷰 요청
2. **빌드 검증**: 번역/수정 1차 완료 후 로컬 `npm run build`를 실행하여 빌드 성공을 확인
3. **재번역 금지**: 특별히 지시하지 않는 한 이미 번역된 문서를 다시 번역하지 않음
4. **피드백**: 한국어 소스에서 발견된 오류 및 번역 중 어려움 보고

## 중요 번역 규칙 요약

### 반드시 보존할 것

- 마크다운 포맷팅 (표, 목록, `**강조**` 등)
  - `**text**` 강조 표시 (`<strong>` 대체 금지)
- 줄 바꿈 형식
- HTML 인코딩된 문자열 (임의로 디코드 금지)
  - `&lt;`, `&gt;`로 인코딩된 문자열 그대로 유지
  - 예: 원문의 `&lt;token&gt;`을 `<token>`으로 변경 금지
- 중괄호로 감싸인 문자열의 backquote 유지
  - 예: `{querypie url}` 그대로 유지
- 문서 간 상대 경로 링크
- 코드 블록 내용 (번역하지 않음)
- 이미지 경로

### 번역 대상

- Frontmatter 제목
- 본문 텍스트
- 이미지 alt 텍스트와 캡션

### 번역하지 않는 것

- 코드 예시
- 코드 주석 (영어로 유지)
- 이미지 파일 (한국어 소스와 동일하게 사용)
- 링크 경로 (텍스트만 번역)

## MDX 문법 참조

### Frontmatter

```yaml
---
title: '페이지 제목'
---
```

### Callout 컴포넌트

```jsx
import { Callout } from 'nextra/components'

<Callout type="info">
  중요한 정보를 여기에 작성
</Callout>
```

### 이미지 (figure 컴포넌트)

```jsx
<figure data-layout="center" data-align="center">
  ![이미지 설명](/path/to/image.png)
  <figcaption>
    캡션 텍스트
  </figcaption>
</figure>
```

### 테이블

```markdown
<table data-table-width="760" data-layout="default">
```

### 링크

- 내부 링크: `[링크 텍스트](relative/path/to/page)` (상대 경로)
- 파일 이름: kebab-case 사용

## 언어별 톤 가이드

### 영어 (en)

- 표준 영어, 격식 있지만 친화적
- 딱딱한 스타일보다 대화체 선호
- 능동태 사용 권장

### 일본어 (ja)

- 표준 일본어, 적절한 경어
- 격식 있지만 친화적
- 기술 용어는 영어 또는 가타카나 사용 가능

## 품질 체크리스트

번역 완료 전:

- [ ] 모든 콘텐츠가 한국어에서 번역됨
- [ ] 마크다운 포맷팅이 원본과 동일함
- [ ] `npm run build` 성공
- [ ] 구조가 한국어 소스와 일치함

## 상세 지침

다음 문서에서 상세한 번역 지침을 확인하세요:

- **번역 상세 지침**: [docs/translation.md](/docs/translation.md)
- **제품명/API 명칭 지침**: [docs/api-naming-guide.md](/docs/api-naming-guide.md)
- **Skeleton MDX 비교**: [docs/translation.md](/docs/translation.md)의 "Skeleton MDX 를 비교하기" 섹션
- **MDX 스켈레톤 비교 Skill**: [mdx-skeleton-comparison.md](mdx-skeleton-comparison.md)
