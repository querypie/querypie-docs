"""인라인 포맷 변경 감지 — MDX content의 inline 마커 변경을 감지한다."""
import re

from text_utils import collapse_ws


# ── Inline format 변경 감지 ──

_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_INLINE_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_INLINE_ITALIC_RE = re.compile(r'(?<!\*)\*([^*]+)\*(?!\*)')
_INLINE_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def _extract_inline_markers(content: str) -> list:
    """MDX content에서 inline 포맷 마커를 위치순으로 추출한다."""
    markers = []
    for m in _INLINE_CODE_RE.finditer(content):
        markers.append(('code', m.start(), m.group(1)))
    for m in _INLINE_BOLD_RE.finditer(content):
        markers.append(('bold', m.start(), m.group(1)))
    for m in _INLINE_ITALIC_RE.finditer(content):
        markers.append(('italic', m.start(), m.group(1)))
    for m in _INLINE_LINK_RE.finditer(content):
        markers.append(('link', m.start(), m.group(1), m.group(2)))
    return sorted(markers, key=lambda x: x[1])


def _strip_positions(markers: list) -> list:
    """마커 리스트에서 위치(index 1)를 제거하여 type+content만 비교 가능하게 한다."""
    return [(m[0],) + m[2:] for m in markers]


def _extract_marker_spans(content: str) -> list:
    """MDX content에서 inline 포맷 마커의 (start, end) 위치 범위를 추출한다."""
    spans = []
    for m in _INLINE_CODE_RE.finditer(content):
        spans.append((m.start(), m.end()))
    for m in _INLINE_BOLD_RE.finditer(content):
        spans.append((m.start(), m.end()))
    for m in _INLINE_ITALIC_RE.finditer(content):
        spans.append((m.start(), m.end()))
    for m in _INLINE_LINK_RE.finditer(content):
        spans.append((m.start(), m.end()))
    return sorted(spans)


def _extract_between_marker_texts(content: str) -> list:
    """연속된 inline 마커 사이의 텍스트를 추출한다."""
    spans = _extract_marker_spans(content)
    between = []
    for i in range(len(spans) - 1):
        between.append(content[spans[i][1]:spans[i + 1][0]])
    return between


def has_inline_format_change(old_content: str, new_content: str) -> bool:
    """old/new MDX 콘텐츠의 inline 포맷 마커가 다른지 감지한다.

    마커 type/content 변경뿐 아니라, 연속된 마커 사이의 텍스트가
    변경된 경우도 inline 변경으로 판단한다 (XHTML code 요소 경계에서
    text-only 패치가 올바르게 동작하지 않기 때문).
    """
    old_markers = _strip_positions(_extract_inline_markers(old_content))
    new_markers = _strip_positions(_extract_inline_markers(new_content))
    if old_markers != new_markers:
        return True

    # 마커가 있을 때, 연속된 마커 사이 텍스트 변경 감지
    if old_markers:
        old_between = _extract_between_marker_texts(old_content)
        new_between = _extract_between_marker_texts(new_content)
        if ([collapse_ws(s) for s in old_between]
                != [collapse_ws(s) for s in new_between]):
            return True

    return False


def has_inline_boundary_change(old_content: str, new_content: str) -> bool:
    """inline 마커의 경계 이동을 감지한다.

    마커 type 추가/제거, 마커 간 텍스트 변경(경계 이동)을 감지한다.
    마커 내부 content만 변경된 경우는 무시한다 (text-only 패치로 처리 가능).
    flat list의 전체 리스트 재생성 판단에 사용한다.
    (has_inline_format_change보다 보수적 — 이미지 등 XHTML 고유 요소 보존)
    """
    old_markers = _extract_inline_markers(old_content)
    new_markers = _extract_inline_markers(new_content)
    old_types = [m[0] for m in old_markers]
    new_types = [m[0] for m in new_markers]
    if old_types != new_types:
        return True

    # 마커가 있을 때, 연속된 마커 사이 텍스트 변경 감지 (경계 이동)
    if old_markers:
        old_between = _extract_between_marker_texts(old_content)
        new_between = _extract_between_marker_texts(new_content)
        if ([collapse_ws(s) for s in old_between]
                != [collapse_ws(s) for s in new_between]):
            return True

        # 첫 번째 마커 앞 텍스트 변경 감지 (마커가 leading text를 흡수하는 경우)
        # 예: `Executed Result : \`X\`` → `\`Executed Result: X\`` (code span boundary 확장)
        old_before = old_content[:old_markers[0][1]]
        new_before = new_content[:new_markers[0][1]]
        if collapse_ws(old_before) != collapse_ws(new_before):
            return True

    return False
