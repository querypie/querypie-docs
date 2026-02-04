#!/usr/bin/env python3
"""
Text Utility Functions

Common text processing utilities shared across confluence-mdx scripts.
"""

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
