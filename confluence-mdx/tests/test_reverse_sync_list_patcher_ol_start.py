"""_get_ordered_list_start 단위 테스트."""
from reverse_sync.list_patcher import _get_ordered_list_start


class TestGetOrderedListStart:
    def test_starts_at_one(self):
        assert _get_ordered_list_start('1. first\n2. second\n') == 1

    def test_starts_at_three(self):
        assert _get_ordered_list_start('3. first\n4. second\n') == 3

    def test_starts_at_zero(self):
        assert _get_ordered_list_start('0. zeroth\n1. first\n') == 0

    def test_unordered_list_returns_none(self):
        assert _get_ordered_list_start('* item\n* item2\n') is None

    def test_empty_returns_none(self):
        assert _get_ordered_list_start('') is None

    def test_indented_ordered_list(self):
        """들여쓰기된 순서 목록도 인식한다."""
        assert _get_ordered_list_start('    5. first\n    6. second\n') == 5
