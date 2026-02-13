"""_find_containing_mapping() 유닛 테스트."""
from reverse_sync.patch_builder import _find_containing_mapping
from reverse_sync.mapping_recorder import BlockMapping


def _make_mapping(block_id: str, xhtml_plain_text: str) -> BlockMapping:
    return BlockMapping(
        block_id=block_id,
        type='paragraph',
        xhtml_xpath=f'p[{block_id}]',
        xhtml_text=f'<p>{xhtml_plain_text}</p>',
        xhtml_plain_text=xhtml_plain_text,
        xhtml_element_index=0,
    )


class TestFindContainingMapping:
    def test_finds_mapping_containing_old_plain(self):
        m1 = _make_mapping('m1', 'Command Audit : Server내 수행 명령어 이력')
        m2 = _make_mapping('m2', 'General User Access History Activity Logs Servers Command Audit : Server내 수행 명령어 이력 Account Lock History')
        mappings = [m1, m2]
        result = _find_containing_mapping(
            'Command Audit : Server내 수행 명령어 이력', mappings, set())
        # m1이 정확히 포함하므로 m1 반환
        assert result is m1

    def test_skips_used_ids(self):
        m1 = _make_mapping('m1', 'Command Audit : Server내 수행 명령어 이력')
        m2 = _make_mapping('m2', 'General Servers Command Audit : Server내 수행 명령어 이력 Account Lock')
        mappings = [m1, m2]
        used = {'m1'}
        result = _find_containing_mapping(
            'Command Audit : Server내 수행 명령어 이력', mappings, used)
        assert result is m2

    def test_returns_none_for_short_text(self):
        m1 = _make_mapping('m1', 'hello world foo bar')
        result = _find_containing_mapping('abc', [m1], set())
        assert result is None

    def test_returns_none_for_empty_text(self):
        m1 = _make_mapping('m1', 'hello world foo bar')
        result = _find_containing_mapping('', [m1], set())
        assert result is None

    def test_returns_none_when_no_mapping_contains_text(self):
        m1 = _make_mapping('m1', 'completely different text here')
        result = _find_containing_mapping(
            'Command Audit : Server내 수행 명령어 이력', [m1], set())
        assert result is None

    def test_ignores_whitespace_differences(self):
        m1 = _make_mapping('m1', 'Command  Audit :  Server내   수행 명령어   이력')
        result = _find_containing_mapping(
            'Command Audit : Server내 수행 명령어 이력', [m1], set())
        assert result is m1

    def test_ignores_invisible_unicode_chars(self):
        # Hangul Filler (U+3164) and ZWSP (U+200B) in XHTML text
        m1 = _make_mapping(
            'm1',
            'Account Lock History\u3164 : QueryPie\u200b사용자별 서버 접속 계정')
        result = _find_containing_mapping(
            'Account Lock History : QueryPie사용자별 서버 접속 계정',
            [m1], set())
        assert result is m1
