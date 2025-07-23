# Python 환경 설정과 Python 스크립트 사용법 안내

## Python 가상환경(venv) 생성 및 필수 모듈 설치

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

## generate_toc.py

`sitemap.xml` 파일을 읽어, 같은 디렉토리에 `urls.txt`, `titles.txt`, `breadcrumbs.txt` 파일을 생성합니다.
- 각 파일의 내용:
  - `urls.txt`: sitemap.xml에 포함된 모든 URL 목록 (한 줄에 하나)
  - `titles.txt`: 각 URL에서 추출한 문서 제목 (한 줄에 하나, 줄바꿈 없음)
  - `breadcrumbs.txt`: 각 URL에서 추출한 탐색 경로 (breadcrumb, /로 구분)
- 실행 중 각 URL의 처리 상태가 화면에 출력됩니다.
- 처리 완료 후, 문서 수와 오류 건수, 오류 유형별 건수가 출력됩니다.

`sitemap.xml` 파일이 있는 디렉토리에서 아래와 같이 실행합니다.
```bash
python generate_toc.py sitemap.xml
```

## save_files_from_sitemap.py

`sitemap.xml` 파일에서 URL을 추출하여 해당 URL의 HTML 파일을 저장하는 스크립트입니다.
1.html, 2.html, ... 형식으로 URL 의 HTML 파일을 저장합니다. html 파일에 첨부된 image 파일도 함께 저장하는데, image 파일은 `1/`, `2/` 등의 디렉토리에 저장됩니다.

## generate_breadcrumbs_revised.py

`generate_breadcrumbs_revised.py`는 문서 탐색 경로(breadcrumbs)를 개선하는 스크립트입니다. 이 스크립트는 다음과 같은 기능을 수행합니다:

- 입력 파일로 `breadcrumbs.txt`, `titles.txt`, `titles.en.txt`를 사용합니다.
- 한국어 제목과 영어 제목을 매핑하여 URL 슬러그를 생성합니다.
- 상대 경로로 된 탐색 경로를 절대 경로로 변환합니다.
- 각 문서의 탐색 경로에 현재 페이지 정보를 추가합니다.
- 결과를 `breadcrumbs.revised.txt` 파일로 출력합니다.

실행 방법:
```bash
python generate_breadcrumbs_revised.py \
  --breadcrumbs breadcrumbs.txt \
  --titles titles.txt \
  --titles_en titles.en.txt \
  --output breadcrumbs.revised.txt
```

## generate_ko_contents.py

`generate_ko_contents.py`는 HTML 파일을 MDX 형식으로 변환하여 한국어 문서를 생성하는 스크립트입니다. 이 스크립트는 다음과 같은 기능을 수행합니다:

- 탐색 경로(breadcrumbs)를 분석하여 출력 파일의 경로와 이름을 결정합니다.
- HTML 파일을 MDX 형식으로 변환합니다 (pandoc 사용).
- HTML 파일에 포함된 이미지를 찾아 새 이름으로 복사하고 참조를 업데이트합니다.
- 이미지는 유형(스크린샷/일반 이미지)에 따라 다른 이름 형식으로 저장됩니다.

실행 방법:
```bash
python generate_ko_contents.py \
  --breadcrumbs breadcrumbs.revised.txt \
  --html_dir html_files_directory \
  --output_dir src/content/ko
```

## 가상환경 비활성화

작업이 끝난 후 가상환경을 비활성화하려면 아래 명령어를 입력하세요.

```bash
deactivate
```

