import pytest
from reverse_sync.mdx_block_parser import parse_mdx_blocks
from reverse_sync.block_diff import diff_blocks, BlockChange


def test_no_changes():
    mdx = "---\ntitle: 'T'\n---\n\n# Title\n\nParagraph.\n"
    original = parse_mdx_blocks(mdx)
    improved = parse_mdx_blocks(mdx)
    changes = diff_blocks(original, improved)
    assert changes == []


def test_text_change_in_paragraph():
    original_mdx = "# Title\n\n접근 제어를 설정합니다.\n"
    improved_mdx = "# Title\n\n접근 통제를 설정합니다.\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)
    changes = diff_blocks(original, improved)

    assert len(changes) == 1
    assert changes[0].index == 2  # paragraph 블록의 인덱스
    assert changes[0].change_type == "modified"
    assert "접근 제어" in changes[0].old_block.content
    assert "접근 통제" in changes[0].new_block.content


def test_multiple_changes():
    original_mdx = "# Title\n\nPara one.\n\nPara two.\n"
    improved_mdx = "# Title\n\nPara ONE.\n\nPara TWO.\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)
    changes = diff_blocks(original, improved)

    assert len(changes) == 2


def test_block_count_mismatch_raises():
    """Phase 1에서 블록 수가 다르면 에러."""
    original_mdx = "# Title\n\nParagraph.\n"
    improved_mdx = "# Title\n\nParagraph.\n\nNew paragraph.\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)

    with pytest.raises(ValueError, match="block count mismatch"):
        diff_blocks(original, improved)
