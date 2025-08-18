# querypie-docs
QueryPie 제품의 Docs를 관리하는 Git Repository입니다.

# 오픈 전 다음 파일 TODO 보고 로직이나 값 고쳐서 나가야 함
- src/middleware.ts
- scripts/generate-sitemap/index.js
- src/app/[lang]/layout.tsx

## 기술 스택
- Next.js 15
- React.js 19
- Nextra 4
- TypeScript 5

## 로컬 실행 방법
- 파일 고치면 고친게 바로 웹브라우저에 반영되나, 좀 느립니다.
- `http://localhost:3000`
```shell
npm run dev
```

## 빌드 및 실행
- 빌드 후 실행하면 Production과 마찬가지로 빠릅니다.
- `http://localhost:3000`
```shell
npm run build
npm start
```

## 배포 - Local Environment
- `scripts/deploy/` 디렉토리로 이동합니다.
- `npm install` 명령으로 Vercel SDK 등을 node_modules 에 설치합니다.
- `index.js`가 필요로 하는 환경변수를 설정합니다.
  - VERCEL_TOKEN: vercel.com 의 계정에서 생성한 Token 을 지정합니다. Scope 은 QueryPie team 을 지정합니다.
  - VERCEL_TEAM_ID: QueryPie team 의 Team ID 를 지정합니다. Settings -> General 에서 확인할 수 있습니다.
  - TARGET_ENV: production, staging, preview 중 하나를 지정합니다.
  - BRANCH: branch 이름을 지정합니다.
- `index.js`를 실행합니다.
```shell
TARGET_ENV=preview BRANCH=main node ./index.js
```

## 배포 - GitHub Action
- [GitHub Actions](https://github.com/chequer-io/querypie-ai-docs/actions/workflows/deploy.yml) 에 접속합니다.
- `Run workflow`를 눌러서 알맞게 설정한 후 실행합니다.
  - 기본값: Production으로 배포할 거면 기본값으로 두고 나가면 됩니다. 
    - 배포할 브랜치: `main`
    - 타겟 환경: `production`
  - 타겟 환경을 `preview`로 바꾸면 별도로 빌드해서 별도의 서버를 띄울 수 있습니다.
    - Deploy 워크플로우의 로그를 보면 배포된 서버 주소를 확인 가능합니다.
- `preview` 환경 서버
  - 해당 브랜치가 삭제되면 제거되니 주의 바랍니다.
  - Global Protect VPN 연결이 된 상태에서만 접속이 가능합니다.
- 특이사항
  - 이 액션에서 사용한 Vercel의 Access Token은 임시로 Teddy 개인 계정의 토큰을 사용했습니다. 

### 배포 관련 화면 스크린샷
![deploy-action.png](docs/deploy-action.png)
![preview-deploy-url.png](docs/preview-deploy-url.png)