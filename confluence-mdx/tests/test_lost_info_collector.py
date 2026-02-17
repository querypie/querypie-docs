"""LostInfoCollector 유닛 테스트."""
from bs4 import BeautifulSoup
from converter.lost_info import LostInfoCollector


def _tag(html: str):
    """HTML 문자열에서 첫 번째 Tag를 반환한다."""
    return BeautifulSoup(html, 'html.parser').find()


class TestLostInfoCollector:
    def test_empty_collector_returns_empty_dict(self):
        c = LostInfoCollector()
        assert c.to_dict() == {}

    def test_add_emoticon(self):
        c = LostInfoCollector()
        node = _tag(
            '<ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:" '
            'ac:emoji-id="atlassian-check_mark" ac:emoji-fallback=":check_mark:"/>'
        )
        c.add_emoticon(node)
        result = c.to_dict()
        assert len(result['emoticons']) == 1
        assert result['emoticons'][0]['name'] == 'tick'
        assert result['emoticons'][0]['shortname'] == ':check_mark:'

    def test_add_link(self):
        c = LostInfoCollector()
        node = _tag(
            '<ac:link><ri:page ri:content-title="Missing Page"/>'
            '<ac:link-body>Missing Page</ac:link-body></ac:link>'
        )
        c.add_link(node)
        result = c.to_dict()
        assert len(result['links']) == 1
        assert result['links'][0]['content_title'] == 'Missing Page'

    def test_add_filename(self):
        c = LostInfoCollector()
        c.add_filename('스크린샷 2024-08-01 오후 2.50.06.png', 'screenshot-20240801-145006.png')
        result = c.to_dict()
        assert len(result['filenames']) == 1
        assert result['filenames'][0]['original'] == '스크린샷 2024-08-01 오후 2.50.06.png'

    def test_add_filename_same_name_skips(self):
        c = LostInfoCollector()
        c.add_filename('image.png', 'image.png')
        assert c.to_dict() == {}

    def test_add_adf_extension(self):
        c = LostInfoCollector()
        node = _tag('<ac:adf-extension><ac:adf-node type="panel"/></ac:adf-extension>')
        c.add_adf_extension(node, 'note')
        result = c.to_dict()
        assert len(result['adf_extensions']) == 1
        assert result['adf_extensions'][0]['panel_type'] == 'note'

    def test_multiple_categories(self):
        c = LostInfoCollector()
        node = _tag('<ac:emoticon ac:name="tick"/>')
        c.add_emoticon(node)
        c.add_filename('orig.png', 'norm.png')
        result = c.to_dict()
        assert 'emoticons' in result
        assert 'filenames' in result
        assert 'links' not in result
