"""Emit Confluence Storage XHTML from parsed blocks."""

from typing import Optional

from .parser import Block


def emit_block(block: Block, context: Optional[dict] = None) -> str:
    """Emit XHTML for a single block.

    This is a skeleton implementation for Task 1.1.
    """
    raise NotImplementedError("emit_block is not implemented yet")


def emit_document(blocks: list[Block]) -> str:
    """Emit XHTML for a full MDX document.

    This is a skeleton implementation for Task 1.1.
    """
    raise NotImplementedError("emit_document is not implemented yet")
