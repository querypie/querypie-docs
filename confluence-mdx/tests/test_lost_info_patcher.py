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
