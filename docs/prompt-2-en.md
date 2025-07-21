# QueryPie 11.0.0 영어 문서를 src/content/en/ 디렉토리에 작성합니다.

## 작업의 개요

이 작업은 QueryPie 11.0.0 영어 문서를 src/content/en/ 디렉토리에 작성하는 것입니다. 
디렉토리는 QueryPie의 영어 문서 전용 디렉토리로, 다른 언어의 문서와는 별도로 관리됩니다.

QueryPie 11.0.0 영어 문서는 https://docs.querypie.com/en/querypie-manual/11.0.0/ 를 
출처로 합니다. 이 웹사이트에 있는 내용을 바탕으로, Overview, User Manual, Admin Manual 등 문서를
src/content/en/ 디렉토리로 옮겨옵니다.

용어
- Source Website: https://docs.querypie.com/en/querypie-manual/11.0.0/ 를 Source Website 로 지칭합니다.
- Local Repository: querypie-docs Git Repository를 Local Repository 로 지칭합니다.
- Target Directory: Local Repository 내에 놓인 src/content/en/ 디렉토리를 Target Directory 로 지칭합니다.
- Breadcrumbs: Source Website 에서 특정 문서의 Breadcrumbs 정보를 의미합니다. 영어로 "탐색 경로"라고 합니다.

## Source Website 에 대한 상세 정보
- https://docs.querypie.com/en/querypie-manual/11.0.0/ URL 을 통해 해당 문서를 가져올 수 있습니다.
- Local Repository 의 docs/11.0.0-en/ 디렉토리에 있는 파일들을 참고하여, 
  Target Directory 에 옮겨올 문서의 구조를 이해합니다.
- docs/11.0.0-en/sitemap.xml 은 Source Website 의 Sitemap 파일입니다.
- docs/11.0.0-en/urls.txt 는 Source Website 의 전체 문서에 대한 URL 을 담고 있습니다. 
  urls.txt 는 텍스트 파일이며, 한 줄에 하나의 URL 이 포함되어 있습니다.
- docs/11.0.0-en/titles.txt 는 Source Website 의 전체 문서에 대한 url 과 title 을 담고 있습니다. 
  titles.txt 는 텍스트 파일이며, 한 줄에 url + `\t` + (url 문서의 제목) 으로 구성됩니다.
- docs/11.0.0-en/breadcrumbs.txt 는 Source Website 의 전체 문서에 대한 url 과 
  Breadcrumbs 정보를 담고 있습니다. breadcrumbs.txt 는 텍스트 파일이며, 
  한 줄에 url + `\t` + (url 문서의 Breadcrumbs) 으로 구성됩니다. Breadcrumbs 정보는 / 를 구분자로 하여,
  해당 문서를 탐색하기 위한 경로 정보를 포함합니다. 경로 정보는 `[문서 제목](URI)` 형식으로 작성되어 있습니다.
- urls.txt, titles.txt, breadcrumbs.txt 파일은 각 줄마다 동일한 문서의 속성을 갖고 있습니다.
  예를 들어, urls.txt 의 첫번째 줄과 titles.txt 의 첫번째 줄, breadcrumbs.txt 의 첫번째 줄은 
  동일한 문서에 대한 URL, 제목, 탐색경로를 나타냅니다.
- Source Website 의 문서 구조를 이해하는 데 
  유용합니다. 이 파일들을 참고하여 Target Directory 에 옮겨올 문서의 구조를 이해합니다.

## Source Website 문서의 계층 구조
- Source Website 의 문서같은 URL의 패턴은 다음과 같습니다.
    - /querypie-manual/11.0.0/ : Source Website 의 루트 디렉토리입니다.
    - /querypie-manual/11.0.0/<page_name> : 개별 문서 페이지입니다.
- Source Website 의 문서는 논리적으로, 계층적인 구조를 갖고 있습니다.
    - 각 문서는 페이지 단위로 구성되어 있으며, 페이지는 개별적인 주제를 다루고 있고, 새로운 카테고리가 됩니다.
    - Source Website 의 루트 디렉토리에 놓인 문서는 "QueryPie Docs" 라는 제목을 갖고 있습니다.
    - 루트 디렉토리 아래에는 Release Notes, Overview, User Manual, Admin Manual, 4개의 주요 카테고리가 있습니다.

## src/content/en/ 디렉토리의 구조
- src/content/en/ 디렉토리는 QueryPie 11.0.0 영어 문서 전용 디렉토리입니다.
- 디렉토리 구조는 다음과 같습니다.
    - src/content/en/: Source Website 의 /querypie-manual/11.0.0/ 에 대응합니다.
    - src/content/en/overview/: Source Website 의 /querypie-manual/11.0.0/overview 에 대응합니다.
    - src/content/en/user-manual/: Source Website 의 /querypie-manual/11.0.0/user-manual 에 대응합니다.

## 수행할 작업 1: breadcrumbs.revised.txt 파일 작성
- 입력파일: breadcrumbs.txt
    - breadcrumbs.txt 의 각 줄은 하나의 문서에 대한 URL, 탐색경로 가리킵니다. 
      각 줄의 처음에 URL 이 오고, 그 뒤에 탭 문자(`\t`)가 있으며, 그 뒤에 탐색경로가 옵니다.
    - 탐색경로 breadcrumbs 는 하나 이상의 경로가 / 로 구분되며, 하나의 경로는 `[문서 제목](URI)` 형식으로 작성되어 있습니다.
- 변환절차:
    - `[문서 제목](URI)` 형식의 탐색경로에서, '문서 제목'은 영어 또는 원래의 문구를 그대로 유지하고, 'URI' 부분을 재작성합니다.
    - URI 는 /path/filename 으로 구성됩니다. 문서 제목을 영어로 번역하여 URI 의 filename 부분에 적용합니다.
    - 영어 번역한 문서 제목에서, a, the 등 정관사는 생략합니다.
    - 영어 번역한 문서 제목에서, 여러 단어의 구분자는 - 를 사용합니다.
    - 탐색경로에 사용되는 URI 는 해당 탐색경로 전체를 나타내는 URI 로 작성합니다. 
      특정 경로의 URI 는 (상위 경로에 사용된 URI)/(해당 페이지의 영어 번역된 제목) 형식으로 작성합니다.
    - 탐색경로의 마지막 항목을 추가하여 주세요. 마지막 항목을 해당 문서의 제목, URI 로 작성합니다. 
      기존 breadcrumbs.txt 파일의 탐색경로는 상위 경로에 대한 정보만 포함되어 있고, 해당 문서 자체에 대한 정보가 누락되어 있습니다.
- 출력파일: breadcrumbs.revised.txt
    - 탐색경로의 논리적인 계층구조에 맞추어, URI 을 재작성하고, 변경된 탐색경로를 breadcrumbs.revised.txt 파일에 작성합니다.
    - breadcrumbs.revised.txt 파일은 breadcrumbs.txt 파일과 동일한 디렉토리에 저장합니다.
    - breadcrumbs.revised.txt 파일의 내용은 breadcrumbs.txt 파일의 내용과 동일한 순서로 작성되어야 합니다.
- 작업 오류의 예시 #1: 다음과 같은 오류가 발생하지 않도록, 유의하여 주세요.
    - `[QueryPie Docs](/querypie-docs)/[Admin Manual](/querypie-docs/admin-manual/databases/connection-management/db-connections)`
    - 위의 예시에서, 탐색경로의 두번째 항목에서 문서제목은 `[Admin Manual]`이지만, URI 는 `admin-manual/databases/connection-management/db-connections` 입니다.
    - 탐색경로의 하위 항목의 URI 가 상위 항목에 적용되어 있습니다.
