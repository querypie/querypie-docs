"""Shared XHTML normalization and fragment helpers for reverse sync."""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from xhtml_beautify_diff import beautify_xhtml


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

_CALLOUT_MACRO_NAMES = frozenset({"tip", "info", "note", "warning", "panel"})
_XPATH_SEGMENT_RE = re.compile(r"^(?P<name>.+)\[(?P<index>\d+)\]$")


def extract_plain_text(fragment: str) -> str:
    """Extract plain text for reconstruction coordinates.

    Rules:
    - preserve ordinary text spacing
    - exclude preservation-unit tags such as `ac:image` and `ac:link`
    - exclude `ac:plain-text-body`
    - include `ac:emoticon` fallback text
    - join container child blocks with single spaces
    """
    soup = BeautifulSoup(fragment, "html.parser")
    _strip_layout_sections(soup)
    _strip_nonreversible_macros(soup)
    _strip_decorations(soup)

    root = _find_first_meaningful_node(soup)
    if root is None:
        return ""
    if isinstance(root, NavigableString):
        return str(root)

    content_container = _find_content_container(root)
    if content_container is not None:
        return _extract_text_from_container(content_container)
    return _extract_text_from_element(root)


def normalize_fragment(
    fragment: str,
    ignore_ri_filename: bool = False,
    strip_ignored_attrs: bool = True,
) -> str:
    """Normalize an XHTML page or fragment for comparison."""
    soup = BeautifulSoup(fragment, "html.parser")
    _strip_layout_sections(soup)
    _strip_nonreversible_macros(soup)
    _strip_decorations(soup)
    if strip_ignored_attrs:
        _strip_ignored_attributes(soup, ignore_ri_filename=ignore_ri_filename)
    return beautify_xhtml(str(soup)).strip()


def extract_fragment_by_xpath(page_xhtml: str, xpath: str) -> Optional[str]:
    """Extract an outerHTML fragment using the simplified mapping XPath."""
    soup = BeautifulSoup(page_xhtml, "html.parser")
    current: BeautifulSoup | Tag | None = soup
    for segment in xpath.split("/"):
        if current is None:
            return None
        tag_name, target_index = _parse_xpath_segment(segment)
        current = _find_xpath_child(current, tag_name, target_index)
    return str(current) if current is not None else None


def _extract_text_from_element(element) -> str:
    parts: list[str] = []
    for child in element.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            if child.name == "ac:plain-text-body":
                continue
            if child.name == "ac:emoticon":
                fallback = child.get("ac:emoji-fallback", "")
                if fallback:
                    parts.append(fallback)
                continue
            if child.name in ("ac:image", "ac:link"):
                continue
            parts.append(_extract_text_from_element(child))
    return "".join(parts)


def _extract_text_from_container(container: Tag) -> str:
    parts = []
    for child in container.children:
        if isinstance(child, NavigableString):
            text = _collapse_ws(str(child))
            if text:
                parts.append(text)
        elif isinstance(child, Tag):
            text = _collapse_ws(_extract_text_from_element(child))
            if text:
                parts.append(text)
    return " ".join(parts)


def _find_first_meaningful_node(soup: BeautifulSoup) -> Tag | NavigableString | None:
    for child in _iter_block_children(soup):
        if isinstance(child, Tag):
            return child
        if isinstance(child, NavigableString) and child.strip():
            return child
    return None


def _find_xpath_child(
    parent: BeautifulSoup | Tag,
    tag_name: str,
    target_index: int,
) -> Tag | None:
    count = 0
    for child in _iter_xpath_children(parent):
        if _segment_matches(child, tag_name):
            count += 1
            if count == target_index:
                return child
    return None


def _iter_xpath_children(parent: BeautifulSoup | Tag):
    if isinstance(parent, BeautifulSoup):
        yield from (child for child in _iter_block_children(parent) if isinstance(child, Tag))
        return

    content_container = _find_content_container(parent)
    if content_container is not None:
        yield from (child for child in content_container.children if isinstance(child, Tag))
        return

    yield from (child for child in parent.children if isinstance(child, Tag))


def _segment_matches(tag: Tag, segment_name: str) -> bool:
    if segment_name.startswith("macro-"):
        return tag.name == "ac:structured-macro" and tag.get("ac:name", "") == segment_name[6:]
    return tag.name == segment_name


def _parse_xpath_segment(segment: str) -> tuple[str, int]:
    match = _XPATH_SEGMENT_RE.match(segment)
    if not match:
        raise ValueError(f"invalid xpath segment: {segment}")
    return match.group("name"), int(match.group("index"))


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_ignored_attributes(
    soup: BeautifulSoup,
    ignore_ri_filename: bool = False,
    extra: Optional[frozenset[str]] = None,
) -> None:
    ignored = set(IGNORED_ATTRIBUTES)
    if ignore_ri_filename:
        ignored.add("ri:filename")
    if extra:
        ignored.update(extra)
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr in ignored:
                del tag.attrs[attr]


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
    for p in soup.find_all("p"):
        if not p.get_text(strip=True) and not p.find_all(True):
            p.decompose()


def _iter_block_children(parent):
    for child in parent.children:
        if isinstance(child, Tag) and child.name == "ac:layout":
            for section in child.find_all("ac:layout-section", recursive=False):
                for cell in section.find_all("ac:layout-cell", recursive=False):
                    yield from cell.children
        else:
            yield child


def _get_adf_panel_type(element: Tag) -> str:
    node = element.find("ac:adf-node")
    if node is None:
        return ""
    attr = node.find("ac:adf-attribute", attrs={"key": "panel-type"})
    if attr is None:
        return ""
    return attr.get_text().strip()


def _find_content_container(parent: Tag) -> Tag | None:
    if parent.name == "ac:structured-macro" and parent.get("ac:name", "") in _CALLOUT_MACRO_NAMES:
        return parent.find("ac:rich-text-body")
    if parent.name == "ac:adf-extension" and _get_adf_panel_type(parent) in _CALLOUT_MACRO_NAMES:
        node = parent.find("ac:adf-node")
        if node is not None:
            return node.find("ac:adf-content")
    return None
