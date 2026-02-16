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
from .byte_verify import ByteVerificationResult, iter_case_dirs, verify_case_dir

__all__ = [
    "ROUNDTRIP_SCHEMA_VERSION",
    "RoundtripSidecar",
    "build_sidecar",
    "load_sidecar",
    "rehydrate_xhtml",
    "rehydrate_xhtml_from_files",
    "sidecar_matches_mdx",
    "ByteVerificationResult",
    "iter_case_dirs",
    "verify_case_dir",
    "write_sidecar",
]
