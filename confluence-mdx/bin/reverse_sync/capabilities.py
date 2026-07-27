"""reverse-sync planner가 사용하는 capability registry와 판별 규칙."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional

from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.sidecar import SidecarBlock
from reverse_sync.visible_segments import extract_visible_model_from_mdx


class SupportLevel(str, Enum):
    """capability의 push 지원 수준."""

    SUPPORTED = "supported"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"


class RendererStrategy(str, Enum):
    """planner와 legacy adapter가 공유하는 renderer strategy."""

    TEXT_BLOCK = "text_block"
    LIST = "list"
    PRESERVED_ANCHOR = "preserved_anchor"
    CONTAINER = "container"
    TABLE = "table"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class StrategyDecision:
    """target mapping을 기준으로 확정한 renderer strategy."""

    strategy: RendererStrategy
    source_kind: str
    reason_code: str = ""


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


def _contains_only_mdx_owned_links(
    block_content: str,
    block_type: str,
    mapping: BlockMapping,
) -> bool:
    """XHTML preservation unit이 MDX link emitter 소유인지 판별합니다."""
    if block_type not in {"paragraph", "heading"}:
        return False

    link_fragments = re.findall(
        r"<ac:link(?:\s|>).*?</ac:link>",
        mapping.xhtml_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not link_fragments:
        return False
    remainder = mapping.xhtml_text
    for fragment in link_fragments:
        remainder = remainder.replace(fragment, "", 1)
    if "<ac:" in remainder or "<ri:" in remainder:
        return False

    mdx_model = extract_visible_model_from_mdx(block_content, block_type)
    mdx_link_count = sum(
        1
        for segment in mdx_model.segments
        if segment.kind == "anchor" and segment.meta.get("kind") == "link"
    )
    return mdx_link_count >= len(link_fragments)


def is_markdown_table(content: str) -> bool:
    """MDX content가 pipe table인지 판별합니다."""
    lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return False
    pipe_lines = sum(
        1
        for line in lines
        if line.startswith("|") and line.endswith("|")
    )
    return pipe_lines >= 2


def is_raw_html_table(content: str, block_type: str) -> bool:
    return (
        block_type == "html_block"
        and bool(re.match(r"^\s*<table(?:\s|>)", content, flags=re.IGNORECASE))
    )


def select_renderer_strategy(
    *,
    block_type: str,
    block_content: str,
    mapping: Optional[BlockMapping],
    sidecar_block: Optional[SidecarBlock] = None,
) -> StrategyDecision:
    """mapping 이후 renderer 전략을 typed category로 결정합니다.

    identity resolution은 이 함수보다 먼저 수행합니다. mapping이 없으면 list/table
    diagnostic fallback만 category를 유지하고, 나머지는 fail-closed합니다.
    """
    list_source = block_type == "list"
    raw_html_table = is_raw_html_table(block_content, block_type)
    markdown_table = is_markdown_table(block_content)
    table_source = raw_html_table or markdown_table

    if mapping is None:
        if list_source:
            return StrategyDecision(RendererStrategy.LIST, "list")
        if table_source:
            source_kind = "raw_html_table" if raw_html_table else "table"
            return StrategyDecision(RendererStrategy.TABLE, source_kind)
        return StrategyDecision(
            RendererStrategy.BLOCKED,
            block_type,
            reason_code="missing_identity",
        )

    if block_type == "callout" or mapping.children:
        if list_source:
            return StrategyDecision(RendererStrategy.LIST, "list")
        return StrategyDecision(RendererStrategy.CONTAINER, block_type)
    if list_source:
        return StrategyDecision(RendererStrategy.LIST, "list")
    if table_source:
        source_kind = "raw_html_table" if raw_html_table else "table"
        return StrategyDecision(RendererStrategy.TABLE, source_kind)
    if (
        _contains_preservation_unit(mapping)
        and not (
            sidecar_block is not None
            and sidecar_block.reconstruction is not None
            and sidecar_block.reconstruction.get("kind") == "paragraph"
            and not sidecar_block.reconstruction.get("anchors", [])
            and _contains_only_mdx_owned_links(
                block_content,
                block_type,
                mapping,
            )
        )
    ):
        return StrategyDecision(
            RendererStrategy.PRESERVED_ANCHOR,
            block_type,
        )
    return StrategyDecision(RendererStrategy.TEXT_BLOCK, block_type)


_LEGACY_UNSUPPORTED_CAPABILITIES = {
    "not_markdown_table": "raw_html_table_edit",
    "preserved_anchor_table": "unknown_macro_mutation",
    "raw_html_table": "raw_html_table_edit",
    "unknown_preservation_unit": "unknown_macro_mutation",
    "unsafe_html_table_edit": "raw_html_table_edit",
}


def capability_for_legacy_skip(reason_code: str) -> Optional[CapabilitySpec]:
    """legacy renderer skip을 canonical blocked capability로 변환합니다."""
    capability_id = _LEGACY_UNSUPPORTED_CAPABILITIES.get(reason_code)
    return get_capability(capability_id) if capability_id else None


def _has_supported_preserved_template(mapping: Optional[BlockMapping]) -> bool:
    if mapping is None:
        return False
    return (
        "<ac:link" in mapping.xhtml_text
        or "<ri:attachment" in mapping.xhtml_text
    )


def classify_capability(
    *,
    action: str,
    strategy: StrategyDecision,
    mapping: Optional[BlockMapping],
    block_type: str,
) -> CapabilitySpec:
    """typed intent와 renderer strategy를 capability로 분류합니다.

    raw patch shape은 capability source로 사용하지 않습니다. 분류할 수 없는
    macro/HTML mutation은 generic success로 흘려보내지 않고 blocked
    capability로 닫습니다.
    """
    if strategy.source_kind == "raw_html_table":
        return get_capability("raw_html_table_edit")

    mapping_type = mapping.type if mapping is not None else ""
    unknown_html = mapping_type == "html_block" or block_type == "html_block"

    if action == "insert":
        if unknown_html:
            return get_capability("unknown_macro_mutation")
        return get_capability("insert_owned_block")

    if action == "delete":
        if unknown_html:
            return get_capability("unknown_macro_mutation")
        return get_capability("delete_exact_block")

    if strategy.strategy is RendererStrategy.CONTAINER:
        return get_capability("container_body_reconstruct")
    if unknown_html:
        return get_capability("unknown_macro_mutation")
    if strategy.strategy is RendererStrategy.TABLE:
        if _contains_preservation_unit(mapping):
            return get_capability("unknown_macro_mutation")
        return get_capability("simple_markdown_table_replace")
    if strategy.strategy is RendererStrategy.PRESERVED_ANCHOR:
        if _has_supported_preserved_template(mapping):
            return get_capability("preserved_anchor_template_rewrite")
        return get_capability("unknown_macro_mutation")
    if strategy.strategy is RendererStrategy.LIST:
        if _contains_preservation_unit(mapping):
            if _has_supported_preserved_template(mapping):
                return get_capability("preserved_anchor_template_rewrite")
            return get_capability("unknown_macro_mutation")
        return get_capability("clean_list_reconstruct")
    if strategy.strategy is RendererStrategy.BLOCKED:
        return get_capability("unknown_macro_mutation")
    if mapping_type == "heading" or block_type == "heading":
        return get_capability("heading_visible_edit")
    if mapping_type == "code" or block_type == "code_block":
        return get_capability("code_block_replace")
    if mapping_type == "paragraph" or block_type == "paragraph":
        return get_capability("paragraph_visible_edit")
    return get_capability("unknown_macro_mutation")
