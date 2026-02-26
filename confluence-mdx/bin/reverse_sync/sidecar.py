"""Sidecar 통합 모듈 — Block-level roundtrip sidecar 스키마/IO + Mapping lookup/인덱스.

Block-level sidecar (schema v2):
  RoundtripSidecar, SidecarBlock, DocumentEnvelope,
  build_sidecar, verify_sidecar_integrity,
  write_sidecar, load_sidecar, sha256_text

Mapping lookup (mapping.yaml 기반):
  SidecarEntry, load_sidecar_mapping, build_mdx_to_sidecar_index,
  build_xpath_to_mapping, generate_sidecar_mapping, find_mapping_by_sidecar
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.block_diff import NON_CONTENT_TYPES


# ---------------------------------------------------------------------------
# Roundtrip sidecar — block-level fragment + metadata
# ---------------------------------------------------------------------------

ROUNDTRIP_SCHEMA_VERSION = "2"


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
            "blocks": [
                {
                    "block_index": b.block_index,
                    "xhtml_xpath": b.xhtml_xpath,
                    "xhtml_fragment": b.xhtml_fragment,
                    "mdx_content_hash": b.mdx_content_hash,
                    "mdx_line_range": list(b.mdx_line_range),
                    "lost_info": b.lost_info,
                }
                for b in self.blocks
            ],
            "separators": self.separators,
            "document_envelope": {
                "prefix": self.document_envelope.prefix,
                "suffix": self.document_envelope.suffix,
            },
        }

    @staticmethod
    def from_dict(data: dict) -> "RoundtripSidecar":
        """JSON 역직렬화."""
        blocks = [
            SidecarBlock(
                block_index=b["block_index"],
                xhtml_xpath=b["xhtml_xpath"],
                xhtml_fragment=b["xhtml_fragment"],
                mdx_content_hash=b.get("mdx_content_hash", ""),
                mdx_line_range=tuple(b.get("mdx_line_range", (0, 0))),
                lost_info=b.get("lost_info", {}),
            )
            for b in data.get("blocks", [])
        ]
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

        sidecar_blocks.append(
            SidecarBlock(
                block_index=i,
                xhtml_xpath=xpath,
                xhtml_fragment=fragment,
                mdx_content_hash=mdx_hash,
                mdx_line_range=mdx_range,
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
# Mapping lookup — mapping.yaml 로드 및 인덱스 구축
# ---------------------------------------------------------------------------

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
    data = yaml.safe_load(path.read_text()) or {}
    entries = []
    for item in data.get('mappings', []):
        entries.append(SidecarEntry(
            xhtml_xpath=item['xhtml_xpath'],
            xhtml_type=item.get('xhtml_type', ''),
            mdx_blocks=item.get('mdx_blocks', []),
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
    from mdx_to_storage.parser import parse_mdx_blocks
    from text_utils import normalize_mdx_to_plain, collapse_ws

    xhtml_mappings = record_mapping(xhtml)
    mdx_blocks = parse_mdx_blocks(mdx)

    # 콘텐츠 블록만 필터 (frontmatter, empty, import 제외)
    entries = []
    mdx_content_indices = [
        i for i, b in enumerate(mdx_blocks)
        if b.type not in NON_CONTENT_TYPES
    ]
    # Empty MDX 블록 중 콘텐츠 영역 내의 것만 매핑 대상으로 추적
    # (frontmatter/import 사이의 빈 줄은 XHTML에 대응하지 않음)
    first_content_idx = mdx_content_indices[0] if mdx_content_indices else len(mdx_blocks)
    mdx_empty_indices = [
        i for i, b in enumerate(mdx_blocks)
        if b.type == 'empty' and i > first_content_idx
    ]
    empty_ptr = 0

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

    LOOKAHEAD = 5  # 최대 앞으로 탐색할 MDX 블록 수

    for xm in top_mappings:
        xhtml_plain = collapse_ws(xm.xhtml_plain_text)

        # 빈 텍스트 XHTML 블록 — empty MDX 블록과 순차 매핑
        if not xhtml_plain:
            if xm.type == 'paragraph':
                # 현재 content 포인터의 MDX 인덱스 이후의 empty만 사용
                last_content_idx = (
                    mdx_content_indices[mdx_ptr - 1] if mdx_ptr > 0 else -1
                )
                # empty_ptr를 last_content_idx 이후로 전진
                while (empty_ptr < len(mdx_empty_indices)
                       and mdx_empty_indices[empty_ptr] <= last_content_idx):
                    empty_ptr += 1
                if empty_ptr < len(mdx_empty_indices):
                    entries.append({
                        'xhtml_xpath': xm.xhtml_xpath,
                        'xhtml_type': xm.type,
                        'mdx_blocks': [mdx_empty_indices[empty_ptr]],
                    })
                    empty_ptr += 1
                else:
                    entries.append({
                        'xhtml_xpath': xm.xhtml_xpath,
                        'xhtml_type': xm.type,
                        'mdx_blocks': [],
                    })
            else:
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
                    xm, mdx_content_indices, mdx_plains,
                    mdx_ptr, top_mappings, collapse_ws,
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
        'version': 2,
        'source_page_id': page_id,
        'mdx_file': 'page.mdx',
        'mappings': entries,
    }
    if lost_infos:
        mapping_data['lost_info'] = lost_infos
    return yaml.dump(mapping_data, allow_unicode=True, default_flow_style=False)


def _count_child_mdx_blocks(
    xm,
    mdx_content_indices,
    mdx_plains,
    mdx_ptr,
    top_mappings,
    collapse_ws,
) -> int:
    """children이 있는 XHTML 매핑에 대응하는 MDX 블록 수를 결정한다.

    다음 비빈 top-level XHTML 매핑의 텍스트와 겹치지 않는 범위에서
    후속 MDX 블록을 소비한다.
    """
    current_idx = None
    for i, tm in enumerate(top_mappings):
        if tm is xm:
            current_idx = i
            break
    if current_idx is None:
        return len(xm.children)

    next_sigs = []
    for tm in top_mappings[current_idx + 1:]:
        sig = _strip_all_ws(collapse_ws(tm.xhtml_plain_text))
        if sig:
            next_sigs.append(sig)
        if len(next_sigs) >= 3:
            break

    if not next_sigs:
        return len(xm.children)

    count = 0
    max_scan = len(xm.children) + 5
    for offset in range(max_scan):
        ptr = mdx_ptr + offset
        if ptr >= len(mdx_content_indices):
            break
        mdx_idx = mdx_content_indices[ptr]
        mdx_sig = _strip_all_ws(mdx_plains[mdx_idx])
        if not mdx_sig:
            count += 1
            continue

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
    """XHTML plain text와 일치하는 MDX 블록을 전방 탐색한다."""
    end_ptr = min(start_ptr + lookahead, len(mdx_content_indices))
    xhtml_sig = _strip_all_ws(xhtml_plain)

    for ptr in range(start_ptr, end_ptr):
        mdx_idx = mdx_content_indices[ptr]
        if xhtml_plain == mdx_plains[mdx_idx]:
            return ptr

    for ptr in range(start_ptr, end_ptr):
        mdx_idx = mdx_content_indices[ptr]
        mdx_sig = _strip_all_ws(mdx_plains[mdx_idx])
        if xhtml_sig == mdx_sig:
            return ptr

    if len(xhtml_sig) >= 10:
        prefix = xhtml_sig[:50]
        for ptr in range(start_ptr, end_ptr):
            mdx_idx = mdx_content_indices[ptr]
            mdx_sig = _strip_all_ws(mdx_plains[mdx_idx])
            if not mdx_sig:
                continue
            if prefix in mdx_sig or mdx_sig[:50] in xhtml_sig:
                return ptr

    # 4차: 짧은 prefix 포함 매칭 (emoticon/lost_info 차이 허용)
    # XHTML ac:emoticon 태그가 텍스트로 치환되지 않는 경우,
    # 전체 문자열의 substring 비교가 실패할 수 있으므로
    # 앞부분 20자만으로 포함 관계를 검사한다.
    _SHORT_PREFIX = 20
    for ptr in range(start_ptr, end_ptr):
        mdx_idx = mdx_content_indices[ptr]
        mdx_sig = _strip_all_ws(mdx_plains[mdx_idx])
        if len(mdx_sig) < _SHORT_PREFIX:
            continue
        mdx_prefix = mdx_sig[:_SHORT_PREFIX]
        if mdx_prefix in xhtml_sig:
            return ptr

    return None


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
