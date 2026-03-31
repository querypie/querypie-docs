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


class TestMapAnchorOffset:
    def test_no_change_preserves_offset(self):
        """텍스트 변경 없으면 offset 그대로 유지된다."""
        from reverse_sync.reconstructors import map_anchor_offset
        result = map_anchor_offset('hello world', 'hello world', 5)
        assert result == 5

    def test_insert_before_anchor_shifts_offset(self):
        """anchor 앞에 텍스트 삽입 시 offset이 증가한다."""
        from reverse_sync.reconstructors import map_anchor_offset
        # old: "AB", anchor at 1 (between A and B)
        # new: "XAB" (X inserted before A)
        result = map_anchor_offset('AB', 'XAB', 1)
        # After inserting X before A, old offset 1 (end of A) → new offset 2 (end of A in XAB)
        assert result == 2

    def test_delete_before_anchor_shifts_offset(self):
        """anchor 앞 텍스트 삭제 시 offset이 감소한다."""
        from reverse_sync.reconstructors import map_anchor_offset
        # old: "XAB", anchor at 2 (end of XA)
        # new: "AB" (X deleted)
        result = map_anchor_offset('XAB', 'AB', 2)
        # anchor was after "XA", now after "A" → offset 1
        assert result == 1

    def test_replace_before_anchor(self):
        """anchor 앞 텍스트 교체 시 offset이 새 길이로 조정된다."""
        from reverse_sync.reconstructors import map_anchor_offset
        # old: "hello world", anchor at 5 (after "hello")
        # new: "hi world" (hello→hi)
        result = map_anchor_offset('hello world', 'hi world', 5)
        # "hello" replaced by "hi" → anchor moves from 5 to 2
        assert result == 2

    def test_offset_at_end_stays_at_end(self):
        """anchor가 텍스트 끝이면 새 끝으로 이동한다."""
        from reverse_sync.reconstructors import map_anchor_offset
        result = map_anchor_offset('hello', 'world2', 5)
        assert result == 6


class TestInsertAnchorAtOffset:
    def test_insert_at_beginning(self):
        """offset=0이면 첫 텍스트 노드 앞에 삽입된다."""
        from reverse_sync.reconstructors import insert_anchor_at_offset
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<p>hello</p>', 'html.parser')
        p = soup.find('p')
        anchor_html = '<ac:image ac:width="50"><ri:attachment ri:filename="x.png"/></ac:image>'
        insert_anchor_at_offset(p, 0, anchor_html)
        result = str(soup)
        assert result.index('ac:image') < result.index('hello')

    def test_insert_in_middle(self):
        """offset이 중간이면 해당 텍스트 위치에 삽입된다."""
        from reverse_sync.reconstructors import insert_anchor_at_offset
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<p>helloworld</p>', 'html.parser')
        p = soup.find('p')
        anchor_html = '<ac:image ac:width="50"><ri:attachment ri:filename="x.png"/></ac:image>'
        insert_anchor_at_offset(p, 5, anchor_html)
        result = str(p)
        # hello[image]world 순서여야 함
        idx_hello = result.index('hello')
        idx_image = result.index('ac:image')
        idx_world = result.index('world')
        assert idx_hello < idx_image < idx_world

    def test_insert_at_end(self):
        """offset이 텍스트 끝이면 마지막 텍스트 뒤에 삽입된다."""
        from reverse_sync.reconstructors import insert_anchor_at_offset
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<p>hello</p>', 'html.parser')
        p = soup.find('p')
        anchor_html = '<ac:image ac:width="50"><ri:attachment ri:filename="x.png"/></ac:image>'
        insert_anchor_at_offset(p, 5, anchor_html)
        result = str(p)
        assert result.index('hello') < result.index('ac:image')


class TestReconstructInlineAnchorFragment:
    def test_basic_text_change_preserves_image(self):
        """텍스트 변경 시 ac:image가 보존된다."""
        from reverse_sync.reconstructors import reconstruct_inline_anchor_fragment
        old_fragment = (
            '<p>Old text '
            '<ac:image ac:width="100"><ri:attachment ri:filename="img.png"/></ac:image>'
            ' rest</p>'
        )
        new_fragment = '<p>New text rest</p>'  # emitted from new MDX
        anchors = [{'kind': 'image', 'offset': len('Old text '), 'raw_xhtml': '<ac:image ac:width="100"><ri:attachment ri:filename="img.png"/></ac:image>'}]

        result = reconstruct_inline_anchor_fragment(old_fragment, anchors, new_fragment)
        assert 'ac:image' in result
        assert 'New text' in result
        assert 'rest' in result


class TestPatchBuilderInlineAnchor:
    """patch_builder가 anchor가 있는 paragraph를 올바르게 처리하는지 통합 테스트."""

    def test_changed_paragraph_with_image_preserves_image(self):
        """텍스트가 변경된 paragraph의 ac:image가 보존된다."""
        import yaml
        from mdx_to_storage.parser import parse_mdx_blocks
        from reverse_sync.block_diff import diff_blocks
        from reverse_sync.mapping_recorder import record_mapping
        from reverse_sync.patch_builder import build_patches
        from reverse_sync.sidecar import (
            SidecarEntry, build_mdx_to_sidecar_index, build_sidecar,
            build_xpath_to_mapping, generate_sidecar_mapping,
        )
        from reverse_sync.xhtml_patcher import patch_xhtml

        xhtml = (
            '<p>Original text '
            '<ac:image ac:width="100"><ri:attachment ri:filename="img.png"/></ac:image>'
            ' more text</p>'
        )
        original_mdx = '---\ntitle: test\n---\n\n# Test\n\nOriginal text more text\n'
        improved_mdx = '---\ntitle: test\n---\n\n# Test\n\nChanged text more text\n'

        orig_blocks = list(parse_mdx_blocks(original_mdx))
        imp_blocks = list(parse_mdx_blocks(improved_mdx))
        changes, alignment = diff_blocks(orig_blocks, imp_blocks)

        mappings = record_mapping(xhtml)
        roundtrip_sidecar = build_sidecar(xhtml, original_mdx)
        sidecar_yaml = generate_sidecar_mapping(xhtml, original_mdx)
        sidecar_data = yaml.safe_load(sidecar_yaml) or {}
        sidecar_entries = [
            SidecarEntry(
                xhtml_xpath=item['xhtml_xpath'],
                xhtml_type=item.get('xhtml_type', ''),
                mdx_blocks=item.get('mdx_blocks', []),
                mdx_line_start=item.get('mdx_line_start', 0),
                mdx_line_end=item.get('mdx_line_end', 0),
            )
            for item in sidecar_data.get('mappings', [])
        ]
        mdx_to_sidecar = build_mdx_to_sidecar_index(sidecar_entries)
        xpath_to_mapping = build_xpath_to_mapping(mappings)

        patches, *_ = build_patches(
            changes, orig_blocks, imp_blocks,
            mappings, mdx_to_sidecar, xpath_to_mapping,
            alignment, roundtrip_sidecar=roundtrip_sidecar,
        )
        result = patch_xhtml(xhtml, patches)

        assert 'ac:image' in result
        assert 'ri:attachment' in result
        assert 'Changed text' in result
        assert 'Original text' not in result


class TestBuildListAnchorEntries:
    def test_list_with_inline_image(self):
        from reverse_sync.sidecar import _build_list_anchor_entries
        fragment = (
            '<ul>'
            '<li><p>item '
            '<ac:image ac:width="50"><ri:attachment ri:filename="a.png"/></ac:image>'
            ' text</p></li>'
            '</ul>'
        )
        entries = _build_list_anchor_entries(fragment)
        assert len(entries) == 1
        assert entries[0]['path'] == [0]
        assert entries[0]['offset'] == len('item ')
        assert 'a.png' in entries[0]['raw_xhtml']

    def test_nested_list_with_image(self):
        from reverse_sync.sidecar import _build_list_anchor_entries
        fragment = (
            '<ul><li><p>outer</p>'
            '<ul><li><p>'
            '<ac:image ac:width="50"><ri:attachment ri:filename="b.png"/></ac:image>'
            'nested</p></li></ul>'
            '</li></ul>'
        )
        entries = _build_list_anchor_entries(fragment)
        assert len(entries) == 1
        assert entries[0]['path'] == [0, 0]
        assert entries[0]['offset'] == 0

    def test_list_without_images_returns_empty(self):
        from reverse_sync.sidecar import _build_list_anchor_entries
        fragment = '<ul><li><p>plain text</p></li></ul>'
        entries = _build_list_anchor_entries(fragment)
        assert entries == []

    def test_multiple_items_with_images(self):
        from reverse_sync.sidecar import _build_list_anchor_entries
        fragment = (
            '<ul>'
            '<li><p>first '
            '<ac:image ac:width="50"><ri:attachment ri:filename="x.png"/></ac:image>'
            '</p></li>'
            '<li><p>second</p></li>'
            '<li><p>'
            '<ac:image ac:width="50"><ri:attachment ri:filename="y.png"/></ac:image>'
            ' after</p></li>'
            '</ul>'
        )
        entries = _build_list_anchor_entries(fragment)
        assert len(entries) == 2
        assert entries[0]['path'] == [0]
        assert entries[0]['offset'] == len('first ')
        assert entries[1]['path'] == [2]
        assert entries[1]['offset'] == 0
