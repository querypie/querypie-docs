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

    def test_add_image(self):
        c = LostInfoCollector()
        node = _tag(
            '<ac:image ac:width="760">'
            '<ri:attachment ri:filename="img.png"/>'
            '</ac:image>'
        )
        c.add_image(node, 'attachments/img.png')
        result = c.to_dict()
        assert len(result['images']) == 1
        assert result['images'][0]['src'] == 'attachments/img.png'
        assert 'ac:image' in result['images'][0]['raw']

    def test_multiple_categories(self):
        c = LostInfoCollector()
        node = _tag('<ac:emoticon ac:name="tick"/>')
        c.add_emoticon(node)
        c.add_filename('orig.png', 'norm.png')
        result = c.to_dict()
        assert 'emoticons' in result
        assert 'filenames' in result
        assert 'links' not in result


class TestSingleLineParserCollector:
    """SingleLineParser가 collector에 emoticon/link를 기록하는지 테스트한다."""

    def test_emoticon_collected(self):
        from converter.lost_info import LostInfoCollector
        from converter.core import SingleLineParser

        html = (
            '<p><ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:" '
            'ac:emoji-id="atlassian-check_mark" ac:emoji-fallback=":check_mark:"/></p>'
        )
        node = _tag(html)
        collector = LostInfoCollector()
        parser = SingleLineParser(node, collector=collector)
        _ = parser.as_markdown
        result = collector.to_dict()
        assert 'emoticons' in result
        assert result['emoticons'][0]['name'] == 'tick'

    def test_emoticon_without_collector_works(self):
        """collector 없이도 기존 동작이 유지되어야 한다."""
        from converter.core import SingleLineParser

        html = (
            '<p><ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:" '
            'ac:emoji-id="atlassian-check_mark" ac:emoji-fallback=":check_mark:"/></p>'
        )
        node = _tag(html)
        parser = SingleLineParser(node)
        result = parser.as_markdown
        # Should contain emoji character or shortname - either way it should work
        assert len(result) > 0


class TestSingleLineParserTimeDatetime:
    """SingleLineParser가 <time datetime="..."> 태그를 언어별로 올바르게 변환하는지 테스트한다."""

    def test_time_ko(self):
        import converter.context as ctx
        from converter.core import SingleLineParser

        original_lang = ctx.LANGUAGE
        try:
            ctx.LANGUAGE = 'ko'
            node = _tag('<p><time datetime="2025-08-29" /></p>')
            result = SingleLineParser(node).as_markdown
            assert result == '2025년 08월 29일'
        finally:
            ctx.LANGUAGE = original_lang

    def test_time_en(self):
        import converter.context as ctx
        from converter.core import SingleLineParser

        original_lang = ctx.LANGUAGE
        try:
            ctx.LANGUAGE = 'en'
            node = _tag('<p><time datetime="2025-08-29" /></p>')
            result = SingleLineParser(node).as_markdown
            assert result == 'Aug 29, 2025'
        finally:
            ctx.LANGUAGE = original_lang

    def test_time_ja(self):
        import converter.context as ctx
        from converter.core import SingleLineParser

        original_lang = ctx.LANGUAGE
        try:
            ctx.LANGUAGE = 'ja'
            node = _tag('<p><time datetime="2025-08-29" /></p>')
            result = SingleLineParser(node).as_markdown
            assert result == '2025年08月29日'
        finally:
            ctx.LANGUAGE = original_lang

    def test_time_default_iso(self):
        """알 수 없는 언어 코드일 때 ISO 형식으로 fallback한다."""
        import converter.context as ctx
        from converter.core import SingleLineParser

        original_lang = ctx.LANGUAGE
        try:
            ctx.LANGUAGE = 'fr'
            node = _tag('<p><time datetime="2025-08-29" /></p>')
            result = SingleLineParser(node).as_markdown
            assert result == '2025-08-29'
        finally:
            ctx.LANGUAGE = original_lang


class TestConfluenceToMarkdownLostInfos:
    """ConfluenceToMarkdown가 lost_infos를 수집하는지 테스트한다."""

    def test_emoticon_in_paragraph(self):
        from converter.core import ConfluenceToMarkdown

        html = (
            '<p>Check: <ac:emoticon ac:name="tick" '
            'ac:emoji-shortname=":check_mark:" '
            'ac:emoji-id="atlassian-check_mark" '
            'ac:emoji-fallback=":check_mark:"/></p>'
        )
        converter = ConfluenceToMarkdown(html)
        _ = converter.as_markdown()
        lost = converter.lost_infos
        assert 'emoticons' in lost
        assert lost['emoticons'][0]['name'] == 'tick'

    def test_no_lost_info_when_nothing_lost(self):
        from converter.core import ConfluenceToMarkdown

        html = '<p>Simple text</p>'
        converter = ConfluenceToMarkdown(html)
        _ = converter.as_markdown()
        assert converter.lost_infos == {}


class TestMappingYamlLostInfo:
    def test_version_is_2(self):
        import yaml
        from reverse_sync.sidecar import generate_sidecar_mapping

        xhtml = '<h2>Title</h2>'
        mdx = '---\ntitle: test\n---\n\n# Doc\n\n## Title\n'

        result = generate_sidecar_mapping(xhtml, mdx, '12345')
        data = yaml.safe_load(result)
        assert data['version'] == 2

    def test_lost_info_in_mapping_yaml(self):
        import yaml
        from reverse_sync.sidecar import generate_sidecar_mapping

        lost_infos = {
            'emoticons': [{'name': 'tick', 'shortname': ':check_mark:', 'emoji_id': '', 'fallback': '', 'raw': '<ac:emoticon ac:name="tick"/>'}],
        }

        xhtml = '<h2>Title</h2><p>text</p>'
        mdx = '---\ntitle: test\n---\n\n# Doc\n\n## Title\n\ntext\n'

        result = generate_sidecar_mapping(xhtml, mdx, '12345', lost_infos=lost_infos)
        data = yaml.safe_load(result)
        assert data['version'] == 2
        assert 'lost_info' in data
        assert data['lost_info']['emoticons'][0]['name'] == 'tick'

    def test_no_lost_info_when_empty(self):
        import yaml
        from reverse_sync.sidecar import generate_sidecar_mapping

        xhtml = '<h2>Title</h2>'
        mdx = '---\ntitle: test\n---\n\n# Doc\n\n## Title\n'

        result = generate_sidecar_mapping(xhtml, mdx, '12345')
        data = yaml.safe_load(result)
        assert 'lost_info' not in data
