"""split_into_sentences 및 blockquote 문장 분리 유닛 테스트."""
from bs4 import BeautifulSoup

from converter.context import split_into_sentences
from converter.core import MultiLineParser
from converter.lost_info import LostInfoCollector


class TestSplitIntoSentences:
    def test_korean_paragraph_with_parentheses_and_bold(self):
        """괄호와 bold 마크다운이 포함된 한국어 문단의 문장 분리."""
        line = (
            '+srv 스킴은 TLS 옵션이 자동으로 true이므로 standard string으로 변환하면'
            ' **tls=true**를 수동으로 입력해 주어야 합니다.'
            ' (TXT 레코드에 TLS 옵션이 없기 때문입니다.)'
            ' 따라서 Other options 항목에 위 그림과 같이  **&tls=true**를 입력합니다.'
        )
        result = split_into_sentences(line)
        assert result == [
            '+srv 스킴은 TLS 옵션이 자동으로 true이므로 standard string으로 변환하면'
            ' **tls=true**를 수동으로 입력해 주어야 합니다.',
            '(TXT 레코드에 TLS 옵션이 없기 때문입니다.)',
            '따라서 Other options 항목에 위 그림과 같이  **&tls=true**를 입력합니다.',
        ]


class TestBlockquoteSentenceSplit:
    def test_blockquote_sentences_have_newlines(self):
        """blockquote 안의 문장 분리 결과가 각 줄마다 개행을 포함해야 한다."""
        html = (
            '<blockquote><p>'
            '+srv 스킴은 TLS 옵션이 자동으로 true이므로 standard string으로 변환하면'
            ' tls=true를 수동으로 입력해 주어야 합니다.'
            ' (TXT 레코드에 TLS 옵션이 없기 때문입니다.)'
            ' 따라서 Other options 항목에 위 그림과 같이 tls=true를 입력합니다.'
            '</p></blockquote>'
        )
        soup = BeautifulSoup(html, 'html.parser')
        result = MultiLineParser(soup, collector=LostInfoCollector()).as_markdown
        output = ''.join(result)
        assert output == (
            '> +srv 스킴은 TLS 옵션이 자동으로 true이므로 standard string으로 변환하면'
            ' tls=true를 수동으로 입력해 주어야 합니다.\n'
            '> (TXT 레코드에 TLS 옵션이 없기 때문입니다.)\n'
            '> 따라서 Other options 항목에 위 그림과 같이 tls=true를 입력합니다.\n'
        )
