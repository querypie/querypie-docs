#!/usr/bin/env python3
"""
MDX to Skeleton Converter

This script converts MDX files to skeleton format by preserving the markdown structure
and replacing text content with a _TEXT_ placeholder.

Usage:
    bin/skeleton/cli.py path/to/filename.mdx
    # Creates path/to/filename.skel.mdx

Features Preserved:
    The following features are preserved during conversion:

    1. YAML Frontmatter
       - YAML frontmatter structure is preserved
       - Text values are replaced with _TEXT_ placeholder

    2. Code Blocks
       - Code blocks (```...```) are fully preserved as-is
       - Inline code (`...`) text content is replaced with _TEXT_ placeholder (not preserved as-is)

    3. URLs and Links
       - URLs in links and images are preserved
       - Link text is replaced with _TEXT_ placeholder
       - Image alt text is replaced with _TEXT_ placeholder

    4. HTML Entities
       - HTML entities (&amp;, &lt;, etc.) are preserved as-is

    5. Markdown Formatting
       - Bold (**text** or __text__) structure preserved: **_TEXT_**
       - Italic (*text* or _text_) structure preserved: *_TEXT_*
       - Link structure preserved: [_TEXT_](url)

    6. Document Structure
       - Headers (#, ##, ###, etc.) structure preserved
       - Lists (ordered and unordered) structure preserved
       - HTML tags structure preserved

    7. Image Links
       - Image markdown syntax preserved: ![_TEXT_](url)
       - Image URLs are preserved

Text Replacement Behavior:
    - All text content (Korean, Japanese, Chinese, English, numbers) is replaced with _TEXT_
    - Multiple sentences in a line are replaced with a single _TEXT_ placeholder
    - Punctuation marks (periods, exclamation marks, question marks, colons, semicolons, commas) are NOT preserved
    - Colon (:) in general text is treated as regular punctuation and removed (not a markdown syntax element)
    - Consecutive _TEXT_ placeholders are merged into a single _TEXT_

Whitespace Preservation Rules:
    - Leading whitespace (indentation) at the beginning of each line MUST be preserved
    - This includes spaces and tabs used for list indentation, code blocks, and nested structures
    - The skeleton conversion should maintain the exact same indentation structure as the original MDX
    - Only text content is replaced with _TEXT_; all structural whitespace remains unchanged
Whitespace Normalization Rules:
    To ensure consistent spacing across different language versions, the following normalization
    is applied during skeleton conversion:
    
    1. Inline Code
       - Pattern: `code` followed by non-whitespace text
       - Normalization: `code`_TEXT_ → `code` _TEXT_
       - Example: `` `On`입니다 `` → `` `On` _TEXT_ ``
    
    2. Links
       - Pattern: ](url) followed by non-whitespace text
       - Normalization: ](url)_TEXT_ → ](url) _TEXT_
       - Example: `[DB Connections](url)内` → `[_TEXT_](url) _TEXT_`
    
    3. HTML Tags
       - Pattern: <br/> or /> followed by non-whitespace text
       - Normalization: <br/>_TEXT_ → <br/> _TEXT_
       - Example: `<br/>미리` → `<br/> _TEXT_`
    
    4. Markdown Formatting (Bold/Italic)
       - Pattern: **_TEXT_** or *_TEXT_* followed by non-whitespace text
       - Normalization: **_TEXT_**_TEXT_ → **_TEXT_** _TEXT_
       - Example: `**Setting**文書` → `**_TEXT_** _TEXT_`
    
    Note: This normalization ensures that skeleton files from different languages have
    consistent spacing, making diff comparisons more reliable when using diff -b option.

"""

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

# Resolve project root (confluence-mdx/) from this script's location
_SCRIPT_DIR = Path(__file__).resolve().parent.parent  # confluence-mdx/bin/
_PROJECT_DIR = _SCRIPT_DIR.parent                     # confluence-mdx/

# Ensure bin/ is on sys.path so skeleton package imports resolve without PYTHONPATH
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Import modules for recursive processing and comparison
from skeleton.compare import compare_files
from skeleton.diff import (
    compare_with_korean_skel,
    process_directories_recursive,
    initialize_config,
    should_exclude_file,
)
from skeleton.common import (
    extract_language_code,
    get_korean_equivalent_path,
)

# Set up logger
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProtectedSection:
    """Represents a protected section that should not be modified"""
    content: str
    placeholder: str


def _is_path_url(url: str) -> bool:
    """Check if URL is a path or absolute URL"""
    return (url.startswith('/') or 
            url.startswith('../') or
            url.startswith('./') or
            '://' in url or 
            url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.md', '.mdx')))


class ContentProtector:
    """
    Manages extraction and restoration of protected content sections.
    
    This class protects the following content types from being modified:
    - YAML frontmatter
    - Import statements (import ... from '...')
    - Code blocks (```...```)
    - URLs in links and images
    - HTML entities (&amp;, &lt;, etc.)
    
    Note: Inline code (`...`) is NOT protected - its text content is converted to _TEXT_
    
    Protected sections are temporarily replaced with placeholders during text processing
    and restored at the end of the conversion process.
    """

    def __init__(self):
        self.protected_sections: List[ProtectedSection] = []
        self.placeholder_counter = 0

    def _create_placeholder(self, prefix: str) -> str:
        """Create a unique placeholder with given prefix"""
        self.placeholder_counter += 1
        return f"__{prefix}_{self.placeholder_counter}__"

    def extract_yaml_frontmatter(self, text: str) -> Tuple[str, Optional[ProtectedSection]]:
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

    def extract_import_statements(self, text: str) -> str:
        """
        Extracts import statements (single-line and multi-line) and replaces them with placeholders.
        
        Handles patterns like:
        - import DefaultExport from 'module';
        - import { ... } from 'module';
        - import * as name from 'module';
        - Multi-line imports with braces
        """
        lines = text.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if this line starts with 'import'
            if line.strip().startswith('import'):
                # Collect all lines until we find the complete import statement
                import_lines = [line]
                j = i + 1
                
                # Check if this is a single-line import
                if re.search(r'from\s+["\'][^"\']+["\']', line):
                    # Single-line import - already complete
                    j = i + 1
                else:
                    # Multi-line import - collect lines until we find 'from ...'
                    while j < len(lines):
                        next_line = lines[j]
                        import_lines.append(next_line)
                        if re.search(r'from\s+["\'][^"\']+["\']', next_line):
                            j += 1
                            break
                        j += 1
                
                # Join the import lines
                import_statement = '\n'.join(import_lines)
                
                # Create placeholder and protect
                placeholder = self._create_placeholder("IMPORT")
                protected = ProtectedSection(import_statement, placeholder)
                self.protected_sections.append(protected)
                
                result_lines.append(placeholder)
                i = j
            else:
                result_lines.append(line)
                i += 1
        
        return '\n'.join(result_lines)

    def extract_code_blocks(self, text: str) -> str:
        """Extracts code blocks and replaces them with placeholders"""
        pattern = r'(```\w*\n.*?```)'

        def replace_code_block(match):
            full_block = match.group(1)
            placeholder = self._create_placeholder("CODE_BLOCK")
            protected = ProtectedSection(full_block, placeholder)
            self.protected_sections.append(protected)
            return placeholder

        return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)

    def extract_inline_code(self, text: str) -> str:
        """Extracts inline code and replaces it with placeholders"""
        pattern = r'(?<!`)`([^`\n]+)`(?!`)'

        def replace_inline_code(match):
            code = match.group(1)
            placeholder = self._create_placeholder("INLINE_CODE")
            protected = ProtectedSection(code, placeholder)
            self.protected_sections.append(protected)
            return f"`{placeholder}`"

        return re.sub(pattern, replace_inline_code, text)

    def extract_urls(self, text: str) -> str:
        """Extracts URLs from links and images and preserves them"""
        pattern = r'(!?\[[^\]]*\]\()([^)]+)(\))'

        def replace_url(match):
            prefix = match.group(1)
            url = match.group(2)
            suffix = match.group(3)
            is_image = prefix.startswith('!')
            
            if not _is_path_url(url):
                return match.group(0)
            
            if is_image:
                # For images, replace alt text with _TEXT_ and protect the URL
                placeholder = self._create_placeholder("IMAGE_LINK")
                replacement = f'![_TEXT_]({url})'
                protected = ProtectedSection(replacement, placeholder)
                self.protected_sections.append(protected)
                return placeholder
            else:
                # For regular links, protect the URL
                placeholder = self._create_placeholder("URL")
                protected = ProtectedSection(url, placeholder)
                self.protected_sections.append(protected)
                return prefix + placeholder + suffix

        return re.sub(pattern, replace_url, text)


    def extract_html_entities(self, text: str) -> str:
        """Extracts HTML entities and preserves them"""
        pattern = r'(&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;)'

        def replace_entity(match):
            entity = match.group(1)
            placeholder = self._create_placeholder("HTML_ENTITY")
            protected = ProtectedSection(entity, placeholder)
            self.protected_sections.append(protected)
            return placeholder

        return re.sub(pattern, replace_entity, text)

    def restore_all(self, text: str) -> str:
        """Restores all protected sections from placeholders"""
        for section in self.protected_sections:
            text = text.replace(section.placeholder, section.content)
        return text


class TextProcessor:
    """
    Handles text content replacement with _TEXT_ placeholder.
    
    This class processes text content while preserving:
    - Markdown formatting (bold, italic, links)
    - Document structure (headers, lists, HTML tags)
    - Leading whitespace (indentation) at the beginning of each line
    
    Text replacement behavior:
    - All text content (Korean, Japanese, Chinese, English, numbers) is replaced with _TEXT_
    - Multiple sentences in a line are replaced with a single _TEXT_ placeholder
    - Punctuation marks are NOT preserved
    - Consecutive _TEXT_ placeholders are merged
    
    Whitespace preservation:
    - Leading whitespace (indentation) MUST be preserved exactly as in the original
    - This ensures list nesting, code block indentation, and structural formatting remain intact
    """

    def replace_text_in_content(self, text: str) -> str:
        """Replaces text content with _TEXT_ while preserving Markdown formatting"""
        if not text.strip():
            return text

        # Combined processing: preserve markdown formatting and replace text in one pass
        result = self._replace_text_with_placeholders(text)

        # Final cleanup: merge consecutive _TEXT_ placeholders
        result = self._cleanup_text(result)

        return result

    def _split_preserving_html_tags(self, text: str) -> list[str]:
        """
        Split by whitespace, but preserve spaces inside <...> tag brackets.

        content.split() breaks HTML tags with attributes because it splits on
        the space inside <Badge color="green">. This method avoids splitting
        on whitespace that falls between < and >.

        Examples:
            "_TEXT_ <Badge color='green'>_TEXT_</Badge>"
            -> ["_TEXT_", "<Badge color='green'>_TEXT_</Badge>"]

            "_TEXT_ <br/> <Badge color='green'>_TEXT_</Badge>"
            -> ["_TEXT_", "<br/>", "<Badge color='green'>_TEXT_</Badge>"]
        """
        if not text:
            return []

        tokens = []
        current = []
        in_tag = False
        in_quote = False
        quote_char = None

        for i, char in enumerate(text):
            if in_tag:
                current.append(char)
                if in_quote:
                    if char == quote_char:
                        in_quote = False
                elif char in ('"', "'"):
                    in_quote = True
                    quote_char = char
                elif char == '>':
                    in_tag = False
            elif char == '<' and i + 1 < len(text) and (text[i + 1].isalpha() or text[i + 1] == '/'):
                # Only treat < as tag start if followed by a letter or /
                # This avoids false positives like <=, <`, etc.
                current.append(char)
                in_tag = True
            elif char.isspace():
                if current:
                    tokens.append(''.join(current))
                    current = []
            else:
                current.append(char)

        if current:
            tokens.append(''.join(current))

        return tokens

    def _normalize_pattern_order(self, line: str) -> str:
        """
        Normalize the order of patterns in a converted line to reduce differences
        between Korean and English translations.
        
        This function treats patterns in a line as a Set, ensuring:
        1. Simple _TEXT_ patterns appear before formatted patterns (inline code, bold, etc.)
        2. Trailing simple _TEXT_ patterns are removed if they appear after formatted patterns
        3. Structural elements (indentation, list markers, headers) are preserved
        4. Leading whitespace is always preserved exactly as it appears in the original
        
        Examples:
            "2. _TEXT_ `_TEXT_` _TEXT_" -> "2. _TEXT_ `_TEXT_`"
            "_TEXT_ **_TEXT_** _TEXT_" -> "_TEXT_ **_TEXT_**"
            "* `_TEXT_` _TEXT_" -> "* _TEXT_ `_TEXT_`"
        
        Args:
            line: A line of skeleton-converted text
            
        Returns:
            The normalized line with patterns reordered
        """
        if not line.strip():
            return line
        
        # Extract structural prefix (indentation, list markers, headers, etc.)
        # Match: optional whitespace + optional list marker (number, bullet) + required whitespace
        # or header markers (#)
        # Note: List marker must be followed by whitespace (not part of markdown formatting)
        # Pattern: (whitespace)(number. or - or *)(whitespace) or (whitespace)(#+)(whitespace)
        structural_match = re.match(r'^(\s*)(\d+\.\s+|[-*]\s+|#+\s+)', line)
        if structural_match:
            prefix = structural_match.group(0)
            content = line[len(prefix):]
        else:
            # Try to match just whitespace prefix
            whitespace_match = re.match(r'^(\s+)', line)
            if whitespace_match:
                prefix = whitespace_match.group(0)
                content = line[len(prefix):]
            else:
                prefix = ''
                content = line
        
        if not content.strip():
            return line

        # Split content by whitespace to get tokens, preserving complete HTML tags
        tokens = self._split_preserving_html_tags(content)
        
        # Identify pattern types (order matters: check longer patterns first)
        # Check bold (**_TEXT_**) before italic (*_TEXT_*) to avoid false matches
        pattern_types = [
            ('**_TEXT_**', 'bold'),
            ('*_TEXT_*', 'italic'),
            ('`_TEXT_`', 'code'),
            ('_TEXT_', 'text_placeholder'),
        ]
        
        # Collect patterns and other tokens
        patterns_found = {
            'text_placeholder': False,
            'code': False,
            'bold': False,
            'italic': False,
        }
        
        other_tokens = []
        
        for token in tokens:
            pattern_type = None
            for pattern, ptype in pattern_types:
                if token == pattern:
                    pattern_type = ptype
                    patterns_found[ptype] = True
                    break
            
            if pattern_type is None:
                # Not a standard pattern - preserve it (could be link, HTML entity, etc.)
                other_tokens.append(token)
        
        # Build normalized pattern list in order: _TEXT_, `_TEXT_`, **_TEXT_**, *_TEXT_*
        normalized_patterns = []
        if patterns_found['text_placeholder']:
            normalized_patterns.append('_TEXT_')
        if patterns_found['code']:
            normalized_patterns.append('`_TEXT_`')
        if patterns_found['bold']:
            normalized_patterns.append('**_TEXT_**')
        if patterns_found['italic']:
            normalized_patterns.append('*_TEXT_*')
        
        # Remove duplicate patterns from other_tokens
        # If a pattern type is already in normalized_patterns, remove tokens that contain that pattern
        # This handles cases like "**_TEXT_****_TEXT_**" where multiple patterns are concatenated
        filtered_other_tokens = []
        for token in other_tokens:
            # Check if this token is exactly a pattern that's already in normalized_patterns
            is_exact_duplicate_pattern = False
            for pattern in pattern_types:
                pattern_str, _ = pattern
                if token == pattern_str:
                    is_exact_duplicate_pattern = True
                    break
            
            if is_exact_duplicate_pattern:
                # Skip exact duplicate patterns (they're already in normalized_patterns)
                continue
            
            # Check if token contains patterns that are already in normalized_patterns
            # For example, "**_TEXT_****_TEXT_**" contains "**_TEXT_**" which is already normalized
            # BUT: preserve links, HTML entities, and other structural elements even if they contain _TEXT_
            is_structural_element = (
                token.startswith('[') and '](' in token and token.endswith(')') or  # Link: [_TEXT_](url)
                token.startswith('![') and '](' in token and token.endswith(')') or  # Image: ![_TEXT_](url)
                token.startswith('&') and token.endswith(';') or  # HTML entity: &amp;
                token.startswith('<') and token.endswith('>')  # HTML tag: <tag>
            )
            
            if is_structural_element:
                # Preserve structural elements (links, images, HTML entities, tags) even if they contain patterns
                filtered_other_tokens.append(token)
                continue
            
            contains_duplicate_pattern = False
            for pattern_str in normalized_patterns:
                # Check if the pattern appears in the token (as a substring)
                # Use word boundaries to avoid false matches
                if pattern_str in token:
                    # More precise check: pattern should be surrounded by word boundaries or start/end
                    # For patterns like "**_TEXT_**", check if it appears as a complete pattern
                    pattern_escaped = re.escape(pattern_str)
                    if re.search(pattern_escaped, token):
                        contains_duplicate_pattern = True
                        break
            
            if not contains_duplicate_pattern:
                filtered_other_tokens.append(token)
        
        # Combine: prefix + normalized patterns + filtered other tokens
        # IMPORTANT: Preserve leading whitespace in prefix exactly as it appears
        content_parts = []
        if normalized_patterns:
            content_parts.extend(normalized_patterns)
        
        if filtered_other_tokens:
            content_parts.extend(filtered_other_tokens)
        
        # Join content parts with single spaces
        content_result = ' '.join(content_parts) if content_parts else ''
        
        # Combine prefix (with preserved leading whitespace) and content
        # If prefix ends with whitespace and content exists, use prefix as-is
        # Otherwise, ensure proper spacing between prefix and content
        if prefix:
            # Preserve prefix exactly, including all leading whitespace
            if content_result:
                # Check if prefix already ends with whitespace (for list markers, headers)
                if prefix.rstrip() != prefix:
                    # Prefix ends with whitespace (e.g., "  * " or "## ")
                    result = prefix + content_result
                else:
                    # Prefix doesn't end with whitespace, add space before content
                    result = prefix + ' ' + content_result
            else:
                # No content, return prefix as-is (preserving trailing whitespace if any)
                result = prefix
        else:
            result = content_result
        
        # Preserve trailing whitespace from original if it exists
        if line.endswith(' ') and not result.endswith(' '):
            result += ' '
        
        return result

    def _is_boundary_char(self, char: str) -> bool:
        """Check if character is a word boundary (space, newline, tab, or non-alphanumeric)"""
        return not char or char in (' ', '\n', '\t') or not char.isalnum()
    
    def _match_italic(self, text: str, pos: int, marker: str) -> Optional[Tuple[str, int]]:
        """Match italic markdown: *text* or _text_. Returns (content, length) if matched, None otherwise."""
        if text[pos:pos+len(marker)*2] == marker * 2:  # Skip bold markers
            return None
        
        # Check for wildcard pattern (*.csv)
        if marker == '*' and pos + 1 < len(text) and text[pos + 1] == '.':
            return None
        
        # Check boundary before marker
        prev_char = text[pos - 1] if pos > 0 else ''
        if not self._is_boundary_char(prev_char):
            return None
        
        # Match italic content
        pattern = rf'\{marker}([^{marker}]+?)\{marker}'
        match = re.match(pattern, text[pos:])
        if not match:
            return None
        
        # Check boundary after closing marker
        end_pos = pos + len(match.group(0))
        next_char = text[end_pos] if end_pos < len(text) else ''
        if not self._is_boundary_char(next_char):
            return None
        
        return (match.group(1), len(match.group(0)))
    
    def _is_underscore_marker(self, text: str, pos: int) -> bool:
        """Check if _ at pos is a valid italic marker (not part of word/emoji/bold)."""
        if pos + 1 < len(text) and text[pos + 1] == '_':
            return False  # Part of __ (bold) or placeholder
        if re.match(r'__[A-Z_]+_\d+__', text[pos:]):
            return False  # Part of placeholder
        # Check boundaries: must be at word boundary (whitespace or start/end)
        before = text[pos - 1] if pos > 0 else ' '
        after = text[pos + 1] if pos + 1 < len(text) else ' '
        return (before in ' \n\t' or pos == 0) and (after in ' \n\t' or pos + 1 >= len(text))
    
    def _find_next_marker(self, text: str, start: int) -> int:
        """Find position of next markdown marker, skipping wildcard patterns."""
        patterns = [
            r'`__[A-Z_]+_\d+__`',  # Placeholders with backticks
            r'__[A-Z_]+_\d+__',     # Placeholders
            r'\*\*',                # Bold start
            r'__',                  # Bold start
            r'`',                   # Code
            r'\*',                  # Italic or wildcard
            r'\[',                  # Link
        ]
        
        next_pos = len(text)
        for pattern in patterns:
            match = re.search(pattern, text[start:])
            if match:
                pos = start + match.start()
                if text[pos] == '*' and pos + 1 < len(text) and text[pos + 1] == '.':
                    continue  # Skip wildcard patterns (*.csv)
                if match.start() < next_pos - start:
                    next_pos = pos
        
        # Check for underscore (_) as italic marker
        underscore_pos = text.find('_', start)
        if underscore_pos != -1 and underscore_pos < next_pos and self._is_underscore_marker(text, underscore_pos):
            next_pos = underscore_pos
        
        return next_pos
    
    def _replace_text_with_placeholders(self, text: str) -> str:
        """Replace all text content with _TEXT_ while preserving markdown structure"""
        tokens = []
        i = 0
        
        while i < len(text):
            matched = False
            
            # 1. Placeholders (most specific)
            if re.match(r'\((__[A-Z_]+_\d+__)\)', text[i:]):
                match = re.match(r'\((__[A-Z_]+_\d+__)\)', text[i:])
                tokens.append(('placeholder', match.group(0)))
                i += len(match.group(0))
                continue
            
            match = re.match(r'`__[A-Z_]+_\d+__`|__[A-Z_]+_\d+__', text[i:])
            if match:
                tokens.append(('placeholder', match.group(0)))
                i += len(match.group(0))
                continue
            
            # 2. Bold
            if text[i:].startswith('**'):
                match = re.match(r'\*\*([^*]+)\*\*', text[i:])
                if match:
                    tokens.append(('bold', match.group(1)))
                    i += len(match.group(0))
                    continue
            
            if text[i:].startswith('__') and not re.match(r'__[A-Z_]+_\d+__', text[i:]):
                match = re.match(r'__([^_]+)__', text[i:])
                if match:
                    tokens.append(('bold', match.group(1)))
                    i += len(match.group(0))
                    continue
            
            # 3. Inline code
            # Note: inline code text is converted to _TEXT_ (not preserved as-is)
            if text[i] == '`':
                match = re.match(r'`([^`]+)`', text[i:])
                if match:
                    tokens.append(('code', '_TEXT_'))
                    i += len(match.group(0))
                    continue
            
            # 4. Italic
            for marker in ['*', '_']:
                if text[i] == marker:
                    result = self._match_italic(text, i, marker)
                    if result:
                        content, length = result
                        tokens.append(('italic', content))
                        i += length
                        matched = True
                        break
            if matched:
                continue
            
            # 5. Links
            if text[i] == '[' and not text[i:].startswith('!['):
                # Match link with URL (including placeholder URLs)
                match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', text[i:])
                if match:
                    tokens.append(('link', (match.group(1), match.group(2))))
                    i += len(match.group(0))
                    continue
                
                match = re.match(r'\[([^\]]+)\]', text[i:])
                if match:
                    tokens.append(('link', (match.group(1), None)))
                    i += len(match.group(0))
                    continue
            
            # 6. Emoji pattern (before regular text to prevent splitting)
            # Emoji pattern: :[a-z_]+:
            emoji_match = re.match(r':[a-z_]+:', text[i:])
            if emoji_match:
                tokens.append(('text', emoji_match.group(0)))
                i += len(emoji_match.group(0))
                continue
            
            # 7. Regular text
            next_pos = self._find_next_marker(text, i)
            if next_pos > i:
                tokens.append(('text', text[i:next_pos]))
                i = next_pos
            else:
                tokens.append(('text', text[i:]))
                break
        
        # Helper functions
        def needs_space_before():
            return result_parts and not result_parts[-1].endswith((' ', '\n', '>', '`'))
        
        def preserve_space_after(token_idx):
            """Preserve space if next token is text starting with space."""
            if token_idx + 1 < len(tokens):
                next_type, next_content = tokens[token_idx + 1]
                if next_type == 'text' and next_content and next_content[0] == ' ':
                    result_parts.append(' ')
        
        # Process tokens
        result_parts = []
        for i, (token_type, content) in enumerate(tokens):
            if token_type == 'placeholder':
                if needs_space_before() and (content.startswith('`') or 'HTML_ENTITY' in content):
                    result_parts.append(' ')
                result_parts.append(content)
                preserve_space_after(i)
            elif token_type == 'bold':
                result_parts.append('**_TEXT_**')
            elif token_type == 'italic':
                result_parts.append('*_TEXT_*')
            elif token_type == 'code':
                result_parts.append(f'`{content}`')
                preserve_space_after(i)
            elif token_type == 'link':
                if needs_space_before():
                    result_parts.append(' ')
                link_text, link_url = content if isinstance(content, tuple) else (content, None)
                if link_url:
                    # URL can be a placeholder (__URL_N__) or actual URL
                    result_parts.append(f'[_TEXT_]({link_url})')
                else:
                    result_parts.append('[_TEXT_]')
            elif token_type == 'text':
                # Preserve spaces in text segments
                # Remove punctuation marks (periods, exclamation marks, question marks, colons, semicolons, commas, Japanese comma)
                # Note: Colon (:) in general text is NOT a markdown syntax element and is removed like other punctuation
                # Note: Japanese comma (、) is treated the same as regular comma (,)
                cleaned = re.sub(r'[.,;:!?。！？、]+', '', content)
                if cleaned.strip():
                    # Regular text processing
                    if needs_space_before() and content and content[0] == ' ':
                        result_parts.append(' ')
                    result_parts.append('_TEXT_')
                    # Add space after _TEXT_ if next token needs separation
                    if i + 1 < len(tokens):
                        next_type, next_content = tokens[i + 1]
                        if next_type in ('bold', 'italic', 'code', 'link'):
                            result_parts.append(' ')
                        elif next_type == 'placeholder' and (next_content.startswith('`') or 'HTML_ENTITY' in next_content):
                            result_parts.append(' ')
                        elif content and content[-1] == ' ' and next_type == 'text':
                            result_parts.append(' ')
        
        return ''.join(result_parts)

    def _cleanup_text(self, text: str) -> str:
        """Final cleanup: merge consecutive _TEXT_ placeholders and normalize spacing after inline code, links, HTML tags, and formatting
        
        Uses token-based approach instead of regex to avoid pattern matching issues.
        """
        # Step 0: Separate concatenated patterns (e.g., "**_TEXT_****_TEXT_**" -> "**_TEXT_** **_TEXT_**")
        # This handles cases where multiple patterns are concatenated without spaces
        # Define all patterns that need spacing when concatenated
        patterns = [
            r'\*\*_TEXT_\*\*',  # Bold: **_TEXT_**
            r'\*_TEXT_\*',      # Italic: *_TEXT_*
            r'`_TEXT_`',        # Inline code: `_TEXT_`
            r'_TEXT_',          # Text placeholder: _TEXT_
        ]
        
        # Add space between any two patterns (same or different) that are concatenated without space
        # This handles:
        # - Same patterns (e.g., "**_TEXT_****_TEXT_**" -> "**_TEXT_** **_TEXT_**")
        # - Different patterns in any order (e.g., "_TEXT_**_TEXT_**" or "*_TEXT_*_TEXT_")
        # Process all combinations to ensure both directions are handled
        for pattern1 in patterns:
            for pattern2 in patterns:
                # Create regex pattern: (pattern1)(pattern2) -> (pattern1) (pattern2)
                regex_pattern = f'({pattern1})({pattern2})'
                text = re.sub(regex_pattern, r'\1 \2', text)
        
        # Step 1: Merge consecutive _TEXT_ placeholders
        text = re.sub(r'_TEXT_([\s_]*_TEXT_)+', '_TEXT_', text)
        
        # Step 2: Remove trailing spaces after HTML tags (e.g., <br/>  -> <br/>)
        text = re.sub(r'(<br/?>|/>)\s+', r'\1', text)
        
        # Step 3: Tokenize the text
        tokens = self._tokenize_for_cleanup(text)
        
        # Step 4: Normalize spacing between tokens
        normalized_parts = self._normalize_spacing(tokens)
        
        # Step 5: Join tokens back into string
        return ''.join(normalized_parts)
    
    def _tokenize_for_cleanup(self, text: str) -> List[Tuple[str, str]]:
        """Tokenize text for cleanup processing. Returns list of (type, content) tuples."""
        tokens = []
        i = 0
        
        while i < len(text):
            # 1. Bold: **_TEXT_**
            if text[i:].startswith('**_TEXT_**'):
                tokens.append(('bold', '**_TEXT_**'))
                i += len('**_TEXT_**')
            # 2. Italic: *_TEXT_*
            elif text[i:].startswith('*_TEXT_*'):
                tokens.append(('italic', '*_TEXT_*'))
                i += len('*_TEXT_*')
            # 3. Inline code: `...`
            elif text[i] == '`':
                match = re.match(r'`([^`]+)`', text[i:])
                if match:
                    tokens.append(('code', match.group(0)))
                    i += len(match.group(0))
                else:
                    tokens.append(('text', text[i]))
                    i += 1
            # 4. Link: [_TEXT_](url)
            elif text[i] == '[' and text[i:].startswith('[_TEXT_]('):
                match = re.match(r'\[_TEXT_\]\(([^)]+)\)', text[i:])
                if match:
                    tokens.append(('link', match.group(0)))
                    i += len(match.group(0))
                else:
                    tokens.append(('text', text[i]))
                    i += 1
            # 5. HTML tag: <br/>, />
            elif text[i] == '<' and i + 3 < len(text) and text[i:i+3] == '<br':
                match = re.match(r'<br/?>', text[i:])
                if match:
                    tokens.append(('html_tag', match.group(0)))
                    i += len(match.group(0))
                else:
                    tokens.append(('text', text[i]))
                    i += 1
            elif i + 1 < len(text) and text[i:i+2] == '/>':
                tokens.append(('html_tag', '/>'))
                i += 2
            # 6. HTML entity: &lt;, &gt;, &amp;, etc.
            elif text[i] == '&':
                match = re.match(r'(&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;)', text[i:])
                if match:
                    tokens.append(('html_entity', match.group(0)))
                    i += len(match.group(0))
                else:
                    tokens.append(('text', text[i]))
                    i += 1
            # 7. Whitespace
            elif text[i] in ' \n\t':
                tokens.append(('whitespace', text[i]))
                i += 1
            # 8. _TEXT_ placeholder
            elif text[i:].startswith('_TEXT_'):
                tokens.append(('text_placeholder', '_TEXT_'))
                i += len('_TEXT_')
            # 9. 기타 문자
            else:
                tokens.append(('text', text[i]))
                i += 1
        
        return tokens
    
    def _normalize_spacing(self, tokens: List[Tuple[str, str]]) -> List[str]:
        """Normalize spacing between tokens. Returns list of strings to join."""
        result = []
        
        for i, (token_type, content) in enumerate(tokens):
            result.append(content)
            
            # 다음 토큰 확인
            if i + 1 < len(tokens):
                next_type, next_content = tokens[i + 1]
                
                # 공백 정규화 규칙 적용
                needs_space = False
                
                # 1. Bold/Italic 다음에 공백이 아닌 텍스트가 오면 공백 추가
                if token_type in ('bold', 'italic') and next_type not in ('whitespace', 'bold', 'italic'):
                    needs_space = True
                
                # 2. Inline code 다음에 공백이 아닌 텍스트가 오면 공백 추가 (다음이 code여도 공백 추가)
                elif token_type == 'code' and next_type != 'whitespace':
                    needs_space = True
                
                # 3. Link 다음에 공백이 아닌 텍스트가 오면 공백 추가
                elif token_type == 'link' and next_type not in ('whitespace', 'link'):
                    needs_space = True
                
                # 4. HTML tag 다음에 공백이 아닌 텍스트가 오면 공백 추가
                elif token_type == 'html_tag' and next_type not in ('whitespace', 'html_tag'):
                    needs_space = True
                
                # 5. HTML entity 다음에 공백이 아닌 텍스트가 오면 공백 추가
                elif token_type == 'html_entity' and next_type not in ('whitespace', 'html_entity'):
                    needs_space = True
                
                # 6. _TEXT_ 다음에 HTML tag가 오면 공백 추가 (역방향)
                elif token_type == 'text_placeholder' and next_type == 'html_tag':
                    needs_space = True
                
                # 7. _TEXT_ 다음에 HTML entity가 오면 공백 추가 (역방향)
                elif token_type == 'text_placeholder' and next_type == 'html_entity':
                    needs_space = True
                
                # 8. _TEXT_ 다음에 inline code가 오면 공백 추가
                elif token_type == 'text_placeholder' and next_type == 'code':
                    needs_space = True
                
                # 9. _TEXT_ 다음에 _TEXT_가 오면 공백 추가 (변환 결과물 사이 공백 보장)
                elif token_type == 'text_placeholder' and next_type == 'text_placeholder':
                    needs_space = True
                
                # 공백 추가 (다음 토큰이 공백이 아닐 때만)
                if needs_space and next_type != 'whitespace':
                    result.append(' ')
        
        return result

def process_yaml_frontmatter(yaml_content: str) -> List[str]:
    """Process YAML frontmatter content, replacing text values with _TEXT_"""
    processed_lines = []
    for line in yaml_content.split('\n'):
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
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
    return processed_lines


def process_text_line(line: str, text_processor: TextProcessor) -> str:
    """
    Processes a line of text, replacing content with _TEXT_ while preserving structure.
    
    IMPORTANT: Leading whitespace (indentation) MUST be preserved.
    This function maintains the exact leading whitespace of the input line.
    """
    if not line.strip():
        return line

    # Import statements are now handled by ContentProtector.extract_import_statements
    # Check if this line is an import placeholder
    if re.match(r'^__IMPORT_\d+__$', line.strip()):
        return line

    if line.strip().startswith('```') or line.strip() == '```':
        return line
    if '__CODE_BLOCK_' in line:
        return line
    
    # Don't skip lines with placeholders - they may contain text that needs processing

    # Preserve horizontal rules (---, ___, ***, or with spaces like - - -)
    # Markdown horizontal rule: 3 or more of the SAME character (-, _, or *) with optional spaces
    # Must use the same character type throughout (e.g., --- is valid, but *-* is not)
    if re.match(r'^\s*([-](\s*[-]){2,}|[_](\s*[_]){2,}|[*](\s*[*]){2,})\s*$', line.strip()):
        return line

    # Check if line contains HTML tags - process HTML first
    if '<' in line and '>' in line:
        # For lines with HTML, check if it's a markdown list item first
        list_match = re.match(r'^(\s*)([-*]|\d+\.)(\s+)(.*)$', line)
        if list_match:
            # It's a list item with HTML - process markdown structure first, then HTML content
            indent = list_match.group(1)
            marker = list_match.group(2)
            spacing = list_match.group(3)
            content = list_match.group(4)
            # Process HTML content
            processed_content = _process_html_line(content, text_processor)
            # Normalize spacing after marker: use single space if content exists, no space if empty
            normalized_spacing = ' ' if processed_content.strip() else ''
            result = indent + marker + normalized_spacing + processed_content
            # Apply pattern normalization
            return text_processor._normalize_pattern_order(result)
        else:
            # Regular HTML line
            result = _process_html_line(line, text_processor)
            # Apply pattern normalization
            return text_processor._normalize_pattern_order(result)

    result = process_markdown_line(line, text_processor)
    # Apply pattern normalization
    return text_processor._normalize_pattern_order(result)


def _process_html_line(line: str, text_processor: TextProcessor) -> str:
    """
    Process HTML tags structure but replace text content using regex.

    IMPORTANT: Leading whitespace (indentation) MUST be preserved.
    The function preserves leading whitespace at the beginning of the line.
    """
    # Preserve leading whitespace
    leading_whitespace = ''
    stripped = line.lstrip()
    if stripped != line:
        leading_whitespace = line[:len(line) - len(stripped)]

    # Process <img> tags to replace alt attribute text with _TEXT_
    # Pattern: <img ... alt="some text" ... />
    # Replace alt attribute content with _TEXT_
    def replace_img_alt(match):
        tag = match.group(0)
        # Replace alt="..." with alt="_TEXT_"
        # Handle both alt="..." and alt='...'
        tag = re.sub(r'alt="[^"]*"', 'alt="_TEXT_"', tag)
        tag = re.sub(r"alt='[^']*'", "alt='_TEXT_'", tag)
        return tag

    stripped = re.sub(r'<img[^>]*>', replace_img_alt, stripped)

    # Split by HTML tags, keeping the tags
    parts = re.split(r'(<[^>]+>|</[^>]+>)', stripped)
    result = []
    for i, part in enumerate(parts):
        if part.startswith('<'):
            # HTML tag - keep as-is (alt already processed for img tags)
            result.append(part)
        elif part.strip():
            # Text content - process it
            # Preserve trailing space if it exists in the original
            # This preserves spaces before HTML tags as they appear in the original
            trailing_space = ''
            if part.endswith(' '):
                trailing_space = ' '
            processed_text = text_processor.replace_text_in_content(part.rstrip())
            result.append(processed_text + trailing_space)
        else:
            # Preserve whitespace-only parts
            result.append(part)
    # Join all parts
    joined_result = ''.join(result)
    # Apply cleanup to normalize spacing (e.g., <br/>_TEXT_ -> <br/> _TEXT_)
    cleaned_result = text_processor._cleanup_text(joined_result)
    return leading_whitespace + cleaned_result


def process_markdown_line(line: str, text_processor: TextProcessor) -> str:
    """
    Processes a markdown line, preserving structure.
    
    IMPORTANT: Leading whitespace (indentation) MUST be preserved.
    The function extracts and preserves leading whitespace before processing content.
    """
    header_match = re.match(r'^(\s*#+\s+)(.*)$', line)
    if header_match:
        prefix = header_match.group(1)  # Preserves leading whitespace
        content = header_match.group(2)
        processed_content = text_processor.replace_text_in_content(content)
        return prefix + processed_content

    list_match = re.match(r'^(\s*)([-*]|\d+\.)(\s+)(.*)$', line)
    if list_match:
        indent = list_match.group(1)  # Preserves leading whitespace (indentation)
        marker = list_match.group(2)
        spacing = list_match.group(3)
        content = list_match.group(4)
        processed_content = text_processor.replace_text_in_content(content)
        # Normalize spacing after marker: use single space if content exists, no space if empty
        normalized_spacing = ' ' if processed_content.strip() else ''
        return indent + marker + normalized_spacing + processed_content

    # For regular lines, preserve leading whitespace
    leading_whitespace = ''
    stripped = line.lstrip()
    if stripped != line:
        leading_whitespace = line[:len(line) - len(stripped)]
    processed_content = text_processor.replace_text_in_content(stripped)
    return leading_whitespace + processed_content


def delete_skeleton_files(directories: List[Path]) -> int:
    """
    Delete all .skel.mdx files in the specified directories recursively.
    If directories list is empty, uses default directories (target/ko, target/ja, target/en).
    
    Args:
        directories: List of directories to process
        
    Returns:
        Exit code (0 for success, 1 for errors)
    """
    if len(directories) == 0:
        # No directories specified, use defaults (Korean, Japanese, English order)
        default_dirs = [
            _PROJECT_DIR / 'target/ko',
            _PROJECT_DIR / 'target/ja',
            _PROJECT_DIR / 'target/en',
        ]
        directories = default_dirs
    
    total_deleted = 0
    total_errors = 0
    
    for directory in directories:
        if not directory.exists():
            print(f"Warning: Directory not found: {directory}", file=sys.stderr)
            continue
        if not directory.is_dir():
            print(f"Warning: Path is not a directory: {directory}", file=sys.stderr)
            continue
        
        # Find all .skel.mdx files recursively
        skel_files = list(directory.rglob('*.skel.mdx'))
        
        deleted_count = 0
        error_count = 0
        
        for skel_file in skel_files:
            try:
                skel_file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {skel_file}: {e}", file=sys.stderr)
                error_count += 1
        
        total_deleted += deleted_count
        total_errors += error_count
        
        print(f"{directory}: {deleted_count} files deleted, {error_count} errors")
    
    # Print overall summary if multiple directories
    if len(directories) > 1:
        print(f"Total: {total_deleted} files deleted, {total_errors} errors")
    
    return 0 if total_errors == 0 else 1


def convert_mdx_to_skeleton(input_path: Path) -> Path:
    """
    Converts an MDX file to skeleton format.
    
    This function performs the following steps:
    1. Extracts and protects YAML frontmatter
    2. Extracts and protects code blocks, inline code, URLs, HTML entities, and image links
    3. Processes each line to replace text content with _TEXT_ placeholder
    4. Restores all protected sections
    5. Writes the skeleton MDX file
    
    Features preserved during conversion:
    - YAML frontmatter structure (text values replaced with _TEXT_)
    - Code blocks and inline code (preserved as-is)
    - URLs in links and images (preserved)
    - HTML entities (preserved as-is)
    - Markdown formatting (bold, italic, links structure preserved)
    - Document structure (headers, lists, HTML tags)
    - Image links (alt text replaced with _TEXT_, URL preserved)
    - Leading whitespace (indentation) MUST be preserved exactly as in the original
    
    Whitespace Preservation Rule:
    - Leading whitespace at the beginning of each line MUST be maintained
    - This includes spaces and tabs used for indentation in lists, code blocks, and nested structures
    - The skeleton output should have identical indentation structure as the input
    
    Args:
        input_path: Path to the input MDX file
        
    Returns:
        Path to the generated skeleton MDX file
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix != '.mdx':
        raise ValueError(f"Input file must have .mdx extension: {input_path}")

    if input_path.name.endswith('.skel.mdx'):
        raise ValueError(f"Skipping .skel.mdx file to avoid recursion: {input_path}")

    # Read input file
    content = input_path.read_text(encoding='utf-8')

    # Initialize processors
    protector = ContentProtector()
    text_processor = TextProcessor()

    # Step 1: Extract and protect YAML frontmatter
    content, yaml_section = protector.extract_yaml_frontmatter(content)

    # Step 2: Extract and protect import statements
    content = protector.extract_import_statements(content)

    # Step 3: Extract and protect other content sections
    content = protector.extract_code_blocks(content)
    # Note: inline code is no longer protected - its text content will be converted to _TEXT_
    content = protector.extract_urls(content)  # Now handles both links and images
    content = protector.extract_html_entities(content)

    # Step 4: Process YAML frontmatter if present
    yaml_start_idx = None
    yaml_end_idx = None
    if yaml_section:
        # Process YAML content
        yaml_lines = process_yaml_frontmatter(yaml_section.content)
        processed_yaml = '\n'.join(yaml_lines)
        # Replace the YAML placeholder with processed content (keeping delimiters)
        # The placeholder is in the format: ---\n__YAML_FRONTMATTER__\n---
        yaml_block = f"---\n{yaml_section.placeholder}\n---"
        processed_block = f"---\n{processed_yaml}\n---"
        content = content.replace(yaml_block, processed_block)
        
        # Find YAML block boundaries to skip processing
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == '---' and yaml_start_idx is None:
                yaml_start_idx = i
            elif line.strip() == '---' and yaml_start_idx is not None and yaml_end_idx is None:
                yaml_end_idx = i
                break
    else:
        lines = content.split('\n')

    # Step 5: Process lines and replace text content
    if lines is None:
        lines = content.split('\n')
    processed_lines = []

    for i, line in enumerate(lines):
        # Skip YAML frontmatter lines (already processed)
        if yaml_start_idx is not None and yaml_end_idx is not None:
            if yaml_start_idx <= i <= yaml_end_idx:
                processed_lines.append(line)
                continue
        
        # Process each line
        processed_line = process_text_line(line, text_processor)
        processed_lines.append(processed_line)

    content = '\n'.join(processed_lines)

    # Step 6: Restore all protected sections (including import statements, image links, etc.)
    content = protector.restore_all(content)
    
    # Step 5: Post-processing to handle special cases
    # Normalize spacing after HTML entities: ensure space between HTML entity and _TEXT_
    # Pattern: &lt;_TEXT_ -> &lt; _TEXT_, &gt;_TEXT_ -> &gt; _TEXT_
    content = re.sub(r'(&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;)(_TEXT_)', r'\1 \2', content)
    # Pattern: _TEXT_&lt; -> _TEXT_ &lt;, _TEXT_&gt; -> _TEXT_ &gt;
    content = re.sub(r'(_TEXT_)(&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;)', r'\1 \2', content)
    
    # Remove trailing spaces after HTML tags at end of lines
    # Note: Use [ \t]+ instead of \s+ to avoid matching newlines, which would remove blank lines
    content = re.sub(r'(<br/?>|/>)[ \t]+\n', r'\1\n', content)
    # Remove trailing spaces after HTML tags before newlines (but preserve spaces before other content)
    lines = content.split('\n')
    processed_final_lines = []
    for line in lines:
        # Remove trailing space after /> or <br/> at end of line
        line = re.sub(r'(<br/?>|/>)\s+$', r'\1', line)
        processed_final_lines.append(line)
    content = '\n'.join(processed_final_lines)

    # Generate output path
    output_path = input_path.parent / f"{input_path.stem}.skel.mdx"

    # Write output file
    output_path.write_text(content, encoding='utf-8')

    return output_path


def compare_skeleton_files(
    korean_skel_path: Path,
    translation_skel_path: Path,
    translation_mdx_path: Path
) -> Tuple[bool, Optional[str], Optional[Path]]:
    """
    Compare two skeleton MDX files and return comparison result.
    
    This function compares the Korean skeleton file with the translation skeleton file
    and returns the comparison result. It uses the common comparison logic from skeleton_diff module.
    
    Args:
        korean_skel_path: Path to the Korean skeleton MDX file
        translation_skel_path: Path to the translation skeleton MDX file
        translation_mdx_path: Path to the original translation MDX file (for error reporting)
    
    Returns:
        Tuple of (should_continue, comparison_result, unmatched_file_path)
        - should_continue: True if it should continue processing, False if max_diff is reached and should stop
        - comparison_result: 'matched' if files are identical, 'unmatched' if different, None if not compared
        - unmatched_file_path: Path to the unmatched .mdx file (with target/{lang} prefix) if unmatched, None otherwise
    """
    from skeleton import diff as skeleton_diff
    # Access the internal comparison function
    return skeleton_diff._compare_two_skeleton_files(
        korean_skel_path,
        translation_skel_path,
        translation_mdx_path
    )


def convert_and_compare_mdx_to_skeleton(input_path: Path) -> Tuple[Path, Optional[str], Optional[Path]]:
    """
    Converts an MDX file to skeleton format and compares it with Korean equivalent.
    
    This function performs the following steps:
    1. Converts the input MDX file to skeleton MDX (deletes existing skeleton if present)
    2. Finds the corresponding Korean MDX file (raises error if not found)
    3. Converts the Korean MDX file to skeleton MDX (deletes existing skeleton if present)
    4. Compares the translation skeleton MDX with the Korean skeleton MDX
    
    Args:
        input_path: Path to the input MDX file
        
    Returns:
        Tuple of (output_path, comparison_result, unmatched_file_path)
        - output_path: Path to the generated skeleton MDX file
        - comparison_result: 'matched' if files are identical, 'unmatched' if different, None if not compared
        - unmatched_file_path: Path to the unmatched .mdx file (with target/{lang} prefix) if unmatched, None otherwise
        
    Raises:
        FileNotFoundError: If Korean MDX file is not found
    """
    # Check if file should be excluded from comparison
    if should_exclude_file(input_path):
        # Still convert to skeleton, but skip comparison
        output_path = input_path.parent / f"{input_path.stem}.skel.mdx"
        if output_path.exists():
            output_path.unlink()
        output_path = convert_mdx_to_skeleton(input_path)
        return output_path, None, None
    
    # Step 1: Convert input MDX to skeleton MDX
    # Delete existing skeleton file if it exists
    output_path = input_path.parent / f"{input_path.stem}.skel.mdx"
    if output_path.exists():
        output_path.unlink()
    
    # Convert and save
    output_path = convert_mdx_to_skeleton(input_path)
    
    # Step 2: Find corresponding Korean MDX file
    # Check if current file is Korean first
    current_lang = extract_language_code(input_path)
    if current_lang == 'ko':
        # Korean file, no need to compare
        return output_path, None, None
    
    # Get Korean equivalent path
    korean_mdx_path, korean_exists = get_korean_equivalent_path(input_path)
    if not korean_exists:
        logger.warning(f"Corresponding Korean MDX file not found: {korean_mdx_path}")
        return output_path, None, None
    
    # Step 3: Convert Korean MDX to skeleton MDX
    # Delete existing skeleton file if it exists
    korean_skel_path = korean_mdx_path.parent / f"{korean_mdx_path.stem}.skel.mdx"
    if korean_skel_path.exists():
        korean_skel_path.unlink()
    
    # Convert and save
    korean_skel_path = convert_mdx_to_skeleton(korean_mdx_path)
    
    # Step 4: Compare translation skeleton MDX with Korean skeleton MDX
    _, comparison_result, unmatched_file_path = compare_skeleton_files(
        korean_skel_path, output_path, input_path
    )
    
    return output_path, comparison_result, unmatched_file_path


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
    parser.add_argument(
        '--output',
        type=Path,
        metavar='FILE',
        help='Output file path to save list of unmatched files (only used with --recursive option). Each line contains a path with target/{lang} prefix.'
    )
    parser.add_argument(
        '--use-ignore',
        action='store_true',
        help='Use ignore_skeleton_diff.yaml patterns when comparing files (only applies to single file mode).'
    )
    parser.add_argument(
        '--ignore-file',
        type=Path,
        metavar='FILE',
        help='Path to ignore_skeleton_diff.yaml file. If not specified, uses default location (same directory as script).'
    )
    parser.add_argument(
        '--reset',
        nargs='*',
        type=Path,
        metavar='DIR',
        help='Delete all .skel.mdx files in directory(ies) recursively. If no directories specified, defaults to target/ko, target/ja, target/en'
    )

    args = parser.parse_args()

    # Initialize config if recursive mode is used or if --use-ignore is specified
    if args.recursive is not None or args.use_ignore:
        exclude_patterns = args.exclude if args.exclude and len(args.exclude) > 0 else ['/index.skel.mdx']
        # For single file mode, max_diff is not applicable, so use None
        max_diff_for_config = args.max_diff if args.recursive is not None else None
        ignore_file_path = args.ignore_file if args.ignore_file else None
        initialize_config(max_diff_for_config, exclude_patterns, ignore_file_path)

    try:
        if args.reset is not None:
            # Reset mode: delete skeleton files
            reset_directories = args.reset if len(args.reset) > 0 else []
            return delete_skeleton_files(reset_directories)
        elif args.compare:
            # Compare mode
            compare_files(verbose=args.verbose)
            return 0
        elif args.recursive is not None:
            # Recursive mode: process directories
            exit_code, unmatched_file_paths = process_directories_recursive(args.recursive, convert_and_compare_mdx_to_skeleton)
            
            # Save unmatched file paths to output file if specified
            if args.output is not None:
                try:
                    # Sort paths for consistent output
                    sorted_paths = sorted(set(str(path) for path in unmatched_file_paths))
                    args.output.write_text('\n'.join(sorted_paths) + '\n', encoding='utf-8')
                    print(f"Unmatched file paths saved to: {args.output}")
                except Exception as e:
                    print(f"Error writing output file {args.output}: {e}", file=sys.stderr)
                    return 1
            
            return exit_code
        elif args.input_path:
            # Single file mode
            if args.input_path.is_dir():
                print("Error: Input path is a directory. Use -r option for directory processing.", file=sys.stderr)
                return 1

            output_path, _, _ = convert_and_compare_mdx_to_skeleton(args.input_path)
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
