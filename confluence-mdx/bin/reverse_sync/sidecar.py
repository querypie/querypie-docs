"""Sidecar 통합 모듈 — Block-level roundtrip sidecar 스키마/IO + Mapping lookup/인덱스.

Block-level sidecar (schema v3):
  RoundtripSidecar, SidecarBlock, DocumentEnvelope,
  build_sidecar, verify_sidecar_integrity,
  write_sidecar, load_sidecar, sha256_text

Mapping lookup (mapping.yaml v3 기반):
  SidecarChildEntry, SidecarEntry, load_sidecar_mapping, build_mdx_to_sidecar_index,
  build_xpath_to_mapping, generate_sidecar_mapping, find_mapping_by_sidecar
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.block_diff import NON_CONTENT_TYPES
from reverse_sync.xhtml_normalizer import extract_plain_text


# ---------------------------------------------------------------------------
# Roundtrip sidecar — block-level fragment + metadata
# ---------------------------------------------------------------------------

ROUNDTRIP_SCHEMA_VERSION = "3"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class DocumentEnvelope:
    """첫 블록 앞, 마지막 블록 뒤의 원본 텍스트."""

    prefix: str = ""
    suffix: str = ""


@dataclass
class SidecarBlock:
    """Individual XHTML block + metadata."""

    block_index: int
    xhtml_xpath: str
    xhtml_fragment: str
    mdx_content_hash: str = ""
    mdx_line_range: tuple = (0, 0)
    lost_info: dict = field(default_factory=dict)
    reconstruction: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "block_index": self.block_index,
            "xhtml_xpath": self.xhtml_xpath,
            "xhtml_fragment": self.xhtml_fragment,
            "mdx_content_hash": self.mdx_content_hash,
            "mdx_line_range": list(self.mdx_line_range),
            "lost_info": self.lost_info,
            "reconstruction": self.reconstruction,
        }

    @staticmethod
    def from_dict(data: dict) -> "SidecarBlock":
        return SidecarBlock(
            block_index=data["block_index"],
            xhtml_xpath=data["xhtml_xpath"],
            xhtml_fragment=data["xhtml_fragment"],
            mdx_content_hash=data.get("mdx_content_hash", ""),
            mdx_line_range=tuple(data.get("mdx_line_range", (0, 0))),
            lost_info=data.get("lost_info", {}),
            reconstruction=data.get("reconstruction"),
        )


@dataclass
class RoundtripSidecar:
    """Block-level sidecar structure."""

    schema_version: str = ROUNDTRIP_SCHEMA_VERSION
    page_id: str = ""
    mdx_sha256: str = ""
    source_xhtml_sha256: str = ""
    blocks: List[SidecarBlock] = field(default_factory=list)
    separators: List[str] = field(default_factory=list)
    document_envelope: DocumentEnvelope = field(default_factory=DocumentEnvelope)

    def reassemble_xhtml(self) -> str:
        """Fragment + separator + envelope에서 원본 XHTML을 재조립한다."""
        parts = [self.document_envelope.prefix]
        for i, block in enumerate(self.blocks):
            parts.append(block.xhtml_fragment)
            if i < len(self.separators):
                parts.append(self.separators[i])
        parts.append(self.document_envelope.suffix)
        return "".join(parts)

    def to_dict(self) -> dict:
        """JSON 직렬화."""
        return {
            "schema_version": self.schema_version,
            "page_id": self.page_id,
            "mdx_sha256": self.mdx_sha256,
            "source_xhtml_sha256": self.source_xhtml_sha256,
            "blocks": [b.to_dict() for b in self.blocks],
            "separators": self.separators,
            "document_envelope": {
                "prefix": self.document_envelope.prefix,
                "suffix": self.document_envelope.suffix,
            },
        }

    @staticmethod
    def from_dict(data: dict) -> "RoundtripSidecar":
        """JSON 역직렬화."""
        blocks = [SidecarBlock.from_dict(b) for b in data.get("blocks", [])]
        env = data.get("document_envelope", {})
        return RoundtripSidecar(
            schema_version=data.get("schema_version", ROUNDTRIP_SCHEMA_VERSION),
            page_id=data.get("page_id", ""),
            mdx_sha256=data.get("mdx_sha256", ""),
            source_xhtml_sha256=data.get("source_xhtml_sha256", ""),
            blocks=blocks,
            separators=data.get("separators", []),
            document_envelope=DocumentEnvelope(
                prefix=env.get("prefix", ""),
                suffix=env.get("suffix", ""),
            ),
        )


def build_sidecar_identity_index(
    blocks: List[SidecarBlock],
) -> Dict[str, List[SidecarBlock]]:
    """Group sidecar blocks by content hash in deterministic line-range order."""
    grouped: Dict[str, List[SidecarBlock]] = defaultdict(list)
    for block in blocks:
        if not block.mdx_content_hash:
            continue
        grouped[block.mdx_content_hash].append(block)
    for content_hash, content_blocks in grouped.items():
        grouped[content_hash] = sorted(
            content_blocks,
            key=lambda block: (tuple(block.mdx_line_range), block.block_index),
        )
    return dict(grouped)


def find_sidecar_block_by_identity(
    blocks: List[SidecarBlock],
    mdx_content_hash: str,
    mdx_line_range: tuple[int, int] | None = None,
    occurrence_index: int = 0,
) -> Optional[SidecarBlock]:
    """Resolve a block using hash first, then line range, then stable order."""
    candidates = build_sidecar_identity_index(blocks).get(mdx_content_hash, [])
    if not candidates:
        return None
    if mdx_line_range is not None:
        ranged = [
            block for block in candidates
            if tuple(block.mdx_line_range) == tuple(mdx_line_range)
        ]
        if ranged:
            return ranged[occurrence_index] if occurrence_index < len(ranged) else None
    return candidates[occurrence_index] if occurrence_index < len(candidates) else None


def verify_sidecar_integrity(
    sidecar: RoundtripSidecar,
    expected_xhtml: str,
) -> None:
    """Fragment + separator + envelope 재조립이 원본과 byte-equal인지 검증한다.

    실패 시 ValueError를 발생시킨다.
    """
    reassembled = sidecar.reassemble_xhtml()

    if reassembled != expected_xhtml:
        first_offset = -1
        for j, (c1, c2) in enumerate(zip(reassembled, expected_xhtml)):
            if c1 != c2:
                first_offset = j
                break
        if first_offset < 0 and len(reassembled) != len(expected_xhtml):
            first_offset = min(len(reassembled), len(expected_xhtml))
        raise ValueError(
            f"Sidecar integrity check failed: "
            f"reassembled ({len(reassembled)}) != expected ({len(expected_xhtml)}), "
            f"first mismatch at offset {first_offset}"
        )


def build_sidecar(
    page_xhtml_text: str,
    mdx_text: str,
    page_id: str = "",
) -> RoundtripSidecar:
    """Block-level sidecar를 생성한다.

    Fragment 추출 → MDX alignment → 무결성 검증 → RoundtripSidecar 반환.
    """
    from reverse_sync.fragment_extractor import extract_block_fragments
    from reverse_sync.mapping_recorder import record_mapping
    from reverse_sync.mdx_block_parser import parse_mdx_blocks

    # 1. XHTML mapping + fragment 추출
    xhtml_mappings = record_mapping(page_xhtml_text)
    frag_result = extract_block_fragments(page_xhtml_text)
    mdx_blocks = parse_mdx_blocks(mdx_text)
    id_to_mapping = {mapping.block_id: mapping for mapping in xhtml_mappings}

    # 2. top-level mapping 필터링
    child_ids = set()
    for m in xhtml_mappings:
        child_ids.update(m.children)
    top_mappings = [m for m in xhtml_mappings if m.block_id not in child_ids]

    # 3. MDX content 블록 (frontmatter, empty, import 제외)
    mdx_content_blocks = [b for b in mdx_blocks if b.type not in NON_CONTENT_TYPES]

    # 4. Block 생성 — fragment와 top-level mapping을 정렬
    sidecar_blocks: List[SidecarBlock] = []
    for i, fragment in enumerate(frag_result.fragments):
        xpath = top_mappings[i].xhtml_xpath if i < len(top_mappings) else f"unknown[{i}]"

        # 순차 1:1 대응 (향후 block alignment로 개선)
        mdx_block = mdx_content_blocks[i] if i < len(mdx_content_blocks) else None
        mdx_hash = sha256_text(mdx_block.content) if mdx_block else ""
        mdx_range = (mdx_block.line_start, mdx_block.line_end) if mdx_block else (0, 0)
        mapping = top_mappings[i] if i < len(top_mappings) else None

        sidecar_blocks.append(
            SidecarBlock(
                block_index=i,
                xhtml_xpath=xpath,
                xhtml_fragment=fragment,
                mdx_content_hash=mdx_hash,
                mdx_line_range=mdx_range,
                reconstruction=_build_reconstruction_metadata(fragment, mapping, id_to_mapping),
            )
        )

    sidecar = RoundtripSidecar(
        page_id=page_id,
        mdx_sha256=sha256_text(mdx_text),
        source_xhtml_sha256=sha256_text(page_xhtml_text),
        blocks=sidecar_blocks,
        separators=frag_result.separators,
        document_envelope=DocumentEnvelope(
            prefix=frag_result.prefix,
            suffix=frag_result.suffix,
        ),
    )

    # 5. 무결성 검증
    verify_sidecar_integrity(sidecar, page_xhtml_text)

    return sidecar


def _build_reconstruction_metadata(
    fragment: str,
    mapping: BlockMapping | None,
    id_to_mapping: Dict[str, BlockMapping],
) -> Optional[dict]:
    if mapping is None:
        return None

    metadata: dict[str, Any] = {
        "kind": mapping.type,
        "old_plain_text": extract_plain_text(fragment),
    }
    if mapping.type == "paragraph":
        metadata["anchors"] = []
    elif mapping.type == "list":
        metadata["ordered"] = mapping.xhtml_xpath.startswith("ol[")
        metadata["items"] = []
    elif mapping.children:
        child_plain_texts = [
            id_to_mapping[child_id].xhtml_plain_text.strip()
            for child_id in mapping.children
            if child_id in id_to_mapping and id_to_mapping[child_id].xhtml_plain_text.strip()
        ]
        if child_plain_texts:
            metadata["old_plain_text"] = " ".join(child_plain_texts)
        metadata["child_xpaths"] = [
            id_to_mapping[child_id].xhtml_xpath
            for child_id in mapping.children
            if child_id in id_to_mapping
        ]
    return metadata


def write_sidecar(sidecar: RoundtripSidecar, path: Path) -> None:
    """RoundtripSidecar를 JSON 파일로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sidecar.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_sidecar(path: Path) -> RoundtripSidecar:
    """JSON 파일에서 RoundtripSidecar를 로드한다."""
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("invalid sidecar payload")
    if data.get("schema_version") != ROUNDTRIP_SCHEMA_VERSION:
        raise ValueError(
            f"expected schema_version={ROUNDTRIP_SCHEMA_VERSION}, "
            f"got {data.get('schema_version')}"
        )
    return RoundtripSidecar.from_dict(data)


# ---------------------------------------------------------------------------
# Mapping lookup — mapping.yaml v3 로드 및 인덱스 구축
# ---------------------------------------------------------------------------

# XHTML record_mapping type → 호환 MDX parse_mdx type
_TYPE_COMPAT: Dict[str, frozenset] = {
    'heading':    frozenset({'heading'}),
    'paragraph':  frozenset({'paragraph'}),
    'list':       frozenset({'list'}),
    'code':       frozenset({'code_block'}),
    'table':      frozenset({'table', 'html_block'}),
    'html_block': frozenset({'callout', 'details', 'html_block', 'blockquote',
                             'figure', 'badge', 'hr'}),
}

# MDX 출력을 생성하지 않는 XHTML 매크로 이름
_SKIP_MACROS = frozenset({'toc', 'children'})


def _should_skip_xhtml(xm: Any) -> bool:
    """toc, children 등 MDX 출력이 없는 XHTML 매크로를 판별한다."""
    xpath = xm.xhtml_xpath
    for skip_name in _SKIP_MACROS:
        if xpath.startswith(f'macro-{skip_name}'):
            return True
    return False


def _type_compatible(xhtml_type: str, mdx_type: str) -> bool:
    """XHTML 타입과 MDX 블록 타입이 호환되는지 확인한다."""
    return mdx_type in _TYPE_COMPAT.get(xhtml_type, frozenset())



def _align_children(
    xm: Any,
    mdx_block: Any,
    id_to_mapping: Dict[str, Any],
) -> List[Dict]:
    """XHTML children과 MDX Block.children을 타입 기반 순차 정렬한다.

    각 XHTML child에 대응하는 MDX child의 절대 line range를 계산하여
    children entry 목록을 반환한다.

    절대 line = parent_mdx_block.line_start + child.line_start
    (callout의 경우 첫 줄이 <Callout...>이므로 +1 offset이 자연스럽게 적용됨)
    """
    child_entries = []
    # NON_CONTENT_TYPES는 런타임에 임포트 (순환 참조 방지)
    from reverse_sync.block_diff import NON_CONTENT_TYPES
    mdx_children = [c for c in mdx_block.children if c.type not in NON_CONTENT_TYPES]
    mdx_child_ptr = 0

    for child_id in xm.children:
        child_mapping = id_to_mapping.get(child_id)
        if child_mapping is None:
            continue

        if mdx_child_ptr < len(mdx_children):
            mdx_child = mdx_children[mdx_child_ptr]
            if _type_compatible(child_mapping.type, mdx_child.type):
                abs_start = mdx_block.line_start + mdx_child.line_start
                abs_end = mdx_block.line_start + mdx_child.line_end
                child_entries.append({
                    'xhtml_xpath': child_mapping.xhtml_xpath,
                    'xhtml_block_id': child_id,
                    'mdx_line_start': abs_start,
                    'mdx_line_end': abs_end,
                })
                mdx_child_ptr += 1
                continue

        child_entries.append({
            'xhtml_xpath': child_mapping.xhtml_xpath,
            'xhtml_block_id': child_id,
            'mdx_line_start': 0,
            'mdx_line_end': 0,
        })

    return child_entries


@dataclass
class SidecarChildEntry:
    """mapping.yaml v3 children 항목."""
    xhtml_xpath: str
    xhtml_block_id: str
    mdx_line_start: int = 0
    mdx_line_end: int = 0


@dataclass
class SidecarEntry:
    xhtml_xpath: str
    xhtml_type: str
    mdx_blocks: List[int] = field(default_factory=list)
    mdx_line_start: int = 0
    mdx_line_end: int = 0
    children: List[SidecarChildEntry] = field(default_factory=list)


def load_sidecar_mapping(mapping_path: str) -> List[SidecarEntry]:
    """mapping.yaml 파일을 로드하여 SidecarEntry 목록을 반환한다."""
    path = Path(mapping_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Sidecar mapping not found: {mapping_path}\n"
            f"Forward converter를 실행하여 mapping.yaml을 생성하세요."
        )
    data = yaml.safe_load(path.read_text()) or {}
    entries = []
    for item in data.get('mappings', []):
        children = [
            SidecarChildEntry(
                xhtml_xpath=ch.get('xhtml_xpath', ''),
                xhtml_block_id=ch.get('xhtml_block_id', ''),
                mdx_line_start=ch.get('mdx_line_start', 0),
                mdx_line_end=ch.get('mdx_line_end', 0),
            )
            for ch in item.get('children', [])
        ]
        entries.append(SidecarEntry(
            xhtml_xpath=item['xhtml_xpath'],
            xhtml_type=item.get('xhtml_type', ''),
            mdx_blocks=item.get('mdx_blocks', []),
            mdx_line_start=item.get('mdx_line_start', 0),
            mdx_line_end=item.get('mdx_line_end', 0),
            children=children,
        ))
    return entries


def load_page_lost_info(mapping_path: str) -> dict:
    """mapping.yaml에서 페이지 레벨 lost_info를 로드한다."""
    path = Path(mapping_path)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data.get('lost_info', {})


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
    lost_infos: dict | None = None,
) -> str:
    """XHTML + MDX로부터 mapping.yaml v3 내용을 생성한다.

    타입 호환성 기반 순차 정렬(two-pointer)로 XHTML top-level 블록과
    MDX content 블록을 매핑한다. 텍스트 비교 없이 블록 타입만 사용한다.

    타입 불일치 시 XHTML 블록이 MDX 출력을 생성하지 않은 것으로 판단
    (ac:image → figure 없는 MDX, toc 등). MDX 포인터는 유지된다.
    """
    from reverse_sync.mapping_recorder import record_mapping
    from mdx_to_storage.parser import parse_mdx_blocks

    xhtml_mappings = record_mapping(xhtml)
    mdx_blocks_all = parse_mdx_blocks(mdx)

    # MDX 콘텐츠 블록만 필터 (frontmatter, empty, import 제외), 원본 인덱스 보존
    mdx_content_indexed = [
        (i, b) for i, b in enumerate(mdx_blocks_all)
        if b.type not in NON_CONTENT_TYPES
    ]

    # child IDs 수집 → top-level mapping 필터링
    child_ids: set = set()
    for m in xhtml_mappings:
        child_ids.update(m.children)
    top_mappings = [m for m in xhtml_mappings if m.block_id not in child_ids]

    # block_id → BlockMapping (children 해석용)
    id_to_mapping = {m.block_id: m for m in xhtml_mappings}

    entries = []
    # MDX H1 헤딩(페이지 제목)은 XHTML 본문에 존재하지 않으므로 건너뛴다.
    # forward converter는 MDX 첫 줄에 `# <페이지 제목>`을 자동 생성하며,
    # 이 블록은 Confluence XHTML의 페이지 제목(본문 외부)에 해당한다.
    mdx_ptr = 0
    while (mdx_ptr < len(mdx_content_indexed)
           and mdx_content_indexed[mdx_ptr][1].type == 'heading'
           and mdx_content_indexed[mdx_ptr][1].content.startswith('# ')):
        mdx_ptr += 1

    for xm in top_mappings:
        # 스킵 매크로 (toc, children 등)
        if _should_skip_xhtml(xm):
            entries.append({
                'xhtml_xpath': xm.xhtml_xpath,
                'xhtml_type': xm.type,
                'mdx_blocks': [],
            })
            continue

        # 빈 텍스트 paragraph XHTML 블록 — MDX 콘텐츠 대응 없음
        # (빈 <p>는 MDX의 empty 줄에 해당하며 content 블록이 아님)
        if not xm.xhtml_plain_text.strip() and xm.type == 'paragraph':
            entries.append({
                'xhtml_xpath': xm.xhtml_xpath,
                'xhtml_type': xm.type,
                'mdx_blocks': [],
            })
            continue

        if mdx_ptr >= len(mdx_content_indexed):
            entries.append({
                'xhtml_xpath': xm.xhtml_xpath,
                'xhtml_type': xm.type,
                'mdx_blocks': [],
            })
            continue

        mdx_idx, mdx_block = mdx_content_indexed[mdx_ptr]

        if _type_compatible(xm.type, mdx_block.type):
            entry: Dict[str, Any] = {
                'xhtml_xpath': xm.xhtml_xpath,
                'xhtml_type': xm.type,
                'mdx_blocks': [mdx_idx],
                'mdx_line_start': mdx_block.line_start,
                'mdx_line_end': mdx_block.line_end,
            }
            # compound block (callout/details 등): children 정렬
            if xm.children and mdx_block.children:
                child_entries = _align_children(xm, mdx_block, id_to_mapping)
                if child_entries:
                    entry['children'] = child_entries
            entries.append(entry)
            mdx_ptr += 1
        else:
            # 타입 불일치 → XHTML 블록이 MDX 출력을 생성하지 않음
            # MDX 포인터는 유지 (MDX 블록이 다음 XHTML과 매칭될 수 있음)
            entries.append({
                'xhtml_xpath': xm.xhtml_xpath,
                'xhtml_type': xm.type,
                'mdx_blocks': [],
            })

    mapping_data: Dict[str, Any] = {
        'version': 3,
        'source_page_id': page_id,
        'mdx_file': 'page.mdx',
        'mappings': entries,
    }
    if lost_infos:
        mapping_data['lost_info'] = lost_infos
    return yaml.dump(mapping_data, allow_unicode=True, default_flow_style=False)



def find_mapping_by_sidecar(
    mdx_block_index: int,
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, BlockMapping],
) -> Optional[BlockMapping]:
    """MDX 블록 인덱스로부터 sidecar를 거쳐 BlockMapping을 찾는다."""
    entry = mdx_to_sidecar.get(mdx_block_index)
    if entry is None:
        return None
    return xpath_to_mapping.get(entry.xhtml_xpath)
