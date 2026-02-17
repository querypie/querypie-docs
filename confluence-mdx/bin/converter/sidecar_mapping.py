"""Sidecar Mapping — forward converter가 생성한 XHTML→MDX 대응 정보를 기록한다.

변환 완료 후, XHTML 블록과 MDX 블록을 순서대로 매칭하여
mapping.yaml sidecar 파일을 생성한다.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

import yaml

from reverse_sync.mapping_recorder import BlockMapping, record_mapping
from mdx_to_storage.parser import Block as MdxBlock, parse_mdx_blocks

logger = logging.getLogger(__name__)

# MDX 파서가 content 블록으로 분류하지 않는 타입들
_NON_CONTENT_TYPES = frozenset({'frontmatter', 'import_statement', 'empty'})


def generate_sidecar_mapping(
    xhtml_content: str,
    mdx_content: str,
    page_id: Optional[str],
    input_dir: str,
    output_file_path: str,
) -> Optional[str]:
    """XHTML→MDX 매핑 sidecar 파일을 생성한다.

    Args:
        xhtml_content: namespace prefix 제거 전 원본 XHTML
        mdx_content: 변환된 MDX 문자열
        page_id: Confluence page ID
        input_dir: var/<page_id>/ 디렉토리
        output_file_path: MDX 출력 파일 경로

    Returns:
        생성된 mapping.yaml 파일 경로, 실패 시 None
    """
    xhtml_mappings = record_mapping(xhtml_content)
    mdx_blocks = parse_mdx_blocks(mdx_content)

    entries = _build_mapping_entries(xhtml_mappings, mdx_blocks)

    mapping_path = os.path.join(input_dir, 'mapping.yaml')
    data = {
        'version': 1,
        'source_page_id': page_id or '',
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'mdx_file': os.path.basename(output_file_path),
        'mappings': entries,
    }

    with open(mapping_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    logger.info(f"Sidecar mapping 생성 완료: {mapping_path} ({len(entries)} entries)")
    return mapping_path


def _build_mapping_entries(
    xhtml_mappings: List[BlockMapping],
    mdx_blocks: List[MdxBlock],
) -> List[Dict]:
    """XHTML 매핑과 MDX 블록을 순서대로 매칭하여 매핑 엔트리를 생성한다."""
    # content 블록만 필터 (frontmatter, import, empty 제외)
    content_blocks: List[tuple] = []  # (original_index, block)
    for idx, block in enumerate(mdx_blocks):
        if block.type not in _NON_CONTENT_TYPES:
            content_blocks.append((idx, block))

    # 자식 block_id 집합 구성 — 자식은 부모가 처리하므로 건너뜀
    child_ids: Set[str] = set()
    for m in xhtml_mappings:
        child_ids.update(m.children)

    entries: List[Dict] = []
    mdx_idx = 0  # content_blocks 내 현재 위치

    for mapping in xhtml_mappings:
        if mapping.block_id in child_ids:
            continue

        if mdx_idx >= len(content_blocks):
            logger.debug(f"MDX 블록 소진: {mapping.xhtml_xpath} 이후 매핑 불가")
            break

        if mapping.children:
            # Callout: MDX에서 <Callout ~ </Callout> 범위를 찾아 할당
            callout_indices = _find_callout_range(content_blocks, mdx_idx)
            if callout_indices:
                entries.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'xhtml_type': mapping.type,
                    'mdx_blocks': callout_indices,
                })
                mdx_idx = _next_index_after(content_blocks, callout_indices[-1], mdx_idx)
            else:
                # Callout 범위를 찾지 못하면 1:1로 할당
                orig_idx = content_blocks[mdx_idx][0]
                entries.append({
                    'xhtml_xpath': mapping.xhtml_xpath,
                    'xhtml_type': mapping.type,
                    'mdx_blocks': [orig_idx],
                })
                mdx_idx += 1
        else:
            # 일반 블록: 1:1 매칭
            orig_idx = content_blocks[mdx_idx][0]
            entries.append({
                'xhtml_xpath': mapping.xhtml_xpath,
                'xhtml_type': mapping.type,
                'mdx_blocks': [orig_idx],
            })
            mdx_idx += 1

    return entries


def _find_callout_range(
    content_blocks: List[tuple],
    start_idx: int,
) -> Optional[List[int]]:
    """content_blocks[start_idx]부터 Callout 범위를 찾아 원본 인덱스 리스트를 반환한다."""
    if start_idx >= len(content_blocks):
        return None

    orig_idx, block = content_blocks[start_idx]
    if '<Callout' not in block.content:
        return None

    indices = [orig_idx]
    depth = block.content.count('<Callout') - block.content.count('</Callout>')

    i = start_idx + 1
    while i < len(content_blocks) and depth > 0:
        o_idx, blk = content_blocks[i]
        indices.append(o_idx)
        depth += blk.content.count('<Callout') - blk.content.count('</Callout>')
        i += 1

    if depth != 0:
        # 닫힘 태그를 찾지 못한 경우 — 현재 블록만 반환
        return [orig_idx]

    return indices


def _next_index_after(
    content_blocks: List[tuple],
    last_orig_idx: int,
    current_mdx_idx: int,
) -> int:
    """last_orig_idx 이후의 content_blocks 인덱스를 반환한다."""
    for i in range(current_mdx_idx, len(content_blocks)):
        if content_blocks[i][0] > last_orig_idx:
            return i
    return len(content_blocks)
