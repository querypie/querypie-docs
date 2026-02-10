import pytest
import yaml
from reverse_sync.mapping_recorder import record_mapping, BlockMapping


def test_simple_mapping():
    xhtml = '<h2>Overview</h2><p>This is a paragraph.</p>'
    mappings = record_mapping(xhtml)

    assert len(mappings) >= 2
    heading_map = [m for m in mappings if m.type == 'heading'][0]
    assert 'Overview' in heading_map.xhtml_plain_text

    para_map = [m for m in mappings if m.type == 'paragraph'][0]
    assert 'This is a paragraph.' in para_map.xhtml_plain_text


def test_mapping_preserves_xhtml_markup():
    xhtml = '<p><strong>Bold</strong> normal text.</p>'
    mappings = record_mapping(xhtml)

    para_map = [m for m in mappings if m.type == 'paragraph'][0]
    assert '<strong>Bold</strong>' in para_map.xhtml_text
    assert para_map.xhtml_plain_text == 'Bold normal text.'


def test_mapping_to_yaml():
    xhtml = '<h2>Title</h2><p>Content.</p>'
    mappings = record_mapping(xhtml)
    yaml_str = yaml.dump(
        [m.__dict__ for m in mappings],
        allow_unicode=True,
        default_flow_style=False,
    )
    assert 'type: heading' in yaml_str
    assert 'type: paragraph' in yaml_str


def test_callout_macro_generates_child_mappings():
    """Callout 매크로(info, note 등)의 ac:rich-text-body 자식이 개별 매핑으로 생성된다."""
    xhtml = (
        '<ac:structured-macro ac:name="info">'
        '<ac:rich-text-body>'
        '<p>First paragraph.</p>'
        '<p>Second paragraph.</p>'
        '<ul><li>item 1</li></ul>'
        '</ac:rich-text-body>'
        '</ac:structured-macro>'
    )
    mappings = record_mapping(xhtml)

    # 부모 매크로 매핑 1개 + 자식 3개 = 총 4개
    assert len(mappings) == 4

    parent = mappings[0]
    assert parent.type == 'html_block'
    assert parent.xhtml_xpath == 'macro-info[1]'
    assert len(parent.children) == 3

    child_p1 = mappings[1]
    assert child_p1.type == 'paragraph'
    assert child_p1.xhtml_xpath == 'macro-info[1]/p[1]'
    assert child_p1.xhtml_plain_text == 'First paragraph.'

    child_p2 = mappings[2]
    assert child_p2.type == 'paragraph'
    assert child_p2.xhtml_xpath == 'macro-info[1]/p[2]'
    assert child_p2.xhtml_plain_text == 'Second paragraph.'

    child_ul = mappings[3]
    assert child_ul.type == 'list'
    assert child_ul.xhtml_xpath == 'macro-info[1]/ul[1]'
    assert 'item 1' in child_ul.xhtml_plain_text


def test_callout_macro_multiple_types():
    """tip, note, warning, panel 등 다양한 callout 매크로가 자식 매핑을 생성한다."""
    for macro_name in ('tip', 'note', 'warning', 'panel'):
        xhtml = (
            f'<ac:structured-macro ac:name="{macro_name}">'
            '<ac:rich-text-body>'
            '<p>Content inside.</p>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        mappings = record_mapping(xhtml)
        assert len(mappings) == 2, f"Failed for macro: {macro_name}"
        assert mappings[0].children == [mappings[1].block_id]


def test_non_callout_macro_no_children():
    """code 이외의 비-callout 매크로는 자식 매핑을 생성하지 않는다."""
    xhtml = (
        '<ac:structured-macro ac:name="expand">'
        '<ac:rich-text-body>'
        '<p>Hidden content.</p>'
        '</ac:rich-text-body>'
        '</ac:structured-macro>'
    )
    mappings = record_mapping(xhtml)
    assert len(mappings) == 1
    assert mappings[0].children == []


from pathlib import Path

def test_mapping_real_testcase():
    xhtml_path = Path(__file__).parent / "testcases" / "793608206" / "page.xhtml"
    if not xhtml_path.exists():
        pytest.skip("Test case not found")
    xhtml = xhtml_path.read_text()
    mappings = record_mapping(xhtml)
    assert len(mappings) > 0
    types = {m.type for m in mappings}
    assert 'heading' in types
    assert 'paragraph' in types or 'table' in types
