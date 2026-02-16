"""Roundtrip sidecar schema and IO helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


ROUNDTRIP_SCHEMA_VERSION = "1"


@dataclass
class RoundtripSidecar:
    roundtrip_schema_version: str
    page_id: str
    mdx_sha256: str
    source_xhtml_sha256: str
    raw_xhtml: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_sidecar(
    expected_mdx: str,
    source_xhtml: str,
    page_id: str = "",
) -> RoundtripSidecar:
    return RoundtripSidecar(
        roundtrip_schema_version=ROUNDTRIP_SCHEMA_VERSION,
        page_id=page_id,
        mdx_sha256=sha256_text(expected_mdx),
        source_xhtml_sha256=sha256_text(source_xhtml),
        raw_xhtml=source_xhtml,
    )


def write_sidecar(sidecar: RoundtripSidecar, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(sidecar), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_sidecar(path: Path) -> RoundtripSidecar:
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid sidecar payload")

    required = {
        "roundtrip_schema_version",
        "page_id",
        "mdx_sha256",
        "source_xhtml_sha256",
        "raw_xhtml",
    }
    missing = sorted(required - set(data.keys()))
    if missing:
        raise ValueError(f"missing sidecar fields: {', '.join(missing)}")

    return RoundtripSidecar(
        roundtrip_schema_version=str(data["roundtrip_schema_version"]),
        page_id=str(data["page_id"]),
        mdx_sha256=str(data["mdx_sha256"]),
        source_xhtml_sha256=str(data["source_xhtml_sha256"]),
        raw_xhtml=str(data["raw_xhtml"]),
    )
