"""Lossless visible segment extraction for reverse sync text-bearing blocks.

The model keeps visible whitespace as explicit segments, records preservation
units separately from visible text, and exposes structural fingerprints for
paragraph, heading, and list planning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import html as html_module
import re
from typing import Any, Iterable, List, Literal, Tuple

SegmentKind = Literal["list_marker", "ws", "text", "item_boundary", "anchor"]

from bs4 import BeautifulSoup, Tag
from reverse_sync.mapping_recorder import get_text_with_emoticons
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_inner_xhtml


@dataclass(frozen=True)
class VisibleSegment:
    kind: SegmentKind
    text: str
    visible: bool
    structural: bool
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VisibleContentModel:
    segments: List[VisibleSegment]
    visible_text: str
    structural_fingerprint: Tuple[Any, ...]


_MDX_LIST_ITEM_RE = re.compile(r'^(\s*)(\d+\.|[-*+])(\s*)(.*)$')
_MDX_TABLE_SEPARATOR_RE = re.compile(r'^\|[\s\-:|]+\|$')


@dataclass(frozen=True)
class _MdxListEntry:
    path: Tuple[int, ...]
    marker: str
    marker_ws: str
    body: str
    continuation_lines: Tuple[str, ...]


_TEXT_BLOCK_TYPES = frozenset({"paragraph", "heading"})
_PRESERVATION_TAGS = frozenset(
    {"a", "ac:link", "ac:image", "ac:structured-macro", "ri:attachment"}
)


def extract_visible_model_from_mdx(
    content: str,
    block_type: str,
) -> VisibleContentModel:
    """MDX paragraph, heading, list를 공통 visible-content model로 변환합니다."""
    if block_type == "list":
        return extract_list_model_from_mdx(content)
    if block_type not in _TEXT_BLOCK_TYPES:
        raise ValueError(f"지원하지 않는 visible MDX block type입니다: {block_type}")

    rendered_inner = mdx_block_to_inner_xhtml(content, block_type)
    heading_level = _mdx_heading_level(content) if block_type == "heading" else None
    return _extract_text_model(
        rendered_inner,
        block_type=block_type,
        heading_level=heading_level,
        source="mdx",
    )


def extract_visible_model_from_xhtml(
    fragment: str,
    block_type: str,
) -> VisibleContentModel:
    """Storage XHTML paragraph, heading, list의 visible-content model을 만듭니다."""
    if block_type == "list":
        return extract_list_model_from_xhtml(fragment)
    if block_type not in _TEXT_BLOCK_TYPES:
        raise ValueError(f"지원하지 않는 visible XHTML block type입니다: {block_type}")

    soup = BeautifulSoup(fragment, "html.parser")
    heading = soup.find(re.compile(r"^h[1-6]$"))
    heading_level = (
        int(heading.name[1])
        if block_type == "heading" and isinstance(heading, Tag)
        else None
    )
    return _extract_text_model(
        fragment,
        block_type=block_type,
        heading_level=heading_level,
        source="xhtml",
    )


def _extract_text_model(
    fragment: str,
    *,
    block_type: str,
    heading_level: int | None,
    source: str,
) -> VisibleContentModel:
    soup = BeautifulSoup(fragment, "html.parser")
    visible_text = get_text_with_emoticons(soup)
    segments = _tokenize_visible_text(visible_text)
    units = _collect_preservation_units(soup)
    segments.extend(
        VisibleSegment(
            kind="anchor",
            text="",
            visible=False,
            structural=True,
            meta={"kind": kind, "source": source, **metadata},
        )
        for kind, metadata in units
    )
    return VisibleContentModel(
        segments=segments,
        visible_text=visible_text,
        structural_fingerprint=(
            block_type,
            heading_level,
            tuple(kind for kind, _ in units),
        ),
    )


def _collect_preservation_units(
    soup: BeautifulSoup,
) -> List[Tuple[str, dict[str, Any]]]:
    units: List[Tuple[str, dict[str, Any]]] = []
    for tag in soup.find_all(sorted(_PRESERVATION_TAGS)):
        if tag.name in {"a", "ac:link"}:
            kind = "link"
            page = tag.find("ri:page")
            metadata = {
                "href": str(tag.get("href", "")),
                "anchor": str(tag.get("ac:anchor", "")),
                "page_title": (
                    str(page.get("ri:content-title", ""))
                    if isinstance(page, Tag)
                    else ""
                ),
            }
        elif tag.name == "ac:image":
            kind = "attachment"
            attachment = tag.find("ri:attachment")
            metadata = {
                "filename": (
                    str(attachment.get("ri:filename", ""))
                    if isinstance(attachment, Tag)
                    else ""
                ),
            }
        elif tag.name == "ri:attachment":
            if tag.find_parent("ac:image") is not None:
                continue
            kind = "attachment"
            metadata = {"filename": str(tag.get("ri:filename", ""))}
        else:
            kind = "macro"
            metadata = {"name": str(tag.get("ac:name", ""))}
        units.append((kind, metadata))
    return units


def _mdx_heading_level(content: str) -> int | None:
    match = re.match(r"^\s*(#{1,6})\s+", content)
    return len(match.group(1)) if match is not None else None


def extract_list_model_from_mdx(content: str) -> VisibleContentModel:
    """Build a lossless visible-content model from MDX list content."""
    entries = _parse_mdx_list_entries(content)
    root_kind = _detect_root_list_kind(entries)
    ol_start = _detect_ordered_start(entries)

    segments: List[VisibleSegment] = []
    visible_parts: List[str] = []
    fingerprint_items: List[Tuple[Any, ...]] = []

    for index, entry in enumerate(entries):
        rendered = _render_mdx_list_entry(entry)
        continuation_target = _find_continuation_target_path(entries, index)
        if continuation_target is not None and not rendered:
            continue

        segment_path = continuation_target or entry.path
        if (continuation_target is not None and rendered and visible_parts
                and not visible_parts[-1].endswith((' ', '\t'))
                and not rendered.startswith((' ', '\t'))):
            rendered = f" {rendered}"
        if continuation_target is None:
            segments.append(VisibleSegment(
                kind="list_marker",
                text=entry.marker,
                visible=False,
                structural=True,
                meta={"path": entry.path},
            ))
            if entry.marker_ws:
                segments.append(VisibleSegment(
                    kind="ws",
                    text=entry.marker_ws,
                    visible=False,
                    structural=True,
                    meta={"path": entry.path, "role": "marker_gap"},
                ))

        for segment in _tokenize_visible_text(rendered, path=segment_path):
            segments.append(segment)
            if segment.visible:
                visible_parts.append(segment.text)

        if continuation_target is None:
            segments.append(VisibleSegment(
                kind="item_boundary",
                text="",
                visible=False,
                structural=True,
                meta={"path": entry.path},
            ))
            marker_kind = "ol" if entry.marker.endswith('.') else "ul"
            fingerprint_items.append((entry.path, marker_kind))

    return VisibleContentModel(
        segments=segments,
        visible_text=''.join(visible_parts),
        structural_fingerprint=(root_kind, ol_start, tuple(fingerprint_items)),
    )


def extract_list_model_from_xhtml(fragment: str) -> VisibleContentModel:
    """Build a lossless visible-content model from XHTML list content."""
    soup = BeautifulSoup(fragment, "html.parser")
    root = soup.find(["ul", "ol"])
    if root is None:
        return VisibleContentModel([], "", ("", None, (), ()))

    # Use the same DOM text basis that patch_xhtml validates against.
    # Only trim non-visible trailing whitespace from whitespace-only tail blocks.
    visible_text = get_text_with_emoticons(root).rstrip()
    segments: List[VisibleSegment] = []
    for segment in _tokenize_visible_text(visible_text):
        segments.append(segment)

    item_paths, anchor_paths = _collect_xhtml_list_structure(root)
    for anchor_path in anchor_paths:
        segments.append(VisibleSegment(
            kind="anchor",
            text="",
            visible=False,
            structural=True,
            meta={"path": anchor_path},
        ))

    start = int(root.get("start", "1")) if root.name == "ol" and root.get("start") else 1
    return VisibleContentModel(
        segments=segments,
        visible_text=visible_text,
        structural_fingerprint=(root.name, start if root.name == "ol" else None,
                                tuple(item_paths), tuple(anchor_paths)),
    )


def model_has_anchor_segments(model: VisibleContentModel) -> bool:
    return any(segment.kind == "anchor" for segment in model.segments)


def _parse_mdx_list_entries(content: str) -> List[_MdxListEntry]:
    entries: List[_MdxListEntry] = []
    stack: List[Tuple[int, Tuple[int, ...]]] = []
    current: dict[str, Any] | None = None

    for raw_line in content.split('\n'):
        match = _MDX_LIST_ITEM_RE.match(raw_line)
        if match is None:
            if current is not None:
                current["continuation_lines"].append(raw_line)
            continue

        if current is not None:
            entries.append(_MdxListEntry(
                path=current["path"],
                marker=current["marker"],
                marker_ws=current["marker_ws"],
                body=current["body"],
                continuation_lines=tuple(current["continuation_lines"]),
            ))

        indent = len(match.group(1))
        marker = match.group(2)
        marker_ws = match.group(3)
        body = match.group(4)

        while stack and indent < stack[-1][0]:
            stack.pop()

        if stack and indent == stack[-1][0]:
            parent_path = stack[-2][1] if len(stack) >= 2 else ()
            index = stack[-1][1][-1] + 1
            stack.pop()
        elif stack and indent > stack[-1][0]:
            parent_path = stack[-1][1]
            index = 0
        else:
            parent_path = ()
            index = 0

        path = parent_path + (index,)
        current = {
            "path": path,
            "marker": marker,
            "marker_ws": marker_ws,
            "body": body,
            "continuation_lines": [],
        }
        stack.append((indent, path))

    if current is not None:
        entries.append(_MdxListEntry(
            path=current["path"],
            marker=current["marker"],
            marker_ws=current["marker_ws"],
            body=current["body"],
            continuation_lines=tuple(current["continuation_lines"]),
        ))

    return entries


def _render_mdx_list_entry(entry: _MdxListEntry) -> str:
    pieces: List[str] = []
    if entry.body:
        rendered = _render_mdx_line(entry.body, preserve_leading=True)
        if rendered:
            pieces.append(rendered)

    for line in entry.continuation_lines:
        rendered = _render_mdx_line(line.lstrip(), preserve_leading=False)
        if rendered:
            pieces.append(rendered)

    return _join_rendered_pieces(pieces)


def _render_mdx_line(line: str, *, preserve_leading: bool) -> str:
    if not line:
        return ""

    s = line if preserve_leading else line.lstrip()
    stripped = s.strip()
    if not stripped:
        return ""
    if stripped.startswith(("<figure", "<img", "</figure")):
        return ""
    if stripped.startswith("```"):
        return ""
    if _MDX_TABLE_SEPARATOR_RE.match(stripped):
        return ""
    if stripped.startswith("|") and stripped.endswith("|"):
        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        s = " ".join(cell for cell in cells if cell)

    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'`([^`]+)`', r'\1', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', s)
    s = re.sub(
        r'\[([^\]]+)\]\([^)]+\)',
        lambda m: m.group(1).split(' | ')[0] if ' | ' in m.group(1) else m.group(1),
        s,
    )
    s = re.sub(
        r'<Badge\s+color="([^"]+)">(.*?)</Badge>',
        lambda m: m.group(2) + m.group(1).capitalize(),
        s,
    )
    # Terminal <br/> before a non-visible continuation (for example a figure)
    # does not contribute visible text and should not leave a trailing space.
    s = re.sub(r'\s*<br\s*/?>\s*$', '', s)
    s = re.sub(r'<[^>]+/?>', '', s)
    return html_module.unescape(s)


def _join_rendered_pieces(pieces: Iterable[str]) -> str:
    result = ""
    for piece in pieces:
        if not piece:
            continue
        if not result:
            result = piece
            continue
        joiner = ""
        if not result.endswith((' ', '\t')) and not piece.startswith((' ', '\t')):
            joiner = " "
        result = result + joiner + piece
    return result


def _find_continuation_target_path(
    entries: List[_MdxListEntry],
    index: int,
) -> Tuple[int, ...] | None:
    entry = entries[index]
    if entry.body.strip() or not entry.continuation_lines or index == 0:
        return None

    previous = entries[index - 1]
    if previous.path[:-1] != entry.path[:-1]:
        return None
    if previous.path[-1] + 1 != entry.path[-1]:
        return None

    if all(
        not _render_mdx_line(line.lstrip(), preserve_leading=False)
        for line in entry.continuation_lines
    ):
        return previous.path

    if _is_figure_only_continuation_lines(entry.continuation_lines):
        return previous.path

    return None


def _is_figure_only_continuation_lines(lines: Tuple[str, ...]) -> bool:
    in_figure = False
    in_figcaption = False
    saw_figure = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<figure"):
            in_figure = True
            saw_figure = True
            continue
        if stripped.startswith("<img") and in_figure:
            continue
        if stripped == "<figcaption>" and in_figure:
            in_figcaption = True
            continue
        if stripped == "</figcaption>" and in_figcaption:
            in_figcaption = False
            continue
        if stripped == "</figure>" and in_figure and not in_figcaption:
            in_figure = False
            continue
        if in_figcaption:
            continue
        return False

    return saw_figure and not in_figure and not in_figcaption


def _tokenize_visible_text(text: str, *, path: Tuple[int, ...] | None = None) -> List[VisibleSegment]:
    segments: List[VisibleSegment] = []
    if not text:
        return segments

    for match in re.finditer(r'\s+|[^\s]+', text):
        token = match.group(0)
        segments.append(VisibleSegment(
            kind="ws" if token.isspace() else "text",
            text=token,
            visible=True,
            structural=False,
            meta={"path": path} if path is not None else {},
        ))
    return segments


def _detect_root_list_kind(entries: List[_MdxListEntry]) -> str:
    if not entries:
        return "ul"
    return "ol" if entries[0].marker.endswith('.') else "ul"


def _detect_ordered_start(entries: List[_MdxListEntry]) -> int | None:
    if not entries:
        return None
    first = entries[0].marker
    if not first.endswith('.'):
        return None
    try:
        return int(first[:-1])
    except ValueError:
        return None


def _collect_xhtml_list_structure(root: Tag) -> Tuple[List[Tuple[int, ...]], List[Tuple[int, ...]]]:
    item_paths: List[Tuple[int, ...]] = []
    anchor_paths: List[Tuple[int, ...]] = []

    def walk_list(list_tag: Tag, parent_path: Tuple[int, ...]) -> None:
        items = [child for child in list_tag.children if isinstance(child, Tag) and child.name == 'li']
        for index, li in enumerate(items):
            path = parent_path + (index,)
            item_paths.append(path)
            if li.find(['ac:link', 'ac:image']) is not None:
                anchor_paths.append(path)
            nested_lists = [
                child for child in li.children
                if isinstance(child, Tag) and child.name in ('ul', 'ol')
            ]
            for nested in nested_lists:
                walk_list(nested, path)

    walk_list(root, ())
    return item_paths, anchor_paths
