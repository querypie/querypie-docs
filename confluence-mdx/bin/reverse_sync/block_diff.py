"""Block Diff — 두 MDX 블록 시퀀스를 비교하여 변경된 블록을 추출한다."""
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from mdx_to_storage.parser import Block as MdxBlock
from text_utils import normalize_mdx_to_plain, collapse_ws

NON_CONTENT_TYPES = frozenset(('empty', 'frontmatter', 'import_statement'))


@dataclass
class BlockChange:
    index: int              # 블록 인덱스 (original 기준 or improved 기준)
    change_type: str        # "modified" | "added" | "deleted"
    old_block: Optional[MdxBlock]   # None when added
    new_block: Optional[MdxBlock]   # None when deleted


def _block_key(block: MdxBlock) -> str:
    """블록을 비교 가능한 키로 변환한다."""
    if block.type in NON_CONTENT_TYPES:
        return f'__non_content_{block.type}__'
    plain = normalize_mdx_to_plain(block.content, block.type)
    return collapse_ws(plain)


def diff_blocks(
    original: List[MdxBlock], improved: List[MdxBlock],
) -> Tuple[List[BlockChange], Dict[int, int]]:
    """두 블록 시퀀스를 SequenceMatcher로 정렬하여 변경 목록과 alignment를 반환한다.

    Returns:
        changes: BlockChange 목록 (modified, added, deleted)
        alignment: improved_idx → original_idx 매핑 (매칭된 블록만)
    """
    orig_keys = [_block_key(b) for b in original]
    impr_keys = [_block_key(b) for b in improved]

    sm = SequenceMatcher(None, orig_keys, impr_keys)
    changes: List[BlockChange] = []
    alignment: Dict[int, int] = {}

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for i, j in zip(range(i1, i2), range(j1, j2)):
                alignment[j] = i
                if original[i].content != improved[j].content:
                    changes.append(BlockChange(
                        index=i, change_type='modified',
                        old_block=original[i], new_block=improved[j],
                    ))
        elif tag == 'replace':
            old_len = i2 - i1
            new_len = j2 - j1
            if old_len == new_len:
                # 같은 수의 블록이 대체 → 위치별 modified로 쌍 매칭
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    alignment[j] = i
                    changes.append(BlockChange(
                        index=i, change_type='modified',
                        old_block=original[i], new_block=improved[j],
                    ))
            else:
                # 다른 수의 블록이 대체 → delete + add로 분해
                for i in range(i1, i2):
                    changes.append(BlockChange(
                        index=i, change_type='deleted',
                        old_block=original[i], new_block=None,
                    ))
                for j in range(j1, j2):
                    changes.append(BlockChange(
                        index=j, change_type='added',
                        old_block=None, new_block=improved[j],
                    ))
        elif tag == 'insert':
            for j in range(j1, j2):
                changes.append(BlockChange(
                    index=j, change_type='added',
                    old_block=None, new_block=improved[j],
                ))
        elif tag == 'delete':
            for i in range(i1, i2):
                changes.append(BlockChange(
                    index=i, change_type='deleted',
                    old_block=original[i], new_block=None,
                ))

    return changes, alignment
