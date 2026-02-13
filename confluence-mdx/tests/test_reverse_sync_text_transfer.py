"""text_transfer 유닛 테스트."""
import pytest
from reverse_sync.text_transfer import (
    align_chars,
    find_insert_pos,
    transfer_text_changes,
)


class TestAlignChars:
    def test_identical_strings(self):
        mapping = align_chars('abc', 'abc')
        assert mapping == {0: 0, 1: 1, 2: 2}

    def test_different_whitespace(self):
        mapping = align_chars('a b', 'a  b')
        assert mapping[0] == 0  # 'a'
        assert mapping[2] == 3  # 'b'
        assert mapping[1] == 1  # space mapped to first space

    def test_extra_chars_in_target(self):
        mapping = align_chars('ab', 'aXb')
        assert mapping[0] == 0  # 'a'
        assert mapping[1] == 2  # 'b'

    def test_empty_strings(self):
        mapping = align_chars('', '')
        assert mapping == {}

    def test_spaces_between_anchors(self):
        mapping = align_chars('a b c', 'a  b  c')
        # Non-space chars anchored
        assert mapping[0] == 0  # 'a'
        assert mapping[2] == 3  # 'b'
        assert mapping[4] == 6  # 'c'

    def test_no_common_chars(self):
        mapping = align_chars('abc', 'xyz')
        # No equal matches → only spaces mapped (none here)
        assert mapping == {}


class TestFindInsertPos:
    def test_insert_after_mapped_char(self):
        char_map = {0: 0, 1: 1, 2: 2}
        assert find_insert_pos(char_map, 2) == 2

    def test_insert_at_beginning(self):
        char_map = {1: 1, 2: 2}
        assert find_insert_pos(char_map, 0) == 0

    def test_insert_after_gap(self):
        char_map = {0: 0, 3: 5}
        # Insert at pos 2 → walks back to pos 0 → returns 1
        assert find_insert_pos(char_map, 2) == 1

    def test_empty_map(self):
        assert find_insert_pos({}, 5) == 0


class TestTransferTextChanges:
    def test_simple_word_replacement(self):
        result = transfer_text_changes(
            'hello world', 'hello earth', 'hello world')
        assert result == 'hello earth'

    def test_preserves_xhtml_whitespace(self):
        result = transfer_text_changes(
            'hello world', 'hello earth', 'hello  world')
        assert 'earth' in result

    def test_deletion(self):
        result = transfer_text_changes(
            'hello world', 'hello', 'hello world')
        assert 'world' not in result

    def test_insertion(self):
        result = transfer_text_changes(
            'hello world', 'hello beautiful world', 'hello world')
        assert 'beautiful' in result

    def test_no_change(self):
        result = transfer_text_changes(
            'hello world', 'hello world', 'hello world')
        assert result == 'hello world'

    def test_preserves_xhtml_extra_spaces(self):
        # XHTML has different whitespace from MDX
        result = transfer_text_changes(
            'A B', 'A C', 'A   B')
        assert 'C' in result
        assert 'B' not in result

    def test_korean_text(self):
        result = transfer_text_changes(
            '서버 접속', '서버 연결', '서버 접속')
        assert result == '서버 연결'

    def test_mixed_language(self):
        result = transfer_text_changes(
            'Server 접속 이력', 'Server 연결 이력', 'Server 접속 이력')
        assert result == 'Server 연결 이력'

    def test_empty_old_and_new(self):
        result = transfer_text_changes('', '', 'hello')
        assert result == 'hello'

    def test_multi_word_replacement(self):
        result = transfer_text_changes(
            'the quick brown fox',
            'the slow red fox',
            'the quick brown fox',
        )
        assert result == 'the slow red fox'
