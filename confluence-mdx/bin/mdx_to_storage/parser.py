"""Parser for converting MDX text to block objects."""

from dataclasses import dataclass, field


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
    """Parse MDX text into block objects.

    This is a skeleton implementation for Task 1.1.
    """
    raise NotImplementedError("parse_mdx is not implemented yet")
