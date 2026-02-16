"""Lossless roundtrip helpers for MDX <-> Storage XHTML."""

from .sidecar import (
    ROUNDTRIP_SCHEMA_VERSION,
    RoundtripSidecar,
    build_sidecar,
    load_sidecar,
    write_sidecar,
)
from .rehydrator import (
    rehydrate_xhtml,
    rehydrate_xhtml_from_files,
    sidecar_matches_mdx,
)

__all__ = [
    "ROUNDTRIP_SCHEMA_VERSION",
    "RoundtripSidecar",
    "build_sidecar",
    "load_sidecar",
    "rehydrate_xhtml",
    "rehydrate_xhtml_from_files",
    "sidecar_matches_mdx",
    "write_sidecar",
]
