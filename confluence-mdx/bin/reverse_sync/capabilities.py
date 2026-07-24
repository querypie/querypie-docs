"""reverse-sync planner가 사용하는 capability registry와 판별 규칙."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.sidecar import SidecarBlock


class SupportLevel(str, Enum):
    """capability의 push 지원 수준."""

    SUPPORTED = "supported"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CapabilitySpec:
    """planner와 proof가 공유하는 capability 계약."""

    capability_id: str
    support_level: SupportLevel
    renderer_owner: str
    required_proof: tuple[str, ...]
    block_reason: str = ""

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "capability_id": self.capability_id,
            "renderer_owner": self.renderer_owner,
            "required_proof": list(self.required_proof),
            "support_level": self.support_level.value,
        }
        if self.block_reason:
            result["block_reason"] = self.block_reason
        return result


_COMMON_PROOF = (
    "target_identity",
    "preservation",
    "semantic_roundtrip",
    "determinism",
    "idempotency",
)


CAPABILITY_REGISTRY: dict[str, CapabilitySpec] = {
    "paragraph_visible_edit": CapabilitySpec(
        "paragraph_visible_edit",
        SupportLevel.SUPPORTED,
        "legacy_adapter/paragraph",
        _COMMON_PROOF,
    ),
    "heading_visible_edit": CapabilitySpec(
        "heading_visible_edit",
        SupportLevel.SUPPORTED,
        "legacy_adapter/heading",
        _COMMON_PROOF,
    ),
    "code_block_replace": CapabilitySpec(
        "code_block_replace",
        SupportLevel.SUPPORTED,
        "legacy_adapter/code_block",
        _COMMON_PROOF + ("storage_well_formed",),
    ),
    "clean_list_reconstruct": CapabilitySpec(
        "clean_list_reconstruct",
        SupportLevel.SUPPORTED,
        "legacy_adapter/list",
        _COMMON_PROOF + ("visible_structure",),
    ),
    "preserved_anchor_template_rewrite": CapabilitySpec(
        "preserved_anchor_template_rewrite",
        SupportLevel.CONDITIONAL,
        "legacy_adapter/preserved_anchor",
        _COMMON_PROOF + ("preserved_anchor_identity",),
    ),
    "container_body_reconstruct": CapabilitySpec(
        "container_body_reconstruct",
        SupportLevel.CONDITIONAL,
        "legacy_adapter/container",
        _COMMON_PROOF + ("container_wrapper_preservation",),
    ),
    "simple_markdown_table_replace": CapabilitySpec(
        "simple_markdown_table_replace",
        SupportLevel.CONDITIONAL,
        "legacy_adapter/markdown_table",
        _COMMON_PROOF + ("table_structure",),
    ),
    "insert_owned_block": CapabilitySpec(
        "insert_owned_block",
        SupportLevel.CONDITIONAL,
        "legacy_adapter/insert",
        _COMMON_PROOF + ("neighbor_identity", "dependency"),
    ),
    "delete_exact_block": CapabilitySpec(
        "delete_exact_block",
        SupportLevel.CONDITIONAL,
        "legacy_adapter/delete",
        _COMMON_PROOF + ("exact_fragment_identity",),
    ),
    "raw_html_table_edit": CapabilitySpec(
        "raw_html_table_edit",
        SupportLevel.BLOCKED,
        "unimplemented/raw_html_table",
        _COMMON_PROOF + ("typed_table_cell_proof",),
        block_reason="unsupported_capability",
    ),
    "unknown_macro_mutation": CapabilitySpec(
        "unknown_macro_mutation",
        SupportLevel.BLOCKED,
        "unimplemented/unknown_macro",
        _COMMON_PROOF + ("macro_preservation_contract",),
        block_reason="unsupported_capability",
    ),
}


def get_capability(capability_id: str) -> CapabilitySpec:
    """등록된 capability를 반환하고 오타나 미등록 ID를 즉시 거부합니다."""
    try:
        return CAPABILITY_REGISTRY[capability_id]
    except KeyError as exc:
        raise ValueError(
            f"등록되지 않은 reverse-sync capability입니다: {capability_id}"
        ) from exc


def _contains_preservation_unit(mapping: Optional[BlockMapping]) -> bool:
    if mapping is None:
        return False
    return "<ac:" in mapping.xhtml_text or "<ri:" in mapping.xhtml_text


def _is_container(
    mapping: Optional[BlockMapping],
    sidecar_block: Optional[SidecarBlock],
) -> bool:
    if mapping is not None and mapping.children:
        return True
    reconstruction = sidecar_block.reconstruction if sidecar_block is not None else None
    return bool(reconstruction and reconstruction.get("kind") == "container")


def classify_capability(
    *,
    action: str,
    mapping: Optional[BlockMapping],
    sidecar_block: Optional[SidecarBlock],
    source_block_types: tuple[str, ...],
    contains_raw_html_table: bool,
) -> CapabilitySpec:
    """legacy patch 하나를 명시적인 capability로 분류합니다.

    분류할 수 없는 macro/HTML mutation은 generic success로 흘려보내지 않고
    blocked capability로 닫습니다.
    """
    if contains_raw_html_table:
        return get_capability("raw_html_table_edit")

    mapping_type = mapping.type if mapping is not None else ""
    source_types = set(source_block_types)
    unknown_html = mapping_type == "html_block" or "html_block" in source_types

    if action == "insert":
        if unknown_html:
            return get_capability("unknown_macro_mutation")
        return get_capability("insert_owned_block")

    if action == "delete":
        if unknown_html:
            return get_capability("unknown_macro_mutation")
        return get_capability("delete_exact_block")

    if _is_container(mapping, sidecar_block):
        return get_capability("container_body_reconstruct")
    if unknown_html:
        return get_capability("unknown_macro_mutation")
    if mapping_type == "table" or "table" in source_types:
        return get_capability("simple_markdown_table_replace")
    if _contains_preservation_unit(mapping):
        return get_capability("preserved_anchor_template_rewrite")
    if mapping_type == "list" or "list" in source_types:
        return get_capability("clean_list_reconstruct")
    if mapping_type == "heading" or "heading" in source_types:
        return get_capability("heading_visible_edit")
    if mapping_type == "code" or "code_block" in source_types:
        return get_capability("code_block_replace")
    if mapping_type == "paragraph" or "paragraph" in source_types:
        return get_capability("paragraph_visible_edit")
    return get_capability("unknown_macro_mutation")
