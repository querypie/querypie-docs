"""테이블 블록 패치 유틸리티."""


def is_markdown_table(content: str) -> bool:
    """Content가 Markdown table 형식인지 판별한다."""
    lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        return False
    pipe_lines = sum(1 for l in lines if l.startswith('|') and l.endswith('|'))
    return pipe_lines >= 2
