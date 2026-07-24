"""legacy patch builder를 typed PatchPlan 경계 뒤에 격리하는 planner."""

from __future__ import annotations

from typing import Any, Optional

from mdx_to_storage.link_resolver import LinkResolver
from mdx_to_storage.parser import Block as MdxBlock
from reverse_sync.block_diff import BlockChange, NON_CONTENT_TYPES
from reverse_sync.capabilities import SupportLevel, classify_capability
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.models import sha256_text
from reverse_sync.operations import (
    ChangeIntent,
    PatchOperation,
    PatchPlan,
    PlanIssue,
    TargetIdentity,
)
from reverse_sync.patch_builder import build_patches
from reverse_sync.sidecar import RoundtripSidecar, SidecarBlock, SidecarEntry


def _root_xpath(xpath: str) -> str:
    return xpath.split("/", 1)[0]


def _strict_sidecar_identity(
    block: MdxBlock,
    sidecar: Optional[RoundtripSidecar],
) -> Optional[SidecarBlock]:
    """hash와 line range가 모두 같은 유일한 provenance만 반환합니다."""
    if sidecar is None or not block.content:
        return None
    content_hash = sha256_text(block.content)
    line_range = (block.line_start, block.line_end)
    matches = [
        candidate
        for candidate in sidecar.blocks
        if candidate.mdx_content_hash == content_hash
        and tuple(candidate.mdx_line_range) == line_range
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _build_intents(
    changes: list[BlockChange],
    sidecar: Optional[RoundtripSidecar],
) -> tuple[ChangeIntent, ...]:
    deleted_targets: dict[int, str] = {}
    for change in changes:
        if change.change_type != "deleted" or change.old_block is None:
            continue
        identity = _strict_sidecar_identity(change.old_block, sidecar)
        if identity is not None:
            deleted_targets[change.index] = _root_xpath(identity.xhtml_xpath)

    intents: list[ChangeIntent] = []
    for ordinal, change in enumerate(changes):
        block = change.old_block or change.new_block
        if block is None or block.type in NON_CONTENT_TYPES:
            continue
        identity = (
            _strict_sidecar_identity(change.old_block, sidecar)
            if change.old_block is not None
            else None
        )
        provenance_xpath = (
            _root_xpath(identity.xhtml_xpath)
            if identity is not None
            else deleted_targets.get(change.index, "")
        )
        intents.append(
            ChangeIntent(
                ordinal=ordinal,
                index=change.index,
                change_type=change.change_type,
                block_type=block.type,
                old_sha256=sha256_text(change.old_block.content)
                if change.old_block is not None
                else "",
                new_sha256=sha256_text(change.new_block.content)
                if change.new_block is not None
                else "",
                provenance_xpath=provenance_xpath,
            )
        )
    return tuple(intents)


def _sidecar_index(sidecar: Optional[RoundtripSidecar]) -> dict[str, SidecarBlock]:
    if sidecar is None:
        return {}
    return {block.xhtml_xpath: block for block in sidecar.blocks}


def _mapping_for_patch(
    patch: dict[str, Any],
    mappings: list[BlockMapping],
) -> Optional[BlockMapping]:
    target = (
        patch.get("after_xpath")
        if patch.get("action") == "insert"
        else patch.get("xhtml_xpath")
    )
    if target is None:
        return None
    target_text = str(target)
    exact = {mapping.xhtml_xpath: mapping for mapping in mappings}
    return exact.get(target_text) or exact.get(_root_xpath(target_text))


def _target_identity(
    patch: dict[str, Any],
    sidecar: Optional[RoundtripSidecar],
) -> Optional[TargetIdentity]:
    action = str(patch.get("action", "modify"))
    sidecar_by_xpath = _sidecar_index(sidecar)
    if action == "insert":
        anchor = patch.get("after_xpath")
        if anchor is None:
            if sidecar is None:
                return None
            boundary = (
                sidecar.document_envelope.prefix
                + (sidecar.blocks[0].xhtml_xpath if sidecar.blocks else "$empty")
            )
            return TargetIdentity(
                kind="document_start",
                xpath="$document-start",
                root_xpath="$document-start",
                base_fragment_sha256=sha256_text(boundary),
            )
        xpath = str(anchor)
        root = _root_xpath(xpath)
        block = sidecar_by_xpath.get(root)
        if block is None:
            return None
        return TargetIdentity(
            kind="insert_after",
            xpath=xpath,
            root_xpath=root,
            base_fragment_sha256=sha256_text(block.xhtml_fragment),
            mdx_content_sha256=block.mdx_content_hash,
            mdx_line_range=tuple(block.mdx_line_range),
        )

    xpath_value = patch.get("xhtml_xpath")
    if not xpath_value:
        return None
    xpath = str(xpath_value)
    root = _root_xpath(xpath)
    block = sidecar_by_xpath.get(root)
    if block is None:
        return None
    return TargetIdentity(
        kind="exact_fragment",
        xpath=xpath,
        root_xpath=root,
        base_fragment_sha256=sha256_text(block.xhtml_fragment),
        mdx_content_sha256=block.mdx_content_hash,
        mdx_line_range=tuple(block.mdx_line_range),
    )


def _intent_ordinals_for_patch(
    *,
    patch: dict[str, Any],
    intents: tuple[ChangeIntent, ...],
    changes: list[BlockChange],
    already_assigned_inserts: set[int],
) -> tuple[int, ...]:
    action = str(patch.get("action", "modify"))
    if action == "insert":
        intent_by_ordinal = {intent.ordinal: intent for intent in intents}
        for ordinal, change in enumerate(changes):
            if change.change_type != "added":
                continue
            if ordinal in already_assigned_inserts:
                continue
            already_assigned_inserts.add(ordinal)
            block = change.new_block
            if block is None or block.type in NON_CONTENT_TYPES:
                # legacy builder가 empty source line을 <p></p> insert로 바꾸는
                # operation은 source-formatting intent가 아니므로
                # renderer에서 제거합니다.
                return (-1,)
            intent = intent_by_ordinal.get(ordinal)
            if intent is None:
                return ()
            if intent.provenance_xpath:
                continue
            return (intent.ordinal,)
        return ()

    target = patch.get("xhtml_xpath")
    if not target:
        return ()
    root = _root_xpath(str(target))
    matched = tuple(
        intent.ordinal
        for intent in intents
        if intent.provenance_xpath == root
    )
    return matched


def _source_details(
    intent_ordinals: tuple[int, ...],
    intents: tuple[ChangeIntent, ...],
    changes: list[BlockChange],
) -> tuple[tuple[str, ...], bool]:
    by_ordinal = {intent.ordinal: intent for intent in intents}
    block_types: list[str] = []
    contains_raw_html_table = False
    for ordinal in intent_ordinals:
        intent = by_ordinal.get(ordinal)
        if intent is None:
            continue
        block_types.append(intent.block_type)
        change = changes[ordinal]
        for block in (change.old_block, change.new_block):
            if (
                block is not None
                and block.type == "html_block"
                and block.content.lstrip().lower().startswith("<table")
            ):
                contains_raw_html_table = True
    return tuple(block_types), contains_raw_html_table


_LEGACY_UNSUPPORTED_CAPABILITIES = {
    "not_markdown_table": "raw_html_table_edit",
    "preserved_anchor_table": "unknown_macro_mutation",
    "raw_html_table": "raw_html_table_edit",
    "unsafe_html_table_edit": "raw_html_table_edit",
}
_LEGACY_MISSING_IDENTITY_REASONS = frozenset(
    {"missing_roundtrip_sidecar", "no_mapping"}
)


def _legacy_skip_intent_ordinal(
    item: dict[str, Any],
    intents: tuple[ChangeIntent, ...],
    mappings: list[BlockMapping],
    mdx_to_sidecar: Optional[dict[int, SidecarEntry]],
) -> int | None:
    """legacy skip의 block ID를 원래 ChangeIntent에 유일하게 연결합니다."""
    block_id = str(item.get("block_id", ""))
    candidates: list[ChangeIntent] = []
    if block_id.startswith("idx-"):
        try:
            index = int(block_id.removeprefix("idx-"))
        except ValueError:
            return None
        candidates = [intent for intent in intents if intent.index == index]
    else:
        roots = {
            _root_xpath(mapping.xhtml_xpath)
            for mapping in mappings
            if mapping.block_id == block_id
        }
        candidates = [
            intent
            for intent in intents
            if intent.provenance_xpath in roots
        ]
        if not candidates and mdx_to_sidecar:
            mapped_indexes = {
                index
                for index, entry in mdx_to_sidecar.items()
                if _root_xpath(entry.xhtml_xpath) in roots
            }
            candidates = [
                intent
                for intent in intents
                if intent.index in mapped_indexes
            ]
    if len(candidates) != 1:
        return None
    return candidates[0].ordinal


def _legacy_skip_issue(
    item: dict[str, Any],
    *,
    intents: tuple[ChangeIntent, ...],
    mappings: list[BlockMapping],
    mdx_to_sidecar: Optional[dict[int, SidecarEntry]],
    enforce_capabilities: bool,
    enforce_provenance: bool,
) -> PlanIssue:
    """legacy skip을 strict typed reason/capability boundary로 정규화합니다."""
    legacy_reason = str(item.get("reason", "incomplete_patch_plan"))
    capability_id = ""
    reason_code = legacy_reason
    if enforce_capabilities and legacy_reason in _LEGACY_UNSUPPORTED_CAPABILITIES:
        reason_code = "unsupported_capability"
        capability_id = _LEGACY_UNSUPPORTED_CAPABILITIES[legacy_reason]
    elif (
        enforce_provenance
        and legacy_reason in _LEGACY_MISSING_IDENTITY_REASONS
    ):
        reason_code = "missing_identity"
    return PlanIssue(
        reason_code=reason_code,
        description=str(
            item.get(
                "description",
                "legacy planner가 변경을 적용하지 못했습니다",
            )
        ),
        block_id=str(item.get("block_id", "")),
        capability_id=capability_id,
        intent_ordinal=_legacy_skip_intent_ordinal(
            item,
            intents,
            mappings,
            mdx_to_sidecar,
        ),
    )


def plan_patches(
    changes: list[BlockChange],
    original_blocks: list[MdxBlock],
    improved_blocks: list[MdxBlock],
    mappings: Optional[list[BlockMapping]] = None,
    mdx_to_sidecar: Optional[dict[int, SidecarEntry]] = None,
    xpath_to_mapping: Optional[dict[str, BlockMapping]] = None,
    alignment: Optional[dict[int, int]] = None,
    page_lost_info: Optional[dict] = None,
    roundtrip_sidecar: Optional[RoundtripSidecar] = None,
    page_xhtml: Optional[str] = None,
    link_resolver: Optional[LinkResolver] = None,
    attachment_filenames: frozenset[str] = frozenset(),
    allow_text_identity_fallback: bool = True,
    enforce_capabilities: bool = False,
    enforce_provenance: bool = False,
) -> tuple[PatchPlan, list[BlockMapping]]:
    """legacy builder output을 capability/provenance가 있는 typed plan으로 바꿉니다."""
    raw_patches, resolved_mappings, legacy_skips = build_patches(
        changes,
        original_blocks,
        improved_blocks,
        mappings=mappings,
        mdx_to_sidecar=mdx_to_sidecar,
        xpath_to_mapping=xpath_to_mapping,
        alignment=alignment,
        page_lost_info=page_lost_info,
        roundtrip_sidecar=roundtrip_sidecar,
        page_xhtml=page_xhtml,
        link_resolver=link_resolver,
        attachment_filenames=attachment_filenames,
        allow_text_identity_fallback=allow_text_identity_fallback,
    )
    intents = _build_intents(changes, roundtrip_sidecar)
    issues = [
        _legacy_skip_issue(
            item,
            intents=intents,
            mappings=resolved_mappings,
            mdx_to_sidecar=mdx_to_sidecar,
            enforce_capabilities=enforce_capabilities,
            enforce_provenance=enforce_provenance,
        )
        for item in legacy_skips
    ]
    sidecar_by_xpath = _sidecar_index(roundtrip_sidecar)
    assigned_inserts: set[int] = set()
    operations: list[PatchOperation] = []

    for operation_index, patch in enumerate(raw_patches):
        intent_ordinals = _intent_ordinals_for_patch(
            patch=patch,
            intents=intents,
            changes=changes,
            already_assigned_inserts=assigned_inserts,
        )
        if intent_ordinals == (-1,):
            continue
        target = _target_identity(patch, roundtrip_sidecar)
        if target is None:
            if enforce_provenance:
                mapping = _mapping_for_patch(patch, resolved_mappings)
                issue_intent_ordinal = (
                    intent_ordinals[0]
                    if len(intent_ordinals) == 1
                    else _legacy_skip_intent_ordinal(
                        {
                            "block_id": (
                                mapping.block_id
                                if mapping is not None
                                else ""
                            )
                        },
                        intents,
                        resolved_mappings,
                        mdx_to_sidecar,
                    )
                )
                issues.append(
                    PlanIssue(
                        reason_code="missing_identity",
                        description=(
                            "renderer operation의 exact base fragment identity가 없습니다"
                        ),
                        block_id=str(
                            patch.get("xhtml_xpath")
                            or patch.get("after_xpath")
                            or "$document-start"
                        ),
                        intent_ordinal=issue_intent_ordinal,
                    )
                )
                continue
            # offline diagnostic도 typed target shape를 유지하되 push provenance로
            # 해석할 수 없음을 kind와 빈 fragment hash로 명시합니다.
            raw_target = (
                patch.get("after_xpath")
                if patch.get("action") == "insert"
                else patch.get("xhtml_xpath")
            )
            target_text = "$document-start" if raw_target is None else str(raw_target)
            target = TargetIdentity(
                kind="diagnostic_unverified",
                xpath=target_text,
                root_xpath=_root_xpath(target_text),
                base_fragment_sha256="",
            )

        mapping = _mapping_for_patch(patch, resolved_mappings)
        source_types, contains_raw_html_table = _source_details(
            intent_ordinals,
            intents,
            changes,
        )
        capability = classify_capability(
            action=str(patch.get("action", "modify")),
            mapping=mapping,
            sidecar_block=sidecar_by_xpath.get(target.root_xpath),
            source_block_types=source_types,
            contains_raw_html_table=contains_raw_html_table,
        )
        capability_blocked = (
            enforce_capabilities
            and capability.support_level is SupportLevel.BLOCKED
        )
        provenance_blocked = enforce_provenance and not intent_ordinals
        blocked = capability_blocked or provenance_blocked
        reason_code = (
            capability.block_reason
            if capability_blocked
            else "missing_identity"
            if provenance_blocked
            else ""
        )
        operation = PatchOperation.from_legacy_patch(
            operation_id=f"op-{operation_index + 1:04d}",
            patch=patch,
            capability_id=capability.capability_id,
            target=target,
            required_proof=capability.required_proof,
            intent_ordinals=intent_ordinals,
            executable=not blocked,
            reason_code=reason_code,
        )
        operations.append(operation)
        if capability_blocked:
            issues.append(
                PlanIssue(
                    reason_code=reason_code,
                    description=(
                        f"{capability.capability_id} capability는 push 경로에서 "
                        "지원되지 않습니다"
                    ),
                    block_id=target.xpath,
                    capability_id=capability.capability_id,
                )
            )
        elif provenance_blocked:
            issues.append(
                PlanIssue(
                    reason_code="missing_identity",
                    description=(
                        "renderer operation을 exact MDX intent provenance에 "
                        "대응시키지 못했습니다"
                    ),
                    block_id=target.xpath,
                    capability_id=capability.capability_id,
                )
            )

    if enforce_provenance:
        mapped = {
            ordinal
            for operation in operations
            for ordinal in operation.intent_ordinals
        }
        issued_intents = {
            issue.intent_ordinal
            for issue in issues
            if issue.intent_ordinal is not None
        }
        for intent in intents:
            if intent.ordinal in mapped:
                continue
            if intent.ordinal in issued_intents:
                continue
            issues.append(
                PlanIssue(
                    reason_code="missing_identity",
                    description=(
                        f"MDX intent #{intent.ordinal}을 exact target operation에 "
                        "대응시키지 못했습니다"
                    ),
                    block_id=f"idx-{intent.index}",
                    intent_ordinal=intent.ordinal,
                )
            )

    return (
        PatchPlan(
            intents=intents,
            operations=tuple(operations),
            issues=tuple(issues),
        ),
        resolved_mappings,
    )
