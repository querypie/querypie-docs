# Plan: MDX 내부 링크 → `<ac:link>` 변환 구현

## Context

MDX→XHTML 변환기에서 내부 링크(`[text](relative/path)`)를 Confluence `<ac:link>` 요소로 변환해야 한다.

**현재 동작**: 모든 MDX 링크가 `<a href="...">text</a>`로 변환됨 (`inline.py:31`)
**목표 동작**: `var/pages.yaml` 기반으로 상대 경로를 페이지 제목으로 해석하여 `<ac:link><ri:page ri:content-title="제목" /><ac:link-body>text</ac:link-body></ac:link>` 생성

**배경**:
- Forward 변환기(`converter/context.py`)는 `PAGES_BY_TITLE` + `calculate_relative_path()`로 내부 링크를 상대 경로로 변환
- Reverse 방향(이번 구현)은 반대로 상대 경로 → 페이지 제목 역매핑이 필요
- `var/pages.yaml`에 293개 페이지 정보 (page_id, title_orig, path 배열)
- 21개 testcase 중 12개 이상에 내부 링크 포함, 8개가 P1(internal_link_unresolved)

## 변경 대상 파일

| 파일 | 변경 유형 |
|------|----------|
| `bin/mdx_to_storage/link_resolver.py` | **신규 생성** |
| `bin/mdx_to_storage/inline.py` | 수정 |
| `bin/mdx_to_storage/emitter.py` | 수정 |
| `bin/mdx_to_storage/__init__.py` | 수정 |
| `bin/reverse_sync/mdx_to_storage_xhtml_verify.py` | 수정 |
| `bin/mdx_to_storage_xhtml_verify_cli.py` | 수정 |
| `tests/test_mdx_to_storage/test_link_resolver.py` | **신규 생성** |
| `tests/test_mdx_to_storage/test_inline.py` | 수정 |
| `tests/test_mdx_to_storage/test_emitter.py` | 수정 |
| `tests/test_mdx_to_storage_xhtml_verify.py` | 수정 |

## 구현 상세

### Step 1: `link_resolver.py` 신규 모듈 생성

**파일**: `bin/mdx_to_storage/link_resolver.py`

```python
"""Resolve MDX relative links to Confluence <ac:link> elements."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PageEntry:
    page_id: str
    title_orig: str
    path: list[str] = field(default_factory=list)


class LinkResolver:
    """Map relative MDX paths to Confluence page titles using pages.yaml data."""

    def __init__(self, pages: list[PageEntry]) -> None:
        self._by_path: dict[tuple[str, ...], PageEntry] = {
            tuple(p.path): p for p in pages
        }
        self._by_id: dict[str, PageEntry] = {p.page_id: p for p in pages}
        self._current_page: PageEntry | None = None

    def set_current_page(self, page_id: str) -> None:
        self._current_page = self._by_id.get(page_id)

    def resolve(self, href: str, text: str) -> str | None:
        """상대 경로 링크를 <ac:link> XHTML로 변환. 외부 링크는 None 반환."""
        # 1. 외부/앵커 링크 → None
        if href.startswith(("http://", "https://", "#")):
            return None
        # 2. current_page 미설정 → None
        if self._current_page is None:
            return None
        # 3. 상대 → 절대 경로 변환
        current_dir = posixpath.join("/", *self._current_page.path[:-1])
        abs_path = posixpath.normpath(posixpath.join(current_dir, href))
        path_parts = tuple(abs_path.strip("/").split("/"))
        # 4. 경로 → PageEntry 매핑
        page = self._by_path.get(path_parts)
        if page is None:
            return None
        return format_ac_link(page.title_orig, text)


def format_ac_link(title: str, link_text: str) -> str:
    return (
        f'<ac:link><ri:page ri:content-title="{title}" />'
        f"<ac:link-body>{link_text}</ac:link-body></ac:link>"
    )


def load_pages_yaml(yaml_path: Path) -> list[PageEntry]:
    with open(yaml_path, encoding="utf-8") as f:
        data: list[dict[str, Any]] = yaml.safe_load(f)
    return [
        PageEntry(
            page_id=str(entry.get("page_id", "")),
            title_orig=str(entry.get("title_orig", "")),
            path=entry.get("path", []),
        )
        for entry in data
    ]
```

### Step 2: `inline.py` 수정

**변경 요약**: `convert_inline()`, `convert_heading_inline()`에 `link_resolver` 파라미터 추가, `_resolve_links()` 헬퍼 도입

**구체적 변경**:

1. `from __future__ import annotations` 추가
2. TYPE_CHECKING import 추가:
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from .link_resolver import LinkResolver
   ```
3. `_resolve_links()` 함수 추가 (기존 `_LINK_RE.sub(...)` 정규식 로직을 대체):
   ```python
   def _resolve_links(text: str, link_resolver: LinkResolver | None) -> str:
       def _replace(match: re.Match[str]) -> str:
           link_text, href = match.group(1), match.group(2)
           if link_resolver:
               resolved = link_resolver.resolve(href, link_text)
               if resolved:
                   return resolved
           return f'<a href="{href}">{link_text}</a>'
       return _LINK_RE.sub(_replace, text)
   ```
4. `convert_inline()` 시그니처 변경:
   - 기존: `def convert_inline(text: str) -> str:`
   - 변경: `def convert_inline(text: str, link_resolver: LinkResolver | None = None) -> str:`
   - line 31 `_LINK_RE.sub(r'<a href="\2">\1</a>', converted)` → `_resolve_links(converted, link_resolver)`
5. `convert_heading_inline()` 시그니처 변경:
   - 기존: `def convert_heading_inline(text: str) -> str:`
   - 변경: `def convert_heading_inline(text: str, link_resolver: LinkResolver | None = None) -> str:`
   - line 56 `_LINK_RE.sub(r'<a href="\2">\1</a>', converted)` → `_resolve_links(converted, link_resolver)`

### Step 3: `emitter.py` 수정

**변경 요약**: `emit_document()`에 `link_resolver` 파라미터 추가, context dict를 통해 내부 함수들에 전달

**구체적 변경**:

1. `emit_document()` 시그니처 변경 (line 93):
   ```python
   # 기존
   def emit_document(blocks: list[Block]) -> str:
       context: dict[str, str] = {"frontmatter_title": ""}
   # 변경
   def emit_document(blocks: list[Block], link_resolver=None) -> str:
       context: dict = {"frontmatter_title": "", "link_resolver": link_resolver}
   ```
2. `emit_block()` 내 `convert_inline()` / `convert_heading_inline()` 호출부에 `link_resolver` 전달.
   context에서 꺼내는 헬퍼 변수를 사용:
   ```python
   lr = context.get("link_resolver")
   ```
   수정 대상 10곳:

   | 위치 (line) | 기존 코드 | 변경 코드 |
   |------------|----------|----------|
   | 52 (heading) | `convert_heading_inline(heading_text)` | `convert_heading_inline(heading_text, link_resolver=lr)` |
   | 56 (paragraph) | `convert_inline(paragraph_text)` | `convert_inline(paragraph_text, link_resolver=lr)` |
   | 188 (list item) | `convert_inline(node.text)` | `convert_inline(node.text, link_resolver=lr)` |
   | 244 (figure caption) | `convert_inline(caption)` | `convert_inline(caption, link_resolver=lr)` |
   | 252 (table fallback) | `convert_inline(content.strip())` | `convert_inline(content.strip(), link_resolver=lr)` |
   | 259 (table header) | `convert_inline(cell)` | `convert_inline(cell, link_resolver=lr)` |
   | 263 (table body) | `convert_inline(cell)` | `convert_inline(cell, link_resolver=lr)` |
   | 286 (html table cell) | `convert_inline(inner.strip())` | `convert_inline(inner.strip(), link_resolver=lr)` |
   | 317 (blockquote) | `convert_inline(text)` | `convert_inline(text, link_resolver=lr)` |

   **주의**: line 188, 244, 252, 259, 263, 286, 317은 private 함수 내부에 있으므로 해당 함수들에도 `link_resolver` 파라미터를 전달하는 리팩토링이 필요하다.

   **접근 방식**: 각 private 함수에 개별 파라미터를 추가하는 대신, `context` dict를 내부 함수에 전달하는 방식을 채택한다:

   - `_render_list_item(node)` → `_render_list_item(node, context)` (line 186-188)
   - `_render_list_nodes(nodes)` → `_render_list_nodes(nodes, context)` (line 170-183)
   - `_emit_single_depth_list(content)` → `_emit_single_depth_list(content, context)` (line 120-126)
   - `_emit_figure(block)` → `_emit_figure(block, context)` (line 228-246)
   - `_emit_markdown_table(content)` → `_emit_markdown_table(content, context)` (line 249-266)
   - `_emit_html_block(content)` → `_emit_html_block(content, context)` (line 274-288)
   - `_emit_blockquote(content)` → `_emit_blockquote(content, context)` (line 291-318)

   `emit_block()` 내 호출부도 함께 수정 (line 70, 76, 82, 85, 88):
   ```python
   # 기존
   return _emit_single_depth_list(block.content)
   # 변경
   return _emit_single_depth_list(block.content, context)
   ```

### Step 4: verify 파이프라인 수정

#### 4a. `bin/reverse_sync/mdx_to_storage_xhtml_verify.py`

1. `mdx_to_storage_xhtml_fragment()` (line 67-70):
   ```python
   # 기존
   def mdx_to_storage_xhtml_fragment(mdx_text: str) -> str:
       blocks = parse_mdx(mdx_text)
       return emit_document(blocks)
   # 변경
   def mdx_to_storage_xhtml_fragment(mdx_text: str, link_resolver=None) -> str:
       blocks = parse_mdx(mdx_text)
       return emit_document(blocks, link_resolver=link_resolver)
   ```

2. `verify_expected_mdx_against_page_xhtml()` (line 82-98):
   ```python
   # 기존
   def verify_expected_mdx_against_page_xhtml(
       expected_mdx: str, page_xhtml: str
   ) -> tuple[bool, str, str]:
       generated = mdx_to_storage_xhtml_fragment(expected_mdx)
   # 변경
   def verify_expected_mdx_against_page_xhtml(
       expected_mdx: str, page_xhtml: str, link_resolver=None
   ) -> tuple[bool, str, str]:
       generated = mdx_to_storage_xhtml_fragment(expected_mdx, link_resolver=link_resolver)
   ```

3. `verify_testcase_dir()` (line 140-152):
   ```python
   # 기존
   def verify_testcase_dir(case_dir: Path) -> CaseVerification:
       expected_mdx = (case_dir / "expected.mdx").read_text(encoding="utf-8")
       page_xhtml = (case_dir / "page.xhtml").read_text(encoding="utf-8")
       passed, generated, diff_report = verify_expected_mdx_against_page_xhtml(
           expected_mdx, page_xhtml
       )
   # 변경
   def verify_testcase_dir(case_dir: Path, link_resolver=None) -> CaseVerification:
       if link_resolver:
           link_resolver.set_current_page(case_dir.name)
       expected_mdx = (case_dir / "expected.mdx").read_text(encoding="utf-8")
       page_xhtml = (case_dir / "page.xhtml").read_text(encoding="utf-8")
       passed, generated, diff_report = verify_expected_mdx_against_page_xhtml(
           expected_mdx, page_xhtml, link_resolver=link_resolver
       )
   ```

#### 4b. `bin/mdx_to_storage_xhtml_verify_cli.py`

1. `_build_parser()`에 인자 추가:
   ```python
   parser.add_argument(
       "--pages-yaml", type=Path,
       help="pages.yaml path for internal link resolution",
   )
   ```

2. `main()`에서 resolver 생성 (line 112 부근):
   ```python
   link_resolver = None
   if args.pages_yaml:
       from mdx_to_storage.link_resolver import LinkResolver, load_pages_yaml
       pages = load_pages_yaml(args.pages_yaml)
       link_resolver = LinkResolver(pages)

   results = [verify_testcase_dir(case_dir, link_resolver=link_resolver) for case_dir in case_dirs]
   ```

### Step 5: `__init__.py` 업데이트

```python
from .emitter import emit_block, emit_document
from .inline import convert_heading_inline, convert_inline
from .link_resolver import LinkResolver, PageEntry, load_pages_yaml
from .parser import Block, parse_mdx

__all__ = [
    "Block",
    "LinkResolver",
    "PageEntry",
    "convert_heading_inline",
    "convert_inline",
    "emit_block",
    "emit_document",
    "load_pages_yaml",
    "parse_mdx",
]
```

## 테스트 계획

### 신규: `tests/test_mdx_to_storage/test_link_resolver.py` (~10개 테스트)

| 테스트 | 설명 |
|--------|------|
| `test_format_ac_link` | 출력 형식 검증 |
| `test_load_pages_yaml` | YAML 로딩 → PageEntry 리스트 (tmp_path에 미니 yaml 작성) |
| `test_resolve_external_https_returns_none` | `https://example.com` → None |
| `test_resolve_external_http_returns_none` | `http://example.com` → None |
| `test_resolve_anchor_returns_none` | `#section` → None |
| `test_resolve_link_error_returns_none` | `#link-error` → None |
| `test_resolve_no_current_page_returns_none` | `set_current_page` 미호출 시 None |
| `test_resolve_internal_link_same_level` | `../sibling-page` → ac:link |
| `test_resolve_internal_link_deeper` | `sub/page` → ac:link |
| `test_resolve_internal_link_multi_level_up` | `../../other/page` → ac:link |
| `test_resolve_unknown_path_returns_none` | 존재하지 않는 경로 → None |
| `test_set_current_page_unknown_id` | 없는 page_id → resolve returns None |

### 기존 테스트 수정

**`test_inline.py`** (~3개 추가):
- `test_convert_inline_with_link_resolver`: resolver가 ac:link로 변환하는지 확인
- `test_convert_inline_with_link_resolver_fallback`: resolver가 None 반환하면 `<a>` 폴백
- `test_convert_heading_inline_with_link_resolver`: heading에서도 resolver 동작 확인

**`test_emitter.py`** (~2개 추가):
- `test_emit_document_with_link_resolver`: 전체 문서에서 내부 링크 → ac:link 변환
- `test_emit_document_without_link_resolver_unchanged`: `link_resolver=None`이면 기존 동작 유지

**`test_mdx_to_storage_xhtml_verify.py`** (~2개 추가):
- `test_mdx_to_storage_xhtml_fragment_with_link_resolver`: fragment 생성 시 resolver 적용
- `test_verify_testcase_dir_with_link_resolver`: resolver 유무에 따른 verify 결과 차이

## 검증 방법

1. **단위 테스트**: `pytest tests/test_mdx_to_storage/ -v`
2. **Batch verify (resolver 없이, 기존 동작 확인)**:
   ```bash
   python bin/mdx_to_storage_xhtml_verify_cli.py --show-analysis
   ```
3. **Batch verify (resolver 포함)**:
   ```bash
   python bin/mdx_to_storage_xhtml_verify_cli.py --pages-yaml var/pages.yaml --show-analysis
   ```
4. 8개 P1 `internal_link_unresolved` 케이스 중 대부분이 해소되는지 확인

## 예상 결과

- P1 `internal_link_unresolved` 8건 → 대부분 해소 (pages.yaml에 없는 제목만 잔존)
- `#link-error` 링크는 resolver가 경로 해석 불가 → 기존 `<a>` 폴백 유지
- 기존 테스트 전부 통과 (`link_resolver=None`이 기본값이므로 하위호환)
