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
2. **스케줄 트리거 (schedule)**: 주기적으로 최신 버전 확인 (예: 매주 월요일)

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

`public/openapi-specification/` 디렉토리의 Spec 파일을 웹페이지로 서비스 제공하는 기능은 별도의 구현 단계로 구분하며, 이 문서의 구현 계획 범위에는 포함하지 않습니다.

웹페이지 서비스 제공을 위한 구현은 다음을 포함할 수 있습니다:
- Next.js 컴포넌트로 OpenAPI Spec 렌더링
- Redoc 또는 Swagger UI 통합
- 버전별 동적 라우팅
- API 문서 페이지 생성

이러한 기능들은 별도의 문서나 이슈에서 계획 및 구현됩니다.

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

