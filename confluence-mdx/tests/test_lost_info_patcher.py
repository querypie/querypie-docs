# tests/test_lost_info_patcher.py
"""lost_info_patcher 유닛 테스트."""
import pytest


class TestPatchEmoticons:
    def test_unicode_emoji_replaced_with_original(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>Check ✔️ done</p>'
        lost_info = {
            'emoticons': [{
                'name': 'tick',
                'shortname': ':check_mark:',
                'emoji_id': 'atlassian-check_mark',
                'fallback': ':check_mark:',
                'raw': '<ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:" ac:emoji-id="atlassian-check_mark" ac:emoji-fallback=":check_mark:"/>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:emoticon ac:name="tick"' in result
        assert '✔️' not in result

    def test_fallback_emoji_char_replaced(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>Status ✅</p>'
        lost_info = {
            'emoticons': [{
                'name': 'blue-star',
                'shortname': ':white_check_mark:',
                'emoji_id': '2705',
                'fallback': '✅',
                'raw': '<ac:emoticon ac:name="blue-star" ac:emoji-shortname=":white_check_mark:" ac:emoji-id="2705" ac:emoji-fallback="✅"/>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:emoticon ac:name="blue-star"' in result

    def test_no_emoticons_returns_unchanged(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>No emoji here</p>'
        result = apply_lost_info(emitted, {})
        assert result == emitted

    def test_multiple_emoticons_sequential(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>✔️ first ✅ second</p>'
        lost_info = {
            'emoticons': [
                {'name': 'tick', 'shortname': ':check_mark:', 'emoji_id': '', 'fallback': ':check_mark:',
                 'raw': '<ac:emoticon ac:name="tick"/>'},
                {'name': 'blue-star', 'shortname': '', 'emoji_id': '', 'fallback': '✅',
                 'raw': '<ac:emoticon ac:name="blue-star"/>'},
            ],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:emoticon ac:name="tick"/>' in result
        assert '<ac:emoticon ac:name="blue-star"/>' in result

    def test_emoticon_not_found_skipped(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>No matching emoji</p>'
        lost_info = {
            'emoticons': [{'name': 'tick', 'shortname': ':check_mark:', 'emoji_id': '', 'fallback': ':check_mark:',
                           'raw': '<ac:emoticon ac:name="tick"/>'}],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted


class TestPatchLinks:
    def test_link_error_replaced_with_original(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p><a href="#link-error">Missing Page</a></p>'
        lost_info = {
            'links': [{
                'content_title': 'Missing Page',
                'space_key': '',
                'raw': '<ac:link><ri:page ri:content-title="Missing Page"/><ac:link-body>Missing Page</ac:link-body></ac:link>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:link>' in result
        assert 'ri:content-title="Missing Page"' in result
        assert '#link-error' not in result

    def test_multiple_link_errors_sequential(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p><a href="#link-error">Page A</a> and <a href="#link-error">Page B</a></p>'
        lost_info = {
            'links': [
                {'content_title': 'Page A', 'space_key': '', 'raw': '<ac:link><ri:page ri:content-title="Page A"/><ac:link-body>Page A</ac:link-body></ac:link>'},
                {'content_title': 'Page B', 'space_key': '', 'raw': '<ac:link><ri:page ri:content-title="Page B"/><ac:link-body>Page B</ac:link-body></ac:link>'},
            ],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result.count('<ac:link>') == 2

    def test_no_link_error_skipped(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p><a href="https://example.com">Link</a></p>'
        lost_info = {
            'links': [{'content_title': 'Page', 'space_key': '', 'raw': '<ac:link>...</ac:link>'}],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted


class TestPatchFilenames:
    def test_normalized_filename_restored(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<ac:image ac:align="center"><ri:attachment ri:filename="screenshot-20240801-145006.png"></ri:attachment></ac:image>'
        lost_info = {
            'filenames': [{
                'original': '스크린샷 2024-08-01 오후 2.50.06.png',
                'normalized': 'screenshot-20240801-145006.png',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '스크린샷 2024-08-01 오후 2.50.06.png' in result
        assert 'screenshot-20240801-145006.png' not in result

    def test_filename_not_found_skipped(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<ac:image><ri:attachment ri:filename="other.png"></ri:attachment></ac:image>'
        lost_info = {
            'filenames': [{'original': 'orig.png', 'normalized': 'norm.png'}],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted


class TestPatchAdfExtensions:
    def test_structured_macro_replaced_with_adf(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<ac:structured-macro ac:name="note"><ac:rich-text-body><p>content</p></ac:rich-text-body></ac:structured-macro>'
        lost_info = {
            'adf_extensions': [{
                'panel_type': 'note',
                'raw': '<ac:adf-extension><ac:adf-node type="panel"><ac:adf-attribute key="panel-type">note</ac:adf-attribute><ac:adf-content><p>content</p></ac:adf-content></ac:adf-node></ac:adf-extension>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:adf-extension>' in result
        assert '<ac:structured-macro' not in result

    def test_panel_type_mismatch_skipped(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<ac:structured-macro ac:name="info"><ac:rich-text-body><p>text</p></ac:rich-text-body></ac:structured-macro>'
        lost_info = {
            'adf_extensions': [{
                'panel_type': 'error',
                'raw': '<ac:adf-extension>...</ac:adf-extension>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted

    def test_no_adf_returns_unchanged(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>No ADF here</p>'
        lost_info = {
            'adf_extensions': [{'panel_type': 'note', 'raw': '<ac:adf-extension>...</ac:adf-extension>'}],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted


class TestPatchImages:
    def test_img_tag_replaced_with_ac_image(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p>See <img src="attachments/img.png" alt="screenshot" /> here</p>'
        lost_info = {
            'images': [{
                'src': 'attachments/img.png',
                'raw': '<ac:image ac:width="760"><ri:attachment ri:filename="img.png"/></ac:image>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:image ac:width="760">' in result
        assert '<img ' not in result

    def test_img_with_width_attribute_replaced(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p><img src="attachments/img.png" alt="img.png" width="760" /></p>'
        lost_info = {
            'images': [{
                'src': 'attachments/img.png',
                'raw': '<ac:image ac:custom-width="true" ac:width="760"><ri:attachment ri:filename="img.png"/></ac:image>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:image ac:custom-width="true"' in result
        assert '<img ' not in result

    def test_img_src_no_match_skipped(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p><img src="attachments/other.png" alt="other" /></p>'
        lost_info = {
            'images': [{
                'src': 'attachments/img.png',
                'raw': '<ac:image><ri:attachment ri:filename="img.png"/></ac:image>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result == emitted

    def test_multiple_images_sequential(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = (
            '<p><img src="attachments/a.png" alt="a" /> and '
            '<img src="attachments/b.png" alt="b" /></p>'
        )
        lost_info = {
            'images': [
                {'src': 'attachments/a.png', 'raw': '<ac:image><ri:attachment ri:filename="a.png"/></ac:image>'},
                {'src': 'attachments/b.png', 'raw': '<ac:image><ri:attachment ri:filename="b.png"/></ac:image>'},
            ],
        }
        result = apply_lost_info(emitted, lost_info)
        assert result.count('<ac:image>') == 2
        assert '<img ' not in result

    def test_self_closing_img_tag_replaced(self):
        from reverse_sync.lost_info_patcher import apply_lost_info

        emitted = '<p><img src="attachments/img.png" alt="img.png"></p>'
        lost_info = {
            'images': [{
                'src': 'attachments/img.png',
                'raw': '<ac:image><ri:attachment ri:filename="img.png"/></ac:image>',
            }],
        }
        result = apply_lost_info(emitted, lost_info)
        assert '<ac:image>' in result


class TestLoadPageLostInfo:
    def test_load_lost_info_from_mapping_yaml(self):
        import tempfile, yaml
        from pathlib import Path
        from reverse_sync.sidecar import load_page_lost_info

        data = {
            'version': 2,
            'source_page_id': '123',
            'mdx_file': 'page.mdx',
            'mappings': [{'xhtml_xpath': 'p[1]', 'xhtml_type': 'paragraph', 'mdx_blocks': [0]}],
            'lost_info': {
                'emoticons': [{'name': 'tick', 'shortname': ':check_mark:', 'emoji_id': '', 'fallback': '', 'raw': '<ac:emoticon ac:name="tick"/>'}],
            },
        }
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f:
            yaml.dump(data, f, allow_unicode=True)
            f.flush()
            result = load_page_lost_info(f.name)

        assert 'emoticons' in result
        assert result['emoticons'][0]['name'] == 'tick'

    def test_no_lost_info_returns_empty(self):
        import tempfile, yaml
        from reverse_sync.sidecar import load_page_lost_info

        data = {
            'version': 2,
            'source_page_id': '123',
            'mdx_file': 'page.mdx',
            'mappings': [],
        }
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f:
            yaml.dump(data, f, allow_unicode=True)
            f.flush()
            result = load_page_lost_info(f.name)

        assert result == {}


class TestDistributeLostInfo:
    def test_emoticon_assigned_to_containing_block(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info
        from reverse_sync.sidecar import SidecarBlock

        blocks = [
            SidecarBlock(block_index=0, xhtml_xpath='h2[1]', xhtml_fragment='<h2>Title</h2>'),
            SidecarBlock(block_index=1, xhtml_xpath='p[1]',
                         xhtml_fragment='<p>Check <ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:"/></p>'),
        ]
        page_lost_info = {
            'emoticons': [{
                'name': 'tick', 'shortname': ':check_mark:', 'emoji_id': '', 'fallback': '',
                'raw': '<ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:"/>',
            }],
        }
        distribute_lost_info(blocks, page_lost_info)
        assert blocks[0].lost_info == {}
        assert 'emoticons' in blocks[1].lost_info
        assert blocks[1].lost_info['emoticons'][0]['name'] == 'tick'

    def test_multiple_categories_distributed(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info
        from reverse_sync.sidecar import SidecarBlock

        blocks = [
            SidecarBlock(block_index=0, xhtml_xpath='p[1]',
                         xhtml_fragment='<p><ac:emoticon ac:name="tick"/></p>'),
            SidecarBlock(block_index=1, xhtml_xpath='p[2]',
                         xhtml_fragment='<p><ac:link><ri:page ri:content-title="Page"/></ac:link></p>'),
        ]
        page_lost_info = {
            'emoticons': [{'name': 'tick', 'shortname': '', 'emoji_id': '', 'fallback': '',
                           'raw': '<ac:emoticon ac:name="tick"/>'}],
            'links': [{'content_title': 'Page', 'space_key': '',
                       'raw': '<ac:link><ri:page ri:content-title="Page"/></ac:link>'}],
        }
        distribute_lost_info(blocks, page_lost_info)
        assert 'emoticons' in blocks[0].lost_info
        assert 'links' in blocks[1].lost_info

    def test_empty_lost_info_no_change(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info
        from reverse_sync.sidecar import SidecarBlock

        blocks = [SidecarBlock(block_index=0, xhtml_xpath='p[1]', xhtml_fragment='<p>text</p>')]
        distribute_lost_info(blocks, {})
        assert blocks[0].lost_info == {}

    def test_filename_distributed_by_normalized_name(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info
        from reverse_sync.sidecar import SidecarBlock

        blocks = [
            SidecarBlock(block_index=0, xhtml_xpath='p[1]',
                         xhtml_fragment='<ac:image><ri:attachment ri:filename="스크린샷.png"></ri:attachment></ac:image>'),
        ]
        page_lost_info = {
            'filenames': [{'original': '스크린샷.png', 'normalized': 'screenshot.png'}],
        }
        distribute_lost_info(blocks, page_lost_info)
        # Filenames match by ORIGINAL name in the XHTML fragment (original is in the source XHTML)
        assert 'filenames' in blocks[0].lost_info


class TestDistributeLostInfoToMappings:
    def test_emoticon_distributed_to_matching_mapping(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info_to_mappings
        from reverse_sync.mapping_recorder import BlockMapping

        mappings = [
            BlockMapping(block_id='h1', type='heading', xhtml_xpath='h2[1]',
                         xhtml_text='<h2>Title</h2>', xhtml_plain_text='Title',
                         xhtml_element_index=0),
            BlockMapping(block_id='p1', type='paragraph', xhtml_xpath='p[1]',
                         xhtml_text='<p>Check <ac:emoticon ac:name="tick"/></p>',
                         xhtml_plain_text='Check', xhtml_element_index=1),
        ]
        page_lost_info = {
            'emoticons': [{
                'name': 'tick', 'shortname': '', 'emoji_id': '', 'fallback': '',
                'raw': '<ac:emoticon ac:name="tick"/>',
            }],
        }
        result = distribute_lost_info_to_mappings(mappings, page_lost_info)
        assert 'h1' not in result
        assert 'p1' in result
        assert 'emoticons' in result['p1']

    def test_image_distributed_to_matching_mapping(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info_to_mappings
        from reverse_sync.mapping_recorder import BlockMapping

        mappings = [
            BlockMapping(block_id='p1', type='paragraph', xhtml_xpath='p[1]',
                         xhtml_text='<p>See <ac:image><ri:attachment ri:filename="img.png"/></ac:image></p>',
                         xhtml_plain_text='See', xhtml_element_index=0),
        ]
        page_lost_info = {
            'images': [{
                'src': 'attachments/img.png',
                'raw': '<ac:image><ri:attachment ri:filename="img.png"/></ac:image>',
            }],
        }
        result = distribute_lost_info_to_mappings(mappings, page_lost_info)
        assert 'p1' in result
        assert 'images' in result['p1']

    def test_empty_page_lost_info_returns_empty(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info_to_mappings
        from reverse_sync.mapping_recorder import BlockMapping

        mappings = [
            BlockMapping(block_id='p1', type='paragraph', xhtml_xpath='p[1]',
                         xhtml_text='<p>text</p>', xhtml_plain_text='text',
                         xhtml_element_index=0),
        ]
        result = distribute_lost_info_to_mappings(mappings, {})
        assert result == {}

    def test_filename_distributed_by_original(self):
        from reverse_sync.lost_info_patcher import distribute_lost_info_to_mappings
        from reverse_sync.mapping_recorder import BlockMapping

        mappings = [
            BlockMapping(block_id='img1', type='html_block', xhtml_xpath='ac:image[1]',
                         xhtml_text='<ac:image><ri:attachment ri:filename="스크린샷.png"/></ac:image>',
                         xhtml_plain_text='', xhtml_element_index=0),
        ]
        page_lost_info = {
            'filenames': [{'original': '스크린샷.png', 'normalized': 'screenshot.png'}],
        }
        result = distribute_lost_info_to_mappings(mappings, page_lost_info)
        assert 'img1' in result
        assert 'filenames' in result['img1']


class TestSpliceWithLostInfo:
    def test_emitted_block_gets_lost_info_applied(self):
        """splice 경로에서 emitter 출력에 lost_info가 적용되는지 테스트."""
        from reverse_sync.rehydrator import splice_rehydrate_xhtml
        from reverse_sync.sidecar import RoundtripSidecar, SidecarBlock, DocumentEnvelope, sha256_text

        # 변경된 MDX (hash 불일치하도록)
        mdx_text = '## Title\n\nCheck ✔️ done\n'

        # Sidecar: block 1의 hash가 불일치하도록 설정
        sidecar = RoundtripSidecar(
            page_id='test',
            mdx_sha256='different',
            source_xhtml_sha256='test',
            blocks=[
                SidecarBlock(
                    block_index=0,
                    xhtml_xpath='h2[1]',
                    xhtml_fragment='<h2>Title</h2>',
                    mdx_content_hash=sha256_text('## Title'),
                ),
                SidecarBlock(
                    block_index=1,
                    xhtml_xpath='p[1]',
                    xhtml_fragment='<p>original <ac:emoticon ac:name="tick"/></p>',
                    mdx_content_hash='wrong_hash',  # 불일치 → emitter 호출
                    lost_info={
                        'emoticons': [{
                            'name': 'tick',
                            'shortname': ':check_mark:',
                            'emoji_id': '',
                            'fallback': ':check_mark:',
                            'raw': '<ac:emoticon ac:name="tick"/>',
                        }],
                    },
                ),
            ],
            separators=['\n'],
            document_envelope=DocumentEnvelope(prefix='', suffix=''),
        )

        result = splice_rehydrate_xhtml(mdx_text, sidecar)
        # emitter가 ✔️를 출력하지만, lost_info로 <ac:emoticon>으로 복원됨
        assert '<ac:emoticon ac:name="tick"/>' in result.xhtml


class TestInsertPatchWithLostInfo:
    def test_insert_patch_applies_lost_info(self):
        from reverse_sync.patch_builder import build_patches
        from reverse_sync.block_diff import BlockChange
        from reverse_sync.mapping_recorder import BlockMapping
        from reverse_sync.mdx_block_parser import MdxBlock
        from reverse_sync.sidecar import SidecarEntry

        # added 블록 (emoticon 포함)
        new_block = MdxBlock(type='paragraph', content='Check ✔️ done',
                             line_start=0, line_end=1)
        change = BlockChange(index=0, change_type='added',
                             old_block=None, new_block=new_block)

        anchor_block = MdxBlock(type='heading', content='## Title',
                                line_start=0, line_end=1)
        mappings = [BlockMapping(block_id='h1', type='heading',
                                 xhtml_xpath='h2[1]', xhtml_text='<h2>Title</h2>',
                                 xhtml_plain_text='Title',
                                 xhtml_element_index=0, children=[])]

        sidecar_entry = SidecarEntry(xhtml_xpath='h2[1]', xhtml_type='heading', mdx_blocks=[0])
        mdx_to_sidecar = {0: sidecar_entry}
        xpath_to_mapping = {'h2[1]': mappings[0]}
        alignment = {0: 0}

        page_lost_info = {
            'emoticons': [{
                'name': 'tick', 'shortname': ':check_mark:',
                'emoji_id': '', 'fallback': ':check_mark:',
                'raw': '<ac:emoticon ac:name="tick"/>',
            }],
        }

        patches = build_patches(
            [change], [anchor_block], [anchor_block, new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            alignment, page_lost_info=page_lost_info)

        assert len(patches) == 1
        assert patches[0]['action'] == 'insert'
        assert '<ac:emoticon ac:name="tick"/>' in patches[0]['new_element_xhtml']
