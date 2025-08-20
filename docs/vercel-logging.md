# Vercel 환경에서의 로깅 설정 가이드

## 개요

이 문서는 QueryPie 문서 사이트에서 Vercel 운영 환경에서 효과적인 로깅을 설정하고 사용하는 방법을 설명합니다. 현재 구현된 `src/lib/logger.ts`를 기반으로 실제 사용 사례와 함께 설명합니다.

## 현재 로거 구현 구조

### 1. 환경 감지 및 설정

```typescript
// src/lib/logger.ts
const isVercel = process.env.VERCEL === '1';
const isProduction = process.env.NODE_ENV === 'production';
const isDevelopment = process.env.NODE_ENV === 'development';
```

### 2. Pino 기반 로거 설정

```typescript
const logger = pino({
  // 로그 레벨 설정
  level: process.env.LOG_LEVEL || (isProduction ? 'info' : 'debug'),

  // 개발 환경에서 pretty 출력
  transport: isDevelopment && !isVercel ? {
    target: 'pino-pretty',
    options: {
      colorize: true,
      translateTime: 'SYS:standard',
      ignore: 'pid,hostname',
      messageFormat: '[{time}] {level} ({module}/{service}): {msg}',
      levelFirst: true,
    }
  } : undefined,

  // Vercel 환경 정보 포함
  base: {
    env: process.env.NODE_ENV,
    vercel: isVercel,
    vercelEnv: process.env.VERCEL_ENV,
    vercelRegion: process.env.VERCEL_REGION,
    revision: process.env.VERCEL_GIT_COMMIT_SHA || 'unknown',
    deploymentId: process.env.VERCEL_DEPLOYMENT_ID,
  },

  // 타임스탬프 포맷
  timestamp: () => `,"time":"${new Date().toISOString()}"`,

  // Vercel 최적화 설정
  ...(isVercel && {
    sync: false,
    buffer: true,
  }),
});
```

### 3. 모듈별 로거 생성

```typescript
// 모듈별 로거 인스턴스
export const proxyLogger = createDevLogger(logger, 'proxy');
export const appLogger = createDevLogger(logger, 'app');
export const middlewareLogger = createDevLogger(logger, 'middleware');
```

## 실제 사용 사례

### 1. Proxy 요청 처리 로깅

```typescript
// src/lib/proxy.ts
proxyLogger.info('Proxy request received', {
  method: request.method,
  pathname,
  search: request.nextUrl.search,
  clientIP
});

proxyLogger.info('No matching prefix found', { pathname });

proxyLogger.info('Proxy response received', {
  status: response.status,
  statusText: response.statusText,
  contentType: response.headers.get('content-type') || 'unknown'
});

proxyLogger.error('Proxy request failed', {
  error: error instanceof Error ? error.message : String(error),
  stack: error instanceof Error ? error.stack : undefined
});
```

### 2. 캐시 통계 로깅

```typescript
// src/lib/proxy.ts
proxyLogger.info('Cache statistics', {
  cacheHits,
  cacheMisses,
  totalRequests,
  hitRate: `${hitRate}%`,
  cacheSize: pathnameMatchCache.size()
});
```

### 3. Middleware 로깅

```typescript
// src/middleware.ts
middlewareLogger.debug('Middleware request', { 
  pathname: request.nextUrl.pathname,
  method: request.method 
});

middlewareLogger.debug('Handling robots.txt request');

middlewareLogger.debug('Proxy request detected, handling with proxy');

middlewareLogger.debug('Handling with Nextra middleware');
```

### 4. 에러 처리 및 디버깅 로깅

```typescript
// src/lib/proxy.ts
proxyLogger.info('Trailing slash redirect detected, making direct request', {
  currentUrl: request.nextUrl.href,
  location,
  status: response.status
});

proxyLogger.info('Direct request completed for trailing slash redirect', {
  status: directResponse.status,
  statusText: directResponse.statusText,
  contentType: directResponse.headers.get('content-type') || 'unknown'
});

proxyLogger.error('Direct request failed for trailing slash redirect', {
  error: error instanceof Error ? error.message : String(error),
  targetUrl
});
```

## 개발 환경 vs 프로덕션 환경

### 1. 개발 환경 로깅

개발 환경에서는 사용자 친화적인 포맷으로 로그가 출력됩니다:

```typescript
function formatLogForDevelopment(level: string, module: string, message: string, data?: Record<string, unknown>): string {
  const timestamp = new Date().toLocaleTimeString('ko-KR', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });

  const levelUpper = level.toUpperCase();
  let formattedLog = `[${timestamp}] ${levelUpper} (${module}): ${message}`;

  if (data && Object.keys(data).length > 0) {
    const dataStr = JSON.stringify(data).replace(/\s+/g, ' ');
    formattedLog += ` ${dataStr}`;
  }

  return formattedLog;
}
```

**출력 예시:**
```
[14:30:25] INFO (proxy): Proxy request received {"method":"GET","pathname":"/querypie/","clientIP":"127.0.0.1"}
[14:30:26] INFO (proxy): Proxy response received {"status":200,"contentType":"text/html"}
```

### 2. 프로덕션 환경 로깅

프로덕션 환경에서는 JSON 형태로 구조화된 로그가 출력됩니다:

```json
{
  "level": 30,
  "time": "2024-01-15T14:30:25.123Z",
  "pid": 123,
  "hostname": "vercel-function",
  "env": "production",
  "vercel": true,
  "vercelEnv": "production",
  "vercelRegion": "iad1",
  "revision": "abc123def",
  "deploymentId": "dep_123456",
  "module": "proxy",
  "msg": "Proxy request received",
  "method": "GET",
  "pathname": "/querypie/",
  "clientIP": "192.168.1.1"
}
```

## 로깅 모범 사례

### 1. 구조화된 데이터 로깅

```typescript
// ✅ 좋은 예
proxyLogger.info('Request processed', {
  method: request.method,
  pathname: request.nextUrl.pathname,
  status: response.status,
  duration: Date.now() - startTime,
  clientIP: getClientIP(request),
  userAgent: request.headers.get('user-agent')
});

// ❌ 좋지 않은 예
proxyLogger.info(`Request ${request.method} to ${request.nextUrl.pathname} processed`);
```

### 2. 에러 로깅

```typescript
proxyLogger.error('Operation failed', {
  error: error instanceof Error ? error.message : String(error),
  stack: error instanceof Error ? error.stack : undefined,
  context: {
    operation: 'proxy_request',
    pathname: request.nextUrl.pathname
  }
});
```

### 3. 성능 모니터링

```typescript
proxyLogger.info('Operation completed', {
  operation: 'proxy_request',
  duration,
  durationMs: `${duration}ms`
});
```

### 4. 디버그 로깅

```typescript
proxyLogger.debug('Cache hit for pathname', { 
  pathname, 
  cacheSize: pathnameMatchCache.size() 
});

proxyLogger.debug('URL similarity check', {
  url1, 
  url2, 
  normalized1, 
  normalized2, 
  isSimilar: normalized1 === normalized2
});
```

## Vercel 환경 변수

### 1. 자동 설정되는 환경 변수

```bash
VERCEL=1                    # Vercel 환경 여부
VERCEL_ENV=production       # 환경 (production, preview, development)
VERCEL_REGION=iad1          # 배포 지역
VERCEL_GIT_COMMIT_SHA=abc   # Git 커밋 해시
VERCEL_DEPLOYMENT_ID=123    # 배포 ID
```

### 2. 수동 설정 가능한 환경 변수

```bash
LOG_LEVEL=debug    # 개발 환경
LOG_LEVEL=info     # 프로덕션 환경
NODE_ENV=production
```

## Vercel 대시보드에서 로그 확인

### 1. 실시간 로그 스트리밍
- Vercel 대시보드 → 프로젝트 → Functions 탭
- 실시간으로 로그 확인 가능

### 2. 로그 검색 및 필터링
- 로그 레벨별 필터링 (error, warn, info, debug)
- 텍스트 검색
- 시간 범위 설정
- 환경별 필터링

### 3. 로그 분석
- 에러 발생 빈도 및 패턴
- 성능 지표 (응답 시간, 처리량)
- 사용자 행동 패턴
- 캐시 히트율 등

## 성능 최적화

### 1. 로그 레벨 조정
- 프로덕션에서는 `debug` 레벨 비활성화
- 중요한 비즈니스 로직만 `info` 레벨로 로깅
- 에러와 경고는 항상 로깅

### 2. 로그 버퍼링 (Vercel 환경)
```typescript
...(isVercel && {
  sync: false,    // 비동기 로깅
  buffer: true,   // 로그 버퍼링
}),
```

### 3. 로그 크기 최적화
- 불필요한 데이터 제거
- 민감한 정보 마스킹
- 로그 메시지 간소화

## 문제 해결

### 1. 로그가 보이지 않는 경우
- 로그 레벨 확인 (`LOG_LEVEL` 환경 변수)
- Vercel 환경 변수 설정 확인
- 함수 배포 상태 확인

### 2. 로그 성능 문제
- 로그 레벨을 `info`로 상향 조정
- 불필요한 `debug` 로그 제거
- 로그 버퍼링 활성화 확인

### 3. 로그 포맷 문제
- 개발 환경과 프로덕션 환경 구분 확인
- JSON 파싱 오류 확인
- 타임스탬프 포맷 확인

## 모니터링 및 알림

### 1. 에러 알림 설정
- Vercel 대시보드에서 에러 알림 설정
- Slack, Discord 등으로 알림 전송
- 에러 발생 빈도 임계값 설정

### 2. 성능 모니터링
- 함수 실행 시간 추적
- 메모리 사용량 모니터링
- 콜드 스타트 빈도 확인

### 3. 사용자 행동 분석
- 인기 있는 경로 추적
- 에러 발생 패턴 분석
- 성능 병목 지점 식별

## 참고 자료

- [Vercel Functions Logging](https://vercel.com/docs/concepts/functions/function-logs)
- [Pino Documentation](https://getpino.io/)
- [Next.js Logging](https://nextjs.org/docs/advanced-features/debugging)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
