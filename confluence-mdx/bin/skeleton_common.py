#!/usr/bin/env python3
"""
Skeleton Common Module

This module provides common utility functions used across skeleton processing modules.
It includes functions for path manipulation and language code extraction.
"""

import re
from pathlib import Path
from typing import Optional


def extract_language_code(file_path: Path) -> Optional[str]:
    """
    Extract language code from the file path.
    Assumes a relative path starting with target/{lang}/.
    Checks for 'ko', 'en', 'ja' in the target/{lang}/ pattern.
    Returns language code if found, None otherwise.
    """
    path_str = str(file_path)
    path_lower = path_str.lower()

    # Check for language codes in the target/{lang}/ pattern at the start
    for lang in ['ko', 'en', 'ja']:
        pattern = r'^target[/\\]' + lang + r'[/\\]'
        if re.match(pattern, path_lower, re.IGNORECASE):
            return lang.lower()

    return None


def get_korean_equivalent_path(file_path: Path) -> Optional[Path]:
    """
    Gets the Korean equivalent path by replacing the language code in the path.
    Assumes a relative path starting with target/{lang}/.
    If file_path is target/en/file.mdx, returns target/ko/file.mdx.
    If file_path is target/ja/file.mdx, returns target/ko/file.mdx.
    If no language code found, returns None.
    """
    path_str = str(file_path)
    path_lower = path_str.lower()

    # Try to replace language codes in the target/{lang}/ pattern
    for lang in ['en', 'ja']:
        # Match the target/{lang}/ pattern at the start
        pattern = r'^target[/\\]' + lang + r'[/\\]'
        if re.match(pattern, path_lower, re.IGNORECASE):
            # Replace target/{lang}/ with target/ko/
            new_path_str = re.sub(pattern, 'target/ko/', path_str, flags=re.IGNORECASE, count=1)
            return Path(new_path_str)

    return None


def get_path_without_lang_dir(file_path: Path) -> Optional[str]:
    """
    Extracts a path without the target/{lang} prefix.
    Assumes a relative path starting with target/{lang}/.
    For example: target/en/some/path/file.skel.mdx -> /some/path/file.skel.mdx
    Returns None if target/{lang} pattern is not found.
    """
    path_str = str(file_path)
    path_lower = path_str.lower()

    # Check for the target/{lang}/ pattern at the start (relative path only)
    for lang in ['ko', 'en', 'ja']:
        pattern = r'^target[/\\]' + lang + r'[/\\]'
        match = re.match(pattern, path_lower, re.IGNORECASE)
        if match:
            end = match.end()
            relative_path = path_str[end:]
            # Ensure it starts with /
            if not relative_path.startswith('/'):
                relative_path = '/' + relative_path
            return relative_path

    return None


def get_original_mdx_path(skel_path: Path) -> Optional[Path]:
    """
    Gets the original .mdx file path from the .skel.mdx path.
    For example: target/ko/file.skel.mdx -> target/ko/file.mdx
    """
    if not skel_path.name.endswith('.skel.mdx'):
        return None
    return skel_path.parent / skel_path.name.replace('.skel.mdx', '.mdx')

