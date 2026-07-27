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

현재 reverse-sync는 MDX diff를 Confluence Storage XHTML에 보수적으로 반영하고, 생성 결과를 다시 MDX로 변환해 검증한 뒤, 검증 실행에 결합된 immutable manifest만 발행하는 파이프라인입니다. 로컬 `page.xhtml`을 사용하는 진단 경로와 원격 `current` page snapshot을 사용하는 온라인 경로는 안전성 수준과 산출물이 다릅니다.

### 전체 흐름

```
original MDX + improved MDX
              │
              ▼
       prepare_service
              │
              ├── 로컬 진단: var/<page_id>/page.xhtml
              │
              └── 온라인 준비: Confluence current PageSnapshot
                  (page_id, status, title, version, storage_xhtml)
                              │
                              ▼
                    verification_service
                              │
             source identity / base parity / dependency gate
                              │
                              ▼
            planner: BlockChange[] → typed PatchPlan v2
                              │
                              ▼
          preserving renderer → candidate Storage XHTML
                              │
                              ▼
              forward conversion + local proof
     (intent completeness, parse, preservation, equivalence,
                 determinism, idempotency, dependency)
                              │
                              ▼
        immutable run artifacts + SyncManifest
                              │
                              ▼
                 explicit manifest publish
                              │
                              ▼
             preflight snapshot / draft / dependency
                              │
                              ▼
             version-bound PUT(base.version + 1)
                              │
                              ▼
           persisted snapshot postcondition 검증
```

### 실행 경로와 상태

| 경로 | base XHTML | renderer | 결과 상태 | 발행 가능 여부 |
|------|------------|----------|-----------|----------------|
| `verify`, `debug` | 로컬 `var/<page_id>/page.xhtml` | `legacy_xhtml_patcher.py` | `pass`, `fail`, `no_changes` | 항상 불가 |
| `push --dry-run <mdx>` | 원격 `current` `PageSnapshot.storage_xhtml` | `preserving_patcher.py` | `verified_local`, `blocked`, `no_changes` | manifest 생성까지만 수행 |
| `push <mdx>` | 원격 `current` snapshot | `preserving_patcher.py` | 준비 후 `remote_verified`, `already_applied`, `postcondition_failed` 또는 conflict | 확인 후 발행 |
| `push --manifest <path>` | manifest에 결합된 base snapshot | candidate를 다시 생성하지 않음 | `remote_verified`, `already_applied`, `postcondition_failed` 또는 conflict | 명시한 manifest만 발행 |

로컬 `verify`와 `debug`는 converter 회귀 진단과 기존 fixture 호환을 위한 경로입니다. `--lenient`와 `--no-normalize`도 이 진단 결과에만 영향을 주며 `push_eligible`을 만들지 않습니다.

온라인 준비는 한 v2 API response에서 `page_id`, `status`, `title`, `version`, `storage_xhtml`을 함께 읽은 `PageSnapshot`을 사용합니다. 로컬 `page.xhtml`이나 별도 version 조회를 온라인 base로 대체하지 않습니다. 원격 snapshot을 forward 변환한 MDX와 repository original MDX가 일치하지 않거나 provenance가 불충분하면 `base_parity_mismatch`, `stale_original_mdx`, `forward_converter_drift` 등의 reason code로 중단합니다.

온라인 planner는 모든 MDX 변경을 typed intent로 만들고 각 intent가 실행 가능한 operation으로 정확히 한 번 커버되는지 확인합니다. 지원하지 않거나 모호한 변경은 진단 경로에서는 `skipped_changes`로 볼 수 있지만, 온라인 경로에서는 `PatchPlan.intent_complete = false`가 되어 전체 실행을 차단합니다.

candidate는 원본 fragment의 보존 대상 구조를 유지하는 renderer로 생성합니다. 이후 다음 gate를 모두 통과해야 `verified_local` manifest를 만들 수 있습니다.

- typed intent completeness
- Storage XHTML parse
- 변경하지 않은 구조와 fragment preservation
- candidate를 forward 변환한 MDX와 improved MDX의 push equivalence
- 동일 입력으로 plan과 candidate를 다시 만들었을 때의 determinism
- 생성된 candidate를 base로 같은 변경을 다시 적용했을 때의 idempotency
- attachment와 internal link dependency identity

### 발행 transaction

Publisher는 CLI의 “최신 결과 파일”을 추측하지 않고 `--manifest`로 지정된 immutable run만 소비합니다. 발행 직전에 다음 순서로 fail-closed 검사를 수행합니다.

1. manifest schema, tool version, verifier policy, artifact hash와 typed plan contract를 검증합니다.
2. 원격 `current` snapshot의 page identity가 manifest base와 같은지 검사합니다.
3. active draft가 있으면 발행을 중단합니다.
4. 검증 때 기록한 attachment와 internal link dependency identity를 다시 검사합니다.
5. 이미 candidate와 같거나 검증된 의미 동등 상태이면 `already_applied` receipt를 기록하고 PUT하지 않습니다.
6. 원격 version과 Storage body hash가 manifest base와 같은지 검사합니다.
7. `base.version + 1`로 page body와 기존 title을 함께 PUT합니다.
8. 원격 page를 다시 읽어 identity, version, body의 byte 또는 semantic postcondition을 검사합니다.

version conflict나 remote drift가 발생해도 최신 version을 새 base로 채택하거나 PUT을 재시도하지 않습니다. active draft도 자동 병합하거나 덮어쓰지 않습니다. 실패 시 snapshot, API response, receipt를 run directory에 남겨 수동 복구와 판정을 가능하게 합니다.

현재 publisher는 body 변경만 지원합니다. frontmatter title 변경, attachment 생성·갱신·삭제, preserved anchor target 변경은 capability gate에서 차단합니다.

### 현재 모듈 구성

| 모듈 | 현재 역할 |
|------|-----------|
| `reverse_sync_cli.py` | argument parsing, 출력, 사용자 확인, runtime dependency 조립과 service 호출 |
| `prepare_service.py` | MDX source와 page identity 해석, 원격 snapshot·attachment catalog 준비 |
| `verification_service.py` | diff, planner, renderer, forward conversion, proof, manifest 생성 lifecycle |
| `batch_service.py` | 브랜치 대상의 eligibility 판정, 순차 발행, 실패 시 halt와 resume 정보 조립 |
| `publish_service.py` | explicit manifest 요약·확인 입력, publisher 호출, semantic postcondition adapter, backup 관리 |
| `models.py` | `PageSnapshot`, `SyncManifest`, `PushReceipt`, reason code 등 불변 모델 |
| `confluence_client.py` | v2 page/draft/attachment snapshot과 version-bound page update gateway |
| `base_parity.py`, `dependencies.py` | repository source/provenance, remote base, attachment, internal link gate |
| `planner.py`, `operations.py`, `capabilities.py` | `BlockChange`를 typed intent와 executable operation을 가진 `PatchPlan` v2로 컴파일 |
| `strategies/` | text, list, table, container별 operation 생성 전략 |
| `preserving_patcher.py` | 온라인 plan의 source-range 기반 preservation renderer |
| `xhtml_patcher.py` | 검증된 operation 적용 primitive |
| `legacy_xhtml_patcher.py` | 로컬 진단 경로의 호환 패처 |
| `proof.py`, `equivalence.py` | local proof gate와 push equivalence 검증 |
| `manifest.py` | 실행별 immutable artifact, manifest hash binding, compatibility symlink |
| `publisher.py` | preflight, active draft/dependency 검사, CAS PUT, postcondition, receipt |
| `sidecar.py`, `mapping_recorder.py`, `patch_builder.py` | identity/preservation metadata와 legacy migration adapter |

### 현재 생성/사용 파일

온라인 검증이 통과하면 다음 immutable run을 생성합니다.

```
var/<page_id>/reverse-sync/<run_id>/
├── manifest.json
├── manifest.sha256
├── base.xhtml
├── original.mdx
├── improved.mdx
├── patch-plan.json
├── candidate.xhtml
└── local-proof.json
```

발행 단계는 같은 run directory에 `preflight.snapshot.json`, `draft.snapshot.json`, dependency snapshot, `update.response.json`, `post.snapshot.json`, `push-receipt.json`을 필요에 따라 추가합니다.

page directory의 `reverse-sync.manifest.json`, `reverse-sync.patched.xhtml`, `reverse-sync.plan.json`, `reverse-sync.proof.json`은 가장 최근 온라인 immutable run을 가리키는 진단·호환 symlink입니다. Publisher는 이 symlink를 자동 탐색하지 않고 explicit manifest path만 입력으로 받습니다.

로컬 진단 경로는 기존 `reverse-sync.diff.yaml`, `reverse-sync.mapping.*.yaml`, `reverse-sync.patched.xhtml`, `reverse-sync.result.yaml`, `verify.mdx`를 page directory에 생성하지만, 이 flat artifact는 manifest가 아니며 발행 입력으로 사용할 수 없습니다.

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
├── pages.yaml                           ← forward converter용 전체 페이지 메타데이터
├── pages.qm.yaml                        ← reverse-sync의 MDX path ↔ page identity 인덱스
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
    ├── reverse-sync.manifest.json       ← 최신 온라인 run manifest 호환 symlink
    ├── reverse-sync.patched.xhtml       ← 진단 artifact 또는 최신 candidate 호환 symlink
    ├── reverse-sync.plan.json           ← 최신 온라인 typed plan 호환 symlink
    ├── reverse-sync.proof.json          ← 최신 온라인 local proof 호환 symlink
    ├── reverse-sync.result.yaml         ← 검증 결과
    ├── verify.mdx                       ← 라운드트립 검증용: 패치된 XHTML을 정순변환한 MDX
    ├── reverse-sync/
    │   └── <run_id>/                    ← immutable online verification run
    │       ├── manifest.json
    │       ├── manifest.sha256
    │       ├── base.xhtml
    │       ├── original.mdx
    │       ├── improved.mdx
    │       ├── patch-plan.json
    │       ├── candidate.xhtml
    │       └── local-proof.json
    └── <attachment files>               ← 다운로드된 첨부파일
```

### `tests/testcases/` 디렉토리 (테스트 데이터)

```
tests/testcases/
└── <case_id>/
    ├── page.xhtml                       ← 원본 Confluence XHTML
    ├── expected.mdx                     ← 기대 MDX 출력
    ├── output.mdx                       ← 실제 변환 결과 (테스트 시 생성)
    └── expected.roundtrip.json          ← Roundtrip sidecar v3 (블록 프래그먼트)
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
| `reverse_sync_cli.py verify <mdx>` | 로컬 `page.xhtml` 기반 단일 파일 진단. 항상 push-ineligible |
| `reverse_sync_cli.py debug <mdx>` | 로컬 진단 + MDX/XHTML/verify diff 출력 |
| `reverse_sync_cli.py push --dry-run <mdx>` | 원격 snapshot 기반 검증과 immutable manifest 생성. PUT은 생략 |
| `reverse_sync_cli.py push <mdx>` | 원격 snapshot 기반 검증 후 확인을 거쳐 단일 manifest 발행 |
| `reverse_sync_cli.py push --manifest <manifest.json>` | 이미 검증한 immutable run을 명시적으로 발행 |
| `reverse_sync_cli.py verify --branch <branch>` | 브랜치의 변경된 한국어 MDX를 로컬 배치 진단 |
| `reverse_sync_cli.py push --branch <branch> [--dry-run]` | 브랜치 대상을 온라인 검증하고 순차 발행. version conflict와 일반 발행 오류는 기록하고 계속하며, postcondition 실패 시에만 후속 발행 중단 |

---

## Reverse Sync 설계 불변조건

Reverse Sync 파이프라인의 정확성은 다음 불변조건에 의존합니다. 이 조건이 확인되지 않은 실행은 보수적으로 중단합니다.

### 핵심 흐름

```
remote current PageSnapshot ── forward converter ──▶ converted base MDX
             │                                          │
             │                               repository original MDX
             │                                          │
             └──────── base/provenance parity ───────────┘
                                │
improved MDX ── diff ──▶ typed intent / operation plan
                                │
                                ▼
                 preserving render + local proof
                                │
                                ▼
                 immutable manifest-bound candidate
                                │
                                ▼
             identical preflight + version-bound PUT
                                │
                                ▼
                   persisted postcondition proof
```

### 필수 불변조건

- 온라인 base는 한 API response로 얻은 원격 `current` `PageSnapshot`입니다.
- repository original MDX는 snapshot을 forward 변환한 결과 및 저장된 provenance와 일치해야 합니다.
- 모든 의미 있는 MDX 변경은 typed intent이며, 모든 intent는 실행 가능한 operation으로 정확히 커버되어야 합니다.
- candidate는 source range와 preservation fingerprint로 보호된 원본 fragment의 비변경 영역을 보존해야 합니다.
- `--lenient`, `--no-normalize`, text identity fallback은 push eligibility에 사용할 수 없습니다.
- manifest는 base snapshot, 입력 MDX, plan, candidate, local proof를 hash로 결합하며 생성 후 변경할 수 없습니다.
- publisher는 명시한 manifest만 소비하고, preflight가 manifest base와 다르면 PUT하지 않습니다.
- active draft가 있으면 자동 병합이나 덮어쓰기 없이 중단합니다.
- conflict 시 최신 version으로 재시도하지 않습니다.
- 성공은 PUT response가 아니라 persisted snapshot의 identity, version, body postcondition으로 판정합니다.

### 위반 시 처리

| 징후 | 처리 |
|------|------|
| repository MDX와 remote snapshot의 forward 결과가 다름 | stale source 또는 converter drift로 차단하고 원인을 먼저 복구 |
| intent가 없거나 중복·미지원 operation만 존재 | incomplete plan으로 전체 실행 차단 |
| preservation, determinism, idempotency 불일치 | local proof 실패, manifest 미생성 |
| preflight version/body/title/status drift | remote drift 또는 conflict로 차단, 자동 재시도 금지 |
| active draft 발견 | draft snapshot을 기록하고 수동 reconciliation 전까지 차단 |
| PUT 후 body 또는 version 불일치 | `postcondition_failed` receipt를 남기고 성공으로 보고하지 않음 |

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
