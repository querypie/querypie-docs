# generate_toc.py 사용법 및 Python 환경 설정 안내

## 1. Python 가상환경(venv) 생성 및 필수 모듈 설치

```bash
# docs 디렉토리로 이동
cd docs

# Python 가상환경 생성 (venv)
python3 -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 필수 모듈 설치
pip install requests beautifulsoup4
```

## 2. generate_toc.py 사용법

`sitemap.xml` 파일이 있는 디렉토리에서 아래와 같이 실행합니다.

```bash
python generate_toc.py sitemap.xml
```

- `sitemap.xml` 파일을 읽어, 같은 디렉토리에 `urls.txt`, `titles.txt`, `breadcrumbs.txt` 파일을 생성합니다.
- 각 파일의 내용:
  - `urls.txt`: sitemap.xml에 포함된 모든 URL 목록 (한 줄에 하나)
  - `titles.txt`: 각 URL에서 추출한 문서 제목 (한 줄에 하나, 줄바꿈 없음)
  - `breadcrumbs.txt`: 각 URL에서 추출한 탐색 경로 (breadcrumb, /로 구분)
- 실행 중 각 URL의 처리 상태가 화면에 출력됩니다.
- 처리 완료 후, 문서 수와 오류 건수, 오류 유형별 건수가 출력됩니다.

## 3. 가상환경 비활성화

작업이 끝난 후 가상환경을 비활성화하려면 아래 명령어를 입력하세요.

```bash
deactivate
``` 