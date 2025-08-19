# Vercel 환경에서의 로깅 설정 가이드

## 개요

이 문서는 Vercel 운영 환경에서 효과적인 로깅을 설정하는 방법을 설명합니다.

## Vercel 환경 특징

### 1. 서버리스 환경
- 각 요청마다 새로운 함수 인스턴스
- 함수 실행 시간 제한 (최대 10초)
- 콜드 스타트 고려 필요

### 2. 로그 집계
- Vercel 대시보드에서 로그 확인 가능
- 실시간 로그 스트리밍
- 로그 검색 및 필터링

### 3. 환경 변수
```bash
VERCEL=1                    # Vercel 환경 여부
VERCEL_ENV=production       # 환경 (production, preview, development)
VERCEL_REGION=iad1          # 배포 지역
VERCEL_GIT_COMMIT_SHA=abc   # Git 커밋 해시
VERCEL_DEPLOYMENT_ID=123    # 배포 ID
```

## 로거 설정

### 1. 기본 설정 (`src/lib/logger.ts`)

```typescript
import pino from 'pino';

const isVercel = process.env.VERCEL === '1';
const isProduction = process.env.NODE_ENV === 'production';

const logger = pino({
  level: process.env.LOG_LEVEL || (isProduction ? 'info' : 'debug'),
  
  // Vercel 환경 정보 포함
  base: {
    env: process.env.NODE_ENV,
    vercel: isVercel,
    vercelEnv: process.env.VERCEL_ENV,
    vercelRegion: process.env.VERCEL_REGION,
    revision: process.env.VERCEL_GIT_COMMIT_SHA,
    deploymentId: process.env.VERCEL_DEPLOYMENT_ID,
  },
  
  // Vercel 최적화 설정
  ...(isVercel && {
    sync: false,
    buffer: true,
  }),
});
```

### 2. 환경별 로그 레벨

| 환경 | 로그 레벨 | 설명 |
|------|-----------|------|
| Development | debug | 모든 로그 출력 |
| Preview | info | 중요 로그만 출력 |
| Production | info | 중요 로그만 출력 |

## 로깅 모범 사례

### 1. 구조화된 로깅

```typescript
// ❌ 좋지 않은 예
proxyLogger.info('User login failed');

// ✅ 좋은 예
proxyLogger.info('User login failed', {
  userId: 'user123',
  reason: 'invalid_password',
  ip: '192.168.1.1',
  userAgent: request.headers.get('user-agent'),
});
```

### 2. 에러 로깅

```typescript
try {
  // 비즈니스 로직
} catch (error) {
  proxyLogger.error('Operation failed', {
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
    },
    context: {
      operation: 'user_login',
      userId: 'user123',
    },
    ...vercelHelpers.createVercelMetadata(),
  });
}
```

### 3. 성능 모니터링

```typescript
const startTime = Date.now();

// 비즈니스 로직 실행
await someOperation();

const duration = Date.now() - startTime;
proxyLogger.info('Operation completed', {
  operation: 'database_query',
  duration,
  durationMs: `${duration}ms`,
  ...vercelHelpers.createVercelMetadata(),
});
```

### 4. 요청/응답 로깅

```typescript
export async function handleRequest(request: NextRequest) {
  const startTime = Date.now();
  
  try {
    const response = await processRequest(request);
    
    const duration = Date.now() - startTime;
    proxyLogger.info('Request processed', {
      method: request.method,
      pathname: request.nextUrl.pathname,
      status: response.status,
      duration,
      ...vercelHelpers.createVercelMetadata(),
    });
    
    return response;
  } catch (error) {
    const duration = Date.now() - startTime;
    proxyLogger.error('Request failed', {
      method: request.method,
      pathname: request.nextUrl.pathname,
      duration,
      error: error.message,
      ...vercelHelpers.createVercelMetadata(),
    });
    
    throw error;
  }
}
```

## Vercel 대시보드에서 로그 확인

### 1. 실시간 로그
- Vercel 대시보드 → 프로젝트 → Functions 탭
- 실시간 로그 스트리밍 확인

### 2. 로그 검색
- 로그 레벨별 필터링 (error, warn, info, debug)
- 텍스트 검색
- 시간 범위 설정

### 3. 로그 분석
- 에러 발생 빈도
- 성능 지표
- 사용자 행동 패턴

## 환경 변수 설정

### 1. Vercel 대시보드에서 설정
```
Settings → Environment Variables
```

### 2. 로그 레벨 설정
```bash
LOG_LEVEL=debug    # 개발 환경
LOG_LEVEL=info     # 프로덕션 환경
```

### 3. 추가 설정
```bash
NODE_ENV=production
VERCEL_ENV=production
```

## 성능 최적화

### 1. 로그 버퍼링
```typescript
// Vercel 환경에서 로그 버퍼링 활성화
...(isVercel && {
  sync: false,
  buffer: true,
}),
```

### 2. 로그 레벨 조정
- 프로덕션에서는 `debug` 레벨 비활성화
- 중요한 비즈니스 로직만 `info` 레벨로 로깅

### 3. 로그 크기 최적화
- 불필요한 데이터 제거
- 민감한 정보 마스킹
- 로그 메시지 간소화

## 모니터링 및 알림

### 1. 에러 알림
- Vercel 대시보드에서 에러 알림 설정
- Slack, Discord 등으로 알림 전송

### 2. 성능 모니터링
- 함수 실행 시간 추적
- 메모리 사용량 모니터링
- 콜드 스타트 빈도 확인

### 3. 사용자 행동 분석
- 인기 있는 경로 추적
- 에러 발생 패턴 분석
- 성능 병목 지점 식별

## 문제 해결

### 1. 로그가 보이지 않는 경우
- 로그 레벨 확인
- Vercel 환경 변수 설정 확인
- 함수 배포 상태 확인

### 2. 로그 성능 문제
- 로그 레벨을 info로 상향 조정
- 불필요한 로그 제거
- 로그 버퍼링 활성화

### 3. 로그 크기 문제
- 로그 메시지 간소화
- 불필요한 컨텍스트 제거
- 로그 로테이션 설정

## 참고 자료

- [Vercel Functions Logging](https://vercel.com/docs/concepts/functions/function-logs)
- [Pino Documentation](https://getpino.io/)
- [Next.js Logging](https://nextjs.org/docs/advanced-features/debugging)
