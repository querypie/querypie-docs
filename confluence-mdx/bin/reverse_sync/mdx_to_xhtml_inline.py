"""MDX block content → XHTML inner HTML 변환 모듈.

MDX 블록의 content를 파싱하여 대상 XHTML 요소의 innerHTML로
직접 교체할 수 있는 HTML 문자열을 생성한다.
"""
import re
from typing import List


def mdx_block_to_inner_xhtml(content: str, block_type: str) -> str:
    """MDX 블록 content → XHTML inner HTML.

    heading:    "## Title\\n" → "Title"
    paragraph:  "**bold** and `code`\\n" → "<strong>bold</strong> and <code>code</code>"
    list:       "* item1\\n* item2\\n" → "<li><p>item1</p></li><li><p>item2</p></li>"
    code_block: "```\\ncode\\n```\\n" → "code"
    """
    text = content.strip()

    if block_type == 'heading':
        return _convert_heading(text)
    elif block_type == 'paragraph':
        return _convert_paragraph(text)
    elif block_type == 'list':
        return _convert_list_content(text)
    elif block_type == 'code_block':
        return _convert_code_block(text)
    else:
        return _convert_inline(text)


def _convert_heading(text: str) -> str:
    """heading: # 마커 제거 후 인라인 변환 (bold는 마커만 제거)."""
    stripped = re.sub(r'^#+\s+', '', text)
    # heading 내부의 **bold**는 <strong> 변환 없이 마커만 제거
    # (forward converter가 heading 내부 strong을 strip하므로)
    stripped = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
    # code span과 link는 변환
    stripped = _convert_code_spans(stripped)
    stripped = _convert_links(stripped)
    return stripped


def _convert_paragraph(text: str) -> str:
    """paragraph: 인라인 변환 적용. 여러 줄이면 join."""
    lines = text.split('\n')
    converted = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        converted.append(_convert_inline(line))
    return ''.join(converted)


def _convert_code_block(text: str) -> str:
    """code_block: 펜스 마커 제거, 코드 내용만 추출."""
    lines = text.split('\n')
    # 첫 줄(```)과 마지막 줄(```) 제거
    if lines and lines[0].strip().startswith('```'):
        lines = lines[1:]
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]
    return '\n'.join(lines)


def _convert_inline(text: str) -> str:
    """인라인 마크다운 → XHTML 변환.

    처리 순서 (충돌 방지):
    1. code span (`text` → placeholder) — 내부가 bold/link 처리되지 않도록 보호
    2. bold (**text** → <strong>text</strong>)
    3. link ([text](url) → <a href="url">text</a>)
    4. code span placeholder 복원 → <code>text</code>
    5. HTML entities (&gt;, &lt;) — 이미 XHTML 형식이므로 그대로 유지
    6. <br/> — 그대로 유지
    """
    # 1. code span 추출 → placeholder
    code_spans: List[str] = []
    def _replace_code(m):
        code_spans.append(m.group(1))
        return f'\x00CODE{len(code_spans) - 1}\x00'
    text = re.sub(r'`([^`]+)`', _replace_code, text)

    # 2. bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # 3. link
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # 4. code span placeholder 복원
    def _restore_code(m):
        idx = int(m.group(1))
        return f'<code>{code_spans[idx]}</code>'
    text = re.sub(r'\x00CODE(\d+)\x00', _restore_code, text)

    return text


def _convert_code_spans(text: str) -> str:
    """code span만 변환 (`text` → <code>text</code>)."""
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', text)


def _convert_links(text: str) -> str:
    """link만 변환 ([text](url) → <a href="url">text</a>)."""
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)


def _convert_list_content(text: str) -> str:
    """리스트 블록 → <li><p>...</p></li> 구조의 inner HTML."""
    items = _parse_list_items(text)
    return _render_list_items(items)


def _parse_list_items(content: str) -> List[dict]:
    """리스트 content를 파싱하여 아이템 목록을 반환한다.

    Returns:
        list of dict: {'indent': int, 'ordered': bool, 'content': str}
    """
    lines = content.strip().split('\n')
    items: List[dict] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # figure/img 줄 skip
        if stripped.startswith('<figure') or stripped.startswith('<img') or stripped.startswith('</figure'):
            continue

        # indent level (공백 수 기준)
        indent = len(line) - len(line.lstrip())

        # ordered list: "1. ", "2. ", etc.
        ol_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        # unordered list: "* ", "- ", "+ "
        ul_match = re.match(r'^[-*+]\s+(.*)', stripped)

        if ol_match:
            items.append({
                'indent': indent,
                'ordered': True,
                'content': ol_match.group(2),
            })
        elif ul_match:
            items.append({
                'indent': indent,
                'ordered': False,
                'content': ul_match.group(1),
            })
        else:
            # continuation line — append to last item
            if items:
                items[-1]['content'] += ' ' + stripped

    return items


def _render_list_items(items: List[dict]) -> str:
    """파싱된 리스트 아이템을 <li><p>...</p></li> HTML로 렌더링한다.

    중첩 리스트: indent 기반으로 <li> 안에 <ul>/<ol> 중첩.
    """
    if not items:
        return ''

    result_parts: List[str] = []

    i = 0
    while i < len(items):
        item = items[i]
        inner = _convert_inline(item['content'])

        # 다음 아이템이 더 깊은 indent인지 확인 → 중첩 리스트
        children_start = i + 1
        children_end = children_start
        while children_end < len(items) and items[children_end]['indent'] > item['indent']:
            children_end += 1

        if children_end > children_start:
            # 중첩 리스트가 있는 경우
            child_items = items[children_start:children_end]
            child_html = _render_nested_list(child_items)
            result_parts.append(f'<li><p>{inner}</p>{child_html}</li>')
            i = children_end
        else:
            result_parts.append(f'<li><p>{inner}</p></li>')
            i += 1

    return ''.join(result_parts)


def _render_nested_list(items: List[dict]) -> str:
    """중첩 리스트 아이템을 <ul>/<ol>로 감싸서 렌더링한다."""
    if not items:
        return ''
    ordered = items[0]['ordered']
    tag = 'ol' if ordered else 'ul'
    inner = _render_list_items(items)
    return f'<{tag}>{inner}</{tag}>'
