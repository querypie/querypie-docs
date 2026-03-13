"""XHTML Normalizer — 공용 XHTML 정규화 및 plain-text 추출 유틸리티.

reverse-sync 재구성 파이프라인의 공용 helper 모듈.
BeautifulSoup 기반으로 fragment 비교, plain-text 추출, xpath 기반 fragment 추출을 제공한다.
"""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag


# ---------------------------------------------------------------------------
# Ignored attributes — 비교 시 무시하는 Confluence 메타데이터 속성
# ---------------------------------------------------------------------------

IGNORED_ATTRIBUTES: frozenset[str] = frozenset({
    "ac:macro-id",
    "ac:local-id",
    "local-id",
    "ac:schema-version",
    "ri:version-at-save",
    "ac:original-height",
    "ac:original-width",
    "ac:custom-width",
    "ac:alt",
    "ac:layout",
    "data-table-width",
    "data-layout",
    "data-highlight-colour",
    "data-card-appearance",
    "ac:breakout-mode",
    "ac:breakout-width",
    "ri:space-key",
    "style",
    "class",
})


# ---------------------------------------------------------------------------
# Plain-text extraction
# ---------------------------------------------------------------------------

def extract_plain_text(fragment: str) -> str:
    """XHTML fragment에서 plain text를 추출한다.

    ac:plain-text-body(코드 블록 본문)는 제외하고,
    ac:emoticon의 fallback 텍스트는 포함한다.

    이 함수의 출력은 reconstruction에서 anchor offset 좌표의 기준이 된다.
    """
    soup = BeautifulSoup(fragment, "html.parser")
    return _extract_text_from_element(soup)


def _extract_text_from_element(element) -> str:
    """재귀적으로 텍스트를 추출한다."""
    parts: list[str] = []
    for child in element.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            # 코드 블록 본문은 제외
            if child.name == "ac:plain-text-body":
                continue
            # emoticon은 fallback 텍스트 사용
            if child.name == "ac:emoticon":
                fallback = child.get("ac:emoji-fallback", "")
                if fallback:
                    parts.append(fallback)
                continue
            # ac:image, ac:link 등 preservation unit은 텍스트 없음 (anchor로 처리)
            if child.name in ("ac:image", "ac:link"):
                continue
            parts.append(_extract_text_from_element(child))
    return "".join(parts)


# ---------------------------------------------------------------------------
# Fragment normalization
# ---------------------------------------------------------------------------

def normalize_fragment(fragment: str, strip_ignored_attrs: bool = True) -> str:
    """XHTML fragment를 비교 가능한 정규화된 형태로 변환한다.

    - layout section unwrap
    - non-reversible macro 제거
    - decoration unwrap
    - ignored attribute 제거 (선택)
    - BeautifulSoup prettify로 노드별 줄바꿈
    """
    soup = BeautifulSoup(fragment, "html.parser")
    _strip_layout_sections(soup)
    _strip_nonreversible_macros(soup)
    _strip_decorations(soup)
    if strip_ignored_attrs:
        _strip_ignored_attributes(soup)
    return soup.prettify(formatter="minimal").strip()


def _strip_layout_sections(soup: BeautifulSoup) -> None:
    for tag_name in ("ac:layout", "ac:layout-section", "ac:layout-cell"):
        for tag in soup.find_all(tag_name):
            tag.unwrap()


def _strip_nonreversible_macros(soup: BeautifulSoup) -> None:
    for macro in soup.find_all("ac:structured-macro"):
        if macro.get("ac:name") in {"toc", "view-file"}:
            macro.decompose()


def _strip_decorations(soup: BeautifulSoup) -> None:
    for tag_name in ("ac:adf-mark", "ac:inline-comment-marker"):
        for tag in soup.find_all(tag_name):
            tag.unwrap()
    for colgroup in soup.find_all("colgroup"):
        colgroup.decompose()


def _strip_ignored_attributes(
    soup: BeautifulSoup,
    extra: Optional[frozenset[str]] = None,
) -> None:
    ignored = IGNORED_ATTRIBUTES | extra if extra else IGNORED_ATTRIBUTES
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr in ignored:
                del tag.attrs[attr]


# ---------------------------------------------------------------------------
# Fragment extraction by XPath
# ---------------------------------------------------------------------------

def extract_fragment_by_xpath(page_xhtml: str, xpath: str) -> Optional[str]:
    """page XHTML에서 간이 XPath로 요소를 찾아 outerHTML을 반환한다.

    xpath 형식: "p[1]", "ul[2]", "macro-info[1]/p[1]"
    """
    soup = BeautifulSoup(page_xhtml, "html.parser")
    element = _find_element_by_xpath(soup, xpath)
    if element is None:
        return None
    return str(element)


def _find_element_by_xpath(soup, xpath: str):
    """간이 XPath로 요소를 찾는다."""
    parts = xpath.split("/")
    if len(parts) == 1:
        return _find_element_by_simple_xpath(soup, xpath)

    current = _find_element_by_simple_xpath(soup, parts[0])
    if current is None:
        return None

    for part in parts[1:]:
        container = _find_content_container(current)
        if container is None:
            if ":" in (current.name or ""):
                return None
            container = current
        current = _find_element_by_simple_xpath(container, part)
        if current is None:
            return None

    return current


_XPATH_PATTERN = re.compile(r"([a-z0-9:-]+)\[(\d+)\]")


def _find_element_by_simple_xpath(parent, xpath: str):
    """단일 XPath 파트로 요소를 찾는다."""
    match = _XPATH_PATTERN.match(xpath)
    if not match:
        return None
    tag_name = match.group(1)
    index = int(match.group(2))  # 1-based

    macro_name = None
    if tag_name.startswith("macro-"):
        macro_name = tag_name[len("macro-"):]

    count = 0
    for child in _iter_block_children(parent):
        if not isinstance(child, Tag):
            continue
        if macro_name:
            if child.name == "ac:structured-macro" and child.get("ac:name") == macro_name:
                count += 1
                if count == index:
                    return child
        elif child.name == tag_name:
            count += 1
            if count == index:
                return child
    return None


def _iter_block_children(parent):
    """블록 레벨 자식을 순회한다. ac:layout은 cell 내부로 진입한다."""
    for child in parent.children:
        if isinstance(child, Tag) and child.name == "ac:layout":
            for section in child.find_all("ac:layout-section", recursive=False):
                for cell in section.find_all("ac:layout-cell", recursive=False):
                    yield from cell.children
        else:
            yield child


def _find_content_container(parent: Tag):
    """복합 xpath의 부모에서 콘텐츠 컨테이너를 찾는다."""
    rich_body = parent.find("ac:rich-text-body")
    if rich_body is not None:
        return rich_body
    node = parent.find("ac:adf-node")
    if node is not None:
        content = node.find("ac:adf-content")
        if content is not None:
            return content
    return None
