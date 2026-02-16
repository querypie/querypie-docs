"""Inline MDX -> XHTML conversion helpers."""

import re

_CODE_SPAN_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_ITALIC_RE = re.compile(r"\*\*\*(.+?)\*\*\*")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def convert_inline(text: str) -> str:
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
    converted = _LINK_RE.sub(r'<a href="\2">\1</a>', converted)

    def _restore_code(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return f"<code>{placeholders[idx]}</code>"

    converted = re.sub(r"\x00CODE(\d+)\x00", _restore_code, converted)
    return converted


def convert_heading_inline(text: str) -> str:
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
    converted = _LINK_RE.sub(r'<a href="\2">\1</a>', converted)

    def _restore_code(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return f"<code>{placeholders[idx]}</code>"

    converted = re.sub(r"\x00CODE(\d+)\x00", _restore_code, converted)
    return converted
