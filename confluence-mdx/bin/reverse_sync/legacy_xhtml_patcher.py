"""Offline diagnostic용 lenient raw XHTML patch compatibility API."""

from typing import Dict, List

from reverse_sync.xhtml_patch_engine import patch_xhtml_engine


def patch_xhtml(
    xhtml: str,
    patches: List[Dict[str, str]],
) -> str:
    """Legacy raw patch를 적용하고 unresolved operation은 건너뜁니다.

    이 API는 offline diagnostic과 regression fixture 호환 전용입니다.
    publish candidate 생성에는 ``apply_validated_patches()``를 사용해야 합니다.
    """
    return patch_xhtml_engine(xhtml, patches, strict=False)
