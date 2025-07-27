# QueryPie 11.0.0 한국어 문서를 src/content/ko/ 디렉토리에 작성합니다.

## 작업의 개요

이 작업은 QueryPie Manual 한국어 문서를 src/content/ko/ 디렉토리에 작성하는 것입니다. 
디렉토리는 QueryPie의 한국어 문서 전용 디렉토리로, 다른 언어의 문서와는 별도로 관리됩니다.

QueryPie Manual 한국어 문서는 https://querypie.atlassian.net/wiki/spaces/QM/pages/608501837/QueryPie+Docs 를 
출처로 합니다. 이 Confluence Space 의 내용을 바탕으로, Overview, User Manual, Admin Manual 등 문서를
src/content/ko/ 디렉토리로 옮겨옵니다.

용어
- Confluence Space: QueryPie Manual 한국어 문서가 위치한 Confluence Space를 의미합니다. 
  이 Space는 https://querypie.atlassian.net/wiki/spaces/QM/pages/608501837/QueryPie+Docs URL을 통해 접근할 수 있습니다.
- Local Repository: querypie-docs Git Repository를 Local Repository 로 지칭합니다.
- Target Directory: Local Repository 내에 놓인 src/content/ko/ 디렉토리를 Target Directory 로 지칭합니다.
- Breadcrumbs: Confluence 에서 특정 문서의 Breadcrumbs 정보를 의미합니다. 한국어로 "탐색 경로"라고 합니다.

## Confluence Space 의 문서를 내려받기
- 이 Space는 https://querypie.atlassian.net/wiki/spaces/QM/pages/608501837/QueryPie+Docs URL을 통해 접근할 수 있습니다.
- scripts/pages_of_confluence.py 명령은 이 Confluence Space 에서 문서를 내려받아 저장하고, 목록을 만들어 내는 프로그램입니다.
  pages_of_confluence.py 는 지정한 문서에서 시작하여 children 문서를 재귀적으로 내려받아 저장합니다.
  프로그램 코드에는 한국어, 한글을 사용하지 않고, 영어로 설명, 코멘트를 작성하는 것이 규칙입니다.
- 개발 과정에서 프로그램의 기능 테스트를 빠르게 수행하기 위해, 다음의 문서를 시작 페이지로 지정하면 좋습니다:
  https://querypie.atlassian.net/wiki/spaces/QM/pages/544375784/QueryPie+Overview
- 문서 데이터를 저장하는 경로는 기본 `docs/latest-ko-confluence/`입니다. 문서 데이터는 이 아래에 `<page_id>/` 디렉토리를 생성하고
  데이터를 저장합니다. 상세한 절차는 다음의 4단계로 구분됩니다.
  1. 데이터 저장 과정의 첫번째 단계는 API 를 호출하고, 그 결과를 `<page_id>/*.yaml` 파일에 저장하는 것입니다.
      - page.v1.yaml: page v1 API 응답 결과를 yaml 로 저장합니다.
      - page.v2.yaml: page v2 API 응답 결과를 yaml 로 저장합니다.
      - ancestors.v2.yaml: ancestors v2 API
      - children.v2.yaml: children v2 API
      - attachments.v1.yaml: attachments v1 API
      - `--local` 실행 옵션을 지정한 경우, 이 API 호출 및 저장 과정을 수행하지 않습니다.
  2. API 결과에서 본문 데이터를 추출하여 저장합니다.
      - 앞의 과정에서 저장된 *.yaml 파일을 읽어서 작업을 수행합니다. `--local` 실행 옵션을 지정한 경우, 이 과정을 생략하지 않습니다.
      - page.xhtml: page v1 API 응답의 body.storage.value 를 저장합니다.
      - page.html: page v1 API 응답의 body.view.value 를 저장합니다.
      - page.adf: page v2 API 응답의 body.atlas_doc_format.value
      - ancestors.v1.yaml: page v1 API 응답의 ancestors 를 저장합니다.
  3. `--attachments` 실행 옵션을 지정한 경우, 첨부파일을 각각 내려받아 `<page_id>/` 디렉토리에 첨부파일의 이름으로 저장합니다. 
      - `--local` 실행 옵션이 지정된 경우, 이 과정은 생략합니다.
  4. ancestors, title 을 참조하여 문서 목록을 stdout 으로 출력합니다.
      - ancestors 에서, 문서 수집을 시작한 첫페이지, 그리고 이 첫페이지의 부모 등 상위 페이지 정보를 제외합니다.
```
# page v1 API
expand_params = "title,ancestors,body.storage,body.view"
url = f"{self.args.base_url}/rest/api/content/{page_id}?expand={expand_params}"

# page v2 API
url = f"{self.args.base_url}/api/v2/pages/{page_id}?body-format=atlas_doc_format"

# ancestors v2 API
ancestors_url = f"{self.args.base_url}/api/v2/pages/{page_id}/ancestors"

# children v2 API
child_url = f"{self.args.base_url}/api/v2/pages/{page_id}/children?type=page&limit=100"

# attachments v1 API
attachment_url = f"{self.args.base_url}/rest/api/content/{page_id}/child/attachment"

```
- 문서 목록은 다음의 형식을 갖습니다. stdout 결과를 redirect 하여 list.txt 에 저장하면, 이러한 구조를 갖게 됩니다:
  이 파일은 각 줄마다 하나의 문서에 대한 Page_ID, Breadcrumbs, 제목을 포함하고 있습니다. 각 항목은 tab 문자(`\t`)로 구분되어 있습니다.
  list.txt 파일의 예시는 다음과 같습니다.
```
608501837	QueryPie Docs	QueryPie Docs
544375335	QueryPie Docs > Release Notes	Release Notes
1064830173	QueryPie Docs > Release Notes > 11.0.0	11.0.0
954335909	QueryPie Docs > Release Notes > 10.3.0 ~ 10.3.4	10.3.0 ~ 10.3.4
703463517	QueryPie Docs > Release Notes > 10.2.0 ~ 10.2.12	10.2.0 ~ 10.2.12
604995641	QueryPie Docs > Release Notes > 10.1.0 ~ 10.1.11	10.1.0 ~ 10.1.11
544375355	QueryPie Docs > Release Notes > 10.0.0 ~ 10.0.2	10.0.0 ~ 10.0.2
544375370	QueryPie Docs > Release Notes > 9.20.0 ~ 9.20.2	9.20.0 ~ 9.20.2
544375385	QueryPie Docs > Release Notes > 9.19.0 	9.19.0 
544375399	QueryPie Docs > Release Notes > 9.18.0 ~ 9.18.3	9.18.0 ~ 9.18.3
```
- `<page_id>` 디렉토리에 저장된 page.xhtml, 첨부파일에 대한 예시는 다음과 같습니다.
```shell
% find latest-ko-confluence | head -20 
latest-ko-confluence
latest-ko-confluence/912425288
latest-ko-confluence/912425288/host use ..mov
latest-ko-confluence/912425288/host use.mov
latest-ko-confluence/912425288/page.xhtml
latest-ko-confluence/912425288/page.md
latest-ko-confluence/544375659
latest-ko-confluence/544375659/page.xhtml
latest-ko-confluence/544375659/11596736020377
latest-ko-confluence/544375659/page.md
latest-ko-confluence/921436219
latest-ko-confluence/921436219/image-20250411-080409.png
latest-ko-confluence/921436219/image-20250411-080251.png
latest-ko-confluence/921436219/page.xhtml
latest-ko-confluence/921436219/image-20250410-021636.png
latest-ko-confluence/921436219/image-20250411-080100.png
latest-ko-confluence/921436219/image-20250515-085639.png
latest-ko-confluence/921436219/page.md
latest-ko-confluence/544383110
latest-ko-confluence/544383110/page.xhtml
```
- Confluence Space 의 문서는 논리적으로, 계층적인 구조를 갖고 있습니다.
  - 각 문서는 페이지 단위로 구성되어 있으며, 페이지는 개별적인 주제를 다루고 있고, 새로운 카테고리가 됩니다.
  - Confluence Space 의 루트 페이지 문서는 "QueryPie Docs" 라는 제목을 갖고 있습니다.
  - 루트 디렉토리 아래에는 Release Notes, Overview, User Manual, Admin Manual, 4개의 주요 카테고리가 있습니다.

## src/content/ko/ 디렉토리의 구조
- src/content/ko/ 디렉토리는 QueryPie 11.0.0 한국어 문서 전용 디렉토리입니다.
- 디렉토리 구조는 다음과 같습니다.
    - src/content/ko/: Confluence Space 의 계층구조 최상위에 대응합니다.
    - src/content/ko/release-notes.mdx: Confluence Space 의 "Release Notes" 문서에 대응합니다.
    - src/content/ko/release-notes/: Confluence Space 의 "Release Notes" 하위 문서가 저장됩니다.
    - src/content/ko/user-manual.mdx: Confluence Space 의 "User Manual" 또는 "사용자 매뉴얼" 에 대응합니다.
    - src/content/ko/user-manual/: Confluence Space 의 "User Manual" 하위 문서가 저장됩니다.

## 수행할 작업 1: list.en.txt 파일을 읽고, confluence_xhtml_to_markdown.py 를 실행하는 명령을 생성합니다.

- 입력파일: docs/latest-ko-confluence/list.en.txt
    - list.en.txt 의 각 줄은 하나의 문서에 대한 Page_ID, 탐색경로, 문서의 제목을 가리킵니다.
      각 줄의 처음에 Page_ID 가 오고, 그 뒤에 탭 문자(`\t`)가 있으며, 그 뒤에 탐색경로가 옵니다.
    - 탐색경로 breadcrumbs 는 하나 이상의 경로가 > 로 구분됩니다.
- 변환절차:
    - list.en.txt 파일의 각 줄을 읽어, Page_ID, 탐색경로, 문서 제목을 추출합니다.
    - list.en.txt 가 놓인 디렉토리에, <Page_ID> 라는 디렉토리가 존재합니다. 
      <Page_ID>/page.xhtml 파일은 Confluence 의 본문을 표현하는 xhtml 형식 파일입니다.
    - 각 문서의 탐색경로를 분석하여, 현재 디렉토리 아래에 해당 문서의 경로를 결정합니다.
- Python program 의 작동 방식
    - python program 은 CLI 방식으로 작동합니다. 입력파일로 list.en.txt 파일,
      <Page_ID>/page.md 파일이 위치한 경로 (기본값: docs/latest-ko-confluence/) 를 argument 로 지정받고,
      출력파일로 src/content/ko/ 디렉토리 아래에 생성할 markdown 파일의 경로를 argument 로 지정받습니다.
    - python program 의 파일은 scripts/generate_commands_for_xhtml2markdown.py 파일에 저장하여 주세요.
    - 실행할 때 option 으로 list.en.txt 디렉토리의 경로를 입력하도록 작성하여 주세요.
    - `#!/usr/bin/env python3` 로 시작하는 shebang 을 추가하여, Python 3 환경에서 실행되도록 합니다.
    - python code 안에는 한글이 아닌 영어로 comment, message 등을 작성합니다.
- 문서의 경로와 파일이름을 결정하기
    - 탐색경로를 참조하여, 해당 문서의 경로를 결정하고, 그에 맞추어 디렉토리를 현재 디렉토리 아래에 생성합니다.
    - mkdir -p 명령으로 디렉토리를 생성하는 명령을 수행할 수 있게 제공합니다.
    - 탐색경로의 마지막 항목에 사용된 URI 를 활용하여, 문서의 경로와 파일이름을 결정합니다. URI 는 `/`로 구분되어 있으며,
      URI 의 마지막 부분이 문서의 파일이름이 됩니다. 이 파일이름에 `.mdx` 확장자를 덧붙여, markdown 파일을 생성합니다.
    - `QueryPie Manual` 은 `./querypie-manual.mdx` 파일로 저장합니다.
    - `QueryPie Manual > QueryPie Docs` 은 `./querypie-manual/querypie-docs.mdx` 파일로 저장합니다.
    - 예를 들어, 탐색경로가 `QueryPie Manual > QueryPie Docs > Admin Manual > Databases > Connection Management > DB Connections` 이라면,
      `./querypie-manual/querypie-docs/admin-manual/databases/connection-management/db-connections.mdx` 파일을 생성합니다.
    - 문서 경로, 문서의 이름에 사용되는 URI 에 a, the 와 같은 관사를 제외합니다.
- 이 프로그램은 실제 변경사항을 만들지 않고, 변경사항을 출력하는 명령을 생성합니다.
  - 예를 들어, `mkdir -p ./querypie-manual/querypie-docs/admin-manual/databases/connection-management/db-connections` 와 같은 명령을 출력합니다.
  - 이 명령은 실제로 디렉토리를 생성하지 않고, 단순히 출력만 합니다.

## 수행할 작업: 작성 중입니다.

- 문서 내용 작성하기
    - 각 줄의 Page_ID 에 해당하는 문서를 docs/latest-ko-confluence/ 디렉토리 아래에서 <Page_ID>/page.md 에서 찾을 수 있습니다.
    - 문서 내에 포함된 이미지 파일을 본문을 저장하는 `.mdx` 파일과 동일한 디렉토리에 저장합니다. 
- 문서에 포함된 이미지 파일을 저장하기
    - 이미지 파일의 이름은 `prefix-screenshot-1.png`, `prefix-image-1.png` 와 같은 형식으로 작성합니다.
    - prefix 부분은 문서의 이름(.mdx 확장자를 제외한 이름)과 동일하게 설정합니다.
    - (.mdx 확장자를 ) 포함하는 `.mdx` 파일과 prefix 가 동일하게 지정합니다.
    - 이미지 파일이 screenshot 유형의 경우, `prefix-screenshot-` 접두사를 사용합니다.
    - 이미지 파일이 diagram, illustration 유형의 경우, `prefix-image-` 접두사를 사용합니다.
    - 첫번째 이미지 파일은 -1, 두번째 이미지 파일은 -2, 세번째 이미지 파일은 -3 과 같이 순차적으로 번호를 매깁니다.
- list.en.txt 파일의 각 항목을 모두 변환한 이후, 작업을 종료합니다.
    - 하나의 문서를 변환 완료할 때마다, 이용자에게 변환 여부를 간단히 한 줄 안내 문구로 알려줍니다.
