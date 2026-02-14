# OpenAPI Specification 자동 이관 계획

## 목표

QueryPie ACP 제품에서 제공하는 OpenAPI Specification 문서를 `querypie-docs` repository에 버전별로 자동으로 이관하여 관리하고, 문서 사이트에서 제공합니다.

## 진행 현황 (2026-02-14 기준)

- ✅ `scripts/fetch-openapi-spec/` 구현 완료
  - URL 기반 다운로드, API 버전 자동 감지(v0.9/v2), `x-querypie-version` 파싱, `public/openapi-specification/{version}/{apiVersion}.json` 저장
- ✅ `.github/workflows/fetch-openapi-spec.yml` 구현 완료
  - `workflow_dispatch` 수동 실행, base URL 입력, 변경분 브랜치 생성/커밋/PR 생성
- ✅ 문서 사이트 연동 완료
  - 경로: `src/app/[lang]/api-reference/[acpVersion]/[apiVersion]/page.tsx`
  - 렌더러: `src/components/openapi-viewer/OpenApiViewer.tsx` (`redoc` 사용)
  - 사이드바 메타: `src/content/{lang}/api-reference/_meta.ts`
- 🔄 남은 작업
  - `fetch-openapi-spec` 워크플로우 스케줄 트리거 추가 여부 결정
  - 신규 ACP 버전 추가 시 `src/content/{lang}/api-reference/_meta.ts` 갱신 자동화

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

- `public/openapi-specification/11.4.1/v0.9.json`, `public/openapi-specification/11.4.1/v2.json` 파일이 존재합니다.
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

### 현재 채택 접근 방법

현재 저장소 구현은 **방법 2 (사내 QueryPie 인스턴스에서 다운로드)** 를 사용합니다.
- 근거: `scripts/fetch-openapi-spec/index.ts`가 URL 인자를 직접 받아 다운로드
- 근거: `.github/workflows/fetch-openapi-spec.yml`이 base URL 입력값을 받아 `external`, `external-v2` 엔드포인트 호출

## 구현 계획

### 접근 방법 2: 사내 QueryPie 인스턴스에서 다운로드

이 구현 계획은 사내 QueryPie 인스턴스의 OpenAPI Specification 엔드포인트에서 직접 JSON 파일을 다운로드하는 방법을 기반으로 합니다.

### 1단계: TypeScript 프로그램 개발

**프로그램 이름:** `fetch-openapi-spec`

**프로그램 위치:** `scripts/fetch-openapi-spec/`

**주요 기능 요소:**
1. **URL 인자 파싱**: 실행 시 전달받은 URL에서 API 버전(v0.9 또는 v2) 자동 감지
2. **HTTP 다운로드**: 사내 QueryPie 인스턴스에서 OpenAPI Spec JSON 파일 다운로드
3. **버전 정보 추출**: JSON 파일의 `info.x-querypie-version` 필드에서 QueryPie 버전 추출
4. **JSON 포맷팅**: 다운로드한 JSON을 사람이 읽기 쉬운 형태로 포맷팅 (들여쓰기, 정렬)
5. **디렉토리 구조 생성**: 버전별 디렉토리 자동 생성
6. **파일 저장**: 포맷팅된 JSON 파일을 적절한 경로에 저장
7. **에러 처리**: 네트워크 오류, JSON 파싱 오류, 파일 쓰기 오류 등 처리
8. **로깅**: 진행 상황 및 결과를 콘솔에 출력

**코드 파일 구조:**
```
scripts/fetch-openapi-spec/
  index.ts                      # 메인 진입점, CLI 인자 처리
  downloader.ts                 # HTTP 다운로드 로직
  version-parser.ts             # 버전 정보 추출 및 파싱
  json-formatter.ts             # JSON 포맷팅 로직
  file-manager.ts               # 디렉토리 생성 및 파일 저장
  types.ts                      # TypeScript 타입 정의
  utils.ts                      # 유틸리티 함수
  package.json                  # 의존성 관리
  tsconfig.json                 # TypeScript 설정
  README.md                     # 사용 방법 문서
```

**실행 방법:**
```bash
# V0.9 API Spec 다운로드
npm run fetch-openapi-spec -- https://internal.dev.querypie.io/api/docs/specification/external

# V2 API Spec 다운로드
npm run fetch-openapi-spec -- https://internal.dev.querypie.io/api/docs/specification/external-v2
```

**URL에서 API 버전 구분 로직:**
- URL 경로에 `/external-v2` 또는 `/v2`가 포함되어 있으면 → `v2.json`으로 저장
- URL 경로에 `/external`만 포함되어 있으면 → `v0.9.json`으로 저장
- 또는 명시적으로 `--api-version` 옵션으로 지정 가능

### 2단계: JSON 포맷팅 구현

**포맷팅 요구사항:**
- 들여쓰기: 2 spaces
- 키 정렬: 알파벳 순서로 정렬 (선택사항)
- 줄바꿈: 객체/배열의 각 요소를 새 줄에 배치
- 최대 줄 길이: 가독성을 위해 적절한 길이 유지

**구현 방법:**
- Node.js의 `JSON.stringify()` 메서드 사용
- `JSON.stringify(obj, null, 2)` 형태로 포맷팅
- 또는 `prettier` 라이브러리 사용 고려 (더 세밀한 제어 가능)

**예상 출력 형태:**
```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "QueryPie API",
    "version": "V2",
    "x-querypie-version": "11.4.1-eee1211"
  },
  "servers": [
    {
      "url": "https://internal.dev.querypie.io",
      "description": "Generated server url"
    }
  ]
}
```

### 3단계: 디렉토리 구조 및 파일 저장

**저장 경로 구조:**
```
public/openapi-specification/
  {querypie-version}/          # 예: 11.4.1, 11.5.0
    v0.9.json                  # V0.9 API Specification
    v2.json                     # V2 API Specification
```

**버전 추출 로직:**
1. 다운로드한 JSON 파일에서 `info.x-querypie-version` 필드 읽기
2. 버전 형식: `{major}.{minor}.{patch}-{commit-hash}` (예: `11.4.1-eee1211`)
3. 디렉토리명에는 `{major}.{minor}.{patch}` 부분만 사용 (예: `11.4.1`)
4. 해당 디렉토리가 없으면 자동 생성
5. 파일명은 API 버전에 따라 `v0.9.json` 또는 `v2.json`으로 저장

**파일 저장 로직:**
- 기존 파일이 있으면 덮어쓰기
- 변경사항 감지 기능 (선택사항): 기존 파일과 해시 비교하여 변경 여부 확인
- 저장 전 JSON 유효성 검증 수행

### 4단계: 추가 JSON 파일 변경 로직 구현 (향후 확장)

이 단계는 향후 필요에 따라 JSON 파일을 추가로 가공하거나 변경하는 기능을 구현하기 위한 확장 포인트입니다.

**예상 변경 사항:**
1. **서버 URL 변경**: `servers[].url` 필드를 프로덕션 URL로 변경
2. **민감 정보 제거**: 내부 정보나 개발 환경 관련 내용 제거
3. **메타데이터 추가**: 다운로드 날짜, 소스 URL 등의 메타데이터 추가
4. **스키마 정규화**: OpenAPI 스키마를 표준 형식으로 정규화
5. **예제 데이터 보강**: API 예제 데이터 추가 또는 수정

**구현 구조:**
```
scripts/fetch-openapi-spec/
  transformers/
    server-url-transformer.ts   # 서버 URL 변경
    metadata-transformer.ts      # 메타데이터 추가
    schema-normalizer.ts         # 스키마 정규화
    example-enricher.ts          # 예제 데이터 보강
  transformer-registry.ts        # 변환기 등록 및 실행 관리
```

**변환기 실행 순서:**
1. JSON 다운로드
2. 기본 포맷팅
3. 등록된 변환기들을 순차적으로 실행
4. 최종 포맷팅
5. 파일 저장

**변환기 활성화 방법:**
- 환경 변수로 제어: `TRANSFORM_SERVER_URL=true`
- 설정 파일로 제어: `config.json`에서 변환기 활성화 여부 지정
- CLI 옵션으로 제어: `--transform server-url`

### 5단계: 에러 처리 및 로깅

**에러 처리 시나리오:**
1. **네트워크 오류**: 연결 실패, 타임아웃, HTTP 에러 상태 코드
2. **JSON 파싱 오류**: 다운로드한 파일이 유효한 JSON이 아닌 경우
3. **버전 정보 누락**: `x-querypie-version` 필드가 없는 경우
4. **파일 시스템 오류**: 디렉토리 생성 실패, 파일 쓰기 권한 오류
5. **URL 형식 오류**: 잘못된 URL 형식 또는 접근 불가능한 엔드포인트

**로깅 레벨:**
- `INFO`: 정상 진행 상황 (다운로드 시작, 파일 저장 완료 등)
- `WARN`: 경고 사항 (기존 파일 덮어쓰기, 버전 형식 이상 등)
- `ERROR`: 에러 발생 시 상세 정보 출력

**출력 예시:**
```
[INFO] Starting OpenAPI Spec download...
[INFO] URL: https://internal.dev.querypie.io/api/docs/specification/external-v2
[INFO] Detected API version: v2
[INFO] Downloading JSON file...
[INFO] Extracted QueryPie version: 11.4.1-eee1211
[INFO] Creating directory: public/openapi-specification/11.4.1
[INFO] Formatting JSON file...
[INFO] Saving file: public/openapi-specification/11.4.1/v2.json
[INFO] Download completed successfully!
```

### 6단계: GitHub Actions 워크플로우 (선택사항)

**워크플로우 파일:** `.github/workflows/fetch-openapi-spec.yml`

**트리거 방식:**
1. **수동 트리거 (workflow_dispatch)**: 필요 시 수동으로 실행
2. **스케줄 트리거 (schedule)**: 미구현 (필요 시 추가 예정)

**워크플로우 단계:**
1. Repository 체크아웃
2. Node.js 환경 설정
3. 의존성 설치 (`npm install`)
4. OpenAPI Spec 다운로드 스크립트 실행
   - V0.9: `npm run fetch-openapi-spec -- <v0.9-url>`
   - V2: `npm run fetch-openapi-spec -- <v2-url>`
5. 변경사항 확인 (`git diff`)
6. 변경사항이 있으면 PR 생성 또는 직접 커밋

**필요한 Secrets:**
- `QUERYPIE_INSTANCE_URL`: 사내 QueryPie 인스턴스 URL (선택사항)
- `QUERYPIE_AUTH_TOKEN`: 인증 토큰 (필요한 경우)

### 참고: 웹페이지 서비스 제공

이 기능은 현재 구현되어 있습니다.
- 페이지 라우트: `src/app/[lang]/api-reference/[acpVersion]/[apiVersion]/page.tsx`
- 렌더링 컴포넌트: `src/components/openapi-viewer/OpenApiViewer.tsx`
- 스펙 파일 로딩 경로: `/openapi-specification/{querypieVersion}/{apiVersion}.json`

## 기술적 고려사항

### 1. 다운로드 실행 환경

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

- 다운로드 실행 실패
- 네트워크 오류
- JSON 파싱 오류
- 버전 정보 추출 실패
- 파일 쓰기 권한 오류

모든 에러에 대해 적절한 로깅과 사용자 피드백 제공 필요

### 5. 인증 및 보안

- Docker 레지스트리 접근 권한
- 사내 인스턴스 접근 권한 (방법 2 사용 시)
- GitHub Actions Secrets에 민감 정보 저장

### 6. Phase 3 구현 시 고려사항

#### 6.1 번들 크기 최적화

- OpenAPI Spec JSON 파일은 매우 큼 (약 84,000줄)
- 클라이언트 사이드에서 로드하므로 번들 크기 고려 필요
- **해결 방안:**
  - JSON 파일은 `public` 폴더에 저장하여 별도 번들로 처리
  - OpenAPI 뷰어 컴포넌트(`redoc`)와 일반 문서 페이지의 코드 경로 분리
  - 코드 스플리팅 활용

#### 6.2 성능 최적화

- **초기 로딩 시간:**
  - JSON 파일 크기가 크므로 로딩 시간 고려
  - 로딩 스피너 및 진행 상태 표시 필요
  
- **캐싱 전략:**
  - 브라우저 캐싱 활용 (JSON 파일은 변경 빈도 낮음)
  - Next.js 정적 생성 활용
  - CDN 캐싱 고려

#### 6.3 SEO 최적화

- MDX 파일 사용으로 SEO 자동 지원
- 페이지 메타데이터(front matter) 설정
- 구조화된 데이터(JSON-LD) 추가 고려
- 버전별 canonical URL 설정

#### 6.4 다국어 지원

- 기존 Next.js i18n 설정과 일치
- 각 언어별 MDX 파일 생성
- 버전 정보 및 설명 다국어화
- 언어별 사이드바 네비게이션 구성

#### 6.5 버전 관리

- 새로운 QueryPie 버전 출시 시 자동 MDX 파일 생성
- 레거시 버전 유지 정책 결정
- 버전 선택 UI 구현 (선택사항)
- 최신 버전 자동 감지 및 표시

## 구현 우선순위

### Phase 1: 기본 기능 구현
1. ✅ 사내 QueryPie 인스턴스 다운로드 스크립트 개발
2. ✅ 버전 정보 파싱 및 파일 저장
3. ✅ 수동 실행 가능한 스크립트 완성

### Phase 2: 자동화
1. ✅ GitHub Actions 워크플로우 구현
2. 🔄 수동 트리거 구현, 스케줄 트리거는 미구현
3. ✅ PR 자동 생성 기능

### Phase 3: 문서 통합

이 단계에서는 `public/openapi-specification/` 디렉토리에 저장된 OpenAPI Spec JSON 파일을 웹 문서 사이트에서 표시하는 기능을 구현합니다.

#### 3.1 URI 체계 설계

**권장 URI 구조:**
```
/{lang}/api-reference/{querypie-version}/{api-version}
```

**예시:**
- `/en/api-reference/11.4.1/v2` - 영어, QueryPie 11.4.1, V2 API
- `/ko/api-reference/11.4.1/v0.9` - 한국어, QueryPie 11.4.1, V0.9 API
- `/ja/api-reference/11.5.0/v2` - 일본어, QueryPie 11.5.0, V2 API

**라우팅 규칙:**
- `{lang}`: 다국어 지원 (en, ko, ja) - 기존 Next.js i18n 설정과 일치
- `{querypie-version}`: QueryPie 버전 (예: 11.4.1, 11.5.0)
- `{api-version}`: API 버전 (v0.9 또는 v2)

**대체 URI 구조 (선택사항):**
```
/{lang}/api-reference/{querypie-version}?apiVersion={api-version}
```
- 쿼리 파라미터 방식은 URL이 더 짧지만, SEO와 공유 측면에서 덜 유리

#### 3.2 구현 방식 결정

**실제 구현: Next.js 동적 라우트 + React 컴포넌트**

**구현 요약:**
1. `src/app/[lang]/api-reference/[acpVersion]/[apiVersion]/page.tsx`에서 정적 파라미터 생성 및 메타데이터 처리
2. `OpenApiViewer`에서 JSON fetch 후 Redoc 렌더링
3. 언어별 `_meta.ts`로 사이드바 엔트리 제공

**구현 구조:**
```
src/app/[lang]/api-reference/[acpVersion]/[apiVersion]/page.tsx  # 동적 라우트
src/components/openapi-viewer/OpenApiViewer.tsx                  # Redoc 렌더링
src/content/{lang}/api-reference/_meta.ts                        # 사이드바 메타데이터
src/content/{lang}/api-reference/{version}/_meta.ts              # 버전별 사이드바 메타
```

**대안 방식 비교:**

| 방식 | 장점 | 단점 | 권장도 |
|------|------|------|--------|
| **Next.js 동적 라우트 + React 컴포넌트 (현재 적용)** | 파일 자동 생성 불필요, 버전/언어 파라미터 처리 용이 | 사이드바 메타를 별도 유지해야 함 | ⭐⭐⭐⭐⭐ |
| MDX 파일 + React 컴포넌트 | Nextra 통합 직관적 | 버전 증가 시 파일 생성/관리 비용 증가 | ⭐⭐⭐ |
| 순수 MDX 파일 | 단순함 | 대용량 JSON 처리 어려움 | ⭐⭐ |

#### 3.3 OpenAPI 렌더링 라이브러리 선택

**현재 적용: `redoc` 패키지 (`RedocStandalone`)**

**옵션 1: Redoc (권장)**
- **장점:**
  - 깔끔하고 읽기 쉬운 UI
  - 3-panel 레이아웃 (메뉴, 요청/응답, 코드 샘플)
  - React 컴포넌트 제공 (`redoc`)
  - 번들 크기 최적화
  - 다크 모드 지원
- **단점:**
  - Swagger UI 대비 커스터마이징 옵션 제한
- **설치:**
  ```bash
  npm install redoc
  ```

**옵션 2: Swagger UI React**
- **장점:**
  - 널리 사용되는 표준 도구
  - Try it out 기능 (실제 API 호출 테스트)
  - 풍부한 커스터마이징 옵션
- **단점:**
  - 번들 크기가 큼
  - UI가 Redoc 대비 다소 복잡
- **설치:**
  ```bash
  npm install swagger-ui-react
  ```

**옵션 3: ReDocly (Redocly)**
- Redoc의 상용 버전
- 추가 기능: 검색, 다중 스펙 지원 등
- 무료 버전도 제공

**최종 선택: Redoc (`redoc`)**
- 문서 사이트에 적합한 깔끔한 UI
- React 통합 용이
- 적절한 번들 크기

#### 3.4 React 컴포넌트 구현

**컴포넌트 구조:**
```
src/components/
  openapi-viewer/
    index.tsx                      # 메인 컴포넌트
    OpenApiViewer.tsx              # OpenAPI Spec 렌더링 컴포넌트
    VersionSelector.tsx            # 버전 선택 드롭다운 (선택사항)
    types.ts                        # TypeScript 타입 정의
```

**주요 기능:**
1. **OpenAPI Spec 로드:**
   - `public/openapi-specification/{version}/{api-version}.json` 파일 로드
   - 클라이언트 사이드에서 `fetch` 또는 Next.js `public` 폴더 직접 참조
   - 로딩 상태 표시

2. **에러 처리:**
   - 파일이 없을 경우 404 에러 표시
   - JSON 파싱 오류 처리
   - 네트워크 오류 처리

3. **버전 정보 표시:**
   - QueryPie 버전 표시
   - API 버전 표시
   - 마지막 업데이트 날짜 (선택사항)

**구현 예시:**
```tsx
// src/components/openapi-viewer/OpenApiViewer.tsx
'use client';

import { useEffect, useState } from 'react';
import { RedocStandalone } from 'redoc';

interface OpenApiViewerProps {
  querypieVersion: string;
  apiVersion: 'v0.9' | 'v2';
  lang: string;
}

export function OpenApiViewer({ 
  querypieVersion, 
  apiVersion,
  lang 
}: OpenApiViewerProps) {
  const [spec, setSpec] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const specPath = `/openapi-specification/${querypieVersion}/${apiVersion}.json`;
    
    fetch(specPath)
      .then(res => {
        if (!res.ok) throw new Error(`Failed to load: ${res.statusText}`);
        return res.json();
      })
      .then(data => {
        setSpec(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [querypieVersion, apiVersion]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!spec) return null;

  return (
    <div>
      <RedocStandalone 
        spec={spec}
        options={{
          theme: {
            colors: {
              primary: {
                main: '#0070f3'
              }
            }
          }
        }}
      />
    </div>
  );
}
```

#### 3.5 MDX 페이지 파일 생성

현재 구현에서는 버전별 `.mdx` 파일을 생성하지 않고, 동적 라우트에서 직접 렌더링합니다.

**파일 구조:**
```
src/content/{lang}/api-reference/
  _meta.ts
  {querypie-version}/
    _meta.ts
    v2.mdx
    v0.9.mdx
```

**MDX 파일 예시:**
```mdx
---
title: API Reference - V2
description: QueryPie API V2 Specification
sidebarTitle: V2 API
---

import { OpenApiViewer } from '@/components/openapi-viewer';

# QueryPie API Reference - V2

<OpenApiViewer 
  querypieVersion="11.4.1"
  apiVersion="v2"
  lang="en"
/>
```

**메타데이터 파일 (`_meta.ts`):**
```typescript
// src/content/en/api-reference/_meta.ts
export default {
  '11.4.1': {
    title: 'Version 11.4.1',
    type: 'page',
    children: {
      'v2': {
        title: 'V2 API',
        type: 'page'
      },
      'v0.9': {
        title: 'V0.9 API',
        type: 'page'
      }
    }
  }
};
```

#### 3.6 동적 라우팅 구현 (선택사항)

이 항목은 현재 구현 방식으로 채택 완료되었습니다.

**방법 1: 정적 MDX 파일 생성 (권장)**
- 각 버전별로 MDX 파일을 수동 또는 자동 생성
- 빌드 타임에 모든 페이지 생성
- SEO와 성능에 유리

**방법 2: Next.js 동적 라우트**
- `app/[lang]/api-reference/[version]/[apiVersion]/page.tsx` 사용
- 런타임에 JSON 파일 로드
- 파일 생성 불필요하지만 SEO 제한

**채택: 방법 2 (Next.js 동적 라우트)**
- 구현 파일: `src/app/[lang]/api-reference/[acpVersion]/[apiVersion]/page.tsx`
- 정적 파라미터 생성으로 빌드 시점에 버전/언어 조합 페이지를 생성

#### 3.7 자동 MDX 파일 생성 스크립트

현재 저장소에는 `scripts/generate-api-reference-pages/`가 없으며, 미도입 상태입니다.

**기능:**
1. `public/openapi-specification/` 디렉토리 스캔
2. 버전별 `_meta.ts` 엔트리 자동 생성/정렬
3. 다국어 지원 (en, ko, ja)

대신 `_meta.ts` 갱신 자동화만 별도 개선 과제로 유지합니다.

#### 3.8 구현 단계별 계획

**3.8.1 컴포넌트 개발**
1. OpenAPI Viewer 컴포넌트 구현
2. 에러 처리 및 로딩 상태 구현
3. 버전 정보 표시 컴포넌트 구현

**3.8.2 MDX 파일 구조 생성**
1. `src/content/{lang}/api-reference/` 디렉토리 생성
2. 샘플 MDX 파일 생성 (11.4.1/v2.mdx)
3. `_meta.ts` 파일 생성

**3.8.3 자동화 스크립트 개발**
1. `_meta.ts` 자동 업데이트 스크립트 개발
2. `fetch-openapi-spec` 스크립트와 통합

**3.8.4 테스트 및 검증**
1. 로컬 환경에서 페이지 렌더링 테스트
2. 다양한 버전 조합 테스트
3. 다국어 지원 테스트
4. 빌드 및 배포 테스트

**3.8.5 문서화**
1. API Reference 페이지 접근 방법 문서화
2. 버전 선택 가이드 작성
3. 개발자 가이드 업데이트

### Phase 4: 최적화
1. Git LFS 적용 (필요 시)
2. 캐싱 전략 구현
3. 성능 최적화

## 참고 자료

### OpenAPI 관련
- [SpringDoc OpenAPI](https://springdoc.org/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Redoc](https://github.com/Redocly/redoc)
- [Redocly React Doc](https://github.com/Redocly/react-doc)
- [Swagger UI React](https://github.com/swagger-api/swagger-ui)

### Next.js 및 Nextra 관련
- [Next.js Static File Serving](https://nextjs.org/docs/app/building-your-application/optimizing/static-assets)
- [Next.js Dynamic Routes](https://nextjs.org/docs/app/building-your-application/routing/dynamic-routes)
- [Nextra Content Directory](https://nextra.site/docs/file-conventions/content-directory)
- [Nextra MDX Components](https://nextra.site/docs/file-conventions/mdx-components-file)

### 구현 참고
- [Redocly Documentation](https://redocly.com/docs)
- [MDX Documentation](https://mdxjs.com/)
- [React Server Components](https://nextjs.org/docs/app/building-your-application/rendering/server-components)

## 다음 단계

### 완료된 단계
1. ✅ `fetch-openapi-spec` 스크립트 구현 및 수동 실행 검증
2. ✅ OpenAPI fetch GitHub Actions 워크플로우 및 PR 자동 생성 구현
3. ✅ API Reference 동적 라우팅/렌더링 구현

### 다음 작업
1. `fetch-openapi-spec` 워크플로우의 `schedule` 트리거 추가 여부 결정 및 적용
2. 신규 버전 추가 시 언어별 `_meta.ts` 자동 갱신 스크립트 도입 여부 결정
3. API Reference 페이지의 버전 선택 UX(예: latest 링크/selector) 개선 검토
