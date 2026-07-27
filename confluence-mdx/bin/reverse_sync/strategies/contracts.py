"""Renderer strategy handler가 공유하는 typed 실행 계약."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional

from mdx_to_storage.parser import Block as MdxBlock
from reverse_sync.block_diff import BlockChange
from reverse_sync.capabilities import StrategyDecision
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.sidecar import RoundtripSidecar, SidecarBlock, SidecarEntry

Patch = Dict[str, Any]
SkippedChange = Dict[str, str]


@dataclass(frozen=True)
class StrategyPrimitives:
    """기존 patch primitive를 handler에 주입하는 migration seam."""

    apply_mdx_diff_to_xhtml: Callable[[str, str, str], str]
    build_inline_fixups: Callable[..., List[Patch]]
    offset_inline_fixup_match_indexes: Callable[..., List[Patch]]
    detect_list_item_space_change: Callable[[str, str], bool]
    build_list_item_merge_patch: Callable[
        [BlockMapping, str, str, str, str],
        Optional[Patch],
    ]
    build_replace_fragment_patch: Callable[
        [BlockMapping, MdxBlock, Optional[SidecarBlock], Optional[dict]],
        Patch,
    ]
    build_preserved_template_patch: Callable[[BlockMapping, str, dict], Patch]
    classify_table_fragment_skip: Callable[
        [BlockChange, Optional[BlockMapping], Optional[RoundtripSidecar]],
        Optional[SkippedChange],
    ]
    extract_html_table_cells: Callable[[str], List[str]]
    is_safe_cell_text_edit: Callable[[List[str], List[str]], bool]
    is_clean_block: Callable[
        [str, Optional[BlockMapping], Optional[SidecarBlock]],
        bool,
    ]
    contains_preserved_anchor_markup: Callable[[str], bool]
    contains_only_supported_preservation_units: Callable[[str], bool]
    xhtml_visible_text: Callable[[BlockMapping, str], str]


@dataclass
class StrategyRenderContext:
    """한 modified MDX block을 렌더링하는 데 필요한 명시적 입력과 출력."""

    decision: StrategyDecision
    change: BlockChange
    mapping: BlockMapping
    old_plain: str
    new_plain: str
    mapping_via_v3_fallback: bool
    roundtrip_sidecar: Optional[RoundtripSidecar]
    sidecar_block: Optional[SidecarBlock]
    mapping_lost_info: dict
    improved_blocks: List[MdxBlock]
    mdx_to_sidecar: Mapping[int, SidecarEntry]
    id_to_mapping: Mapping[str, BlockMapping]
    used_ids: set[str]
    patches: List[Patch]
    skipped_changes: List[SkippedChange]
    text_change_patches: Dict[str, Patch]
    mark_used_callback: Callable[[str, BlockMapping], None]
    primitives: StrategyPrimitives

    @property
    def old_block(self) -> MdxBlock:
        if self.change.old_block is None:
            raise ValueError("renderer strategy에는 old_block이 필요합니다")
        return self.change.old_block

    @property
    def new_block(self) -> MdxBlock:
        if self.change.new_block is None:
            raise ValueError("renderer strategy에는 new_block이 필요합니다")
        return self.change.new_block

    def mark_used(self, mapping: Optional[BlockMapping] = None) -> None:
        target = mapping or self.mapping
        self.mark_used_callback(target.block_id, target)

    def append_replace_fragment(
        self,
        *,
        mapping: Optional[BlockMapping] = None,
        block: Optional[MdxBlock] = None,
        sidecar_block: Optional[SidecarBlock] = None,
    ) -> None:
        target = mapping or self.mapping
        new_block = block or self.new_block
        self.patches.append(
            self.primitives.build_replace_fragment_patch(
                target,
                new_block,
                sidecar_block,
                self.mapping_lost_info,
            )
        )
