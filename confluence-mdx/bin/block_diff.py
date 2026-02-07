"""Block Diff — 두 MDX 블록 시퀀스를 비교하여 변경된 블록을 추출한다."""
from dataclasses import dataclass
from typing import List
from mdx_block_parser import MdxBlock


@dataclass
class BlockChange:
    index: int              # 블록 인덱스 (0-based)
    change_type: str        # "modified" (Phase 1에서는 modified만 발생)
    old_block: MdxBlock
    new_block: MdxBlock


def diff_blocks(original: List[MdxBlock], improved: List[MdxBlock]) -> List[BlockChange]:
    """두 블록 시퀀스를 1:1 비교하여 변경된 블록 목록을 반환한다.

    Phase 1: 블록 수가 동일해야 한다. 다르면 ValueError.
    """
    if len(original) != len(improved):
        raise ValueError(
            f"block count mismatch: original={len(original)}, improved={len(improved)}"
        )

    changes: List[BlockChange] = []
    for i, (orig, impr) in enumerate(zip(original, improved)):
        if orig.content != impr.content:
            changes.append(BlockChange(
                index=i,
                change_type="modified",
                old_block=orig,
                new_block=impr,
            ))
    return changes
