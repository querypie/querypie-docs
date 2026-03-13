"""Level 0 helper tests — parse_list_tree() public API 검증.

Phase 0 게이트: list tree helper가 public API로 정상 동작하는지 확인한다.
"""

import pytest

from mdx_to_storage import ListNode, parse_list_tree


class TestParseListTree:
    """parse_list_tree() public API 검증."""

    def test_simple_unordered_list(self):
        content = "- Item 1\n- Item 2\n- Item 3"
        roots = parse_list_tree(content)
        assert len(roots) == 3
        assert all(not node.ordered for node in roots)
        assert roots[0].text == "Item 1"
        assert roots[1].text == "Item 2"
        assert roots[2].text == "Item 3"

    def test_simple_ordered_list(self):
        content = "1. First\n2. Second\n3. Third"
        roots = parse_list_tree(content)
        assert len(roots) == 3
        assert all(node.ordered for node in roots)
        assert roots[0].text == "First"
        assert roots[0].start == 1
        assert roots[1].start == 2
        assert roots[2].start == 3

    def test_nested_list(self):
        content = "- Parent\n    - Child 1\n    - Child 2"
        roots = parse_list_tree(content)
        assert len(roots) == 1
        assert roots[0].text == "Parent"
        assert len(roots[0].children) == 2
        assert roots[0].children[0].text == "Child 1"
        assert roots[0].children[1].text == "Child 2"

    def test_mixed_ordered_unordered(self):
        content = "- Unordered\n1. Ordered"
        roots = parse_list_tree(content)
        assert len(roots) == 2
        assert not roots[0].ordered
        assert roots[1].ordered

    def test_deeply_nested(self):
        content = "- L0\n    - L1\n        - L2"
        roots = parse_list_tree(content)
        assert len(roots) == 1
        assert len(roots[0].children) == 1
        assert len(roots[0].children[0].children) == 1
        assert roots[0].children[0].children[0].text == "L2"

    def test_continuation_line(self):
        content = "- Item with\n  continuation"
        roots = parse_list_tree(content)
        assert len(roots) == 1
        assert "continuation" in roots[0].text

    def test_empty_content(self):
        roots = parse_list_tree("")
        assert roots == []

    def test_list_node_type(self):
        """반환값이 ListNode 인스턴스인지 확인."""
        roots = parse_list_tree("- test")
        assert isinstance(roots[0], ListNode)

    def test_nested_ordered_under_unordered(self):
        content = "- Parent\n    1. Child ordered"
        roots = parse_list_tree(content)
        assert len(roots) == 1
        assert not roots[0].ordered
        assert roots[0].start is None  # unordered → no start
        assert len(roots[0].children) == 1
        assert roots[0].children[0].ordered
        assert roots[0].children[0].start == 1

    def test_ordered_list_start_number_preserved(self):
        """중간부터 시작하는 ordered list의 marker number가 보존된다."""
        content = "2. Second\n3. Third\n4. Fourth"
        roots = parse_list_tree(content)
        assert len(roots) == 3
        assert roots[0].start == 2
        assert roots[1].start == 3
        assert roots[2].start == 4
