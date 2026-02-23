# Reverse-Sync Inline Format Patch 구현 계획

**Goal:** Reverse-sync에서 MDX의 inline format 변경(backtick, bold, italic, link)을 감지하여 XHTML에 `<code>`, `<strong>` 등의 태그를 올바르게 반영한다.

**Architecture:** `patch_builder.py`에 inline format 변경 감지 함수를 추가하고, 변경이 감지되면 기존 text patch 대신 `new_inner_xhtml` 패치를 생성한다. `xhtml_patcher.py`는 이미 `new_inner_xhtml` 패치를 `_replace_inner_html()`로 처리하므로 변경 불필요.

**Tech Stack:** Python 3, pytest, BeautifulSoup4, regex

**Design doc:** [`2026-02-23-inline-format-patch-design.md`](./2026-02-23-inline-format-patch-design.md)

---

### Task 1: `_extract_inline_markers()` 및 `has_inline_format_change()` 유닛 테스트 + 구현

MDX content에서 inline 포맷 마커(code, bold, italic, link)를 추출하는 함수와,
old/new MDX의 마커를 비교하여 inline 포맷 변경 여부를 판정하는 함수를 TDD로 구현한다.

1. 테스트 클래스 `TestExtractInlineMarkers`(7개)와 `TestHasInlineFormatChange`(8개)를 작성하여 실패를 확인한다.
2. `_extract_inline_markers()`, `_strip_positions()`, `has_inline_format_change()`를 구현한다.
3. 전체 테스트 통과를 확인한 후 커밋한다.

**구현 결과:**
- 구현: [`bin/reverse_sync/patch_builder.py:20-51`](../bin/reverse_sync/patch_builder.py#L20-L51)
- 테스트: [`tests/test_reverse_sync_patch_builder.py:932-1023`](../tests/test_reverse_sync_patch_builder.py#L932-L1023)
- 커밋: `e7fb220d`

**설계 노트:** 원래 계획에서는 `has_inline_format_change()`가 `_extract_inline_markers()`의 결과를 직접 비교했으나,
주변 텍스트 변경 시 마커 위치가 이동하여 false positive가 발생했다.
`_strip_positions()` 헬퍼를 추가하여 type+content만 비교하도록 개선했다.

---

### Task 2: `build_patches()` direct 전략에 inline format 분기 추가

`build_patches()`의 direct 전략에서, `has_inline_format_change()`로 inline 포맷 변경을 감지하면
`mdx_block_to_inner_xhtml()`로 XHTML inner HTML을 생성하여 `new_inner_xhtml` 패치를 발행한다.
변경이 없으면 기존 `new_plain_text` text patch 로직을 유지한다.

1. `TestBuildPatches`에 `test_direct_inline_code_added_generates_inner_xhtml`과 `test_direct_text_only_change_uses_plain_text_patch`를 추가하여 실패를 확인한다.
2. `mdx_block_to_inner_xhtml` import를 추가하고, direct 전략에 `has_inline_format_change()` 분기를 삽입한다.
3. paragraph, heading 등 direct 전략을 사용하는 모든 블록 유형에 자동 적용된다.

**구현 결과:**
- 구현: [`bin/reverse_sync/patch_builder.py:266-288`](../bin/reverse_sync/patch_builder.py#L266-L288)
- 테스트: [`tests/test_reverse_sync_patch_builder.py:457-494`](../tests/test_reverse_sync_patch_builder.py#L457-L494)
- 커밋: `73a69afe`

---

### Task 3: `build_list_item_patches()`에 inline format 분기 추가

`build_list_item_patches()`의 child 매칭 성공 분기에서, 리스트 항목의 inline 포맷 변경을 감지하면
리스트 마커를 제거한 후 `convert_inline()`으로 XHTML 변환하여 `new_inner_xhtml` 패치를 발행한다.

1. `TestBuildListItemPatches`에 `test_list_item_inline_code_added_generates_inner_xhtml`을 추가한다.
2. `convert_inline` import를 추가하고, child 매칭 분기에 `has_inline_format_change(old_item, new_item)` 검사를 삽입한다.
3. 리스트 항목에서는 `mdx_block_to_inner_xhtml()` 대신 `convert_inline()`을 사용한다 (각 항목이 단일 인라인 콘텐츠이므로).

**구현 결과:**
- 구현: [`bin/reverse_sync/patch_builder.py:491-524`](../bin/reverse_sync/patch_builder.py#L491-L524)
- 테스트: [`tests/test_reverse_sync_patch_builder.py:635-657`](../tests/test_reverse_sync_patch_builder.py#L635-L657)
- 커밋: `8bcbd4ef`

---

### Task 4: containing 전략 text patch 유지 확인

containing 전략은 여러 MDX 블록이 하나의 XHTML 블록에 매핑되는 경우이다.
이 경우 개별 변경의 inline format만 바꿀 수 없으므로, 기존 text patch 방식을 유지한다.
`_flush_containing_changes()`는 변경하지 않고, 동작을 확인하는 테스트만 추가한다.

**구현 결과:**
- 테스트: [`tests/test_reverse_sync_patch_builder.py:822-832`](../tests/test_reverse_sync_patch_builder.py#L822-L832)
- 커밋: `23500063`

---

### Task 5: 전체 회귀 테스트 + 실제 verify 검증

코드 변경 없이 검증만 수행한다.

1. `python -m pytest tests/test_reverse_sync_patch_builder.py` — 91개 PASS
2. `python -m pytest tests/test_reverse_sync_mdx_to_xhtml_inline.py tests/test_reverse_sync_xhtml_patcher.py` — 61개 PASS
3. `python bin/reverse_sync_cli.py verify --branch=split/ko-proofread-20260221-overview` — 4/4 PASS, backtick diff 해결 확인

---

### Task 6: heading/bold 블록 유형 테스트 보강

heading에서 inline code 추가, paragraph에서 bold 추가 시 `new_inner_xhtml` 패치가
올바르게 생성되는지 확인하는 테스트를 추가한다.
Task 2의 구현이 block type에 무관하게 동작하므로, 별도 구현 변경 없이 테스트만 추가한다.

**구현 결과:**
- 테스트: [`tests/test_reverse_sync_patch_builder.py:516-559`](../tests/test_reverse_sync_patch_builder.py#L516-L559)
- 커밋: `d24ad001`
