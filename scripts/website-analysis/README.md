# QueryPie Docs 웹사이트 분석 툴

이 디렉토리는 QueryPie Docs 웹사이트의 상태를 분석하는 자동화된 툴들을 포함합니다.

## 📋 개요

웹사이트 분석 툴은 다음 사항들을 자동으로 검사합니다:

1. **웹페이지 탐색**: 20개 이상의 문서 페이지를 자동으로 탐색
2. **404 에러 검사**: 이미지, CSS 등 리소스 파일의 404 에러 감지
3. **외부 연결 검사**: docs.querypie.com 서버로의 직접 연결 감지

## 🛠️ 설치 및 설정

### 필수 요구사항
- Node.js 18+ 
- npm 또는 yarn

### 설치
```bash
# scripts/website-analysis 디렉토리로 이동
cd scripts/website-analysis

# 의존성 설치
npm install
```

## 📁 파일 구조

```
scripts/website-analysis/
├── README.md                    # 이 파일
├── analyze_website.js           # 기본 분석 툴
├── analyze_website_enhanced.js  # 향상된 분석 툴 (권장)
└── package.json                 # 의존성 관리 (선택사항)
```

## 🚀 사용법

### 1. 독립 실행 (권장)
```bash
# scripts/website-analysis 디렉토리로 이동
cd scripts/website-analysis

# 의존성 설치 (최초 1회)
npm install

# 기본 분석 툴 실행
npm run analyze:basic

# 향상된 분석 툴 실행 (권장)
npm run analyze
```

### 2. 프로젝트 루트에서 실행
```bash
# 프로젝트 루트에서 실행
npm run analyze
npm run analyze:basic
```

## 📊 분석 결과

### 출력 파일
- `scripts/website-analysis/website_analysis_report.json`: 기본 분석 결과
- `scripts/website-analysis/enhanced_website_analysis_report.json`: 향상된 분석 결과

### 콘솔 출력 예시
```
🌐 향상된 웹사이트 분석을 시작합니다...
📡 대상 URL: http://localhost:3000/ko/querypie-manual

📄 페이지 분석 중: http://localhost:3000/ko/querypie-manual
✅ 성공: http://localhost:3000/ko/querypie-manual
🔗 발견된 링크 수: 9

============================================================
📊 향상된 웹사이트 분석 결과
============================================================
📄 총 분석 페이지: 30
✅ 성공한 페이지: 29
❌ 오류 페이지: 1
🔗 리소스 오류: 0
🌐 외부 연결: 0
```

## 🔧 툴별 특징

### analyze_website.js (기본)
- 고정된 경로 목록을 기반으로 분석
- 빠른 실행
- 제한된 페이지 수 분석

### analyze_website_enhanced.js (향상된)
- 동적 링크 탐색
- 최대 30개 페이지까지 분석
- 큐 기반 링크 처리
- 상세한 분석 결과
- **권장 사용**

## ⚙️ 설정 옵션

### 기본 설정
- **대상 URL**: `http://localhost:3000` (또는 3001, 자동 감지)
- **최대 페이지 수**: 30개 (테스트용 제한)
- **대기 시간**: 1초 (페이지 간)
- **브라우저 모드**: Desktop mode (1920x1080)
- **User Agent**: Chrome Desktop (Mac)

### 설정 변경
`analyze_website_enhanced.js` 파일에서 다음 값들을 수정할 수 있습니다:

```javascript
class EnhancedWebsiteAnalyzer {
  constructor(baseUrl = null) {
    // ...
    this.maxPages = 30; // 최대 분석 페이지 수
  }
}

// Desktop mode 설정
async setupDesktopMode(page) {
  await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
  await page.setViewport({
    width: 1920,
    height: 1080,
    deviceScaleFactor: 1,
    isMobile: false,
    hasTouch: false,
    isLandscape: false
  });
}

// 환경 변수로 포트 설정
export PORT=3001
```

## 🔍 분석 항목

### 1. 웹페이지 탐색
- ✅ 20개 이상의 문서 페이지 자동 탐색
- ✅ 각 페이지의 링크 수 카운트
- ✅ 페이지 로드 상태 확인

### 2. 404 에러 검사
- ✅ 이미지 파일 (.png, .jpg, .gif 등)
- ✅ CSS 파일 (.css)
- ✅ JavaScript 파일 (.js)
- ✅ 기타 리소스 파일

### 3. 외부 연결 검사
- ✅ docs.querypie.com으로의 직접 연결 감지
- ✅ 프록시 시스템 정상 작동 확인

## 📈 결과 해석

### 성공 지표
- **성공한 페이지**: 29/30 (96.7%)
- **리소스 오류**: 0개
- **외부 연결**: 0개

### 문제 지표
- **오류 페이지**: 1개 이상
- **리소스 오류**: 1개 이상
- **외부 연결**: 1개 이상

## 🐛 문제 해결

### 일반적인 문제들

1. **Puppeteer 설치 실패**
   ```bash
   npm install puppeteer --force
   ```

2. **포트 충돌**
   - 기본 포트 3000이 사용 중인 경우 3001로 변경
   - `baseUrl` 설정 확인

3. **메모리 부족**
   - `maxPages` 값을 줄여서 실행
   - 시스템 리소스 확인

### 로그 확인
- 콘솔 출력에서 상세한 진행 상황 확인
- JSON 결과 파일에서 상세 분석 결과 확인

## 🔄 정기 실행

### 수동 실행
```bash
# 개발 중 정기적으로 실행하여 문제 감지
node scripts/website-analysis/analyze_website_enhanced.js
```

### 자동화 (선택사항)
```bash
# 프로젝트 루트의 package.json에 이미 추가됨
npm run analyze
npm run analyze:basic

# 또는 독립 실행
cd scripts/website-analysis
npm run analyze
```

## 📝 주의사항

1. **서버 실행 필요**: 분석 전에 `npm run dev`로 서버가 실행 중인지 확인
2. **브라우저 자동 실행**: Puppeteer가 Chrome 브라우저를 자동으로 실행합니다
3. **네트워크 사용**: 분석 중 네트워크 트래픽이 발생할 수 있습니다
4. **시간 소요**: 30개 페이지 분석 시 약 1-2분 소요

## 🤝 기여

분석 툴 개선이나 새로운 기능 추가 시 다음 사항을 고려해주세요:

1. 기존 기능과의 호환성 유지
2. 상세한 로그 출력
3. 에러 처리 강화
4. 성능 최적화

---

**마지막 업데이트**: 2025-08-20
**버전**: 1.0.0
