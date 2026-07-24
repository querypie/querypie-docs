"""top-level fragment와 separator를 byte-preserving하는 XHTML patch renderer."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import TYPE_CHECKING, Any, Iterable

from reverse_sync.models import sha256_text
from reverse_sync.sidecar import RoundtripSidecar
from reverse_sync.xhtml_patcher import XhtmlPatchError, patch_xhtml

if TYPE_CHECKING:
    from reverse_sync.operations import PatchPlan


class PatchApplicationError(ValueError):
    """patch target을 exact base fragment로 해결하지 못했습니다."""

    reason_code = "missing_identity"


_XPATH_PART = re.compile(r"^([a-z0-9:-]+)\[(\d+)\]$", flags=re.IGNORECASE)


def _root_xpath(xpath: str) -> str:
    return xpath.split("/", 1)[0]


def _rebase_xpath(xpath: str) -> str:
    parts = xpath.split("/")
    match = _XPATH_PART.match(parts[0])
    if not match:
        raise PatchApplicationError(f"지원하지 않는 patch xpath입니다: {xpath}")
    parts[0] = f"{match.group(1)}[1]"
    return "/".join(parts)


def _rebase_patch(patch: dict[str, Any]) -> dict[str, Any]:
    rebased = deepcopy(patch)
    if "xhtml_xpath" in rebased:
        rebased["xhtml_xpath"] = _rebase_xpath(str(rebased["xhtml_xpath"]))
    if "after_xpath" in rebased and rebased["after_xpath"] is not None:
        rebased["after_xpath"] = _rebase_xpath(str(rebased["after_xpath"]))
    return rebased


def _index_by_xpath(sidecar: RoundtripSidecar) -> dict[str, int]:
    index: dict[str, int] = {}
    for position, block in enumerate(sidecar.blocks):
        if block.xhtml_xpath in index:
            raise PatchApplicationError(
                f"sidecar xpath가 중복되었습니다: {block.xhtml_xpath}"
            )
        index[block.xhtml_xpath] = position
    return index


def _validate_patch_targets(
    patches: Iterable[dict[str, Any]],
    xpath_index: dict[str, int],
) -> None:
    for patch in patches:
        action = patch.get("action", "modify")
        if action == "insert":
            anchor = patch.get("after_xpath")
            if anchor is not None and _root_xpath(str(anchor)) not in xpath_index:
                raise PatchApplicationError(f"insert anchor를 찾을 수 없습니다: {anchor}")
            if "new_element_xhtml" not in patch:
                raise PatchApplicationError("insert patch에 new_element_xhtml이 없습니다")
            continue
        target = patch.get("xhtml_xpath")
        if not target or _root_xpath(str(target)) not in xpath_index:
            raise PatchApplicationError(f"patch target을 찾을 수 없습니다: {target}")


def patch_xhtml_preserving(
    base_xhtml: str,
    patches: list[dict[str, Any]],
    sidecar: RoundtripSidecar,
) -> str:
    """변경된 top-level fragment만 DOM patch하고 나머지 bytes를 유지한다."""
    if sidecar.reassemble_xhtml() != base_xhtml:
        raise PatchApplicationError("sidecar가 base XHTML과 byte-equal하지 않습니다")

    xpath_index = _index_by_xpath(sidecar)
    _validate_patch_targets(patches, xpath_index)

    fragment_patches: dict[int, list[dict[str, Any]]] = {}
    insert_before: list[str] = []
    insert_after: dict[int, list[str]] = {}

    for patch in patches:
        action = patch.get("action", "modify")
        if action == "insert":
            new_fragment = str(patch["new_element_xhtml"])
            anchor = patch.get("after_xpath")
            if anchor is None:
                insert_before.append(new_fragment)
            else:
                position = xpath_index[_root_xpath(str(anchor))]
                insert_after.setdefault(position, []).append(new_fragment)
            continue

        target = str(patch["xhtml_xpath"])
        position = xpath_index[_root_xpath(target)]
        fragment_patches.setdefault(position, []).append(_rebase_patch(patch))

    parts = [sidecar.document_envelope.prefix]
    parts.extend(insert_before)
    for position, block in enumerate(sidecar.blocks):
        local_patches = fragment_patches.get(position)
        if local_patches:
            try:
                rendered = patch_xhtml(
                    block.xhtml_fragment,
                    local_patches,
                    strict=True,
                )
            except XhtmlPatchError as exc:
                raise PatchApplicationError(str(exc)) from exc
            parts.append(rendered)
        else:
            parts.append(block.xhtml_fragment)
        parts.extend(insert_after.get(position, ()))
        if position < len(sidecar.separators):
            parts.append(sidecar.separators[position])
    parts.append(sidecar.document_envelope.suffix)
    return "".join(parts)


def render_patch_plan_preserving(
    base_xhtml: str,
    plan: "PatchPlan",
    sidecar: RoundtripSidecar,
) -> str:
    """typed plan target identity를 재검증한 뒤 XHTML renderer를 호출합니다.

    raw patch dict 복원은 이 validated renderer boundary 안에서만 수행합니다.
    """
    if sidecar.reassemble_xhtml() != base_xhtml:
        raise PatchApplicationError("sidecar가 base XHTML과 byte-equal하지 않습니다")

    sidecar_by_xpath = {
        block.xhtml_xpath: block
        for block in sidecar.blocks
    }
    if len(sidecar_by_xpath) != len(sidecar.blocks):
        raise PatchApplicationError("sidecar xpath가 중복되었습니다")

    for operation in plan.executable_operations:
        target = operation.target
        if target.kind == "document_start":
            boundary = (
                sidecar.document_envelope.prefix
                + (sidecar.blocks[0].xhtml_xpath if sidecar.blocks else "$empty")
            )
            if target.base_fragment_sha256 != sha256_text(boundary):
                raise PatchApplicationError(
                    "document start identity hash가 base와 다릅니다"
                )
            continue

        block = sidecar_by_xpath.get(target.root_xpath)
        if block is None:
            raise PatchApplicationError(
                f"typed operation target을 찾을 수 없습니다: {target.root_xpath}"
            )
        if not target.base_fragment_sha256:
            raise PatchApplicationError(
                f"typed operation target hash가 없습니다: {target.xpath}"
            )
        if target.base_fragment_sha256 != sha256_text(block.xhtml_fragment):
            raise PatchApplicationError(
                f"typed operation target hash가 base와 다릅니다: {target.xpath}"
            )
        if (
            target.mdx_content_sha256
            and target.mdx_content_sha256 != block.mdx_content_hash
        ):
            raise PatchApplicationError(
                f"typed operation MDX provenance hash가 다릅니다: {target.xpath}"
            )
        if (
            target.mdx_line_range != (0, 0)
            and tuple(target.mdx_line_range) != tuple(block.mdx_line_range)
        ):
            raise PatchApplicationError(
                f"typed operation MDX line range가 다릅니다: {target.xpath}"
            )

    return patch_xhtml_preserving(
        base_xhtml,
        plan.to_patch_dicts(),
        sidecar,
    )


def changed_root_xpaths(patches: Iterable[dict[str, Any]]) -> frozenset[str]:
    """기존 base fragment 중 mutation 대상인 top-level xpath를 반환한다."""
    roots = {
        _root_xpath(str(patch["xhtml_xpath"]))
        for patch in patches
        if patch.get("action", "modify") != "insert" and patch.get("xhtml_xpath")
    }
    return frozenset(roots)
