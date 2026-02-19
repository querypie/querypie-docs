import pytest
from reverse_sync.xhtml_patcher import patch_xhtml


def test_simple_text_replacement():
    xhtml = '<p>접근 제어를 설정합니다.</p>'
    patches = [
        {
            'xhtml_xpath': 'p[1]',
            'old_plain_text': '접근 제어를 설정합니다.',
            'new_plain_text': '접근 통제를 설정합니다.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '접근 통제를 설정합니다.' in result
    assert '접근 제어' not in result


def test_preserve_inline_formatting():
    xhtml = '<p><strong>접근 제어</strong>를 설정합니다.</p>'
    patches = [
        {
            'xhtml_xpath': 'p[1]',
            'old_plain_text': '접근 제어를 설정합니다.',
            'new_plain_text': '접근 통제를 설정합니다.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '<strong>접근 통제</strong>' in result
    assert '를 설정합니다.' in result


def test_heading_text_replacement():
    xhtml = '<h2>시스템 아키텍쳐</h2>'
    patches = [
        {
            'xhtml_xpath': 'h2[1]',
            'old_plain_text': '시스템 아키텍쳐',
            'new_plain_text': '시스템 아키텍처',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '<h2>시스템 아키텍처</h2>' in result


def test_no_change_when_text_not_found():
    xhtml = '<p>Original text.</p>'
    patches = [
        {
            'xhtml_xpath': 'p[1]',
            'old_plain_text': 'Not in document.',
            'new_plain_text': 'Replaced.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert result == xhtml  # 변경 없음


def test_compound_xpath_patches_callout_child():
    """복합 xpath로 callout 매크로 내부 자식 요소를 패치한다."""
    xhtml = (
        '<ac:structured-macro ac:name="info">'
        '<ac:rich-text-body>'
        '<p>Original text.</p>'
        '<p>Second para.</p>'
        '</ac:rich-text-body>'
        '</ac:structured-macro>'
    )
    patches = [
        {
            'xhtml_xpath': 'macro-info[1]/p[1]',
            'old_plain_text': 'Original text.',
            'new_plain_text': 'Updated text.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert 'Updated text.' in result
    assert 'Second para.' in result  # 다른 자식은 변경 없음


def test_compound_xpath_inner_html_replacement():
    """복합 xpath로 callout 매크로 자식의 innerHTML을 교체한다."""
    xhtml = (
        '<ac:structured-macro ac:name="note">'
        '<ac:rich-text-body>'
        '<p>Old content.</p>'
        '</ac:rich-text-body>'
        '</ac:structured-macro>'
    )
    patches = [
        {
            'xhtml_xpath': 'macro-note[1]/p[1]',
            'old_plain_text': 'Old content.',
            'new_inner_xhtml': '<strong>New</strong> content.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '<strong>New</strong> content.' in result


def test_compound_xpath_nonexistent_parent():
    """존재하지 않는 부모 매크로의 복합 xpath는 무시된다."""
    xhtml = '<p>Simple paragraph.</p>'
    patches = [
        {
            'xhtml_xpath': 'macro-info[1]/p[1]',
            'old_plain_text': 'Simple paragraph.',
            'new_plain_text': 'Changed.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert result == xhtml  # 변경 없음


def test_compound_xpath_adf_extension():
    """ac:adf-extension 내부 자식 요소를 복합 xpath로 패치한다."""
    xhtml = (
        '<ac:adf-extension>'
        '<ac:adf-node type="panel">'
        '<ac:adf-attribute key="panel-type">note</ac:adf-attribute>'
        '<ac:adf-content>'
        '<p>Original text.</p>'
        '<p>Second para.</p>'
        '</ac:adf-content>'
        '</ac:adf-node>'
        '<ac:adf-fallback><div><p>Original text.</p></div></ac:adf-fallback>'
        '</ac:adf-extension>'
    )
    patches = [
        {
            'xhtml_xpath': 'ac:adf-extension[1]/p[1]',
            'old_plain_text': 'Original text.',
            'new_plain_text': 'Updated text.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert 'Updated text.' in result
    assert 'Second para.' in result


# --- Phase 2: delete/insert 테스트 ---


class TestDeletePatch:
    def test_delete_paragraph(self):
        xhtml = '<h1>Title</h1><p>Para one</p><p>Para two</p>'
        patches = [{'action': 'delete', 'xhtml_xpath': 'p[1]'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>Para one</p>' not in result
        assert '<p>Para two</p>' in result
        assert '<h1>Title</h1>' in result

    def test_delete_heading(self):
        xhtml = '<h1>Title</h1><h2>Sub</h2><p>Text</p>'
        patches = [{'action': 'delete', 'xhtml_xpath': 'h2[1]'}]
        result = patch_xhtml(xhtml, patches)
        assert '<h2>Sub</h2>' not in result
        assert '<h1>Title</h1>' in result

    def test_delete_multiple_preserves_order(self):
        xhtml = '<p>A</p><p>B</p><p>C</p>'
        patches = [
            {'action': 'delete', 'xhtml_xpath': 'p[1]'},
            {'action': 'delete', 'xhtml_xpath': 'p[3]'},
        ]
        result = patch_xhtml(xhtml, patches)
        assert 'A' not in result
        assert '<p>B</p>' in result
        assert 'C' not in result

    def test_delete_nonexistent_xpath_skipped(self):
        xhtml = '<p>Only</p>'
        patches = [{'action': 'delete', 'xhtml_xpath': 'p[99]'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>Only</p>' in result


class TestInsertPatch:
    def test_insert_after_element(self):
        xhtml = '<h1>Title</h1><p>Existing</p>'
        patches = [{'action': 'insert', 'after_xpath': 'h1[1]',
                     'new_element_xhtml': '<p>New para</p>'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>New para</p>' in result
        h1_pos = result.index('<h1>')
        new_pos = result.index('New para')
        exist_pos = result.index('Existing')
        assert h1_pos < new_pos < exist_pos

    def test_insert_at_beginning(self):
        xhtml = '<h1>Title</h1><p>Text</p>'
        patches = [{'action': 'insert', 'after_xpath': None,
                     'new_element_xhtml': '<p>First</p>'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>First</p>' in result
        first_pos = result.index('First')
        title_pos = result.index('Title')
        assert first_pos < title_pos

    def test_insert_at_end(self):
        xhtml = '<h1>Title</h1><p>Last</p>'
        patches = [{'action': 'insert', 'after_xpath': 'p[1]',
                     'new_element_xhtml': '<p>After last</p>'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>After last</p>' in result
        last_pos = result.index('Last')
        after_pos = result.index('After last')
        assert last_pos < after_pos

    def test_insert_nonexistent_anchor_skipped(self):
        xhtml = '<p>Only</p>'
        patches = [{'action': 'insert', 'after_xpath': 'h1[99]',
                     'new_element_xhtml': '<p>Ghost</p>'}]
        result = patch_xhtml(xhtml, patches)
        assert 'Ghost' not in result


class TestPatchOrdering:
    def test_delete_before_insert_before_modify(self):
        xhtml = '<p>Delete me</p><p>Modify me</p><p>Keep</p>'
        patches = [
            {'action': 'delete', 'xhtml_xpath': 'p[1]'},
            {'action': 'insert', 'after_xpath': 'p[2]',
             'new_element_xhtml': '<p>Inserted</p>'},
            {'action': 'modify', 'xhtml_xpath': 'p[2]',
             'old_plain_text': 'Modify me', 'new_plain_text': 'Modified'},
        ]
        result = patch_xhtml(xhtml, patches)
        assert 'Delete me' not in result
        assert 'Inserted' in result
        assert 'Modified' in result

    def test_legacy_patch_without_action_treated_as_modify(self):
        xhtml = '<p>Old text</p>'
        patches = [{'xhtml_xpath': 'p[1]',
                     'old_plain_text': 'Old text',
                     'new_plain_text': 'New text'}]
        result = patch_xhtml(xhtml, patches)
        assert 'New text' in result


def test_remove_space_before_korean_particle_after_strong():
    """<strong> 뒤 조사 앞 공백 제거를 올바르게 패치한다.

    XHTML: <h3>... <strong>AGENT_SECRET</strong> 를 변경해도 괜찮은가요?</h3>
    교정: 'AGENT_SECRET 를' → 'AGENT_SECRET를' (공백 제거)

    old_plain_text는 xhtml_plain_text(element.get_text())에서 오므로 double-space를 포함.
    <strong> 다음 text node의 leading whitespace가 diff에서 삭제된 경우,
    xhtml_patcher가 해당 공백도 제거해야 한다.
    """
    xhtml = '<h3>Q: 운영 도중  <strong>AGENT_SECRET</strong> 를 변경해도 괜찮은가요?</h3>'
    patches = [
        {
            'xhtml_xpath': 'h3[1]',
            # old_plain_text는 element.get_text()에서 오므로 XHTML 그대로의 공백 포함
            'old_plain_text': 'Q: 운영 도중  AGENT_SECRET 를 변경해도 괜찮은가요?',
            'new_plain_text': 'Q: 운영 도중  AGENT_SECRET를 변경해도 괜찮은가요?',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '<strong>AGENT_SECRET</strong>를 변경해도' in result
    assert '<strong>AGENT_SECRET</strong> 를 변경해도' not in result
