# confluence-mdx 아키텍처

Confluence XHTML 문서를 Nextra용 MDX로 변환하고, MDX 편집 내용을 Confluence에 역반영하는 양방향 변환 시스템의 아키텍처를 설명한다.

## 용어 정의

| 용어 | 방향 | 패키지 | 설명 |
|------|------|--------|------|
| **Forward Conversion (정순변환)** | XHTML → MDX | `converter/` | Confluence XHTML을 MDX로 변환 |
| **Backward Conversion (역순변환)** | MDX → XHTML | `mdx_to_storage/` | MDX를 Confluence Storage XHTML로 변환 |
| **Reverse Sync (역반영)** | MDX 편집 → Confluence 반영 | `reverse_sync/` | MDX 교정 내용을 Confluence에 반영하는 파이프라인 |
| **Round Trip Verification (라운드트립 검증)** | MDX → XHTML → MDX → 비교 | — | 변경된 MDX를 역순변환 후, 다시 정순변환하여 원래 MDX와 동일한지 검증 |

**라운드트립 검증 흐름:**

```
변경된 MDX ──(역순변환)──▶ XHTML ──(정순변환)──▶ 재변환 MDX
    │                                                │
    └──────────────── 동일한지 비교 ──────────────────┘
```

---

## 전체 구조

시스템은 세 개의 파이프라인과 하나의 메타데이터 시스템으로 구성된다.

```
                           Sidecar 시스템
                    (mapping.yaml, roundtrip.json)
                         ┌──────────┐
                         │          │
  ┌──────────────────────┼──────────┼──────────────────────┐
  │                      │          │                      │
  ▼                      ▼          ▼                      ▼
┌─────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Forward │   │ Backward        │   │ Reverse Sync     │
│Converter│   │ Converter       │   │                  │
│ XHTML → │   │ MDX → XHTML    │   │ (MDX 편집 →      │
│ MDX     │   │                 │   │  Confluence 반영) │
│         │   │                 │   │                  │
│converter│   │mdx_to_storage/  │   │reverse_sync/     │
└─────────┘   └──────────────────┘   └──────────────────┘
```

| 파이프라인 | 방향 | 패키지 | 용도 |
|-----------|------|--------|------|
| Forward Converter (정순변환) | Confluence XHTML → MDX | `converter/` | 초기 문서 마이그레이션 |
| Backward Converter (역순변환) | MDX → Confluence Storage XHTML | `mdx_to_storage/` | 역반영 시 XHTML 재생성, 라운드트립 검증 |
| Reverse Sync (역반영) | MDX 편집 → XHTML 패치 → Confluence 업데이트 | `reverse_sync/` | MDX 교정 내용을 Confluence에 반영 |

---

## Forward Converter: XHTML → MDX (`converter/`)

Confluence API에서 수집한 XHTML을 Nextra용 MDX 파일로 변환하는 정순변환기이다.

### 실행 흐름

```
Confluence API
      │
      ▼
fetch_cli.py                ← 데이터 수집 (4-Stage 파이프라인)
      │
      ▼
var/                        ← 로컬 캐시 (page.xhtml, 메타데이터, 첨부파일)
      │
      ▼
convert_all.py              ← 배치 변환 (pages.yaml 순회, subprocess 호출)
      │
      ▼
converter/cli.py            ← 단일 페이지 변환 진입점
      │
      ├─▶ target/ko/*.mdx   ← MDX 출력
      └─▶ target/public/    ← 이미지 등 첨부파일
```

### 데이터 수집 (`fetch/`)

`fetch_cli.py`가 Confluence REST API를 호출하여 로컬에 원시 데이터를 캐싱한다.

| 모듈 | 역할 |
|------|------|
| `fetch/processor.py` | 4-Stage 파이프라인 오케스트레이터 |
| `fetch/stages.py` | Stage 1~4 구현 |
| `fetch/api_client.py` | Confluence REST API 클라이언트 |
| `fetch/config.py` | 접속 설정 (base_url, space_key, 시작 page_id) |
| `fetch/models.py` | 데이터 모델 (Page 등) |
| `fetch/file_manager.py` | YAML/파일 I/O |
| `fetch/translation.py` | 제목 번역 서비스 |

**4-Stage 파이프라인:**

1. **Stage 1 — API 수집**: Confluence REST API → `page.v1.yaml`, `page.v2.yaml`, `children.v2.yaml`, `attachments.v1.yaml`
2. **Stage 2 — XHTML 추출**: API 응답에서 본문 추출 → `page.xhtml`
3. **Stage 3 — 첨부파일 다운로드** (`--attachments`): 바이너리 파일 → `var/<page_id>/`
4. **Stage 4 — 문서 목록**: 전체 페이지 메타데이터 → `var/pages.yaml`

**실행 모드**: `--remote`(전체 fetch), `--recent`(최근 수정만, 기본값), `--local`(로컬만)

### 변환 엔진 (`converter/`)

| 모듈 | 역할 |
|------|------|
| `converter/cli.py` | 단일 페이지 변환 진입점 |
| `converter/core.py` | 변환 클래스 (1,438줄) |
| `converter/context.py` | 전역 상태, 유틸리티 (665줄) |
| `converter/sidecar_mapping.py` | XHTML↔MDX 블록 매핑 생성 (160줄) |

**클래스 계층:**

```
ConfluenceToMarkdown                ← 오케스트레이터
├── 첨부파일 로드: Attachment 인스턴스 생성
├── import문 결정: Callout 사용 여부 검사
├── frontmatter 생성: title, confluenceUrl
├── 본문 변환:
│   └── MultiLineParser             ← 블록 레벨 변환
│       ├── SingleLineParser         ← 인라인 변환
│       ├── TableToNativeMarkdown    ← 단순 테이블
│       ├── TableToHtmlTable         ← 복잡 테이블
│       ├── StructuredMacroToCallout ← Confluence 매크로 → Callout
│       └── AdfExtensionToCallout   ← ADF 확장 → Callout
└── 최종 조합: remark + imports + body
```

**주요 변환 매핑:**

| XHTML 노드 | MDX 출력 |
|-------------|----------|
| `h1`~`h6` | `##`~`######` (레벨 +1 조정) |
| `p`, `div` | 문단, 인라인은 SingleLineParser |
| `ac:structured-macro` (tip/info/note/warning) | `<Callout>` |
| `ac:structured-macro` (code) | ` ```language ` 코드 블록 |
| `ac:structured-macro` (expand) | `<details><summary>` |
| `ac:structured-macro` (toc) | 스킵 (Nextra TOC 사용) |
| `ac:structured-macro` (status) | `<Badge>` |
| `ac:adf-extension` (panel) | `<Callout>` |
| `table` | 네이티브 Markdown 테이블 또는 HTML 테이블 |
| `ac:image` | `<figure>` + `<img>` |
| `ac:link` | 내부/외부 링크 해석 |
| `ac:emoticon` | 이모지 문자 변환 |
| `time` | 언어별 날짜 포맷 |

**인라인 변환 (SingleLineParser):**

| XHTML 노드 | Markdown 출력 |
|-------------|---------------|
| `strong` | `**text**` (헤딩 내에서는 무시) |
| `em` | `*text*` |
| `code` | `` `text` `` |
| `a` | `[text](href)` (Confluence URL → 내부 링크 변환) |
| `NavigableString` | 텍스트 (이스케이프, `{}` 백틱 감싸기) |

**링크 변환 (`convert_ac_link`):** `<ac:link>` 내부의 `<ri:page>`를 분석하여 `PAGES_BY_TITLE`에 있으면 상대 경로, 없으면 Confluence URL로 변환한다.

### 변환 시 생성되는 파일

| 파일 | 위치 | 설명 |
|------|------|------|
| `*.mdx` | `target/{lang}/` | 변환된 MDX 문서 |
| `_meta.ts` | `target/{lang}/*/` | Nextra 사이드바 메타데이터 |
| 첨부파일 | `target/public/` | 이미지 등 |
| `mapping.yaml` | `var/<page_id>/` | XHTML↔MDX 블록 매핑 (sidecar) |

---

## Backward Converter: MDX → XHTML (`mdx_to_storage/`)

MDX 텍스트를 Confluence Storage Format XHTML로 변환하는 역순변환기이다. Forward Converter의 역방향이며, 두 가지 목적으로 사용된다:
1. **라운드트립 검증**: 역순변환 결과를 원본 `page.xhtml`과 비교하거나, 역순변환 → 정순변환 경로로 MDX 동일성을 검증
2. **역반영 시 XHTML 재생성**: 변경된 MDX 블록을 XHTML로 재생성 (insert 패치)

### 모듈 구성

| 모듈 | 줄 수 | 역할 |
|------|-------|------|
| `parser.py` | 474 | MDX 텍스트 → Block AST 파싱 |
| `emitter.py` | 398 | Block AST → Confluence Storage XHTML 생성 |
| `inline.py` | 95 | 인라인 Markdown → XHTML 변환 |
| `link_resolver.py` | 158 | MDX 상대 경로 → Confluence `<ac:link>` 변환 |

### 파싱 → 변환 흐름

```
MDX 텍스트
    │
    ▼
parse_mdx()              ← parser.py: 줄 단위 상태머신
    │
    ▼
Block[] (AST)            ← Block(type, content, level, language, children, attrs)
    │
    ▼
emit_document()          ← emitter.py: 블록별 XHTML 생성
    │
    ├── convert_inline()  ← inline.py: 인라인 마크업 변환
    └── LinkResolver      ← link_resolver.py: 내부 링크 해석
    │
    ▼
Confluence Storage XHTML (문자열)
```

### Block 타입

| Block type | MDX 소스 | XHTML 출력 |
|-----------|----------|-----------|
| `frontmatter` | `---` YAML `---` | 스킵 (메타데이터) |
| `heading` | `## Title` | `<h2>Title</h2>` |
| `paragraph` | 텍스트 | `<p>텍스트</p>` |
| `code_block` | ` ```lang ` | `<ac:structured-macro ac:name="code">` |
| `list` | `* item` / `1. item` | `<ul>/<ol><li>...</li></ul>` |
| `callout` | `<Callout type="info">` | `<ac:structured-macro ac:name="info">` |
| `figure` | `<figure>` | `<ac:image><ri:attachment>` |
| `details` | `<details>` | `<ac:structured-macro ac:name="expand">` |
| `badge` | `<Badge>` | `<ac:structured-macro ac:name="status">` |
| `table` | `\| h1 \| h2 \|` | `<table><tbody><tr>` |
| `blockquote` | `> text` | `<blockquote><p>text</p></blockquote>` |
| `html_block` | `<table>`, `<div>` 등 | 인라인 링크만 변환하여 통과 |
| `import_statement` | `import { ... }` | 스킵 |
| `empty` | 빈 줄 | 스킵 |

### 인라인 변환 (`inline.py`)

| Markdown | XHTML |
|----------|-------|
| `` `code` `` | `<code>code</code>` |
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` | `<em>italic</em>` |
| `[text](url)` | `<a href="url">text</a>` 또는 `<ac:link>` (내부 링크) |

### 링크 해석 (`link_resolver.py`)

`var/pages.yaml`에서 페이지 메타데이터를 로드하여, MDX 상대 경로를 Confluence 페이지 제목으로 역매핑한다.

```
MDX 상대 경로                     Confluence XHTML
../../user-guide          →   <ac:link>
                                 <ri:page ri:content-title="사용자 가이드" />
                                 <ac:link-body>사용자 가이드</ac:link-body>
                               </ac:link>
```

**해석 알고리즘:**
1. 외부 URL(`http://`, `https://`) / 앵커(`#`) → 통과 (해석 안 함)
2. 현재 페이지의 경로(`pages.yaml`의 `path` 필드) 기준으로 상대 경로를 절대 경로로 변환
3. 절대 경로로 `pages.yaml`에서 페이지 검색 → `title_orig`을 사용하여 `<ac:link>` 생성
4. 미발견 시 일반 `<a>` 링크로 폴백

---

## Reverse Sync: MDX 편집 → Confluence 반영 (`reverse_sync/`)

MDX 파일의 교정 내용을 Confluence XHTML에 반영한다. 블록 단위 diff를 XHTML 패치로 변환하는 정밀한 파이프라인이다.

### 전체 흐름

```
원본 MDX (main 브랜치)    교정된 MDX (작업 브랜치)
        │                        │
        ▼                        ▼
  parse_mdx_blocks()       parse_mdx_blocks()
        │                        │
        ▼                        ▼
   MdxBlock[]               MdxBlock[]
        │                        │
        └────────┬───────────────┘
                 ▼
          diff_blocks()          ← 블록 단위 diff
                 │
                 ▼
          BlockChange[]          ← modified / added / deleted
                 │
        ┌────────┴────────┐
        ▼                 ▼
  record_mapping()   Sidecar 인덱스
  (원본 XHTML)       (mapping.yaml)
        │                 │
        └────────┬────────┘
                 ▼
          build_patches()        ← MDX 변경 → XHTML 패치 변환
                 │
                 ▼
          patch_xhtml()          ← BeautifulSoup으로 XHTML 수정
                 │
                 ▼
          verify_roundtrip()     ← 라운드트립 검증 (XHTML→정순변환→MDX→비교)
                 │
                 ▼
       Confluence API push       ← (선택) 실제 반영
```

### 모듈 구성

| 모듈 | 줄 수 | 역할 |
|------|-------|------|
| `mdx_block_parser.py` | 129 | MDX → MdxBlock 시퀀스 파싱 (splice rehydrator 호환용 유지) |
| `block_diff.py` | 90 | 두 MdxBlock 시퀀스 diff |
| `mapping_recorder.py` | 210 | XHTML → BlockMapping 추출 |
| `sidecar.py` | 524 | Roundtrip sidecar + 매핑 인덱스 |
| `fragment_extractor.py` | 204 | XHTML byte-exact 프래그먼트 추출 |
| `patch_builder.py` | 547 | BlockChange → XHTML 패치 변환 |
| `text_normalizer.py` | 7 | Backward-compat re-export (`text_utils` 위임) |
| `text_transfer.py` | 79 | 텍스트 변경을 XHTML에 전사 |
| `xhtml_patcher.py` | 333 | 패치를 XHTML에 적용 |
| `roundtrip_verifier.py` | 174 | 패치 결과 라운드트립 검증 |
| `mdx_to_xhtml_inline.py` | 240 | 삽입 패치용 MDX → XHTML 블록 변환 (`mdx_to_storage.inline` 활용) |
| `rehydrator.py` | 149 | Sidecar 기반 무손실 XHTML 복원 (fast path + splice + fallback) |
| `byte_verify.py` | 126 | Byte-equal 검증 (document-level + forced-splice) |
| `confluence_client.py` | 65 | Confluence REST API 클라이언트 |

### 단계별 상세

#### Step 1: MDX 블록 파싱 (`mdx_to_storage/parser.py`)

MDX 텍스트를 줄 단위 상태머신으로 파싱하여 블록 시퀀스를 생성한다. (`mdx_block_parser.py`는 backward-compat re-export 래퍼)

```python
Block(type, content, level, language, children, attrs, line_start, line_end)
# type: "frontmatter" | "import_statement" | "heading" | "paragraph" |
#       "code_block" | "list" | "html_block" | "callout" | "figure" |
#       "details" | "badge" | "table" | "blockquote" | "empty"
```

#### Step 2: 블록 Diff (`block_diff.py`)

SequenceMatcher 기반으로 원본/교정 블록 시퀀스를 정렬하고 변경 사항을 추출한다.

```python
BlockChange(index, change_type, old_block, new_block)
# change_type: "modified" | "added" | "deleted"
```

#### Step 3: XHTML 매핑 추출 (`mapping_recorder.py`)

원본 XHTML을 BeautifulSoup으로 파싱하여 블록 레벨 요소를 추출하고 XPath를 부여한다.

```python
BlockMapping(block_id, type, xhtml_xpath, xhtml_text, xhtml_plain_text,
             xhtml_element_index, children)
# type: "heading" | "paragraph" | "list" | "code" | "table" | "html_block"
# xhtml_xpath: "p[3]", "macro-info[1]" 등
```

Callout 매크로, ADF 패널 내부의 자식 요소는 `children` 필드로 재귀 추출한다.

#### Step 4: Sidecar 인덱스 구축 (`sidecar.py`)

`mapping.yaml`을 로드하여 O(1) 조회 인덱스를 구축한다.

```python
mdx_to_sidecar   = build_mdx_to_sidecar_index(mappings)    # MDX 블록 인덱스 → SidecarEntry
xpath_to_mapping = build_xpath_to_mapping(block_mappings)   # XPath → BlockMapping
```

**조회 체인:** `MDX 블록 인덱스 → SidecarEntry → BlockMapping → XHTML XPath`

#### Step 5: 패치 생성 (`patch_builder.py`)

각 `BlockChange`에 대해 sidecar 인덱스로 대응하는 XHTML 요소를 찾고, 텍스트 변경을 패치로 변환한다.

- **Modified**: `text_normalizer`로 MDX를 일반 텍스트로 정규화 → `text_transfer`로 XHTML 텍스트에 변경 전사
- **Added**: `mdx_to_xhtml_inline`로 새 MDX 블록을 XHTML 요소로 변환 → insert 패치
- **Deleted**: 대응 XPath 요소 삭제 패치
- **리스트/테이블**: 항목별 세분화된 패치 (항목 매칭, 셀 매칭)

자식 매핑 해석 (`_resolve_child_mapping`): Callout 내부 단락 등은 정규화된 텍스트로 4단계 비교하여 매칭한다.

#### Step 6: XHTML 패치 적용 (`xhtml_patcher.py`)

BeautifulSoup으로 패치를 적용한다. 실행 순서: **delete → insert → modify** (인덱스 시프트 방지를 위해 XPath를 사전 해석).

#### Step 7: 라운드트립 검증 (`roundtrip_verifier.py`)

패치된 XHTML을 정순변환(Forward Conversion)하여 MDX로 되돌린 뒤, 교정된 MDX와 비교한다. 두 MDX가 동일하면 패치가 정확하게 적용된 것이다. 정규화 항목:
- Trailing whitespace, 날짜 포맷 (한국어 ↔ 영어), 테이블 패딩, h1 헤딩 (페이지 제목), `<td>` 내 줄 합치기, 코드 블록 HTML 엔티티

### Reverse Sync 생성 파일

| 파일 | 위치 | 설명 |
|------|------|------|
| `reverse-sync.diff.yaml` | `var/<page_id>/` | 블록 변경 사항 |
| `reverse-sync.mapping.original.yaml` | `var/<page_id>/` | 원본 XHTML 매핑 |
| `reverse-sync.mapping.patched.yaml` | `var/<page_id>/` | 패치 후 XHTML 매핑 |
| `reverse-sync.patched.xhtml` | `var/<page_id>/` | 패치된 XHTML |
| `reverse-sync.result.yaml` | `var/<page_id>/` | 검증 결과 (pass/fail, diff) |
| `verify.mdx` | `var/<page_id>/` | 라운드트립 검증용: 패치된 XHTML을 정순변환한 MDX |

---

## Sidecar 시스템

Forward Converter와 Reverse Sync를 연결하는 메타데이터 시스템이다. 두 종류의 sidecar 파일이 있다.

### 1. Mapping Sidecar (`mapping.yaml`)

Forward Converter 실행 시 `converter/sidecar_mapping.py`가 생성한다. XHTML 블록과 MDX 블록의 대응 관계를 기록한다.

**위치:** `var/<page_id>/mapping.yaml`

```yaml
version: 1
source_page_id: "608501837"
generated_at: "2025-01-15T09:30:00Z"
mdx_file: "installation.mdx"
mappings:
  - xhtml_xpath: "p[1]"
    xhtml_type: "paragraph"
    mdx_blocks: [3]
  - xhtml_xpath: "macro-info[1]"
    xhtml_type: "callout"
    mdx_blocks: [4, 5, 6]
```

**생성 과정:**
1. `record_mapping(xhtml)` → XHTML 블록 목록 (`BlockMapping`)
2. `parse_mdx_blocks(mdx)` → MDX 블록 목록 (`MdxBlock`)
3. `_build_mapping_entries()` → 순차 매칭하여 매핑 기록

**사용처:** Reverse Sync에서 `build_mdx_to_sidecar_index()`로 O(1) 조회 인덱스를 구축한다.

### 2. Roundtrip Sidecar (`expected.roundtrip.json`)

Backward Converter의 검증 인프라에서 사용한다. XHTML 원본을 블록 단위 프래그먼트로 분해하여 저장하며, **프래그먼트 재조립이 원본과 byte-equal**함을 보장한다.

**위치:** `tests/testcases/<case_id>/expected.roundtrip.json`

**스키마 (v2):**

```json
{
  "schema_version": "2",
  "page_id": "544381877",
  "mdx_sha256": "<MDX 전체 SHA256>",
  "source_xhtml_sha256": "<XHTML 전체 SHA256>",
  "blocks": [
    {
      "block_index": 0,
      "xhtml_xpath": "h2[1]",
      "xhtml_fragment": "<h2>Title</h2>",
      "mdx_content_hash": "<블록 MDX SHA256>",
      "mdx_line_range": [3, 3],
      "lost_info": null
    }
  ],
  "separators": ["\n"],
  "document_envelope": {
    "prefix": "",
    "suffix": "\n"
  }
}
```

**핵심 불변조건:**

```
envelope.prefix
  + blocks[0].xhtml_fragment
  + separators[0]
  + blocks[1].xhtml_fragment
  + separators[1]
  + ...
  + blocks[N].xhtml_fragment
  + envelope.suffix
== page.xhtml (byte-equal)
```

**프래그먼트 추출 (`fragment_extractor.py`):** BeautifulSoup으로 태그 시퀀스를 식별한 뒤, 원문을 직접 스캔하여 정확한 태그 경계를 추출한다. BS4의 속성 재정렬, 공백 정규화, self-closing 변환 문제를 회피한다.

**무손실 복원 (`rehydrator.py`):** 세 가지 경로로 XHTML을 복원한다:

1. **Fast path** — MDX 전체 SHA256이 sidecar와 일치하면 `reassemble_xhtml()`으로 원본을 document-level byte-equal 복원
2. **Splice path** — 블록 단위 해시 매칭. sidecar 블록을 순회하면서 MDX 대응 없는 블록(이미지 등)은 원본 fragment 보존, 해시 일치 블록은 원본 fragment 사용, 불일치 블록은 emitter 폴백
3. **Fallback path** — 전체 emitter 재생성 (byte-equal 미보장)

---

## 검증 인프라

### 역순변환 검증 (`mdx_to_storage_xhtml_verify`)

Backward Converter의 출력을 원본 `page.xhtml`과 비교한다. XHTML을 정규화(beautify)한 뒤 diff를 생성한다.

| 모듈 | 역할 |
|------|------|
| `mdx_to_storage_xhtml_verify.py` | 테스트케이스 검증 + 실패 원인 분류 (P1/P2/P3) |
| `mdx_to_storage_xhtml_cli.py final-verify` | 최종 검증 + 목표 달성 확인 (CLI 서브커맨드) |
| `mdx_to_storage_xhtml_cli.py baseline` | 베이스라인 측정 + 리포트 생성 (CLI 서브커맨드) |

**실패 원인 분류:** diff 패턴을 분석하여 자동으로 이슈 카테고리를 분류한다.
- **P1**: 내부 링크 미해석, 테이블 구조 불일치 등 (기능적 오류)
- **P2**: 매크로 속성 차이, 코드 블록 언어 누락 등
- **P3**: 공백, 정렬, 포맷팅 차이

### Byte-equal 검증 (`byte_verify`)

Roundtrip sidecar를 사용하여 byte 수준 일치를 검증한다. 정규화 없이 원문 그대로 비교한다. 두 가지 검증 모드를 제공한다:

- **`verify_case_dir()`** — document-level fast path 사용 (production 경로)
- **`verify_case_dir_splice()`** — forced-splice 경로 사용 (sidecar 구조 검증)

```python
ByteVerificationResult(case_id, passed, reason, first_mismatch_offset)
# reason: "byte_equal" | "byte_mismatch" | "sidecar_missing"

SpliceVerificationResult(case_id, passed, reason, first_mismatch_offset,
                         matched_count, emitted_count, total_blocks)
# reason: "byte_equal_splice" | "byte_mismatch_splice" | "sidecar_missing"
```

### 현재 배치 검증 결과

| 검증 기준 | 결과 | 비고 |
|-----------|------|------|
| normalize-diff (emitter 단독) | **0/21 pass** | 역순변환기 단독 출력 |
| document-level sidecar (Lossless v1) | **21/21 pass** | MDX 미변경 시 원본 XHTML 그대로 반환 (trivial) |
| L1 fragment reassembly | **21/21 pass** | sidecar v2 프래그먼트 재조립 byte-equal |
| **block-level splice (L2)** | **21/21 pass** | forced-splice 경로로 블록 단위 byte-equal |

**Emitter 단독 실패 원인 분포:**

| 원인 | 건수 | 비가역 여부 |
|------|------|-------------|
| `ordered_list_start_mismatch` | 12 | emitter 수정 가능 (L5) |
| `internal_link_unresolved` (`#link-error`) | 7 | **비가역** — 정순변환에서 원본 정보 소실 |
| `attachment_filename_mismatch` | 7 | **비가역** — 정순변환에서 파일명 정규화 |
| `image_block_structure_mismatch` | 5 | emitter 수정 가능 (L5) |
| `emoticon_representation_mismatch` | 4 | **비가역** — 정순변환에서 shortname 소실 |
| `adf_extension_panel_mismatch` | 3 | **비가역** — ADF 구조가 MDX에 없음 |

비가역 항목은 emitter 개선으로 해결할 수 없으며, 정순변환 시 sidecar의 `lost_info`에 원본 정보를 보존해야 한다 (Phase L3).

### CJK 인라인 요소 공백 규칙

Markdown 인라인 요소(bold, italic, code, link)와 CJK 문자의 인접 시 CommonMark flanking delimiter 규칙에 의해 공백 처리가 달라진다.

| 요소 | flanking 규칙 | CJK 인접 시 공백 필요 여부 |
|------|-------------|------------------------|
| Code span (`` ` ``) | 없음 | 불필요 — 정규화 가능 |
| Link `[]()` | 없음 | 불필요 — 정규화 가능 |
| Bold `**` / Italic `*` | 있음 | 내부에 구두점이 있을 때만 필요 |
| Bold `__` / Italic `_` | 있음 (엄격) | CJK 문서에서 사용 불가 |
| Strikethrough `~~` | 있음 | Bold/Italic과 동일 |

**정규화 전략:** 검증 시 code span, link, trailing whitespace 주변의 공백 차이는 안전하게 정규화 가능하다. Bold/Italic은 delimiter 내부의 구두점 여부를 확인해야 한다.

---

## 중간 데이터 파일 종합

### `var/` 디렉토리 (런타임 데이터)

```
var/
├── pages.yaml                           ← 전체 페이지 메타데이터
└── <page_id>/
    ├── page.v1.yaml                     ← V1 API 메타데이터 (body.view HTML 포함)
    ├── page.v2.yaml                     ← V2 API 메타데이터
    ├── page.xhtml                       ← Confluence XHTML 본문
    ├── children.v2.yaml                 ← 자식 페이지 목록 + 정렬 순서
    ├── attachments.v1.yaml              ← 첨부파일 메타데이터
    ├── mapping.yaml                     ← XHTML↔MDX 매핑 sidecar (Forward Converter 생성)
    ├── reverse-sync.diff.yaml           ← 블록 변경 diff (Reverse Sync 생성)
    ├── reverse-sync.mapping.original.yaml
    ├── reverse-sync.mapping.patched.yaml
    ├── reverse-sync.patched.xhtml       ← 패치된 XHTML
    ├── reverse-sync.result.yaml         ← 검증 결과
    ├── verify.mdx                       ← 라운드트립 검증용: 패치된 XHTML을 정순변환한 MDX
    └── <attachment files>               ← 다운로드된 첨부파일
```

### `tests/testcases/` 디렉토리 (테스트 데이터)

```
tests/testcases/
└── <case_id>/
    ├── page.xhtml                       ← 원본 Confluence XHTML
    ├── expected.mdx                     ← 기대 MDX 출력
    ├── output.mdx                       ← 실제 변환 결과 (테스트 시 생성)
    └── expected.roundtrip.json          ← Roundtrip sidecar v2 (블록 프래그먼트)
```

### `pages.yaml` 엔트리 구조

```yaml
- page_id: "608501837"
  title: "English Title"
  title_orig: "한국어 제목"
  breadcrumbs: ["Docs", "시작하기", "설치"]
  breadcrumbs_en: ["Docs", "Getting Started", "Installation"]
  path: ["getting-started", "installation"]
```

`path` 필드가 출력 디렉토리 구조와 파일명을 결정한다.

---

## CLI 명령어

### 데이터 수집 및 정순변환 (Forward Conversion)

| 명령어 | 설명 |
|--------|------|
| `fetch_cli.py --recent` | 최근 수정 페이지 수집 |
| `convert_all.py` | pages.yaml 기반 전체 배치 변환 (XHTML → MDX) |
| `converter/cli.py <input> <output>` | 단일 페이지 XHTML → MDX 변환 |

### 역순변환 (Backward Conversion)

| 명령어 | 설명 |
|--------|------|
| `mdx_to_storage_xhtml_cli.py convert <mdx>` | MDX → XHTML 변환 |
| `mdx_to_storage_xhtml_cli.py verify <mdx> --expected <xhtml>` | 단일 케이스 검증 |
| `mdx_to_storage_xhtml_cli.py batch-verify` | 테스트케이스 배치 검증 (정규화 diff 기반) |
| `mdx_to_storage_xhtml_cli.py final-verify` | 최종 검증 + 목표 달성 확인 리포트 |
| `mdx_to_storage_xhtml_cli.py baseline` | Phase 1 baseline 측정 리포트 |

### 검증 (Verify)

| 명령어 | 설명 |
|--------|------|
| `mdx_to_storage_xhtml_byte_verify_cli.py --testcases-dir <dir>` | byte-equal 배치 검증 |

### Sidecar 생성

| 명령어 | 설명 |
|--------|------|
| `mdx_to_storage_roundtrip_sidecar_cli.py generate --mdx <path> --xhtml <path> --output <path>` | 단일 sidecar 생성 |
| `mdx_to_storage_roundtrip_sidecar_cli.py batch-generate --testcases-dir <dir>` | 테스트케이스 배치 sidecar 생성 |

### 역반영 (Reverse Sync)

| 명령어 | 설명 |
|--------|------|
| `reverse_sync_cli.py verify <mdx>` | 단일 파일 역반영 검증 (dry-run) |
| `reverse_sync_cli.py push <mdx>` | 단일 파일 Confluence 반영 |
| `reverse_sync_cli.py debug <mdx>` | 검증 + 상세 diff 출력 |
| `reverse_sync_cli.py --branch <branch>` | 브랜치 전체 배치 검증/반영 |

---

## 알려진 제약과 구조적 이슈

### 정보 손실 카테고리

Forward Conversion(XHTML → MDX)은 구조적으로 다음 정보를 손실한다:

| 카테고리 | 설명 |
|---------|------|
| Emoticon 단축명 | `ac:name="tick"` → `✔️` (다대일 매핑) |
| 첨부파일명 | Unicode → NFC 정규화 + 스크린샷 파일명 변환 |
| 링크 대상 | pages.yaml 누락 → `#link-error` |
| ADF 확장 | 복잡한 구조 → 단순 Callout |
| Layout 래퍼 | `ac:layout` → 제거 |
| 인라인 코멘트 | 메타데이터 스트립 |
| Confluence 속성 | macro-id 등 19개 속성 |
| 속성 순서 | DOM 파싱 시 재정렬 |
| Self-closing 표기 | `<br/>` vs `<br />` |
| 블록 간 공백 | 정규화 |

### Converter 모듈 구조적 이슈

- **전역 가변 상태**: `context.py`의 모듈 수준 전역 변수로 인해 in-process 병렬화 불가. 현재는 subprocess 격리로 우회.
- **테이블 rowspan/colspan**: 동시 사용 시 셀 위치 추적 오류 가능.

---

## 로드맵: Byte-equal 라운드트립 구현 계획

### Phase 진행 상태

| Phase | 범위 | 상태 | PR |
|-------|------|------|-----|
| L0 | 코드 통합 (`lossless_roundtrip` → `reverse_sync` 흡수) | **완료** | #791 |
| L1 | Roundtrip Sidecar v2 + block fragment 추출 | **완료** | #792 |
| L2 | Block alignment + splice rehydrator | **완료** | #794 |
| L3 | Forward Conversion 정보 보존 강화 (`lost_info`) | 미착수 | — |
| L4 | Metadata-enhanced emitter + patcher | 미착수 | — |
| L5 | Backward Converter 정확도 개선 | 미착수 | — |
| L6 | CI gate 전환 (byte-equal을 기본 게이트로) | 미착수 | — |

### Phase L2: 블록 정렬 + Splice Rehydrator ✅

`rehydrator.py`에 `splice_rehydrate_xhtml()` 함수를 추가하여 블록 단위 splice 경로를 구현했다. Sidecar 블록 기준으로 순회하면서 MDX content 블록과 해시 매칭한다.

**Splice 알고리즘 (`splice_rehydrate_xhtml`):**

```
MDX → parse_mdx_blocks() → content 블록 추출 (frontmatter, empty, import 제외)

Sidecar 블록 순회 (XHTML fragment 기준):
  ├── mdx_content_hash 없음 → 원본 fragment 보존 (이미지, 빈 단락 등)
  ├── hash 일치 → 원본 xhtml_fragment 사용 (sidecar)
  └── hash 불일치 → emit_block() emitter 폴백

envelope.prefix + fragments[0] + separators[0] + ... + envelope.suffix → XHTML
```

**설계 포인트:** MDX content 블록이 아닌 **sidecar 블록을 기준으로 순회**하고, MDX 포인터를 별도로 관리한다. XHTML에는 MDX 대응이 없는 블록(이미지, 빈 단락, macro-only 요소)이 존재하므로, MDX 기준 순회 시 이러한 블록이 누락되어 separator 정렬이 깨진다.

**결과:** `SpliceResult(xhtml, matched_count, emitted_count, total_blocks, block_details)` — 각 블록의 복원 방법(sidecar/emitter/preserved)을 추적한다.

**검증 결과:** 21/21 forced-splice byte-equal 통과.

### Phase L3: Forward Conversion 정보 보존

`converter/core.py`의 정순변환(Forward Conversion) 과정에서 손실되는 정보를 sidecar의 `lost_info` 필드에 기록한다.

| 필드 | 대상 | 저장 내용 |
|------|------|----------|
| `emoticons[]` | `ac:emoticon` 태그 | shortname, raw XHTML |
| `links[]` | `#link-error` 링크 | 원본 `ri:content-title`, `ri:space-key`, raw XHTML |
| `filenames[]` | 정규화된 파일명 | 원본 `ri:filename` |
| `adf_extensions[]` | `ac:adf-extension` | raw XHTML 전체 |
| `stripped_attrs` | 제거된 속성 19종 | `{attr_name: value}` |
| `layout_wrapper` | `ac:layout` 래핑 | 래핑 구조 raw XHTML |

**인수 기준:** 비가역 정보를 포함하는 모든 블록에서 `lost_info`에 해당 원본 정보 존재 + 기존 splice 21/21 유지

### Phase L4: 메타데이터 활용 Emitter + Patcher

변경된 블록을 재생성할 때 `lost_info`를 활용하여 원본에 가까운 XHTML을 생성한다.

- Emoticon 패치: Unicode 이모지 → 원본 `<ac:emoticon>` 태그
- 링크 패치: `#link-error` → 원본 `<ac:link>` 태그
- 파일명 패치: 정규화된 이름 → 원본 `ri:filename`
- ADF 패치: Callout → 원본 `ac:adf-extension` raw

**인수 기준:** partial edit 시 unchanged blocks byte-equal 유지 + changed blocks well-formed XHTML 생성

### Phase L5: Backward Converter 정확도 개선

역순변환기(Backward Converter)의 XHTML 출력 품질을 개선한다.

- `<ol>` 생성 시 `start="1"` 속성 추가 (12건 영향)
- `<br/>` → `<br />` 표기 통일
- 리스트 내 `<ac:image>` 구조 수정 (5건)
- `<details>` → `expand` 매크로 매핑 개선
- `<Badge>` → `status` 매크로 매핑 개선

**인수 기준:** emitter 개선 항목별 단위 테스트 통과 + block-level splice 21/21 유지

### Phase L6: CI Gate 전환

Byte-equal 검증을 CI의 기본 게이트로 설정한다.

- `byte_verify` CLI를 CI 스크립트에 통합
- 기존 normalize-verify를 `--diagnostic` 모드로 전환
- Byte mismatch → build fail (exit code 1)

**인수 기준:** CI pipeline에서 byte-equal gate 활성화, 21/21 pass

### Reverse Sync Phase 3: 전면 재구성

문서 구조, 위치, 이름 변경을 포함한 전면 재구성을 Confluence에 반영한다. Phase 2의 SequenceMatcher를 확장하여 이동(reorder) 감지, Confluence API 페이지 이동/이름 변경 연동, 페이지 트리 구조 관리를 구현한다. 별도 설계 필요.
