"""Inline MDX -> XHTML conversion helpers."""

from __future__ import annotations

import re

from .link_resolver import LinkResolver

_CODE_SPAN_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_ITALIC_RE = re.compile(r"\*\*\*(.+?)\*\*\*")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_BR_TAG_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_BADGE_INLINE_RE = re.compile(
    r'<Badge\s+color="([^"]+)">(.*?)</Badge>', flags=re.DOTALL
)
_BADGE_COLOR_MAP = {
    "green": "Green",
    "blue": "Blue",
    "red": "Red",
    "yellow": "Yellow",
    "grey": "Grey",
    "gray": "Grey",
    "purple": "Purple",
}


def _replace_badge(match: re.Match[str]) -> str:
    color = match.group(1).strip().lower()
    text = match.group(2).strip()
    colour = _BADGE_COLOR_MAP.get(color, "Grey")
    return (
        f'<ac:structured-macro ac:name="status">'
        f'<ac:parameter ac:name="title">{text}</ac:parameter>'
        f'<ac:parameter ac:name="colour">{colour}</ac:parameter>'
        f'</ac:structured-macro>'
    )


def convert_inline(text: str, link_resolver: LinkResolver | None = None) -> str:
    """Convert inline MDX syntax to XHTML.

    Supported syntax:
    - `code`
    - **bold**
    - *italic*
    - [text](url)
    """
    placeholders: list[str] = []

    def _stash_code(match: re.Match[str]) -> str:
        placeholders.append(match.group(1))
        return f"\x00CODE{len(placeholders) - 1}\x00"

    converted = _CODE_SPAN_RE.sub(_stash_code, text)
    converted = _BOLD_ITALIC_RE.sub(r"<strong><em>\1</em></strong>", converted)
    converted = _BOLD_RE.sub(r"<strong>\1</strong>", converted)
    converted = _ITALIC_RE.sub(r"<em>\1</em>", converted)
    converted = _convert_links(converted, link_resolver=link_resolver)
    converted = _BR_TAG_RE.sub("<br />", converted)
    converted = _BADGE_INLINE_RE.sub(_replace_badge, converted)

    def _restore_code(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return f"<code>{placeholders[idx]}</code>"

    converted = re.sub(r"\x00CODE(\d+)\x00", _restore_code, converted)
    return converted


def convert_heading_inline(
    text: str,
    link_resolver: LinkResolver | None = None,
) -> str:
    """Convert heading inline text while stripping bold markers.

    Heading behavior follows forward converter semantics where strong tags
    are not emitted in headings.
    """
    without_bold_markers = _BOLD_RE.sub(r"\1", text)

    placeholders: list[str] = []

    def _stash_code(match: re.Match[str]) -> str:
        placeholders.append(match.group(1))
        return f"\x00CODE{len(placeholders) - 1}\x00"

    converted = _CODE_SPAN_RE.sub(_stash_code, without_bold_markers)
    converted = _convert_links(converted, link_resolver=link_resolver)

    def _restore_code(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return f"<code>{placeholders[idx]}</code>"

    converted = re.sub(r"\x00CODE(\d+)\x00", _restore_code, converted)
    return converted


def _convert_links(text: str, link_resolver: LinkResolver | None) -> str:
    def _replace_link(match: re.Match[str]) -> str:
        link_text = match.group(1)
        href = match.group(2)
        if link_resolver is None:
            return f'<a href="{href}">{link_text}</a>'

        content_title, anchor = link_resolver.resolve(href, link_text=link_text)
        if not content_title:
            return f'<a href="{href}">{link_text}</a>'

        anchor_attr = f' ac:anchor="{anchor}"' if anchor else ""
        return (
            f"<ac:link{anchor_attr}>"
            f'<ri:page ri:content-title="{content_title}"></ri:page>'
            f"<ac:link-body>{link_text}</ac:link-body>"
            f"</ac:link>"
        )

    return _LINK_RE.sub(_replace_link, text)
