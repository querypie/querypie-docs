"""push eligibility를 위한 versioned typed MDX equivalence.

진단용 regex normalization과 달리 이 모듈은 MDX를 block/token model로
변환한 뒤 구조와 visible content를 비교한다. v1에서 허용하는 source
formatting 차이는 Markdown table의 cell padding과 separator dash 길이뿐이다.
"""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any
from urllib.parse import unquote, urlparse

from mdx_to_storage.parser import Block, parse_mdx_blocks


PUSH_EQUIVALENCE_POLICY = "reverse-sync-equivalence-v1"
_NON_BODY_BLOCKS = frozenset({"empty", "frontmatter", "import_statement"})
_TABLE_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
_LIST_ITEM = re.compile(r"^([ \t]*)([-+*]|\d+\.)([ \t]+)(.*)$")


@dataclass(frozen=True)
class InlineToken:
    """MDX inline source에서 의미 보존이 필요한 token."""

    kind: str
    value: str = ""
    target: str = ""
    attachment_filename: str = ""
    children: tuple["InlineToken", ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"kind": self.kind}
        if self.value:
            value["value"] = self.value
        if self.target:
            value["target"] = self.target
        if self.attachment_filename:
            value["attachment_filename"] = self.attachment_filename
        if self.children:
            value["children"] = [child.to_dict() for child in self.children]
        return value


@dataclass(frozen=True)
class CanonicalBlock:
    """push equivalence에서 비교하는 typed block."""

    kind: str
    level: int = 0
    language: str = ""
    tokens: tuple[InlineToken, ...] = ()
    structure: tuple[Any, ...] = ()
    marker: str = ""

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"kind": self.kind}
        if self.level:
            value["level"] = self.level
        if self.language:
            value["language"] = self.language
        if self.tokens:
            value["tokens"] = [token.to_dict() for token in self.tokens]
        if self.structure:
            value["structure"] = _jsonable(self.structure)
        if self.marker:
            value["marker"] = self.marker
        return value


@dataclass(frozen=True)
class CanonicalDocument:
    """policy version과 block sequence로 구성된 canonical MDX."""

    policy: str
    blocks: tuple[CanonicalBlock, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocks": [block.to_dict() for block in self.blocks],
            "policy": self.policy,
        }

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EquivalenceResult:
    """두 typed document의 비교 결과와 재현 가능한 evidence."""

    passed: bool
    policy: str
    expected_sha256: str
    actual_sha256: str
    diff_report: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "actual_sha256": self.actual_sha256,
            "diff_report": self.diff_report,
            "expected_sha256": self.expected_sha256,
            "passed": self.passed,
            "policy": self.policy,
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, InlineToken):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in sorted(value.items())}
    return value


def _strip_single_terminal_newline(value: str) -> str:
    return value[:-1] if value.endswith("\n") else value


def _find_closing_bracket(value: str, start: int) -> int:
    escaped = False
    for index in range(start, len(value)):
        char = value[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "]":
            return index
    return -1


def _find_closing_paren(value: str, start: int) -> int:
    depth = 1
    escaped = False
    quote = ""
    for index in range(start, len(value)):
        char = value[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _find_tag_end(value: str, start: int) -> int:
    quote = ""
    for index in range(start, len(value)):
        char = value[index]
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == ">":
            return index
    return -1


def _split_link_destination(value: str) -> tuple[str, str]:
    """link destination과 optional title을 보수적으로 분리한다."""
    value = value.strip()
    match = re.match(r"^(\S+?)(?:\s+([\"'])(.*)\2)?$", value, flags=re.DOTALL)
    if not match:
        return value, ""
    return match.group(1), match.group(3) or ""


def _attachment_filename(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https", "data"}:
        return ""
    return PurePosixPath(unquote(parsed.path)).name


def _append_text(tokens: list[InlineToken], value: str) -> None:
    if not value:
        return
    if tokens and tokens[-1].kind == "text":
        previous = tokens.pop()
        tokens.append(InlineToken(kind="text", value=previous.value + value))
    else:
        tokens.append(InlineToken(kind="text", value=value))


def tokenize_inline(value: str) -> tuple[InlineToken, ...]:
    """inline source를 link/code/HTML marker/text token으로 분해한다.

    해석할 수 없는 syntax는 text로 남긴다. 따라서 parser가 오인한 입력이
    동등하다고 완화되는 대신 exact source 차이로 fail-closed된다.
    """
    tokens: list[InlineToken] = []
    index = 0
    text_start = 0
    while index < len(value):
        image = value.startswith("![", index)
        link = value.startswith("[", index)
        if image or link:
            label_start = index + (2 if image else 1)
            label_end = _find_closing_bracket(value, label_start)
            if label_end >= 0 and label_end + 1 < len(value) and value[label_end + 1] == "(":
                destination_end = _find_closing_paren(value, label_end + 2)
                if destination_end >= 0:
                    _append_text(tokens, value[text_start:index])
                    destination, title = _split_link_destination(
                        value[label_end + 2 : destination_end]
                    )
                    label = value[label_start:label_end]
                    if image:
                        tokens.append(
                            InlineToken(
                                kind="image",
                                value=label,
                                target=destination,
                                attachment_filename=_attachment_filename(destination),
                                children=(
                                    InlineToken(kind="title", value=title),
                                )
                                if title
                                else (),
                            )
                        )
                    else:
                        children = list(tokenize_inline(label))
                        if title:
                            children.append(InlineToken(kind="title", value=title))
                        tokens.append(
                            InlineToken(
                                kind="link",
                                target=destination,
                                children=tuple(children),
                            )
                        )
                    index = destination_end + 1
                    text_start = index
                    continue

        if value[index] == "`":
            delimiter_length = 1
            while (
                index + delimiter_length < len(value)
                and value[index + delimiter_length] == "`"
            ):
                delimiter_length += 1
            delimiter = "`" * delimiter_length
            closing = value.find(delimiter, index + delimiter_length)
            if closing >= 0:
                _append_text(tokens, value[text_start:index])
                tokens.append(
                    InlineToken(
                        kind="code",
                        value=value[index + delimiter_length : closing],
                    )
                )
                index = closing + delimiter_length
                text_start = index
                continue

        if value[index] == "<":
            tag_end = _find_tag_end(value, index + 1)
            if tag_end >= 0:
                candidate = value[index : tag_end + 1]
                if re.match(r"^</?[A-Za-z][^>]*>$", candidate):
                    _append_text(tokens, value[text_start:index])
                    marker_match = re.match(r"^</?([A-Za-z][\w:.-]*)", candidate)
                    marker = marker_match.group(1) if marker_match else ""
                    tokens.append(
                        InlineToken(kind="html_marker", value=candidate, target=marker)
                    )
                    index = tag_end + 1
                    text_start = index
                    continue

        index += 1

    _append_text(tokens, value[text_start:])
    return tuple(tokens)


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        raise ValueError(f"Markdown table row가 아닙니다: {line!r}")
    body = stripped[1:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    code_delimiter = 0
    index = 0
    while index < len(body):
        char = body[index]
        if escaped:
            current.append(char)
            escaped = False
            index += 1
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            index += 1
            continue
        if char == "`":
            run = 1
            while index + run < len(body) and body[index + run] == "`":
                run += 1
            current.extend("`" * run)
            if code_delimiter == 0:
                code_delimiter = run
            elif code_delimiter == run:
                code_delimiter = 0
            index += run
            continue
        if char == "|" and code_delimiter == 0:
            cells.append("".join(current).strip(" \t"))
            current = []
        else:
            current.append(char)
        index += 1
    cells.append("".join(current).strip(" \t"))
    return cells


def _table_structure(content: str) -> tuple[Any, ...]:
    rows = [_split_table_row(line) for line in content.rstrip("\n").splitlines()]
    structure: list[Any] = []
    for row_index, cells in enumerate(rows):
        if row_index == 1 and all(_TABLE_SEPARATOR_CELL.match(cell) for cell in cells):
            alignments = []
            for cell in cells:
                if cell.startswith(":") and cell.endswith(":"):
                    alignments.append("center")
                elif cell.endswith(":"):
                    alignments.append("right")
                elif cell.startswith(":"):
                    alignments.append("left")
                else:
                    alignments.append("default")
            structure.append(("separator", tuple(alignments)))
        else:
            structure.append(
                ("row", tuple(tuple(tokenize_inline(cell)) for cell in cells))
            )
    return tuple(structure)


def _list_structure(content: str) -> tuple[Any, ...]:
    entries: list[Any] = []
    for line in content.rstrip("\n").splitlines():
        match = _LIST_ITEM.match(line)
        if match:
            indent, marker, separator, body = match.groups()
            list_kind = "ordered" if marker.endswith(".") and marker[:-1].isdigit() else "unordered"
            ordinal = int(marker[:-1]) if list_kind == "ordered" else 0
            entries.append(
                (
                    "item",
                    indent,
                    list_kind,
                    ordinal,
                    separator,
                    tokenize_inline(body),
                )
            )
        elif line == "":
            entries.append(("blank",))
        else:
            entries.append(("continuation", line))
    return tuple(entries)


def _blockquote_structure(content: str) -> tuple[Any, ...]:
    lines: list[Any] = []
    for line in content.rstrip("\n").splitlines():
        match = re.match(r"^(>+)([ \t]?)(.*)$", line)
        if not match:
            lines.append(("raw", line))
            continue
        markers, separator, body = match.groups()
        lines.append(("quote", len(markers), separator, tokenize_inline(body)))
    return tuple(lines)


def _opaque_marker(block: Block) -> str:
    content = block.content.lstrip()
    match = re.match(r"<([A-Za-z][\w:.-]*)", content)
    if match:
        return match.group(1)
    return block.type


def canonicalize_block(block: Block) -> CanonicalBlock:
    content = _strip_single_terminal_newline(block.content)
    if block.type == "heading":
        match = re.match(r"^#{1,6}[ \t]+(.*)$", content, flags=re.DOTALL)
        body = match.group(1) if match else content
        return CanonicalBlock(
            kind="heading",
            level=block.level,
            tokens=tokenize_inline(body),
        )
    if block.type == "paragraph":
        return CanonicalBlock(kind="paragraph", tokens=tokenize_inline(content))
    if block.type == "table":
        return CanonicalBlock(kind="table", structure=_table_structure(content))
    if block.type == "list":
        return CanonicalBlock(kind="list", structure=_list_structure(content))
    if block.type == "blockquote":
        return CanonicalBlock(
            kind="blockquote",
            structure=_blockquote_structure(content),
        )
    if block.type == "code_block":
        lines = content.splitlines()
        body_lines = lines[1:-1] if len(lines) >= 2 else []
        return CanonicalBlock(
            kind="code_block",
            language=block.language,
            tokens=(InlineToken(kind="code_block_text", value="\n".join(body_lines)),),
        )
    if block.type == "hr":
        return CanonicalBlock(kind="hr", marker=content)

    # Macro/JSX/HTML 구조는 v1에서 임의로 의미 해석하지 않는다. type과
    # marker를 기록하고 source를 exact token으로 보존해 unsafe equivalence를 막는다.
    return CanonicalBlock(
        kind=block.type,
        marker=_opaque_marker(block),
        tokens=(InlineToken(kind="opaque_source", value=content),),
    )


def canonicalize_mdx(mdx: str) -> CanonicalDocument:
    blocks = tuple(
        canonicalize_block(block)
        for block in parse_mdx_blocks(mdx)
        if block.type not in _NON_BODY_BLOCKS
    )
    return CanonicalDocument(policy=PUSH_EQUIVALENCE_POLICY, blocks=blocks)


def _unified_model_diff(
    expected: CanonicalDocument,
    actual: CanonicalDocument,
) -> str:
    expected_json = json.dumps(
        expected.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    actual_json = json.dumps(
        actual.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    return "".join(
        difflib.unified_diff(
            expected_json.splitlines(keepends=True),
            actual_json.splitlines(keepends=True),
            fromfile="expected.typed.json",
            tofile="actual.typed.json",
            lineterm="",
        )
    )


def verify_push_equivalence(expected_mdx: str, actual_mdx: str) -> EquivalenceResult:
    """v1 typed canonical model로 두 MDX body를 비교한다."""
    expected = canonicalize_mdx(expected_mdx)
    actual = canonicalize_mdx(actual_mdx)
    passed = expected == actual
    return EquivalenceResult(
        passed=passed,
        policy=PUSH_EQUIVALENCE_POLICY,
        expected_sha256=expected.sha256,
        actual_sha256=actual.sha256,
        diff_report="" if passed else _unified_model_diff(expected, actual),
    )
