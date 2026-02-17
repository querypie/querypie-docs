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
