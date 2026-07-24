"""Resolve internal markdown links to Confluence storage link macros."""

from __future__ import annotations

from dataclasses import dataclass, field
import posixpath
import re
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote

import yaml

# Ensure bin/ is on sys.path for fetch package imports
_BIN_DIR = Path(__file__).resolve().parent.parent  # confluence-mdx/bin/
if str(_BIN_DIR) not in sys.path:
    sys.path.insert(0, str(_BIN_DIR))

from fetch.sync_profiles import SYNC_PROFILES


_EXTERNAL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


@dataclass
class PageEntry:
    page_id: str
    title_orig: str
    path: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LinkResolution:
    """internal link resolution 결과와 fail-closed 상태."""

    status: str
    href: str
    content_title: Optional[str] = None
    anchor: Optional[str] = None
    candidate_page_ids: tuple[str, ...] = ()


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
            var_dir = Path(__file__).resolve().parents[2] / "var"
            default_code = next(iter(SYNC_PROFILES), "qm")
            pages = var_dir / f"pages.{default_code}.yaml"
            if not pages.exists():
                pages = var_dir / "pages.yaml"
        if isinstance(pages, Path):
            pages = load_pages_yaml(pages)

        self._by_id: dict[str, PageEntry] = {}
        self._current_page: PageEntry | None = None
        self._path_to_entries: dict[str, list[PageEntry]] = {}
        self._title_to_entries: dict[str, list[PageEntry]] = {}
        self._load_pages(pages)

    def has_pages(self) -> bool:
        return bool(self._path_to_entries)

    def set_current_page(self, page_id: str) -> None:
        self._current_page = self._by_id.get(str(page_id))

    def resolve(self, href: str, link_text: str = "") -> tuple[Optional[str], Optional[str]]:
        """Resolve href to (content_title, anchor) or (None, None)."""
        resolution = self.resolve_with_evidence(href, link_text=link_text)
        if resolution.status != "resolved":
            return None, None
        return resolution.content_title, resolution.anchor

    def resolve_with_evidence(
        self,
        href: str,
        link_text: str = "",
    ) -> LinkResolution:
        """href를 resolve하고 unresolved/ambiguous를 구분합니다."""
        raw_href = href.strip()
        if not raw_href:
            return LinkResolution("unresolved", raw_href)
        if _EXTERNAL_SCHEME_RE.match(raw_href) or raw_href.startswith("//"):
            return LinkResolution("external", raw_href)
        if raw_href.startswith("#"):
            return LinkResolution("local_anchor", raw_href, anchor=raw_href[1:] or None)

        path_part, anchor = self._split_anchor(raw_href)
        if path_part in {".", "./"} and anchor:
            return LinkResolution(
                "local_anchor",
                raw_href,
                anchor=anchor,
            )
        normalized_path = self._normalize_path(path_part)

        current_page_path = self._resolve_from_current_page(path_part)
        if current_page_path:
            resolution = self._resolution_for_entries(
                raw_href,
                self._path_to_entries.get(current_page_path, []),
                anchor,
            )
            if resolution.status != "unresolved":
                return resolution

        if not normalized_path and link_text:
            resolution = self._resolve_by_title(
                raw_href,
                link_text,
                anchor,
            )
            if resolution.status != "unresolved":
                return resolution

        resolution = self._resolution_for_entries(
            raw_href,
            self._path_to_entries.get(normalized_path, []),
            anchor,
        )
        if resolution.status != "unresolved":
            return resolution

        return LinkResolution("unresolved", raw_href, anchor=anchor)

    def _load_pages(self, pages: list[PageEntry]) -> None:
        for page in pages:
            normalized_path = self._normalize_path("/".join(page.path))
            if normalized_path:
                self._path_to_entries.setdefault(normalized_path, []).append(page)
            self._title_to_entries.setdefault(page.title_orig, []).append(page)
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

    @staticmethod
    def _resolution_for_entries(
        href: str,
        entries: list[PageEntry],
        anchor: Optional[str],
    ) -> LinkResolution:
        if not entries:
            return LinkResolution("unresolved", href, anchor=anchor)
        page_ids = tuple(sorted({entry.page_id for entry in entries}))
        if (
            len(entries) != 1
            or len(page_ids) != 1
            or not page_ids[0]
        ):
            return LinkResolution(
                "ambiguous" if len(entries) > 1 else "unresolved",
                href,
                anchor=anchor,
                candidate_page_ids=page_ids,
            )
        return LinkResolution(
            "resolved",
            href,
            content_title=entries[0].title_orig,
            anchor=anchor,
            candidate_page_ids=page_ids,
        )

    def _resolve_by_title(
        self,
        href: str,
        link_text: str,
        anchor: Optional[str],
    ) -> LinkResolution:
        title_candidate = link_text.strip()
        if not title_candidate:
            return LinkResolution("unresolved", href, anchor=anchor)
        return self._resolution_for_entries(
            href,
            self._title_to_entries.get(title_candidate, []),
            anchor,
        )

    def _resolve_from_current_page(self, path_part: str) -> Optional[str]:
        if self._current_page is None:
            return None
        if not path_part or path_part.startswith("/"):
            return None
        if path_part in {".", "./"}:
            return self._normalize_path("/".join(self._current_page.path))

        current_dir = "/" + "/".join(self._current_page.path[:-1])
        joined = posixpath.normpath(posixpath.join(current_dir, path_part))
        normalized = self._normalize_path(joined)
        return normalized or None
