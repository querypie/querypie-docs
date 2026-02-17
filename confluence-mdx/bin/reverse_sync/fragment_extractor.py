"""Fragment Extractor — XHTML에서 top-level block fragment를 byte-exact 추출한다.

BS4로 DOM 구조를 파악한 뒤 원본 텍스트에서 태그 경계를 추적하여
BeautifulSoup의 변형 없이 원본 그대로의 fragment를 추출한다.

핵심 불변식:
  prefix + fragments[0] + separators[0] + ... + fragments[-1] + suffix == xhtml_text
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag

from reverse_sync.mapping_recorder import _iter_block_children


@dataclass
class FragmentExtractionResult:
    """XHTML fragment 추출 결과."""

    prefix: str
    fragments: List[str]
    separators: List[str]  # len == len(fragments) - 1
    suffix: str


def extract_block_fragments(xhtml_text: str) -> FragmentExtractionResult:
    """원본 XHTML 텍스트에서 top-level block fragment를 추출한다.

    _iter_block_children()과 동일한 순서로 top-level 요소를 식별한 뒤,
    원본 텍스트에서 태그 경계를 직접 추적하여 byte-exact fragment를 추출한다.

    Returns:
        FragmentExtractionResult (prefix, fragments, separators, suffix)

    Raises:
        ValueError: 태그 경계를 찾지 못한 경우
    """
    soup = BeautifulSoup(xhtml_text, "html.parser")

    # Top-level element 순서 파악
    top_elements: List[Tuple[str, str]] = []
    for child in _iter_block_children(soup):
        if isinstance(child, Tag):
            top_elements.append(("tag", child.name))
        elif isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                top_elements.append(("text", text))

    if not top_elements:
        return FragmentExtractionResult(
            prefix=xhtml_text, fragments=[], separators=[], suffix=""
        )

    # 원본 텍스트에서 위치 추적
    positions: List[Tuple[int, int]] = []
    search_pos = 0

    for elem_type, elem_info in top_elements:
        if elem_type == "tag":
            start = _find_tag_start(xhtml_text, elem_info, search_pos)
            if start < 0:
                raise ValueError(
                    f"Cannot find <{elem_info}> at or after position {search_pos}"
                )
            end = _find_element_end(xhtml_text, elem_info, start)
            positions.append((start, end))
            search_pos = end
        else:
            # NavigableString — 원본 텍스트에서 찾기
            idx = xhtml_text.find(elem_info, search_pos)
            if idx >= 0:
                positions.append((idx, idx + len(elem_info)))
                search_pos = idx + len(elem_info)

    if not positions:
        return FragmentExtractionResult(
            prefix=xhtml_text, fragments=[], separators=[], suffix=""
        )

    # 결과 구성
    prefix = xhtml_text[: positions[0][0]]
    suffix = xhtml_text[positions[-1][1] :]
    fragments = [xhtml_text[s:e] for s, e in positions]
    separators = [
        xhtml_text[positions[i][1] : positions[i + 1][0]]
        for i in range(len(positions) - 1)
    ]

    return FragmentExtractionResult(
        prefix=prefix,
        fragments=fragments,
        separators=separators,
        suffix=suffix,
    )


def _find_tag_start(text: str, tag_name: str, start_pos: int) -> int:
    """원본 텍스트에서 <tag_name 의 시작 위치를 찾는다.

    <tag_name 뒤에 공백, >, / 중 하나가 와야 실제 태그로 인정한다.
    (예: <p 를 찾을 때 <pre 를 건너뛴다.)
    """
    prefix = f"<{tag_name}"
    pos = start_pos
    while pos < len(text):
        idx = text.find(prefix, pos)
        if idx < 0:
            return -1
        next_pos = idx + len(prefix)
        if next_pos >= len(text):
            return idx
        nc = text[next_pos]
        if nc in (" ", ">", "/", "\t", "\n", "\r"):
            return idx
        pos = idx + 1
    return -1


def _find_tag_close_gt(text: str, start: int) -> int:
    """Opening tag의 닫는 ``>`` 위치를 찾는다.

    따옴표(``"`` / ``'``) 안의 ``>``는 건너뛴다.
    """
    in_quote = None
    for i in range(start, len(text)):
        c = text[i]
        if in_quote:
            if c == in_quote:
                in_quote = None
        elif c in ('"', "'"):
            in_quote = c
        elif c == ">":
            return i
    return -1


def _find_element_end(text: str, tag_name: str, open_tag_start: int) -> int:
    """Element의 끝 위치(exclusive)를 찾는다.

    Self-closing tag (``<tag ... />``)와 중첩된 동일 이름 태그를 올바르게 처리한다.

    Returns:
        element 끝 위치 (exclusive)

    Raises:
        ValueError: 닫는 태그를 찾지 못한 경우
    """
    gt = _find_tag_close_gt(text, open_tag_start)
    if gt < 0:
        raise ValueError(f"No closing > for <{tag_name}> at {open_tag_start}")

    # Self-closing 확인
    if text[gt - 1] == "/":
        return gt + 1

    # Matching close tag 찾기 (depth counting)
    close_tag = f"</{tag_name}>"
    open_prefix = f"<{tag_name}"
    depth = 1
    pos = gt + 1

    while depth > 0:
        lt = text.find("<", pos)
        if lt < 0:
            raise ValueError(f"Unclosed <{tag_name}> (depth={depth})")

        # Close tag 확인
        if text.startswith(close_tag, lt):
            depth -= 1
            if depth == 0:
                return lt + len(close_tag)
            pos = lt + len(close_tag)
            continue

        # Same-name opening tag 확인
        if text.startswith(open_prefix, lt):
            next_char_pos = lt + len(open_prefix)
            if next_char_pos < len(text) and text[next_char_pos] in (
                " ",
                ">",
                "/",
                "\t",
                "\n",
                "\r",
            ):
                inner_gt = _find_tag_close_gt(text, lt)
                if inner_gt >= 0 and text[inner_gt - 1] == "/":
                    pos = inner_gt + 1  # self-closing → depth 불변
                else:
                    depth += 1
                    pos = inner_gt + 1 if inner_gt >= 0 else lt + 1
            else:
                pos = lt + 1
            continue

        pos = lt + 1

    raise ValueError(f"Depth counting failed for <{tag_name}>")
