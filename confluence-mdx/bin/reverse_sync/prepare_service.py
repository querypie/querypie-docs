"""MDX source와 remote snapshot을 verification 입력으로 준비하는 service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from reverse_sync.verification_service import MdxSource


@dataclass(frozen=True)
class VerificationRequest:
    """단일 MDX verification에 필요한 사용자 입력입니다."""

    improved_mdx: str
    original_mdx: str | None = None
    page_id: str | None = None
    page_dir: str | None = None
    lenient: bool = False
    no_normalize: bool = False


@dataclass(frozen=True)
class PrepareRuntime:
    """CLI와 repository 환경 의존성을 prepare lifecycle에 주입합니다."""

    resolve_mdx_source: Callable[[str], MdxSource]
    extract_ko_mdx_path: Callable[[str], str]
    resolve_page_id: Callable[[str], str]
    ensure_config: Callable[[], object]
    run_verification: Callable[..., dict]


def prepare_verification(
    request: VerificationRequest,
    *,
    runtime: PrepareRuntime,
    config=None,
    prepare_push: bool = False,
) -> dict:
    """MDX identity를 해석하고 필요할 때 remote snapshot을 결합합니다."""

    improved_src = runtime.resolve_mdx_source(request.improved_mdx)
    if request.original_mdx:
        original_src = runtime.resolve_mdx_source(request.original_mdx)
    else:
        ko_path = runtime.extract_ko_mdx_path(improved_src.descriptor)
        original_src = runtime.resolve_mdx_source(f"main:{ko_path}")

    page_id = request.page_id
    if not page_id:
        page_id = runtime.resolve_page_id(
            runtime.extract_ko_mdx_path(improved_src.descriptor)
        )

    page_dir = request.page_dir
    xhtml_path = str(Path(page_dir) / "page.xhtml") if page_dir else None
    base_snapshot = None
    attachment_catalog = None
    if prepare_push:
        from reverse_sync.confluence_client import (
            get_attachment_catalog,
            get_page_snapshot,
        )
        from reverse_sync.dependencies import added_attachment_filenames

        if config is None:
            config = runtime.ensure_config()
        base_snapshot = get_page_snapshot(config, page_id)
        if added_attachment_filenames(
            original_src.content,
            improved_src.content,
        ):
            attachment_catalog = get_attachment_catalog(config, page_id)

    return runtime.run_verification(
        page_id=page_id,
        original_src=original_src,
        improved_src=improved_src,
        xhtml_path=xhtml_path,
        lenient=request.lenient,
        no_normalize=request.no_normalize,
        page_dir=page_dir,
        base_snapshot=base_snapshot,
        attachment_catalog=attachment_catalog,
        for_push=prepare_push,
    )
