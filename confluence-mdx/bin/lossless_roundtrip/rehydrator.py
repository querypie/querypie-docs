"""Lossless rehydration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from mdx_to_storage import emit_document, parse_mdx

from .sidecar import RoundtripSidecar, load_sidecar, sha256_text


FallbackRenderer = Callable[[str], str]


def default_fallback_renderer(mdx_text: str) -> str:
    blocks = parse_mdx(mdx_text)
    return emit_document(blocks)


def sidecar_matches_mdx(mdx_text: str, sidecar: RoundtripSidecar) -> bool:
    return sha256_text(mdx_text) == sidecar.mdx_sha256


def rehydrate_xhtml(
    mdx_text: str,
    sidecar: RoundtripSidecar,
    fallback_renderer: FallbackRenderer | None = None,
) -> str:
    if sidecar_matches_mdx(mdx_text, sidecar):
        return sidecar.raw_xhtml

    renderer = fallback_renderer or default_fallback_renderer
    return renderer(mdx_text)


def rehydrate_xhtml_from_files(
    mdx_path: Path,
    sidecar_path: Path,
    fallback_renderer: FallbackRenderer | None = None,
) -> str:
    mdx_text = mdx_path.read_text(encoding="utf-8")
    sidecar = load_sidecar(sidecar_path)
    return rehydrate_xhtml(
        mdx_text,
        sidecar,
        fallback_renderer=fallback_renderer,
    )
