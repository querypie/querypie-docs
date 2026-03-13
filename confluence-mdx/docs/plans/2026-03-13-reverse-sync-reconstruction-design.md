# Reverse Sync 전면 재구성 설계

> 작성일: 2026-03-13
> 대상 PR: #913
> 연관 문서:
> - `docs/plans/2026-03-13-reverse-sync-reconstruction-design-review.md`
> - `docs/analysis-reverse-sync-refactoring.md`

## 1. 문서 목적

이 문서는 PR #913의 reverse-sync 설계를 전면 재작성한 버전이다.

목표는 세 가지다.

1. MDX 변경을 XHTML로 재구성하여 Confluence 문서를 안정적으로 업데이트한다.
2. 현재의 heuristic 텍스트 패치 체인을 구조적 재구성 경로로 치환한다.
3. 현재 저장소에 이미 존재하는 `tests/testcases/` 와 `tests/reverse-sync/` 자산을 중심으로, 구현·회귀·유지보수가 가능한 테스트 체계를 만든다.

이 문서는 "방향 제안"이 아니라, 구현 착수 전에 필요한 설계 전제와 테스트 게이트를 코드베이스 기준으로 확정하는 문서다.

## 2. 현재 문제와 재설계 목표

현재 reverse-sync 파이프라인은 다음 흐름이다.

`MDX diff -> mapping 추론 -> text/plain 기준 패치 -> patched XHTML -> forward convert -> MDX 재검증`

핵심 병목은 `patch_builder.py` 와 `text_transfer.py` 에 있다.

- 변경 블록을 XHTML로 다시 만드는 대신, 기존 XHTML 내부 텍스트만 이식한다.
- list, table, callout, containing block, direct replacement 등 전략 분기가 계속 늘어난다.
- Confluence 전용 요소(`<ac:image>`, `<ac:link>`, `<ac:structured-macro>`, `ac:adf-extension`)는 텍스트 좌표계 밖에 있기 때문에, 텍스트만 옮기는 방식이 구조적으로 불안정하다.

이번 재설계의 목표는 분명하다.

- 변경된 MDX 블록은 가능한 한 "다시 emit한 XHTML fragment"로 교체한다.
- emitter가 재현할 수 없는 Confluence 전용 정보만 sidecar metadata로 보존 후 재주입한다.
- modified block 처리의 기본 전략을 `transfer_text_changes()` 가 아니라 `reconstruct_fragment()` 로 바꾼다.

즉 새 기본 경로는 다음과 같다.

`MDX diff -> changed block identify -> emit XHTML fragment -> restore preserved anchors/lost info -> replace top-level fragment -> forward verify`

## 3. 리뷰에서 확정된 수정 요구

리뷰 문서에서 지적한 사항 중 설계 착수 전에 반드시 확정해야 하는 항목은 아래 네 가지다.

### 3.1 Paragraph 좌표계

기존 문서는 `convert_inline()` 를 사실상 "XHTML -> MDX 역변환기"처럼 가정했다. 실제 코드에서는 성립하지 않는다.

- `convert_inline()` 는 `mdx_to_storage.inline.convert_inline`
- 역할은 MDX inline -> XHTML inline 변환
- XHTML fragment를 넣어도 MDX로 돌아오지 않는다

따라서 새 설계는 다음 원칙을 따른다.

- paragraph/list-item anchor 매핑의 기준 좌표계는 "MDX literal"이 아니다
- 기준 좌표계는 "XHTML DOM 에서 추출한 normalized plain text"다
- old/new 비교는 `old_mdx_text` 가 아니라 `old_plain_text -> new_plain_text` 로 수행한다

이 결정으로 XHTML -> MDX inverse 가정을 제거한다.

### 3.2 테스트 oracle

`mapping.yaml` 은 runtime lookup 용이지, fragment oracle 용이 아니다. 실제 저장소의 `load_sidecar_mapping()` 도 fragment 본문을 읽지 않는다.

새 설계의 oracle은 다음 순서로 사용한다.

1. `expected.roundtrip.json`
   - 모든 `tests/testcases/*` 21개에 존재
   - top-level `xhtml_fragment` 를 exact oracle로 제공
2. `page.xhtml`
   - sidecar에 없는 nested fragment나 sub-xpath 비교에 사용
3. `expected.reverse-sync.patched.xhtml`
   - 변경 시나리오 16개에 대한 golden page oracle

즉 unit/integration 테스트는 `mapping.yaml` 에 의존하지 않는다.

### 3.3 XHTML normalization

새 비교 전략은 `lxml` 을 도입하지 않는다.

이 저장소에는 이미 다음 자산이 있다.

- `bin/reverse_sync/mdx_to_storage_xhtml_verify.py`
- `xhtml_beautify_diff.py`
- BeautifulSoup 기반 attribute stripping / layout stripping / macro stripping

새 설계는 이 경로를 공용 normalizer로 승격한다.

- 새 공용 모듈: `reverse_sync/xhtml_normalizer.py`
- 구현 기반: BeautifulSoup + 기존 ignored-attribute 규칙 재사용
- 비교 단위: page 전체와 fragment 모두 지원

이로써 새 의존성 없이 테스트 가능성을 확보한다.

### 3.4 block identity

`mdx_content_hash` 단독 매칭은 충분하지 않다.

현재 실제 데이터에서도 중복 content가 존재한다. 특히 `reverse_sync.mdx_block_parser` 기준으로는 `</Callout>` 같은 동일 블록이 여러 번 잡히는 케이스가 이미 보인다.

새 설계의 block identity는 아래를 함께 사용한다.

- `block_index`
- `mdx_line_range`
- `mdx_content_hash`
- 필요 시 동일 hash 후보군 내 상대 순서

즉 lookup key는 "hash 하나"가 아니라 "hash + line range + order"다.

## 4. 현재 코드베이스와 자산 분석

### 4.1 코드베이스에서 재사용할 축

이미 있는 구현 중 이번 설계에서 그대로 활용할 축은 다음과 같다.

- `reverse_sync_cli.py`
  - verify / push orchestration
  - forward convert 후 strict roundtrip 검증
- `reverse_sync.sidecar`
  - `RoundtripSidecar`, `SidecarBlock`, `expected.roundtrip.json`
- `reverse_sync.mapping_recorder`
  - XHTML top-level / callout child mapping 추출
- `mdx_to_storage.parser`, `mdx_to_storage.emitter`
  - MDX 구조 파싱과 XHTML emission
  - callout child 재귀 emission 가능
  - nested list tree 구성 함수 보유
- `reverse_sync.lost_info_patcher`
  - 링크, 이모티콘, filename, image, ADF extension 복원 로직

반대로 이번 재설계에서 더 이상 중심축이 되어서는 안 되는 부분은 다음과 같다.

- `transfer_text_changes()` 기반 modified block 패치
- `mapping.yaml` 을 fragment oracle처럼 사용하는 방식
- block 내부 구조를 content text만으로 추론하는 방식

### 4.2 테스트 자산 현황

현재 확보된 테스트 자산은 설계 검증에 충분히 강하다.

#### `tests/testcases/`

- 총 21개 케이스
- `page.xhtml`: 21개
- `expected.mdx`: 21개
- `expected.roundtrip.json`: 21개
- `original.mdx` + `improved.mdx` + `expected.reverse-sync.*`: 16개
- `attachments.v1.yaml`: 19개
- `page.v1.yaml`: 19개
- `page.v2.yaml`, `children.v2.yaml`: 각 19개
- `page.adf`: 18개

구조적 커버리지:

- list: 20개
- table: 9개
- image: 13개
- callout macro/ADF panel: 12개
- `ac:adf-extension`: 3개
- 링크: 12개
- code macro: 4개

대표 케이스:

- list item + image: `544113141`, `544145591`, `692355151`, `880181257`, `883654669`
- callout + nested list: `1454342158`, `544145591`, `692355151`, `880181257`, `883654669`
- callout + code macro: `544112828`
- ADF panel: `1454342158`, `544379140`, `panels`

#### `tests/reverse-sync/`

- 총 42개 실제 reverse-sync 회귀 케이스
- `pages.yaml` 기준: `pass` 28개, `fail` 14개, `catalog_only` 24개

구조적 커버리지:

- list: 42개
- image: 38개
- callout: 28개
- table: 10개
- 링크: 19개
- code macro: 7개

특히 중요한 실사례:

- paragraph/list item 내부 inline image: `544376004`
- callout + code: `544112828`
- 다수의 이미지/링크/callout 혼합 페이지: `544145591`, `1454342158`

#### 결론

새 설계는 "fixture가 부족해서 추상 설계를 해야 하는 상태"가 아니다. 오히려 반대다.

- unchanged fragment oracle: 이미 충분함
- changed-page golden oracle: 16개 존재
- failure reproduction corpus: 42개 존재

부족한 것은 fixture 양이 아니라, 이 자산을 설계 검증 단계별로 재배치하는 일이다.

## 5. 제안 아키텍처

### 5.1 최상위 원칙

1. modified block는 whole-fragment replacement가 기본이다
2. preserved 정보는 "text"가 아니라 "raw XHTML preservation unit" 으로 다룬다
3. anchor 재주입은 MDX 좌표가 아니라 normalized plain-text 좌표에서 수행한다
4. list / callout / details / ADF panel 은 child order 기반으로 재구성한다
5. 지원 범위 밖 구조는 fuzzy patch 하지 않고 명시적으로 fail 한다

### 5.2 sidecar 전략

기존 `RoundtripSidecar` 를 primary runtime artifact 로 승격한다.

- `mapping.yaml`
  - 역할 축소: top-level routing, 사람이 읽는 디버그 용도
- `expected.roundtrip.json`
  - 역할 확대: exact fragment oracle + reconstruction metadata

새 스키마는 `RoundtripSidecar schema_version = 3` 으로 정의한다.

핵심 변화:

- 각 `SidecarBlock` 에 reconstruction metadata 추가
- modified block 재구성에 필요한 preserved anchor/unit 을 block 단위로 저장

예시:

```json
{
  "block_index": 12,
  "xhtml_xpath": "p[3]",
  "xhtml_fragment": "<p>A <ac:image ... /> B</p>",
  "mdx_content_hash": "...",
  "mdx_line_range": [40, 40],
  "lost_info": {},
  "reconstruction": {
    "kind": "paragraph",
    "old_plain_text": "A  B",
    "anchors": [
      {
        "anchor_id": "p[3]/ac:image[1]",
        "raw_xhtml": "<ac:image ... />",
        "old_plain_offset": 2,
        "affinity": "after"
      }
    ]
  }
}
```

리스트 예시:

```json
{
  "block_index": 8,
  "xhtml_xpath": "ul[1]",
  "xhtml_fragment": "<ul>...</ul>",
  "reconstruction": {
    "kind": "list",
    "ordered": false,
    "items": [
      {
        "item_xpath": "ul[1]/li[1]",
        "old_plain_text": "item 1",
        "anchors": [],
        "child_blocks": []
      },
      {
        "item_xpath": "ul[1]/li[2]",
        "old_plain_text": "item 2",
        "anchors": [
          {
            "anchor_id": "ul[1]/li[2]/ac:image[1]",
            "raw_xhtml": "<ac:image ... />",
            "old_plain_offset": 6,
            "affinity": "after"
          }
        ],
        "child_blocks": [
          {
            "kind": "list",
            "xpath": "ul[1]/li[2]/ol[1]"
          }
        ]
      }
    ]
  }
}
```

이 구조의 의도는 단순하다.

- top-level fragment는 `xhtml_fragment` 가 책임진다
- list/paragraph/container 내부 보존 정보는 `reconstruction` 이 책임진다
- 테스트 oracle와 runtime metadata가 같은 artifact 안에 있게 한다

### 5.3 block 분류

새 재구성기는 top-level block를 네 종류로 나눈다.

#### A. Clean block

대상:

- heading
- code macro
- table
- hr
- paragraph without preserved anchors

처리:

- `mdx_to_storage.emit_block()` 또는 `mdx_block_to_xhtml_element()` 로 새 fragment emit
- block-level `lost_info` 적용
- 기존 fragment 전체 replace

#### B. Inline-anchor block

대상:

- paragraph 안의 `ac:image`, `ac:link` 류 preservation unit
- list item 안의 inline image / trailing preserved node

처리:

1. improved MDX block를 먼저 XHTML로 emit
2. emit 결과에서 plain text를 추출
3. sidecar의 `old_plain_text` 와 anchor offset을 기준으로 old -> new offset 매핑
4. 매핑된 위치에 raw anchor XHTML 삽입

중요한 점:

- old/new 비교는 plain-text 좌표
- 삽입 대상은 "생성된 XHTML DOM"
- raw 문자열 위치 삽입이 아니라 DOM walk 기반 삽입

#### C. Ordered child block

대상:

- nested list
- callout / details / ADF panel body

처리:

- original XHTML 의 child order를 sidecar에 저장
- improved MDX 는 `mdx_to_storage.parser.parse_mdx()` 로 child blocks 파싱
- child type과 순서를 기준으로 재귀 reconstruct

여기서는 text matching을 하지 않는다. 위치와 child slot이 기준이다.

#### D. Opaque block

대상:

- emitter가 재구성하지 못하는 custom macro
- 현재 testcase에 없거나 metadata 규칙이 정의되지 않은 구조

처리:

- `UnsupportedReconstructionError`
- verify는 fail
- 해당 페이지를 testcase로 승격 후 설계 범위 확장

이 fail-closed 정책이 중요하다. unsupported structure에서 silent corruption이 가장 위험하다.

### 5.4 paragraph / list item anchor 재주입

이 설계의 핵심 차별점은 "anchor를 plain-text offset에 고정"하는 것이다.

#### 좌표계

- `old_plain_text`: original XHTML fragment에서 DOM text를 뽑아 정규화한 값
- `new_plain_text`: improved MDX 를 emit한 XHTML fragment에서 같은 규칙으로 뽑은 값
- `old_plain_offset`: original plain text 기준 anchor 위치
- `new_plain_offset`: old -> new diff로 계산된 삽입 위치

#### 알고리즘

1. `extract_plain_text(fragment)` 로 old/new plain text 생성
2. `map_offsets(old_plain, new_plain, offsets)` 로 new offset 계산
3. `insert_raw_anchor_at_plain_offset(soup, raw_xhtml, offset)` 로 DOM 삽입

이 방식은 review에서 지적된 "XHTML inline fragment를 MDX text로 역변환해야 하는가" 문제를 제거한다.

### 5.5 list 재구성

리스트는 text queue가 아니라 tree + order 매칭으로 재구성한다.

재사용 자산:

- `mdx_to_storage.emitter._parse_list_items()`
- `mdx_to_storage.emitter._build_list_tree()`

다만 private 함수 직접 import는 피한다. 이번 작업에서 public helper로 승격한다.

제안:

- 새 public API: `mdx_to_storage.emitter.parse_list_tree(content: str) -> list[ListNode]`

재구성 로직:

1. improved MDX list block -> list tree 생성
2. sidecar list item sequence와 index 기반 zip
3. 각 item에 대해
   - item text emit
   - item-level anchors 재삽입
   - child list / block child 재귀 재구성
4. top-level `<ul>` / `<ol>` wrapper regenerate

이렇게 하면 다음이 가능하다.

- 동일 텍스트 item이 여러 번 나와도 안정적
- nested list의 중복 삽입 방지
- image가 들어간 list item도 text patch 없이 처리

### 5.6 callout / details / ADF panel 재구성

callout은 이번 설계에서 "containing block에 text만 이식"하지 않는다.

이미 있는 자산:

- `mapping_recorder.record_mapping()` 는 callout의 child xpath를 생성한다
- `mdx_to_storage.parser.parse_mdx()` 와 `_emit_callout()` 은 child block 재귀 emission 을 지원한다

따라서 새 경로는 아래와 같다.

1. original callout body child order를 sidecar metadata에 저장
2. improved MDX callout body를 `parse_mdx()` 로 child block sequence로 파싱
3. child slot 단위로 reconstruct
4. 최종 body를 `<ac:rich-text-body>` 또는 `ac:adf-content` 아래에 다시 조립

주의:

- `macro-panel` 과 `ac:adf-extension` 은 body 구조는 같지만 outer wrapper가 다르다
- outer wrapper 보존은 `lost_info_patcher` 가 아니라 reconstruction metadata가 책임진다
- ADF panel raw outer fragment가 필요한 경우 sidecar에 raw wrapper를 저장한다

### 5.7 patch 적용 단위

modified block는 `new_inner_xhtml` 보다 `new_element_xhtml` 교체가 기본이다.

이유:

- top-level element 전체를 교체해야 wrapper, attribute, child structure를 한 번에 통제할 수 있다
- innerHTML 교체만으로는 callout outer wrapper, list root tag, table root tag의 일관성을 강제하기 어렵다

따라서 `xhtml_patcher.py` 에 새 액션을 추가한다.

- `replace_fragment`
  - 입력: `xhtml_xpath`, `new_element_xhtml`
  - 의미: xpath 대상 top-level element 전체를 새 fragment로 치환

기존 `insert` / `delete` 는 유지한다.

### 5.8 block identity와 planner

기존 `patch_builder.py` 는 전략 분기와 fallback이 많다. 새 설계는 planner를 분리한다.

제안 모듈:

- `reverse_sync/reconstruction_planner.py`
  - changed block -> reconstruction strategy 결정
- `reverse_sync/reconstruction_sidecar.py`
  - sidecar schema v3 load/build
- `reverse_sync/reconstructors.py`
  - paragraph/list/container별 fragment rebuild
- `reverse_sync/xhtml_normalizer.py`
  - shared normalization / plain-text extraction

`patch_builder.py` 는 최종적으로 orchestration thin layer가 된다.

## 6. 구현 범위와 비범위

### 이번 설계 범위

- modified top-level block의 whole-fragment reconstruction
- paragraph/list item inline anchor 재주입
- nested list reconstruction
- callout/details/ADF panel body reconstruction
- block identity 안정화
- golden/oracle 기반 테스트 체계 구축

### 이번 설계 비범위

- sidecar/rehydrator 전체를 단일 parser 체계로 통합하는 대형 리팩토링
- testcase에 없는 custom macro 일반화
- Confluence storage 전체에 대한 generic DOM diff 엔진

parser 통합은 후속 과제로 남긴다. 이번 작업은 "reverse-sync를 구조적 재구성 경로로 전환"하는 데 집중한다.

## 7. 테스트 설계

테스트는 두 묶음으로 나눈다.

1. 설계 검증 테스트
2. 회귀 방지 테스트

### 7.1 설계 검증 테스트

#### Level 0. Helper / invariant

새 파일 제안:

- `tests/test_reverse_sync_xhtml_normalizer.py`
- `tests/test_reverse_sync_reconstruction_offsets.py`
- `tests/test_reverse_sync_reconstruction_insert.py`

검증 항목:

- plain-text extraction이 original/emitted fragment에서 같은 규칙으로 동작하는지
- old -> new offset mapping이 삽입/삭제/대체에 대해 안정적인지
- raw anchor insertion이 DOM 파괴 없이 수행되는지
- `hash + line_range` disambiguation이 duplicate content에서도 안정적인지

여기서 review의 Critical 이슈를 먼저 red test로 고정한다.

필수 red cases:

1. paragraph + inline image
2. list item + image
3. duplicate hash candidate
4. namespace-bearing fragment normalization

#### Level 1. Block reconstruction against exact fragment oracle

새 파일 제안:

- `tests/test_reverse_sync_reconstruct_paragraph.py`
- `tests/test_reverse_sync_reconstruct_list.py`
- `tests/test_reverse_sync_reconstruct_container.py`

oracle:

- 기본: `expected.roundtrip.json.blocks[].xhtml_fragment`
- nested child: `page.xhtml` 에서 xpath extraction

검증 방식:

- unchanged MDX block를 reconstruct 했을 때 oracle fragment와 normalize-equal

대표 파라미터:

- list item + image: `544113141`, `544145591`, `692355151`, `880181257`, `883654669`
- callout + list: `1454342158`, `544145591`, `692355151`, `880181257`, `883654669`
- callout + code: `544112828`
- ADF panel: `1454342158`, `544379140`, `panels`
- inline paragraph image: `tests/reverse-sync/544376004`

`544376004` 는 `tests/testcases` 가 아니므로, unit test에서는 해당 page에서 관련 fragment만 추출한 minimal fixture를 추가해도 된다. 이것은 review의 "새 fixture가 아예 불필요하다고 말하면 안 된다"는 지적에 대한 현실적 대응이다.

#### Level 2. Changed block golden reconstruction

새 파일 제안:

- `tests/test_reverse_sync_reconstruction_goldens.py`

oracle:

- `expected.reverse-sync.patched.xhtml`
- 필요한 경우 `expected.reverse-sync.mapping.original.yaml` / `expected.reverse-sync.result.yaml`

대상:

- `original.mdx` + `improved.mdx` + `expected.reverse-sync.*` 가 존재하는 16개 `tests/testcases`

검증 방식:

- changed block만 reconstruct + page assembly 후 `expected.reverse-sync.patched.xhtml` 와 normalize-equal
- `expected.reverse-sync.result.yaml` 의 `status: pass` 케이스는 forward verify까지 exact pass

### 7.2 회귀 방지 테스트

#### Level 3. Existing sidecar / byte-equal gates

기존 테스트를 유지하고 schema v3에 맞춰 확장한다.

- `tests/test_reverse_sync_sidecar_v2.py`
- `tests/test_reverse_sync_rehydrator.py`
- `tests/test_reverse_sync_byte_verify.py`

변경점:

- `expected.roundtrip.json` builder/loader가 reconstruction metadata를 읽고 써야 한다
- unchanged case에서는 여전히 21/21 byte-equal 유지

#### Level 4. CLI / E2E

기존 테스트를 유지하되 reconstruction path를 기본 경로로 바꾼다.

- `tests/test_reverse_sync_cli.py`
- `tests/test_reverse_sync_e2e.py`
- `tests/test_reverse_sync_structural.py`

여기에 다음을 추가한다.

- `tests/reverse-sync/pages.yaml` 의 `expected_status: pass` 케이스는 새 경로에서도 계속 pass
- `expected_status: fail` 케이스는 failure type별로 하나씩 우선 red -> green 전환

우선순위는 아래 순으로 둔다.

1. list/image
2. callout/code
3. callout/list
4. ADF panel

### 7.3 현재 자산 활용 계획 요약

| 자산 | 수량 | 새 설계에서의 역할 |
|------|------|--------------------|
| `tests/testcases/*/page.xhtml` | 21 | exact source page, nested fragment extraction |
| `tests/testcases/*/expected.roundtrip.json` | 21 | unchanged top-level fragment oracle |
| `tests/testcases/*/original.mdx` | 16 | reverse-sync original input |
| `tests/testcases/*/improved.mdx` | 16 | reverse-sync changed input |
| `tests/testcases/*/expected.reverse-sync.patched.xhtml` | 16 | changed-page golden oracle |
| `tests/testcases/*/expected.reverse-sync.result.yaml` | 16 | expected verify outcome |
| `tests/testcases/*/attachments.v1.yaml` | 19 | image filename / asset context |
| `tests/testcases/*/page.v1.yaml`, `page.v2.yaml`, `children.v2.yaml`, `page.adf` | 18~19 | forward converter context, ADF/callout/link validation |
| `tests/reverse-sync/*` | 42 | 실사례 회귀 및 failure reproduction |

## 8. 단계별 구현 계획

### Phase 0. 공용 helper 추출

- `xhtml_normalizer.py` 추가
- `extract_plain_text()`, `normalize_fragment()`, `extract_fragment_by_xpath()` 구현
- list tree helper public API 승격

게이트:

- Level 0 helper tests green

### Phase 1. sidecar schema v3

- `RoundtripSidecar` 에 reconstruction metadata 추가
- builder/load/write/update 구현
- `hash + line_range` 기반 identity helper 도입

게이트:

- existing sidecar tests green
- unchanged 21개 `expected.roundtrip.json` roundtrip 유지

### Phase 2. clean block whole-fragment replacement

- heading/code/table/simple paragraph modified block를 reconstruction path로 전환
- `replace_fragment` patch 추가

게이트:

- simple modified golden cases green
- `transfer_text_changes()` 경로 없이 clean block 변경 처리 가능

### Phase 3. paragraph/list anchor reconstruction

- inline anchor metadata builder
- offset mapping + DOM insertion helper
- list item + nested list reconstruction

게이트:

- `544113141`, `544145591`, `692355151`, `880181257`, `883654669`
- `544376004` helper/unit case

### Phase 4. container reconstruction

- callout/details/ADF panel body reconstruction
- child slot order 기반 재귀 rebuild

게이트:

- `544112828`
- `1454342158`
- `544379140`
- `panels`

### Phase 5. planner 전환과 batch 회귀

- `patch_builder.py` modified path를 reconstruction planner로 위임
- legacy text-transfer path는 fallback 또는 제거

게이트:

- `tests/testcases` 16개 reverse-sync golden green
- `tests/reverse-sync/pages.yaml` pass 케이스 유지

## 9. 승인 기준

이 설계는 아래를 만족해야 구현 완료로 본다.

1. modified block의 기본 경로가 whole-fragment reconstruction 이다
2. paragraph/list anchor 처리가 plain-text 좌표계 기준으로 구현된다
3. test oracle이 `mapping.yaml` 이 아니라 `expected.roundtrip.json` / `page.xhtml` / `expected.reverse-sync.patched.xhtml` 로 확정된다
4. XHTML normalization은 BeautifulSoup 기반 공용 helper로 통일된다
5. duplicate content에서도 `hash + line_range` 기반 identity가 동작한다
6. 기존 `tests/testcases` / `tests/reverse-sync` 자산을 그대로 회귀 게이트로 사용할 수 있다

## 10. 최종 판단

PR #913의 원래 방향은 맞다. 다만 기존 문서는 "재구성으로 간다"는 선언에 비해, 실제 구현이 의존할 좌표계, oracle, sidecar 책임 분리가 부족했다.

새 설계의 핵심 차이는 다음 세 가지다.

- `convert_inline()` 역변환 가정을 버리고 plain-text 좌표계를 채택한다
- `mapping.yaml` 을 oracle 자리에서 내리고 `expected.roundtrip.json` 을 중심 artifact 로 올린다
- 기존 testcase 자산을 설계 검증 테스트와 회귀 테스트로 분리해 사용한다

이 기준으로 구현하면, 최종 목표인 "MDX 변경을 XHTML로 재구성하여 Confluence 문서를 업데이트"하는 기능을 현재 코드베이스 위에서 더 안정적으로 구현하고 유지보수할 수 있다.
