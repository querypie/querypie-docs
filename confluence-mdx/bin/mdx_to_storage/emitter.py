"""Emit Confluence Storage XHTML from parsed blocks."""

from __future__ import annotations

import re
from typing import Optional

from .inline import convert_heading_inline, convert_inline
from .parser import Block


_ORDERED_LIST_PATTERN = re.compile(r"^\d+\.\s+(.*)$")
_UNORDERED_LIST_PATTERN = re.compile(r"^[-*+]\s+(.*)$")
_HEADING_LINE_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")


def emit_block(block: Block, context: Optional[dict] = None) -> str:
    """Emit XHTML for a single block."""
    if context is None:
        context = {}

    if block.type in {"frontmatter", "import_statement", "empty"}:
        return ""

    if block.type == "heading":
        match = _HEADING_LINE_PATTERN.match(block.content.strip())
        if not match:
            return ""

        heading_text = match.group(2)
        frontmatter_title = context.get("frontmatter_title", "").strip()

        if block.level == 1 and frontmatter_title and heading_text.strip() == frontmatter_title:
            return ""

        xhtml_level = max(1, min(6, block.level - 1))
        return f"<h{xhtml_level}>{convert_heading_inline(heading_text)}</h{xhtml_level}>"

    if block.type == "paragraph":
        paragraph_text = _join_paragraph_lines(block.content)
        return f"<p>{convert_inline(paragraph_text)}</p>"

    if block.type == "code_block":
        code_body = _extract_code_body(block.content)
        parts = ['<ac:structured-macro ac:name="code">']
        if block.language:
            parts.append(
                f'<ac:parameter ac:name="language">{block.language}</ac:parameter>'
            )
        parts.append(f"<ac:plain-text-body><![CDATA[{code_body}]]></ac:plain-text-body>")
        parts.append("</ac:structured-macro>")
        return "".join(parts)

    if block.type == "list":
        return _emit_single_depth_list(block.content)

    if block.type == "hr":
        return "<hr />"

    if block.type == "html_block":
        return block.content.strip()

    return ""


def emit_document(blocks: list[Block]) -> str:
    """Emit XHTML for a full MDX document."""
    context: dict[str, str] = {"frontmatter_title": ""}
    for block in blocks:
        if block.type == "frontmatter":
            context["frontmatter_title"] = block.attrs.get("title", "")
            break

    return "".join(emit_block(block, context=context) for block in blocks)


def _join_paragraph_lines(content: str) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return " ".join(lines)


def _extract_code_body(content: str) -> str:
    lines = content.splitlines()
    if not lines:
        return ""
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


def _emit_single_depth_list(content: str) -> str:
    parsed = _parse_list_items(content)
    if not parsed:
        return ""

    ordered = parsed[0][0]
    tag = "ol" if ordered else "ul"
    items = "".join(f"<li><p>{convert_inline(item)}</p></li>" for _, item in parsed)
    return f"<{tag}>{items}</{tag}>"


def _parse_list_items(content: str) -> list[tuple[bool, str]]:
    items: list[tuple[bool, str]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        ordered_match = _ORDERED_LIST_PATTERN.match(stripped)
        if ordered_match:
            items.append((True, ordered_match.group(1)))
            continue

        unordered_match = _UNORDERED_LIST_PATTERN.match(stripped)
        if unordered_match:
            items.append((False, unordered_match.group(1)))
            continue

        if items:
            is_ordered, existing = items[-1]
            items[-1] = (is_ordered, f"{existing} {stripped}")
    return items
