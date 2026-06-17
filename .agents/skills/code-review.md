# 코드 리뷰 가이드라인

## 개요

QueryPie 문서 저장소의 변경 사항을 검토하기 위한 가이드라인입니다.

## 프로젝트 컨텍스트

- **프레임워크**: Next.js 16 + Nextra 4
- **콘텐츠**: MDX 파일 (문서용)
- **빌드 시스템**: npm 기반, Vercel 배포

## 검토 중점 영역

### MDX 문서

- **Frontmatter**: frontmatter가 올바른지 확인
- **구조**: 제목 계층 구조 확인
- **링크**: 내부 및 외부 링크 작동 확인
- **이미지**: 이미지 경로가 올바른지 확인
- **다국어**: 세 가지 언어 버전 (en, ja, ko) 모두 확인

### 다국어 일관성

- 모든 언어(en, ja, ko) 버전이 업데이트되었는지 확인
- 언어 간 동일한 구조 확인
- 번역 품질 확인 — [translation.md](translation.md) 참조

### 빌드 및 배포

- `npm run build` 성공 확인
- `npm run dev`로 콘텐츠 렌더링 확인
- `vercel.json` 수정 시 설정 확인

## 주의해야 할 문제

- frontmatter 누락
- 마크다운 구문 오류
- 잘못된 이미지 경로
- 깨진 내부 링크
- 언어 간 일관되지 않은 구조
- 코드 주석이 영어가 아닌 경우 (프로젝트 규칙: 영어로 작성)

## 리소스

- **프로젝트 README**: `/README.md`
- **개발 가이드**: `/docs/DEVELOPMENT.md`
- **Confluence 워크플로우**: `/confluence-mdx/README.md`
