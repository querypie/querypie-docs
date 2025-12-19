# fetch-openapi-spec

QueryPie 인스턴스에서 OpenAPI Specification을 다운로드하고 저장하는 TypeScript 스크립트입니다.

## 개요

이 스크립트는 사내 QueryPie 인스턴스의 OpenAPI Specification 엔드포인트에서 JSON 파일을 다운로드하여, 버전별로 정리하여 저장합니다.

## 기능

- URL에서 OpenAPI Spec JSON 파일 다운로드
- API 버전 자동 감지 (v0.9 또는 v2)
- QueryPie 버전 정보 추출 (`x-querypie-version` 필드)
- JSON 포맷팅 (가독성 향상)
- 버전별 디렉토리 자동 생성 및 파일 저장
- 변경 감지 (기존 파일과 비교)
- 에러 처리 및 상세 로깅

## 설치

프로젝트 루트에서 의존성을 설치합니다:

```bash
npm install
```

## 사용 방법

### 기본 사용법

```bash
# V2 API Spec 다운로드 (URL에서 버전 자동 감지)
npm run fetch-openapi-spec -- https://internal.dev.querypie.io/api/docs/specification/external-v2

# V0.9 API Spec 다운로드
npm run fetch-openapi-spec -- https://internal.dev.querypie.io/api/docs/specification/external
```

### 옵션

- `--api-version <version>`: API 버전 명시적 지정 (v0.9 또는 v2)
- `--auth-token <token>`: 인증 토큰 (보호된 엔드포인트용)
- `--timeout <ms>`: 요청 타임아웃 (밀리초, 기본값: 30000)
- `--no-overwrite`: 기존 파일 덮어쓰기 방지
- `--help`, `-h`: 도움말 표시

### 예제

```bash
# 명시적 API 버전 지정
npm run fetch-openapi-spec -- https://example.com/api/spec --api-version v2

# 인증 토큰 사용
npm run fetch-openapi-spec -- https://example.com/api/spec --auth-token <your-token>

# 타임아웃 설정
npm run fetch-openapi-spec -- https://example.com/api/spec --timeout 60000

# 기존 파일 덮어쓰기 방지
npm run fetch-openapi-spec -- https://example.com/api/spec --no-overwrite
```

## 출력 디렉토리 구조

다운로드한 파일은 다음 구조로 저장됩니다:

```
public/openapi-specification/
  {querypie-version}/          # 예: 11.4.1, 11.5.0
    v0.9.json                  # V0.9 API Specification
    v2.json                     # V2 API Specification
```

버전 정보는 OpenAPI Spec JSON의 `info.x-querypie-version` 필드에서 추출됩니다.

## API 버전 감지

URL 경로를 분석하여 API 버전을 자동으로 감지합니다:

- `/external-v2` 또는 `/v2` 포함 → `v2.json`
- `/external` 포함 → `v0.9.json`

명시적으로 `--api-version` 옵션을 사용하여 지정할 수도 있습니다.

## 에러 처리

스크립트는 다음 상황에서 에러를 발생시킵니다:

- 네트워크 연결 실패
- HTTP 에러 상태 코드
- JSON 파싱 실패
- 버전 정보 누락 또는 잘못된 형식
- 파일 쓰기 권한 오류

모든 에러는 상세한 메시지와 함께 로그에 기록됩니다.

## 로깅

스크립트는 진행 상황을 다음과 같이 로깅합니다:

- `[INFO]`: 정상 진행 상황
- `[WARN]`: 경고 사항 (기존 파일 덮어쓰기 등)
- `[ERROR]`: 에러 발생

## 개발

### 파일 구조

```
scripts/fetch-openapi-spec/
  index.ts                      # 메인 진입점, CLI 인자 처리
  downloader.ts                 # HTTP 다운로드 로직
  version-parser.ts             # 버전 정보 추출 및 파싱
  json-formatter.ts             # JSON 포맷팅 로직
  file-manager.ts               # 디렉토리 생성 및 파일 저장
  types.ts                      # TypeScript 타입 정의
  utils.ts                      # 유틸리티 함수
  README.md                     # 이 파일
```

### 로컬 개발

TypeScript 파일을 직접 실행하려면 `tsx`를 사용합니다:

```bash
npx tsx scripts/fetch-openapi-spec/index.ts <url>
```

## 참고

- OpenAPI Specification: https://swagger.io/specification/
- QueryPie API 문서: https://docs.querypie.com

