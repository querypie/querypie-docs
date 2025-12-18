# OpenAPI Specification 자동 이관 계획

## 목표

QueryPie ACP 제품에서 제공하는 OpenAPI Specification 문서를 `querypie-docs` repository에 버전별로 자동으로 이관하여 관리하고, 문서 사이트에서 제공합니다.

## 현재 상황 파악

### 1. OpenAPI Spec 생성 방식

QueryPie ACP는 Spring Boot 기반 애플리케이션으로, `springdoc-openapi` 라이브러리를 사용하여 OpenAPI Specification을 동적으로 생성합니다.

- **Swagger UI URL 예시:**
  - V0.9: `https://internal.dev.querypie.io/api/docs/external`
  - V2: `https://internal.dev.querypie.io/api/docs/external/v2`

- **OpenAPI Spec JSON 다운로드 URL:**
  - V0.9: `https://internal.dev.querypie.io/api/docs/specification/external`
  - V2: `https://internal.dev.querypie.io/api/docs/specification/external-v2`

### 2. Docker 이미지 구조

- Docker 이미지 내부에는 OpenAPI Spec JSON이나 Static HTML/JS 파일이 별도로 존재하지 않습니다.
- `/app/api/api.jar` 내부의 `springdoc-openapi` 기능에서 동적으로 생성됩니다.
- Swagger는 OpenAPI Spec이 주어졌을 때 HTML UI를 생성하여 보여주는 역할을 담당합니다.

### 3. 현재 저장 상태

- `public/openapi-specification/11.4.1/v2.json` 파일이 이미 존재합니다.
- OpenAPI Spec JSON 파일에는 `x-querypie-version` 필드에 QueryPie 버전 정보가 포함되어 있습니다.

## 버전 관리 전략

### 디렉토리 구조

```
public/openapi-specification/
  {querypie-version}/          # 예: 11.4.1, 11.5.0
    v0.9.json                  # V0.9 API Specification
    v2.json                     # V2 API Specification
```

### 버전 식별 방법

1. **QueryPie 버전**: OpenAPI Spec JSON의 `info.x-querypie-version` 필드에서 추출
   - 형식: `{major}.{minor}.{patch}-{commit-hash}` (예: `11.4.1-eee1211`)
   - 디렉토리명에는 `{major}.{minor}.{patch}` 부분만 사용

2. **API 버전**: URL 경로에서 구분
   - `/api/docs/specification/external` → `v0.9.json`
   - `/api/docs/specification/external-v2` → `v2.json`

### 버전 저장 정책

- QueryPie의 각 릴리스 버전마다 OpenAPI Spec을 저장합니다.
- V0.9와 V2 모두 저장합니다 (호환성 유지 및 레거시 지원).

## 자동화 방법

### 접근 방법 비교

#### 방법 1: Docker 이미지에서 추출 (권장)

**장점:**
- 외부 의존성 없음 (사내 인스턴스 접근 불필요)
- 버전별 Docker 이미지만 있으면 언제든지 추출 가능
- CI/CD 파이프라인에서 자동화하기 용이

**구현 방법:**
1. Docker 이미지에서 컨테이너 실행
2. 컨테이너 내부에서 Spring Boot 애플리케이션 시작
3. 헬스체크로 애플리케이션 준비 완료 대기
4. `curl` 또는 `wget`으로 OpenAPI Spec JSON 다운로드
5. 컨테이너 종료 및 정리

**필요한 환경:**
- Docker 이미지 또는 이미지 레지스트리 접근 권한
- 컨테이너 실행에 필요한 환경 변수 및 설정 정보
- 네트워크 포트 매핑 (기본적으로 8080 포트 사용)

#### 방법 2: 사내 QueryPie 인스턴스에서 다운로드

**장점:**
- 구현이 간단함 (HTTP 요청만 필요)
- 실제 운영 환경의 Spec을 바로 가져올 수 있음

**단점:**
- 사내 인스턴스 접근 권한 필요
- 네트워크 의존성
- 인스턴스가 다운되어 있으면 사용 불가

**구현 방법:**
1. 사내 QueryPie 인스턴스 URL 확인
2. 인증 토큰 또는 접근 권한 확인
3. HTTP GET 요청으로 OpenAPI Spec JSON 다운로드

### 추천 접근 방법

**방법 1 (Docker 이미지 추출)을 권장합니다.** 이유:
- 외부 의존성 최소화
- 재현 가능한 빌드 프로세스
- 버전 관리와 일관성 유지

## 구현 계획

### 1단계: 스크립트 개발

**스크립트 위치:** `scripts/fetch-openapi-spec/`

**기능 요구사항:**
- Docker 이미지에서 OpenAPI Spec 추출
- 버전 정보 파싱 및 디렉토리 생성
- JSON 유효성 검증
- 변경 감지 (기존 파일과 비교)
- 에러 처리 및 로깅

**스크립트 구조:**
```
scripts/fetch-openapi-spec/
  index.ts                    # 메인 스크립트
  docker-extractor.ts         # Docker 이미지에서 추출하는 로직
  version-parser.ts           # 버전 정보 파싱
  json-validator.ts           # JSON 유효성 검증
  README.md                   # 사용 방법 문서
```

### 2단계: GitHub Actions 워크플로우

**워크플로우 파일:** `.github/workflows/fetch-openapi-spec.yml`

**트리거 방식:**
1. **수동 트리거 (workflow_dispatch)**: 필요 시 수동으로 실행
2. **스케줄 트리거 (schedule)**: 주기적으로 최신 버전 확인
3. **릴리스 트리거 (release)**: 새 버전 릴리스 시 자동 실행

**워크플로우 단계:**
1. Repository 체크아웃
2. Docker 이미지 다운로드 (또는 레지스트리에서 pull)
3. OpenAPI Spec 추출 스크립트 실행
4. 변경사항 확인
5. 변경사항이 있으면 PR 생성 또는 직접 커밋

### 3단계: OpenAPI Spec 표시

**표시 방법 옵션:**

#### 옵션 A: Redoc을 사용한 정적 HTML 생성
- Redoc CLI를 사용하여 OpenAPI Spec JSON에서 HTML 생성
- 빌드 시점에 HTML 파일 생성
- Next.js의 정적 파일로 제공

#### 옵션 B: Next.js 컴포넌트로 통합
- `@redocly/react-doc` 또는 유사한 라이브러리 사용
- 런타임에 OpenAPI Spec JSON을 읽어서 렌더링
- 동적 라우팅으로 버전별 페이지 제공

#### 옵션 C: iframe으로 Swagger UI 임베드
- 별도 서버에서 Swagger UI 제공
- 문서 사이트에서 iframe으로 임베드
- 가장 간단하지만 별도 인프라 필요

**권장 방법:** 옵션 B (Next.js 컴포넌트로 통합)
- 문서 사이트와 일관된 UI/UX
- SEO 최적화 가능
- 버전별 동적 라우팅 용이

### 4단계: 문서 페이지 생성

**페이지 구조:**
```
src/content/{lang}/api/
  index.mdx                    # API 문서 인덱스 페이지
  [version]/
    index.mdx                  # 버전별 API 문서 페이지
    v0.9.mdx                   # V0.9 API 문서
    v2.mdx                     # V2 API 문서
```

**MDX 파일 예시:**
```mdx
---
title: 'API Documentation - V2'
---

import { OpenAPISpec } from '@/components/OpenAPISpec'

# QueryPie API V2

<OpenAPISpec 
  specPath="/openapi-specification/11.4.1/v2.json"
  version="v2"
/>
```

## 기술적 고려사항

### 1. Docker 컨테이너 실행

**필요한 설정:**
- 환경 변수: 데이터베이스 연결 정보, 라이센스 키 등
- 포트 매핑: 컨테이너 내부 포트를 호스트 포트로 매핑
- 헬스체크: 애플리케이션 시작 완료까지 대기
- 타임아웃: 응답이 없을 경우 타임아웃 처리

**예상 실행 시간:**
- 컨테이너 시작: 30-60초
- 애플리케이션 초기화: 1-2분
- Spec 다운로드: 1-2초
- 총 소요 시간: 약 2-3분

### 2. JSON 파일 크기

- 현재 `v2.json` 파일이 약 84,000줄로 매우 큽니다.
- Git 저장소에 직접 커밋하는 것이 적절한지 검토 필요
- **Git LFS 사용 고려**: 대용량 파일 관리

### 3. 변경 감지

- 기존 파일과 새로 다운로드한 파일을 비교
- 해시 값 비교로 변경 여부 확인
- 변경사항이 없으면 스킵하여 불필요한 커밋 방지

### 4. 에러 처리

- Docker 컨테이너 실행 실패
- 네트워크 오류
- JSON 파싱 오류
- 버전 정보 추출 실패
- 파일 쓰기 권한 오류

모든 에러에 대해 적절한 로깅과 사용자 피드백 제공 필요

### 5. 인증 및 보안

- Docker 레지스트리 접근 권한
- 사내 인스턴스 접근 권한 (방법 2 사용 시)
- GitHub Actions Secrets에 민감 정보 저장

## 구현 우선순위

### Phase 1: 기본 기능 구현
1. ✅ Docker 이미지에서 OpenAPI Spec 추출 스크립트 개발
2. ✅ 버전 정보 파싱 및 파일 저장
3. ✅ 수동 실행 가능한 스크립트 완성

### Phase 2: 자동화
1. GitHub Actions 워크플로우 구현
2. 수동 트리거 및 스케줄 트리거 설정
3. PR 자동 생성 기능

### Phase 3: 문서 통합
1. OpenAPI Spec 표시 컴포넌트 개발
2. 문서 페이지 생성
3. 버전별 라우팅 설정

### Phase 4: 최적화
1. Git LFS 적용 (필요 시)
2. 캐싱 전략 구현
3. 성능 최적화

## 참고 자료

- [SpringDoc OpenAPI](https://springdoc.org/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Redoc](https://github.com/Redocly/redoc)
- [Next.js Static File Serving](https://nextjs.org/docs/app/building-your-application/optimizing/static-assets)

## 다음 단계

1. Docker 이미지 접근 방법 확인 및 테스트
2. 스크립트 프로토타입 개발
3. GitHub Actions 워크플로우 설계
4. OpenAPI Spec 표시 컴포넌트 선택 및 구현

