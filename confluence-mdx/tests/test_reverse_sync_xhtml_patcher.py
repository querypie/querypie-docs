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
