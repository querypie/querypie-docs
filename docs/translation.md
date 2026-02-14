# Markdown 으로 작성된 컨텐츠 문서의 언어를 번역합니다.

- 이 문서는 Claude, JetBrains Junie, ChatGPT 등 LLM 모델 기반의 AI Agent 가 참조하기 위한 목적으로 작성되었습니다.

## 컨텐츠의 원문

- [src/content/ko](../src/content/ko) 아래의 .mdx 확장자를 가진 MDX 문서가 원문입니다.
- 원문은 한국어로 작성되어 있습니다.
- MDX 문서는 Markdown 에 JSX 기능을 확장한 문서양식입니다. MDX 문서는 서로 참조하는 링크를 갖고 있습니다.
- 컨텐츠 원문은 스크린샷과 같은 이미지 파일을 본문에 포함하고 있습니다. 이미지 파일은 [public/](../public) 디렉토리에 놓여 있습니다.
   - 이미지 파일의 경로는 이를 참조하는 MDX 파일의 경로에 의해 결정됩니다. `src/content/ko/path/filename.mdx`라는 원문의 경우, `public/path/filename/` 디렉토리에 이미지 파일이 놓입니다.
   - 이미지 파일은 `screenshot-yyyymmdd-hhmmss.png` 또는 `image-yyyymmdd-hhmmss.png` 와 같은 이름을 갖고 있는 경우가 대부분입니다.
   - 이미지 파일의 이름은 `.png` 와 같이 이미지 파일의 종류를 가리키는 확장자를 갖고 있습니다.
   - 이미지 파일의 이름은 `screenshot-`, `image-` 라는 Prefix 를 갖는 경우가 대부분이나, 반드시 갖는 것은 아닙니다.
- 이미지 파일은 언어에 무관하게 공통적으로 사용할 수 있습니다. 따라서, 원문을 번역하더라도, 이미지 파일을 교체하지 않고, 그대로 사용할 수 있습니다.

## 영어로 번역된 컨텐츠

- [src/content/en](../src/content/en) 아래의 .mdx 확장자를 가진 MDX 문서가 영어로 번역된 문서입니다.
- 이 문서는 표준 영어로 작성되어야 합니다.
- 문서의 경로, 파일이름은 컨텐츠의 원문과 동일한 경로, 파일이름을 사용하여야 합니다.
    - `src/content/ko/path/filename.mdx`라는 원문의 경우, `src/content/en/path/filename.mdx`라는 영어 문서가 대응합니다.
    - 다시 말해, `src/content/ko/`, `src/content/en/` 의 경로는 언어에 따라 다르지만, 그 이후 경로와 파일이름은 동일하여야 합니다.
- 번역된 문서는 스크린샷과 같은 이미지 파일을 본문에 포함할 수 있습니다. 이때, 한국어 원문에 사용된 이미지 파일을 동일하게 사용합니다.
    - 이미지 파일의 Caption 등 설명 문구는 한국어 원문을 영어로 번역하는 대상이 됩니다.

## 일본어로 번역된 컨텐츠

- [src/content/ja](../src/content/ja) 아래의 .mdx 확장자를 가진 MDX 문서가 일본어로 번역된 문서입니다.
- 이 문서는 표준 일본어로 작성되어야 합니다.
- 문서의 경로, 파일이름은 컨텐츠의 원문과 동일한 경로, 파일이름을 사용하여야 합니다.
    - `src/content/ko/path/filename.mdx`라는 원문의 경우, `src/content/ja/path/filename.mdx`라는 일본어 문서가 대응합니다.
    - 다시 말해, `src/content/ko/`, `src/content/ja/` 의 경로는 언어에 따라 다르지만, 그 이후 경로와 파일이름은 동일하여야 합니다.
- 번역된 문서는 스크린샷과 같은 이미지 파일을 본문에 포함할 수 있습니다. 이때, 한국어 원문에 사용된 이미지 파일을 동일하게 사용합니다.
    - 이미지 파일의 Caption 등 설명 문구는 한국어 원문을 일본어로 번역하는 대상이 됩니다.

## Skeleton MDX 를 비교하기

- `confluence-mdx/bin/skeleton/cli.py` 를 실행하여, `filename.mdx`에서 생성한 `filename.skel.mdx` 를 Skeleton MDX 라고 합니다.
    - 이 파일은 자연어로 작성된 MDX 문서에서 Markdown, MDX 문법 요소만을 남겨두고, 자연어 문장을 _TEXT_ 와 같은 키워드로 대체한 파일입니다.
    - 한국어, 일본어, 영어 등 원문의 언어와 무관하게, Skeleton MDX 는 동일한 내용의 파일이 생성되는 것이 특징입니다.
    - 이 Skeleton MDX 파일을 비교하여, 원문과 번역문의 MDX 파일이 동일한 구성을 갖고 있는지, 문장의 수가 동일한지, Image link 가 동일한
      파일을 가리키는지, 검증할 수 있습니다.
- `skeleton/cli.py`는 venv 환경에서 실행할 수 있습니다.
    - `cd confluence-mdx; source venv/bin/activate; bin/skeleton/cli.py target/en/path/to/file.mdx` 와 같이 실행할 수 있습니다.
    - Skeleton MDX 파일은 원문 MDX 파일과 동일한 디렉토리에 생성됩니다.
- `bin/skeleton/cli.py --recursive`를 실행하면, target 디렉토리 아래의 모든 MDX 파일에 대해 Skeleton MDX 를 생성하고,
  한국어 원문 MDX 와 번역문 MDX 의 Skeleton MDX 를 비교하여 줍니다. 이때, diff 결과와 유사한 형식의 결과가 출력되는데, Skeleton MDX 의 비교와 함께
  원문 MDX 와 번역문 MDX 의 해당 라인을 diff 형식과 유사하게 보여줍니다. 이를 활용하여, 원문 MDX 와 번역문 MDX 의 차이가 발생한 부분을 효과적으로
  파악할 수 있습니다.
- 특정 번역문과 원문의 Skeleton MDX 를 비교하는 방법
    1. `bin/skeleton/cli.py target/en/path/to/file.mdx`와 같이 실행합니다. target/en, target/ja 아래에는 src/content/en, src/content/ja 아래의
       디렉토리 경로가 Symbolic link 로 연결되어 있고, MDX 파일에서 Skeleton MDX 를 생성하여 비교하는 기능이 작동합니다.
- Skeleton MDX 에서 원문과 번역문은 줄바꿈, 공백 차이가 없어야 합니다.
- 그러나, 몇몇 예외적인 경우, 원문과 번역문의 Skeleton MDX 의 차이가 발생할 수 있으며, 이는 정상적인 번역 결과로 간주합니다.
    - 자연어의 특성에 따라, 원문을 적절하게 번역하였으나, 어순 차이, 표현 방식 차이가 있는 경우
    - Code Block 내에 원문에서 영어가 아닌 한국어를 사용한 경우, 번역문에서 이를 영어 또는 일본어로 번역한 경우

## 번역시 유의할 사항

- 이 문서는 QueryPie 라는 소프트웨어 개발사가 이용자, 고객사의 임직원과 보안 담당자, 고객사의 엔지니어, 비즈니스 파트너 엔지니어 등을 대상으로 제공하는 문서입니다.
- 높은 수준의 품질과 기술지원을 제공하는 소프트웨어 제조사의 입장에서, 격식을 갖춘 표현을 사용하여 주세요.
    - 딱딱하고 건조한 문체보다, 이용자에게 친화적인 대화체를 사용하는 것을 선호합니다.
    - 그러나, 일상적인 구어체, 친구들 사이에 사용하는 가벼운 문체를 사용하지 않아야 합니다.
- 원문의 MDX 파일에 사용된 markdown 표현 형식, 줄바꿈 등 형식을 번역, 수정한 문서에 그대로 유지하여 주세요.
    - 표, 목록, 강조(예: **text**) 등 마크다운 구조는 한국어 원문과 동일하게 유지한다.
    - `**Example Phrase**`와 같이 `**`를 이용해 강조표시된 Markdown 구문을 그대로 유지합니다. `<strong>`으로 대체하지 않습니다.
    - Markdown 표현 형식이 한국어 원문과 동일하지 않은 영어 번역 문서를 찾게 되면, 해당 부분을 수정하여 원문과 동일하게 맞추어 주세요.
- 원문의 MDX 파일에서 적절히 Escape 된 문자열을 임의로 Decode 하지 않습니다.
    - `&lt;` `&gt;`로 HTML Encode 된 문자열을 그대로 유지합니다.
    - 예시) 원문에서 `&lt;token&gt;` 인 문자열을 `<token>`으로 옮기면 안 됩니다. 원문의 문자열, `&lt;token&gt;`을 유지하여야 합니다.
    - 예시) 중괄호 Embrace 로 감싸인 문자열에 덧붙은 backquote 를 없애면 안 됩니다. 원문의 문자열, `{querypie url}`을 유지하여야 합니다.
- 문서 사이의 링크는 상대 경로를 유지합니다.

## 번역, 수정 과정에 대한 지침

- Skeleton MDX 를 비교하여, 원문과 번역문의 차이가 없어야 합니다.
- 번역, 수정 과정이 1차 완료된 이후, `npm run build`를 수행하여, 번역, 수정된 MDX 파일이 올바르게 빌드되는지 확인합니다.
    - 빌드 오류가 발생하는 경우, 에러 메시지에서 그 원인을 확인하고, 잘못된 부분을 고칩니다.
    - `npm run build`가 성공할 때까지, 위 과정을 반복합니다.
    - `npm run build`를 실행하기 위해, 명령 지시자에게 확인받지 않습니다. 직접 곧바로 명령을 수행합니다.
- 별도의 지시가 없으면, 이미 번역된 문서를 대상으로, 다시 번역하지 않습니다.
    - 별도의 지시가 없으면, 이미 검토 결과가 작성된 문서에 대해, 교정, 교열을 수행하지 않습니다.
- 별도의 지시가 없으면, 한번에 50개의 문서를 번역하거나 검토한 이후, 작업을 완료하고, 명령 지시자에게 리뷰를 요청하세요.
- 원문 한국어에서 오타, 문법 오류, 어법에 맞지 않는 표현이 발견된 경우, 이에 대한 것을 Feedback 으로 남겨 주세요.
- 그 외 번역 과정에서 어려운 점이 발견된 경우, Feedback 으로 남겨 주세요.
- Feedback 남기는 방법
    - 이 문서의 마지막에 놓인 "# AI Agent 로부터의 Feedback" 섹션에 의견, 번역, 수정 과정의 어려움을 알려주세요.

# AI Agent 로부터의 Feedback

- to-be-added
