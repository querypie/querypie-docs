"""split_into_sentences 유닛 테스트."""
from converter.context import split_into_sentences


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
