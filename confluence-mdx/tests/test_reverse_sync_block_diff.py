import pytest
from reverse_sync.mdx_block_parser import parse_mdx_blocks, MdxBlock
from reverse_sync.block_diff import diff_blocks, BlockChange


# ---- 기존 테스트 (반환값 언패킹 적용) ----

def test_no_changes():
    mdx = "---\ntitle: 'T'\n---\n\n# Title\n\nParagraph.\n"
    original = parse_mdx_blocks(mdx)
    improved = parse_mdx_blocks(mdx)
    changes, alignment = diff_blocks(original, improved)
    assert changes == []
    assert len(alignment) == len(original)


def test_text_change_in_paragraph():
    original_mdx = "# Title\n\n접근 제어를 설정합니다.\n"
    improved_mdx = "# Title\n\n접근 통제를 설정합니다.\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original, improved)

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
    changes, alignment = diff_blocks(original, improved)

    assert len(changes) == 2


# ---- Phase 2: Optional 필드 테스트 ----

def test_block_change_supports_optional_blocks():
    """BlockChange가 old_block=None (added), new_block=None (deleted)을 허용한다."""
    block = MdxBlock(type='paragraph', content='Hello', line_start=1, line_end=1)

    added = BlockChange(index=0, change_type='added', old_block=None, new_block=block)
    assert added.old_block is None
    assert added.new_block is block

    deleted = BlockChange(index=0, change_type='deleted', old_block=block, new_block=None)
    assert deleted.old_block is block
    assert deleted.new_block is None


# ---- Phase 2: SequenceMatcher 기반 테스트 ----

def test_diff_returns_tuple():
    """diff_blocks가 (changes, alignment) 튜플을 반환한다."""
    mdx = "# Title\n\nParagraph.\n"
    original = parse_mdx_blocks(mdx)
    improved = parse_mdx_blocks(mdx)
    result = diff_blocks(original, improved)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_paragraph_added():
    """블록 추가 감지."""
    original_mdx = "# Title\n\nPara one.\n"
    improved_mdx = "# Title\n\nNew para.\n\nPara one.\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original, improved)

    added = [c for c in changes if c.change_type == 'added']
    assert len(added) >= 1
    added_contents = ' '.join(c.new_block.content for c in added)
    assert 'New para' in added_contents
    for c in added:
        assert c.old_block is None


def test_paragraph_deleted():
    """블록 삭제 감지."""
    original_mdx = "# Title\n\nPara one.\n\nPara two.\n"
    improved_mdx = "# Title\n\nPara two.\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original, improved)

    deleted = [c for c in changes if c.change_type == 'deleted']
    assert len(deleted) >= 1
    deleted_contents = ' '.join(c.old_block.content for c in deleted)
    assert 'Para one' in deleted_contents
    for c in deleted:
        assert c.new_block is None


def test_block_count_mismatch_no_longer_raises():
    """Phase 2: 블록 수가 달라도 에러 없이 처리."""
    original_mdx = "# Title\n\nParagraph.\n"
    improved_mdx = "# Title\n\nParagraph.\n\nNew paragraph.\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original, improved)
    # 에러 없이 반환
    assert isinstance(changes, list)


def test_alignment_maps_improved_to_original():
    """alignment이 improved index → original index 매핑을 올바르게 생성한다."""
    original_mdx = "# Title\n\nPara one.\n\nPara two.\n"
    improved_mdx = "# Title\n\nNew.\n\nPara one.\n\nPara two.\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original, improved)

    # improved의 "# Title"은 original의 "# Title"에 매핑
    assert alignment[0] == 0


def test_non_content_types_always_match():
    """frontmatter, empty, import_statement는 항상 매칭된다."""
    original_mdx = "---\ntitle: T\n---\n\nimport X from 'y'\n\n# Title\n"
    improved_mdx = "---\ntitle: T\n---\n\nimport X from 'y'\n\nNew para.\n\n# Title\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original, improved)

    # frontmatter, empty, import_statement는 변경으로 나오지 않음
    non_content_changes = [
        c for c in changes
        if (c.old_block and c.old_block.type in ('frontmatter', 'empty', 'import_statement'))
        or (c.new_block and c.new_block.type in ('frontmatter', 'empty', 'import_statement'))
    ]
    # empty 블록은 추가될 수 있으므로, non_content_types 중 실제 내용 블록만 확인
    content_non_content = [
        c for c in non_content_changes
        if c.change_type == 'modified'
    ]
    assert len(content_non_content) == 0


def test_mixed_add_delete_modify():
    """추가 + 삭제 + 수정이 동시에 발생."""
    original_mdx = "# Title\n\nPara one.\n\nPara two.\n\nPara three.\n"
    improved_mdx = "# Title\n\nPara ONE.\n\nNew para.\n\nPara three.\n"
    original = parse_mdx_blocks(original_mdx)
    improved = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original, improved)

    types = {c.change_type for c in changes}
    # 변경이 감지되어야 함
    assert len(changes) >= 2
