"""Resolve internal markdown links to Confluence storage link macros."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

import yaml


_EXTERNAL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


class LinkResolver:
    """Resolve markdown href to Confluence page title using pages.yaml."""

    def __init__(self, pages_yaml_path: Optional[Path] = None) -> None:
        if pages_yaml_path is None:
            pages_yaml_path = Path(__file__).resolve().parents[2] / "var" / "pages.yaml"
        self._path_to_title: dict[str, str] = {}
        self._titles: set[str] = set()
        self._load_pages_yaml(pages_yaml_path)

    def has_pages(self) -> bool:
        return bool(self._path_to_title)

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

    def _load_pages_yaml(self, pages_yaml_path: Path) -> None:
        if not pages_yaml_path.exists():
            return

        data = yaml.safe_load(pages_yaml_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return

        for row in data:
            if not isinstance(row, dict):
                continue
            path_list = row.get("path")
            if not isinstance(path_list, list) or not path_list:
                continue

            title = (
                str(row.get("title_orig") or row.get("title") or "").strip()
            )
            if not title:
                continue

            normalized_path = self._normalize_path("/".join(str(p) for p in path_list))
            if normalized_path:
                self._path_to_title[normalized_path] = title
            self._titles.add(title)

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
