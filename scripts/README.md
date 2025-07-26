# Python 환경 설정과 Python 스크립트 사용법 안내

## Python 가상환경(venv) 생성 및 필수 모듈 설치

```bash
# 프로젝트 루트 디렉토리로 이동
cd querypie-docs

# Python 가상환경 생성 (venv)
python3 -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 필수 모듈 설치
pip install requests beautifulsoup4 pyyaml
```

## 데이터 수집, 변환 절차의 개요

1. `docs/latest-ko-confluence/`에 Confluence 문서 데이터를 저장합니다.
    - 문서의 목록인 `list.txt`를 저장합니다.
    - 개별 문서마다 `<page_id>/page.yaml`, `<page_id>/page.xhtml`을 저장합니다.
    - `pages_of_confluence.py`를 사용합니다.
2. `docs/latest-ko-confluence/list.en.txt`를 생성합니다.
   - `list.en.txt`는 `list.txt`를 영어로 번역한 것입니다.
   - `translate_titles.py`를 사용합니다.
3. `scripts/xhtml2markdown.sh`를 생성합니다.
4. - `generate_commands_for_xhtml2markdown.py`를 사용합니다.
4. `src/content/ko/` 아래에 MDX 문서를 생성합니다.
    - `scripts/xhtml2markdown.sh`를 실행하면, MDX 문서가 생성됩니다.
    - `docs/latest-ko-confluence/` 아래의 `<page_id>/page.xhtml`을 입력 데이터로 사용합니다.

## 데이터 수집 및 변환 절차 상세 안내

### 1. Confluence 문서 데이터 수집 (pages_of_confluence.py)

`pages_of_confluence.py`는 Confluence REST API를 이용하여 지정한 문서와 그 하위 페이지들을 수집하여 저장하는 스크립트입니다. 
이 스크립트는 다음과 같은 기능을 수행합니다:

- 각 페이지의 ID, 탐색 경로(breadcrumbs), 제목을 탭으로 구분된 형식으로 출력합니다.
- 각 페이지 ID에 대한 디렉토리를 생성하고 다음 파일을 저장합니다:
  - XHTML 형식의 문서 내용 (`page.xhtml`)
  - 페이지 메타데이터 (`page.yaml`)
  - 첨부 파일(있는 경우)

실행 방법:
```bash
# 로컬에서 pages_of_confluence.py 개선 과정에서 사용하는 명령
python scripts/pages_of_confluence.py --local >docs/latest-ko-confluence/list.txt

# 기본 설정으로 실행
python scripts/pages_of_confluence.py

# 로컬에 저장한 데이터파일을 이용해, 목록을 생성하고, page.xhtml 을 업데이트
python scripts/pages_of_confluence.py --local

# list.txt 에 파일 목록을 저장
python scripts/pages_of_confluence.py >list.txt

# 특정 페이지 ID와 공간 키 지정
python scripts/pages_of_confluence.py --page-id 123456789 --space-key DOCS

# 인증 정보 지정
python scripts/pages_of_confluence.py --email user@example.com --api-token your-api-token

# 첨부파일을 다운로드
python scripts/pages_of_confluence.py --attachments

# 로그 레벨 설정
python scripts/pages_of_confluence.py --log-level DEBUG
```

실행 결과:
- `docs/latest-ko-confluence/` 디렉토리에 문서 데이터가 저장됩니다.
- 각 페이지 ID에 해당하는 디렉토리에 `page.yaml`과 `page.xhtml` 파일이 저장됩니다.
- `>list.txt`로 stdout 을 redirect 하면, `list.txt` 파일에 문서 목록이 저장됩니다.

### 2. 문서 제목 번역 (translate_titles.py)

`translate_titles.py`는 문서 제목을 번역하여 `list.en.txt` 파일을 생성하는 스크립트입니다. 
이 스크립트는 `list.txt` 파일을 입력으로 사용하여 한국어 제목을 영어로 번역합니다.

> 참고: 이 스크립트는 현재 하드코딩된 파일 경로를 사용합니다:
> - 입력 파일: docs/latest-ko-confluence/list.txt
> - 출력 파일: docs/latest-ko-confluence/list.en.txt
> - 번역 파일: docs/korean-titles-translations.txt

실행 방법:
```bash
# 스크립트 실행
python scripts/translate_titles.py
```

실행 결과:
- `docs/latest-ko-confluence/list.en.txt` 파일이 생성됩니다.
- 이 파일은 원본 `list.txt`와 동일한 형식이지만 제목이 영어로 번역되어 있습니다.

### 3. XHTML을 Markdown으로 변환하기 위한 명령어 생성 (generate_commands_for_xhtml2markdown.py)

`generate_commands_for_xhtml2markdown.py`는 Confluence XHTML 파일을 Markdown으로 변환하기 위한 명령어를 생성하는 스크립트입니다. 
이 스크립트는 `list.en.txt` 파일을 읽어 각 문서에 대한 변환 명령어를 생성합니다.

실행 방법:
```bash
# 기본 설정으로 실행하여 xhtml2markdown.sh 파일 생성
python scripts/generate_commands_for_xhtml2markdown.py docs/latest-ko-confluence/list.en.txt > scripts/xhtml2markdown.sh

# Confluence 디렉토리 지정
python scripts/generate_commands_for_xhtml2markdown.py docs/latest-ko-confluence/list.en.txt --confluence-dir docs/custom-path/ > scripts/xhtml2markdown.sh

# 출력 디렉토리 지정
python scripts/generate_commands_for_xhtml2markdown.py docs/latest-ko-confluence/list.en.txt --output-dir src/content/custom-path/ > scripts/xhtml2markdown.sh

# 생성된 스크립트에 실행 권한 부여
chmod +x scripts/xhtml2markdown.sh
```

실행 결과:
- `scripts/xhtml2markdown.sh` 파일이 생성됩니다.
- 이 파일은 각 XHTML 파일을 Markdown으로 변환하기 위한 명령어들을 포함하고 있습니다.

### 4. XHTML을 Markdown으로 변환 (xhtml2markdown.sh)

`xhtml2markdown.sh`는 `generate_commands_for_xhtml2markdown.py`에 의해 생성된 스크립트로, 각 XHTML 파일을 Markdown으로 변환하는 명령어들을 실행합니다. 
이 스크립트는 `confluence_xhtml_to_markdown.py`를 사용하여 변환 작업을 수행합니다.

실행 방법:
```bash
# 스크립트 실행
./scripts/xhtml2markdown.sh
```

실행 결과:
- `src/content/ko/` 디렉토리에 MDX 파일들이 생성됩니다.
- 각 MDX 파일은 원본 XHTML 파일의 내용을 Markdown 형식으로 변환한 것입니다.

## Confluence xhtml 을 Markdown 으로 변환하기

### confluence_xhtml_to_markdown.py

`confluence_xhtml_to_markdown.py`는 Confluence XHTML 내보내기를 깔끔한 Markdown으로 변환하는 스크립트입니다.
이 스크립트는 다음과 같은 특수 케이스를 처리합니다:

- 코드 블록의 CDATA 섹션
- colspan 및 rowspan 속성이 있는 테이블
- 구조화된 매크로 및 기타 Confluence 특정 요소

실행 방법:
```bash
# 기본 실행
python scripts/confluence_xhtml_to_markdown.py input_file.xhtml output_file.md

# 로그 레벨 설정
python scripts/confluence_xhtml_to_markdown.py input_file.xhtml output_file.md --log-level debug
```

실행 결과:
- 지정된 출력 파일에 Markdown 형식으로 변환된 내용이 저장됩니다.
- 이 스크립트는 일반적으로 `xhtml2markdown.sh`에 의해 자동으로 호출됩니다.

### Makefile (confluence_xhtml_to_markdown.py 테스트용)

`Makefile`은 `confluence_xhtml_to_markdown.py` 스크립트의 테스트를 자동화하기 위한 파일입니다. 이 Makefile은 다음과 같은 기능을 제공합니다:

- 모든 테스트 케이스 실행
- 특정 테스트 케이스 실행
- 디버그 로그 레벨로 테스트 실행
- 테스트 출력 파일 정리

실행 방법:
```bash
# 모든 테스트 실행
cd scripts
make test

# 특정 테스트 실행
cd scripts
make test-one TEST_ID=<test_id>

# 디버그 로그 레벨로 모든 테스트 실행
cd scripts
make debug

# 디버그 로그 레벨로 특정 테스트 실행
cd scripts
make debug-one TEST_ID=<test_id>

# 출력 파일 정리
cd scripts
make clean

# 도움말 표시
cd scripts
make help
```

테스트 케이스는 `scripts/tests/confluence_xhtml_to_markdown/testcases/` 디렉토리에 있으며, 각 테스트 케이스는 다음 파일을 포함합니다:
- `page.xhtml`: 입력 XHTML 파일
- `expected.mdx`: 예상 출력 MDX 파일
- `output.mdx`: 테스트 실행 시 생성되는 실제 출력 파일

## 기타 유틸리티 스크립트

### repeat_npm_run_build.sh

`repeat_npm_run_build.sh`는 빌드 과정에서 문제가 되는 MDX 파일을 자동으로 식별하고 제거하면서 `npm run build` 명령을 반복적으로 실행하는 스크립트입니다. 이 스크립트는 다음과 같은 기능을 수행합니다:

- 빌드 오류 메시지에서 문제가 되는 MDX 파일 경로를 추출합니다.
- 문제가 되는 MDX 파일을 자동으로 삭제합니다.
- 최대 10번까지 빌드를 반복 시도합니다.
- 빌드가 성공하거나 최대 시도 횟수에 도달하면 종료합니다.

실행 방법:
```bash
# 기본 빌드 모드로 실행
./scripts/repeat_npm_run_build.sh

# 문제 파일 추출 모드로 실행
./scripts/repeat_npm_run_build.sh extract
```

실행 결과:
- 빌드 과정에서 문제가 되는 MDX 파일이 자동으로 삭제됩니다.
- 빌드가 성공하면 성공 메시지와 함께 종료됩니다.
- 최대 시도 횟수에 도달해도 빌드가 실패하면 오류 메시지와 함께 종료됩니다.

### deploy 디렉토리 (Vercel 배포 스크립트)

`deploy` 디렉토리에는 문서 사이트를 Vercel에 배포하기 위한 Node.js 스크립트가 포함되어 있습니다:

#### index.js
Vercel SDK를 사용하여 문서 사이트를 배포하는 스크립트입니다. 다음과 같은 기능을 수행합니다:
- 지정된 브랜치의 코드를 Vercel에 배포합니다.
- 배포 상태를 확인하고 결과를 보고합니다.
- 프로덕션 또는 프리뷰 환경에 배포할 수 있습니다.

#### delete-deploy.js
Vercel에서 프리뷰 배포를 삭제하는 스크립트입니다. 다음과 같은 기능을 수행합니다:
- 지정된 브랜치의 프리뷰 배포를 찾습니다.
- 찾은 프리뷰 배포를 삭제합니다.

### generate-sitemap 디렉토리 (사이트맵 생성 스크립트)

`generate-sitemap` 디렉토리에는 웹사이트의 sitemap.xml 파일을 생성하기 위한 Node.js 스크립트가 포함되어 있습니다:

#### index.js
MDX 파일을 스캔하여 sitemap.xml 파일을 생성하는 스크립트입니다. 다음과 같은 기능을 수행합니다:
- `src/content` 디렉토리에서 MDX 파일을 찾습니다.
- 각 MDX 파일에 대한 URL을 생성합니다.
- 생성된 URL을 sitemap.xml 형식으로 저장합니다.
- 여러 언어(en, ko, ja)를 지원합니다.

## 가상환경 비활성화

작업이 끝난 후 가상환경을 비활성화하려면 아래 명령어를 입력하세요.

```bash
deactivate
```