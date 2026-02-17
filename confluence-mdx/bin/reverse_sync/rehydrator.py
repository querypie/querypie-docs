"""Lossless rehydration — MDX + sidecar → XHTML 복원.

세 가지 복원 경로:
  1. Fast path     — MDX 전체 SHA256 일치 → reassemble_xhtml() (document-level)
  2. Splice path   — 블록 단위 해시 매칭 → 원본 fragment / emitter 혼합 조립
  3. Fallback path — 전체 emitter 재생성
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List

from mdx_to_storage import emit_document, parse_mdx
from mdx_to_storage.emitter import emit_block as emit_single_block
from mdx_to_storage.parser import Block

from .lost_info_patcher import apply_lost_info
from .mdx_block_parser import MdxBlock, parse_mdx_blocks
from .sidecar import RoundtripSidecar, SidecarBlock, load_sidecar, sha256_text


FallbackRenderer = Callable[[str], str]

_NON_CONTENT = frozenset(("empty", "frontmatter", "import_statement"))

_MDX_TYPE_TO_PARSER_TYPE = {
    "heading": "heading",
    "paragraph": "paragraph",
    "code_block": "code_block",
    "list": "list",
    "html_block": "html_block",
}


@dataclass
class SpliceResult:
    """Splice rehydration 결과."""

    xhtml: str
    matched_count: int
    emitted_count: int
    total_blocks: int
    block_details: List[dict] = field(default_factory=list)


def default_fallback_renderer(mdx_text: str) -> str:
    blocks = parse_mdx(mdx_text)
    return emit_document(blocks)


def sidecar_matches_mdx(mdx_text: str, sidecar: RoundtripSidecar) -> bool:
    return sha256_text(mdx_text) == sidecar.mdx_sha256


def _mdx_block_to_parser_block(mdx_block: MdxBlock) -> Block:
    """MdxBlock을 mdx_to_storage.parser.Block으로 변환한다."""
    block_type = _MDX_TYPE_TO_PARSER_TYPE.get(mdx_block.type, mdx_block.type)
    return Block(type=block_type, content=mdx_block.content)


def splice_rehydrate_xhtml(
    mdx_text: str,
    sidecar: RoundtripSidecar,
) -> SpliceResult:
    """블록 단위 splice 경로로 XHTML을 복원한다.

    Sidecar 블록을 기준으로 순회하면서, MDX 대응이 있는 블록은 해시를 비교한다.
    - mdx_content_hash가 비어 있는 sidecar 블록 (이미지 등 MDX 대응 없음):
      원본 xhtml_fragment를 그대로 사용
    - 해시가 일치하는 블록: 원본 xhtml_fragment 사용
    - 해시가 불일치하는 블록: emitter로 재생성
    """
    mdx_blocks = parse_mdx_blocks(mdx_text)
    content_blocks = [b for b in mdx_blocks if b.type not in _NON_CONTENT]

    matched_count = 0
    emitted_count = 0
    preserved_count = 0
    fragments: List[str] = []
    details: List[dict] = []
    mdx_ptr = 0  # MDX content 블록 포인터

    for i, sb in enumerate(sidecar.blocks):
        if not sb.mdx_content_hash:
            # MDX 대응 없는 XHTML 블록 (이미지, 빈 단락 등) → 원본 유지
            fragments.append(sb.xhtml_fragment)
            preserved_count += 1
            details.append({
                "index": i,
                "method": "preserved",
                "xpath": sb.xhtml_xpath,
            })
            continue

        if mdx_ptr < len(content_blocks):
            mdx_block = content_blocks[mdx_ptr]
            content_hash = sha256_text(mdx_block.content)

            if content_hash == sb.mdx_content_hash:
                fragments.append(sb.xhtml_fragment)
                matched_count += 1
                details.append({
                    "index": i,
                    "type": mdx_block.type,
                    "method": "sidecar",
                    "xpath": sb.xhtml_xpath,
                })
            else:
                parser_block = _mdx_block_to_parser_block(mdx_block)
                emitted = emit_single_block(parser_block)
                # L4: lost_info 적용
                if sb.lost_info:
                    emitted = apply_lost_info(emitted, sb.lost_info)
                fragments.append(emitted)
                emitted_count += 1
                details.append({
                    "index": i,
                    "type": mdx_block.type,
                    "method": "emitter",
                    "hash_expected": sb.mdx_content_hash,
                    "hash_actual": content_hash,
                })
            mdx_ptr += 1
        else:
            # MDX 블록 소진 — sidecar 블록의 원본 fragment 사용
            fragments.append(sb.xhtml_fragment)
            preserved_count += 1
            details.append({
                "index": i,
                "method": "preserved",
                "xpath": sb.xhtml_xpath,
            })

    # separators + envelope로 조립
    parts = [sidecar.document_envelope.prefix]
    for i, frag in enumerate(fragments):
        parts.append(frag)
        if i < len(sidecar.separators):
            parts.append(sidecar.separators[i])
    parts.append(sidecar.document_envelope.suffix)

    return SpliceResult(
        xhtml="".join(parts),
        matched_count=matched_count,
        emitted_count=emitted_count,
        total_blocks=len(sidecar.blocks),
        block_details=details,
    )


def rehydrate_xhtml(
    mdx_text: str,
    sidecar: RoundtripSidecar,
    fallback_renderer: FallbackRenderer | None = None,
) -> str:
    if sidecar_matches_mdx(mdx_text, sidecar):
        return sidecar.reassemble_xhtml()

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
