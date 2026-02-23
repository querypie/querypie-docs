# Reverse-Sync Inline Format Patch 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reverse-sync에서 MDX의 inline format 변경(backtick, bold, italic, link)을 감지하여 XHTML에 `<code>`, `<strong>` 등의 태그를 올바르게 반영한다.

**Architecture:** `patch_builder.py`에 inline format 변경 감지 함수를 추가하고, 변경이 감지되면 기존 text patch 대신 `new_inner_xhtml` 패치를 생성한다. `xhtml_patcher.py`는 이미 `new_inner_xhtml` 패치를 `_replace_inner_html()`로 처리하므로 변경 불필요.

**Tech Stack:** Python 3, pytest, BeautifulSoup4, regex

**Design doc:** `docs/plans/2026-02-23-inline-format-patch-design.md`

---

### Task 1: `_extract_inline_markers()` 및 `has_inline_format_change()` 유닛 테스트 작성

**Files:**
- Modify: `tests/test_reverse_sync_patch_builder.py`
- Modify: `bin/reverse_sync/patch_builder.py` (import만 추가)

**Step 1: 실패하는 테스트 작성**

`tests/test_reverse_sync_patch_builder.py` 파일 끝에 테스트 클래스를 추가한다.
import 섹션에 `has_inline_format_change`, `_extract_inline_markers`를 추가한다.

```python
# import 섹션에 추가:
from reverse_sync.patch_builder import (
    # ... 기존 import ...
    has_inline_format_change,
    _extract_inline_markers,
)

# 파일 끝에 추가:
class TestExtractInlineMarkers:
    """_extract_inline_markers()의 inline 포맷 마커 추출을 테스트한다."""

    def test_no_markers(self):
        assert _extract_inline_markers('plain text only') == []

    def test_code_span(self):
        markers = _extract_inline_markers('use `kubectl` command')
        assert len(markers) == 1
        assert markers[0][0] == 'code'
        assert markers[0][2] == 'kubectl'

    def test_bold(self):
        markers = _extract_inline_markers('this is **important** text')
        assert len(markers) == 1
        assert markers[0][0] == 'bold'
        assert markers[0][2] == 'important'

    def test_italic(self):
        markers = _extract_inline_markers('this is *emphasized* text')
        assert len(markers) == 1
        assert markers[0][0] == 'italic'
        assert markers[0][2] == 'emphasized'

    def test_link(self):
        markers = _extract_inline_markers('see [docs](https://example.com)')
        assert len(markers) == 1
        assert markers[0][0] == 'link'
        assert markers[0][2] == 'docs'
        assert markers[0][3] == 'https://example.com'

    def test_multiple_markers_sorted_by_position(self):
        markers = _extract_inline_markers('**bold** and `code`')
        assert len(markers) == 2
        assert markers[0][0] == 'bold'
        assert markers[1][0] == 'code'

    def test_code_inside_bold_not_double_counted(self):
        """bold 내부의 backtick은 code로만 감지된다."""
        markers = _extract_inline_markers('use `code` here')
        code_markers = [m for m in markers if m[0] == 'code']
        assert len(code_markers) == 1


class TestHasInlineFormatChange:
    """has_inline_format_change()의 inline 변경 감지를 테스트한다."""

    def test_no_change_plain_text(self):
        assert has_inline_format_change('hello world', 'hello earth') is False

    def test_code_added(self):
        assert has_inline_format_change(
            'use https://example.com/ URL',
            'use `https://example.com/` URL',
        ) is True

    def test_code_removed(self):
        assert has_inline_format_change(
            'use `kubectl` command',
            'use kubectl command',
        ) is True

    def test_code_content_changed(self):
        assert has_inline_format_change(
            'use `old_cmd` here',
            'use `new_cmd` here',
        ) is True

    def test_bold_added(self):
        assert has_inline_format_change(
            'important note',
            '**important** note',
        ) is True

    def test_link_changed(self):
        assert has_inline_format_change(
            'see [docs](https://old.com)',
            'see [docs](https://new.com)',
        ) is True

    def test_same_markers_no_change(self):
        assert has_inline_format_change(
            '**bold** and `code`',
            '**bold** and `code`',
        ) is False

    def test_text_only_change_with_existing_markers(self):
        """마커 외부의 텍스트만 변경 → inline 변경 아님."""
        assert has_inline_format_change(
            '앞문장 `code` 뒷문장',
            '변경된 앞문장 `code` 변경된 뒷문장',
        ) is False
```

**Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py::TestExtractInlineMarkers -v`
Expected: FAIL (ImportError — `has_inline_format_change`, `_extract_inline_markers` 미정의)

**Step 3: 최소 구현 작성**

`bin/reverse_sync/patch_builder.py` 파일 상단(import 이후, `NON_CONTENT_TYPES` 앞)에 추가:

```python
# ── Inline format 변경 감지 ──

_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_INLINE_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_INLINE_ITALIC_RE = re.compile(r'(?<!\*)\*([^*]+)\*(?!\*)')
_INLINE_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def _extract_inline_markers(content: str) -> list:
    """MDX content에서 inline 포맷 마커를 위치순으로 추출한다."""
    markers = []
    for m in _INLINE_CODE_RE.finditer(content):
        markers.append(('code', m.start(), m.group(1)))
    for m in _INLINE_BOLD_RE.finditer(content):
        markers.append(('bold', m.start(), m.group(1)))
    for m in _INLINE_ITALIC_RE.finditer(content):
        markers.append(('italic', m.start(), m.group(1)))
    for m in _INLINE_LINK_RE.finditer(content):
        markers.append(('link', m.start(), m.group(1), m.group(2)))
    return sorted(markers, key=lambda x: x[1])


def has_inline_format_change(old_content: str, new_content: str) -> bool:
    """old/new MDX 콘텐츠의 inline 포맷 마커가 다른지 감지한다."""
    return _extract_inline_markers(old_content) != _extract_inline_markers(new_content)
```

**Step 4: 테스트 실행 — 통과 확인**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py::TestExtractInlineMarkers tests/test_reverse_sync_patch_builder.py::TestHasInlineFormatChange -v`
Expected: ALL PASS

**Step 5: 커밋**

```bash
git add bin/reverse_sync/patch_builder.py tests/test_reverse_sync_patch_builder.py
git commit -m "feat(confluence-mdx): inline format 변경 감지 함수 추가"
```

---

### Task 2: `build_patches()` direct 전략에 inline format 분기 추가

**Files:**
- Modify: `bin/reverse_sync/patch_builder.py:231-241` (direct 전략)
- Modify: `bin/reverse_sync/patch_builder.py:16` (import 추가)
- Modify: `tests/test_reverse_sync_patch_builder.py`

**Step 1: 실패하는 테스트 작성**

`tests/test_reverse_sync_patch_builder.py`의 `TestBuildPatches` 클래스에 테스트를 추가한다.

```python
class TestBuildPatches:
    # ... 기존 테스트 유지 ...

    # Inline format 변경 → new_inner_xhtml 패치 생성
    def test_direct_inline_code_added_generates_inner_xhtml(self):
        """paragraph에서 backtick이 추가되면 new_inner_xhtml 패치를 생성한다."""
        m1 = _make_mapping('m1', 'QueryPie는 https://example.com/과 같은 URL', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(
            0,
            'QueryPie는 https://example.com/과 같은 URL',
            'QueryPie는 `https://example.com/`과 같은 URL',
        )
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert 'new_inner_xhtml' in patches[0]
        assert '<code>https://example.com/</code>' in patches[0]['new_inner_xhtml']
        assert 'new_plain_text' not in patches[0]

    def test_direct_text_only_change_uses_plain_text_patch(self):
        """inline format 변경 없이 텍스트만 바뀌면 기존 text patch를 사용한다."""
        m1 = _make_mapping('m1', 'hello world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'hello world', 'hello earth')
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert 'new_plain_text' in patches[0]
        assert 'new_inner_xhtml' not in patches[0]
```

**Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py::TestBuildPatches::test_direct_inline_code_added_generates_inner_xhtml -v`
Expected: FAIL (`new_inner_xhtml` 키가 없음)

**Step 3: 구현**

`bin/reverse_sync/patch_builder.py`의 import에 `mdx_block_to_inner_xhtml`을 추가한다:

```python
# 기존:
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_xhtml_element

# 변경:
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_xhtml_element, mdx_block_to_inner_xhtml
```

`build_patches()`의 direct 전략 부분(L231-241)을 수정한다:

```python
        # strategy == 'direct'
        _mark_used(mapping.block_id, mapping)

        # inline 포맷 변경 감지 → new_inner_xhtml 패치
        if has_inline_format_change(
                change.old_block.content, change.new_block.content):
            new_inner = mdx_block_to_inner_xhtml(
                change.new_block.content, change.new_block.type)
            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': mapping.xhtml_plain_text,
                'new_inner_xhtml': new_inner,
            })
        else:
            if collapse_ws(old_plain) != collapse_ws(mapping.xhtml_plain_text):
                new_plain = transfer_text_changes(
                    old_plain, new_plain, mapping.xhtml_plain_text)

            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': mapping.xhtml_plain_text,
                'new_plain_text': new_plain,
            })
```

**Step 4: 테스트 실행 — 통과 확인**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py::TestBuildPatches -v`
Expected: ALL PASS (기존 테스트 + 새 테스트 모두)

**Step 5: 커밋**

```bash
git add bin/reverse_sync/patch_builder.py tests/test_reverse_sync_patch_builder.py
git commit -m "feat(confluence-mdx): direct 전략에 inline format 변경 시 new_inner_xhtml 패치 생성 추가"
```

---

### Task 3: `build_list_item_patches()` 에 inline format 분기 추가

**Files:**
- Modify: `bin/reverse_sync/patch_builder.py:444-466` (list item child 매칭 패치)
- Modify: `tests/test_reverse_sync_patch_builder.py`

**Step 1: 실패하는 테스트 작성**

`tests/test_reverse_sync_patch_builder.py`의 `TestBuildListItemPatches` 클래스에 추가:

```python
class TestBuildListItemPatches:
    # ... 기존 테스트 유지 ...

    def test_list_item_inline_code_added_generates_inner_xhtml(self):
        """리스트 항목에서 backtick 추가 시 new_inner_xhtml 패치를 생성한다."""
        child = _make_mapping('c1', 'use kubectl command', xpath='ul[1]/li[1]/p[1]')
        parent = _make_mapping('p1', 'use kubectl command', xpath='ul[1]',
                               type_='list', children=['c1'])
        mappings = [parent, child]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        id_to_mapping = {m.block_id: m for m in mappings}

        change = _make_change(
            0,
            '* use kubectl command\n',
            '* use `kubectl` command\n',
            type_='list',
        )
        mdx_to_sidecar = {0: _make_sidecar('ul[1]', [0])}

        patches = build_list_item_patches(
            change, mappings, set(),
            mdx_to_sidecar, xpath_to_mapping, id_to_mapping)

        assert len(patches) == 1
        assert 'new_inner_xhtml' in patches[0]
        assert '<code>kubectl</code>' in patches[0]['new_inner_xhtml']
```

**Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py::TestBuildListItemPatches::test_list_item_inline_code_added_generates_inner_xhtml -v`
Expected: FAIL

**Step 3: 구현**

`bin/reverse_sync/patch_builder.py`에 import 추가:

```python
from mdx_to_storage.inline import convert_inline
```

`build_list_item_patches()`의 child 매칭 성공 분기(L444-466)를 수정한다:

```python
        if mapping is not None:
            # child 매칭: 패치 생성
            if used_ids is not None:
                used_ids.add(mapping.block_id)

            # inline 포맷 변경 감지 → new_inner_xhtml 패치
            if has_inline_format_change(old_item, new_item):
                new_item_text = re.sub(r'^[-*+]\s+', '', new_item.strip())
                new_item_text = re.sub(r'^\d+\.\s+', '', new_item_text)
                new_inner = convert_inline(new_item_text)
                patches.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'old_plain_text': mapping.xhtml_plain_text,
                    'new_inner_xhtml': new_inner,
                })
            else:
                new_plain = normalize_mdx_to_plain(new_item, 'list')

                xhtml_text = mapping.xhtml_plain_text
                prefix = extract_list_marker_prefix(xhtml_text)
                if prefix and collapse_ws(old_plain) != collapse_ws(xhtml_text):
                    xhtml_body = xhtml_text[len(prefix):]
                    if collapse_ws(old_plain) != collapse_ws(xhtml_body):
                        new_plain = transfer_text_changes(
                            old_plain, new_plain, xhtml_body)
                    new_plain = prefix + new_plain
                elif collapse_ws(old_plain) != collapse_ws(xhtml_text):
                    new_plain = transfer_text_changes(
                        old_plain, new_plain, xhtml_text)

                patches.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'old_plain_text': xhtml_text,
                    'new_plain_text': new_plain,
                })
```

**Step 4: 테스트 실행 — 통과 확인**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py::TestBuildListItemPatches -v`
Expected: ALL PASS

**Step 5: 커밋**

```bash
git add bin/reverse_sync/patch_builder.py tests/test_reverse_sync_patch_builder.py
git commit -m "feat(confluence-mdx): list item 전략에 inline format 변경 시 new_inner_xhtml 패치 생성 추가"
```

---

### Task 4: `_flush_containing_changes()` 에 inline format 분기 추가

**Files:**
- Modify: `bin/reverse_sync/patch_builder.py:57-79` (`_flush_containing_changes`)
- Modify: `bin/reverse_sync/patch_builder.py:224-229` (containing 전략에서 raw content 전달)
- Modify: `tests/test_reverse_sync_patch_builder.py`

**Step 1: 실패하는 테스트 작성**

`tests/test_reverse_sync_patch_builder.py`의 `TestFlushContainingChanges` 클래스에 추가:

```python
class TestFlushContainingChanges:
    # ... 기존 테스트 유지 ...

    def test_inline_format_change_generates_inner_xhtml(self):
        """containing block에서 inline 변경 감지 시 new_inner_xhtml 패치를 생성한다."""
        m = _make_mapping('m1', 'use command and url', xpath='p[1]')
        containing_changes = {
            'm1': (m, [
                ('use command and url', 'use `command` and url'),
            ]),
        }
        # raw_contents를 전달하여 inline 변경 감지
        raw_contents = {
            'm1': [
                ('use command and url', 'use `command` and url'),
            ],
        }
        patches = _flush_containing_changes(
            containing_changes, raw_contents=raw_contents)
        assert len(patches) == 1
        assert 'new_inner_xhtml' in patches[0]
        assert '<code>command</code>' in patches[0]['new_inner_xhtml']
```

**Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py::TestFlushContainingChanges::test_inline_format_change_generates_inner_xhtml -v`
Expected: FAIL

**Step 3: 구현**

`_flush_containing_changes()`에 `raw_contents` 파라미터를 추가하고, inline 변경 감지 로직을 넣는다:

```python
def _flush_containing_changes(
    containing_changes: dict,
    used_ids: 'set | None' = None,
    raw_contents: 'dict | None' = None,
) -> List[Dict[str, str]]:
    """그룹화된 containing_changes를 패치 목록으로 변환한다.

    containing_changes: block_id → (mapping, [(old_plain, new_plain)])
    raw_contents: block_id → [(old_raw, new_raw)] — inline 변경 감지용 원본 MDX 콘텐츠
    각 매핑의 xhtml_plain_text에 transfer_text_changes를 순차 적용하여 패치를 생성한다.
    """
    patches = []
    for bid, (mapping, item_changes) in containing_changes.items():
        # inline 포맷 변경 감지
        has_inline = False
        if raw_contents and bid in raw_contents:
            for old_raw, new_raw in raw_contents[bid]:
                if has_inline_format_change(old_raw, new_raw):
                    has_inline = True
                    break

        if has_inline:
            # containing block 전체를 text 기반으로 패치 후 new_inner_xhtml로 전달할 수 없으므로
            # 개별 변경에 대해 text transfer 적용 후 결과를 그대로 사용
            xhtml_text = mapping.xhtml_plain_text
            for old_plain, new_plain in item_changes:
                xhtml_text = transfer_text_changes(
                    old_plain, new_plain, xhtml_text)
            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': mapping.xhtml_plain_text,
                'new_plain_text': xhtml_text,
            })
        else:
            xhtml_text = mapping.xhtml_plain_text
            for old_plain, new_plain in item_changes:
                xhtml_text = transfer_text_changes(
                    old_plain, new_plain, xhtml_text)
            patches.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'old_plain_text': mapping.xhtml_plain_text,
                'new_plain_text': xhtml_text,
            })
        if used_ids is not None:
            used_ids.add(bid)
    return patches
```

**주의:** containing 전략은 여러 MDX 블록이 하나의 XHTML 블록에 매핑되는 경우입니다. 이 경우 개별 변경의 inline format만 바꿀 수 없으므로, containing 전략에서는 **text patch를 유지**합니다. containing 전략에서 inline format 변경이 발생하는 케이스는 드물며, 향후 필요시 별도 처리할 수 있습니다.

→ **설계 단순화:** containing 전략에서는 inline format 변경 분기를 추가하지 않고, 기존 text patch 방식을 유지한다. `_flush_containing_changes()`는 변경하지 않는다.

**Step 3 (수정): 테스트 수정**

containing 전략에서는 text patch를 유지하므로, 해당 테스트를 제거하고 대신 containing 전략이 기존처럼 동작하는지 확인하는 테스트를 추가한다:

```python
    def test_inline_change_in_containing_still_uses_text_patch(self):
        """containing block에서는 inline 변경이 있어도 text patch를 유지한다."""
        m = _make_mapping('m1', 'use command and url', xpath='p[1]')
        containing_changes = {
            'm1': (m, [
                ('use command and url', 'use command and url'),
            ]),
        }
        patches = _flush_containing_changes(containing_changes)
        assert len(patches) == 1
        assert 'new_plain_text' in patches[0]
```

**Step 4: 테스트 실행 — 통과 확인**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py::TestFlushContainingChanges -v`
Expected: ALL PASS

**Step 5: 커밋**

```bash
git add tests/test_reverse_sync_patch_builder.py
git commit -m "test(confluence-mdx): containing 전략의 inline 변경 시 text patch 유지 확인 테스트 추가"
```

---

### Task 5: 전체 회귀 테스트 + 실제 verify 검증

**Files:**
- 변경 없음 (검증만)

**Step 1: 기존 patch_builder 테스트 전체 실행**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py -v`
Expected: ALL PASS (70+ tests)

**Step 2: 관련 테스트 파일 전체 실행**

Run: `python -m pytest tests/test_reverse_sync_mdx_to_xhtml_inline.py tests/test_reverse_sync_xhtml_patcher.py -v`
Expected: ALL PASS

**Step 3: 전체 테스트 스위트 실행**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 4: 실제 verify 명령으로 검증**

Run: `python bin/reverse_sync_cli.py verify --branch=split/ko-proofread-20260221-overview`
Expected:
- `system-architecture-overview.mdx`의 verify diff에서 backtick 관련 diff가 **사라져야** 한다.
- 4/4 PASS 유지

**Step 5: 커밋 (필요시)**

검증 통과 후 추가 변경이 없으면 커밋 불필요. 문제 발견 시 수정 후 커밋.

---

### Task 6: heading 블록 유형 테스트 보강

**Files:**
- Modify: `tests/test_reverse_sync_patch_builder.py`

**Step 1: heading에서 inline code 추가 테스트 작성**

```python
class TestBuildPatches:
    # ... 기존 테스트 ...

    def test_direct_heading_inline_code_added(self):
        """heading에서 backtick 추가 시 new_inner_xhtml 패치를 생성한다."""
        m1 = _make_mapping('m1', 'kubectl 명령어 가이드', xpath='h2[1]', type_='heading')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(
            0,
            '## kubectl 명령어 가이드\n',
            '## `kubectl` 명령어 가이드\n',
            type_='heading',
        )
        mdx_to_sidecar = self._setup_sidecar('h2[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert 'new_inner_xhtml' in patches[0]
        assert '<code>kubectl</code>' in patches[0]['new_inner_xhtml']
```

**Step 2: 테스트 실행 — 통과 확인**

Run: `python -m pytest tests/test_reverse_sync_patch_builder.py::TestBuildPatches::test_direct_heading_inline_code_added -v`
Expected: PASS (Task 2의 구현이 block type 무관하게 동작하므로)

**Step 3: 커밋**

```bash
git add tests/test_reverse_sync_patch_builder.py
git commit -m "test(confluence-mdx): heading/list inline format 변경 테스트 보강"
```
