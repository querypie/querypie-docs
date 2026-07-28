"""Lifecycle management for title-derived public content redirects."""

import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import yaml


REDIRECT_RETENTION_DAYS = 56


class ContentRedirectError(RuntimeError):
    """Raised when the content redirect registry is invalid."""


def _parse_iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ContentRedirectError(f"{field} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ContentRedirectError(
            f"{field} must use YYYY-MM-DD: {value!r}"
        ) from exc
    if parsed.isoformat() != value:
        raise ContentRedirectError(
            f"{field} must use canonical YYYY-MM-DD: {value!r}"
        )
    return parsed


def _validate_route(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("/"):
        raise ContentRedirectError(f"{field} must be a root-relative route")
    if value == "/" or value.endswith("/") or "//" in value:
        raise ContentRedirectError(f"{field} is not a canonical content route: {value!r}")
    if any(part in ("", ".", "..") for part in value.split("/")[1:]):
        raise ContentRedirectError(f"{field} contains an unsafe segment: {value!r}")
    return value


def _validate_redirects(data: Any) -> list[Dict[str, str]]:
    if data is None:
        return []
    if not isinstance(data, list):
        raise ContentRedirectError("Content redirect registry must be a list")

    validated: list[Dict[str, str]] = []
    seen_sources: set[str] = set()
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ContentRedirectError(
                f"Content redirect at index {index} must be a mapping"
            )
        source = _validate_route(item.get("source"), "source")
        destination = _validate_route(item.get("destination"), "destination")
        if source == destination:
            raise ContentRedirectError(
                f"Content redirect source equals destination: {source}"
            )
        if source in seen_sources:
            raise ContentRedirectError(
                f"Duplicate content redirect source: {source}"
            )
        created_on = _parse_iso_date(item.get("created_on"), "created_on")
        expires_on = _parse_iso_date(item.get("expires_on"), "expires_on")
        if expires_on <= created_on:
            raise ContentRedirectError(
                f"expires_on must be later than created_on for {source}"
            )
        seen_sources.add(source)
        validated.append({
            "source": source,
            "destination": destination,
            "created_on": created_on.isoformat(),
            "expires_on": expires_on.isoformat(),
        })
    return validated


def load_content_redirects(path: Path) -> list[Dict[str, str]]:
    """Load and validate the persisted redirect registry."""
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContentRedirectError(
            f"Invalid YAML in content redirect registry {path}: {exc}"
        ) from exc
    return _validate_redirects(data)


def _mdx_routes_by_content_id(
    outputs: Sequence[Mapping[str, str]],
) -> Dict[str, str]:
    routes: Dict[str, str] = {}
    for entry in outputs:
        if entry.get("kind") != "mdx":
            continue
        content_id = str(entry.get("page_id") or "").strip()
        relative_path = entry.get("path")
        if not content_id or not isinstance(relative_path, str):
            raise ContentRedirectError(
                f"Invalid MDX manifest entry: {entry!r}"
            )
        if not relative_path.endswith(".mdx"):
            raise ContentRedirectError(
                f"MDX manifest path must end with .mdx: {relative_path}"
            )
        route = _validate_route(f"/{relative_path[:-4]}", "manifest route")
        if content_id in routes:
            raise ContentRedirectError(
                f"Duplicate MDX output for content ID: {content_id}"
            )
        routes[content_id] = route
    return routes


def reconcile_content_redirects(
    existing: Sequence[Mapping[str, str]],
    previous_outputs: Sequence[Mapping[str, str]],
    current_outputs: Sequence[Mapping[str, str]],
    current_date: date,
) -> list[Dict[str, str]]:
    """Prune expired redirects and apply current content route moves."""
    redirects = [
        dict(item)
        for item in _validate_redirects(list(existing))
        if _parse_iso_date(item["expires_on"], "expires_on") > current_date
    ]
    previous_routes = _mdx_routes_by_content_id(previous_outputs)
    current_routes = _mdx_routes_by_content_id(current_outputs)
    live_routes = set(current_routes.values())

    redirects = [
        item for item in redirects
        if item["source"] not in live_routes
    ]

    moves = sorted(
        (
            content_id,
            previous_routes[content_id],
            current_routes[content_id],
        )
        for content_id in previous_routes.keys() & current_routes.keys()
        if previous_routes[content_id] != current_routes[content_id]
    )

    for _, old_route, new_route in moves:
        for item in redirects:
            if item["destination"] == old_route:
                item["destination"] = new_route

        existing_rule = next(
            (item for item in redirects if item["source"] == old_route),
            None,
        )
        if existing_rule is None:
            redirects.append({
                "source": old_route,
                "destination": new_route,
                "created_on": current_date.isoformat(),
                "expires_on": (
                    current_date + timedelta(days=REDIRECT_RETENTION_DAYS)
                ).isoformat(),
            })
        else:
            existing_rule["destination"] = new_route

    redirects = [
        item for item in redirects
        if item["source"] not in live_routes
        and item["source"] != item["destination"]
    ]
    return sorted(redirects, key=lambda item: item["source"])


def _dump_redirects(redirects: Sequence[Mapping[str, str]]) -> str:
    return yaml.safe_dump(
        list(redirects),
        allow_unicode=True,
        sort_keys=False,
    )


def update_content_redirects(
    path: Path,
    previous_outputs: Sequence[Mapping[str, str]],
    current_outputs: Sequence[Mapping[str, str]],
    current_date: date | None = None,
) -> list[Dict[str, str]]:
    """Atomically update the redirect registry for a successful conversion."""
    effective_date = current_date or datetime.now(timezone.utc).date()
    resolved_path = path.resolve()
    existing = load_content_redirects(resolved_path)
    redirects = reconcile_content_redirects(
        existing,
        previous_outputs,
        current_outputs,
        effective_date,
    )
    serialized = _dump_redirects(redirects)
    if (
        resolved_path.exists()
        and resolved_path.read_text(encoding="utf-8") == serialized
    ):
        return redirects

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=resolved_path.parent,
            prefix=f".{resolved_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(serialized)
            temp_path = Path(temp_file.name)
        temp_path.chmod(0o644)
        os.replace(temp_path, resolved_path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
    return redirects
