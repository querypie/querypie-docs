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

    def test_repeated_pattern_long_text(self):
        """반복 패턴이 있는 긴 텍스트에서 로컬 변경만 적용되는지 검증.

        SequenceMatcher autojunk=True일 때 반복 패턴이 있으면
        대규모 insert/delete를 생성하여 텍스트가 붕괴되는 버그를 방지.
        """
        # "700MB를 초과"가 두 번 등장하는 긴 텍스트
        xhtml_text = (
            '첫째 항목 텍스트입니다.'
            '둘째 항목 700MB를 초과 여부에 따라 재생화면을 노출합니다. '
            '700MB 미만 상단에 기본 정보가 노출됩니다. '
            '재생화면이 하단에 노출됩니다. '
            '700MB 이상 재생 화면 안에 실행 불가 문구를 제공합니다. '
            '파일 크기가 700MB를 초과하여 세션을 재생할 수 없습니다.'
        )
        mdx_old = (
            '첫째 항목 텍스트입니다. '
            '둘째 항목 700MB를 초과 여부에 따라 재생화면을 노출합니다. '
            '700MB 미만 상단에 기본 정보가 노출됩니다. '
            '재생화면이 하단에 노출됩니다. '
            '700MB 이상 재생 화면 안에 실행 불가 문구를 제공합니다. '
            '파일 크기가 700MB를 초과하여 세션을 재생할 수 없습니다.'
        )
        mdx_new = (
            '첫째 항목 텍스트입니다. '
            '둘째 항목 700MB 초과 여부에 따라 재생 화면을 노출합니다. '
            '700MB 미만 상단에 기본 정보가 노출됩니다. '
            '재생 화면이 하단에 노출됩니다. '
            '700MB 이상 재생 화면 안에 실행 불가 문구를 제공합니다. '
            '파일 크기가 700MB를 초과하여 세션을 재생할 수 없습니다.'
        )
        result = transfer_text_changes(mdx_old, mdx_new, xhtml_text)
        # "를" 삭제, 두 곳의 "재생화면" → "재생 화면" 변경만 적용
        assert '700MB 초과 여부' in result
        assert '700MB를 초과 여부' not in result
        assert '재생 화면을 노출합니다' in result
        assert '재생 화면이 하단에' in result
        # 나머지 텍스트는 보존
        assert '첫째 항목 텍스트입니다.' in result
        assert '700MB를 초과하여 세션을' in result
