"""Shared XHTML normalization and fragment helpers for reverse sync."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag

from reverse_sync.mapping_recorder import (
    _CALLOUT_MACRO_NAMES,
    _get_adf_content_body,
    _get_adf_panel_type,
    _get_text_with_emoticons,
    _iter_block_children,
)
from xhtml_beautify_diff import beautify_xhtml


_IGNORED_ATTRIBUTES = {
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
}

_XPATH_SEGMENT_RE = re.compile(r"^(?P<name>.+)\[(?P<index>\d+)\]$")


def normalize_fragment(xhtml: str, ignore_ri_filename: bool = False) -> str:
    """Normalize a page or fragment for structural comparison."""
    soup = BeautifulSoup(xhtml, "html.parser")
    _strip_layout_sections(soup)
    _strip_nonreversible_macros(soup)
    _strip_decorations(soup)
    _strip_ignored_attributes(soup, ignore_ri_filename=ignore_ri_filename)
    return beautify_xhtml(str(soup)).strip()


def extract_plain_text(xhtml: str) -> str:
    """Extract normalized plain text from a fragment using reverse-sync rules."""
    soup = BeautifulSoup(xhtml, "html.parser")
    _strip_layout_sections(soup)
    _strip_nonreversible_macros(soup)
    _strip_decorations(soup)

    root = _find_first_meaningful_node(soup)
    if root is None:
        return ""
    if isinstance(root, NavigableString):
        return _collapse_ws(str(root))
    if root.name == "ac:structured-macro":
        macro_name = root.get("ac:name", "")
        if macro_name == "code":
            body = root.find("ac:plain-text-body")
            return _collapse_ws(body.get_text() if body else "")
        if macro_name in _CALLOUT_MACRO_NAMES:
            rich_body = root.find("ac:rich-text-body")
            return _collapse_ws(_get_text_with_emoticons(rich_body) if rich_body else "")
    if root.name == "ac:adf-extension" and _get_adf_panel_type(root) in _CALLOUT_MACRO_NAMES:
        content_body = _get_adf_content_body(root)
        return _collapse_ws(_get_text_with_emoticons(content_body) if content_body else "")
    return _collapse_ws(_get_text_with_emoticons(root))


def extract_fragment_by_xpath(xhtml: str, xpath: str) -> str:
    """Return the fragment located at the simplified mapping XPath."""
    soup = BeautifulSoup(xhtml, "html.parser")
    current: BeautifulSoup | Tag = soup
    for segment in xpath.split("/"):
        tag_name, target_index = _parse_xpath_segment(segment)
        current = _find_xpath_child(current, tag_name, target_index)
    return str(current)


def _find_first_meaningful_node(soup: BeautifulSoup) -> Tag | NavigableString | None:
    for child in _iter_block_children(soup):
        if isinstance(child, Tag):
            return child
        if isinstance(child, NavigableString) and child.strip():
            return child
    return None


def _find_xpath_child(parent: BeautifulSoup | Tag, tag_name: str, target_index: int) -> Tag:
    matches = []
    for child in _iter_xpath_children(parent):
        if _segment_matches(child, tag_name):
            matches.append(child)
            if len(matches) == target_index:
                return child
    raise KeyError(f"xpath segment not found: {tag_name}[{target_index}]")


def _iter_xpath_children(parent: BeautifulSoup | Tag):
    if isinstance(parent, BeautifulSoup):
        yield from (child for child in _iter_block_children(parent) if isinstance(child, Tag))
        return
    if parent.name == "ac:structured-macro" and parent.get("ac:name", "") in _CALLOUT_MACRO_NAMES:
        rich_body = parent.find("ac:rich-text-body")
        if rich_body is not None:
            yield from (child for child in rich_body.children if isinstance(child, Tag))
        return
    if parent.name == "ac:adf-extension" and _get_adf_panel_type(parent) in _CALLOUT_MACRO_NAMES:
        content_body = _get_adf_content_body(parent)
        if content_body is not None:
            yield from (child for child in content_body.children if isinstance(child, Tag))
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


def _strip_ignored_attributes(soup: BeautifulSoup, ignore_ri_filename: bool = False) -> None:
    ignored_attrs = set(_IGNORED_ATTRIBUTES)
    if ignore_ri_filename:
        ignored_attrs.add("ri:filename")
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr in ignored_attrs:
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
