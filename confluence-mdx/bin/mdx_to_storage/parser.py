"""Parser for converting MDX text to block objects."""

from dataclasses import dataclass, field
import re
from typing import Optional


_HR_PATTERN = re.compile(r"^_{6,}$")
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_ORDERED_PATTERN = re.compile(r"^\d+\.\s+")
_LIST_UNORDERED_PATTERN = re.compile(r"^[-*+]\s+")
_CALLOUT_ATTR_PATTERN = re.compile(r"(\w+)=(?:\"([^\"]*)\"|'([^']*)')")
_FIGURE_IMG_ATTR_PATTERN = re.compile(r"(\w+(?:-\w+)*)=(?:\"([^\"]*)\"|'([^']*)')")


@dataclass
class Block:
    """Single parsed block from an MDX document."""

    type: str
    content: str
    level: int = 0
    language: str = ""
    children: list["Block"] = field(default_factory=list)
    attrs: dict = field(default_factory=dict)


def parse_mdx(text: str) -> list[Block]:
    """Parse MDX text into block objects."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    blocks: list[Block] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        frontmatter_block = _parse_frontmatter(lines, i)
        if frontmatter_block:
            block, i = frontmatter_block
            blocks.append(block)
            continue

        if line == "":
            blocks.append(Block(type="empty", content="\n"))
            i += 1
            continue

        if line.startswith("import "):
            blocks.append(Block(type="import_statement", content=line + "\n"))
            i += 1
            continue

        heading = _parse_heading(line)
        if heading:
            blocks.append(heading)
            i += 1
            continue

        if line.startswith("```"):
            block, i = _parse_code_block(lines, i)
            blocks.append(block)
            continue

        if _HR_PATTERN.match(line.strip()):
            blocks.append(Block(type="hr", content=line + "\n"))
            i += 1
            continue

        if line.startswith("<Callout"):
            block, i = _parse_callout_block(lines, i)
            blocks.append(block)
            continue

        if line.startswith("<figure"):
            block, i = _parse_figure_block(lines, i)
            blocks.append(block)
            continue

        if _is_list_line(line):
            block, i = _parse_list_block(lines, i)
            blocks.append(block)
            continue

        if _is_html_block_start(line):
            block, i = _parse_html_block(lines, i)
            blocks.append(block)
            continue

        block, i = _parse_paragraph(lines, i)
        blocks.append(block)

    return blocks


def _parse_frontmatter(lines: list[str], start: int) -> Optional[tuple[Block, int]]:
    if start != 0 or lines[start] != "---":
        return None

    i = start + 1
    while i < len(lines) and lines[i] != "---":
        i += 1

    if i >= len(lines):
        return None

    end = i + 1
    content = "\n".join(lines[start:end]) + "\n"
    attrs = {}

    title = _extract_frontmatter_title(lines[start + 1 : i])
    if title:
        attrs["title"] = title

    return Block(type="frontmatter", content=content, attrs=attrs), end


def _extract_frontmatter_title(frontmatter_lines: list[str]) -> str:
    for raw_line in frontmatter_lines:
        line = raw_line.strip()
        if not line.startswith("title:"):
            continue

        value = line.split(":", 1)[1].strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        return value
    return ""


def _parse_heading(line: str) -> Optional[Block]:
    match = _HEADING_PATTERN.match(line)
    if not match:
        return None

    hashes = match.group(1)
    return Block(type="heading", content=line + "\n", level=len(hashes))


def _parse_code_block(lines: list[str], start: int) -> tuple[Block, int]:
    first_line = lines[start]
    language = first_line[3:].strip()

    i = start + 1
    while i < len(lines) and not lines[i].startswith("```"):
        i += 1

    if i < len(lines):
        i += 1

    content = "\n".join(lines[start:i]) + "\n"
    return Block(type="code_block", content=content, language=language), i


def _parse_list_block(lines: list[str], start: int) -> tuple[Block, int]:
    i = start + 1
    while i < len(lines):
        current = lines[i]
        if current == "":
            if i + 1 < len(lines) and _is_list_continuation(lines[i + 1]):
                i += 1
                continue
            break

        if not _is_list_continuation(current):
            break

        i += 1

    content = "\n".join(lines[start:i]) + "\n"
    return Block(type="list", content=content), i


def _parse_callout_block(lines: list[str], start: int) -> tuple[Block, int]:
    i = start + 1
    while i < len(lines) and "</Callout>" not in lines[i]:
        i += 1

    if i < len(lines):
        i += 1

    content = "\n".join(lines[start:i]) + "\n"
    attrs = _parse_callout_attrs(lines[start])
    inner_content = _extract_callout_inner_content(content)
    children = parse_mdx(inner_content) if inner_content else []
    return Block(type="callout", content=content, attrs=attrs, children=children), i


def _parse_callout_attrs(opening_line: str) -> dict:
    attrs = {}
    for key, v1, v2 in _CALLOUT_ATTR_PATTERN.findall(opening_line):
        value = v1 or v2
        attrs[key] = value
    return attrs


def _extract_callout_inner_content(content: str) -> str:
    lines = content.splitlines()
    if not lines:
        return ""
    if lines[0].startswith("<Callout"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("</Callout"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_figure_block(lines: list[str], start: int) -> tuple[Block, int]:
    i = start + 1
    while i < len(lines) and "</figure>" not in lines[i]:
        i += 1

    if i < len(lines):
        i += 1

    content = "\n".join(lines[start:i]) + "\n"
    attrs = _parse_figure_attrs(content)
    return Block(type="figure", content=content, attrs=attrs), i


def _parse_figure_attrs(content: str) -> dict:
    attrs = {}
    img_match = re.search(r"<img\s+([^>]+)>", content)
    if not img_match:
        return attrs

    for key, v1, v2 in _FIGURE_IMG_ATTR_PATTERN.findall(img_match.group(1)):
        value = v1 or v2
        attrs[key] = value
    return attrs


def _parse_html_block(lines: list[str], start: int) -> tuple[Block, int]:
    i = start + 1
    while i < len(lines):
        current = lines[i]
        if current == "":
            break
        if _starts_new_block(current):
            break
        i += 1

    content = "\n".join(lines[start:i]) + "\n"
    return Block(type="html_block", content=content), i


def _parse_paragraph(lines: list[str], start: int) -> tuple[Block, int]:
    i = start + 1
    while i < len(lines):
        current = lines[i]
        if current == "":
            break
        if _starts_new_block(current):
            break
        i += 1

    content = "\n".join(lines[start:i]) + "\n"
    return Block(type="paragraph", content=content), i


def _starts_new_block(line: str) -> bool:
    if line.startswith("import "):
        return True
    if line.startswith("```"):
        return True
    if line.startswith("<Callout"):
        return True
    if line.startswith("<figure"):
        return True
    if _is_list_line(line):
        return True
    if _is_html_block_start(line):
        return True
    if _parse_heading(line):
        return True
    if _HR_PATTERN.match(line.strip()):
        return True
    return False


def _is_list_line(line: str) -> bool:
    stripped = line.lstrip()
    return bool(
        _LIST_UNORDERED_PATTERN.match(stripped)
        or _LIST_ORDERED_PATTERN.match(stripped)
    )


def _is_list_continuation(line: str) -> bool:
    if _is_list_line(line):
        return True
    return line.startswith("  ") or line.startswith("\t")


def _is_html_block_start(line: str) -> bool:
    if not line.startswith("<"):
        return False
    if line.startswith("<Callout"):
        return False
    if line.startswith("<figure"):
        return False
    if line.startswith("<Badge"):
        return False
    return True
