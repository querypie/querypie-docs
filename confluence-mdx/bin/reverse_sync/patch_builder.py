"""패치 빌더 — MDX diff 변경과 XHTML 매핑을 결합하여 XHTML 패치를 생성."""
import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

from mdx_to_storage.emitter import emit_block
from mdx_to_storage.parser import parse_mdx
from reverse_sync.block_diff import BlockChange, NON_CONTENT_TYPES
from reverse_sync.mapping_recorder import BlockMapping, record_mapping
from mdx_to_storage.parser import Block as MdxBlock
from text_utils import (
    normalize_mdx_to_plain, collapse_ws,
)
from reverse_sync.sidecar import (
    RoundtripSidecar,
    SidecarBlock,
    find_mapping_by_sidecar,
    find_sidecar_block_by_identity,
    sha256_text,
    SidecarEntry,
    build_mdx_line_range_index,
)
from reverse_sync.lost_info_patcher import apply_lost_info, distribute_lost_info_to_mappings
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_xhtml_element, mdx_block_to_inner_xhtml
from reverse_sync.reconstructors import (
    sidecar_block_requires_reconstruction,
    reconstruct_fragment_with_sidecar,
    rewrite_on_stored_template,
)


def is_markdown_table(content: str) -> bool:
    """Content가 Markdown table 형식인지 판별한다."""
    lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        return False
    pipe_lines = sum(1 for l in lines if l.startswith('|') and l.endswith('|'))
    return pipe_lines >= 2


_CLEAN_BLOCK_TYPES = frozenset(("heading", "code_block", "hr"))


def _is_container_sidecar(sidecar_block: Optional[SidecarBlock]) -> bool:
    """container kind의 sidecar block인지 판별한다."""
    if sidecar_block is None or sidecar_block.reconstruction is None:
        return False
    return sidecar_block.reconstruction.get('kind') == 'container'


def _build_mdx_to_sidecar_from_v3(
    roundtrip_sidecar: RoundtripSidecar,
    original_blocks: List[MdxBlock],
) -> Dict[int, SidecarEntry]:
    """roundtrip sidecar v3와 original_blocks에서 mdx_to_sidecar 인덱스를 생성한다.

    mapping.yaml 없이 v3 sidecar의 mdx_line_range를 기준으로
    original_blocks의 절대 인덱스 → SidecarEntry를 구축한다.
    find_mapping_by_sidecar()가 entry.xhtml_xpath만 사용하므로
    xhtml_xpath 필드만 채운다.
    """
    from reverse_sync.block_diff import NON_CONTENT_TYPES as _NON_CONTENT
    line_range_idx = build_mdx_line_range_index(roundtrip_sidecar)
    result: Dict[int, SidecarEntry] = {}
    for idx, block in enumerate(original_blocks):
        if block.type in _NON_CONTENT:
            continue
        sc_block = line_range_idx.get((block.line_start, block.line_end))
        if sc_block is None:
            continue
        result[idx] = SidecarEntry(
            xhtml_xpath=sc_block.xhtml_xpath,
            xhtml_type="",
            mdx_blocks=[idx],
        )
    return result


def _contains_preserved_anchor_markup(xhtml_text: str) -> bool:
    """preservation unit이 있으면 clean whole-fragment replacement 대상이 아니다."""
    return "<ac:" in xhtml_text or "<ri:" in xhtml_text


def _is_clean_block(
    block_type: str,
    mapping: Optional[BlockMapping],
    sidecar_block: Optional[SidecarBlock],
) -> bool:
    """Phase 2 clean block 여부를 판별한다."""
    if mapping is None:
        return False

    if block_type in _CLEAN_BLOCK_TYPES:
        return True

    if sidecar_block is not None:
        recon = sidecar_block.reconstruction
        if recon is None:
            return False
        if recon.get("kind") == "paragraph":
            return len(recon.get("anchors", [])) == 0
        return False

    return block_type == "paragraph" and not _contains_preserved_anchor_markup(
        mapping.xhtml_text
    )


def _can_replace_table_fragment(
    change: BlockChange,
    mapping: Optional[BlockMapping],
    roundtrip_sidecar: Optional[RoundtripSidecar],
) -> bool:
    """table 계열을 whole-fragment replacement로 처리할 수 있는지 판별한다."""
    if roundtrip_sidecar is None or mapping is None:
        return False
    if _contains_preserved_anchor_markup(mapping.xhtml_text):
        return False
    block = change.new_block or change.old_block
    return (
        (block.type == "html_block" and block.content.lstrip().startswith("<table"))
        or is_markdown_table(change.old_block.content)
    )


def _emit_replacement_fragment(block: MdxBlock) -> str:
    """Block content를 현재 forward emitter 기준 fragment로 변환한다."""
    parsed_blocks = [parsed for parsed in parse_mdx(block.content) if parsed.type != "empty"]
    if len(parsed_blocks) == 1:
        return emit_block(parsed_blocks[0])
    return mdx_block_to_xhtml_element(block)


def _build_replace_fragment_patch(
    mapping: BlockMapping,
    new_block: MdxBlock,
    sidecar_block: Optional[SidecarBlock] = None,
    mapping_lost_info: Optional[dict] = None,
) -> Dict[str, str]:
    """whole-fragment replacement patch를 생성한다."""
    new_element = _emit_replacement_fragment(new_block)
    if (sidecar_block_requires_reconstruction(sidecar_block)
            or _is_container_sidecar(sidecar_block)):
        new_element = reconstruct_fragment_with_sidecar(new_element, sidecar_block)
    block_lost = (mapping_lost_info or {}).get(mapping.block_id, {})
    if block_lost:
        new_element = apply_lost_info(new_element, block_lost)
    return {
        "action": "replace_fragment",
        "xhtml_xpath": mapping.xhtml_xpath,
        "new_element_xhtml": new_element,
    }


def _find_roundtrip_sidecar_block(
    change: BlockChange,
    mapping: Optional[BlockMapping],
    roundtrip_sidecar: Optional[RoundtripSidecar],
    xpath_to_sidecar_block: Dict[str, SidecarBlock],
) -> Optional[SidecarBlock]:
    """xpath → identity hash 순으로 roundtrip sidecar block을 탐색한다.

    1. xpath로 빠른 조회
    2. mdx_content_hash + mdx_line_range로 검증 → 일치하면 확정 반환
    3. 검증 실패 시 find_sidecar_block_by_identity로 더 정확한 블록 탐색
    4. identity도 없으면 xpath 결과를 fallback으로 반환
    """
    if roundtrip_sidecar is None:
        return None

    identity_block = change.old_block or change.new_block

    # xpath 조회
    xpath_match: Optional[SidecarBlock] = None
    if mapping is not None:
        xpath_match = xpath_to_sidecar_block.get(mapping.xhtml_xpath)

    # hash + line range 검증 → 확정 일치
    if xpath_match is not None and identity_block is not None:
        expected_hash = sha256_text(identity_block.content) if identity_block.content else ""
        expected_range = (identity_block.line_start, identity_block.line_end)
        if (
            xpath_match.mdx_content_hash == expected_hash
            and tuple(xpath_match.mdx_line_range) == expected_range
        ):
            return xpath_match

    # identity fallback: mapping.yaml이 어긋난 경우 hash 기반으로 재탐색
    # block family(paragraph/list/table 등)가 일치하는 경우에만 반환하여 cross-type 오매칭 방지
    if identity_block is not None and identity_block.content:
        identity_match = find_sidecar_block_by_identity(
            roundtrip_sidecar.blocks,
            sha256_text(identity_block.content),
            (identity_block.line_start, identity_block.line_end),
        )
        if identity_match is not None:
            if mapping is not None and _mapping_block_family(mapping) == _xpath_block_family(identity_match.xhtml_xpath):
                return identity_match

    # xpath 결과를 마지막 fallback으로 반환 (hash 불일치라도 없는 것보다 나음)
    return xpath_match


def _xpath_root_tag(xpath: str) -> str:
    """Extract the top-level tag portion from an xpath-like storage path."""
    head = xpath.split("/", 1)[0]
    return head.split("[", 1)[0]


def _xpath_block_family(xpath: str) -> str:
    """xpath의 최상위 태그를 block family 문자열로 변환한다.

    알 수 없는 태그(pre, blockquote, ac:* 등)는 raw tag를 반환하여
    cross-type 보호 목적상 보수적으로 동작한다.
    """
    root_tag = _xpath_root_tag(xpath)
    if root_tag == "p":
        return "paragraph"
    if root_tag in {"ul", "ol"}:
        return "list"
    if root_tag == "table":
        return "table"
    if root_tag.startswith("h") and root_tag[1:].isdigit():
        return "heading"
    return root_tag


def _mapping_block_family(mapping: BlockMapping) -> str:
    if mapping.type in {"paragraph", "list", "heading", "table"}:
        return mapping.type
    return _xpath_block_family(mapping.xhtml_xpath)




def _apply_mdx_diff_to_xhtml(
    old_mdx_plain: str,
    new_mdx_plain: str,
    xhtml_plain: str,
) -> str:
    """MDX old→new diff를 XHTML plain text에 적용한다.

    MDX old와 XHTML text의 문자 정렬(alignment)을 구축하고,
    MDX old→new 변경의 위치를 XHTML 상의 위치로 매핑하여 적용한다.
    이를 통해 XHTML의 공백 구조를 보존하면서 콘텐츠만 업데이트한다.
    (align_chars + transfer_text_changes 알고리즘의 인라인 구현)
    """
    # 1. MDX old ↔ XHTML text 문자 정렬 (비공백 우선 → 공백 gap 채우기)
    src_ns = [(i, c) for i, c in enumerate(old_mdx_plain) if not c.isspace()]
    tgt_ns = [(i, c) for i, c in enumerate(xhtml_plain) if not c.isspace()]
    sm = difflib.SequenceMatcher(
        None, ''.join(c for _, c in src_ns), ''.join(c for _, c in tgt_ns), autojunk=False)
    char_map: Dict[int, int] = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                char_map[src_ns[i1 + k][0]] = tgt_ns[j1 + k][0]
    # 인접 앵커 사이의 공백 매핑
    anchors = sorted(char_map.items())
    bounds = [(-1, -1)] + anchors + [(len(old_mdx_plain), len(xhtml_plain))]
    for idx in range(len(bounds) - 1):
        s_lo, t_lo = bounds[idx]
        s_hi, t_hi = bounds[idx + 1]
        s_sp = [j for j in range(s_lo + 1, s_hi) if old_mdx_plain[j].isspace()]
        t_sp = [j for j in range(t_lo + 1, t_hi) if xhtml_plain[j].isspace()]
        for s, t in zip(s_sp, t_sp):
            char_map[s] = t

    # 2. MDX old → new 변경 추출
    matcher = difflib.SequenceMatcher(None, old_mdx_plain, new_mdx_plain, autojunk=False)

    # 3. 변경을 XHTML 위치로 매핑
    edits = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        replacement = new_mdx_plain[j1:j2] if tag != 'delete' else ''
        if tag in ('replace', 'delete'):
            mapped = sorted(char_map[k] for k in range(i1, i2) if k in char_map)
            if not mapped:
                continue
            edits.append((mapped[0], mapped[-1] + 1, replacement))
        elif tag == 'insert':
            # 삽입 위치: 앞쪽에서 마지막 매핑된 문자 + 1
            xpos = 0
            for k in range(i1 - 1, -1, -1):
                if k in char_map:
                    xpos = char_map[k] + 1
                    break
            else:
                for k in range(i1, max(char_map) + 1) if char_map else []:
                    if k in char_map:
                        xpos = char_map[k]
                        break
            edits.append((xpos, xpos, replacement))

    # 4. 역순 적용
    chars = list(xhtml_plain)
    for xstart, xend, repl in reversed(edits):
        chars[xstart:xend] = list(repl)
    return ''.join(chars)


def _find_best_list_mapping_by_text(
    old_plain: str,
    mappings: List[BlockMapping],
    used_ids: set,
) -> Optional[BlockMapping]:
    """old_plain prefix로 미사용 list mapping을 찾는다.

    sidecar lookup이 잘못된 list mapping을 반환했을 때 plain text로 올바른
    mapping을 복원하기 위한 fallback이다.
    prefix 40자를 기준으로 xhtml_plain_text를 검색한다.

    FC가 한국어 조사(을/를/이/가 등) 앞에 공백을 삽입하므로,
    공백을 제거한 상태로 비교한다 (예: "App을" vs "App 을").
    """
    prefix = old_plain[:40].strip()
    if not prefix:
        return None
    prefix_nospace = prefix.replace(' ', '')
    for m in mappings:
        if m.type != 'list' or m.block_id in used_ids:
            continue
        if prefix_nospace in m.xhtml_plain_text.replace(' ', ''):
            return m
    return None


def _resolve_mapping_for_change(
    change: BlockChange,
    old_plain: str,
    mappings: List[BlockMapping],
    used_ids: set,
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
) -> tuple:
    """변경에 대한 매핑과 처리 전략을 결정한다.

    Returns:
        (strategy, mapping) 튜플.
        strategy: 'direct' | 'containing' | 'list' | 'table' | 'skip'
        mapping: 해당 BlockMapping 또는 None
    """

    # Sidecar 직접 조회 (O(1))
    mapping = find_mapping_by_sidecar(
        change.index, mdx_to_sidecar, xpath_to_mapping)

    if mapping is None:
        if change.old_block.type == 'list':
            return ('list', None)
        if is_markdown_table(change.old_block.content):
            return ('table', None)
        return ('skip', None)

    # callout 블록은 항상 containing 전략 사용
    # (_convert_callout_inner가 <li><p> 구조를 생성할 수 없으므로)
    if change.old_block.type == 'callout':
        return ('containing', mapping)

    # Parent mapping이 children을 가지면 containing 전략으로 위임
    if mapping.children:
        if change.old_block.type == 'list':
            return ('list', mapping)
        return ('containing', mapping)

    # list 블록은 list 전략 사용 (direct 교체 시 <ac:image> 등 Confluence 태그 손실 방지)
    if change.old_block.type == 'list':
        return ('list', mapping)

    # table 블록은 table 전략 사용 (direct 교체 시 <ac:link> 등 Confluence 태그 손실 방지)
    if is_markdown_table(change.old_block.content):
        return ('table', mapping)

    return ('direct', mapping)


def build_patches(
    changes: List[BlockChange],
    original_blocks: List[MdxBlock],
    improved_blocks: List[MdxBlock],
    mappings: List[BlockMapping],
    mdx_to_sidecar: Optional[Dict[int, SidecarEntry]] = None,
    xpath_to_mapping: Optional[Dict[str, 'BlockMapping']] = None,
    alignment: Optional[Dict[int, int]] = None,
    page_lost_info: Optional[dict] = None,
    roundtrip_sidecar: Optional[RoundtripSidecar] = None,
) -> List[Dict[str, str]]:
    """diff 변경과 매핑을 결합하여 XHTML 패치 목록을 구성한다.

    mdx_to_sidecar=None (기본값)이면 roundtrip_sidecar v3에서 자동으로 구축한다.
    """
    # v3 sidecar 기반 경로: mdx_to_sidecar가 없으면 roundtrip_sidecar에서 구축
    if mdx_to_sidecar is None:
        if roundtrip_sidecar is not None:
            mdx_to_sidecar = _build_mdx_to_sidecar_from_v3(
                roundtrip_sidecar, original_blocks)
        else:
            mdx_to_sidecar = {}
    xpath_to_mapping = xpath_to_mapping or {}
    patches = []
    xpath_to_sidecar_block: Dict[str, SidecarBlock] = {}
    if roundtrip_sidecar is not None:
        xpath_to_sidecar_block = {
            block.xhtml_xpath: block for block in roundtrip_sidecar.blocks
        }
    used_ids: set = set()  # 이미 매칭된 mapping block_id (중복 매칭 방지)
    # child → parent 역참조 맵 (부모-자식 간 중복 매칭 방지)
    child_to_parent: dict = {}
    for m in mappings:
        for child_id in m.children:
            child_to_parent[child_id] = m.block_id

    # block_id → BlockMapping 인덱스 (child 해석용)
    id_to_mapping: Dict[str, BlockMapping] = {m.block_id: m for m in mappings}

    # 블록 레벨 lost_info 분배
    mapping_lost_info = distribute_lost_info_to_mappings(
        mappings, page_lost_info or {})

    def _mark_used(block_id: str, m: BlockMapping):
        """매핑 사용 시 부모/자식도 함께 사용 완료로 표시."""
        used_ids.add(block_id)
        for child_id in m.children:
            used_ids.add(child_id)
        parent_id = child_to_parent.get(block_id)
        if parent_id:
            used_ids.add(parent_id)

    # delete + add 쌍 탐지: 같은 인덱스에서 삭제 후 추가된 블록은
    # 구조 변경 없이 텍스트 전이로 처리 (callout 등 복합 블록의 DOM 파괴 방지)
    _delete_by_idx: dict = {}
    _add_by_idx: dict = {}
    for change in changes:
        if change.change_type == 'deleted':
            _delete_by_idx[change.index] = change
        elif change.change_type == 'added':
            _add_by_idx[change.index] = change
    _paired_indices: set = set()
    for idx, del_change in _delete_by_idx.items():
        if idx not in _add_by_idx:
            continue
        add_change = _add_by_idx[idx]
        if del_change.old_block.type in NON_CONTENT_TYPES:
            continue
        mapping = find_mapping_by_sidecar(
            idx, mdx_to_sidecar, xpath_to_mapping)
        if mapping is None:
            continue
        sidecar_block = xpath_to_sidecar_block.get(mapping.xhtml_xpath)
        if _is_clean_block(
            add_change.new_block.type,
            mapping,
            sidecar_block,
        ) or _can_replace_table_fragment(del_change, mapping, roundtrip_sidecar):
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    add_change.new_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
            _paired_indices.add(idx)
            _mark_used(mapping.block_id, mapping)
            continue
        # paired delete+add이지만 clean/table fragment 교체 불가:
        # anchor 재구성, preserved anchor, parameter-bearing container, clean container 순으로 분기
        sidecar_block = xpath_to_sidecar_block.get(mapping.xhtml_xpath)
        if sidecar_block_requires_reconstruction(sidecar_block):
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    add_change.new_block,
                    sidecar_block=sidecar_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
        elif _contains_preserved_anchor_markup(mapping.xhtml_text) and not _is_container_sidecar(sidecar_block):
            # sidecar 없는 preserved anchor → rewrite_on_stored_template (구조 보존)
            # container sidecar가 있으면 rewrite_on_stored_template이 <ac:parameter>를
            # 오염시키므로 아래 분기로 보낸다
            new_plain = normalize_mdx_to_plain(
                add_change.new_block.content, add_change.new_block.type)
            preserved = rewrite_on_stored_template(mapping.xhtml_text, new_plain)
            block_lost = mapping_lost_info.get(mapping.block_id, {})
            if block_lost:
                preserved = apply_lost_info(preserved, block_lost)
            patches.append({
                'action': 'replace_fragment',
                'xhtml_xpath': mapping.xhtml_xpath,
                'new_element_xhtml': preserved,
            })
        elif _is_container_sidecar(sidecar_block) and '<ac:parameter' in mapping.xhtml_text:
            # parameter-bearing container (expand 등): _apply_outer_wrapper_template이
            # body children만 교체하므로 parameter 보존 + body 변경 적용 모두 가능.
            # _apply_outer_wrapper_template이 body children만 교체하므로
            # parameter 보존과 body 변경 적용 모두 가능.
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    add_change.new_block,
                    sidecar_block=sidecar_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
        else:
            # clean container sidecar (parameter 없음) / sidecar 없음 + anchor 없음
            # → sidecar 기반 reconstruct로 전환 (Phase 5 Axis 1)
            # clean container: reconstruct_container_fragment이 per-child 재구성으로 inline styling 보존
            # sidecar 없음: _emit_replacement_fragment만 사용 (Confluence 메타 속성 유실은 수용)
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    add_change.new_block,
                    sidecar_block=sidecar_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
        _paired_indices.add(idx)
        _mark_used(mapping.block_id, mapping)

    # 같은 부모에 대한 text-level 변경을 순차 집계하는 dict (block_id → patch dict)
    # preserved anchor list와 containing case에서 공용 사용
    _text_change_patches: Dict[str, Dict] = {}

    for change in changes:
        if change.index in _paired_indices:
            continue
        if change.change_type == 'deleted':
            patch = _build_delete_patch(
                change, mdx_to_sidecar, xpath_to_mapping)
            if patch:
                patches.append(patch)
            continue

        if change.change_type == 'added':
            patch = _build_insert_patch(
                change, improved_blocks, alignment,
                mdx_to_sidecar, xpath_to_mapping,
                page_lost_info=page_lost_info)
            if patch:
                patches.append(patch)
            continue

        if change.old_block.type in NON_CONTENT_TYPES:
            continue

        old_plain = normalize_mdx_to_plain(
            change.old_block.content, change.old_block.type)

        strategy, mapping = _resolve_mapping_for_change(
            change, old_plain, mappings, used_ids,
            mdx_to_sidecar, xpath_to_mapping)

        # legacy sidecar mapping이 커버하지 못한 list 블록:
        # roundtrip sidecar v3 identity로 fallback하여 mapping 복원
        mapping_via_v3_fallback = False
        if mapping is None and strategy == 'list' and roundtrip_sidecar is not None:
            id_block = change.old_block or change.new_block
            if id_block and id_block.content:
                fallback_sc = find_sidecar_block_by_identity(
                    roundtrip_sidecar.blocks,
                    sha256_text(id_block.content),
                    (id_block.line_start, id_block.line_end),
                )
                if fallback_sc is not None:
                    resolved = xpath_to_mapping.get(fallback_sc.xhtml_xpath)
                    if resolved is not None:
                        mapping = resolved
                        mapping_via_v3_fallback = True

        # v3 identity fallback도 실패한 경우: old_plain prefix text matching으로 최종 복원
        # type-based sidecar 타입 불일치로 mapping=None이 된 list 블록을 복원한다
        if mapping is None and strategy == 'list':
            text_fallback = _find_best_list_mapping_by_text(
                old_plain, mappings, used_ids)
            if text_fallback is not None:
                mapping = text_fallback
                mapping_via_v3_fallback = True

        # sidecar가 잘못된 list mapping을 반환한 경우 (ac: 포함 + plain text 불일치):
        # plain text prefix로 올바른 mapping 복원
        if (strategy == 'list' and mapping is not None
                and _contains_preserved_anchor_markup(mapping.xhtml_text)
                and old_plain[:40].strip() not in mapping.xhtml_plain_text):
            text_fallback = _find_best_list_mapping_by_text(
                old_plain, mappings, used_ids)
            if text_fallback is not None:
                mapping = text_fallback
                mapping_via_v3_fallback = True

        if strategy == 'skip':
            continue

        if strategy == 'list':
            list_sidecar = _find_roundtrip_sidecar_block(
                change, mapping, roundtrip_sidecar, xpath_to_sidecar_block,
            )
            # v3 fallback, sidecar 없음, 또는 실제 텍스트 변경이 있는 경우 whole-fragment 재생성
            # (Phase 5 Axis 3: build_list_item_patches fallback 제거)
            # 실제 텍스트 변경 여부: normalize+collapse_ws로 비교하여 링크 공백 등 형식 차이 무시
            _old_plain = collapse_ws(normalize_mdx_to_plain(change.old_block.content, 'list'))
            _new_plain = collapse_ws(normalize_mdx_to_plain(change.new_block.content, 'list'))
            has_content_change = _old_plain != _new_plain
            # ol start 변경 감지: 숫자 목록의 시작 번호가 달라진 경우
            _old_start = re.match(r'^\s*(\d+)\.', change.old_block.content)
            _new_start = re.match(r'^\s*(\d+)\.', change.new_block.content)
            has_ol_start_change = bool(
                _old_start and _new_start
                and int(_old_start.group(1)) != int(_new_start.group(1))
            )
            has_any_change = has_content_change or has_ol_start_change
            should_replace_clean_list = (
                mapping is not None
                and not _contains_preserved_anchor_markup(mapping.xhtml_text)
                # sidecar 있으면 항상 허용; 없으면 실제 변경(텍스트 또는 번호 시작값)이 있을 때만 허용
                and (roundtrip_sidecar is not None or has_any_change)
                and (list_sidecar is None or mapping_via_v3_fallback or has_any_change)
            )
            if (mapping is not None
                    and (
                        # anchor case: sidecar anchor metadata가 있으면 ac: 포함 여부 무관
                        sidecar_block_requires_reconstruction(list_sidecar)
                        # clean case: preserved anchor 없는 clean list
                        or should_replace_clean_list
                    )):
                _mark_used(mapping.block_id, mapping)
                patches.append(
                    _build_replace_fragment_patch(
                        mapping,
                        change.new_block,
                        sidecar_block=list_sidecar,
                        mapping_lost_info=mapping_lost_info,
                    )
                )
                continue
            # preserved anchor list: text-level 패치로 ac:/ri: XHTML 구조 보존
            # (_apply_mdx_diff_to_xhtml 경로)
            # 같은 부모의 다중 변경은 순차 집계한다 (이전 결과에 누적 적용)
            if mapping is not None and has_any_change:
                bid = mapping.block_id
                if bid not in _text_change_patches:
                    patch_entry: Dict[str, Any] = {
                        'xhtml_xpath': mapping.xhtml_xpath,
                        'old_plain_text': mapping.xhtml_plain_text,
                        'new_plain_text': mapping.xhtml_plain_text,
                    }
                    patches.append(patch_entry)
                    _text_change_patches[bid] = patch_entry
                _text_change_patches[bid]['new_plain_text'] = _apply_mdx_diff_to_xhtml(
                    _old_plain, _new_plain, _text_change_patches[bid]['new_plain_text'])
                if has_ol_start_change:
                    _text_change_patches[bid]['ol_start'] = int(_new_start.group(1))
                _mark_used(mapping.block_id, mapping)
            continue

        if strategy == 'table':
            if _can_replace_table_fragment(change, mapping, roundtrip_sidecar):
                _mark_used(mapping.block_id, mapping)
                patches.append(
                    _build_replace_fragment_patch(
                        mapping,
                        change.new_block,
                        mapping_lost_info=mapping_lost_info,
                    )
                )
            # else: skip — preserved anchor table은 안전한 패치 경로 없음 (Phase 5 Axis 3)
            continue

        new_plain = normalize_mdx_to_plain(
            change.new_block.content, change.new_block.type)

        if strategy == 'containing':
            if mapping is not None:
                bid = mapping.block_id
                first_visit = bid not in used_ids
                _mark_used(bid, mapping)
                sidecar_block = _find_roundtrip_sidecar_block(
                    change, mapping, roundtrip_sidecar, xpath_to_sidecar_block,
                )
                if sidecar_block_requires_reconstruction(sidecar_block):
                    # anchor 재구성이 필요한 경우: 첫 번째 변경만 replace_fragment
                    if first_visit:
                        patches.append(
                            _build_replace_fragment_patch(
                                mapping,
                                change.new_block,
                                sidecar_block=sidecar_block,
                                mapping_lost_info=mapping_lost_info,
                            )
                        )
                else:
                    # clean container / child-of-parent: text-level 누적
                    # (_apply_mdx_diff_to_xhtml 경로)
                    if bid not in _text_change_patches:
                        patch_entry: Dict[str, Any] = {
                            'xhtml_xpath': mapping.xhtml_xpath,
                            'old_plain_text': mapping.xhtml_plain_text,
                            'new_plain_text': mapping.xhtml_plain_text,
                        }
                        patches.append(patch_entry)
                        _text_change_patches[bid] = patch_entry
                    _text_change_patches[bid]['new_plain_text'] = _apply_mdx_diff_to_xhtml(
                        old_plain, new_plain,
                        _text_change_patches[bid]['new_plain_text'])
            continue

        # strategy == 'direct'
        _mark_used(mapping.block_id, mapping)

        # 멱등성 체크: push 후 XHTML이 이미 업데이트된 경우 건너뜀
        # (old != xhtml 이고 new == xhtml → 이미 적용된 변경)
        if (collapse_ws(old_plain) != collapse_ws(mapping.xhtml_plain_text)
                and collapse_ws(new_plain) == collapse_ws(mapping.xhtml_plain_text)):
            continue

        sidecar_block = _find_roundtrip_sidecar_block(
            change, mapping, roundtrip_sidecar, xpath_to_sidecar_block,
        )
        if _can_replace_table_fragment(change, mapping, roundtrip_sidecar):
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    change.new_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
            continue

        if _is_clean_block(change.old_block.type, mapping, sidecar_block):
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    change.new_block,
                    sidecar_block=sidecar_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
            continue

        if sidecar_block_requires_reconstruction(sidecar_block):
            patches.append(
                _build_replace_fragment_patch(
                    mapping,
                    change.new_block,
                    sidecar_block=sidecar_block,
                    mapping_lost_info=mapping_lost_info,
                )
            )
            continue

        # <ac:link> / <ri:attachment> 포함 블록은 inner XHTML 재생성 시 소실 위험
        # 원본 XHTML 구조를 template으로 사용하여 텍스트만 갱신
        if ('<ac:link' in mapping.xhtml_text
                or '<ri:attachment' in mapping.xhtml_text):
            preserved = rewrite_on_stored_template(mapping.xhtml_text, new_plain)
            block_lost = mapping_lost_info.get(mapping.block_id, {})
            if block_lost:
                preserved = apply_lost_info(preserved, block_lost)
            patches.append({
                'action': 'replace_fragment',
                'xhtml_xpath': mapping.xhtml_xpath,
                'new_element_xhtml': preserved,
            })
            continue

        # inner XHTML 재생성 + 블록 레벨 lost_info 적용
        new_inner = mdx_block_to_inner_xhtml(
            change.new_block.content, change.new_block.type)
        block_lost = mapping_lost_info.get(mapping.block_id, {})
        if block_lost:
            new_inner = apply_lost_info(new_inner, block_lost)

        patches.append({
            'xhtml_xpath': mapping.xhtml_xpath,
            'old_plain_text': mapping.xhtml_plain_text,
            'new_inner_xhtml': new_inner,
        })

    return patches


def _build_delete_patch(
    change: BlockChange,
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
) -> Optional[Dict[str, str]]:
    """삭제된 블록에 대한 delete 패치를 생성한다."""
    _SKIP_DELETE_TYPES = frozenset(('frontmatter', 'import_statement'))
    if change.old_block.type in _SKIP_DELETE_TYPES:
        return None
    mapping = find_mapping_by_sidecar(
        change.index, mdx_to_sidecar, xpath_to_mapping)
    if mapping is None:
        return None
    return {'action': 'delete', 'xhtml_xpath': mapping.xhtml_xpath}


def _build_insert_patch(
    change: BlockChange,
    improved_blocks: List[MdxBlock],
    alignment: Optional[Dict[int, int]],
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
    page_lost_info: Optional[dict] = None,
) -> Optional[Dict[str, str]]:
    """추가된 블록에 대한 insert 패치를 생성한다."""
    new_block = change.new_block
    _SKIP_INSERT_TYPES = frozenset(('frontmatter', 'import_statement'))
    if new_block.type in _SKIP_INSERT_TYPES:
        return None

    after_xpath = _find_insert_anchor(
        change.index, alignment, mdx_to_sidecar, xpath_to_mapping)
    new_xhtml = mdx_block_to_xhtml_element(new_block)
    # L4: lost_info 적용
    if page_lost_info:
        new_xhtml = apply_lost_info(new_xhtml, page_lost_info)

    return {
        'action': 'insert',
        'after_xpath': after_xpath,
        'new_element_xhtml': new_xhtml,
    }


def _find_insert_anchor(
    improved_idx: int,
    alignment: Optional[Dict[int, int]],
    mdx_to_sidecar: Dict[int, SidecarEntry],
    xpath_to_mapping: Dict[str, 'BlockMapping'],
) -> Optional[str]:
    """추가 블록의 삽입 위치 앵커를 찾는다.

    improved 시퀀스에서 역순으로 탐색하여 alignment에 존재하는
    (= original에 매칭되는) 첫 번째 블록의 xhtml_xpath를 반환한다.
    """
    if alignment is None:
        return None

    for j in range(improved_idx - 1, -1, -1):
        if j in alignment:
            orig_idx = alignment[j]
            mapping = find_mapping_by_sidecar(
                orig_idx, mdx_to_sidecar, xpath_to_mapping)
            if mapping is not None:
                return mapping.xhtml_xpath
    return None
