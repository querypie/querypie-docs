# Phase L5: Backward Converter 정확도 개선 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 역순변환기의 XHTML 출력 품질을 개선하여 `ordered_list_start_mismatch` (12건), inline Badge (2건), 리스트 내 이미지 구조 (5건)를 해결한다.

**Architecture:** `emitter.py`의 리스트 렌더링과 figure 렌더링, `inline.py`의 인라인 변환에 각각 독립적인 수정을 가한다. 기존 파서(`parser.py`)는 변경하지 않는다.

**Tech Stack:** Python 3, pytest, PYTHONPATH=bin

---

## Task 1: `<ol start="1">` 속성 추가

**Files:**
- Modify: `bin/mdx_to_storage/emitter.py:197-213` (`_render_list_nodes()`)
- Test: `tests/test_mdx_to_storage/test_emitter.py`

### Step 1: 기존 테스트 업데이트 (ol → ol start="1")

현재 `<ol>`을 기대하는 기존 테스트 3개를 `<ol start="1">`로 변경한다.

```python
# test_emitter.py:48-52 — test_emit_list_ul_and_ol
def test_emit_list_ul_and_ol():
    ul = emit_document(parse_mdx("* a\n* b\n"))
    ol = emit_document(parse_mdx("1. a\n2. b\n"))
    assert ul == "<ul><li><p>a</p></li><li><p>b</p></li></ul>"
    assert ol == '<ol start="1"><li><p>a</p></li><li><p>b</p></li></ol>'

# test_emitter.py:323-333 — test_emit_nested_mixed_ordered_unordered_list
def test_emit_nested_mixed_ordered_unordered_list():
    mdx = """1. step one
    * detail a
    * detail b
2. step two
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert (
        xhtml
        == '<ol start="1"><li><p>step one</p><ul><li><p>detail a</p></li><li><p>detail b</p></li></ul></li><li><p>step two</p></li></ol>'
    )

# test_emitter.py:336-341 — test_emit_same_depth_mixed_marker_splits_lists
def test_emit_same_depth_mixed_marker_splits_lists():
    mdx = """* bullet
1. ordered
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert xhtml == '<ul><li><p>bullet</p></li></ul><ol start="1"><li><p>ordered</p></li></ol>'
```

### Step 2: 테스트가 실패하는지 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/test_mdx_to_storage/test_emitter.py::test_emit_list_ul_and_ol tests/test_mdx_to_storage/test_emitter.py::test_emit_nested_mixed_ordered_unordered_list tests/test_mdx_to_storage/test_emitter.py::test_emit_same_depth_mixed_marker_splits_lists -v`
Expected: 3 FAILED

### Step 3: `_render_list_nodes()` 수정

```python
# emitter.py:212 — 변경 전:
        parts.append(f"<{tag}>{body}</{tag}>")
# 변경 후:
        if tag == "ol":
            parts.append(f'<ol start="1">{body}</ol>')
        else:
            parts.append(f"<ul>{body}</ul>")
```

### Step 4: 테스트 통과 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/test_mdx_to_storage/test_emitter.py -v`
Expected: ALL PASSED

### Step 5: 전체 테스트 스위트 통과 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/ -v --tb=short`
Expected: ALL PASSED (기존 테스트 중 `<ol>`을 하드코딩한 테스트가 없는지 확인)

### Step 6: Commit

```bash
git add bin/mdx_to_storage/emitter.py tests/test_mdx_to_storage/test_emitter.py
git commit -m "confluence-mdx: ol 태그에 start=\"1\" 속성 추가 (L5 Item 1)"
```

---

## Task 2: Badge 인라인 변환

**Files:**
- Modify: `bin/mdx_to_storage/inline.py` (Badge 정규식 + 변환 추가)
- Test: `tests/test_mdx_to_storage/test_inline.py`

### Step 1: 실패하는 테스트 작성

```python
# test_inline.py — 추가
def test_convert_inline_badge_to_status_macro():
    src = '텍스트 <Badge color="blue">와일드카드 허용</Badge>'
    got = convert_inline(src)
    assert got == (
        '텍스트 <ac:structured-macro ac:name="status">'
        '<ac:parameter ac:name="title">와일드카드 허용</ac:parameter>'
        '<ac:parameter ac:name="colour">Blue</ac:parameter>'
        '</ac:structured-macro>'
    )


def test_convert_inline_badge_color_mapping():
    for color, expected in [("green", "Green"), ("red", "Red"), ("yellow", "Yellow"), ("purple", "Purple"), ("gray", "Grey")]:
        src = f'<Badge color="{color}">text</Badge>'
        got = convert_inline(src)
        assert f'<ac:parameter ac:name="colour">{expected}</ac:parameter>' in got


def test_convert_inline_badge_unknown_color_defaults_grey():
    src = '<Badge color="orange">text</Badge>'
    got = convert_inline(src)
    assert '<ac:parameter ac:name="colour">Grey</ac:parameter>' in got
```

### Step 2: 테스트 실패 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/test_mdx_to_storage/test_inline.py::test_convert_inline_badge_to_status_macro -v`
Expected: FAIL (Badge가 raw HTML로 통과)

### Step 3: inline.py에 Badge 변환 구현

`inline.py`에 추가:

```python
# 상단 상수 추가
_BADGE_INLINE_RE = re.compile(
    r'<Badge\s+color="([^"]+)">(.*?)</Badge>', flags=re.DOTALL
)
_BADGE_COLOR_MAP = {
    "green": "Green",
    "blue": "Blue",
    "red": "Red",
    "yellow": "Yellow",
    "grey": "Grey",
    "gray": "Grey",
    "purple": "Purple",
}

# convert_inline() 내부, _BR_TAG_RE.sub 바로 뒤에 추가:
    converted = _BADGE_INLINE_RE.sub(_replace_badge, converted)
```

헬퍼 함수:

```python
def _replace_badge(match: re.Match[str]) -> str:
    color = match.group(1).strip().lower()
    text = match.group(2).strip()
    colour = _BADGE_COLOR_MAP.get(color, "Grey")
    return (
        f'<ac:structured-macro ac:name="status">'
        f'<ac:parameter ac:name="title">{text}</ac:parameter>'
        f'<ac:parameter ac:name="colour">{colour}</ac:parameter>'
        f'</ac:structured-macro>'
    )
```

### Step 4: 테스트 통과 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/test_mdx_to_storage/test_inline.py -v`
Expected: ALL PASSED

### Step 5: 전체 테스트 스위트 통과 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/ -v --tb=short`
Expected: ALL PASSED

### Step 6: Commit

```bash
git add bin/mdx_to_storage/inline.py tests/test_mdx_to_storage/test_inline.py
git commit -m "confluence-mdx: 인라인 Badge → status 매크로 변환 추가 (L5 Item 2)"
```

---

## Task 3: 리스트 내 이미지 → `<ac:image>` 형제 구조

**Files:**
- Modify: `bin/mdx_to_storage/emitter.py` (`_render_list_item()` 수정 + 헬퍼 추가)
- Test: `tests/test_mdx_to_storage/test_emitter.py`

### Step 1: 실패하는 테스트 작성

```python
# test_emitter.py — 추가
def test_emit_list_item_with_figure_becomes_ac_image_sibling():
    """리스트 아이템 내 figure는 <p>의 형제 <ac:image>로 변환."""
    mdx = """1. 텍스트 <br/>
  <figure data-layout="center" data-align="center">
  <img src="/images/path/sample-image.png" alt="sample-image.png" width="712" />
  </figure>
"""
    xhtml = emit_document(parse_mdx(mdx))
    assert '<li><p>텍스트</p>' in xhtml
    assert '<ac:image ac:align="center" ac:width="712">' in xhtml
    assert '<ri:attachment ri:filename="sample-image.png"></ri:attachment>' in xhtml
    assert '<p />' in xhtml
    # figure 태그가 남아있지 않아야 함
    assert '<figure' not in xhtml


def test_emit_list_item_without_figure_unchanged():
    """figure가 없는 일반 리스트 아이템은 기존 동작 유지."""
    mdx = "1. normal item\n2. second item\n"
    xhtml = emit_document(parse_mdx(mdx))
    assert '<ol start="1"><li><p>normal item</p></li><li><p>second item</p></li></ol>' == xhtml
```

### Step 2: 테스트 실패 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/test_mdx_to_storage/test_emitter.py::test_emit_list_item_with_figure_becomes_ac_image_sibling -v`
Expected: FAIL

### Step 3: `_render_list_item()` 수정 + figure 추출 헬퍼

```python
# emitter.py 상단 상수 추가
_FIGURE_IN_LIST_RE = re.compile(
    r'\s*<figure[^>]*>\s*<img\s+([^>]+?)\s*/?\s*>\s*</figure>',
    flags=re.DOTALL,
)
_TRAILING_BR_RE = re.compile(r'\s*<br\s*/?\s*>\s*$')

# _render_list_item() 수정
def _render_list_item(node: _ListNode, link_resolver: Optional[LinkResolver] = None) -> str:
    nested = (
        _render_list_nodes(node.children, link_resolver=link_resolver)
        if node.children
        else ""
    )
    text = node.text
    figure_match = _FIGURE_IN_LIST_RE.search(text)
    if figure_match:
        before_text = text[:figure_match.start()]
        before_text = _TRAILING_BR_RE.sub("", before_text).strip()
        img_attrs_str = figure_match.group(1)
        ac_image = _figure_attrs_to_ac_image(img_attrs_str)
        p_content = convert_inline(before_text, link_resolver=link_resolver) if before_text else ""
        parts = ["<li>"]
        if p_content:
            parts.append(f"<p>{p_content}</p>")
        parts.append(ac_image)
        parts.append("<p />")
        parts.append(nested)
        parts.append("</li>")
        return "".join(parts)
    return f"<li><p>{convert_inline(text, link_resolver=link_resolver)}</p>{nested}</li>"


def _figure_attrs_to_ac_image(img_attrs_str: str) -> str:
    """<img> 속성 문자열에서 <ac:image><ri:attachment> XHTML을 생성."""
    src = ""
    width = ""
    for key, v1, v2 in re.findall(r'(\w[\w-]*)=(?:"([^"]*)"|\'([^\']*)\')', img_attrs_str):
        val = v1 or v2
        if key == "src":
            src = val
        elif key == "width":
            width = val

    import os
    filename = os.path.basename(src) if src else ""
    ac_attrs = ['ac:align="center"']
    if width:
        ac_attrs.append(f'ac:width="{width}"')

    return (
        f'<ac:image {" ".join(ac_attrs)}>'
        f'<ri:attachment ri:filename="{filename}"></ri:attachment>'
        f'</ac:image>'
    )
```

### Step 4: 테스트 통과 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/test_mdx_to_storage/test_emitter.py -v`
Expected: ALL PASSED

### Step 5: 전체 테스트 스위트 통과 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/ -v --tb=short`
Expected: ALL PASSED

### Step 6: Commit

```bash
git add bin/mdx_to_storage/emitter.py tests/test_mdx_to_storage/test_emitter.py
git commit -m "confluence-mdx: 리스트 내 figure → ac:image 형제 구조 변환 (L5 Item 3)"
```

---

## Task 4: Sidecar 재생성 + Splice byte-equal 검증

**Files:**
- Verify: `tests/testcases/*/expected.roundtrip.json` (재생성 필요 시)
- Test: `tests/test_reverse_sync_byte_verify.py`, `tests/test_reverse_sync_rehydrator.py`

### Step 1: Splice byte-equal 검증

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/test_reverse_sync_byte_verify.py::TestSpliceRealTestcases -v`
Expected: 21/21 PASS 또는 sidecar 재생성 필요

### Step 2: (조건부) Sidecar 재생성

emitter 변경은 Forward Conversion(XHTML→MDX)에 영향을 주지 않으므로 sidecar는 변경되지 않을 것이다. 만약 실패 시:

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python bin/mdx_to_storage_roundtrip_sidecar_cli.py batch-generate --testcases-dir tests/testcases`

### Step 3: 전체 테스트 스위트 최종 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: ALL PASSED

### Step 4: Normalize-diff 개선 확인

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && PYTHONPATH=bin ./venv/bin/python bin/mdx_to_storage_xhtml_verify_cli.py --testcases-dir tests/testcases --show-analysis 2>&1 | tail -40`
Expected: `ordered_list_start_mismatch` 0건 확인

### Step 5: Commit (sidecar 변경 시에만)

```bash
git add tests/testcases/*/expected.roundtrip.json
git commit -m "confluence-mdx: L5 변경에 따른 sidecar 재생성"
```

---

## Task 5: 아키텍처 문서 업데이트 + PR 생성

**Files:**
- Modify: `docs/architecture.md` (L5 완료 반영)

### Step 1: 아키텍처 문서 L5 상태 업데이트

- 로드맵 테이블: L5 → **완료**
- L5 섹션: 실제 구현 내용으로 업데이트
- Emitter 실패 원인 분포: `ordered_list_start_mismatch` 건수 업데이트
- 모듈 줄 수 업데이트 (emitter.py, inline.py)

### Step 2: Commit

```bash
git add docs/architecture.md
git commit -m "confluence-mdx: 아키텍처 문서 L5 완료 상태 반영"
```

### Step 3: PR 생성

```bash
gh pr create --base main --title "confluence-mdx: Phase L5 emitter 정확도 개선" --body "..."
```
