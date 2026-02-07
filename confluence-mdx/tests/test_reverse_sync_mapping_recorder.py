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
