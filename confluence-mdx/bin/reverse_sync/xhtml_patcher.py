"""Validated XHTML operation apply boundary."""

from typing import Dict, List

from reverse_sync.xhtml_patch_engine import (
    XhtmlPatchError,
    patch_xhtml_engine as _patch_xhtml_engine,
)

__all__ = ["XhtmlPatchError", "apply_validated_patches"]


def apply_validated_patches(
    xhtml: str,
    patches: List[Dict[str, str]],
) -> str:
    """검증된 XHTML patch를 fail-closed 방식으로 적용합니다.

    Args:
        xhtml: 원본 XHTML 문자열
        patches: 검증된 patch 목록

    Returns:
        패치된 XHTML 문자열
    """
    return _patch_xhtml_engine(xhtml, patches, strict=True)
