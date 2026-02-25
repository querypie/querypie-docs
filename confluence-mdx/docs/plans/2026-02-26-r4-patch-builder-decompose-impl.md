# R4: patch_builder.py 구조 분해 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `patch_builder.py` (719줄)를 책임별 3개 모듈로 분리하고, 중복 상수/함수를 제거한다.

**Architecture:** 동작 변경 없이 함수를 새 모듈로 이동하고 import를 갱신한다. `patch_builder.py`는 기존 public API를 모두 re-export하여 외부 호출부 변경을 최소화한다.

**Tech Stack:** Python 3, pytest (tests/ 디렉토리에서 `python3 -m pytest` 실행, `conftest.py`가 `bin/`을 sys.path에 추가)

**베이스라인:** `python3 -m pytest tests/ -q --ignore=tests/test_unused_attachments.py` → 730 passed

---

## Task 1: R8 — `NON_CONTENT_TYPES` 상수 통합

**배경:** 동일한 `frozenset(('empty', 'frontmatter', 'import_statement'))`가 4개 파일에 6번 정의되어 있다. `block_diff.py`를 단일 출처로 삼고, 나머지는 import로 교체한다.

**Files:**
- Modify: `bin/reverse_sync/block_diff.py`
- Modify: `bin/reverse_sync/patch_builder.py`
- Modify: `bin/reverse_sync/rehydrator.py`
- Modify: `bin/reverse_sync/sidecar.py`

**Step 1: `block_diff.py`의 `NON_CONTENT_TYPES`를 모듈 최상위에 유지 (이미 있음, 확인만)**

```python
# block_diff.py line 9 — 이미 존재, 변경 없음
NON_CONTENT_TYPES = frozenset(('empty', 'frontmatter', 'import_statement'))
```

**Step 2: `patch_builder.py`에서 로컬 정의를 import로 교체**

`bin/reverse_sync/patch_builder.py` line 105 변경:
```python
# 삭제:
NON_CONTENT_TYPES = frozenset(('empty', 'frontmatter', 'import_statement'))

# 추가 (파일 상단 import 블록에):
from reverse_sync.block_diff import NON_CONTENT_TYPES
```

**Step 3: `rehydrator.py`에서 로컬 정의를 import로 교체**

`bin/reverse_sync/rehydrator.py` line 26 변경:
```python
# 삭제:
_NON_CONTENT = frozenset(("empty", "frontmatter", "import_statement"))

# 추가 (파일 상단 import 블록에):
from reverse_sync.block_diff import NON_CONTENT_TYPES as _NON_CONTENT
```

**Step 4: `sidecar.py`의 로컬 변수 2개를 import로 교체**

`bin/reverse_sync/sidecar.py` — 함수 내부 로컬 변수 2개 교체:

파일 상단 import에 추가:
```python
from reverse_sync.block_diff import NON_CONTENT_TYPES
```

`build_sidecar()` 함수 내 (line 183-184):
```python
# 삭제:
NON_CONTENT = frozenset(("empty", "frontmatter", "import_statement"))
mdx_content_blocks = [b for b in mdx_blocks if b.type not in NON_CONTENT]

# 교체:
mdx_content_blocks = [b for b in mdx_blocks if b.type not in NON_CONTENT_TYPES]
```

`generate_sidecar_mapping()` 함수 내 (line 331):
```python
# 삭제:
NON_CONTENT = frozenset(('empty', 'frontmatter', 'import_statement'))
    ...
        if b.type not in NON_CONTENT

# 교체 (함수 내 NON_CONTENT 변수 삭제, NON_CONTENT_TYPES 직접 사용):
        if b.type not in NON_CONTENT_TYPES
```

> **주의:** `sidecar.py`에는 `from __future__ import annotations`와 함께 함수 내부에서 `from reverse_sync.mapping_recorder import record_mapping` 같은 지연 import가 있다. `block_diff` import는 순환 참조 없음 (block_diff는 sidecar를 import하지 않음) — 파일 상단 import에 추가해도 안전.

**Step 5: 테스트 실행**

```bash
python3 -m pytest tests/ -q --ignore=tests/test_unused_attachments.py
```

Expected: `730 passed`

**Step 6: 커밋**

```bash
git add bin/reverse_sync/block_diff.py bin/reverse_sync/patch_builder.py \
        bin/reverse_sync/rehydrator.py bin/reverse_sync/sidecar.py
git commit -m "refactor(confluence-mdx): NON_CONTENT_TYPES 상수 block_diff.py로 통합 (R8)"
```

---

## Task 2: R7 — `_iter_block_children()` 중복 제거

**배경:** `mapping_recorder.py`에 정의된 함수가 `xhtml_patcher.py`에도 로컬 복사본으로 존재한다. `fragment_extractor.py`는 이미 `mapping_recorder.py`에서 import 중. `xhtml_patcher.py`도 동일하게 전환한다.

**Files:**
- Modify: `bin/reverse_sync/xhtml_patcher.py`

**Step 1: `xhtml_patcher.py`에서 로컬 정의 삭제 후 import로 교체**

현재 `xhtml_patcher.py` line 141-149:
```python
def _iter_block_children(parent):
    """블록 레벨 자식을 순회한다. ac:layout은 cell 내부로 진입한다."""
    for child in parent.children:
        if isinstance(child, Tag) and child.name == 'ac:layout':
            for section in child.find_all('ac:layout-section', recursive=False):
                for cell in section.find_all('ac:layout-cell', recursive=False):
                    yield from cell.children
        else:
            yield child
```

변경:
```python
# 위 함수 정의 9줄 삭제

# 파일 상단 import 블록에 추가:
from reverse_sync.mapping_recorder import _iter_block_children
```

**Step 2: 테스트 실행**

```bash
python3 -m pytest tests/test_reverse_sync_xhtml_patcher.py tests/test_reverse_sync_fragment_extractor.py -v
```

Expected: 모두 PASSED

**Step 3: 전체 테스트**

```bash
python3 -m pytest tests/ -q --ignore=tests/test_unused_attachments.py
```

Expected: `730 passed`

**Step 4: 커밋**

```bash
git add bin/reverse_sync/xhtml_patcher.py
git commit -m "refactor(confluence-mdx): xhtml_patcher의 _iter_block_children 중복 제거 (R7)"
```

---

## Task 3: `inline_detector.py` 추출

**배경:** 인라인 포맷 변경 감지 관련 함수 6개 + regex 4개를 `patch_builder.py`에서 `inline_detector.py`로 이동한다.

**Files:**
- Create: `bin/reverse_sync/inline_detector.py`
- Modify: `bin/reverse_sync/patch_builder.py`
- Modify: `tests/test_reverse_sync_patch_builder.py`

**Step 1: `bin/reverse_sync/inline_detector.py` 생성**

```python
"""인라인 포맷 변경 감지 — MDX content의 inline 마커 변경을 감지한다."""
import re

from text_utils import collapse_ws


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


def _strip_positions(markers: list) -> list:
    """마커 리스트에서 위치(index 1)를 제거하여 type+content만 비교 가능하게 한다."""
    return [(m[0],) + m[2:] for m in markers]


def _extract_marker_spans(content: str) -> list:
    """MDX content에서 inline 포맷 마커의 (start, end) 위치 범위를 추출한다."""
    spans = []
    for m in _INLINE_CODE_RE.finditer(content):
        spans.append((m.start(), m.end()))
    for m in _INLINE_BOLD_RE.finditer(content):
        spans.append((m.start(), m.end()))
    for m in _INLINE_ITALIC_RE.finditer(content):
        spans.append((m.start(), m.end()))
    for m in _INLINE_LINK_RE.finditer(content):
        spans.append((m.start(), m.end()))
    return sorted(spans)


def _extract_between_marker_texts(content: str) -> list:
    """연속된 inline 마커 사이의 텍스트를 추출한다."""
    spans = _extract_marker_spans(content)
    between = []
    for i in range(len(spans) - 1):
        between.append(content[spans[i][1]:spans[i + 1][0]])
    return between


def has_inline_format_change(old_content: str, new_content: str) -> bool:
    """old/new MDX 콘텐츠의 inline 포맷 마커가 다른지 감지한다.

    마커 type/content 변경뿐 아니라, 연속된 마커 사이의 텍스트가
    변경된 경우도 inline 변경으로 판단한다 (XHTML code 요소 경계에서
    text-only 패치가 올바르게 동작하지 않기 때문).
    """
    old_markers = _strip_positions(_extract_inline_markers(old_content))
    new_markers = _strip_positions(_extract_inline_markers(new_content))
    if old_markers != new_markers:
        return True

    # 마커가 있을 때, 연속된 마커 사이 텍스트 변경 감지
    if old_markers:
        old_between = _extract_between_marker_texts(old_content)
        new_between = _extract_between_marker_texts(new_content)
        if ([collapse_ws(s) for s in old_between]
                != [collapse_ws(s) for s in new_between]):
            return True

    return False


def has_inline_marker_added(old_content: str, new_content: str) -> bool:
    """inline 마커의 type 목록이 변경되었는지만 확인한다.

    마커 내부 content 변경은 무시하고, type 추가/제거만 감지한다.
    flat list의 전체 리스트 재생성 판단에 사용한다.
    (has_inline_format_change보다 보수적 — 이미지 등 XHTML 고유 요소 보존)
    """
    old_types = [m[0] for m in _extract_inline_markers(old_content)]
    new_types = [m[0] for m in _extract_inline_markers(new_content)]
    return old_types != new_types
```

**Step 2: `patch_builder.py`에서 추출한 코드를 import로 교체**

`patch_builder.py`에서 아래 항목들을 **삭제**:
- lines 22-25: `_INLINE_CODE_RE`, `_INLINE_BOLD_RE`, `_INLINE_ITALIC_RE`, `_INLINE_LINK_RE` 정의
- lines 28-90: `_extract_inline_markers`, `_strip_positions`, `_extract_marker_spans`, `_extract_between_marker_texts`, `has_inline_format_change`, `has_inline_marker_added` 함수 정의

파일 상단 import 블록에 **추가**:
```python
from reverse_sync.inline_detector import (
    has_inline_format_change,
    has_inline_marker_added,
    _extract_inline_markers,
)
```

> `_extract_marker_spans`, `_extract_between_marker_texts`, `_strip_positions`는 `patch_builder.py` 내에서 직접 호출되지 않으므로 import 불필요.

**Step 3: 테스트 파일의 import 갱신**

`tests/test_reverse_sync_patch_builder.py` 상단의 import 블록에서:
```python
# 변경 전:
from reverse_sync.patch_builder import (
    ...
    has_inline_format_change,
    ...
    _extract_inline_markers,
)

# 변경 후: patch_builder import에서 제거, inline_detector에서 직접 import 추가:
from reverse_sync.inline_detector import (
    has_inline_format_change,
    _extract_inline_markers,
)
```

> `patch_builder.py`가 `has_inline_format_change` 등을 re-export하지 않으므로 테스트에서 직접 새 모듈을 import해야 한다.

**Step 4: 테스트 실행**

```bash
python3 -m pytest tests/test_reverse_sync_patch_builder.py -v 2>&1 | tail -20
```

Expected: 모두 PASSED

**Step 5: 전체 테스트**

```bash
python3 -m pytest tests/ -q --ignore=tests/test_unused_attachments.py
```

Expected: `730 passed`

**Step 6: 커밋**

```bash
git add bin/reverse_sync/inline_detector.py bin/reverse_sync/patch_builder.py \
        tests/test_reverse_sync_patch_builder.py
git commit -m "refactor(confluence-mdx): inline_detector.py 추출 — 인라인 포맷 감지 모듈 분리"
```

---

## Task 4: `list_patcher.py` 추출

**배경:** 리스트 블록 패치 생성 관련 함수 4개를 `patch_builder.py`에서 `list_patcher.py`로 이동한다.

**Files:**
- Create: `bin/reverse_sync/list_patcher.py`
- Modify: `bin/reverse_sync/patch_builder.py`
- Modify: `tests/test_reverse_sync_patch_builder.py`

**Step 1: `bin/reverse_sync/list_patcher.py` 생성**

```python
"""리스트 블록 패치 — MDX list 블록 변경을 XHTML에 패치한다."""
import re
from typing import Dict, List, Optional

from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.sidecar import SidecarEntry, find_mapping_by_sidecar
from reverse_sync.inline_detector import has_inline_format_change, has_inline_marker_added
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_inner_xhtml
from mdx_to_storage.inline import convert_inline
from text_utils import normalize_mdx_to_plain, collapse_ws, strip_list_marker, strip_for_compare


def _resolve_child_mapping(
    old_plain: str,
    parent_mapping: BlockMapping,
    id_to_mapping: Dict[str, BlockMapping],
) -> Optional[BlockMapping]:
    """Parent mapping의 children 중에서 old_plain과 일치하는 child를 찾는다."""
    old_norm = collapse_ws(old_plain)
    if not old_norm:
        return None

    # 1차: collapse_ws 완전 일치
    for child_id in parent_mapping.children:
        child = id_to_mapping.get(child_id)
        if child and collapse_ws(child.xhtml_plain_text) == old_norm:
            return child

    # 2차: 공백 무시 완전 일치
    old_nospace = re.sub(r'\s+', '', old_norm)
    for child_id in parent_mapping.children:
        child = id_to_mapping.get(child_id)
        if child:
            child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
            if child_nospace == old_nospace:
                return child

    # 3차: 리스트 마커 제거 후 비교 (XHTML child가 "- text" 형식인 경우)
    for child_id in parent_mapping.children:
        child = id_to_mapping.get(child_id)
        if child:
            child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
            child_unmarked = strip_list_marker(child_nospace)
            if child_unmarked != child_nospace and old_nospace == child_unmarked:
                return child

    # 4차: MDX 쪽 리스트 마커 제거 후 비교
    old_unmarked = strip_list_marker(old_nospace)
    if old_unmarked != old_nospace:
        for child_id in parent_mapping.children:
            child = id_to_mapping.get(child_id)
            if child:
                child_nospace = re.sub(r'\s+', '', child.xhtml_plain_text)
                if old_unmarked == child_nospace:
                    return child

    return None


def split_list_items(content: str) -> List[str]:
    """리스트 블록 content를 개별 항목으로 분리한다."""
    items = []
    current: List[str] = []
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped:
            if current:
                items.append('\n'.join(current))
                current = []
            continue
        # 새 리스트 항목 시작
        if (re.match(r'^[-*+]\s+', stripped) or re.match(r'^\d+\.\s+', stripped)) and current:
            items.append('\n'.join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        items.append('\n'.join(current))
    return items


def extract_list_marker_prefix(text: str) -> str:
    """텍스트에서 선행 리스트 마커 prefix를 추출한다."""
    m = re.match(r'^([-*+]\s+|\d+\.\s+)', text)
    return m.group(0) if m else ''


def build_list_item_patches(
    change: BlockChange,
    mappings: List[BlockMapping],
    used_ids: 'set | None' = None,
    mdx_to_sidecar: Optional[Dict[int, SidecarEntry]] = None,
    xpath_to_mapping: Optional[Dict[str, 'BlockMapping']] = None,
    id_to_mapping: Optional[Dict[str, BlockMapping]] = None,
) -> List[Dict[str, str]]:
    """리스트 블록의 각 항목을 개별 매핑과 대조하여 패치를 생성한다.

    sidecar에서 얻은 parent mapping의 children을 통해 child 매핑을 해석한다.
    """
    from reverse_sync.patch_builder import _find_containing_mapping, _flush_containing_changes
    from reverse_sync.text_transfer import transfer_text_changes

    old_items = split_list_items(change.old_block.content)
    new_items = split_list_items(change.new_block.content)
    if len(old_items) != len(new_items):
        # 항목 수가 다르면 (삭제/추가) 전체 리스트 inner XHTML 재생성
        parent = None
        if mdx_to_sidecar is not None and xpath_to_mapping is not None:
            parent = find_mapping_by_sidecar(
                change.index, mdx_to_sidecar, xpath_to_mapping)
        if parent is not None:
            new_inner = mdx_block_to_inner_xhtml(
                change.new_block.content, change.new_block.type)
            return [{
                'xhtml_xpath': parent.xhtml_xpath,
                'old_plain_text': parent.xhtml_plain_text,
                'new_inner_xhtml': new_inner,
            }]
        return []

    # sidecar에서 parent mapping 획득
    parent_mapping = None
    if mdx_to_sidecar is not None and xpath_to_mapping is not None:
        parent_mapping = find_mapping_by_sidecar(
            change.index, mdx_to_sidecar, xpath_to_mapping)

    patches = []
    # 매칭 실패한 항목을 상위 블록 기준으로 그룹화
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    # flat list에서 inline 포맷 변경이 감지되면 전체 리스트 inner XHTML 재생성
    _flat_inline_change = False
    for old_item, new_item in zip(old_items, new_items):
        if old_item == new_item:
            continue
        old_plain = normalize_mdx_to_plain(old_item, 'list')

        # parent mapping의 children에서 child 해석 시도
        mapping = None
        if parent_mapping is not None and parent_mapping.children and id_to_mapping is not None:
            mapping = _resolve_child_mapping(
                old_plain, parent_mapping, id_to_mapping)

        if mapping is not None:
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
                    # XHTML body가 이미 new_plain과 일치하면 건너뛰기
                    if collapse_ws(new_plain) == collapse_ws(xhtml_body):
                        continue
                    if collapse_ws(old_plain) != collapse_ws(xhtml_body):
                        new_plain = transfer_text_changes(
                            old_plain, new_plain, xhtml_body)
                    new_plain = prefix + new_plain
                elif collapse_ws(old_plain) != collapse_ws(xhtml_text):
                    # XHTML이 이미 new_plain과 일치하면 건너뛰기
                    if collapse_ws(new_plain) == collapse_ws(xhtml_text):
                        continue
                    new_plain = transfer_text_changes(
                        old_plain, new_plain, xhtml_text)

                patches.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'old_plain_text': mapping.xhtml_plain_text,
                    'new_plain_text': new_plain,
                })
        else:
            # child 매칭 실패: inline 마커 추가/제거 여부 추적
            # (has_inline_marker_added: content 변경 무시, type 변경만 감지)
            if has_inline_marker_added(old_item, new_item):
                _flat_inline_change = True

            # parent 또는 텍스트 포함 매핑을 containing block으로 사용
            container = parent_mapping
            if container is not None and used_ids is not None:
                # parent 텍스트에 항목이 포함되지 않으면 더 나은 매핑 찾기
                _item_ns = strip_for_compare(old_plain)
                _cont_ns = strip_for_compare(container.xhtml_plain_text)
                if _item_ns and _cont_ns and _item_ns not in _cont_ns:
                    better = _find_containing_mapping(
                        old_plain, mappings, used_ids)
                    if better is not None:
                        container = better
            elif used_ids is not None:
                container = _find_containing_mapping(old_plain, mappings, used_ids)
            if container is not None:
                new_plain = normalize_mdx_to_plain(new_item, 'list')
                bid = container.block_id
                if bid not in containing_changes:
                    containing_changes[bid] = (container, [])
                containing_changes[bid][1].append((old_plain, new_plain))

    # flat list에서 inline 포맷 변경이 감지된 경우:
    # containing block 텍스트 패치 대신 전체 리스트 inner XHTML 재생성
    if _flat_inline_change and parent_mapping is not None:
        containing_changes.pop(parent_mapping.block_id, None)
        new_inner = mdx_block_to_inner_xhtml(
            change.new_block.content, change.new_block.type)
        patches.append({
            'xhtml_xpath': parent_mapping.xhtml_xpath,
            'old_plain_text': parent_mapping.xhtml_plain_text,
            'new_inner_xhtml': new_inner,
        })

    # 상위 블록에 대한 그룹화된 변경 적용
    patches.extend(_flush_containing_changes(containing_changes, used_ids))
    return patches
```

> **주의:** `build_list_item_patches`는 `_find_containing_mapping`, `_flush_containing_changes`를 호출한다. 이 두 함수는 `patch_builder.py`에 남는다. 순환 참조 방지를 위해 함수 내부에서 지연 import를 사용한다.

**Step 2: `patch_builder.py`에서 추출한 코드를 import로 교체**

`patch_builder.py`에서 아래 항목들을 **삭제**:
- `_resolve_child_mapping` 함수 (lines 354-398)
- `split_list_items` 함수 (lines 491-510)
- `extract_list_marker_prefix` 함수 (lines 648-651)
- `build_list_item_patches` 함수 (lines 513-645)

파일 상단 import 블록에 **추가**:
```python
from reverse_sync.list_patcher import (
    build_list_item_patches,
    split_list_items,
    extract_list_marker_prefix,
    _resolve_child_mapping,
)
```

**Step 3: 테스트 파일의 import 갱신**

`tests/test_reverse_sync_patch_builder.py`에서:
```python
# patch_builder import 블록에서 제거:
#   build_list_item_patches
#   split_list_items
#   extract_list_marker_prefix
#   _resolve_child_mapping

# 새로 추가:
from reverse_sync.list_patcher import (
    build_list_item_patches,
    split_list_items,
    extract_list_marker_prefix,
    _resolve_child_mapping,
)
```

`tests/test_reverse_sync_cli.py`에서도 내부 import 확인 (line 1005, 1064):
```python
# 함수 내부 import가 있으면 동일하게 갱신:
from reverse_sync.list_patcher import build_list_item_patches
```

**Step 4: 테스트 실행**

```bash
python3 -m pytest tests/test_reverse_sync_patch_builder.py tests/test_reverse_sync_cli.py -v 2>&1 | tail -20
```

Expected: 모두 PASSED

**Step 5: 전체 테스트**

```bash
python3 -m pytest tests/ -q --ignore=tests/test_unused_attachments.py
```

Expected: `730 passed`

**Step 6: 커밋**

```bash
git add bin/reverse_sync/list_patcher.py bin/reverse_sync/patch_builder.py \
        tests/test_reverse_sync_patch_builder.py tests/test_reverse_sync_cli.py
git commit -m "refactor(confluence-mdx): list_patcher.py 추출 — 리스트 블록 패치 모듈 분리"
```

---

## Task 5: `table_patcher.py` 추출

**배경:** 테이블 블록 패치 관련 함수 4개를 `patch_builder.py`에서 `table_patcher.py`로 이동한다.

**Files:**
- Create: `bin/reverse_sync/table_patcher.py`
- Modify: `bin/reverse_sync/patch_builder.py`
- Modify: `tests/test_reverse_sync_patch_builder.py`

**Step 1: `bin/reverse_sync/table_patcher.py` 생성**

```python
"""테이블 블록 패치 — MDX table 블록 변경을 XHTML에 패치한다."""
import html as html_module
import re
from typing import Dict, List, Optional

from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.sidecar import SidecarEntry, find_mapping_by_sidecar


def is_markdown_table(content: str) -> bool:
    """Content가 Markdown table 형식인지 판별한다."""
    lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        return False
    pipe_lines = sum(1 for l in lines if l.startswith('|') and l.endswith('|'))
    return pipe_lines >= 2


def split_table_rows(content: str) -> List[str]:
    """Markdown table content를 데이터 행(non-separator) 목록으로 분리한다."""
    rows = []
    for line in content.strip().split('\n'):
        s = line.strip()
        if not s:
            continue
        # separator 행 건너뛰기 (| --- | --- | ...)
        if re.match(r'^\|[\s\-:|]+\|$', s):
            continue
        if s.startswith('|') and s.endswith('|'):
            rows.append(s)
    return rows


def normalize_table_row(row: str) -> str:
    """Markdown table row를 XHTML plain text 대응 형태로 변환한다."""
    cells = [c.strip() for c in row.split('|')[1:-1]]
    parts = []
    for cell in cells:
        s = cell
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'`([^`]+)`', r'\1', s)
        s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', s)
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
        s = re.sub(
            r'<Badge\s+color="([^"]+)">(.*?)</Badge>',
            lambda m: m.group(2) + m.group(1).capitalize(),
            s,
        )
        s = re.sub(r'<[^>]+/?>', '', s)
        s = html_module.unescape(s)
        s = s.strip()
        if s:
            parts.append(s)
    return ' '.join(parts)


def build_table_row_patches(
    change: BlockChange,
    mappings: List[BlockMapping],
    used_ids: 'set | None' = None,
    mdx_to_sidecar: Optional[Dict[int, SidecarEntry]] = None,
    xpath_to_mapping: Optional[Dict[str, 'BlockMapping']] = None,
) -> List[Dict[str, str]]:
    """Markdown table 블록의 변경된 행을 XHTML table에 패치한다.

    sidecar를 통해 parent table mapping을 찾아 containing block으로 사용한다.
    """
    from reverse_sync.patch_builder import _flush_containing_changes

    old_rows = split_table_rows(change.old_block.content)
    new_rows = split_table_rows(change.new_block.content)
    if len(old_rows) != len(new_rows):
        return []

    # sidecar에서 parent mapping 획득
    container = None
    if mdx_to_sidecar is not None and xpath_to_mapping is not None:
        container = find_mapping_by_sidecar(
            change.index, mdx_to_sidecar, xpath_to_mapping)

    if container is None:
        return []

    patches = []
    containing_changes: dict = {}  # block_id → (mapping, [(old_plain, new_plain)])
    for old_row, new_row in zip(old_rows, new_rows):
        if old_row == new_row:
            continue
        old_plain = normalize_table_row(old_row)
        new_plain = normalize_table_row(new_row)
        if not old_plain or old_plain == new_plain:
            continue
        bid = container.block_id
        if bid not in containing_changes:
            containing_changes[bid] = (container, [])
        containing_changes[bid][1].append((old_plain, new_plain))

    patches.extend(_flush_containing_changes(containing_changes, used_ids))
    return patches
```

**Step 2: `patch_builder.py`에서 추출한 코드를 import로 교체**

`patch_builder.py`에서 아래 항목들을 **삭제**:
- `is_markdown_table` 함수
- `split_table_rows` 함수
- `normalize_table_row` 함수
- `build_table_row_patches` 함수
- 파일 상단의 `import html as html_module` (patch_builder에서 더 이상 html 미사용 확인 후)

파일 상단 import 블록에 **추가**:
```python
from reverse_sync.table_patcher import (
    build_table_row_patches,
    split_table_rows,
    normalize_table_row,
    is_markdown_table,
)
```

> **주의:** `_strip_block_markers` 함수는 `patch_builder.py`의 `_find_containing_mapping`에서 사용하므로 patch_builder에 남긴다.

**Step 3: 테스트 파일의 import 갱신**

`tests/test_reverse_sync_patch_builder.py`에서:
```python
# patch_builder import 블록에서 제거:
#   build_table_row_patches
#   is_markdown_table
#   split_table_rows
#   normalize_table_row

# 새로 추가:
from reverse_sync.table_patcher import (
    build_table_row_patches,
    is_markdown_table,
    split_table_rows,
    normalize_table_row,
)
```

**Step 4: 테스트 실행**

```bash
python3 -m pytest tests/test_reverse_sync_patch_builder.py -v 2>&1 | tail -20
```

Expected: 모두 PASSED

**Step 5: 전체 테스트**

```bash
python3 -m pytest tests/ -q --ignore=tests/test_unused_attachments.py
```

Expected: `730 passed`

**Step 6: 커밋**

```bash
git add bin/reverse_sync/table_patcher.py bin/reverse_sync/patch_builder.py \
        tests/test_reverse_sync_patch_builder.py
git commit -m "refactor(confluence-mdx): table_patcher.py 추출 — 테이블 블록 패치 모듈 분리"
```

---

## Task 6: 최종 검증 및 마무리

**Step 1: 전체 테스트 최종 실행**

```bash
python3 -m pytest tests/ -q --ignore=tests/test_unused_attachments.py
```

Expected: `730 passed`

**Step 2: patch_builder.py 줄 수 확인**

```bash
wc -l bin/reverse_sync/patch_builder.py
```

Expected: 330줄 내외 (원래 719줄에서 ~390줄 감소)

**Step 3: 새 모듈 목록 확인**

```bash
ls -la bin/reverse_sync/inline_detector.py bin/reverse_sync/list_patcher.py bin/reverse_sync/table_patcher.py
```

**Step 4: PR 작성**

```bash
git push -u origin refactor/reverse-sync
gh pr create \
  --title "refactor: reverse-sync patch_builder.py 구조 분해 (R4+R7+R8)" \
  --body "$(cat <<'EOF'
## Summary

- `patch_builder.py` (719줄) → 3개 모듈 분리: `inline_detector.py`, `list_patcher.py`, `table_patcher.py`
- `NON_CONTENT_TYPES` 상수 `block_diff.py`로 통합 (R8: 6곳 → 1곳 정의)
- `_iter_block_children()` `xhtml_patcher.py` 중복 제거 (R7: `mapping_recorder.py` import)
- **동작 변경 없음** — 함수 이동 + import 변경만 수행

## 변경 모듈

| 새 모듈 | 추출 내용 | 줄 수 |
|---------|-----------|-------|
| `inline_detector.py` | 인라인 포맷 변경 감지 6개 함수 + regex 4개 | ~100줄 |
| `list_patcher.py` | 리스트 블록 패치 4개 함수 | ~200줄 |
| `table_patcher.py` | 테이블 블록 패치 4개 함수 | ~90줄 |

## Test plan
- [x] 전체 테스트 730 passed 유지 확인
- [x] 매 Task 완료 후 전체 테스트 실행으로 회귀 방지

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## 참고: 파일별 최종 상태

| 파일 | 변경 내용 |
|------|-----------|
| `bin/reverse_sync/inline_detector.py` | **신규** |
| `bin/reverse_sync/list_patcher.py` | **신규** |
| `bin/reverse_sync/table_patcher.py` | **신규** |
| `bin/reverse_sync/patch_builder.py` | 719줄 → ~330줄 (함수 이동 + import 교체) |
| `bin/reverse_sync/xhtml_patcher.py` | `_iter_block_children` 로컬 정의 삭제 + import |
| `bin/reverse_sync/rehydrator.py` | `_NON_CONTENT` 로컬 정의 → import |
| `bin/reverse_sync/sidecar.py` | `NON_CONTENT` 로컬 변수 2개 → import |
| `tests/test_reverse_sync_patch_builder.py` | import 경로 갱신 |
| `tests/test_reverse_sync_cli.py` | 내부 import 갱신 (해당 시) |
