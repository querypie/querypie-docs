# Image Rendering Test Tool

Playwright 기반 이미지 렌더링 크기 측정 도구입니다.

## 용도

이 도구는 **Confluence에서 변환된 문서의 이미지가 원본과 동일한 크기로 렌더링되는지 검증**하기 위해 만들어졌습니다.

### 배경

- Confluence에서 작성된 문서를 MDX로 변환하여 docs.querypie.com에 배포합니다.
- 변환 과정에서 이미지 크기 정보가 손실되면, Next.js Image 컴포넌트가 이미지를 컨테이너 너비에 맞게 확대하여 표시합니다.
- 이로 인해 Confluence에서 480px로 표시되던 이미지가 832px로 확대되는 등의 문제가 발생했습니다.

### 해결하는 문제

- Confluence 원본과 docs.querypie.com 간의 이미지 렌더링 크기 차이 측정
- Vercel Preview 배포 후 수정 사항 검증
- 이미지 크기 관련 이슈에 대한 정량적 리포트 생성

### 관련 이슈

- [#508](https://github.com/querypie/querypie-docs/issues/508) - 이미지 크기 불일치 최초 보고
- [#518](https://github.com/querypie/querypie-docs/issues/518) - 이미지 렌더링 크기 측정 결과
- [#529](https://github.com/querypie/querypie-docs/issues/529) - img 태그 변환 개선 후 비교

## 설치

```bash
cd tests/image-rendering
npm install
```

## 사용법

### 단일 페이지 측정

```bash
# 기본 테이블 출력
node measure.js https://example.com/page

# Markdown 형식으로 파일 저장
node measure.js https://example.com/page -f markdown -o report.md

# JSON 형식으로 저장
node measure.js https://example.com/page -f json -o result.json

# Headless 모드로 실행
node measure.js https://example.com/page --headless
```

### 두 페이지 비교

```bash
# 기본 비교
node compare.js https://site1.com/page https://site2.com/page

# 라벨 지정 및 Markdown 리포트 생성
node compare.js \
  https://vercel-preview.app/page \
  https://confluence.com/page \
  --label1 "Vercel" \
  --label2 "Confluence" \
  -f markdown \
  -o comparison.md
```

## 옵션

### measure.js

| 옵션 | 단축 | 설명 | 기본값 |
|------|------|------|--------|
| `--output` | `-o` | 출력 파일 경로 | stdout |
| `--format` | `-f` | 출력 형식: json, markdown, table | table |
| `--viewport` | `-v` | 뷰포트 크기 WxH | 1920x1080 |
| `--headless` | | Headless 모드 실행 | false |
| `--min-size` | | 최소 이미지 크기 (px) | 50 |

### compare.js

| 옵션 | 단축 | 설명 | 기본값 |
|------|------|------|--------|
| `--output` | `-o` | 출력 파일 경로 | stdout |
| `--format` | `-f` | 출력 형식: json, markdown, table | table |
| `--viewport` | `-v` | 뷰포트 크기 WxH | 1920x1080 |
| `--headless` | | Headless 모드 실행 | false |
| `--label1` | | 첫 번째 URL 라벨 | URL1 |
| `--label2` | | 두 번째 URL 라벨 | URL2 |

## 출력 예시

### Table 형식

```
URL: https://example.com/page
Timestamp: 2026-01-23T12:00:00.000Z
Viewport: 1920x1080
Images: 5

| # | Filename | Rendered (WxH) | Natural (WxH) | HTML Width |
|---|----------|----------------|---------------|------------|
| 1 | image-001.png | 760 x 476 | 2926 x 1832 | 760 |
| 2 | image-002.png | 532 x 316 | 1064 x 632 | 532 |
```

### Markdown 형식

전체 리포트가 Markdown 테이블로 생성되어 GitHub 이슈나 문서에 바로 사용할 수 있습니다.

### JSON 형식

프로그래밍 방식으로 결과를 처리할 때 사용합니다.
