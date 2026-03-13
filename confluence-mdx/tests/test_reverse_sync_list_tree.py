"""Level 0 helper tests for parse_list_tree()."""

from mdx_to_storage import ListNode, parse_list_tree


def test_parse_list_tree_simple_unordered():
    roots = parse_list_tree("- Item 1\n- Item 2\n- Item 3")
    assert len(roots) == 3
    assert all(not node.ordered for node in roots)
    assert roots[0].text == "Item 1"


def test_parse_list_tree_simple_ordered():
    roots = parse_list_tree("1. First\n2. Second\n3. Third")
    assert len(roots) == 3
    assert all(node.ordered for node in roots)
    assert roots[0].text == "First"


def test_parse_list_tree_nested():
    roots = parse_list_tree("- Parent\n    - Child 1\n    - Child 2")
    assert len(roots) == 1
    assert roots[0].text == "Parent"
    assert len(roots[0].children) == 2
    assert roots[0].children[0].text == "Child 1"


def test_parse_list_tree_deeply_nested():
    roots = parse_list_tree("- L0\n    - L1\n        - L2")
    assert roots[0].children[0].children[0].text == "L2"


def test_parse_list_tree_continuation_line():
    roots = parse_list_tree("- Item with\n  continuation")
    assert len(roots) == 1
    assert "continuation" in roots[0].text


def test_parse_list_tree_empty_content():
    assert parse_list_tree("") == []


def test_parse_list_tree_returns_public_type():
    roots = parse_list_tree("- test")
    assert isinstance(roots[0], ListNode)
