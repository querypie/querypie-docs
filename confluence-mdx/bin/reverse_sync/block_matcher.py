"""블록 매칭 — MDX normalized text와 XHTML mapping 간의 매칭 알고리즘."""
import re
from typing import List

from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.text_normalizer import (
    collapse_ws, strip_list_marker, EMOJI_RE, INVISIBLE_RE,
)


def find_mapping_by_text(
    mdx_plain: str,
    mappings: List[BlockMapping],
    exclude: 'set | None' = None,
) -> 'BlockMapping | None':
    """MDX normalized plain text와 가장 잘 매칭되는 XHTML mapping을 찾는다.

    Args:
        exclude: 이미 사용된 mapping block_id 집합. 중복 매칭을 방지한다.
    """
    mdx_norm = collapse_ws(mdx_plain)
    if not mdx_norm:
        return None

    def _excluded(m):
        return exclude is not None and m.block_id in exclude

    # 1차: 완전 일치
    for m in mappings:
        if _excluded(m):
            continue
        if collapse_ws(m.xhtml_plain_text) == mdx_norm:
            return m

    # 2차: prefix 일치 (50자 이상) — 길이가 가장 유사한 후보 선택
    min_prefix = 50
    candidates = []
    for m in mappings:
        if _excluded(m):
            continue
        xhtml_norm = collapse_ws(m.xhtml_plain_text)
        if len(mdx_norm) >= min_prefix and xhtml_norm.startswith(mdx_norm[:min_prefix]):
            candidates.append(m)
        elif len(xhtml_norm) >= min_prefix and mdx_norm.startswith(xhtml_norm[:min_prefix]):
            candidates.append(m)
    if candidates:
        return min(candidates, key=lambda m: abs(len(collapse_ws(m.xhtml_plain_text)) - len(mdx_norm)))

    # 3차: 공백 무시 비교 (table/html_block/list 등 셀/항목 경계 공백 차이 대응)
    mdx_nospace = re.sub(r'\s+', '', mdx_norm)
    if mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            if mdx_nospace == xhtml_nospace:
                return m

    # 3.2차: 공백+보이지 않는 문자 무시 비교
    # (Confluence XHTML에 zero-width space, Hangul filler 등이 포함된 경우 대응)
    mdx_visible = INVISIBLE_RE.sub('', mdx_nospace)
    if mdx_visible and mdx_visible != mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            xhtml_visible = INVISIBLE_RE.sub('', xhtml_nospace)
            if mdx_visible == xhtml_visible:
                return m
    # XHTML 쪽에만 보이지 않는 문자가 있는 경우도 검사
    if mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            xhtml_visible = INVISIBLE_RE.sub('', xhtml_nospace)
            if xhtml_visible != xhtml_nospace and mdx_nospace == xhtml_visible:
                return m

    # 3.5차: 공백+이모지 무시 비교 (Confluence ac:emoticon → MDX 이모지 차이 대응)
    mdx_clean = EMOJI_RE.sub('', mdx_nospace)
    if mdx_clean and mdx_clean != mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            xhtml_clean = EMOJI_RE.sub('', xhtml_nospace)
            if mdx_clean == xhtml_clean:
                return m

    # 4차: 리스트 마커 제거 후 공백 무시 비교
    # (ac:adf-content 내 <p> 요소가 "- " 등 리스트 마커를 포함하는 경우 대응)
    mdx_unmarked = strip_list_marker(mdx_nospace)
    if mdx_unmarked and mdx_unmarked != mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            xhtml_unmarked = strip_list_marker(xhtml_nospace)
            if mdx_unmarked == xhtml_unmarked:
                return m
    # 양쪽 모두 마커 제거 시도
    if mdx_nospace:
        for m in mappings:
            if _excluded(m):
                continue
            xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
            xhtml_unmarked = strip_list_marker(xhtml_nospace)
            if xhtml_unmarked != xhtml_nospace and mdx_nospace == xhtml_unmarked:
                return m

    return None


def find_containing_mapping(
    mdx_plain: str,
    mappings: List[BlockMapping],
    exclude: 'set | None' = None,
) -> 'BlockMapping | None':
    """MDX 텍스트를 포함하는 XHTML 매핑 블록을 찾는다 (substring 매칭)."""
    mdx_nospace = re.sub(r'\s+', '', mdx_plain)
    mdx_visible = INVISIBLE_RE.sub('', mdx_nospace)
    if not mdx_visible or len(mdx_visible) < 10:
        return None  # 너무 짧은 텍스트는 오탐 위험

    candidates = []
    for m in mappings:
        if exclude is not None and m.block_id in exclude:
            continue
        xhtml_nospace = re.sub(r'\s+', '', m.xhtml_plain_text)
        xhtml_visible = INVISIBLE_RE.sub('', xhtml_nospace)
        if mdx_visible in xhtml_visible:
            candidates.append((m, len(xhtml_visible)))
    if not candidates:
        return None
    # 가장 작은 (가장 구체적인) 상위 블록 선택
    return min(candidates, key=lambda x: x[1])[0]
