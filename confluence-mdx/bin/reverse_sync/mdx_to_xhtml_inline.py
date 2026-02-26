"""MDX block content → XHTML inner HTML 변환 모듈.

MDX 블록의 content를 파싱하여 대상 XHTML 요소의 innerHTML로
직접 교체할 수 있는 HTML 문자열을 생성한다.
"""
import re
from typing import List

from bs4 import BeautifulSoup, Tag
from mdx_to_storage.inline import convert_inline


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
    elif block_type == 'callout':
        return _convert_callout_inner(text)
    elif block_type == 'list':
        return _convert_list_content(text)
    elif block_type == 'code_block':
        return _convert_code_block(text)
    elif block_type == 'html_block':
        return _convert_html_block_inner(text)
    else:
        return convert_inline(text)


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
        converted.append(convert_inline(line))
    return ' '.join(converted)


def _convert_callout_inner(text: str) -> str:
    """callout: <Callout> 래퍼 태그를 제거하고 내부 텍스트를 paragraph로 변환."""
    lines = text.splitlines()
    if lines and lines[0].strip().startswith('<Callout'):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith('</Callout'):
        lines = lines[:-1]
    inner = '\n'.join(lines).strip()
    return _convert_paragraph(inner)


def _convert_code_block(text: str) -> str:
    """code_block: 펜스 마커 제거, 코드 내용만 추출."""
    lines = text.split('\n')
    # 첫 줄(```)과 마지막 줄(```) 제거
    if lines and lines[0].strip().startswith('```'):
        lines = lines[1:]
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]
    return '\n'.join(lines)


def _convert_html_block_inner(text: str) -> str:
    """html_block: inline 변환 후 루트 요소의 innerHTML만 반환한다.

    html_block content는 ``<table>...**bold**...</table>`` 처럼
    outer 태그를 포함하므로, inline 변환 후 루트 요소를 벗겨내야
    _replace_inner_html()에서 중첩이 발생하지 않는다.
    """
    converted = convert_inline(text)
    soup = BeautifulSoup(converted, 'html.parser')
    root = soup.find(True)  # 첫 번째 태그 요소
    if isinstance(root, Tag):
        return root.decode_contents()
    return converted


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
        inner = convert_inline(item['content'])

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
    inner = _render_list_items(items)
    if ordered:
        return f'<ol start="1">{inner}</ol>'
    return f'<ul>{inner}</ul>'


def mdx_block_to_xhtml_element(block) -> str:
    """MDX 블록을 완전한 Confluence XHTML 요소(outer tag 포함)로 변환한다."""
    inner = mdx_block_to_inner_xhtml(block.content, block.type)

    if block.type == 'heading':
        level = _detect_heading_level(block.content)
        return f'<h{level}>{inner}</h{level}>'

    elif block.type == 'paragraph':
        return f'<p>{inner}</p>'

    elif block.type == 'list':
        tag = _detect_list_tag(block.content)
        return f'<{tag}>{inner}</{tag}>'

    elif block.type == 'code_block':
        lang = _extract_code_language(block.content)
        code = inner
        parts = ['<ac:structured-macro ac:name="code">']
        if lang:
            parts.append(
                f'<ac:parameter ac:name="language">{lang}</ac:parameter>')
        parts.append(
            f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>')
        parts.append('</ac:structured-macro>')
        return ''.join(parts)

    elif block.type == 'html_block':
        return block.content.strip()

    else:
        return f'<p>{inner}</p>'


def _detect_heading_level(content: str) -> int:
    """heading content에서 레벨(1-6)을 추출한다."""
    stripped = content.strip()
    level = 0
    for ch in stripped:
        if ch == '#':
            level += 1
        else:
            break
    return max(1, min(level, 6))


def _detect_list_tag(content: str) -> str:
    """list content의 첫 번째 마커로 ul/ol을 결정한다."""
    for line in content.strip().split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^\d+\.\s', stripped):
            return 'ol'
        if re.match(r'^[-*+]\s', stripped):
            return 'ul'
    return 'ul'


def _extract_code_language(content: str) -> str:
    """code fence 첫 줄에서 언어를 추출한다."""
    first_line = content.strip().split('\n')[0].strip()
    if first_line.startswith('```'):
        lang = first_line[3:].strip()
        return lang
    return ''
