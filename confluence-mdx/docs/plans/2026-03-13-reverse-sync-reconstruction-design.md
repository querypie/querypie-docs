# Reverse Sync 전면 재구성 설계

> 최초 작성일: 2026-03-13
> 갱신일: 2026-03-19 (4차 — Phase 5 진행 현황 반영 및 설계 기준선 교정)
> 기준 브랜치: `main`
> 기준 커밋: `a1f4a0ac` (PR #937 머지)
> 반영된 선행 PR:
> - `#913` reverse-sync 재구성 설계 초안
> - `#914` Phase 0 공용 helper 추출 (`xhtml_normalizer`, list tree public API)
> - `#915` Phase 1 sidecar schema v3
> - `#917` Phase 1 후속 정리 (`strict v3`, identity helper API 통일, reconstruction metadata 보강)
> - `#886` Phase 2 clean block whole-fragment replacement
> - `#902` Phase 2 + Phase 3 재구성 파이프라인 구현
> - `#888` splice rehydrator 개선 및 sidecar identity fallback 강화
> - `#903` Phase 4 container 재구성 및 list anchor 정확도 개선
> - `#928` Phase 5 Axis 3 — legacy list/table patcher 제거 및 라우팅 정확도 개선
> - `#937` testcase original.mdx 재생성 (forward converter 작동 변경 반영)
> - `#942` Phase 5 Axis 1 — callout/container routing을 reconstruction 경로로 전환
> 연관 문서:
> - `docs/plans/2026-03-13-reverse-sync-reconstruction-design-review.md`
> - `docs/plans/2026-03-15-reverse-sync-reconstruction-cleanup-scope.md`
> - `docs/analysis-reverse-sync-refactoring.md`

## 1. 문서 목적

이 문서는 reverse-sync 전면 재구성의 기준 설계 문서다. 최초 작성(2026-03-13) 이후 세 차례 갱신하며 `main` 브랜치 실제 상태를 반영해 왔다.

- **1차**: Phase 0–2 완료 반영
- **2차**: Phase 3–4 완료 반영 (2026-03-16)
- **3차**: Phase 5 상세 구현 계획 반영, 코드 현황 재검증 (2026-03-18)
- **4차**: Phase 5 Axis 1 routing 변경 반영, 기준선 수치 교정, 삭제 조건 재정의 (2026-03-19)

핵심 목적은 두 가지다.

1. 이미 `main`에 반영된 기반 작업과 아직 남은 재구성 작업을 분리해서 기록한다.
2. 남은 구현을 "legacy text patch 보강"이 아니라 "fragment reconstruction 기본 경로 전환"으로 계속 밀고 갈 수 있도록 단계와 게이트를 확정한다.

## 2. 2026-03-18 기준 main의 실제 상태

### 2.1 현재 런타임 기본 경로

`reverse_sync_cli.py`의 verify/push 경로는 아래 흐름을 사용한다.

```
MDX diff
  → record_mapping(xhtml)           # mapping 계층 (CLI 직접 호출 — Phase 5 Axis 2 캡슐화 대상)
  → build_sidecar(xhtml, mdx)       # v3 sidecar 생성
  → build_patches(..., mdx_to_sidecar=None, roundtrip_sidecar=sidecar)
      → _build_mdx_to_sidecar_from_v3()   # v3 sidecar에서 인덱스 자동 생성
      → clean block → replace_fragment     # Phase 2
      → inline-anchor block → reconstruct_fragment_with_sidecar()  # Phase 3
      → container block (anchor 있음) → 'direct' → reconstruct_container_fragment()
                                           # ← PR #942로 전환 완료
      → container block (anchor 없음, clean) → 'containing' → _flush_containing_changes()
                                           # ← text_transfer 잔존 (Phase 5 Axis 1 fallback)
      → paired delete+add (reconstruction 불가) → transfer_text_changes()
                                           # ← text_transfer 잔존 (Phase 5 Axis 1 대상)
      → direct block with ac:link/ri:attachment → transfer_text_changes()
                                           # ← text_transfer 잔존 (Phase 5 Axis 1 대상)
  → patch_xhtml()
  → roundtrip verify
```

**이미 제거된 모듈:**

- `bin/reverse_sync/list_patcher.py` — 삭제됨 (PR #928)
- `bin/reverse_sync/inline_detector.py` — 삭제됨 (PR #928)

**아직 잔존하는 legacy 경로:**

`transfer_text_changes()` 호출 지점이 현재 3개 존재한다:

1. `_flush_containing_changes()` — anchor 없는 clean container/callout의 'containing' fallback
2. `patch_builder.py` paired delete+add path — clean/table replacement 불가 시 fallback (line ~430)
3. `patch_builder.py` 'direct' path — `<ac:link>` / `<ri:attachment>` 포함 블록 fallback (line ~657)

그 외 CLI 구조적 중복:

- `reverse_sync_cli.py`의 `record_mapping()` 직접 호출 — `build_patches()` 내부로 캡슐화 대상
- `SidecarEntry` 기반 `_build_mdx_to_sidecar_from_v3()` 출력 — v3 sidecar 직접 참조로 교체 대상

### 2.2 이미 main에 머지된 기반 작업

#### Phase 0 완료: 공용 helper 추출

- `bin/reverse_sync/xhtml_normalizer.py`
  - `extract_plain_text()`
  - `normalize_fragment()`
  - `extract_fragment_by_xpath()`
- `mdx_to_storage.emitter`의 list tree 재사용 경로 공개
- 관련 테스트: `tests/test_reverse_sync_xhtml_normalizer.py`, `tests/test_reverse_sync_list_tree.py`

#### Phase 1 완료: sidecar schema v3 기반선

- `bin/reverse_sync/sidecar.py`
  - `ROUNDTRIP_SCHEMA_VERSION = "3"`
  - `SidecarBlock.reconstruction`
  - `build_sidecar_identity_index()` / `find_sidecar_block_by_identity()`
- `build_sidecar()`의 reconstruction metadata 생성 고도화
  - paragraph: `anchors`
  - list: `ordered`, `items`
  - container 계열: `child_xpaths`, `children`
- `load_sidecar()`는 v3 strict 검증만 허용
- 관련 테스트: `tests/test_reverse_sync_sidecar_v3.py`, `expected.roundtrip.json` fixture 갱신

#### Phase 2 완료: clean block whole-fragment replacement

- `bin/reverse_sync/xhtml_patcher.py` — `replace_fragment` patch action 추가
- `bin/reverse_sync/patch_builder.py`
  - `_is_clean_block()` — preserved anchor 없는 단순 paragraph, heading, code, table 판별
  - `_build_replace_fragment_patch()` — clean block modified path를 whole-fragment replacement로 전환
- `bin/reverse_sync/reverse_sync_cli.py` — verify 경로에서 `build_sidecar()` 호출
- 관련 테스트: `tests/test_reverse_sync_reconstruction_goldens.py` 추가

#### Phase 3 완료: inline-anchor 및 list 재구성

- `bin/reverse_sync/sidecar.py`
  - `_build_anchor_entries()` — paragraph 내 `ac:image`의 offset + raw XHTML 기록
  - `_build_list_anchor_entries()` — list item 내 `ac:image`를 path 기반으로 기록 (중첩 list 지원)
- `bin/reverse_sync/reconstructors.py` (신규 파일)
  - `map_anchor_offset()` — difflib opcode 기반 offset 매핑, `affinity` 파라미터로 경계 방향 제어
  - `insert_anchor_at_offset()` — 계산된 offset 위치에 anchor를 DOM에 삽입
  - `reconstruct_inline_anchor_fragment()` — paragraph 재구성 진입점
  - `sidecar_block_requires_reconstruction()` — sidecar block의 재구성 필요 여부 판별
  - `reconstruct_fragment_with_sidecar()` — fragment + sidecar를 받아 재구성 실행하는 통합 인터페이스
- `bin/reverse_sync/patch_builder.py`
  - `_find_roundtrip_sidecar_block()` — xpath 조회 → content hash 검증 → identity fallback 순으로 sidecar block 탐색
  - list strategy 분기: sidecar anchor가 있으면 `replace_fragment`, 없으면 skip/fail
- 관련 테스트: golden test 12개, `tests/test_reverse_sync_reconstruct_paragraph.py`, `tests/test_reverse_sync_reconstructors.py`

#### Phase 4 완료: container 재구성

- `bin/reverse_sync/sidecar.py` — container child metadata 기록 (`children` list: xpath, fragment, plain_text, type)
- `bin/reverse_sync/reconstructors.py`
  - `reconstruct_container_fragment()`, `container_sidecar_requires_reconstruction()` 구현
  - `_rewrite_paragraph_on_template()` — inline markup(bold/italic/link) 보존
  - `_remove_html_img_if_same_image()` — anchor 재삽입 시 중복 `<img>` 제거
- outer wrapper template 보존: `sidecar_block.xhtml_fragment`로 macro 속성 유지
- 완료 fixture: `544112828`, `544379140`, `panels`, `1454342158`

#### 보조 기반: rehydrator 개선

`bin/reverse_sync/rehydrator.py`에는 다음 경로가 존재한다:

1. fast path: `sidecar_matches_mdx`가 True인 경우 MDX 재파싱 없이 `sidecar.reassemble_xhtml()` 반환
2. splice path: 블록 해시 일치 시 sidecar fragment 유지, 불일치 시 emitter fallback
3. fallback path: 전체 emitter 재생성

### 2.3 현재 테스트 자산 (2026-03-18 기준)

#### `tests/testcases/`

- 디렉터리 21개
- `page.xhtml`: 21개 / `expected.mdx`: 21개 / `expected.roundtrip.json`: 21개
- `original.mdx`: 16개 (PR #937에서 forward converter 작동 변경 반영하여 재생성)
- `improved.mdx`: 16개 / `expected.reverse-sync.patched.xhtml`: 16개

#### `tests/reverse-sync/`

- 실제 fixture 디렉터리 42개
- `pages.yaml` 전체 엔트리: 66개
- reverse-sync 테스트 케이스 (`failure_type` 있는 항목): 42개
- `expected_status` 기준:
  - `pass`: **31개** — 현재 전부 통과
  - `fail`: **11개** — 현재 전부 실패 (예상됨)

#### pytest 전체

- 2026-03-18 기준: **전체 passed, 0 failed** (CI green)

---

## 3. 원래 설계에서 유지되는 핵심 결정

### 3.1 좌표계는 MDX literal이 아니라 normalized plain text다

- `convert_inline()`을 XHTML → MDX 역변환기로 가정하지 않는다.
- anchor 위치 계산 기준은 `extract_plain_text()`가 만든 plain text다.
- old/new 비교도 `old_plain_text → new_plain_text`로 수행한다.

### 3.2 테스트 oracle은 `mapping.yaml`이 아니다

우선순위:

1. `expected.roundtrip.json`
2. `page.xhtml`
3. `expected.reverse-sync.patched.xhtml`

### 3.3 XHTML 비교는 BeautifulSoup 기반 공용 normalizer로 통일한다

이미 `xhtml_normalizer.py`로 구현됐다. 새 테스트와 재구성 로직은 같은 normalizer를 공유한다.

### 3.4 block identity는 hash 단독으로 끝내지 않는다

기본 기준: `mdx_content_hash`, `mdx_line_range`, 동일 hash 후보군 내 stable order.
planner 단계에서는 필요 시 `block_index`, 동일 hash 후보군 내 상대 순서도 함께 고려한다.

### 3.5 지원 범위 밖 구조는 fail-closed가 원칙이다

- 재구성 가능한 block만 구조적으로 교체한다.
- 지원 범위 밖 구조는 명시적으로 fail 한다.
- fail 케이스는 `tests/testcases` 또는 `tests/reverse-sync` fixture로 승격해 범위를 넓힌다.

---

## 4. 현재 main에서 남은 문제

### 4.1 text_transfer 잔존 경로 3곳

`transfer_text_changes()`는 현재 `patch_builder.py` 내 3개 호출 지점에 남아있다.

**지점 1 — containing fallback** (PR #942로 일부 해소):
PR #942에서 `_resolve_mapping_for_change()`에 `xpath_to_sidecar_block` 파라미터를 추가하여, anchor가 있는 container/callout 블록은 'containing' 대신 'direct' + `reconstruct_container_fragment()` 경로로 전환됐다. 단, anchor 없는 clean container는 여전히 `_flush_containing_changes()` → `transfer_text_changes()` fallback을 거친다.

**지점 2 — paired delete+add fallback** (미해소):
같은 인덱스에서 delete 후 add로 쌍이 된 블록 중 clean/table replacement가 불가능한 경우 `transfer_text_changes()`로 plain text만 교체한다. 이 경로는 PR #942와 무관하게 독립적으로 잔존한다.

**지점 3 — direct path ac:link/ri:attachment fallback** (미해소):
'direct' 전략 블록에서 `<ac:link>` 또는 `<ri:attachment>`가 포함된 경우 inner XHTML 재생성 시 소실 위험이 있어 `transfer_text_changes()`로 fallback한다.

`text_transfer.py` 삭제는 3개 호출 지점이 모두 제거된 이후에만 가능하다. Axis 1만으로는 조건이 성립하지 않는다.

### 4.2 CLI `record_mapping()` 직접 호출

`reverse_sync_cli.py`는 `record_mapping(xhtml)`을 직접 호출하고 그 결과를 `build_patches()`에 전달한다. 이 호출과 전달 책임을 `build_patches()` 내부로 캡슐화하는 것이 Axis 2의 목표다. 단, `build_sidecar()` 내부에서도 `record_mapping()`을 별도로 호출하고 있으므로(`sidecar.py:233`), Axis 2 이후에도 runtime에서 `record_mapping()`은 2회 호출된다. runtime 중복 제거는 SidecarBlock이 BlockMapping 필드를 흡수한 후 별도 단계에서 진행한다.

`build_patches()`의 `mappings`와 `xpath_to_mapping` 파라미터는 이 캡슐화와 별개로 광범위하게 사용된다:

- `child_to_parent` 역참조 맵 구축 (중복 매칭 방지)
- `distribute_lost_info_to_mappings()` (block_id 기반 lost_info 분배)
- `_find_best_list_mapping_by_text()` (text prefix 기반 fallback)
- delete 패치 생성(`_build_delete_patch`)
- insert anchor 계산(`_find_insert_anchor`)

이 파라미터들을 sidecar v3 기반으로 완전 대체하려면 위 기능들의 대체 경로를 먼저 정의해야 한다. Axis 2의 목표는 **CLI의 `record_mapping()` 직접 호출을 `build_patches()` 내부로 캡슐화하고, `SidecarEntry` import를 제거**하는 것에 한정한다. `build_patches()` 시그니처의 `mappings`/`xpath_to_mapping` 파라미터 제거는 그 대체 경로가 확정된 이후 별도 단계로 진행한다.

### 4.3 해결된 문제 (참고)

| 항목 | 해결 시점 |
|------|-----------|
| modified block 기본 경로가 heuristic text patch | Phase 2 — clean block은 `replace_fragment` 기본 경로로 전환 |
| `reconstruction` metadata가 runtime에 충분하지 않음 | Phase 3 — `_build_anchor_entries`, `_build_list_anchor_entries` |
| patcher에 `replace_fragment` 없음 | Phase 2 — `xhtml_patcher.py`에 추가 |
| inline anchor 재주입 helper 없음 | Phase 3 — `reconstructors.py` 신규 구현 |
| container 재구성 없음 | Phase 4 — `reconstruct_container_fragment()` 구현 |
| `list_patcher.py`, `inline_detector.py` 잔존 | PR #928 — 삭제 완료 |
| `_heading_lookahead()` 기술 부채 | 이미 부재 — `parse_mdx_blocks`의 FC 패턴 처리(빈 줄 없는 연속행을 같은 list 항목으로 합치는 로직)가 이미 구현되어 있어 별도 heuristic 불필요 |
| testcase `original.mdx` forward converter 작동 불일치 | PR #937 — 전체 재생성 완료 |

---

## 5. 목표 아키텍처

최종적으로 reverse-sync modified block 기본 경로는 아래 형태여야 한다.

```
MDX diff → changed block identify → reconstruct fragment
         → restore lost info / preserved anchors
         → replace top-level fragment → forward verify
```

여기서 핵심은 "텍스트 수정분 이식"이 아니라 "fragment 재구성 후 교체"다.

### 5.1 block 분류

#### A. Clean block

대상: heading, code block/macro, table, hr, preserved anchor가 없는 단순 paragraph

처리:
- `mdx_to_storage.emit_block()`으로 새 fragment 생성
- 필요 시 `lost_info_patcher` 적용
- `replace_fragment`로 top-level element 전체 교체

#### B. Inline-anchor block

대상: paragraph 내부 `ac:image`, `ac:link` 등 preservation unit, list item 내부 inline image 또는 trailing preserved node

처리:
1. improved MDX block을 emit
2. emitted fragment의 `new_plain_text` 추출
3. sidecar의 `old_plain_text`, `anchors`로 offset 매핑
4. DOM 기준으로 raw anchor XHTML 재삽입
5. 최종 fragment replace

#### C. Ordered child block

대상: nested list, callout, details, ADF panel body

처리:
- original child order를 sidecar metadata에 저장
- improved MDX child block sequence를 파싱
- child slot 단위로 재귀 reconstruct
- outer wrapper는 fragment-level로 다시 조립

#### D. Opaque block

대상: 현재 emitter가 재구성할 수 없는 custom macro, testcase/metadata 규칙이 아직 없는 구조

처리: 명시적 fail → fixture 추가 후 범위 확장

### 5.2 모듈 책임 배치 (최종 목표)

| 모듈 | 최종 역할 |
|------|-----------|
| `patch_builder.py` | thin orchestration layer — strategy 판단 후 재구성 함수 호출 |
| `reconstructors.py` | paragraph/list/container별 fragment 재구성 |
| `sidecar.py` | v3 roundtrip core (mapping 계층 분리) |
| `xhtml_patcher.py` | fragment-level DOM patcher (`replace_fragment` 중심) |
| `text_transfer.py` | 삭제 예정 |
| `table_patcher.py` | `is_markdown_table()` 이동 후 삭제 예정 |

---

## 6. 단계별 구현 계획

### Phase 0. 공용 helper 추출

상태: **완료**, `main` 반영됨 (PR #914)

### Phase 1. sidecar schema v3 기반선

상태: **완료**, `main` 반영됨 (PR #915, #917)

### Phase 2. clean block whole-fragment replacement

상태: **완료**, `main` 반영됨 (PR #886, #902)

### Phase 3. inline-anchor 및 list 재구성

상태: **완료**, `main` 반영됨 (PR #902, #888)

### Phase 4. container 재구성

상태: **완료**, `main` 반영됨 (PR #903)

### Phase 5. 기본 경로 전환 및 legacy 축소

상태: **미완료** — 진입 게이트 충족, 시작 가능

Phase 5는 3개 Axis로 구성된다. Axis 1 → Axis 2 → Axis 3 순서로 진행한다.

#### 게이트 현황

| 게이트 조건 | 상태 |
|-------------|------|
| `tests/testcases` 16개 changed golden 통과 | ✅ |
| `expected_status: pass` 케이스 유지 | ✅ 31개 통과 |
| unsupported 구조는 silent corruption 없이 skip (patch 미생성) | ✅ — 단, 일부는 명시적 fail이 아닌 skip으로 처리됨 (§3.5 목표와 차이 있음) |
| `mapping.yaml` 없이 sidecar v3만으로 runtime planning 가능 | ⬜ Phase 5 이후 별도 단계 (SidecarBlock 스키마 확장 필요) |

---

#### Phase 5 Axis 1: text_transfer 호출 지점 전수 제거

**목표:** `transfer_text_changes()` 3개 호출 지점을 모두 제거하고 `text_transfer.py`를 삭제한다.

**현황 (PR #942 이후):**

PR #942에서 `_resolve_mapping_for_change()`에 `xpath_to_sidecar_block` 파라미터를 추가하고, anchor가 있는 container/callout은 'containing' 대신 'direct' + `reconstruct_container_fragment()` 경로로 전환했다. 이 변경으로 **지점 1 (containing fallback)** 이 anchor 있는 케이스에서는 해소됐다. 단, anchor 없는 clean container는 여전히 fallback을 거친다.

**남은 작업:**

| 지점 | 위치 | 해소 방법 |
|------|------|-----------|
| ① containing fallback (clean container) | `_flush_containing_changes()` | clean container도 `emit_block()` 기반 replace_fragment로 전환. **단, 현재 `reconstruct_container_fragment()`는 clean container(anchor/item 없음)에서 `new_fragment`를 그대로 반환하므로 outer wrapper template 보존(Step 3)이 적용되지 않는다.** `emit_block()`은 `ac:name`, `panelIcon` 등 MDX round-trip 가능한 속성만 재생성하며, `ac:macro-id`, `ac:schema-version` 등 Confluence 메타 속성은 유실된다. 따라서 전환 전에 `reconstruct_container_fragment()`를 확장하여 clean container에서도 sidecar의 `xhtml_fragment`를 outer wrapper template으로 적용하는 로직을 추가해야 한다. |
| ② paired delete+add fallback | `patch_builder.py` ~line 430 | clean/table replacement 불가 케이스를 reconstruction 또는 명시적 skip으로 전환 |
| ③ direct path ac:link/ri:attachment fallback | `patch_builder.py` ~line 657 | `sidecar_block_requires_reconstruction()` 경로로 커버 가능하면 전환, 불가하면 명시적 fail로 전환 |

**기존 containing 분기의 현재 구조 (참고):**

```
strategy == 'containing' (build_patches 내):
  sidecar_block = _find_roundtrip_sidecar_block(...)
  if container_sidecar_requires_reconstruction(sidecar_block):    # anchor 있음
      → _build_replace_fragment_patch() + reconstruct_container_fragment()  ← 이미 동작 중
  else:                                                            # anchor 없음 (clean)
      → containing_changes → _flush_containing_changes() → transfer_text_changes()  ← 제거 대상
```

즉 anchor 있는 케이스는 기존 'containing' 분기 내에서도 이미 reconstruction 경로를 탔다. PR #942의 routing 변경은 코드 조직을 명확히 하기 위한 것이며, 실질적인 남은 작업은 위 3개 지점의 fallback 제거다.

**① clean container 전환을 위한 `reconstruct_container_fragment()` 확장 방안:**

현재 `reconstruct_container_fragment()`는 anchor/item이 없으면 early return한다(`reconstructors.py:449`). clean container를 replace_fragment로 전환하려면 Step 3(outer wrapper template 보존)만 별도로 적용해야 한다:

```
현재 (reconstructors.py:449):
  if not any(c.get('anchors') or c.get('items') for c in children_meta):
      return new_fragment  # ← outer wrapper 유실 위험

변경 후:
  if not any(c.get('anchors') or c.get('items') for c in children_meta):
      # Step 1, 2는 건너뛰지만 Step 3(outer wrapper template)은 적용
      return _apply_outer_wrapper_template(new_fragment, sidecar_block)
```

`_apply_outer_wrapper_template()`은 기존 Step 3 로직(`sidecar_block.xhtml_fragment`를 template으로 사용, body children만 교체)을 별도 함수로 추출한 것이다. 이렇게 하면 `ac:macro-id`, `ac:schema-version` 등 Confluence 메타 속성이 보존된다.

**⚠ Axis 1 구현 시 금지 사항 (§11.3 참조):**

① clean container 분기에 Step 1/2(stored child fragment 재사용, inline markup 재적용)를 추가하지 않는다. `not has_anchors` 분기는 `_apply_outer_wrapper_template(new_fragment, sidecar_block)` 한 줄로 끝나야 한다.

② `rewrite_on_stored_template()` 등 plain text를 HTML fragment에 embed하는 함수에는 `html.escape()` 적용을 확인한다.

③ fallback을 제거하기 전 해당 fallback이 처리하던 케이스 목록을 작성하고, 각 케이스의 대체 경로가 확보됐는지 확인한다. 대체 경로가 없는 케이스에서 `continue` 처리하지 않는다.

**Axis 1 완료 기준:**
- [ ] `test_reverse_sync_reconstruction_goldens.py` 12개 통과 유지
- [ ] `expected_status: pass` 31개 유지
- [ ] `pytest tests/` 전체 통과
- [ ] `transfer_text_changes()` 호출이 `patch_builder.py`에서 0개

**Axis 1 완료 시 삭제 대상:**
- `_flush_containing_changes()` — 호출 지점 없어지면
- `bin/reverse_sync/text_transfer.py`
- `tests/test_reverse_sync_text_transfer.py`
- `tests/test_reverse_sync_patch_builder.py` 중 text_transfer 기반 테스트
- `tests/test_reverse_sync_reconstruct_container.py`의 `test_clean_callout_still_uses_text_transfer` — clean callout이 replace_fragment로 전환되면 수정 필요

---

#### Phase 5 Axis 2: CLI `record_mapping()` 책임 캡슐화

**목표:** `reverse_sync_cli.py`가 `record_mapping()`을 직접 호출하고 `build_patches()`에 전달하는 책임을 `build_patches()` 내부로 캡슐화한다. 이후 CLI는 `page_xhtml`만 넘기면 된다. 단, `build_sidecar()` 내부의 별도 `record_mapping()` 호출은 이 단계에서 건드리지 않으므로 runtime 호출 횟수는 2회로 유지된다. runtime 중복 제거는 SidecarBlock 스키마 확장 이후 별도 단계에서 진행한다.

**현재 흐름:**

```python
# reverse_sync_cli.py
original_mappings = record_mapping(xhtml)    # CLI 직접 호출 (캡슐화 대상)
roundtrip_sidecar = build_sidecar(xhtml, ...)  # 내부에서도 record_mapping 호출
patches = build_patches(
    ..., original_mappings, ..., xpath_to_mapping, ...
)
```

**데이터 소스 결정:**

현재 `build_patches()`는 `BlockMapping`의 `block_id`, `xhtml_plain_text`, `children`, `xhtml_element_index` 필드에 광범위하게 의존한다(child_to_parent 맵, lost_info 분배, text prefix fallback, containing 분기 등). `SidecarBlock`에는 이 필드들이 없으므로 `roundtrip_sidecar`만으로는 `mappings`/`xpath_to_mapping`을 복원할 수 없다.

따라서 Axis 2의 데이터 소스는 **`build_patches()` 내부에서 `record_mapping()`을 직접 호출**하는 것으로 확정한다. 이로 인해 `build_sidecar()`와 `build_patches()` 양쪽에서 `record_mapping()`이 각각 호출되어 runtime 중복은 남지만, Axis 2의 목표는 runtime 중복 제거가 아니라 **CLI의 배선(wiring) 책임을 `build_patches()` 내부로 캡슐화**하는 것이다. runtime 중복 제거는 SidecarBlock이 BlockMapping 필드를 흡수한 후 별도 단계에서 진행한다.

**전환 순서:**

1. `build_patches()`에 `page_xhtml` 파라미터를 추가하고, 내부에서 `record_mapping(page_xhtml)`을 호출하여 `mappings`와 `xpath_to_mapping`을 자체 구축한다
2. `reverse_sync_cli.py`에서 `record_mapping()` 직접 호출 및 `build_patches()`로의 `mappings`/`xpath_to_mapping` 전달을 제거한다
3. `SidecarEntry` import를 `patch_builder.py`에서 제거 (`_build_mdx_to_sidecar_from_v3()` 출력을 `SidecarBlock` 직접 참조로 교체)

> **주의:** `build_patches()`의 `mappings`와 `xpath_to_mapping`은 내부 변수로 남되, 외부 시그니처에서는 제거한다. 단, SidecarBlock이 BlockMapping 필드를 흡수하여 `record_mapping()` 호출 자체를 제거하는 것은 Axis 2 범위 밖이며, 별도 단계로 진행한다.

**`mapping.original.yaml` artifact 처분 방침:**

현재 CLI는 `record_mapping()` 결과를 패치 입력뿐 아니라 `reverse-sync.mapping.original.yaml` 디버깅 artifact 저장에도 사용한다(`reverse_sync_cli.py:344-351`). `record_mapping()` 직접 호출을 제거하면 이 artifact 생성 경로도 함께 사라진다.

처분 방침: **`build_patches()`의 반환 타입을 확장하여 내부에서 생성한 `mappings`를 부산물로 함께 반환한다.** CLI는 이 반환값으로 artifact를 계속 저장한다. 이 artifact는 패치 결과 디버깅과 `mapping.patched.yaml`과의 비교 검증에 사용되므로 당분간 유지한다. artifact 완전 폐기는 reverse-sync 디버깅 워크플로우 재정비 시점에 별도로 결정한다.

**Axis 2 완료 기준:**
- [ ] `reverse_sync_cli.py`에 `record_mapping()` 직접 호출 없음
- [ ] `SidecarEntry` import가 `patch_builder.py`에서 제거
- [ ] `pytest tests/` 전체 통과

---

#### Phase 5 Axis 3: legacy 모듈 삭제 및 테스트 정리

Axis 1, 2 완료 후 실행한다. 상세 삭제 범위는 `docs/plans/2026-03-15-reverse-sync-reconstruction-cleanup-scope.md` 참조.

**삭제 대상:**

| 파일 | 삭제 조건 |
|------|-----------|
| `bin/reverse_sync/text_transfer.py` | Axis 1 완료 후 |
| `bin/reverse_sync/table_patcher.py` | `is_markdown_table()` → `patch_builder.py` 이동 후 |
| `tests/test_reverse_sync_text_transfer.py` | Axis 1 완료 후 |
| `tests/test_reverse_sync_patch_builder.py` 일부 | text_transfer/containing 기반 테스트 |

> `list_patcher.py`, `inline_detector.py`는 PR #928에서 이미 삭제됐다.

---

## 7. 테스트 계획

### 7.1 반드시 유지할 기존 green 게이트

- `tests/test_reverse_sync_xhtml_normalizer.py`
- `tests/test_reverse_sync_list_tree.py`
- `tests/test_reverse_sync_sidecar_v3.py`
- `tests/test_reverse_sync_rehydrator.py` — unchanged testcase에 대한 splice byte-equal 검증 포함

### 7.2 Phase 5에서 유지/확장할 테스트

- `tests/test_reverse_sync_reconstruction_goldens.py` — 12개 green 유지
- `tests/test_reverse_sync_reconstruct_paragraph.py`
- `tests/test_reverse_sync_reconstructors.py`

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

---

## 8. legacy 코드 정리 기준

상세 삭제 대상과 범위는 `docs/plans/2026-03-15-reverse-sync-reconstruction-cleanup-scope.md`에 별도로 정리한다.

**이미 제거된 파일:**

- `bin/reverse_sync/list_patcher.py` (PR #928)
- `bin/reverse_sync/inline_detector.py` (PR #928)

**새 경로가 기본이 되기 전에는 제거하지 않는 파일:**

- `text_transfer.py` — `patch_builder.py` 내 3개 호출 지점 전부 제거 후 삭제 (Axis 1 완료 조건)
- `table_patcher.py` — `is_markdown_table()` 이동 후 제거
- `patch_builder.py` 내부 `_flush_containing_changes()` — text_transfer 호출 지점 ① 제거 후 삭제
- `xhtml_patcher.py`의 text-only modify 경로 — Axis 1 이후 검토

**정리 전환 조건 (이미 충족):**

1. ✅ changed golden 16개가 새 reconstruction 경로로 green
2. ✅ `expected_status: pass` 31개 회귀 케이스 유지
3. ✅ unsupported 구조는 silent corruption 없이 skip (patch 미생성) — 명시적 fail로의 전환은 Axis 1 내 별도 작업
4. ⬜ `mapping.yaml` 없이도 sidecar v3 기반 runtime planning 가능 — Axis 2 이후 별도 단계

---

## 9. 최종 승인 기준

이번 재구성 작업은 아래를 만족해야 완료로 본다.

1. modified block 기본 경로가 whole-fragment reconstruction으로 전환된다.
2. paragraph/list anchor 재주입이 plain-text 좌표계 기준으로 구현된다.
3. test oracle이 `mapping.yaml`이 아니라 `expected.roundtrip.json`, `page.xhtml`, `expected.reverse-sync.patched.xhtml`로 고정된다.
4. `RoundtripSidecar v3`의 `reconstruction` 필드가 실제 runtime metadata를 담는다.
5. `build_sidecar_identity_index()` / `find_sidecar_block_by_identity()` 기준 identity가 planner에 통합되고, duplicate content에서도 안정적으로 동작한다.
6. unsupported 구조에서 silent corruption 없이 fail-closed가 유지된다.

---

## 10. 판단

### 2026-03-19 (4차 갱신) 기준 상태

PR #937 머지로 `main`은 Phase 0–4를 모두 흡수했고, testcase `original.mdx` 재생성까지 완료됐다. PR #942에서 Phase 5 Axis 1의 routing 변경(anchor 있는 container → 'direct')이 완료됐다. **남은 핵심 작업은 Phase 5 내 text_transfer 제거 3개 지점 완결이다.**

**Phase 5 Axis별 진행 상태:**

1. **Axis 1 — text_transfer 호출 지점 전수 제거**: routing 변경 완료(PR #942). 남은 작업: clean container fallback 제거, paired delete+add fallback 대체, ac:link/ri:attachment fallback 대체. `text_transfer.py` 삭제는 3개 지점 전부 해소 후.

2. **Axis 2 — CLI `record_mapping()` 책임 캡슐화**: CLI의 직접 호출과 배선 책임을 `build_patches()` 내부로 이전, `SidecarEntry` import 제거. runtime 중복 제거(`build_sidecar()`와의 이중 호출 해소)는 SidecarBlock 스키마 확장 후 별도 진행.

3. **Axis 3 — 잔여 legacy 삭제**: Axis 1, 2 완료 후 `table_patcher.py`, 관련 테스트 정리.

**현재 `expected_status: fail` 11개의 failure_type 분류:**

| failure_type | 건수 | 설명 |
|---|---|---|
| ft=13 | 4 | Bold 경계/공백 문제 (text-transfer heuristic 한계) |
| ft=14 | 2 | 테이블 전체 소실 (표 재구성 미지원) |
| ft=17 | 2 | 리스트 항목 [li] 태그 노출, 번호 오류 |
| ft=11 | 1 | 교정 내용 원복 (mapping 오탐) |
| ft=4 | 1 | 빈 Bold 태그 삽입 (emitter 버그) |
| ft=16 | 1 | 리스트 항목 내 코드 블록 인라인 병합 |

이 중 ft=13의 일부는 Phase 5에서 legacy text-transfer를 제거하고 reconstruction 경로로 전환하면 자연히 개선되거나 명확한 fail-closed 처리로 정리될 것으로 예상된다.

---

## 11. 구현 규율 — Phase 5 반복 Regression 방지

PR #942 리뷰에서 3개의 Regression이 발견됐다. 공통 원인을 분석하여 이후 PR에서 동일한 실수가 반복되지 않도록 원칙과 게이트를 정립한다.

### 11.1 발견된 Regression 패턴

#### R-1 — clean container에 Step 1/2 실행 (구조 변경의 silent 무시)

**현상:** `reconstruct_container_fragment()`에 `_root_tags_differ()` 체크를 추가하여, emitted child의 root tag가 stored child와 다르면 stored fragment를 그대로 사용했다. 결과적으로 paragraph → list 같은 구조 변경이 조용히 버려졌다.

**설계 위반:** 이 문서 §6 Axis 1에 clean container는 "Step 1, 2는 건너뛰고 Step 3(outer wrapper template)만 적용"이라고 명시되어 있다. 구현은 명세에 없는 Step 1을 추가했다.

**원칙:** clean container(`has_anchors == False`)의 body children은 `new_fragment`에서 추출한 emitted children을 그대로 사용한다. stored child fragment를 재사용하는 로직(Step 1, 2)은 anchor/item이 있는 container 전용이며, clean container에 적용해서는 안 된다.

**명세 재확인 (§6 Axis 1):**

```
clean container 처리 (변경 후):
  if not has_anchors:
      # Step 1, 2 건너뜀 — new_fragment의 emitted children 그대로 사용
      # Step 3만 적용: outer wrapper 속성(ac:macro-id 등) 보존
      return _apply_outer_wrapper_template(new_fragment, sidecar_block)
```

---

#### R-2 — plain text를 HTML fragment에 직접 embed (HTML injection)

**현상:** `rewrite_on_stored_template(template_fragment, new_plain)`에서 `f'<p>{new_plain}</p>'`로 래핑 시 HTML 이스케이프를 적용하지 않았다. `new_plain`에 `<`, `>`, `&`가 포함되면 BeautifulSoup이 HTML 태그로 파싱하여 내용이 손실된다.

**재현:** `rewrite_on_stored_template('<p><ac:link>...</ac:link></p>', 'a < b & c')` → `<b>` 이후가 태그로 해석되어 일부 소실.

**원칙:** plain text를 HTML 문자열 안에 `f-string` 또는 `+` 연산으로 직접 삽입할 때는 반드시 `html.escape(text)`를 적용한다. `normalize_mdx_to_plain()`의 반환값도 HTML-safe가 아니다.

```python
# ✅ 올바른 사용
import html
return _rewrite_paragraph_on_template(template_fragment, f'<p>{html.escape(new_plain)}</p>')

# ❌ 위험
return _rewrite_paragraph_on_template(template_fragment, f'<p>{new_plain}</p>')
```

---

#### R-3 — fallback 제거 전 coverage 미확보 (silent skip regression)

**현상:** preserved anchor list와 containing + sidecar 없는 케이스를 `continue`(silent skip)로 처리했다. 이전에 `transfer_text_changes()`가 처리하던 케이스가 아무 패치도 생성하지 않게 됐다.

**설계 위반:** §3.5 "지원 범위 밖 구조는 명시적으로 fail한다". 또한 기존 동작하던 케이스를 먼저 새 경로로 커버하지 않고 fallback만 제거했다.

**원칙:** `transfer_text_changes()` 또는 다른 fallback을 제거할 때, 해당 경로가 처리하던 **모든 sub-case**에 대한 대체 경로가 먼저 확보되어야 한다. 대체 경로가 없는 sub-case가 하나라도 있으면 fallback을 유지한다.

```
fallback 제거 체크리스트:
  1. 이 fallback이 처리하던 케이스를 열거한다
  2. 각 케이스에 대한 새 경로가 구현되었는가?
  3. 새 경로가 없는 케이스 → fallback 유지 또는 명시적 fail로 대체
  4. 테스트 기대값이 "0 patches"로 바뀌는 케이스 전수 검토
```

---

### 11.2 구현 게이트

Phase 5 각 PR 구현 시 아래 게이트를 통과해야 한다.

#### Gate 1: 설계 명세 선행

구현하려는 로직이 이 문서에 명시되어 있는가?

- 명시된 pseudocode가 있으면: 한 줄씩 대조하여 추가 로직이 없음을 확인한다.
- 명시되지 않은 로직을 추가할 때: 코드를 먼저 작성하지 않고 이 문서를 먼저 업데이트한다.

> **R-1의 교훈:** `_root_tags_differ()` 추가는 설계 명세에 없었다. 설계를 먼저 업데이트했다면 "clean container는 Step 1/2를 건너뜀" 제약이 확인됐을 것이다.

#### Gate 2: silent skip 금지

`continue` 또는 조용한 `return`으로 변경을 버리는 경우, 아래 중 하나가 충족되어야 한다:

- (a) 해당 케이스가 "처리 안 함" 목록(`expected_status: fail`)에 기재되어 있다.
- (b) 이전에 이 케이스를 처리하던 경로가 없었다(신규 edge case).

이전 동작에서 패치가 생성되던 케이스가 0 patches로 바뀌면 반드시 그 이유를 PR description에 명시한다.

#### Gate 3: HTML embed 이스케이프

plain text를 HTML fragment에 embed할 때 `html.escape()` 적용 여부를 PR diff에서 확인한다. 적용하지 않은 라인이 있으면 merge 전 수정한다.

#### Gate 4: 테스트 기대값 변화 검토

golden test expected 파일 또는 단위 테스트 기대값이 변경되는 경우:

- **기대값이 "없음" 또는 "0 patches"로 바뀐 경우**: 이전에 통과하던 케이스가 silent skip이 된 것이 아닌지 확인한다.
- **기대값이 다른 내용으로 바뀐 경우**: 이전 기대값과 새 기대값 모두 올바른지 검토한다. "테스트를 통과시키기 위해" 기대값을 바꾸는 것은 regression을 숨기는 행위다.

#### Gate 5: fallback 제거 범위 확인

`transfer_text_changes()` 호출을 제거하기 전, 제거 대상 경로가 처리하는 케이스 목록을 작성하고 각 케이스의 대체 경로를 명시한다. 이 목록이 PR description에 포함되어야 한다.

---

### 11.3 clean container 구현 스펙 (Axis 1 구현자용)

R-1의 재발을 막기 위해 `reconstruct_container_fragment()` clean container 분기의 올바른 구현을 명시한다.

**허용되는 변경:**

```python
# reconstructors.py — reconstruct_container_fragment() 내부
if not has_anchors:
    # ✅ Step 3만: outer wrapper 속성 보존, body는 new_fragment의 emitted children 그대로
    return _apply_outer_wrapper_template(new_fragment, sidecar_block)
```

**허용되지 않는 변경:**

```python
# ❌ stored_fragment 재사용 — clean container에서 구조 변경을 버림
if _root_tags_differ(stored_fragment, child_frag):
    child_frag = stored_fragment

# ❌ inline markup 재적용 — clean container는 emitted result를 신뢰함
elif _has_inline_markup(stored_fragment):
    child_frag = _rewrite_paragraph_on_template(stored_fragment, child_frag)
```

**근거:** clean container는 anchor나 Confluence 전용 인라인 요소가 없으므로 `emit_block()`의 결과를 신뢰한다. stored fragment를 참조하면 사용자가 MDX에서 의도적으로 수행한 구조 변경(단락 → 리스트 등)이 조용히 버려진다.
