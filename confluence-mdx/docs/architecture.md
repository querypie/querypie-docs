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
| `list` | `* item` / `1. item` | `<ul>/<ol start="1"><li>...</li></ul>` |
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
| `<Badge color="X">text</Badge>` | `<ac:structured-macro ac:name="status">` (L5) |

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

현재 reverse-sync는 "텍스트만 덮어쓰는 간단한 패처"가 아니라, MDX diff를 XHTML DOM에 보수적으로 되돌려 넣고 다시 forward converter로 검증한 뒤에만 통과시키는 파이프라인입니다. 2026-03 이후 구현은 sidecar 기반 identity preservation과 fragment replacement를 중심으로 재편되었고, 기존 문서에 남아 있던 `text_transfer.py`, `list_patcher.py`, `table_patcher.py` 중심 설명은 더 이상 현재 상태를 반영하지 않습니다.

### 전체 흐름

```
원본 MDX (main / testcase original.mdx)     교정 MDX (작업 브랜치 / improved.mdx)
                  │                                          │
                  ├──────────── parse_mdx_blocks() ───────────┤
                  ▼                                          ▼
             original_blocks                           improved_blocks
                         └──────── diff_blocks() ────────┘
                                      │
                                      ▼
                             BlockChange[] + alignment
                                      │
             ┌────────────────────────┼────────────────────────┐
             ▼                        ▼                        ▼
   record_mapping(page.xhtml)   generate_sidecar_mapping()   build_sidecar()
   (현재 XHTML 블록 구조)       (`mapping.yaml`)              (`expected.roundtrip.json` v3)
             │                        │                        │
             └────────────────────────┴──────────────┬─────────┘
                                                     ▼
                                             build_patches()
                                                     │
                                  delete / insert / modify / replace_fragment
                                                     │
                                                     ▼
                                              patch_xhtml()
                                                     │
                                                     ▼
                               record_mapping(patched_xhtml) + converter/cli.py
                                                     │
                                                     ▼
                                            verify_roundtrip()
                                                     │
                                                     ▼
                                   pass → (선택) push / fail → result.yaml 기록
```

핵심 포인트는 다음과 같습니다.

- `run_verify()`가 사실상 reverse-sync의 표준 실행 경로입니다.
- `mapping.yaml`만으로는 현재 구현을 설명할 수 없고, `expected.roundtrip.json` 기반 sidecar v3가 실제 identity fallback과 reconstruction에 깊게 관여합니다.
- 모호한 변경은 억지로 반영하지 않고 `skipped_changes`로 보고합니다.
- 성공 조건은 "패치 생성"이 아니라 "patched XHTML을 다시 forward 변환했을 때 improved MDX와 일치"입니다.

### 현재 모듈 구성

| 모듈 | 현재 역할 |
|------|-----------|
| `reverse_sync_cli.py` | verify / push 오케스트레이션, 결과 파일 생성, 배치 처리, Confluence push 안전장치 |
| `mdx_block_parser.py` | MDX 블록 파싱 래퍼 |
| `block_diff.py` | 블록 단위 diff + alignment 계산 |
| `mapping_recorder.py` | XHTML에서 top-level / child block mapping 추출 |
| `sidecar.py` | `mapping.yaml` v3 생성, roundtrip sidecar v3 생성/검증, identity 인덱스, lost_info 로딩 |
| `fragment_extractor.py` | XHTML fragment를 byte-exact 수준으로 추출 |
| `patch_builder.py` | reverse-sync의 정책 엔진. direct / containing / paired / list / table / skip 분기 결정 |
| `visible_segments.py` | list 경로에서 visible segment 모델을 사용해 marker/공백/내용 변경을 더 정밀하게 판별 |
| `reconstructors.py` | preserved anchor, container, list item 등에서 원본 fragment 템플릿을 유지한 채 부분 재구성 |
| `mdx_to_xhtml_inline.py` | insert/replace용 MDX 블록을 XHTML fragment로 생성 |
| `xhtml_patcher.py` | patch를 실제 XHTML DOM/fragment에 적용 |
| `roundtrip_verifier.py` | normalize / lenient / no-normalize 옵션을 포함한 roundtrip 검증 |
| `rehydrator.py` | sidecar fragment 재조립/검증 보조 유틸 |
| `confluence_client.py` | Confluence REST API push |

### 단계별 상세

#### Step 1: MDX 블록 파싱과 diff

원본/교정 MDX를 `parse_mdx_blocks()`로 파싱한 뒤 `diff_blocks()`로 `BlockChange[]`와 alignment를 계산합니다.

- non-content 블록(frontmatter, import, empty 등)은 후속 단계에서 제외됩니다.
- reverse-sync는 line range와 block hash를 이후 sidecar identity lookup에 재사용합니다.
- 과거 문서에 있던 일부 파싱 버그 설명은 현재 구현과 완전히 일치하지 않습니다. 현재 기준에서 중요한 것은 "블록 경계가 sidecar line range / content hash와 함께 identity로 사용된다"는 점입니다.

#### Step 2: XHTML 구조 기록

`record_mapping(page.xhtml)`는 XHTML에서 블록 구조를 추출해 `BlockMapping` 목록을 만듭니다.

- heading / paragraph / list / table / code / html_block / macro container 등을 추출합니다.
- callout, ADF panel, expand 같은 compound block은 children 매핑을 함께 기록합니다.
- reverse-sync는 patched XHTML에도 동일 recorder를 다시 적용해 `reverse-sync.mapping.patched.yaml`을 생성합니다.

#### Step 3: 두 종류의 sidecar 구축

현재 구현은 두 종류의 메타데이터를 함께 사용합니다.

1. `mapping.yaml`
   - `generate_sidecar_mapping()`이 생성합니다.
   - 타입 호환성 기반 two-pointer 정렬로 XHTML top-level block과 MDX content block을 연결합니다.
   - reverse-sync에서는 주로 `mdx_to_sidecar` 역인덱스와 page/block-level `lost_info` 로딩에 사용합니다.

2. `expected.roundtrip.json` (schema v3)
   - `build_sidecar()`가 생성합니다.
   - XHTML fragment, `mdx_content_hash`, `mdx_line_range`, `reconstruction` 메타데이터를 함께 저장합니다.
   - 현재 reverse-sync에서 사실상 더 중요한 메타데이터입니다. list fallback, preserved anchor, container reconstruction, roundtrip integrity 검증에 사용됩니다.

#### Step 4: 패치 생성 (`patch_builder.py`)

`patch_builder.py`가 현재 reverse-sync의 실제 정책 엔진입니다. 이 모듈은 각 변경을 다음 중 하나로 분기합니다.

- `delete`: 기존 XHTML 요소 제거
- `insert`: 새 MDX 블록을 XHTML로 생성해 삽입
- `modify`: 안전한 텍스트 수준 변경
- `replace_fragment`: fragment 전체를 교체하되 sidecar/reconstruction metadata를 활용해 원본 구조를 최대한 보존
- `skip`: 위험하거나 identity가 불충분한 변경을 명시적으로 보고

현재 구현의 특징:

- delete+add가 같은 인덱스에서 만나면 `paired` 케이스로 보고 전체 fragment replacement를 우선 검토합니다.
- clean block, container sidecar, preserved anchor, parameter-bearing container, markdown table 여부에 따라 다른 reconstruction 경로를 탑니다.
- list 경로는 `visible_segments.py`를 사용해 marker 뒤 공백, 선행 공백 축소, continuation line merge 같은 회귀를 줄이도록 강화되었습니다.
- table 경로는 whole-fragment replacement를 시도하되, 위험한 경우 `no_mapping`, `missing_roundtrip_sidecar`, `preserved_anchor_table`, `raw_html_table`, `not_markdown_table`, `unsafe_html_table_edit` 등 이유로 skip합니다.
- legacy `mapping.yaml`이 list를 충분히 설명하지 못하는 경우, roundtrip sidecar v3의 `mdx_content_hash + mdx_line_range` identity fallback으로 매핑을 복원합니다.

즉, 현재 reverse-sync는 "가능하면 직접 수정"보다 "안전하면 fragment replacement, 아니면 skip"에 더 가깝습니다.

#### Step 5: XHTML 패치 적용

`xhtml_patcher.py`는 patch 목록을 XHTML에 적용합니다.

- action은 대체로 `delete`, `insert_before`, `insert_after`, `modify`, `replace_fragment` 계열로 정리됩니다.
- 단순 문자열 치환이 아니라 DOM 요소 탐색 + fragment 재파싱을 조합합니다.
- replace_fragment는 reconstruction을 거쳐 생성된 XHTML 조각을 그대로 주입하는 경우가 많습니다.

#### Step 6: roundtrip proof

패치가 끝나면 reverse-sync는 여기서 끝나지 않습니다.

1. `reverse-sync.patched.xhtml` 저장
2. `record_mapping()` 재실행 → `reverse-sync.mapping.patched.yaml` 저장
3. patched XHTML을 `converter/cli.py`로 다시 MDX로 변환 → `verify.mdx` 생성
4. `verify_roundtrip(improved_mdx, verify_mdx, ...)`로 최종 비교

`roundtrip_verifier.py`는 다음과 같은 성격을 가집니다.

- 기본값은 비교적 엄격한 exact/normalized match입니다.
- `--lenient`, `--no-normalize` 옵션이 존재합니다.
- 최근 커밋에서 sentence break, table padding, inline whitespace, badge/heading roundtrip 같은 케이스에 맞춰 정규화가 계속 조정되었습니다.

### 현재 생성/사용 파일

| 파일 | 위치 | 설명 |
|------|------|------|
| `mapping.yaml` | `var/<page_id>/` | XHTML↔MDX top-level mapping + lost_info |
| `expected.roundtrip.json` | `tests/testcases/<case_id>/` 또는 fixture | roundtrip sidecar v3 |
| `reverse-sync.diff.yaml` | `var/<page_id>/` | block diff 결과 |
| `reverse-sync.mapping.original.yaml` | `var/<page_id>/` | 원본 XHTML mapping dump |
| `reverse-sync.mapping.patched.yaml` | `var/<page_id>/` | patched XHTML mapping dump |
| `reverse-sync.patched.xhtml` | `var/<page_id>/` | 패치 결과 XHTML |
| `reverse-sync.result.yaml` | `var/<page_id>/` | verify 결과, skipped_changes, diff 요약 |
| `verify.mdx` | `var/<page_id>/` | patched XHTML을 다시 forward 변환한 MDX |

---

## Sidecar 시스템

현재 구현에서 sidecar는 단순한 부가 메타데이터가 아니라 reverse-sync의 identity preservation 계층입니다.

### 1. Mapping sidecar (`mapping.yaml`)

`generate_sidecar_mapping()`이 생성하며, 현재 포맷은 사실상 v3 semantics를 가집니다.

```yaml
page_id: "..."
mappings:
  - xhtml_xpath: "p[1]"
    xhtml_type: "paragraph"
    mdx_blocks: [3]
    mdx_line_start: 12
    mdx_line_end: 12
lost_info:
  ...
```

현재 역할은 다음에 가깝습니다.

- top-level XHTML block ↔ MDX block의 기본 연결 제공
- child alignment 정보 제공 (callout/details 등)
- `lost_info`를 통해 forward converter에서 사라진 원본 정보 보존
- reverse-sync의 기본 lookup용 역인덱스 제공

다만 현재 구현을 이해할 때 `mapping.yaml`만 보면 부족합니다. list/complex container/preserved anchor는 roundtrip sidecar 없이는 설명되지 않는 경우가 많습니다.

### 2. Roundtrip sidecar (`expected.roundtrip.json`, schema v3)

현재 핵심 스키마는 다음 필드를 가집니다.

```json
{
  "schema_version": "3",
  "page_id": "544381877",
  "mdx_sha256": "...",
  "source_xhtml_sha256": "...",
  "blocks": [
    {
      "block_index": 0,
      "xhtml_xpath": "h2[1]",
      "xhtml_fragment": "<h2>Title</h2>",
      "mdx_content_hash": "...",
      "mdx_line_range": [3, 3],
      "lost_info": {},
      "reconstruction": {}
    }
  ],
  "separators": ["\n"],
  "document_envelope": {"prefix": "", "suffix": "\n"}
}
```

이 sidecar의 핵심 역할은 다음과 같습니다.

- fragment + separator + envelope 재조립이 원본 XHTML과 byte-equal이어야 합니다.
- `mdx_content_hash`와 `mdx_line_range`를 통해 block identity fallback을 제공합니다.
- `reconstruction` 메타데이터를 통해 preserved anchor / container / list item처럼 emitter 단독 재생성이 위험한 블록을 원본 템플릿 기반으로 재구성합니다.
- reverse-sync는 이 sidecar를 이용해 "원래 XHTML fragment의 정체성"을 최대한 유지합니다.

### 현재 이해해야 할 원칙

- `mapping.yaml`은 구조적 lookup과 lost_info 전달 계층입니다.
- `expected.roundtrip.json`은 fragment identity / reconstruction 계층입니다.
- reverse-sync의 안정성은 결국 "patch를 잘 만들었는가"보다 "sidecar가 원본 fragment를 얼마나 안전하게 다시 사용할 수 있는가"에 더 크게 좌우됩니다.

### 알려진 한계

현재 구현이 강한 영역:

- paragraph / heading 중심 텍스트 교정
- badge, code span, inline whitespace 등 최근 커밋으로 회귀가 줄어든 인라인 변경
- preserved anchor가 없거나 sidecar reconstruction metadata가 충분한 container/list 변경

여전히 취약한 영역:

- markdown table과 raw HTML table의 경계 케이스
- preserved anchor가 섞인 list/table
- parameter-bearing container의 구조 변화
- forward converter 정규화 특성에 민감한 roundtrip mismatch
- `patch_builder.py`에 전략/예외/skip 분기가 과도하게 집중된 구조

이 한계는 "아직 구현되지 않은 기능"이라기보다, 현재 구현이 안전성 우선으로 선택한 보수적 경계에 가깝습니다.

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
| normalize-diff (emitter 단독) | **1/21 pass** | L5 개선 후 (L5 이전: 0/21) |
| document-level sidecar (Lossless v1) | **21/21 pass** | MDX 미변경 시 원본 XHTML 그대로 반환 (trivial) |
| L1 fragment reassembly | **21/21 pass** | sidecar v2 프래그먼트 재조립 byte-equal |
| **block-level splice (L2)** | **21/21 pass** | forced-splice 경로로 블록 단위 byte-equal |

**Emitter 단독 실패 원인 분포 (L5 이후):**

| 원인 | 건수 | 비가역 여부 | L5 변화 |
|------|------|-------------|---------|
| `attachment_filename_mismatch` | 9 | **비가역** — 정순변환에서 파일명 정규화 | +2 (분류 변경) |
| `internal_link_unresolved` (`#link-error`) | 7 | **비가역** — 정순변환에서 원본 정보 소실 | 변동 없음 |
| `emoticon_representation_mismatch` | 4 | **비가역** — 정순변환에서 shortname 소실 | 변동 없음 |
| `image_block_structure_mismatch` | 3 | emitter 수정 가능 (중첩 구조) | -2 (L5 해소) |
| `adf_extension_panel_mismatch` | 3 | **비가역** — ADF 구조가 MDX에 없음 | 변동 없음 |
| `table_cell_structure_mismatch` | 2 | emitter 수정 가능 | 신규 분류 |
| `other` | 2 | 분석 필요 | — |
| `underline_tag_mismatch` | 1 | emitter 수정 가능 | -1 |
| ~~`ordered_list_start_mismatch`~~ | ~~0~~ | ~~해소~~ | **-12 (L5 완전 해소)** |

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
    ├── mapping.yaml                     ← XHTML↔MDX 매핑 sidecar (reverse_sync/sidecar.py 생성)
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

## Reverse Sync 설계 불변조건

Reverse Sync 파이프라인의 정확성은 다음 불변조건에 의존한다. **이 조건이 위반된 상태에서 heuristic을 추가하는 것은 근본 원인을 숨기는 것이다.**

### 핵심 흐름

```
old_xhtml ──(forward converter)──▶ old_mdx + sidecar(mapping.yaml)
                                           │
new_mdx ────────────────────────────── diff(old_mdx, new_mdx)
                                           │
                                           ▼
                                    edit sequence
                                           │
                                  sidecar로 MDX 위치 → XHTML 위치 변환
                                           │
                                           ▼
                                    old_xhtml 패치 → new_xhtml
```

### 불변조건: old_xhtml ↔ old_mdx는 항상 동기화되어 있다

`old_mdx`는 `old_xhtml`에서 forward converter가 생성한 결과다. 따라서:

- XHTML 블록과 MDX 블록의 대응 관계는 **변환 시점에 완전히 결정**된다.
- 정보 유실(emoticon, link 등)이 있더라도 **구조적 대응 관계는 확정적**이다.
- sidecar 생성 시 two-pointer alignment이 실패할 수 없다.

### 위반 징후

sidecar 생성 함수(`build_sidecar`, `generate_sidecar_mapping`)에서 alignment 오류가 발생하거나 이를 보완하는 heuristic이 필요하다면, 다음 중 하나를 의미한다:

| 징후 | 실제 원인 | 올바른 수정 |
|------|----------|------------|
| two-pointer alignment MISS | forward converter가 XHTML 구조를 MDX에 올바르게 반영하지 못함 | forward converter 버그 수정 → old_mdx 재생성 |
| sidecar 없이 현재 MDX로 alignment 시도 | new_mdx(편집본)를 old_mdx로 잘못 사용 | old_mdx 복원 경로 확보 |
| alignment heuristic 추가 (예: heading lookahead) | 위 두 경우 중 하나 | heuristic 제거, 근본 원인 수정 |

> **교훈:** `_heading_lookahead()`처럼 "XHTML-MDX 구조 불일치를 heading으로 재동기화"하는 코드가 필요하다고 느껴진다면, sidecar.py를 수정할 것이 아니라 forward converter의 변환 결과가 왜 XHTML 구조를 정확히 반영하지 못하는지를 먼저 조사해야 한다.

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

### ⚠️ TECH DEBT: `_heading_lookahead` — 제거해야 할 중대한 부채

`sidecar.py`의 `_heading_lookahead()` 함수는 반드시 제거해야 할 설계 부채다.

**문제:** `parse_mdx_blocks`가 list item 뒤 빈 줄 없이 이어지는 연속행을 별도 `paragraph` 블록으로 잘못 파싱하여 sidecar two-pointer alignment가 어긋난다. `_heading_lookahead`는 heading을 anchor 삼아 이 어긋남을 임시 보상하는 heuristic이다.

**Markdown 규칙:** paragraph 분리는 반드시 빈 줄이 있어야 한다. forward converter는 한 문장을 한 줄에 표현하는 스펙에 따라 list item 내 문장을 빈 줄 없이 줄바꿈한다. 이 연속행은 동일 list item의 일부이며 별도 블록이 아니다.

**제거 조건:** `parse_mdx_blocks`에서 list item 연속행(빈 줄 없이 이어지는 non-list-marker 줄)을 같은 블록으로 합치면 alignment 오류가 발생하지 않으며 이 함수를 제거할 수 있다.

**추적 케이스:** page 544112828 — XHTML `p[6]`이 MDX에서 `list`(L48) + `paragraph`(L49)로 오분리됨

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
| L5 | Backward Converter 정확도 개선 | **완료** | #TBD |
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

### Phase L5: Backward Converter 정확도 개선 ✅

역순변환기(Backward Converter)의 XHTML 출력 품질을 3개 항목에서 개선했다.

**구현 항목:**

| 항목 | 수정 파일 | 영향 | 결과 |
|------|----------|------|------|
| `<ol start="1">` 속성 추가 | `emitter.py` | 12건 → 0건 | `ordered_list_start_mismatch` 완전 해소 |
| 인라인 `<Badge>` → `status` 매크로 | `inline.py` | 2건 | paragraph/list 내 Badge 변환 |
| 리스트 내 `<figure>` → `<ac:image>` 형제 구조 | `emitter.py` | 5건 → 3건 | 단순 구조 2건 해소 |

나머지 원래 계획 항목 2개(`<br/>` 표기, `<details>` 매핑)는 이미 구현 완료 상태였다.

**검증 결과:** normalize-diff 0/21 → 1/21 pass, splice 21/21 byte-equal 유지

### Phase L6: CI Gate 전환

Byte-equal 검증을 CI의 기본 게이트로 설정한다.

- `byte_verify` CLI를 CI 스크립트에 통합
- 기존 normalize-verify를 `--diagnostic` 모드로 전환
- Byte mismatch → build fail (exit code 1)

**인수 기준:** CI pipeline에서 byte-equal gate 활성화, 21/21 pass

### Reverse Sync Phase 3: 전면 재구성

문서 구조, 위치, 이름 변경을 포함한 전면 재구성을 Confluence에 반영한다. Phase 2의 SequenceMatcher를 확장하여 이동(reorder) 감지, Confluence API 페이지 이동/이름 변경 연동, 페이지 트리 구조 관리를 구현한다. 별도 설계 필요.
