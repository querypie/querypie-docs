# Reverse Sync 전면 재구성 설계

> 최초 작성일: 2026-03-13
> 갱신일: 2026-03-15
> 기준 브랜치: `main`
> 기준 커밋: `9e0d43b91c2e47088274e13e82a5c2750e1529f9`
> 반영된 선행 PR:
> - `#913` reverse-sync 재구성 설계 초안
> - `#914` Phase 0 공용 helper 추출 (`xhtml_normalizer`, list tree public API)
> - `#915` Phase 1 sidecar schema v3
> - `#917` Phase 1 후속 정리 (`strict v3`, identity helper API 통일, reconstruction metadata 보강)
> 연관 문서:
> - `docs/plans/2026-03-13-reverse-sync-reconstruction-design-review.md`
> - `docs/plans/2026-03-15-reverse-sync-reconstruction-cleanup-scope.md`
> - `docs/analysis-reverse-sync-refactoring.md`

## 1. 문서 목적

이 문서는 2026-03-15 기준 `main` 브랜치 상태를 반영해, reverse-sync 재구성 계획을 다시 정리한 버전이다.

핵심 목적은 두 가지다.

1. 이미 `main`에 반영된 기반 작업과 아직 남은 재구성 작업을 분리해서 기록한다.
2. 남은 구현을 "legacy text patch 보강"이 아니라 "fragment reconstruction 기본 경로 전환"으로 계속 밀고 갈 수 있도록 단계와 게이트를 확정한다.

즉 이 문서는 더 이상 PR #913 시점의 순수 제안서가 아니다. 현재 `main`이 어디까지 와 있는지, 그리고 다음 단계가 정확히 무엇인지 정의하는 기준 문서다.

## 2. 2026-03-15 기준 main의 실제 상태

### 2.1 현재 런타임 기본 경로

현재 `reverse_sync_cli.py` 의 verify/push 경로는 여전히 아래 흐름을 기본으로 사용한다.

`MDX diff -> mapping lookup -> patch_builder.py -> xhtml_patcher.py -> roundtrip verify`

구체적으로는 다음 모듈이 아직 중심이다.

- `bin/reverse_sync/patch_builder.py`
- `bin/reverse_sync/text_transfer.py`
- `bin/reverse_sync/list_patcher.py`
- `bin/reverse_sync/table_patcher.py`
- `bin/reverse_sync/xhtml_patcher.py`

즉 "modified block를 새 XHTML fragment로 재구성한다"는 최종 목표는 아직 기본 경로가 아니다.

### 2.2 이미 main에 머지된 기반 작업

PR `#914`, `#915`, `#917`으로 인해, 원래 설계 문서에서 제안했던 선행 기반 중 상당 부분은 이미 코드로 들어와 있다.

#### Phase 0 완료: 공용 helper 추출

이미 반영된 항목:

- `bin/reverse_sync/xhtml_normalizer.py`
  - `extract_plain_text()`
  - `normalize_fragment()`
  - `extract_fragment_by_xpath()`
- `mdx_to_storage.emitter` 의 list tree 재사용 경로 공개
- 관련 테스트:
  - `tests/test_reverse_sync_xhtml_normalizer.py`
  - `tests/test_reverse_sync_list_tree.py`

의미:

- XHTML 비교와 fragment 추출을 위한 공용 기반이 생겼다.
- 새 설계가 별도 `lxml` 의존성 없이 BeautifulSoup 기반으로 진행될 수 있음이 확정됐다.

#### Phase 1 완료: sidecar schema v3 기반선

이미 반영된 항목:

- `bin/reverse_sync/sidecar.py`
  - `ROUNDTRIP_SCHEMA_VERSION = "3"`
  - `SidecarBlock.reconstruction`
  - `SidecarBlock.to_dict()` / `from_dict()`
  - `build_sidecar_identity_index()`
  - `find_sidecar_block_by_identity()`
- `build_sidecar()` 의 reconstruction metadata 생성 고도화
  - paragraph: `anchors`
  - list: `ordered`, `items`
  - container 계열: `child_xpaths`
- `load_sidecar()` 는 이제 v3 strict 검증만 허용
- 관련 테스트:
  - `tests/test_reverse_sync_sidecar_v3.py`
  - `expected.roundtrip.json` fixture 갱신

중요한 현재 상태:

- `reconstruction` 은 더 이상 완전한 placeholder-only 필드는 아니다.
- 하지만 paragraph/list의 실제 preserved anchor/unit 정보는 아직 비어 있다.
- list는 `ordered` 와 `items` 틀만 있고, item-level anchor/child block 정보는 아직 없다.
- container는 `child_xpaths` 까지 기록하지만, runtime reconstruction 에 필요한 raw preservation unit 까지는 저장하지 않는다.
- identity helper는 sidecar 레벨에서 정리됐지만, reverse-sync planner 기본 경로에는 아직 연결되어 있지 않다.

#### 보조 기반: rehydrator 존재

`bin/reverse_sync/rehydrator.py` 에는 다음 세 경로가 이미 존재한다.

1. fast path: MDX SHA 일치 시 sidecar 원본 재조립
2. splice path: 블록 해시 일치 시 sidecar fragment 유지, 불일치 시 emitter fallback
3. fallback path: 전체 emitter 재생성

하지만 이것은 아직 reverse-sync modified block 재구성기와 동일한 개념이 아니다.

- splice 경로는 `reconstruction` metadata를 사용하지 않는다.
- inline anchor 재주입, list child order 재구성, callout/details/ADF body 재조립은 아직 없다.

즉 rehydrator는 "현재 확보된 block-level sidecar 기반"을 보여주는 보조 축이지, 이번 문서의 최종 목표를 이미 달성한 상태는 아니다.

### 2.3 현재 테스트 자산

`main` 기준으로 확인된 자산 수치는 아래와 같다.

#### `tests/testcases/`

- 디렉터리 21개
- `page.xhtml`: 21개
- `expected.mdx`: 21개
- `expected.roundtrip.json`: 21개
- `original.mdx`: 16개
- `improved.mdx`: 16개
- `expected.reverse-sync.patched.xhtml`: 16개
- `attachments.v1.yaml`: 19개
- `page.v1.yaml`: 19개
- `page.v2.yaml`: 19개
- `children.v2.yaml`: 19개
- `page.adf`: 18개

#### `tests/reverse-sync/`

- 실제 fixture 디렉터리 42개
- 각 케이스에 `original.mdx`, `improved.mdx`, `page.xhtml` 존재
- `pages.yaml` 전체 엔트리: 66개
- 이 중 reverse-sync 테스트 메타데이터(`failure_type`)를 가진 실제 테스트 케이스: 42개
- `expected_status` 기준:
  - `pass`: 28개
  - `fail`: 14개

의미:

- `pages.yaml` 은 단순 카탈로그가 아니라 forward converter용 페이지 카탈로그와 reverse-sync 테스트 메타데이터를 함께 담당한다.
- 예전 문서의 `catalog_only` 요약보다, 지금은 `pages.yaml` 내 메타데이터가 실제 기준이다.

## 3. 원래 설계에서 유지되는 핵심 결정

PR #913 시점에 제안된 방향 중, 2026-03-15 기준 `main`에서도 그대로 유지해야 하는 결정은 아래 다섯 가지다.

### 3.1 좌표계는 MDX literal이 아니라 normalized plain text다

이 결정은 그대로 유지한다.

- `convert_inline()` 를 XHTML -> MDX 역변환기로 가정하지 않는다.
- anchor 위치 계산 기준은 `extract_plain_text()` 가 만든 plain text다.
- old/new 비교도 `old_mdx_text -> new_mdx_text` 가 아니라 `old_plain_text -> new_plain_text` 로 수행한다.

### 3.2 테스트 oracle은 `mapping.yaml` 이 아니다

현재도 runtime routing에 `mapping.yaml` 계층이 남아 있지만, fragment oracle로는 적합하지 않다.

우선순위는 그대로 아래 순서다.

1. `expected.roundtrip.json`
2. `page.xhtml`
3. `expected.reverse-sync.patched.xhtml`

### 3.3 XHTML 비교는 BeautifulSoup 기반 공용 normalizer로 통일한다

이 결정은 이미 `xhtml_normalizer.py` 로 구현되었다.

앞으로 새 테스트와 재구성 로직은 같은 normalizer를 공유해야 한다.

### 3.4 block identity는 hash 단독으로 끝내지 않는다

현재 `main`에는 `build_sidecar_identity_index()` 와 `find_sidecar_block_by_identity()` 가 들어와 있다.

기본 기준은 아래와 같다.

- `mdx_content_hash`
- `mdx_line_range`
- 동일 hash 후보군 내 stable order

다만 planner 단계에서는 필요 시 아래까지 함께 고려한다.

- `block_index`
- 동일 hash 후보군 내 상대 순서

즉 현재 helper는 최소 기반선이고, planner integration 단계에서 최종 identity 규칙을 완성해야 한다.

### 3.5 지원 범위 밖 구조는 fail-closed가 원칙이다

지원되지 않는 구조에서 fuzzy patch로 조용히 손상시키는 것이 가장 위험하다.

따라서 새 재구성 경로는 아래 원칙을 따른다.

- 재구성 가능한 block만 구조적으로 교체한다.
- 지원 범위 밖 구조는 명시적으로 fail 한다.
- fail 케이스는 `tests/testcases` 또는 `tests/reverse-sync` fixture로 승격해 범위를 넓힌다.

## 4. 현재 main에서 아직 해결되지 않은 문제

### 4.1 modified block 기본 경로가 아직 heuristic text patch다

`patch_builder.py` 는 여전히 다음 전략 분기에 의존한다.

- `direct`
- `containing`
- `list`
- `table`
- `skip`

그리고 핵심 경로에서 `transfer_text_changes()` 를 반복 호출한다.

이 구조는 list, table, callout, inline image/link 같은 Confluence 전용 구조를 안정적으로 다루기 어렵다.

### 4.2 `reconstruction` metadata가 아직 runtime reconstruction 에 충분하지 않다

현재 `build_sidecar()` 는 `BlockMapping` 기반으로 metadata를 기록하지만, 아직 다음 공백이 남아 있다.

- paragraph: `anchors` 는 비어 있다.
- list: `ordered` 는 기록되지만 `items` 내부 정보는 비어 있다.
- container: `child_xpaths` 는 기록되지만 preserved raw unit 은 저장하지 않는다.
- paragraph/list/container 모두 anchor offset, affinity, raw_xhtml 같은 실제 재주입 정보는 아직 없다.

즉 schema와 최소 메타 구조는 준비됐지만, runtime reconstruction 에 필요한 실제 preservation metadata 는 아직 충분하지 않다.

### 4.3 patcher가 fragment replacement 중심으로 바뀌지 않았다

`xhtml_patcher.py` 의 modify 경로는 아직 다음 두 방식만 사용한다.

- `old_plain_text` + `new_plain_text`
- `new_inner_xhtml`

아직 없는 것:

- top-level element 전체 교체를 위한 `replace_fragment`
- DOM 삽입 기준의 inline anchor rehydration helper

### 4.4 container 재구성이 없다

아직 남은 핵심 공백:

- nested list child order 기반 재구성
- callout body 재구성
- details 재구성
- ADF panel body 재구성

이 부분이 해결되지 않으면 `main`은 복잡한 block에서 계속 heuristic fallback에 의존하게 된다.

### 4.5 mapping 계층이 여전히 런타임 기본 경로를 잡고 있다

현재 `SidecarEntry`, `load_sidecar_mapping()`, `build_mdx_to_sidecar_index()` 계층은 남아 있고, patch planning도 여기에 기대고 있다.

장기 목표는 분명하다.

- `RoundtripSidecar v3` 가 primary runtime artifact가 된다.
- `mapping.yaml` 계층은 디버그/보조 용도로 축소한다.

## 5. 목표 아키텍처

최종적으로 reverse-sync modified block 기본 경로는 아래 형태여야 한다.

`MDX diff -> changed block identify -> reconstruct fragment -> restore lost info / preserved anchors -> replace top-level fragment -> forward verify`

여기서 핵심은 "텍스트 수정분 이식"이 아니라 "fragment 재구성 후 교체"다.

### 5.1 block 분류

새 planner는 modified block를 네 종류로 나눈다.

#### A. Clean block

대상:

- heading
- code block / code macro
- table
- hr
- preserved anchor가 없는 단순 paragraph

처리:

- `mdx_to_storage.emit_block()` 으로 새 fragment 생성
- 필요 시 `lost_info_patcher` 적용
- `replace_fragment` 로 top-level element 전체 교체

#### B. Inline-anchor block

대상:

- paragraph 내부 `ac:image`, `ac:link` 등 preservation unit
- list item 내부 inline image 또는 trailing preserved node

처리:

1. improved MDX block를 emit
2. emitted fragment의 `new_plain_text` 추출
3. sidecar의 `old_plain_text`, `anchors` 로 offset 매핑
4. DOM 기준으로 raw anchor XHTML 재삽입
5. 최종 fragment replace

#### C. Ordered child block

대상:

- nested list
- callout
- details
- ADF panel body

처리:

- original child order를 sidecar metadata에 저장
- improved MDX child block sequence를 파싱
- child slot 단위로 재귀 reconstruct
- outer wrapper는 fragment-level로 다시 조립

#### D. Opaque block

대상:

- 현재 emitter가 재구성할 수 없는 custom macro
- testcase/metadata 규칙이 아직 없는 구조

처리:

- 명시적 fail
- fixture 추가 후 범위 확장

### 5.2 필요한 새 모듈 또는 책임 분리

현재 `main` 기준으로 필요한 후속 구현 축은 아래와 같다.

- `reverse_sync/reconstruction_planner.py`
  - change -> reconstruction strategy 결정
- `reverse_sync/reconstructors.py`
  - paragraph/list/container별 fragment 재구성
- `reverse_sync/sidecar.py` 확장
  - 실제 anchor/item/container metadata 기록
- `reverse_sync/xhtml_patcher.py` 확장
  - `replace_fragment` 추가
  - fragment-level patch 적용기로 역할 축소

`patch_builder.py` 는 최종적으로 thin orchestration layer가 되거나, planner로 책임을 넘긴 뒤 축소되어야 한다.

## 6. 단계별 구현 계획

### Phase 0. 공용 helper 추출

상태: 완료, `main` 반영됨

완료 기준:

- `xhtml_normalizer.py` 추가
- fragment normalize/plain-text extraction/xpath extraction 구현
- list tree public API 확보

### Phase 1. sidecar schema v3 기반선

상태: 완료, `main` 반영됨

완료 기준:

- `reconstruction` 필드 추가
- strict v3 load 정착
- `build_sidecar_identity_index()` / `find_sidecar_block_by_identity()` 도입
- `BlockMapping` 기반 reconstruction metadata 생성

남은 후속 작업:

- placeholder 수준의 anchor/item metadata를 실제 metadata로 채우기
- planner 경로에서 identity helper 사용하기

### Phase 2. clean block whole-fragment replacement

상태: 미완료

구현 항목:

- `replace_fragment` patch action 추가
- heading/code/table/simple paragraph를 fragment replacement로 전환
- modified block에서 `new_plain_text` 기반 patch 의존도 제거

게이트:

- 기존 normalizer/sidecar 테스트 green 유지
- simple modified 케이스에서 `expected.reverse-sync.patched.xhtml` normalize-equal

### Phase 3. inline-anchor 및 list 재구성

상태: 미완료

구현 항목:

- paragraph/list item anchor metadata builder
- old/new plain-text offset mapping helper
- raw anchor DOM insertion helper
- nested list tree 기반 reconstruction

우선 대상 fixture:

- `tests/testcases` 내 list/image 혼합 케이스
- `tests/reverse-sync/544376004`

게이트:

- inline image가 있는 paragraph/list item 재구성 green
- duplicate hash 후보에서도 identity가 안정적으로 동작

### Phase 4. container 재구성

상태: 미완료

구현 항목:

- callout/details/ADF panel body child order 저장
- child slot 기반 재귀 rebuild
- outer wrapper와 inner body 책임 분리

우선 대상 fixture:

- `544112828`
- `1454342158`
- `544379140`
- `panels`

게이트:

- container fragment oracle normalize-equal
- changed-page golden 검증 통과

### Phase 5. 기본 경로 전환 및 legacy 축소

상태: 미완료

구현 항목:

- `patch_builder.py` modified path를 reconstruction planner로 위임
- `mapping.yaml` runtime 의존 축소
- legacy text-transfer 경로를 explicit fallback 또는 제거 대상으로 전환

게이트:

- `tests/testcases` 의 16개 changed golden 통과
- `tests/reverse-sync/pages.yaml` 의 `expected_status: pass` 케이스 유지
- unsupported 구조는 silent corruption 없이 명시적 fail

## 7. 테스트 계획

### 7.1 현재 반드시 유지할 기존 green 게이트

- `tests/test_reverse_sync_xhtml_normalizer.py`
- `tests/test_reverse_sync_list_tree.py`
- `tests/test_reverse_sync_sidecar_v3.py`
- `tests/test_reverse_sync_rehydrator.py`
  - unchanged testcase에 대한 splice byte-equal 검증 포함

이 테스트들은 "이미 main에 들어온 기반이 깨지지 않는다"는 최소 조건이다.

### 7.2 새로 추가할 설계 검증 테스트

필수 신규 묶음:

- `tests/test_reverse_sync_reconstruction_offsets.py`
- `tests/test_reverse_sync_reconstruction_insert.py`
- `tests/test_reverse_sync_reconstruct_paragraph.py`
- `tests/test_reverse_sync_reconstruct_list.py`
- `tests/test_reverse_sync_reconstruct_container.py`
- `tests/test_reverse_sync_reconstruction_goldens.py`

검증 원칙:

1. unchanged fragment는 `expected.roundtrip.json` 기준 exact 또는 normalize-equal
2. nested child fragment는 `page.xhtml` + xpath extraction 기준
3. changed page는 `expected.reverse-sync.patched.xhtml` 기준

### 7.3 fixture 활용 원칙

| 자산 | 현재 수량 | 역할 |
|------|-----------|------|
| `tests/testcases/*/page.xhtml` | 21 | 원본 페이지, nested fragment 추출 |
| `tests/testcases/*/expected.roundtrip.json` | 21 | unchanged top-level fragment oracle |
| `tests/testcases/*/original.mdx` | 16 | reverse-sync original 입력 |
| `tests/testcases/*/improved.mdx` | 16 | reverse-sync changed 입력 |
| `tests/testcases/*/expected.reverse-sync.patched.xhtml` | 16 | changed-page golden |
| `tests/reverse-sync/*` | 42 | 실제 회귀 케이스 및 failure reproduction |
| `tests/reverse-sync/pages.yaml` | 66 entries | catalog + expected_status/failure_type/severity |

## 8. legacy 코드 정리 기준

상세 삭제 대상과 범위는 `docs/plans/2026-03-15-reverse-sync-reconstruction-cleanup-scope.md` 에 별도로 정리한다.

다음 코드는 새 경로가 기본이 되기 전에는 제거하지 않는다.

- `text_transfer.py`
- `list_patcher.py`
- `table_patcher.py`
- `inline_detector.py`
- `patch_builder.py` 내부 heuristic strategy 분기
- `xhtml_patcher.py` 의 text-only modify 경로

반대로 아래 조건이 충족되면 정리 대상으로 넘긴다.

1. changed golden 16개가 새 reconstruction 경로로 green
2. `expected_status: pass` 회귀 케이스 유지
3. unsupported 구조는 명시적 fail
4. `mapping.yaml` 없이도 sidecar v3 기반 runtime planning 가능

그 시점부터는 legacy heuristic path를 기본 동작에서 제거하고, 필요하면 debug fallback으로만 남긴다.

## 9. 최종 승인 기준

이번 재구성 작업은 아래를 만족해야 완료로 본다.

1. modified block 기본 경로가 whole-fragment reconstruction 으로 전환된다.
2. paragraph/list anchor 재주입이 plain-text 좌표계 기준으로 구현된다.
3. test oracle이 `mapping.yaml` 이 아니라 `expected.roundtrip.json`, `page.xhtml`, `expected.reverse-sync.patched.xhtml` 로 고정된다.
4. `RoundtripSidecar v3` 의 `reconstruction` 필드가 실제 runtime metadata를 담는다.
5. `build_sidecar_identity_index()` / `find_sidecar_block_by_identity()` 기준 identity 가 planner에 통합되고, duplicate content에서도 안정적으로 동작한다.
6. unsupported 구조에서 silent corruption 없이 fail-closed가 유지된다.

## 10. 판단

2026-03-15 기준 `main`은 재구성 설계의 출발점이 아니라 이미 Phase 0과 Phase 1을 흡수한 상태다. 따라서 앞으로의 계획은 "설계를 시작한다"가 아니라 "이미 들어온 기반선 위에서 modified path를 실제 fragment reconstruction으로 전환한다"여야 한다.

정리하면 현재의 정확한 방향은 다음과 같다.

- `xhtml_normalizer` 와 sidecar v3는 이미 완료된 기반선으로 본다.
- `#917` 이후 sidecar는 strict v3 와 개선된 metadata shape 를 가지지만, 아직 runtime reconstruction 에 필요한 preservation 정보는 충분하지 않다.
- reverse-sync 기본 경로는 아직 legacy patch 체인에 있으므로 Phase 2 이후가 본 작업이다.
- 다음 구현의 승패는 sidecar metadata를 실제 재구성 정보로 채우고, patcher/planner를 fragment replacement 중심으로 바꾸는 데 달려 있다.

이 기준으로 문서와 구현을 맞추면, 현재 `main`의 실제 상태와 앞으로의 작업 범위가 일관되게 연결된다.
