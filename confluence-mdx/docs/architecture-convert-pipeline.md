# Convert 파이프라인 아키텍처

Confluence XHTML을 Nextra용 MDX로 변환하는 파이프라인의 코드 구조를 설명한다.

## 전체 흐름

```
[Confluence API]
      │
      ▼
bin/fetch_cli.py          ← Phase 1: 데이터 수집
      │
      ▼
var/                      ← 로컬 캐시 (XHTML, YAML, 첨부파일)
      │
      ▼
bin/convert_all.py        ← Phase 2: 배치 변환 (pages.yaml 순회)
      │  각 페이지마다 subprocess로 호출 ↓
      ▼
bin/converter/cli.py      ← 단일 페이지 변환 진입점
      │
      ▼
target/ko/*.mdx           ← 최종 출력
target/public/            ← 이미지 등 첨부파일
```

---

## Phase 1: 데이터 수집 (fetch)

진입점: `bin/fetch_cli.py`

### 모듈 구조

| 파일 | 역할 |
|------|------|
| `bin/fetch/processor.py` | 4-Stage 파이프라인 오케스트레이터 |
| `bin/fetch/stages.py` | Stage 1~4 구현 |
| `bin/fetch/api_client.py` | Confluence REST API 클라이언트 |
| `bin/fetch/config.py` | 설정 (base_url, space_key, 기본 page_id 등) |
| `bin/fetch/models.py` | 데이터 모델 (Page 등) |
| `bin/fetch/file_manager.py` | YAML/파일 I/O |
| `bin/fetch/translation.py` | 제목 번역 서비스 |

### 4-Stage 파이프라인

1. **Stage 1 — API 데이터 수집**: Confluence REST API 호출 → `var/<page_id>/page.v1.yaml`, `page.v2.yaml`, `children.v2.yaml`, `attachments.v1.yaml`
2. **Stage 2 — XHTML 추출**: API 응답에서 본문 추출 → `var/<page_id>/page.xhtml`
3. **Stage 3 — 첨부파일 다운로드** (`--attachments` 필요): 바이너리 파일 → `var/<page_id>/` 에 저장
4. **Stage 4 — 문서 목록 생성**: 전체 페이지 메타데이터 → `var/pages.yaml`

### 실행 모드

- `--remote`: 전체 API fetch + 처리
- `--recent` (기본값): 최근 수정 페이지만 fetch + 로컬 처리
- `--local`: API 호출 없이 로컬 파일만 처리

### var/ 디렉토리 구조

```
var/
├── pages.yaml                ← 전체 페이지 목록 (Stage 4 산출물)
└── <page_id>/
    ├── page.v1.yaml          ← V1 API 메타데이터 (body.view HTML 포함)
    ├── page.v2.yaml          ← V2 API 메타데이터
    ├── page.xhtml            ← Confluence XHTML 본문
    ├── children.v2.yaml      ← 자식 페이지 목록 + 정렬 순서
    ├── attachments.v1.yaml   ← 첨부파일 메타데이터
    ├── mapping.yaml          ← XHTML↔MDX 블록 매핑 (변환 시 생성)
    └── <attachment files>    ← 다운로드된 첨부파일
```

### pages.yaml 엔트리 구조

```yaml
- page_id: "608501837"
  title: "English Title"        # 번역된 영문 제목
  title_orig: "한국어 제목"       # 원본 한국어 제목
  breadcrumbs: ["Docs", "시작하기", "설치"]
  breadcrumbs_en: ["Docs", "Getting Started", "Installation"]
  path: ["getting-started", "installation"]   # slugified 경로
```

`path` 필드가 출력 디렉토리 구조와 파일명을 결정한다.

---

## Phase 2: 변환 (convert)

### 배치 변환: `bin/convert_all.py`

`pages.yaml`를 읽어 각 페이지에 대해 `converter/cli.py`를 subprocess로 호출한다.

**주요 함수**:

- `load_pages_yaml(path)` — pages.yaml 로드 (L42)
- `load_translations(path)` — `etc/korean-titles-translations.txt` 로드 (L51)
- `verify_translations(pages, translations)` — 번역 누락 검증. 한글 제목이 번역 파일에 없으면 에러 (L69)
- `convert_all(pages, var_dir, output_base_dir, public_dir, log_level)` — 페이지 순회하며 변환 실행 (L108)

**출력 경로 결정 로직** (L126-136):

```python
# path = ["getting-started", "installation"] 일 때:
# rel_dir = "getting-started"
# filename = "installation.mdx"
# output_file = "target/ko/getting-started/installation.mdx"
# attachment_dir = "/getting-started/installation"
```

**subprocess 호출** (L144-153):

```python
cmd = [sys.executable, 'bin/converter/cli.py',
       input_file, output_file,
       f'--public-dir={public_dir}',
       f'--attachment-dir={attachment_dir}',
       f'--log-level={log_level}']
```

### 단일 페이지 변환: `bin/converter/cli.py`

**`main()` (L113) 실행 순서**:

1. **컨텍스트 설정** — `ctx.INPUT_FILE_PATH`, `ctx.OUTPUT_FILE_PATH`, `ctx.LANGUAGE` 설정
2. **언어 감지** (L149-158) — 출력 경로에서 2글자 언어 코드(ko/ja/en) 추출
3. **XHTML 로드** — 원본 보존(`xhtml_original`), 네임스페이스 제거(`ac:`, `ri:` 접두사 strip)
4. **pages.yaml 로드** — `PAGES_BY_TITLE`, `PAGES_BY_ID` 딕셔너리 구성
5. **page.v1.yaml 로드** — 현재 페이지 메타데이터 → `GLOBAL_PAGE_V1`
6. **링크 매핑 구축** — `build_link_mapping()`: body.view HTML에서 `data-linked-resource-id` 추출
7. **변환 실행** — `ConfluenceToMarkdown(html_content)` → `.load_attachments()` → `.as_markdown()`
8. **sidecar mapping 생성** — `generate_sidecar_mapping()` (실패해도 변환 차단 안 함)
9. **\_meta.ts 생성** — `generate_meta_from_children()`: children.v2.yaml로 Nextra 사이드바 메타데이터 생성

---

## 핵심 변환 엔진: `bin/converter/core.py`

### 클래스 계층 관계

```
ConfluenceToMarkdown (오케스트레이터)
├── 첨부파일 로드: Attachment 인스턴스 생성
├── import문 결정: Callout 사용 여부 검사
├── frontmatter 생성: title, confluenceUrl
├── 본문 변환 위임:
│   └── MultiLineParser (블록 레벨)
│       ├── 인라인 콘텐츠 → SingleLineParser 위임
│       ├── 테이블 → TableToNativeMarkdown 또는 TableToHtmlTable
│       ├── 매크로 → StructuredMacroToCallout
│       ├── ADF 확장 → AdfExtensionToCallout
│       └── 코드/확장/첨부 → 전용 메서드
└── 최종 조합: remark + imports + body
```

### ConfluenceToMarkdown (L1352)

최상위 오케스트레이터.

**프로퍼티**:
- `remark` — YAML frontmatter 생성 (`title`, `confluenceUrl`)
- `imports` — 필요한 import문 (`import { Callout } from 'nextra/components'`)
- `title` — `# 제목` h1 헤딩 생성

**메서드**:
- `load_attachments(input_dir, output_dir, public_dir)` — `<ac:image>` 내 `<ri:attachment>` 노드를 찾아 Attachment 인스턴스 생성 + 파일 복사
- `as_markdown()` — 전체 변환 실행. `remark + imports + title + body`를 `''.join(chain(...))`으로 조합

**변환 판정 로직** (`as_markdown`, L1424):
1. Callout 사용 여부 감지 → import문 결정
2. title 추가
3. `MultiLineParser(self.soup).as_markdown`으로 본문 변환

### MultiLineParser (L572)

블록 레벨 노드를 Markdown으로 변환한다. DOM을 깊이우선 순회한다.

**핵심 분기** (`convert_recursively`, L636):

| XHTML 노드 | 변환 결과 |
|-------------|-----------|
| `[document]`, `html`, `body`, `ac:layout*` | 자식 노드로 재귀 |
| `h1`~`h6` | `## ` ~ `###### ` (레벨 +1 조정, SingleLineParser 위임) |
| `ac:structured-macro` (tip/info/note/warning/panel) | `<Callout>` (StructuredMacroToCallout 위임) |
| `ac:adf-extension` (panel) | `<Callout>` (AdfExtensionToCallout 위임) |
| `ac:structured-macro` (code) | `` ```language `` 코드 블록 |
| `ac:structured-macro` (expand) | `<details><summary>` |
| `ac:structured-macro` (toc) | 스킵 (Nextra 자체 TOC 사용) |
| `table` | TableToNativeMarkdown 시도 → 실패 시 TableToHtmlTable |
| `p`, `div` | 문단. 인라인은 SingleLineParser, 블록은 MultiLineParser 재귀 |
| `ul`, `ol` | 리스트. `list_stack`으로 중첩 깊이 추적 |
| `ac:image` | `<figure>` + `<img>` + `<figcaption>` |
| `blockquote` | `> ` 접두사 |
| `hr` | `______` (Markdown h2 오해석 방지) |

**문단 처리 (L700-728)**: `<p>` 내 긴 텍스트를 `split_into_sentences()`로 문장 단위 줄바꿈한다.

**리스트 처리 (`convert_ul_ol` L753, `convert_li` L771)**: `list_stack` 배열로 중첩 깊이를 추적하고, 깊이 × 4칸 들여쓰기를 적용한다.

### SingleLineParser (L114)

인라인 노드를 단일 Markdown 문자열로 변환한다.

**`applicable` 판정** (L143): 노드와 모든 자손이 `applicable_nodes` 집합에 포함되는지 재귀 검사. `ac:link`, `ac:image`, `ac:structured-macro[name=status]`도 처리 가능.

**주요 변환** (`convert_recursively`, L169):

| XHTML 노드 | Markdown 출력 |
|-------------|---------------|
| `NavigableString` | 텍스트. `<`/`>` 이스케이프, `{}`를 백틱 감싸기 |
| `strong` | ` **text** `. 헤딩 내에서는 무시 |
| `em` | ` *text* ` |
| `code` | `` `text` `` |
| `u` | `<u>text</u>`. 앵커 내에서는 무시 |
| `br` | `<br/>` |
| `a` | `[text](href)`. Confluence URL이면 내부 링크로 변환 |
| `ac:link` | `convert_ac_link()` → 내부/외부 링크 해석 |
| `ac:emoticon` | emoji 라이브러리로 실제 이모지 문자 변환 |
| `time` | 언어별 날짜 포맷 (ko: `2025년 01월 02일`) |
| `ac:image` (인라인) | `<img src="..." alt="..." />` |
| `ac:structured-macro[name=status]` | `<Badge color="blue">Step 1</Badge>` |
| `ac:adf-fragment-mark` | `<a id="fragment-name"></a>` |

### 링크 변환: `convert_ac_link()` (L400)

`<ac:link>` 내부의 `<ri:page>`를 분석하여:

1. **내부 링크** (`PAGES_BY_TITLE`에 있는 페이지): `relative_path_to_titled_page()`로 상대 경로 생성
2. **외부 링크** (`PAGES_BY_TITLE`에 없는 페이지): `resolve_external_link()`로 Confluence URL 생성. `GLOBAL_LINK_MAPPING`에서 pageId를 찾아 정확한 URL 생성, 없으면 space overview로 폴백
3. **앵커 링크**: `ac:anchor` 속성 → `#fragment` 부가

### TableToNativeMarkdown (L961)

단순 테이블을 네이티브 Markdown 테이블로 변환한다.

**`applicable` 판정** (L987): 모든 자손 노드가 `applicable_nodes` 집합의 부분집합인지 검사. `ul`, `ol`, `ac:structured-macro` 등이 포함되면 불가.

**`convert_table()` (L1029)**: `rowspan`/`colspan` 추적 행렬을 사용하여 셀을 정규화하고, 열 너비를 계산하여 정렬된 Markdown 테이블을 출력한다.

### TableToHtmlTable (L1113)

복잡한 테이블을 HTML 태그로 변환한다. TableToNativeMarkdown이 불가능할 때 사용된다.

셀 내부 콘텐츠는 SingleLineParser(인라인) 또는 MultiLineParser(블록)에 위임한다.
단독 대시(`-`)는 `<p>-</p>`로 감싸 MDX 리스트 마커 오해석을 방지한다 (L1153).

### StructuredMacroToCallout (L1174)

Confluence 매크로 → Nextra `<Callout>` 변환.

| Confluence 매크로 | Callout type |
|-------------------|--------------|
| `tip` | `default` |
| `info` | `info` |
| `note` | `important` |
| `warning` | `error` |
| `panel` (panelIconText 있음) | `info` + emoji 속성 |

### AdfExtensionToCallout (L1266)

Confluence ADF 확장(새 에디터 형식) → `<Callout>` 변환. `ac:adf-node[type=panel]` 내부의 `ac:adf-attribute[key=panel-type]`으로 패널 유형을 판별한다.

### Attachment (L45)

**생성**: `<ri:attachment>` 노드에서 filename 추출 → Unicode NFC 정규화 → 스크린샷 파일명 정규화 (`스크린샷 2024-08-01 오후 2.50.06.png` → `screenshot-20240801-145006.png`)

**`copy_to_destination()`**: `var/<page_id>/<filename>` → `target/public/<attachment_dir>/<filename>` 복사. 동일 파일이면 skip.

**`as_markdown()`**: 이미지 확장자면 `<img src="..." alt="..." width="..." />`, 아니면 `[caption](path)`.

---

## 전역 상태: `bin/converter/context.py`

변환 중 공유되는 전역 변수와 유틸리티 함수를 제공한다.

### 전역 변수

| 변수 | 타입 | 설정 시점 | 용도 |
|------|------|-----------|------|
| `INPUT_FILE_PATH` | `str` | cli.py main() | 디버그 로깅용 현재 파일 경로 |
| `OUTPUT_FILE_PATH` | `str` | cli.py main() | 출력 파일 경로 |
| `LANGUAGE` | `str` | cli.py main() | 언어 코드 (`ko`/`ja`/`en`) |
| `PAGES_BY_TITLE` | `PagesDict` | `load_pages_yaml()` | 원본 제목 → 페이지 정보 매핑 |
| `PAGES_BY_ID` | `PagesDict` | `load_pages_yaml()` | page_id → 페이지 정보 매핑 |
| `GLOBAL_PAGE_V1` | `Optional[PageV1]` | `set_page_v1()` | 현재 페이지의 V1 메타데이터 |
| `GLOBAL_ATTACHMENTS` | `List[Attachment]` | `set_attachments()` | 현재 페이지의 첨부파일 목록 |
| `GLOBAL_LINK_MAPPING` | `Dict[str, str]` | `build_link_mapping()` | 링크 텍스트 → pageId 매핑 |

### 주요 함수

| 함수 | 용도 |
|------|------|
| `load_pages_yaml(path, by_title, by_id)` | pages.yaml → 두 딕셔너리에 적재. key는 `title_orig` |
| `load_page_v1_yaml(path)` | page.v1.yaml → `PageV1` 딕셔너리 반환 |
| `build_link_mapping(page_v1)` | body.view HTML에서 `<a data-linked-resource-id>` 파싱 → 텍스트→pageId 매핑 |
| `resolve_external_link(text, space_key, title)` | `GLOBAL_LINK_MAPPING`에서 pageId 조회 → Confluence URL 생성 |
| `relative_path_to_titled_page(title)` | 현재 페이지 기준 상대 경로 계산 |
| `calculate_relative_path(current, target)` | 경로 리스트 → `os.path.relpath()` |
| `convert_confluence_url(href)` | Confluence URL → 내부 앵커 또는 상대 경로 |
| `navigable_string_as_markdown(node)` | 텍스트 노드 → Markdown. `<`/`>` 이스케이프, `{}` 백틱 감싸기 |
| `split_into_sentences(line)` | 긴 문단을 마침표 기준으로 문장 분리 (`.` 뒤 공백에서 분리, 숫자 뒤 `.`는 제외) |
| `backtick_curly_braces(text)` | `{word}` → `` `{word}` `` (JSX 충돌 방지) |
| `normalize_screenshots(filename)` | 한국어 스크린샷 파일명 → 표준화된 파일명 |

---

## Sidecar Mapping: `bin/converter/sidecar_mapping.py`

변환 후 XHTML 블록과 MDX 블록의 대응 관계를 기록한다. 역동기화(MDX→Confluence) 지원 목적.

**`generate_sidecar_mapping()` (L22)**: 원본 XHTML + 변환된 MDX를 입력받아:

1. `record_mapping(xhtml)` → XHTML 블록 목록 (`BlockMapping`)
2. `parse_mdx_blocks(mdx)` → MDX 블록 목록 (`MdxBlock`)
3. `_build_mapping_entries()` → 순차 매칭하여 `mapping.yaml` 생성

**출력 형식** (`var/<page_id>/mapping.yaml`):

```yaml
version: 1
source_page_id: "608501837"
generated_at: "2025-01-15T09:30:00Z"
mdx_file: "installation.mdx"
mappings:
  - xhtml_xpath: "/body/p[1]"
    xhtml_type: "paragraph"
    mdx_blocks: [3]
  - xhtml_xpath: "/body/ac:structured-macro[1]"
    xhtml_type: "callout"
    mdx_blocks: [4, 5, 6]
```

---

## \_meta.ts 생성: `generate_meta_from_children()` (cli.py L39)

`children.v2.yaml`에서 자식 페이지 목록을 읽고, `childPosition`으로 정렬하여 Nextra 사이드바용 `_meta.ts`를 생성한다.

```typescript
// target/ko/getting-started/_meta.ts
export default {
  'installation': 'Installation',
  'quick-start': 'Quick Start',
};
```

---

## 변환 결과물 구조

```
target/
├── ko/
│   ├── overview.mdx
│   ├── overview/
│   │   ├── _meta.ts
│   │   ├── system-architecture.mdx
│   │   └── ...
│   ├── getting-started.mdx
│   ├── getting-started/
│   │   ├── _meta.ts
│   │   └── installation.mdx
│   └── ...
└── public/
    ├── overview/system-architecture/
    │   ├── image-20240806-095511.png
    │   └── ...
    └── ...
```

### MDX 출력 형식

```mdx
---
title: '시스템 아키텍처'
confluenceUrl: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/608501837/'
---

import { Callout } from 'nextra/components'

# 시스템 아키텍처

본문 텍스트...

<Callout type="info">
정보 패널 내용
</Callout>

| 열1 | 열2 |
|-----|-----|
| 값1 | 값2 |

<figure data-layout="center" data-align="center">
<img src="/overview/system-architecture/image.png" alt="caption" width="760" />
<figcaption>
caption
</figcaption>
</figure>
```

---

## 설정 파일

| 파일 | 용도 |
|------|------|
| `bin/fetch/config.py` | Confluence 접속 정보 (base_url, space_key, 시작 page_id) |
| `etc/korean-titles-translations.txt` | 한국어 제목 → 영어 제목 매핑. `한국어 \| English` 형식 |

---

## 에러 처리 정책

- **sidecar mapping 생성 실패**: 경고 로그만 남기고 변환은 정상 완료 (cli.py L211)
- **첨부파일 누락**: 경고 로그 + `[filename]()` 폴백 (core.py L566)
- **링크 대상 페이지 미발견**: `#target-title-not-found` 또는 `#link-error` 앵커 사용 (context.py L298, L413)
- **\_meta.ts 생성 실패**: 경고 로그만 남기고 진행 (cli.py L109)
- **개별 페이지 변환 실패**: convert_all.py가 실패 카운트를 집계하고 완료 후 요약 출력 (convert_all.py L154)
