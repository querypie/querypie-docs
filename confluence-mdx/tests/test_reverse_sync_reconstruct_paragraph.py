"""Phase 3 paragraph/list-item inline-anchor 재구성 테스트."""
import pytest
from reverse_sync.sidecar import _build_anchor_entries  # noqa: import check


class TestBuildAnchorEntries:
    def test_empty_paragraph_returns_empty(self):
        """ac:image 없는 단순 paragraph는 빈 anchors를 반환한다."""
        fragment = '<p>Simple text without images.</p>'
        anchors = _build_anchor_entries(fragment)
        assert anchors == []

    def test_paragraph_with_inline_image(self):
        """paragraph 안 ac:image를 anchor로 추출한다."""
        fragment = (
            '<p>Text before '
            '<ac:image ac:width="100"><ri:attachment ri:filename="img.png"/></ac:image>'
            ' text after</p>'
        )
        anchors = _build_anchor_entries(fragment)
        assert len(anchors) == 1
        assert anchors[0]['kind'] == 'image'
        assert anchors[0]['offset'] == len('Text before ')
        assert 'ac:image' in anchors[0]['raw_xhtml']

    def test_paragraph_with_multiple_images(self):
        """여러 ac:image를 순서대로 추출한다."""
        fragment = (
            '<p>'
            '<ac:image ac:width="50"><ri:attachment ri:filename="a.png"/></ac:image>'
            'middle'
            '<ac:image ac:width="50"><ri:attachment ri:filename="b.png"/></ac:image>'
            '</p>'
        )
        anchors = _build_anchor_entries(fragment)
        assert len(anchors) == 2
        assert anchors[0]['offset'] == 0
        assert anchors[1]['offset'] == len('middle')

    def test_image_in_list_item_ignored(self):
        """li 직속 자식 ac:image(p 밖)는 anchors에 포함하지 않는다."""
        fragment = (
            '<li>'
            '<p>List item text</p>'
            '<ac:image ac:width="100"><ri:attachment ri:filename="img.png"/></ac:image>'
            '</li>'
        )
        anchors = _build_anchor_entries(fragment)
        assert anchors == []

    def test_no_paragraph_returns_empty(self):
        """p 요소가 없는 fragment는 빈 anchors를 반환한다."""
        fragment = '<h2>Just a heading</h2>'
        anchors = _build_anchor_entries(fragment)
        assert anchors == []
