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
