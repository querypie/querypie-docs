# Container 환경에서 실행하기

GitHub Action 을 이용한 자동화를 위해 Container 환경을 제공합니다. 다음의 작업을 수행할 수 있습니다.

1. Container Image 빌드
    - [docker.io/querypie/confluence-mdx:latest](https://hub.docker.com/r/querypie/confluence-mdx) 이미지를 빌드합니다.
2. 한국어 MDX 파일을 업데이트합니다.
    - [QueryPie ACP Manual](https://querypie.atlassian.net/wiki/spaces/QM/pages/608501837/QueryPie+Docs) 의 문서를 
      한국어 MDX 문서로 변환하여 업데이트합니다.

## Container Image 빌드하기

```bash
# confluence-mdx 디렉토리로 이동
cd querpie-docs/confluence-mdx

# cache 디렉토리에 데이터를 채우기
# - 기존 confluence-mdx:latest 이미지에 포함된 /workdir/var/ 아래의 데이터를 cache/ 에 옮깁니다.
# - var/ 아래의 <page_id> 디렉토리의 데이터를 옮기는 것과 동등합니다.
setup-cache.sh

# confluence-mdx:latest 이미지를 빌드하기
docker compose --progress=plain build
```

cache/ 디렉토리를 채우는 경우,  bin/fetch_cli.py 를 실행하여 첨부파일을 내려받을 때 캐시로 작동합니다.

## 한국어 MDX 파일을 업데이트하기

최근 1주일 Confluence Space 에서 업데이트된 문서를 한국어 MDX 로 변환합니다.
```bash
# --recent 옵션이 기본 적용됩니다.
docker compose --progress=plain run --rm confluence-mdx full
docker compose --progress=plain run --rm confluence-mdx full --recent
```

전체 Confluence Space 문서를 내려받아 한국어 MDX 로 변환합니다.
```bash
# --remote: Confluence API 를 호출하여 var/ 데이터를 업데이트합니다.
docker compose --progress=plain run --rm confluence-mdx full --remote
# --attachments: 첨부파일을 내려받아 변환하는 작업을 포함합니다.
docker compose --progress=plain run --rm confluence-mdx full --remote --attachments
```

Confluence API 를 호출하지 않고, `var/`에 저장된 데이터를 이용하여 한국어 MDX 전체를 변환합니다.
```bash
# --local: Confluence API 를 호출하지 않습니다.
docker compose --progress=plain run --rm confluence-mdx full --local
```

## GitHub Action 설정

- [build-and-push-docker-image.yml](../.github/workflows/build-and-push-docker-image.yml)
  - Container Image 를 빌드하고, DockerHub Registry 에 push 합니다.
- [generate-mdx-from-confluence.yml](../.github/workflows/generate-mdx-from-confluence.yml)
  - Confluence Space 문서를 한국어 MDX 로 변환합니다.
  - `--remote`, `--local` 등 옵션을 선택하여 지정할 수 있습니다.

# Python 환경 설정과 Python 스크립트 사용법 안내

Python 스크립트의 기능을 개선하거나 디버깅할 때에는, Python 가상환경(venv)에서 실행하는 것이 좋습니다.

## Python 가상환경(venv) 생성 및 필수 모듈 설치

```bash
# confluence-mdx 디렉토리로 이동
cd querypie-docs/confluence-mdx

# Python 가상환경 생성 (venv)
python3 -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 필수 모듈 설치
pip3 install requests beautifulsoup4 pyyaml
```

## 데이터 수집, 변환 절차의 개요

1. `confluence-mdx/var/`에 Confluence 문서 데이터를 저장합니다.
    - 문서의 목록인 `list.txt`를 저장합니다.
    - 개별 문서마다 `<page_id>/page.yaml`, `<page_id>/page.xhtml`을 저장합니다.
    - `fetch_cli.py`를 사용합니다.
2. `confluence-mdx/var/list.en.txt`를 생성합니다.
   - `list.en.txt`는 `list.txt`를 영어로 번역한 것입니다.
   - `translate_titles.py`를 사용합니다.
3. `confluence-mdx/bin/generated/xhtml2markdown.ko.sh`를 생성합니다.
   - `generate_commands_for_xhtml2markdown.py`를 사용합니다.
4. `src/content/ko/` 아래에 MDX 문서를 생성합니다.
   - `confluence-mdx/bin/generated/xhtml2markdown.ko.sh`를 실행하면, MDX 문서가 생성됩니다.
   - `confluence-mdx/var/` 아래의 `<page_id>/page.xhtml`을 입력 데이터로 사용합니다.

무작정 따라해 보기
```bash
$ cd confluence-mdx
$ python3 -m venv venv
$ source venv/bin/activate
$ pip3 install requests beautifulsoup4 pyyaml
$ bin/fetch_cli.py --remote --attachments # 2시간 가량, 시간이 오래 걸립니다.
$ bin/translate_titles.py
$ bin/generate_commands_for_xhtml2markdown.py var/list.en.txt >bin/generated/xhtml2markdown.ko.sh
$ bin/generated/xhtml2markdown.ko.sh
# 이제, 변환된 또는 변경된 MDX 파일을 src/content/ko 아래에서 확인할 수 있습니다.
```

## 데이터 수집 및 변환 절차 상세 안내

> **주의:** 아래의 모든 스크립트 실행 예시는 **venv 가상환경이 활성화된 상태**에서 실행해야 합니다.
> ```bash
> cd querypie-docs/confluence-mdx
> source venv/bin/activate  # venv 활성화 필수
> ```

### 1. Confluence 문서 데이터 수집 (fetch_cli.py)

`fetch_cli.py`는 Confluence REST API를 이용하여 지정한 문서와 그 하위 페이지들을 수집하여 저장하는 스크립트입니다. 
이 스크립트는 다음과 같은 기능을 수행합니다:

- 각 페이지의 ID, 탐색 경로(breadcrumbs), 제목을 탭으로 구분된 형식으로 출력합니다.
- 각 페이지 ID에 대한 디렉토리를 생성하고 다음 파일을 저장합니다:
  - XHTML 형식의 문서 내용 (`page.xhtml`)
  - 페이지 메타데이터 (`page.yaml`)
  - 첨부 파일(있는 경우)

실행 방법:
```bash
# 기본 설정으로 실행 - Confluence API 를 호출하고, 그 결과를 var/ 아래에 저장합니다.
bin/fetch_cli.py

# API 호출과 함께, 첨부파일을 다운로드하여 저장합니다.
# 첨부파일 변경시에, 이 옵션을 추가하여 실행합니다. 
# 또는 fetch_cli.py 를 처음 실행하는 경우에 사용합니다.
bin/fetch_cli.py --attachments

# 로컬에 저장한 데이터파일을 이용해, 목록을 생성하고, page.xhtml 을 업데이트
bin/fetch_cli.py --local

# 로컬에서 fetch_cli.py 개선 과정에서, 반복실행할 때 사용하는 명령입니다.
# 또는, var/list.txt 를 업데이트하고자 하는 경우에 실행합니다.
bin/fetch_cli.py --local >var/list.txt

# 특정 페이지 ID와 하위 문서를 내려받습니다. 첨부파일을 포함하여 내려받습니다.
# 일부 문서만 변경한 경우, 해당 문서와 하위 페이지를 API 로 내려받아 저장할 때 사용합니다.
bin/fetch_cli.py --page-id 123456789 --attachments
```

사실상 사용하지 않음. 참고용 기능:
```bash
# 특정 페이지 ID와 하위 문서를 내려받습니다.
bin/fetch_cli.py --page-id 123456789

# 특정 페이지 ID와 공간 키 지정하여, 실행합니다.
bin/fetch_cli.py --page-id 123456789 --space-key DOCS

# 인증 정보 지정
bin/fetch_cli.py --email user@example.com --api-token your-api-token

# 로그 레벨 설정
bin/fetch_cli.py --log-level DEBUG
```

실행 결과:
- `var/` 디렉토리에 문서 데이터가 저장됩니다.
- 각 페이지 ID에 해당하는 디렉토리에 `page.yaml`과 `page.xhtml` 파일이 저장됩니다.
- `>list.txt`로 stdout 을 redirect 하면, `list.txt` 파일에 문서 목록이 저장됩니다.

### 2. 문서 제목 번역 (translate_titles.py)

`translate_titles.py`는 문서 제목을 번역하여 `list.en.txt` 파일을 생성하는 스크립트입니다. 
이 스크립트는 `list.txt` 파일을 입력으로 사용하여 한국어 제목을 영어로 번역합니다.

> 참고: 이 스크립트는 현재 하드코딩된 파일 경로를 사용합니다:
> - 입력 파일: var/list.txt
> - 출력 파일: var/list.en.txt
> - 번역 파일: etc/korean-titles-translations.txt

실행 방법:
```bash
# 스크립트 실행
bin/translate_titles.py
```

실행 결과:
- `var/list.en.txt` 파일이 생성됩니다.
- 이 파일은 원본 `list.txt`와 동일한 형식이지만 제목이 영어로 번역되어 있습니다.
- 만일, list.en.txt 에 영어로 번역되지 않은 한국어 문서 제목이 나타나는 경우, etc/korean-titles-translations.txt 를 보완하여,
  list.en.txt 가 영어로 잘 번역될 수 있도록, 수정하여야 합니다.

### 3. XHTML을 Markdown으로 변환하기 위한 명령어 생성 (generate_commands_for_xhtml2markdown.py)

`generate_commands_for_xhtml2markdown.py`는 Confluence XHTML 파일을 Markdown으로 변환하기 위한 명령어를 생성하는 스크립트입니다. 
이 스크립트는 `list.en.txt` 파일을 읽어 각 문서에 대한 변환 명령어를 생성합니다.

실행 방법:
```bash
# 기본 설정으로 실행하여 xhtml2markdown.ko.sh 파일 생성
bin/generate_commands_for_xhtml2markdown.py var/list.en.txt >bin/generated/xhtml2markdown.ko.sh
```

사실상 사용하지 않음. 참고용 기능:
```bash
# Confluence 디렉토리 지정
bin/generate_commands_for_xhtml2markdown.py var/list.en.txt --confluence-dir var/ >bin/generated/xhtml2markdown.ko.sh

# 출력 디렉토리 지정
bin/generate_commands_for_xhtml2markdown.py var/list.en.txt --output-dir target/content/custom-path/ >bin/generated/xhtml2markdown.ko.sh

# 생성된 스크립트에 실행 권한 부여
chmod +x bin/generated/xhtml2markdown.ko.sh
```

실행 결과:
- `bin/generated/xhtml2markdown.ko.sh` 파일이 생성됩니다.
- 이 파일은 각 XHTML 파일을 Markdown으로 변환하기 위한 명령어들을 포함하고 있습니다.

### 4. XHTML을 Markdown으로 변환 (xhtml2markdown.ko.sh)

`xhtml2markdown.ko.sh`는 `generate_commands_for_xhtml2markdown.py`에 의해 생성된 스크립트로, 각 XHTML 파일을 Markdown으로 변환하는 명령어들을 실행합니다. 
이 스크립트는 `converter/cli.py`를 사용하여 변환 작업을 수행합니다.

실행 방법:
```bash
# 스크립트 실행
bin/generated/xhtml2markdown.ko.sh
```

실행 결과:
- `target/ko/` 디렉토리에 MDX 파일들이 생성됩니다. `target/public/` 디렉토리에 첨부파일에 저장됩니다.
- 각 MDX 파일은 원본 XHTML 파일의 내용을 Markdown 형식으로 변환한 것입니다.

## Confluence xhtml 을 Markdown 으로 변환하기

### converter/cli.py

`converter/cli.py`는 Confluence XHTML 내보내기를 깔끔한 Markdown으로 변환하는 스크립트입니다.
이 스크립트는 다음과 같은 특수 케이스를 처리합니다:

- 코드 블록의 CDATA 섹션
- colspan 및 rowspan 속성이 있는 테이블
- 구조화된 매크로 및 기타 Confluence 특정 요소

실행 방법:
```bash
# 기본 실행
bin/converter/cli.py input_file.xhtml output_file.md

# 로그 레벨 설정
bin/converter/cli.py input_file.xhtml output_file.md --log-level debug
```

실행 결과:
- 지정된 출력 파일에 Markdown 형식으로 변환된 내용이 저장됩니다.
- 이 스크립트는 일반적으로 `xhtml2markdown.ko.sh`에 의해 자동으로 호출됩니다.

### Makefile (converter/cli.py 테스트용)

`Makefile`은 `converter/cli.py` 스크립트의 테스트를 자동화하기 위한 파일입니다. 이 Makefile은 다음과 같은 기능을 제공합니다:

- 모든 테스트 케이스 실행
- 특정 테스트 케이스 실행
- 디버그 로그 레벨로 테스트 실행
- 테스트 출력 파일 정리

실행 방법:
```bash
# 모든 테스트 실행
cd tests
make test

# 특정 테스트 실행
cd tests
make test-one TEST_ID=<test_id>

# 디버그 로그 레벨로 모든 테스트 실행
cd tests
make debug

# 디버그 로그 레벨로 특정 테스트 실행
cd tests
make debug-one TEST_ID=<test_id>

# 출력 파일 정리
cd tests
make clean

# 도움말 표시
cd tests
make help
```

테스트 케이스는 `tests/testcases/` 디렉토리에 있으며, 각 테스트 케이스는 다음 파일을 포함합니다:
- `page.xhtml`: 입력 XHTML 파일
- `expected.mdx`: 예상 출력 MDX 파일
- `output.mdx`: 테스트 실행 시 생성되는 실제 출력 파일

## 가상환경 비활성화

작업이 끝난 후 가상환경을 비활성화하려면 아래 명령어를 입력하세요.

```bash
deactivate
```