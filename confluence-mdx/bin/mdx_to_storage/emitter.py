"""Emit Confluence Storage XHTML from parsed blocks."""

from __future__ import annotations

import os
import re
from typing import Optional

from .inline import convert_heading_inline, convert_inline
from .link_resolver import LinkResolver
from .parser import Block, HEADING_PATTERN


_ORDERED_LIST_PATTERN = re.compile(r"^\d+\.\s+(.*)$")
_UNORDERED_LIST_PATTERN = re.compile(r"^[-*+]\s+(.*)$")
_HEADING_LINE_PATTERN = HEADING_PATTERN
_CALLOUT_TYPE_TO_MACRO = {
    "default": "tip",
    "info": "info",
    "important": "note",
    "error": "warning",
}
_BADGE_COLOR_MAP = {
    "green": "Green",
    "blue": "Blue",
    "red": "Red",
    "yellow": "Yellow",
    "grey": "Grey",
    "gray": "Grey",
    "purple": "Purple",
}
_FIGURE_IN_LIST_RE = re.compile(
    r'\s*<figure[^>]*>\s*<img\s+([^>]+?)\s*/?\s*>\s*</figure>',
    flags=re.DOTALL,
)
_TRAILING_BR_RE = re.compile(r'\s*<br\s*/?\s*>\s*$')
_IMG_ATTR_RE = re.compile(r'(\w[\w-]*)=(?:"([^"]*)"|\'([^\']*)\')')


class _ListNode:
    def __init__(self, ordered: bool, text: str, depth: int) -> None:
        self.ordered = ordered
        self.text = text
        self.depth = depth
        self.children: list["_ListNode"] = []


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
        return (
            f"<h{xhtml_level}>"
            f"{convert_heading_inline(heading_text, link_resolver=context.get('link_resolver'))}"
            f"</h{xhtml_level}>"
        )

    if block.type == "paragraph":
        paragraph_text = _join_paragraph_lines(block.content)
        if not paragraph_text:
            return "<p />"
        return f"<p>{convert_inline(paragraph_text, link_resolver=context.get('link_resolver'))}</p>"

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
        return _emit_single_depth_list(block.content, link_resolver=context.get("link_resolver"))

    if block.type == "hr":
        return "<hr />"

    if block.type == "html_block":
        return _emit_html_block(block.content, link_resolver=context.get("link_resolver"))

    if block.type == "callout":
        return _emit_callout(block, context)

    if block.type == "figure":
        return _emit_figure(block, link_resolver=context.get("link_resolver"))

    if block.type == "table":
        return _emit_markdown_table(block.content, link_resolver=context.get("link_resolver"))

    if block.type == "blockquote":
        return _emit_blockquote(block.content, link_resolver=context.get("link_resolver"))

    if block.type == "details":
        return _emit_details(block, context)

    if block.type == "badge":
        return _emit_badge(block)

    return ""


def emit_document(
    blocks: list[Block],
    link_resolver: Optional[LinkResolver] = None,
) -> str:
    """Emit XHTML for a full MDX document."""
    if link_resolver is None:
        link_resolver = LinkResolver()
    context: dict[str, object] = {"frontmatter_title": "", "link_resolver": link_resolver}
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


def _emit_single_depth_list(content: str, link_resolver: Optional[LinkResolver] = None) -> str:
    parsed = _parse_list_items(content)
    if not parsed:
        return ""

    roots = _build_list_tree(parsed)
    return _render_list_nodes(roots, link_resolver=link_resolver)


def _parse_list_items(content: str) -> list[_ListNode]:
    items: list[_ListNode] = []
    for line in content.splitlines():
        if not line.strip():
            continue
        expanded = line.expandtabs(4)
        indent = len(expanded) - len(expanded.lstrip(" "))
        depth = max(0, indent // 4)
        stripped = line.strip()

        ordered_match = _ORDERED_LIST_PATTERN.match(stripped)
        if ordered_match:
            items.append(_ListNode(True, ordered_match.group(1), depth))
            continue

        unordered_match = _UNORDERED_LIST_PATTERN.match(stripped)
        if unordered_match:
            items.append(_ListNode(False, unordered_match.group(1), depth))
            continue

        if items:
            items[-1].text = f"{items[-1].text} {stripped}"
    return items


def _build_list_tree(items: list[_ListNode]) -> list[_ListNode]:
    roots: list[_ListNode] = []
    stack: list[_ListNode] = []

    for item in items:
        while stack and stack[-1].depth >= item.depth:
            stack.pop()
        if stack:
            stack[-1].children.append(item)
        else:
            roots.append(item)
        stack.append(item)

    return roots


def _render_list_nodes(
    nodes: list[_ListNode],
    link_resolver: Optional[LinkResolver] = None,
) -> str:
    parts: list[str] = []
    i = 0
    while i < len(nodes):
        ordered = nodes[i].ordered
        tag = "ol" if ordered else "ul"
        group: list[_ListNode] = []
        while i < len(nodes) and nodes[i].ordered == ordered:
            group.append(nodes[i])
            i += 1

        body = "".join(_render_list_item(node, link_resolver=link_resolver) for node in group)
        if tag == "ol":
            parts.append(f'<ol start="1">{body}</ol>')
        else:
            parts.append(f"<ul>{body}</ul>")
    return "".join(parts)


def _figure_attrs_to_ac_image(img_attrs_str: str) -> str:
    """<img> 속성 문자열에서 <ac:image><ri:attachment> XHTML을 생성."""
    src = ""
    width = ""
    for key, v1, v2 in _IMG_ATTR_RE.findall(img_attrs_str):
        val = v1 or v2
        if key == "src":
            src = val
        elif key == "width":
            width = val

    filename = os.path.basename(src) if src else ""
    ac_attrs = ['ac:align="center"']
    if width:
        ac_attrs.append(f'ac:width="{width}"')

    return (
        f'<ac:image {" ".join(ac_attrs)}>'
        f'<ri:attachment ri:filename="{filename}"></ri:attachment>'
        f'</ac:image>'
    )


def _render_list_item(node: _ListNode, link_resolver: Optional[LinkResolver] = None) -> str:
    nested = (
        _render_list_nodes(node.children, link_resolver=link_resolver)
        if node.children
        else ""
    )
    text = node.text
    figure_match = _FIGURE_IN_LIST_RE.search(text)
    if figure_match:
        before_text = text[:figure_match.start()]
        before_text = _TRAILING_BR_RE.sub("", before_text).strip()
        img_attrs_str = figure_match.group(1)
        ac_image = _figure_attrs_to_ac_image(img_attrs_str)
        p_content = convert_inline(before_text, link_resolver=link_resolver) if before_text else ""
        parts = ["<li>"]
        if p_content:
            parts.append(f"<p>{p_content}</p>")
        parts.append(ac_image)
        parts.append("<p />")
        parts.append(nested)
        parts.append("</li>")
        return "".join(parts)
    return f"<li><p>{convert_inline(text, link_resolver=link_resolver)}</p>{nested}</li>"


def _emit_callout(block: Block, context: dict) -> str:
    emoji = block.attrs.get("emoji", "").strip()
    callout_type = block.attrs.get("type", "default").strip().lower()

    if emoji:
        macro_name = "panel"
    else:
        macro_name = _CALLOUT_TYPE_TO_MACRO.get(callout_type, "tip")

    children = block.children
    if not children:
        children = _parse_callout_children_from_content(block.content)

    body = "".join(emit_block(child, context=context) for child in children if child.type != "empty")
    parts = [f'<ac:structured-macro ac:name="{macro_name}">']
    if emoji:
        parts.append(f'<ac:parameter ac:name="panelIcon">{emoji}</ac:parameter>')
    parts.append(f"<ac:rich-text-body>{body}</ac:rich-text-body>")
    parts.append("</ac:structured-macro>")
    return "".join(parts)


def _parse_callout_children_from_content(content: str) -> list[Block]:
    lines = content.splitlines()
    if not lines:
        return []
    if lines[0].startswith("<Callout"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("</Callout"):
        lines = lines[:-1]
    inner_text = "\n".join(lines).strip()
    if not inner_text:
        return []
    from .parser import parse_mdx
    return parse_mdx(inner_text)


def _emit_figure(block: Block, link_resolver: Optional[LinkResolver] = None) -> str:
    src = block.attrs.get("src", "").strip()
    if not src:
        return ""

    filename = os.path.basename(src)
    width = block.attrs.get("width", "").strip()
    caption = block.attrs.get("caption", "").strip()

    attrs = ['ac:align="center"']
    if width:
        attrs.append(f'ac:width="{width}"')

    parts = [f"<ac:image {' '.join(attrs)}>"]
    parts.append(f'<ri:attachment ri:filename="{filename}"></ri:attachment>')
    if caption:
        parts.append(f"<ac:caption><p>{convert_inline(caption, link_resolver=link_resolver)}</p></ac:caption>")
    parts.append("</ac:image>")
    return "".join(parts)


def _emit_markdown_table(content: str, link_resolver: Optional[LinkResolver] = None) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) < 2:
        return f"<p>{convert_inline(content.strip())}</p>"

    rows = [_split_table_row(line) for line in lines]
    headers = rows[0]
    body_rows = rows[2:]

    parts = ["<table><tbody><tr>"]
    parts.extend(
        f"<th><p>{convert_inline(cell, link_resolver=link_resolver)}</p></th>"
        for cell in headers
    )
    parts.append("</tr>")
    for row in body_rows:
        parts.append("<tr>")
        parts.extend(
            f"<td><p>{convert_inline(cell, link_resolver=link_resolver)}</p></td>"
            for cell in row
        )
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def _emit_html_block(content: str, link_resolver: Optional[LinkResolver] = None) -> str:
    stripped = content.strip()
    if stripped in {"<p></p>", "<p/>", "<p />"}:
        return "<p />"
    if not stripped.startswith("<table"):
        return stripped
    pattern = re.compile(r"<(td|th)([^>]*)>(.*?)</\1>", flags=re.DOTALL)

    def _replace_cell(match: re.Match[str]) -> str:
        tag = match.group(1)
        attrs = match.group(2)
        inner = match.group(3)
        if "<" in inner and ">" in inner:
            return match.group(0)
        return f"<{tag}{attrs}>{convert_inline(inner.strip(), link_resolver=link_resolver)}</{tag}>"

    return pattern.sub(_replace_cell, stripped)


def _emit_blockquote(content: str, link_resolver: Optional[LinkResolver] = None) -> str:
    raw_lines = content.splitlines()
    stripped_lines: list[str] = []
    for line in raw_lines:
        line = line.lstrip()
        if line.startswith(">"):
            line = line[1:]
            if line.startswith(" "):
                line = line[1:]
        stripped_lines.append(line)

    paragraphs: list[str] = []
    current: list[str] = []
    for line in stripped_lines:
        if line.strip():
            current.append(line.strip())
            continue
        if current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))

    if not paragraphs:
        return "<blockquote><p /></blockquote>"

    body = "".join(f"<p>{convert_inline(text, link_resolver=link_resolver)}</p>" for text in paragraphs)
    return f"<blockquote>{body}</blockquote>"


def _emit_details(block: Block, context: dict) -> str:
    summary = block.attrs.get("summary", "").strip()
    children = block.children
    if not children:
        children = _parse_details_children_from_content(block.content)
    body = "".join(emit_block(child, context=context) for child in children if child.type != "empty")
    parts = ['<ac:structured-macro ac:name="expand">']
    if summary:
        parts.append(f'<ac:parameter ac:name="title">{convert_inline(summary)}</ac:parameter>')
    parts.append(f"<ac:rich-text-body>{body}</ac:rich-text-body>")
    parts.append("</ac:structured-macro>")
    return "".join(parts)


def _parse_details_children_from_content(content: str) -> list[Block]:
    match = re.search(r"</summary>(.*?)</details>", content, flags=re.DOTALL)
    if not match:
        return []
    inner = match.group(1).strip()
    if not inner:
        return []
    from .parser import parse_mdx
    return parse_mdx(inner)


def _emit_badge(block: Block) -> str:
    text = block.attrs.get("text", "").strip()
    color = block.attrs.get("color", "").strip().lower()
    colour = _BADGE_COLOR_MAP.get(color, "Grey")

    parts = ['<ac:structured-macro ac:name="status">']
    parts.append(f'<ac:parameter ac:name="title">{convert_inline(text)}</ac:parameter>')
    parts.append(f'<ac:parameter ac:name="colour">{colour}</ac:parameter>')
    parts.append("</ac:structured-macro>")
    return "".join(parts)
