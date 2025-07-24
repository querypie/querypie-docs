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
- scripts/pages_of_confluence.py 파일을 통해, 이 Confluence Space 에서 문서의 목록을 가져올 수 있습니다.
  pages_of_confluence.py 를 실행한 결과를 docs/latest-ko-confluence/list.txt 파일에 저장합니다.
- docs/latest-ko-confluence/list.txt 파일은 Confluence Space 에서 가져온 문서의 목록을 담고 있습니다.
  이 파일은 각 줄마다 하나의 문서에 대한 Page_ID, Breadcrumbs, 제목을 포함하고 있습니다. 각 항목은 tab 문자(`\t`)로 구분되어 있습니다.
  list.txt 파일의 예시는 다음과 같습니다.
```
% head list.txt
608501837	QueryPie Manual > QueryPie Docs	QueryPie Docs
544375335	QueryPie Manual > QueryPie Docs > Release Notes	Release Notes
1064830173	QueryPie Manual > QueryPie Docs > Release Notes > 11.0.0	11.0.0
954335909	QueryPie Manual > QueryPie Docs > Release Notes > 10.3.0 ~ 10.3.4	10.3.0 ~ 10.3.4
703463517	QueryPie Manual > QueryPie Docs > Release Notes > 10.2.0 ~ 10.2.12	10.2.0 ~ 10.2.12
604995641	QueryPie Manual > QueryPie Docs > Release Notes > 10.1.0 ~ 10.1.11	10.1.0 ~ 10.1.11
544375355	QueryPie Manual > QueryPie Docs > Release Notes > 10.0.0 ~ 10.0.2	10.0.0 ~ 10.0.2
544375370	QueryPie Manual > QueryPie Docs > Release Notes > 9.20.0 ~ 9.20.2	9.20.0 ~ 9.20.2
544375385	QueryPie Manual > QueryPie Docs > Release Notes > 9.19.0 	9.19.0 
544375399	QueryPie Manual > QueryPie Docs > Release Notes > 9.18.0 ~ 9.18.3	9.18.0 ~ 9.18.3
```
- scripts/pages_of_confluence.py 는 문서의 Page_ID 를 디렉토리 이름으로 하여, 그 안에 문서의 본문과 첨부파일을 저장합니다.
  문서의 본문은 `<Page_ID>/page.xhtml` 파일에 저장되며, 첨부파일은 `<Page_ID>/` 디렉토리에 첨부파일의 이름으로 저장됩니다.
  저장된 page.xhtml, 첨부파일의 구조는 다음과 같습니다.
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
