#!/usr/bin/env python3
"""
Text Utility Functions

Common text processing utilities shared across confluence-mdx scripts.
"""

import html as html_module
import re
import unicodedata
from typing import Optional


# Hidden characters for text cleaning
HIDDEN_CHARACTERS = {
    '\u00A0': ' ',  # Non-Breaking Space
    '\u202f': ' ',  # Narrow No-Break Space
    '\u200b': '',   # Zero Width Space
    '\u200e': '',   # Left-to-Right Mark
    '\u3164': ''    # Hangul Filler
}


def clean_text(text: Optional[str]) -> Optional[str]:
    """
    Clean text by removing hidden characters.

    Args:
        text: The text to clean

    Returns:
        Cleaned text with hidden characters removed/replaced, or None if input is None
    """
    if text is None:
        return None

    # Apply unicodedata.normalize to prevent unmatched string comparison.
    # Use Normalization Form Canonical Composition for the unicode normalization.
    cleaned_text = unicodedata.normalize('NFC', text)
    for hidden_char, replacement in HIDDEN_CHARACTERS.items():
        cleaned_text = cleaned_text.replace(hidden_char, replacement)
    return cleaned_text


def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug format.
    Replace spaces with hyphens and remove special characters.

    Special handling for version numbers:
    - Single version (e.g., "11.5.0") → "11.5.0" (preserve dots)
    - Version range (e.g., "11.1.0 ~ 11.1.2") → "11.1.0-11.1.2"

    Args:
        text: The text to convert to a slug

    Returns:
        A URL-friendly slug string
    """
    # First, clean hidden characters (non-breaking spaces, etc.)
    text = clean_text(text) or ''

    # Check for version number pattern (e.g., "11.5.0" or "11.1.0 ~ 11.1.2")
    version_pattern = r'^\d+\.\d+\.\d+(\s*[~\-]\s*\d+\.\d+\.\d+)?$'
    if re.match(version_pattern, text.strip()):
        # For version numbers, preserve dots and convert range separator to hyphen
        result = re.sub(r'\s*[~\-]\s*', '-', text.strip())
        return result

    # Standard slugify for non-version text
    # Convert to lowercase
    text = text.lower()
    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)
    # Remove special characters
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading and trailing hyphens
    text = text.strip('-')
    return text


EMOJI_RE = re.compile(
    r'[\U0001F000-\U0001F9FF\u2700-\u27BF\uFE00-\uFE0F\u200D]+'
)
# 비교 시 제거할 공백·불가시 문자 패턴
# - \s: 일반 공백/탭/줄바꿈
# - \u200B~\uFEFF: zero-width space, zero-width (non-)joiner, word joiner, BOM
# - \u00AD: soft hyphen
# - \u3164, \u115F, \u1160: Hangul Filler 류
# - \u3000: ideographic space
# - \xa0: non-breaking space
_INVISIBLE_AND_WS_RE = re.compile(
    r'[\s\u200b\u200c\u200d\u2060\ufeff\u00ad\u3164\u115f\u1160\u3000\xa0]+'
)


def strip_for_compare(text: str) -> str:
    """비교를 위해 공백 및 불가시 유니코드 문자를 모두 제거한다."""
    return _INVISIBLE_AND_WS_RE.sub('', text)


def normalize_mdx_to_plain(content: str, block_type: str) -> str:
    """MDX 블록 content를 XHTML plain text와 대응하는 형태로 변환한다."""
    text = content.strip()

    if block_type == 'heading':
        s = text.lstrip('#').strip()
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'`([^`]+)`', r'\1', s)
        s = re.sub(
            r'<Badge\s+color="([^"]+)">(.*?)</Badge>',
            lambda m: m.group(2) + m.group(1).capitalize(),
            s,
        )
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
        # 코드 펜스 마커 건너뛰기 (```, ```yaml 등)
        if s.startswith('```'):
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
        # Badge 컴포넌트 → XHTML status macro 형식으로 변환
        # (XHTML get_text()는 title + colour를 이어서 반환)
        s = re.sub(
            r'<Badge\s+color="([^"]+)">(.*?)</Badge>',
            lambda m: m.group(2) + m.group(1).capitalize(),
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
