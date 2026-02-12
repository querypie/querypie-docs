"""Sidecar Mapping Lookup — mapping.yaml 로드 및 인덱스 구축."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from reverse_sync.mapping_recorder import BlockMapping


@dataclass
class SidecarEntry:
    xhtml_xpath: str
    xhtml_type: str
    mdx_blocks: List[int] = field(default_factory=list)


def load_sidecar_mapping(mapping_path: str) -> List[SidecarEntry]:
    """mapping.yaml 파일을 로드하여 SidecarEntry 목록을 반환한다."""
    path = Path(mapping_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Sidecar mapping not found: {mapping_path}\n"
            f"Forward converter를 실행하여 mapping.yaml을 생성하세요."
        )
    data = yaml.safe_load(path.read_text())
    entries = []
    for item in data.get('mappings', []):
        entries.append(SidecarEntry(
            xhtml_xpath=item['xhtml_xpath'],
            xhtml_type=item.get('xhtml_type', ''),
            mdx_blocks=item.get('mdx_blocks', []),
        ))
    return entries


def build_mdx_to_sidecar_index(
    entries: List[SidecarEntry],
) -> Dict[int, SidecarEntry]:
    """MDX 블록 인덱스 → SidecarEntry 역인덱스를 구축한다."""
    index: Dict[int, SidecarEntry] = {}
    for entry in entries:
        for mdx_idx in entry.mdx_blocks:
            index[mdx_idx] = entry
    return index


def build_xpath_to_mapping(
    mappings: List[BlockMapping],
) -> Dict[str, BlockMapping]:
    """xhtml_xpath → BlockMapping 인덱스를 구축한다."""
    index: Dict[str, BlockMapping] = {}
    for m in mappings:
        index[m.xhtml_xpath] = m
    return index


def generate_sidecar_mapping(
    xhtml: str,
    mdx: str,
    page_id: str = '',
) -> str:
    """XHTML + MDX로부터 mapping.yaml 내용을 생성한다.

    Forward converter의 sidecar 생성 로직을 재현한다.
    record_mapping()과 parse_mdx_blocks()를 조합하여 텍스트 기반 매칭을 수행한다.

    순서 + 텍스트 매칭:
      각 XHTML 매핑에 대해 현재 MDX 포인터부터 앞으로 탐색하여
      정규화된 텍스트가 일치하는 MDX 블록을 찾는다.
      일치하지 않는 XHTML 블록(image, toc, empty paragraph 등)은
      빈 mdx_blocks로 기록한다.
    """
    from reverse_sync.mapping_recorder import record_mapping
    from reverse_sync.mdx_block_parser import parse_mdx_blocks
    from reverse_sync.text_normalizer import normalize_mdx_to_plain, collapse_ws

    xhtml_mappings = record_mapping(xhtml)
    mdx_blocks = parse_mdx_blocks(mdx)

    # 콘텐츠 블록만 필터 (frontmatter, empty, import 제외)
    NON_CONTENT = frozenset(('empty', 'frontmatter', 'import_statement'))

    entries = []
    mdx_content_indices = [
        i for i, b in enumerate(mdx_blocks)
        if b.type not in NON_CONTENT
    ]

    # MDX 콘텐츠 블록별 정규화 텍스트를 미리 계산
    mdx_plains = {}
    for ci in mdx_content_indices:
        b = mdx_blocks[ci]
        mdx_plains[ci] = collapse_ws(normalize_mdx_to_plain(b.content, b.type))

    # child mapping은 별도 처리 (parent xpath에 포함)
    child_ids = set()
    for m in xhtml_mappings:
        for cid in m.children:
            child_ids.add(cid)

    # top-level mapping만 매칭 대상
    top_mappings = [m for m in xhtml_mappings if m.block_id not in child_ids]
    mdx_ptr = 0  # MDX 콘텐츠 인덱스 포인터

    # 텍스트가 비어있거나 의미 없는 XHTML 매핑 타입
    SKIP_TYPES = frozenset(('html_block',))
    # XHTML 매핑 중 MDX 대응이 없는 것들 (image, toc 매크로 등)
    NO_MDX_XPATHS = frozenset()  # 동적 판단으로 처리

    LOOKAHEAD = 5  # 최대 앞으로 탐색할 MDX 블록 수

    for xm in top_mappings:
        xhtml_plain = collapse_ws(xm.xhtml_plain_text)

        # 빈 텍스트 XHTML 블록은 MDX 대응 없음
        if not xhtml_plain:
            entries.append({
                'xhtml_xpath': xm.xhtml_xpath,
                'xhtml_type': xm.type,
                'mdx_blocks': [],
            })
            continue

        if mdx_ptr >= len(mdx_content_indices):
            entries.append({
                'xhtml_xpath': xm.xhtml_xpath,
                'xhtml_type': xm.type,
                'mdx_blocks': [],
            })
            continue

        # 현재 MDX 블록과 텍스트 비교
        matched_at = _find_text_match(
            xhtml_plain, mdx_content_indices, mdx_plains, mdx_ptr, LOOKAHEAD)

        if matched_at is not None:
            # 매치 위치까지 MDX 포인터 이동
            mdx_ptr = matched_at
            mdx_idx = mdx_content_indices[mdx_ptr]
            matched_indices = [mdx_idx]
            mdx_ptr += 1

            # children이 있으면 후속 MDX 블록도 이 XHTML 매핑에 대응
            # 단, 다음 top-level XHTML 매핑의 텍스트와 겹치지 않는 범위에서만
            if xm.children:
                num_children = _count_child_mdx_blocks(
                    xm, xhtml_mappings, child_ids,
                    mdx_content_indices, mdx_blocks, mdx_plains,
                    mdx_ptr, top_mappings,
                    normalize_mdx_to_plain, collapse_ws,
                )
                for _ in range(num_children):
                    if mdx_ptr < len(mdx_content_indices):
                        matched_indices.append(mdx_content_indices[mdx_ptr])
                        mdx_ptr += 1

            entries.append({
                'xhtml_xpath': xm.xhtml_xpath,
                'xhtml_type': xm.type,
                'mdx_blocks': matched_indices,
            })
        else:
            # 텍스트 매치 실패 — MDX 대응 없음 (image, toc 등)
            entries.append({
                'xhtml_xpath': xm.xhtml_xpath,
                'xhtml_type': xm.type,
                'mdx_blocks': [],
            })

    mapping_data = {
        'version': 1,
        'source_page_id': page_id,
        'mdx_file': 'page.mdx',
        'mappings': entries,
    }
    return yaml.dump(mapping_data, allow_unicode=True, default_flow_style=False)


def _count_child_mdx_blocks(
    xm,
    xhtml_mappings,
    child_ids,
    mdx_content_indices,
    mdx_blocks,
    mdx_plains,
    mdx_ptr,
    top_mappings,
    normalize_mdx_to_plain,
    collapse_ws,
) -> int:
    """children이 있는 XHTML 매핑에 대응하는 MDX 블록 수를 결정한다.

    다음 비빈 top-level XHTML 매핑의 텍스트와 겹치지 않는 범위에서
    후속 MDX 블록을 소비한다.
    """
    # 현재 XHTML 매핑 이후의 top-level 매핑들을 찾아
    # 그 중 첫 번째로 유의미한 텍스트를 가진 것의 시그니처를 구한다.
    current_idx = None
    for i, tm in enumerate(top_mappings):
        if tm is xm:
            current_idx = i
            break
    if current_idx is None:
        return len(xm.children)

    # 다음 매핑들의 텍스트 시그니처 수집
    next_sigs = []
    for tm in top_mappings[current_idx + 1:]:
        sig = _strip_all_ws(collapse_ws(tm.xhtml_plain_text))
        if sig:
            next_sigs.append(sig)
        if len(next_sigs) >= 3:
            break

    if not next_sigs:
        return len(xm.children)

    # mdx_ptr부터 앞으로 스캔하면서
    # 다음 top-level 매핑의 텍스트와 일치하는 MDX 블록이 나오면 중단
    count = 0
    max_scan = len(xm.children) + 5  # 약간의 여유
    for offset in range(max_scan):
        ptr = mdx_ptr + offset
        if ptr >= len(mdx_content_indices):
            break
        mdx_idx = mdx_content_indices[ptr]
        mdx_sig = _strip_all_ws(mdx_plains[mdx_idx])
        if not mdx_sig:
            count += 1
            continue

        # 다음 top-level 매핑과 일치하면 중단
        hit = False
        for ns in next_sigs:
            if mdx_sig == ns:
                hit = True
                break
            if len(ns) >= 10 and ns[:50] in mdx_sig:
                hit = True
                break
            if len(mdx_sig) >= 10 and mdx_sig[:50] in ns:
                hit = True
                break
        if hit:
            break
        count += 1

    return count


def _strip_all_ws(text: str) -> str:
    """모든 공백 문자를 제거한다. 텍스트 서명 비교용."""
    return ''.join(text.split())


def _find_text_match(
    xhtml_plain: str,
    mdx_content_indices: List[int],
    mdx_plains: Dict[int, str],
    start_ptr: int,
    lookahead: int,
) -> Optional[int]:
    """XHTML plain text와 일치하는 MDX 블록을 전방 탐색한다.

    start_ptr부터 최대 lookahead 범위 내에서 텍스트가 일치하는
    MDX 콘텐츠 블록의 포인터 위치를 반환한다.
    일치하는 블록이 없으면 None을 반환한다.

    매칭 전략:
      1. 완전 일치 (collapse_ws 후 동일)
      2. 공백 무시 완전 일치 (모든 공백 제거 후 동일)
      3. 공백 무시 prefix 포함 (모든 공백 제거 후 앞 50자가 포함)
    """
    end_ptr = min(start_ptr + lookahead, len(mdx_content_indices))
    xhtml_sig = _strip_all_ws(xhtml_plain)

    # 1차: collapse_ws 후 완전 일치
    for ptr in range(start_ptr, end_ptr):
        mdx_idx = mdx_content_indices[ptr]
        if xhtml_plain == mdx_plains[mdx_idx]:
            return ptr

    # 2차: 공백 무시 완전 일치
    for ptr in range(start_ptr, end_ptr):
        mdx_idx = mdx_content_indices[ptr]
        mdx_sig = _strip_all_ws(mdx_plains[mdx_idx])
        if xhtml_sig == mdx_sig:
            return ptr

    # 3차: 공백 무시 prefix 포함
    if len(xhtml_sig) >= 10:
        prefix = xhtml_sig[:50]
        for ptr in range(start_ptr, end_ptr):
            mdx_idx = mdx_content_indices[ptr]
            mdx_sig = _strip_all_ws(mdx_plains[mdx_idx])
            if not mdx_sig:
                continue
            if prefix in mdx_sig or mdx_sig[:50] in xhtml_sig:
                return ptr

    return None


def find_mapping_by_sidecar(
    mdx_block_index: int,
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, BlockMapping],
) -> Optional[BlockMapping]:
    """MDX 블록 인덱스로부터 sidecar를 거쳐 BlockMapping을 찾는다.

    BlockChange.index (MDX 블록 인덱스)
      → SidecarEntry (xhtml_xpath)
      → BlockMapping
    """
    entry = mdx_to_sidecar.get(mdx_block_index)
    if entry is None:
        return None
    return xpath_to_mapping.get(entry.xhtml_xpath)
