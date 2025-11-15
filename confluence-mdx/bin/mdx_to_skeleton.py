#!/usr/bin/env python3
"""
MDX to Skeleton Converter

This script converts MDX files to skeleton format by preserving the markdown structure
and replacing text content with a _TEXT_ placeholder.

Usage:
    python mdx_to_skeleton.py path/to/filename.mdx
    # Creates path/to/filename.skel.mdx
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Import modules for recursive processing and comparison
from skeleton_compare import compare_files
from skeleton_diff import (
    compare_with_korean_skel,
    process_directories_recursive,
    initialize_config,
)


class ProtectedSection:
    """Represents a protected section that should not be modified"""

    def __init__(self, content: str, placeholder: str):
        self.content = content
        self.placeholder = placeholder


def extract_yaml_frontmatter(text: str) -> Tuple[str, Optional[ProtectedSection]]:
    """Extract the YAML frontmatter and replace with a placeholder"""
    pattern = r'^---\n(.*?)\n---\n'
    match = re.match(pattern, text, re.DOTALL)
    if match:
        yaml_content = match.group(1)
        placeholder = "__YAML_FRONTMATTER__"
        protected = ProtectedSection(yaml_content, placeholder)
        modified_text = re.sub(pattern, f"---\n{placeholder}\n---\n", text, count=1, flags=re.DOTALL)
        return modified_text, protected
    return text, None


def extract_code_blocks(text: str) -> Tuple[str, List[ProtectedSection]]:
    """Extracts code blocks and replaces them with placeholders"""
    code_blocks: List[ProtectedSection] = []
    placeholder_counter = 0

    # Pattern to match code blocks: ```language followed by content and closing ```
    # Match the entire code block including markers to preserve it exactly as-is
    pattern = r'(```\w*\n.*?```)'

    def replace_code_block(match):
        nonlocal placeholder_counter
        full_block = match.group(1)  # Entire code block including ``` markers
        placeholder_counter += 1
        placeholder = f"__CODE_BLOCK_{placeholder_counter}__"
        protected = ProtectedSection(full_block, placeholder)
        code_blocks.append(protected)
        return placeholder

    modified_text = re.sub(pattern, replace_code_block, text, flags=re.DOTALL)
    return modified_text, code_blocks


def extract_inline_code(text: str) -> Tuple[str, List[ProtectedSection]]:
    """Extracts inline code and replaces it with placeholders"""
    inline_codes: List[ProtectedSection] = []
    placeholder_counter = 0

    # Pattern to match inline code: `code` (avoid matching code block markers)
    # Match backtick, then non-backtick, non-newline content, then backtick
    pattern = r'(?<!`)`([^`\n]+)`(?!`)'

    def replace_inline_code(match):
        nonlocal placeholder_counter
        code = match.group(1)
        placeholder_counter += 1
        placeholder = f"__INLINE_CODE_{placeholder_counter}__"
        protected = ProtectedSection(code, placeholder)
        inline_codes.append(protected)
        return f"`{placeholder}`"

    modified_text = re.sub(pattern, replace_inline_code, text)
    return modified_text, inline_codes


def extract_urls(text: str) -> Tuple[str, List[ProtectedSection]]:
    """Extracts URLs from links and images and preserves them"""
    urls: List[ProtectedSection] = []
    placeholder_counter = 0

    # Pattern to match URLs in Markdown links and images
    # Match [text](url) or ![alt](url)
    # For images, we preserve the URL but will process alt text later
    pattern = r'(!?\[[^\]]*\]\()([^)]+)(\))'

    def replace_url(match):
        nonlocal placeholder_counter
        prefix = match.group(1)  # [text]( or ![alt](
        url = match.group(2)
        suffix = match.group(3)  # )
        # For image links with path-like URLs, preserve the URL as-is
        # We'll process the alt text separately
        is_image = prefix.startswith('!')
        is_path_url = url.startswith('/') or '://' in url or url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'))

        if is_image and is_path_url:
            # For images with path URLs, keep the URL as-is, alt text will be processed later
            return match.group(0)
        elif is_path_url:
            # For regular links with path URLs, preserve the URL
            placeholder_counter += 1
            placeholder = f"__URL_{placeholder_counter}__"
            protected = ProtectedSection(url, placeholder)
            urls.append(protected)
            return prefix + placeholder + suffix
        return match.group(0)  # Keep as is if not a URL

    modified_text = re.sub(pattern, replace_url, text)
    return modified_text, urls


def extract_html_entities(text: str) -> Tuple[str, List[ProtectedSection]]:
    """Extracts HTML entities and preserves them"""
    entities: List[ProtectedSection] = []
    placeholder_counter = 0

    # Pattern to match HTML entities like &gt;, &lt;, &amp;, etc.
    pattern = r'(&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;)'

    def replace_entity(match):
        nonlocal placeholder_counter
        entity = match.group(1)
        placeholder_counter += 1
        placeholder = f"__HTML_ENTITY_{placeholder_counter}__"
        protected = ProtectedSection(entity, placeholder)
        entities.append(protected)
        return placeholder

    modified_text = re.sub(pattern, replace_entity, text)
    return modified_text, entities


def restore_protected_sections(text: str, sections: List[ProtectedSection]) -> str:
    """Restores protected sections from placeholders"""
    for section in sections:
        text = text.replace(section.placeholder, section.content)
    return text


def process_text_line(line: str) -> str:
    """
    Processes a line of text, replacing content with _TEXT_ while preserving structure.
    """
    # Skip empty lines
    if not line.strip():
        return line

    # Preserve import statements
    if line.strip().startswith('import '):
        return line

    # Preserve code block markers and placeholders
    # Code blocks are already extracted and replaced with placeholders
    # We need to preserve the entire code block structure (```...```)
    if line.strip().startswith('```') or line.strip() == '```':
        return line
    if '__CODE_BLOCK_' in line:
        return line

    # Preserve HTML tags structure but replace text content
    if '<' in line and '>' in line:
        # Extract HTML tags and their attributes, replace text between tags
        result = []
        i = 0
        while i < len(line):
            if line[i] == '<':
                # Find the closing >
                tag_end = line.find('>', i)
                if tag_end == -1:
                    result.append(line[i:])
                    break
                # Extract the tag
                tag = line[i:tag_end + 1]
                result.append(tag)
                i = tag_end + 1
            else:
                # Find the next < or end of line
                text_end = line.find('<', i)
                if text_end == -1:
                    text_end = len(line)
                text = line[i:text_end]
                # Replace text content but preserve structure
                processed_text = replace_text_in_content(text)
                result.append(processed_text)
                i = text_end
        return ''.join(result)

    # Process markdown line
    return process_markdown_line(line)


def process_markdown_line(line: str) -> str:
    """Processes a markdown line, preserving structure"""
    # Preserve headers
    header_match = re.match(r'^(\s*#+\s+)(.*)$', line)
    if header_match:
        prefix = header_match.group(1)
        content = header_match.group(2)
        processed_content = replace_text_in_content(content)
        return prefix + processed_content

    # Preserve list items
    list_match = re.match(r'^(\s*)([-*]|\d+\.)(\s+)(.*)$', line)
    if list_match:
        indent = list_match.group(1)
        marker = list_match.group(2)
        spacing = list_match.group(3)
        content = list_match.group(4)
        processed_content = replace_text_in_content(content)
        return indent + marker + spacing + processed_content

    # Process as regular text
    return replace_text_in_content(line)


def is_sentence_ending_punctuation(text: str) -> bool:
    """
    Check if text is a sentence-ending punctuation mark (optionally with trailing whitespace).
    
    Args:
        text: Text to check
        
    Returns:
        True if text matches sentence-ending punctuation pattern
    """
    return bool(re.match(r'^[.!?。！？]\s*$', text))


def contains_text_characters(text: str) -> bool:
    """
    Check if text contains any text characters (Korean, Japanese, English, numbers).
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains any text characters
    """
    return bool(re.search(r'[가-힣\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAFa-zA-Z0-9]', text))


def extract_leading_whitespace(text: str) -> str:
    """
    Extract leading whitespace from text.
    
    Args:
        text: Text to extract whitespace from
        
    Returns:
        Leading whitespace string, empty string if none
    """
    match = re.match(r'^(\s*)', text)
    return match.group(1) if match else ''


def is_abbreviation_period(text: str, period_pos: int) -> bool:
    """Check if period is part of common abbreviations: e.g., etc., i.e., 7.0.5, .NET"""
    if period_pos < 0:
        return False
    before = text[max(0, period_pos - 4):period_pos].lower()
    # Check common abbreviations
    if before.endswith(('e.g', 'etc', 'i.e')):
        return True
    # Check special cases like ".NET" where period is at start or after space
    # Pattern: period followed by uppercase letter (e.g., ".NET", ".NET Core")
    if period_pos + 1 < len(text) and text[period_pos + 1].isupper():
        # Check if period is at start of text or after space (likely an abbreviation)
        if period_pos == 0 or (period_pos > 0 and text[period_pos - 1].isspace()):
            # Check if it's part of ".NET" or similar known abbreviations
            if period_pos + 3 < len(text):
                after_period = text[period_pos + 1:period_pos + 4].upper()
                if after_period == "NET":
                    return True
            # More general: if period is followed by uppercase and then another period, space, or lowercase,
            # it's likely an abbreviation (e.g., ".NET", ".NET Core")
            if period_pos + 2 < len(text):
                next_char = text[period_pos + 2]
                if next_char.isupper() or next_char == '.' or next_char.islower():
                    return True
    # Check version numbers (e.g., 7.0.5, 1.2.3, 9.14.0, 10.2.5)
    # A period is part of a version number if:
    # - It's between digits (e.g., "9.14" or "10.2")
    # - It's part of a multi-part version (e.g., "9.14.0" or "10.2.5")
    if period_pos >= 1 and period_pos < len(text):
        # Check if before period is a digit
        if text[period_pos - 1].isdigit():
            # Check if after period is also a digit (version number pattern)
            if period_pos + 1 < len(text) and text[period_pos + 1].isdigit():
                return True
            # Also check if it's followed by another period and digit (e.g., "9.14.0")
            if period_pos + 2 < len(text) and text[period_pos + 2] == '.':
                if period_pos + 3 < len(text) and text[period_pos + 3].isdigit():
                    return True
    return False


def process_punctuation_with_space(
    punctuation_with_space: str,
    is_last_punctuation: bool
) -> str:
    """
    Process punctuation with trailing space, removing space if this is the last punctuation.
    
    Args:
        punctuation_with_space: Punctuation mark with trailing space (e.g., '. ')
        is_last_punctuation: True if this is the last punctuation in the text
        
    Returns:
        Processed punctuation (with or without trailing space)
    """
    # Extract punctuation and trailing space separately
    punctuation_match = re.match(r'^([.!?。！？])(\s*)$', punctuation_with_space)
    if punctuation_match:
        punctuation_char = punctuation_match.group(1)
        trailing_space = punctuation_match.group(2)
        # Remove trailing space only if this is the last punctuation
        if is_last_punctuation:
            return punctuation_char
        else:
            return punctuation_char + trailing_space
    else:
        return punctuation_with_space


def replace_text_in_content(text: str) -> str:
    """
    Replaces text content with _TEXT_ while preserving Markdown formatting markers.
    Processes sentences: one sentence becomes _TEXT_. (comma is included in _TEXT_)
    
    Args:
        text: Text content to process
    """
    if not text.strip():
        return text

    # First, protect image links: replace alt text with _TEXT_ but preserve the URL
    # Pattern: ![alt text](url) where the url is a path
    # We need to protect these so they don't get processed again
    image_links = []
    placeholder_counter = 0

    def protect_image_link(match):
        nonlocal placeholder_counter
        _alt_text = match.group(1)  # alt_text is extracted but not used
        url = match.group(2)
        # If the URL is a path (starts with / or is an image file), preserve it
        if url.startswith('/') or '://' in url or url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
            placeholder_counter += 1
            link_placeholder = f"__IMAGE_LINK_{placeholder_counter}__"
            image_links.append((link_placeholder, f'![_TEXT_]({url})'))
            return link_placeholder
        return match.group(0)

    # Match image links: ![alt](url) and protect them
    text = re.sub(r'!\[([^]]*)]\(([^)]+)\)', protect_image_link, text)

    # Check if text is only image link placeholders (no other text)
    if image_links and re.match(r'^\s*(__IMAGE_LINK_\d+__\s*)+$', text):
        # Restore image links immediately and return
        result = text
        for placeholder, replacement in image_links:
            result = result.replace(placeholder, replacement)
        return result

    # Preserve bold markers **text** or __text__
    text = re.sub(r'\*\*([^*]+)\*\*', r'**_TEXT_**', text)
    text = re.sub(r'__([^_]+)__', r'__TEXT__', text)

    # Preserve italic markers *text* or _text_ (but not if part of ** or __)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'*_TEXT_*', text)
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'_TEXT_', text)

    # Preserve regular link structure [text] (but not images, already handled)
    text = re.sub(r'(?<!!)\[([^]]*)]', r'[_TEXT_]', text)

    # Process sentences: replace each sentence with _TEXT_.
    # A sentence ends with . ! ? or end of text
    # Splits text into sentences while preserving structure
    # Finds all text segments and replaces them sentence by sentence

    # Split by sentence boundaries (. ! ?) but keep them
    # Pattern to match sentences: text ending with . ! ? or end of string
    def process_sentences(content):
        # First, check if content is only a placeholder (image link only)
        if re.match(r'^\s*__IMAGE_LINK_\d+__\s*$', content):
            return content

        # Split content by protected placeholders to preserve them
        placeholder_pattern = r'(__IMAGE_LINK_\d+__)'
        segments = re.split(placeholder_pattern, content)
        sentence_result = []

        for segment in segments:
            if re.match(placeholder_pattern, segment):
                # This is a protected placeholder, keep it as-is
                sentence_result.append(segment)
            else:
                # Protect abbreviation periods (e.g., etc., i.e.) before sentence splitting
                protected_segment = segment
                placeholders = []
                for match in reversed(list(re.finditer(r'\.', segment))):
                    if is_abbreviation_period(segment, match.start()):
                        placeholder = f"__ABBR_{len(placeholders)}__"
                        placeholders.append(placeholder)
                        protected_segment = protected_segment[:match.start()] + placeholder + protected_segment[match.start() + 1:]
                
                # Split by sentence boundaries
                parts = re.split(r'([.!?。！？]\s*)', protected_segment)
                
                # Collect text sentences and track punctuation
                has_text = False
                leading_ws = ''
                last_punctuation = ''
                trailing_ws = ''
                non_text_parts = []
                
                i = 0
                while i < len(parts):
                    part = parts[i]
                    punctuation = ''
                    
                    if i + 1 < len(parts) and is_sentence_ending_punctuation(parts[i + 1]):
                        punctuation_with_space = parts[i + 1]
                        for placeholder in placeholders:
                            punctuation_with_space = punctuation_with_space.replace(placeholder, '.')
                        is_last_punctuation = not any(parts[j].strip() and contains_text_characters(parts[j]) for j in range(i + 2, len(parts)))
                        punctuation = process_punctuation_with_space(punctuation_with_space, is_last_punctuation)
                        i += 2
                    else:
                        i += 1
                    
                    # Restore abbreviation periods
                    for placeholder in placeholders:
                        part = part.replace(placeholder, '.')
                    
                    # Check if part contains any text
                    if contains_text_characters(part):
                        has_text = True
                        if not leading_ws:
                            leading_ws = extract_leading_whitespace(part)
                        if punctuation:
                            # Normalize full-width Japanese punctuation to half-width
                            normalized_punctuation = punctuation.replace('。', '.').replace('！', '!').replace('？', '?')
                            last_punctuation = normalized_punctuation
                            # Extract trailing whitespace from punctuation
                            if is_last_punctuation:
                                # Check if there's trailing whitespace after last punctuation
                                trailing_match = re.search(r'([.!?]\s*)$', protected_segment)
                                if trailing_match:
                                    trailing_ws = trailing_match.group(1)[1:]  # Skip punctuation, get whitespace
                    else:
                        # Non-text content - preserve only if no text found yet
                        if not has_text:
                            non_text_parts.append(part)
                            if punctuation:
                                non_text_parts.append(punctuation)
                
                # If we found text, replace all text sentences with single _TEXT_
                if has_text:
                    # Add leading whitespace and non-text parts before first text
                    sentence_result.extend(non_text_parts)
                    if last_punctuation:
                        sentence_result.append(leading_ws + '_TEXT_' + last_punctuation + trailing_ws)
                    else:
                        # Check if segment ended with punctuation
                        if protected_segment.rstrip().endswith(('.', '!', '?', '。', '！', '？')):
                            # Extract trailing whitespace
                            trailing_match = re.search(r'([.!?。！？]\s*)$', protected_segment)
                            if trailing_match:
                                trailing_ws = trailing_match.group(1)[1:]  # Skip punctuation, get whitespace
                            sentence_result.append(leading_ws + '_TEXT_.' + trailing_ws)
                        else:
                            sentence_result.append(leading_ws + '_TEXT_')
                else:
                    # No text found, preserve original segment
                    sentence_result.append(segment)

        return ''.join(sentence_result)

    result = process_sentences(text)

    # Final cleanup: merge consecutive _TEXT_ and handle spacing
    result = re.sub(r'_TEXT_\s*_TEXT_', '_TEXT_', result)
    result = re.sub(r'_TEXT_\s*([.,;:!?])', r'_TEXT_\1', result)
    result = re.sub(r'([.,;:!?])\s*_TEXT_', r'\1 _TEXT_', result)

    # Restore protected image links
    for image_placeholder, replacement in image_links:
        result = result.replace(image_placeholder, replacement)

    return result


def process_yaml_frontmatter_placeholder(
    line: str,
    yaml_section: Optional[ProtectedSection],
    processed_lines: List[str]
) -> Tuple[bool, bool]:
    """
    Process YAML frontmatter placeholder line.
    
    Args:
        line: Current line being processed
        yaml_section: YAML frontmatter section if extracted
        processed_lines: List to append processed lines to
        
    Returns:
        Tuple of (should_continue, yaml_frontmatter_processed)
        should_continue: True if processing should continue to next line
        yaml_frontmatter_processed: True if YAML frontmatter was processed
    """
    if yaml_section and yaml_section.placeholder in line:
        # Process YAML frontmatter: preserve structure but replace content
        yaml_lines = yaml_section.content.split('\n')
        for yaml_line in yaml_lines:
            if ':' in yaml_line:
                # Preserve key: structure, replace value
                parts = yaml_line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    # Replace value with _TEXT_ but preserve quotes if present
                    if value.startswith("'") and value.endswith("'"):
                        processed_lines.append(f"{key}: '_TEXT_'")
                    elif value.startswith('"') and value.endswith('"'):
                        processed_lines.append(f'{key}: "_TEXT_"')
                    else:
                        processed_lines.append(f"{key}: _TEXT_")
                else:
                    processed_lines.append(yaml_line)
            else:
                processed_lines.append(yaml_line)
        return True, True  # should_continue=True, yaml_frontmatter_processed=True
    return False, False  # should_continue=False, yaml_frontmatter_processed=False


def process_yaml_delimiter(
    line: str,
    yaml_frontmatter_processed: bool,
    processed_lines: List[str],
    in_yaml: bool
) -> Tuple[bool, bool]:
    """
    Process YAML frontmatter delimiter (---).
    
    Args:
        line: Current line being processed
        yaml_frontmatter_processed: Whether YAML frontmatter has been processed
        processed_lines: List to append processed lines to
        in_yaml: Current YAML section state
        
    Returns:
        Tuple of (should_continue, new_in_yaml)
        should_continue: True if processing should continue to next line
        new_in_yaml: Updated YAML section state
    """
    # Handle YAML frontmatter delimiter (only if YAML frontmatter hasn't been processed yet)
    # After YAML frontmatter is processed, treat --- as regular markdown
    if line.strip() == '---' and not yaml_frontmatter_processed:
        processed_lines.append(line)
        return True, not in_yaml  # should_continue=True, toggle in_yaml
    return False, in_yaml  # should_continue=False, in_yaml unchanged


def process_yaml_line(
    line: str,
    in_yaml: bool,
    yaml_frontmatter_processed: bool,
    processed_lines: List[str]
) -> bool:
    """
    Process a line within YAML section.
    
    Args:
        line: Current line being processed
        in_yaml: Whether currently in YAML section
        yaml_frontmatter_processed: Whether YAML frontmatter has been processed
        processed_lines: List to append processed lines to
        
    Returns:
        True if line was processed as YAML, False otherwise
    """
    if in_yaml and not yaml_frontmatter_processed:
        # Process YAML line: preserve key: structure, replace value
        # (This handles YAML frontmatter that wasn't extracted by extract_yaml_frontmatter)
        # Only process if YAML frontmatter hasn't been processed yet
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                # Replace value with _TEXT_ but preserve quotes if present
                if value.startswith("'") and value.endswith("'"):
                    processed_lines.append(f"{key}: '_TEXT_'")
                elif value.startswith('"') and value.endswith('"'):
                    processed_lines.append(f'{key}: "_TEXT_"')
                else:
                    processed_lines.append(f"{key}: _TEXT_")
            else:
                processed_lines.append(line)
        else:
            processed_lines.append(line)
        return True
    return False


def convert_mdx_to_skeleton(input_path: Path) -> Tuple[Path, Optional[str]]:
    """
    Converts an MDX file to skeleton format.
    Returns tuple of (output_path, comparison_result).
    comparison_result: 'matched' if skeleton diff matched, 'unmatched' if different, None if not compared
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix != '.mdx':
        raise ValueError(f"Input file must have .mdx extension: {input_path}")

    # Skip .skel.mdx files to avoid infinite recursion
    if input_path.name.endswith('.skel.mdx'):
        raise ValueError(f"Skipping .skel.mdx file to avoid recursion: {input_path}")

    # Read input file
    content = input_path.read_text(encoding='utf-8')

    # Step 1: Extract and protect YAML frontmatter
    content, yaml_section = extract_yaml_frontmatter(content)

    # Step 2: Extract and protect code blocks
    content, code_blocks = extract_code_blocks(content)

    # Step 3: Extract and protect inline code
    content, inline_codes = extract_inline_code(content)

    # Step 4: Extract and protect URLs
    content, urls = extract_urls(content)

    # Step 5: Extract and protect HTML entities
    content, entities = extract_html_entities(content)

    # Step 6: Process lines and replace text content
    lines = content.split('\n')
    processed_lines = []
    in_yaml = False
    yaml_frontmatter_processed = False  # Track if YAML frontmatter has been processed

    for line in lines:
        # Handle YAML frontmatter placeholder
        should_continue, was_processed = process_yaml_frontmatter_placeholder(
            line, yaml_section, processed_lines
        )
        if should_continue:
            yaml_frontmatter_processed = was_processed
            if was_processed:
                in_yaml = False  # Reset in_yaml since YAML frontmatter is now processed
            continue

        # Handle YAML frontmatter delimiter
        should_continue, new_in_yaml = process_yaml_delimiter(
            line, yaml_frontmatter_processed, processed_lines, in_yaml
        )
        if should_continue:
            in_yaml = new_in_yaml
            continue

        # Handle YAML section lines
        if process_yaml_line(line, in_yaml, yaml_frontmatter_processed, processed_lines):
            continue

        # Process other lines
        processed_line = process_text_line(line)
        processed_lines.append(processed_line)

    content = '\n'.join(processed_lines)

    # Step 7: Restore all protected sections in reverse order
    # Note: YAML frontmatter is already processed, so we don't restore it
    content = restore_protected_sections(content, entities)
    content = restore_protected_sections(content, urls)
    content = restore_protected_sections(content, inline_codes)
    content = restore_protected_sections(content, code_blocks)

    # Generate output path
    output_path = input_path.parent / f"{input_path.stem}.skel.mdx"

    # Write output file
    output_path.write_text(content, encoding='utf-8')

    # Compare with Korean equivalent if current file is not Korean
    _, comparison_result = compare_with_korean_skel(output_path)

    return output_path, comparison_result


def main():
    parser = argparse.ArgumentParser(
        description='Convert MDX file(s) to skeleton format by replacing text with _TEXT_'
    )
    parser.add_argument(
        'input_path',
        type=Path,
        nargs='?',
        help='Path to input MDX file or directory (if -r is specified)'
    )
    parser.add_argument(
        '-r', '--recursive',
        nargs='*',
        type=Path,
        metavar='DIR',
        help='Process directory(ies) recursively. If no directories specified, defaults to target/ko, target/ja, target/en'
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare .mdx files across target/en, target/ja, and target/ko directories'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='When used with --compare, output all files including those that exist in all three languages'
    )
    parser.add_argument(
        '--max-diff',
        type=int,
        default=5,
        metavar='N',
        help='Maximum number of diffs to output before stopping (default: 5). Only applies with --recursive option.'
    )
    parser.add_argument(
        '--exclude',
        type=str,
        nargs='*',
        default=['/index.skel.mdx'],
        metavar='PATH',
        help='Exclude paths from diff comparison. Path should be relative to target/{lang} (e.g., /index.skel.mdx). Can specify multiple paths. Default: /index.skel.mdx'
    )

    args = parser.parse_args()

    # Initialize config if recursive mode is used
    if args.recursive is not None:
        exclude_patterns = args.exclude if args.exclude and len(args.exclude) > 0 else ['/index.skel.mdx']
        initialize_config(args.max_diff, exclude_patterns)

    try:
        if args.compare:
            # Compare mode
            compare_files(verbose=args.verbose)
            return 0
        elif args.recursive is not None:
            # Recursive mode: process directories
            return process_directories_recursive(args.recursive, convert_mdx_to_skeleton)
        elif args.input_path:
            # Single file mode
            if args.input_path.is_dir():
                print("Error: Input path is a directory. Use -r option for directory processing.", file=sys.stderr)
                return 1

            output_path, _ = convert_mdx_to_skeleton(args.input_path)
            print(f"Successfully created: {output_path}")
            return 0
        else:
            # No arguments provided
            parser.print_help()
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
