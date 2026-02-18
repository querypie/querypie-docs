# Phase L4: 메타데이터 활용 패처 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** L3에서 수집한 lost_info를 활용하여, 변경된 블록의 emitter 출력을 원본에 가까운 XHTML로 후처리하는 패처를 구현한다.

**Architecture:** 독립 모듈 `reverse_sync/lost_info_patcher.py`에 4가지 카테고리(emoticon, link, filename, adf_extension)의 패치 함수를 구현한다. 페이지 레벨 lost_info를 블록 단위로 분배한 후, rehydrator(splice 경로)와 patch_builder(insert 경로)에서 emitter 출력 후 호출한다.

**Tech Stack:** Python 3.13, emoji library, regex, pytest

---

## Task 1: lost_info_patcher 모듈 — emoticon 패칭

**Files:**
- Create: `bin/reverse_sync/lost_info_patcher.py`
- Create: `tests/test_lost_info_patcher.py`

**Step 1: Write the failing test**

```python
# tests/test_lost_info_patcher.py
"""lost_info_patcher 유닛 테스트."""
import pytest


class TestPatchEmoticons:
    def test_unicode_emoji_replaced_with_original(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>Check ✔️ done</p>'
        lost_info = {
            'emoticons': [{
                'name': 'tick',
                'shortname': ':check_mark:',
                'emoji_id': 'atlassian-check_mark',
                'fallback': ':check_mark:',
                'raw': '<ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:" ac:emoji-id="atlassian-check_mark" ac:emoji-fallback=":check_mark:"/>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:emoticon ac:name="tick"' in result
        assert '✔️' not in result

    def test_fallback_emoji_char_replaced(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>Status ✅</p>'
        lost_info = {
            'emoticons': [{
                'name': 'blue-star',
                'shortname': ':white_check_mark:',
                'emoji_id': '2705',
                'fallback': '✅',
                'raw': '<ac:emoticon ac:name="blue-star" ac:emoji-shortname=":white_check_mark:" ac:emoji-id="2705" ac:emoji-fallback="✅"/>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:emoticon ac:name="blue-star"' in result

    def test_no_emoticons_returns_unchanged(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>No emoji here</p>'
        result = apply_lost_info(emitted, {})
        assert result == emitted

    def test_multiple_emoticons_sequential(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>✔️ first ✅ second</p>'
        lost_info = {
            'emoticons': [
                {'name': 'tick', 'shortname': ':check_mark:', 'emoji_id': '', 'fallback': ':check_mark:',
                 'raw': '<ac:emoticon ac:name="tick"/>'},
                {'name': 'blue-star', 'shortname': '', 'emoji_id': '', 'fallback': '✅',
                 'raw': '<ac:emoticon ac:name="blue-star"/>'},
            ],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:emoticon ac:name="tick"/>' in result
        assert '<ac:emoticon ac:name="blue-star"/>' in result

    def test_emoticon_not_found_skipped(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>No matching emoji</p>'
        lost_info = {
            'emoticons': [{'name': 'tick', 'shortname': ':check_mark:', 'emoji_id': '', 'fallback': ':check_mark:',
                           'raw': '<ac:emoticon ac:name="tick"/>'}],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'reverse_sync.lost_info_patcher'`

**Step 3: Write minimal implementation**

```python
# bin/reverse_sync/lost_info_patcher.py
"""Lost info patcher — emitter 출력에 lost_info를 적용하여 원본에 가까운 XHTML을 생성한다."""
from __future__ import annotations

import emoji as emoji_lib


def apply_lost_info(emitted_xhtml: str, lost_info: dict) -> str:
    """Emitter 출력에 lost_info를 적용한다."""
    if not lost_info:
        return emitted_xhtml

    result = emitted_xhtml

    if 'emoticons' in lost_info:
        result = _patch_emoticons(result, lost_info['emoticons'])

    return result


def _resolve_emoticon_char(entry: dict) -> str | None:
    """lost_info emoticon 엔트리에서 MDX에 들어간 유니코드 문자를 역산한다."""
    fallback = entry.get('fallback', '')
    shortname = entry.get('shortname', '')

    # Case 1: fallback이 이미 유니코드 문자 (: 으로 시작하지 않음)
    if fallback and not fallback.startswith(':'):
        return fallback

    # Case 2: shortname → emoji 변환
    if shortname:
        char = emoji_lib.emojize(shortname, language='alias')
        if char != shortname:
            return char

    # Case 3: fallback이 shortname 형식
    if fallback:
        char = emoji_lib.emojize(fallback, language='alias')
        if char != fallback:
            return char

    return None


def _patch_emoticons(xhtml: str, emoticons: list[dict]) -> str:
    """유니코드 이모지를 원본 <ac:emoticon> 태그로 복원한다."""
    result = xhtml
    for entry in emoticons:
        char = _resolve_emoticon_char(entry)
        if char is None:
            continue
        raw = entry.get('raw', '')
        if not raw:
            continue
        # 첫 번째 매칭만 치환 (순차 소비)
        if char in result:
            result = result.replace(char, raw, 1)
    return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add bin/reverse_sync/lost_info_patcher.py tests/test_lost_info_patcher.py
git commit -m "confluence-mdx: lost_info_patcher 모듈 생성 — emoticon 패칭 구현"
```

---

## Task 2: link 패칭 추가

**Files:**
- Modify: `bin/reverse_sync/lost_info_patcher.py`
- Modify: `tests/test_lost_info_patcher.py`

**Step 1: Write the failing test**

```python
# tests/test_lost_info_patcher.py 에 추가
class TestPatchLinks:
    def test_link_error_replaced_with_original(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p><a href="#link-error">Missing Page</a></p>'
        lost_info = {
            'links': [{
                'content_title': 'Missing Page',
                'space_key': '',
                'raw': '<ac:link><ri:page ri:content-title="Missing Page"/><ac:link-body>Missing Page</ac:link-body></ac:link>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:link>' in result
        assert 'ri:content-title="Missing Page"' in result
        assert '#link-error' not in result

    def test_multiple_link_errors_sequential(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p><a href="#link-error">Page A</a> and <a href="#link-error">Page B</a></p>'
        lost_info = {
            'links': [
                {'content_title': 'Page A', 'space_key': '', 'raw': '<ac:link><ri:page ri:content-title="Page A"/><ac:link-body>Page A</ac:link-body></ac:link>'},
                {'content_title': 'Page B', 'space_key': '', 'raw': '<ac:link><ri:page ri:content-title="Page B"/><ac:link-body>Page B</ac:link-body></ac:link>'},
            ],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result.count('<ac:link>') == 2

    def test_no_link_error_skipped(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p><a href="https://example.com">Link</a></p>'
        lost_info = {
            'links': [{'content_title': 'Page', 'space_key': '', 'raw': '<ac:link>...</ac:link>'}],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py::TestPatchLinks -v`
Expected: FAIL

**Step 3: Write minimal implementation**

`apply_lost_info()`에 link 호출 추가 및 `_patch_links()` 구현:

```python
# apply_lost_info()에 추가
    if 'links' in lost_info:
        result = _patch_links(result, lost_info['links'])


import re

_LINK_ERROR_RE = re.compile(r'<a\s+href="#link-error"[^>]*>.*?</a>', re.DOTALL)


def _patch_links(xhtml: str, links: list[dict]) -> str:
    """#link-error 앵커를 원본 <ac:link> 태그로 복원한다."""
    result = xhtml
    for entry in links:
        raw = entry.get('raw', '')
        if not raw:
            continue
        match = _LINK_ERROR_RE.search(result)
        if match:
            result = result[:match.start()] + raw + result[match.end():]
    return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add bin/reverse_sync/lost_info_patcher.py tests/test_lost_info_patcher.py
git commit -m "confluence-mdx: lost_info_patcher에 link 패칭 추가"
```

---

## Task 3: filename 패칭 추가

**Files:**
- Modify: `bin/reverse_sync/lost_info_patcher.py`
- Modify: `tests/test_lost_info_patcher.py`

**Step 1: Write the failing test**

```python
class TestPatchFilenames:
    def test_normalized_filename_restored(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<ac:image ac:align="center"><ri:attachment ri:filename="screenshot-20240801-145006.png"></ri:attachment></ac:image>'
        lost_info = {
            'filenames': [{
                'original': '스크린샷 2024-08-01 오후 2.50.06.png',
                'normalized': 'screenshot-20240801-145006.png',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '스크린샷 2024-08-01 오후 2.50.06.png' in result
        assert 'screenshot-20240801-145006.png' not in result

    def test_filename_not_found_skipped(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<ac:image><ri:attachment ri:filename="other.png"></ri:attachment></ac:image>'
        lost_info = {
            'filenames': [{'original': 'orig.png', 'normalized': 'norm.png'}],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py::TestPatchFilenames -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# apply_lost_info()에 추가
    if 'filenames' in lost_info:
        result = _patch_filenames(result, lost_info['filenames'])


def _patch_filenames(xhtml: str, filenames: list[dict]) -> str:
    """정규화된 파일명을 원본 파일명으로 복원한다."""
    result = xhtml
    for entry in filenames:
        original = entry.get('original', '')
        normalized = entry.get('normalized', '')
        if not original or not normalized:
            continue
        # ri:filename="normalized" 패턴만 치환 (일반 텍스트는 건드리지 않음)
        old = f'ri:filename="{normalized}"'
        new = f'ri:filename="{original}"'
        result = result.replace(old, new)
    return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add bin/reverse_sync/lost_info_patcher.py tests/test_lost_info_patcher.py
git commit -m "confluence-mdx: lost_info_patcher에 filename 패칭 추가"
```

---

## Task 4: adf_extension 패칭 추가

**Files:**
- Modify: `bin/reverse_sync/lost_info_patcher.py`
- Modify: `tests/test_lost_info_patcher.py`

**Step 1: Write the failing test**

```python
class TestPatchAdfExtensions:
    def test_structured_macro_replaced_with_adf(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<ac:structured-macro ac:name="note"><ac:rich-text-body><p>content</p></ac:rich-text-body></ac:structured-macro>'
        lost_info = {
            'adf_extensions': [{
                'panel_type': 'note',
                'raw': '<ac:adf-extension><ac:adf-node type="panel"><ac:adf-attribute key="panel-type">note</ac:adf-attribute><ac:adf-content><p>content</p></ac:adf-content></ac:adf-node></ac:adf-extension>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:adf-extension>' in result
        assert '<ac:structured-macro' not in result

    def test_panel_type_mismatch_skipped(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<ac:structured-macro ac:name="info"><ac:rich-text-body><p>text</p></ac:rich-text-body></ac:structured-macro>'
        lost_info = {
            'adf_extensions': [{
                'panel_type': 'error',
                'raw': '<ac:adf-extension>...</ac:adf-extension>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        # info macro에 대응하는 panel_type은 info, 여기서는 error이므로 매칭 안 됨
        assert result == emitted

    def test_no_adf_returns_unchanged(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>No ADF here</p>'
        lost_info = {
            'adf_extensions': [{'panel_type': 'note', 'raw': '<ac:adf-extension>...</ac:adf-extension>'}],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py::TestPatchAdfExtensions -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# apply_lost_info()에 추가
    if 'adf_extensions' in lost_info:
        result = _patch_adf_extensions(result, lost_info['adf_extensions'])


# emitter의 Callout type → macro name 매핑의 역방향
_MACRO_NAME_TO_PANEL_TYPE = {
    'tip': 'default',
    'info': 'info',
    'note': 'important',
    'warning': 'error',
}

_STRUCTURED_MACRO_RE = re.compile(
    r'<ac:structured-macro\s+ac:name="(tip|info|note|warning)">'
    r'.*?</ac:structured-macro>',
    re.DOTALL,
)


def _patch_adf_extensions(xhtml: str, adf_extensions: list[dict]) -> str:
    """<ac:structured-macro>를 원본 <ac:adf-extension>으로 복원한다."""
    result = xhtml
    for entry in adf_extensions:
        panel_type = entry.get('panel_type', '')
        raw = entry.get('raw', '')
        if not raw or not panel_type:
            continue

        match = _STRUCTURED_MACRO_RE.search(result)
        if not match:
            continue

        macro_name = match.group(1)
        expected_panel_type = _MACRO_NAME_TO_PANEL_TYPE.get(macro_name, '')
        if expected_panel_type != panel_type:
            continue

        result = result[:match.start()] + raw + result[match.end():]

    return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add bin/reverse_sync/lost_info_patcher.py tests/test_lost_info_patcher.py
git commit -m "confluence-mdx: lost_info_patcher에 adf_extension 패칭 추가"
```

---

## Task 5: mapping.yaml에서 페이지 레벨 lost_info 로드

**Files:**
- Modify: `bin/reverse_sync/sidecar.py` — `load_sidecar_mapping()` (line 257)
- Modify: `tests/test_lost_info_patcher.py`

**Step 1: Write the failing test**

```python
class TestLoadPageLostInfo:
    def test_load_lost_info_from_mapping_yaml(self):
        import tempfile, yaml
        from pathlib import Path
        from reverse_sync.sidecar import load_page_lost_info

        data = {
            'version': 2,
            'source_page_id': '123',
            'mdx_file': 'page.mdx',
            'mappings': [{'xhtml_xpath': 'p[1]', 'xhtml_type': 'paragraph', 'mdx_blocks': [0]}],
            'lost_info': {
                'emoticons': [{'name': 'tick', 'shortname': ':check_mark:', 'emoji_id': '', 'fallback': '', 'raw': '<ac:emoticon ac:name="tick"/>'}],
            },
        }
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f:
            yaml.dump(data, f, allow_unicode=True)
            f.flush()
            result = load_page_lost_info(f.name)

        assert 'emoticons' in result
        assert result['emoticons'][0]['name'] == 'tick'

    def test_no_lost_info_returns_empty(self):
        import tempfile, yaml
        from reverse_sync.sidecar import load_page_lost_info

        data = {
            'version': 2,
            'source_page_id': '123',
            'mdx_file': 'page.mdx',
            'mappings': [],
        }
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f:
            yaml.dump(data, f, allow_unicode=True)
            f.flush()
            result = load_page_lost_info(f.name)

        assert result == {}
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py::TestLoadPageLostInfo -v`
Expected: FAIL — `ImportError: cannot import name 'load_page_lost_info'`

**Step 3: Write minimal implementation**

`bin/reverse_sync/sidecar.py`에 추가:

```python
def load_page_lost_info(mapping_path: str) -> dict:
    """mapping.yaml에서 페이지 레벨 lost_info를 로드한다."""
    path = Path(mapping_path)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data.get('lost_info', {})
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add bin/reverse_sync/sidecar.py tests/test_lost_info_patcher.py
git commit -m "confluence-mdx: load_page_lost_info() 함수 추가"
```

---

## Task 6: lost_info를 블록 단위로 분배

**Files:**
- Modify: `bin/reverse_sync/lost_info_patcher.py`
- Modify: `tests/test_lost_info_patcher.py`

**Step 1: Write the failing test**

```python
class TestDistributeLostInfo:
    def test_emoticon_assigned_to_containing_block(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info
        from reverse_sync.sidecar import SidecarBlock

        blocks = [
            SidecarBlock(block_index=0, xhtml_xpath='h2[1]', xhtml_fragment='<h2>Title</h2>'),
            SidecarBlock(block_index=1, xhtml_xpath='p[1]',
                         xhtml_fragment='<p>Check <ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:"/></p>'),
        ]
        page_lost_info = {
            'emoticons': [{
                'name': 'tick', 'shortname': ':check_mark:', 'emoji_id': '', 'fallback': '',
                'raw': '<ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:"/>',
            }],
        }
        distribute_lost_info(blocks, page_lost_info)
        assert blocks[0].lost_info == {}
        assert 'emoticons' in blocks[1].lost_info
        assert blocks[1].lost_info['emoticons'][0]['name'] == 'tick'

    def test_multiple_categories_distributed(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info
        from reverse_sync.sidecar import SidecarBlock

        blocks = [
            SidecarBlock(block_index=0, xhtml_xpath='p[1]',
                         xhtml_fragment='<p><ac:emoticon ac:name="tick"/></p>'),
            SidecarBlock(block_index=1, xhtml_xpath='p[2]',
                         xhtml_fragment='<p><ac:link><ri:page ri:content-title="Page"/></ac:link></p>'),
        ]
        page_lost_info = {
            'emoticons': [{'name': 'tick', 'shortname': '', 'emoji_id': '', 'fallback': '',
                           'raw': '<ac:emoticon ac:name="tick"/>'}],
            'links': [{'content_title': 'Page', 'space_key': '',
                       'raw': '<ac:link><ri:page ri:content-title="Page"/></ac:link>'}],
        }
        distribute_lost_info(blocks, page_lost_info)
        assert 'emoticons' in blocks[0].lost_info
        assert 'links' in blocks[1].lost_info

    def test_empty_lost_info_no_change(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info
        from reverse_sync.sidecar import SidecarBlock

        blocks = [SidecarBlock(block_index=0, xhtml_xpath='p[1]', xhtml_fragment='<p>text</p>')]
        distribute_lost_info(blocks, {})
        assert blocks[0].lost_info == {}
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py::TestDistributeLostInfo -v`
Expected: FAIL — `ImportError: cannot import name 'distribute_lost_info'`

**Step 3: Write minimal implementation**

`bin/reverse_sync/lost_info_patcher.py`에 추가:

```python
from reverse_sync.sidecar import SidecarBlock


def distribute_lost_info(blocks: list[SidecarBlock], page_lost_info: dict) -> None:
    """페이지 레벨 lost_info를 각 블록에 분배한다.

    각 항목의 raw 필드가 블록의 xhtml_fragment에 포함되는지로 판별한다.
    블록의 lost_info dict를 in-place로 갱신한다.
    """
    if not page_lost_info:
        return

    for category in ('emoticons', 'links', 'filenames', 'adf_extensions'):
        entries = page_lost_info.get(category, [])
        for entry in entries:
            raw = entry.get('raw', '')
            if not raw:
                # filename은 raw가 없으므로 normalized로 매칭
                if category == 'filenames':
                    normalized = entry.get('normalized', '')
                    if not normalized:
                        continue
                    for block in blocks:
                        if normalized in block.xhtml_fragment:
                            block.lost_info.setdefault(category, []).append(entry)
                            break
                continue
            for block in blocks:
                if raw in block.xhtml_fragment:
                    block.lost_info.setdefault(category, []).append(entry)
                    break
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add bin/reverse_sync/lost_info_patcher.py tests/test_lost_info_patcher.py
git commit -m "confluence-mdx: distribute_lost_info() — 블록 단위 lost_info 분배"
```

---

## Task 7: splice rehydration 경로에 lost_info 통합

**Files:**
- Modify: `bin/reverse_sync/rehydrator.py` (line 111)
- Modify: `tests/test_lost_info_patcher.py`

**Step 1: Write the failing test**

```python
class TestSpliceWithLostInfo:
    def test_emitted_block_gets_lost_info_applied(self):
        """splice 경로에서 emitter 출력에 lost_info가 적용되는지 테스트."""
        from reverse_sync.rehydrator import splice_rehydrate_xhtml
        from reverse_sync.sidecar import RoundtripSidecar, SidecarBlock, DocumentEnvelope, sha256_text

        # 변경된 MDX (hash 불일치하도록)
        mdx_text = '## Title\n\nCheck ✔️ done\n'

        # Sidecar: block 1의 hash가 불일치하도록 설정
        sidecar = RoundtripSidecar(
            page_id='test',
            mdx_sha256='different',
            source_xhtml_sha256='test',
            blocks=[
                SidecarBlock(
                    block_index=0,
                    xhtml_xpath='h2[1]',
                    xhtml_fragment='<h2>Title</h2>',
                    mdx_content_hash=sha256_text('## Title'),
                ),
                SidecarBlock(
                    block_index=1,
                    xhtml_xpath='p[1]',
                    xhtml_fragment='<p>original <ac:emoticon ac:name="tick"/></p>',
                    mdx_content_hash='wrong_hash',  # 불일치 → emitter 호출
                    lost_info={
                        'emoticons': [{
                            'name': 'tick',
                            'shortname': ':check_mark:',
                            'emoji_id': '',
                            'fallback': ':check_mark:',
                            'raw': '<ac:emoticon ac:name="tick"/>',
                        }],
                    },
                ),
            ],
            separators=['\n'],
            document_envelope=DocumentEnvelope(prefix='', suffix=''),
        )

        result = splice_rehydrate_xhtml(mdx_text, sidecar)
        # emitter가 ✔️를 출력하지만, lost_info로 <ac:emoticon>으로 복원됨
        assert '<ac:emoticon ac:name="tick"/>' in result.xhtml
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py::TestSpliceWithLostInfo -v`
Expected: FAIL — emitter 출력에 `✔️`가 그대로 남아 있음

**Step 3: Write minimal implementation**

`bin/reverse_sync/rehydrator.py` 수정:

1. import 추가 (line 6 부근):
```python
from .lost_info_patcher import apply_lost_info
```

2. `splice_rehydrate_xhtml()` 내 emitter 호출 후 (line 111):
```python
            else:
                parser_block = _mdx_block_to_parser_block(mdx_block)
                emitted = emit_single_block(parser_block)
                # L4: lost_info 적용
                if sb.lost_info:
                    emitted = apply_lost_info(emitted, sb.lost_info)
                fragments.append(emitted)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add bin/reverse_sync/rehydrator.py tests/test_lost_info_patcher.py
git commit -m "confluence-mdx: splice rehydration 경로에 lost_info 패칭 통합"
```

---

## Task 8: reverse sync insert 경로에 lost_info 통합

**Files:**
- Modify: `bin/reverse_sync/patch_builder.py` (line 516)
- Modify: `tests/test_lost_info_patcher.py`

이 단계에서는 `_build_insert_patch()`에 page_lost_info를 전달할 수 있도록 `build_patches()` 시그니처를 확장한다.

**Step 1: Write the failing test**

```python
class TestInsertPatchWithLostInfo:
    def test_insert_patch_applies_lost_info(self):
        from reverse_sync.patch_builder import build_patches
        from reverse_sync.block_diff import BlockChange
        from reverse_sync.mapping_recorder import BlockMapping
        from reverse_sync.mdx_block_parser import MdxBlock
        from reverse_sync.sidecar import SidecarEntry

        # added 블록 (emoticon 포함)
        new_block = MdxBlock(type='paragraph', content='Check ✔️ done',
                             line_start=0, line_end=1)
        change = BlockChange(index=0, change_type='added',
                             old_block=None, new_block=new_block)

        anchor_block = MdxBlock(type='heading', content='## Title',
                                line_start=0, line_end=1)
        mappings = [BlockMapping(block_id='h1', type='heading',
                                 xhtml_xpath='h2[1]', xhtml_text='<h2>Title</h2>',
                                 xhtml_plain_text='Title', children=[])]

        sidecar_entry = SidecarEntry(xhtml_xpath='h2[1]', xhtml_type='heading', mdx_blocks=[0])
        mdx_to_sidecar = {0: sidecar_entry}
        xpath_to_mapping = {'h2[1]': mappings[0]}
        alignment = {0: 0}

        page_lost_info = {
            'emoticons': [{
                'name': 'tick', 'shortname': ':check_mark:',
                'emoji_id': '', 'fallback': ':check_mark:',
                'raw': '<ac:emoticon ac:name="tick"/>',
            }],
        }

        patches = build_patches(
            [change], [anchor_block], [anchor_block, new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            alignment, page_lost_info=page_lost_info)

        assert len(patches) == 1
        assert patches[0]['action'] == 'insert'
        assert '<ac:emoticon ac:name="tick"/>' in patches[0]['new_element_xhtml']
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py::TestInsertPatchWithLostInfo -v`
Expected: FAIL — `TypeError: build_patches() got an unexpected keyword argument 'page_lost_info'`

**Step 3: Write minimal implementation**

`bin/reverse_sync/patch_builder.py` 수정:

1. import 추가:
```python
from reverse_sync.lost_info_patcher import apply_lost_info
```

2. `build_patches()` 시그니처에 `page_lost_info` 추가 (line 40-48):
```python
def build_patches(
    changes: List[BlockChange],
    original_blocks: List[MdxBlock],
    improved_blocks: List[MdxBlock],
    mappings: List[BlockMapping],
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
    alignment: Optional[Dict[int, int]] = None,
    page_lost_info: Optional[dict] = None,
) -> List[Dict[str, str]]:
```

3. `_build_insert_patch()` 호출에 `page_lost_info` 전달 (line 84-87):
```python
        if change.change_type == 'added':
            patch = _build_insert_patch(
                change, improved_blocks, alignment,
                mdx_to_sidecar, xpath_to_mapping,
                page_lost_info=page_lost_info)
```

4. `_build_insert_patch()` 시그니처와 구현 수정 (line 502-522):
```python
def _build_insert_patch(
    change: BlockChange,
    improved_blocks: List[MdxBlock],
    alignment: Optional[Dict[int, int]],
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
    page_lost_info: Optional[dict] = None,
) -> Optional[Dict[str, str]]:
    new_block = change.new_block
    if new_block.type in NON_CONTENT_TYPES:
        return None

    after_xpath = _find_insert_anchor(
        change.index, alignment, mdx_to_sidecar, xpath_to_mapping)
    new_xhtml = mdx_block_to_xhtml_element(new_block)

    # L4: lost_info 적용
    if page_lost_info:
        new_xhtml = apply_lost_info(new_xhtml, page_lost_info)

    return {
        'action': 'insert',
        'after_xpath': after_xpath,
        'new_element_xhtml': new_xhtml,
    }
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_lost_info_patcher.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add bin/reverse_sync/patch_builder.py tests/test_lost_info_patcher.py
git commit -m "confluence-mdx: reverse sync insert 경로에 lost_info 패칭 통합"
```

---

## Task 9: reverse_sync_cli.py에서 lost_info 로드 및 전달

**Files:**
- Modify: `bin/reverse_sync_cli.py` (line 224-245)

**Step 1: 구현**

`reverse_sync_cli.py`의 `run_verify()` 함수에서 mapping.yaml 로드 후 lost_info를 추출하여 `build_patches()`에 전달:

```python
# Step 3.5 부근, sidecar_data 로드 후:
    page_lost_info = sidecar_data.get('lost_info', {})

# Step 4: build_patches 호출에 page_lost_info 추가:
    patches = build_patches(changes, original_blocks, improved_blocks,
                            original_mappings, mdx_to_sidecar, xpath_to_mapping,
                            alignment, page_lost_info=page_lost_info)
```

**Step 2: Run full test suite**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/ -v --tb=short`
Expected: All existing tests PASS

**Step 3: Commit**

```bash
git add bin/reverse_sync_cli.py
git commit -m "confluence-mdx: reverse_sync_cli에서 lost_info 로드 및 전달"
```

---

## Task 10: 전체 회귀 검증

**Files:** 없음 (검증만)

**Step 1: 전체 테스트 실행**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/ -v --tb=short`
Expected: 모든 테스트 PASS

**Step 2: byte-equal 검증 (CI gate)**

Run: `cd /Users/jk/workspace/querypie-docs-translation-1/confluence-mdx && python -m pytest tests/test_byte_verify.py -v`
Expected: 21/21 PASS (splice 경로에 lost_info가 적용되더라도, 변경이 없는 블록은 hash 일치 → 원본 fragment 사용이므로 byte-equal 유지)

**Step 3: Commit (필요 시)**

회귀 수정이 필요하면 여기서 수정 후 커밋.
