"""텍스트 정규화 — MDX 블록 content를 XHTML plain text 대응 형태로 변환."""
import html as html_module
import re


EMOJI_RE = re.compile(
    r'[\U0001F000-\U0001F9FF\u2700-\u27BF\uFE00-\uFE0F\u200D]+'
)
# Confluence XHTML에 포함될 수 있는 보이지 않는 문자 (zero-width space, Hangul filler 등)
INVISIBLE_RE = re.compile(
    r'[\u200B\u200C\u200D\u2060\uFEFF\u00AD\u3164\u115F\u1160]+'
)


def normalize_mdx_to_plain(content: str, block_type: str) -> str:
    """MDX 블록 content를 XHTML plain text와 대응하는 형태로 변환한다."""
    text = content.strip()

    if block_type == 'heading':
        s = text.lstrip('#').strip()
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'`([^`]+)`', r'\1', s)
        s = re.sub(r'<[^>]+/?>', '', s)
        s = html_module.unescape(s)
        return s.strip()

    lines = text.split('\n')
    parts = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith('<figure') or s.startswith('<img') or s.startswith('</figure'):
            continue
        # Markdown table separator 행 건너뛰기 (| --- | --- | ...)
        if re.match(r'^\|[\s\-:|]+\|$', s):
            continue
        # Markdown table row: | 구분자 제거하여 셀 내용만 추출
        if s.startswith('|') and s.endswith('|'):
            cells = [c.strip() for c in s.split('|')[1:-1]]
            s = ' '.join(c for c in cells if c)
        s = re.sub(r'^\d+\.\s+', '', s)
        s = re.sub(r'^[-*+]\s+', '', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'`([^`]+)`', r'\1', s)
        # italic *...* 제거 (bold 제거 후이므로 단일 * 만 대상)
        s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', s)
        # Confluence 링크 패턴: "[Title | Anchor](url)" → Title만 추출
        # (XHTML ac:link-body에는 Title만 포함됨)
        s = re.sub(
            r'\[([^\]]+)\]\([^)]+\)',
            lambda m: m.group(1).split(' | ')[0] if ' | ' in m.group(1) else m.group(1),
            s,
        )
        s = re.sub(r'<[^>]+/?>', '', s)
        s = html_module.unescape(s)
        s = s.strip()
        if s:
            parts.append(s)
    return ' '.join(parts)


def collapse_ws(text: str) -> str:
    """연속 공백을 하나의 스페이스로 축약한다."""
    return ' '.join(text.split())


def strip_list_marker(text: str) -> str:
    """공백 없는 텍스트에서 선행 리스트 마커를 제거한다."""
    return re.sub(r'^[-*+]|^\d+\.', '', text)
