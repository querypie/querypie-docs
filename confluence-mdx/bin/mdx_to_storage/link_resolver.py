"""Resolve internal markdown links to Confluence storage link macros."""

from __future__ import annotations

from dataclasses import dataclass, field
import posixpath
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote

import yaml


_EXTERNAL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


@dataclass
class PageEntry:
    page_id: str
    title_orig: str
    path: list[str] = field(default_factory=list)


def load_pages_yaml(yaml_path: Path) -> list[PageEntry]:
    if not yaml_path.exists():
        return []

    loaded: Any = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        return []

    pages: list[PageEntry] = []
    for row in loaded:
        if not isinstance(row, dict):
            continue
        path_value = row.get("path")
        if not isinstance(path_value, list):
            continue
        title_orig = str(row.get("title_orig") or row.get("title") or "").strip()
        if not title_orig:
            continue
        pages.append(
            PageEntry(
                page_id=str(row.get("page_id") or ""),
                title_orig=title_orig,
                path=[str(p).strip("/") for p in path_value if str(p).strip("/")],
            )
        )
    return pages


class LinkResolver:
    """Resolve markdown href to Confluence page title using pages.yaml."""

    def __init__(self, pages: Optional[list[PageEntry] | Path] = None) -> None:
        if pages is None:
            pages = Path(__file__).resolve().parents[2] / "var" / "pages.yaml"
        if isinstance(pages, Path):
            pages = load_pages_yaml(pages)

        self._by_id: dict[str, PageEntry] = {}
        self._current_page: PageEntry | None = None
        self._path_to_title: dict[str, str] = {}
        self._titles: set[str] = set()
        self._load_pages(pages)

    def has_pages(self) -> bool:
        return bool(self._path_to_title)

    def set_current_page(self, page_id: str) -> None:
        self._current_page = self._by_id.get(str(page_id))

    def resolve(self, href: str, link_text: str = "") -> tuple[Optional[str], Optional[str]]:
        """Resolve href to (content_title, anchor) or (None, None)."""
        raw_href = href.strip()
        if not raw_href:
            return None, None
        if _EXTERNAL_SCHEME_RE.match(raw_href):
            return None, None
        if raw_href.startswith("#"):
            return None, None

        path_part, anchor = self._split_anchor(raw_href)
        normalized_path = self._normalize_path(path_part)

        current_page_path = self._resolve_from_current_page(path_part)
        if current_page_path:
            title = self._path_to_title.get(current_page_path)
            if title:
                return title, anchor

        if not normalized_path and link_text:
            title = self._resolve_by_title(link_text)
            if title:
                return title, anchor

        title = self._path_to_title.get(normalized_path)
        if title:
            return title, anchor

        if link_text:
            title = self._resolve_by_title(link_text)
            if title:
                return title, anchor
        return None, None

    def _load_pages(self, pages: list[PageEntry]) -> None:
        for page in pages:
            normalized_path = self._normalize_path("/".join(page.path))
            if normalized_path:
                self._path_to_title[normalized_path] = page.title_orig
            self._titles.add(page.title_orig)
            if page.page_id:
                self._by_id[page.page_id] = page

    @staticmethod
    def _split_anchor(href: str) -> tuple[str, Optional[str]]:
        if "#" not in href:
            return href, None
        path_part, anchor = href.split("#", 1)
        return path_part, anchor if anchor else None

    @staticmethod
    def _normalize_path(path: str) -> str:
        raw = unquote(path).strip()
        raw = raw.lstrip("/")
        parts: list[str] = []
        for token in raw.split("/"):
            segment = token.strip()
            if not segment or segment == ".":
                continue
            if segment == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(segment)
        return "/".join(parts)

    def _resolve_by_title(self, link_text: str) -> Optional[str]:
        title_candidate = link_text.strip()
        if not title_candidate:
            return None
        return title_candidate if title_candidate in self._titles else None

    def _resolve_from_current_page(self, path_part: str) -> Optional[str]:
        if self._current_page is None:
            return None
        if not path_part or path_part.startswith("/"):
            return None
        if not (path_part.startswith(".") or path_part.startswith("..")):
            return None

        current_dir = "/" + "/".join(self._current_page.path[:-1])
        joined = posixpath.normpath(posixpath.join(current_dir, path_part))
        normalized = self._normalize_path(joined)
        return normalized or None
