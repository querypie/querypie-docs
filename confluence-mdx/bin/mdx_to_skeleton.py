#!/usr/bin/env python3
"""
MDX to Skeleton Converter

This script converts MDX files to skeleton format by preserving markdown structure
and replacing text content with _TEXT_ placeholder.

Usage:
    python mdx_to_skeleton.py path/to/filename.mdx
    # Creates path/to/filename.skel.mdx
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict


class ProtectedSection:
    """Represents a protected section that should not be modified"""
    def __init__(self, content: str, placeholder: str):
        self.content = content
        self.placeholder = placeholder


def extract_yaml_frontmatter(text: str) -> Tuple[str, ProtectedSection]:
    """Extract YAML frontmatter and replace with placeholder"""
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
    """Extract code blocks and replace with placeholders"""
    code_blocks: List[ProtectedSection] = []
    placeholder_counter = 0
    
    # Pattern to match code blocks: ```language\ncontent\n```
    pattern = r'```(\w*)\n(.*?)```'
    
    def replace_code_block(match):
        nonlocal placeholder_counter
        language = match.group(1) or ""
        content = match.group(2)
        placeholder_counter += 1
        placeholder = f"__CODE_BLOCK_{placeholder_counter}__"
        protected = ProtectedSection(content, placeholder)
        code_blocks.append(protected)
        return f"```{language}\n{placeholder}\n```"
    
    modified_text = re.sub(pattern, replace_code_block, text, flags=re.DOTALL)
    return modified_text, code_blocks


def extract_inline_code(text: str) -> Tuple[str, List[ProtectedSection]]:
    """Extract inline code and replace with placeholders"""
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
    """Extract URLs from links and images, preserve them"""
    urls: List[ProtectedSection] = []
    placeholder_counter = 0
    
    # Pattern to match URLs in markdown links and images
    # Match [text](url) or ![alt](url)
    pattern = r'(!?\[[^\]]*\]\()([^)]+)(\))'
    
    def replace_url(match):
        nonlocal placeholder_counter
        prefix = match.group(1)  # [text]( or ![alt](
        url = match.group(2)
        suffix = match.group(3)  # )
        # Only preserve URLs that look like paths or full URLs
        if url.startswith('/') or '://' in url or url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
            placeholder_counter += 1
            placeholder = f"__URL_{placeholder_counter}__"
            protected = ProtectedSection(url, placeholder)
            urls.append(protected)
            return prefix + placeholder + suffix
        return match.group(0)  # Keep as is if not a URL
    
    modified_text = re.sub(pattern, replace_url, text)
    return modified_text, urls


def extract_html_entities(text: str) -> Tuple[str, List[ProtectedSection]]:
    """Extract HTML entities and preserve them"""
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
    """Restore protected sections from placeholders"""
    for section in sections:
        text = text.replace(section.placeholder, section.content)
    return text


def process_text_line(line: str) -> str:
    """
    Process a line of text, replacing content with _TEXT_ while preserving structure.
    """
    # Skip empty lines
    if not line.strip():
        return line
    
    # Preserve import statements
    if line.strip().startswith('import '):
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
                tag = line[i:tag_end+1]
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
    """Process a markdown line, preserving structure"""
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


def replace_text_in_content(text: str) -> str:
    """
    Replace text content with _TEXT_ while preserving markdown formatting markers.
    """
    if not text.strip():
        return text
    
    # Preserve bold markers **text** or __text__
    text = re.sub(r'\*\*([^*]+)\*\*', r'**_TEXT_**', text)
    text = re.sub(r'__([^_]+)__', r'__TEXT__', text)
    
    # Preserve italic markers *text* or _text_ (but not if part of ** or __)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'*_TEXT_*', text)
    text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'_TEXT_', text)
    
    # Preserve link/image structure [text] or ![alt]
    text = re.sub(r'!\[([^\]]*)\]', r'![_TEXT_]', text)
    text = re.sub(r'(?<!!)\[([^\]]*)\]', r'[_TEXT_]', text)
    
    # Replace remaining text sequences
    # Match words (Korean, English, Japanese characters, numbers)
    # But preserve punctuation and whitespace structure
    words = re.findall(r'[가-힣a-zA-Z0-9]+', text)
    if words:
        # Replace each word with _TEXT_, but keep punctuation
        text = re.sub(r'[가-힣a-zA-Z0-9]+', '_TEXT_', text)
        # Clean up multiple consecutive _TEXT_
        text = re.sub(r'(_TEXT_\s*)+', '_TEXT_', text)
        # Clean up spacing around punctuation
        text = re.sub(r'_TEXT_([.,;:!?])', r'_TEXT_\1', text)
        text = re.sub(r'([.,;:!?])\s*_TEXT_', r'\1 _TEXT_', text)
    
    return text


def convert_mdx_to_skeleton(input_path: Path) -> Path:
    """
    Convert MDX file to skeleton format.
    Returns path to output file.
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
    
    for line in lines:
        # Handle YAML frontmatter
        if line.strip() == '---':
            processed_lines.append(line)
            in_yaml = not in_yaml
            continue
        
        if in_yaml or (yaml_section and yaml_section.placeholder in line):
            # Process YAML frontmatter: preserve structure but replace content
            if yaml_section and yaml_section.placeholder in line:
                # Replace placeholder with processed YAML content
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
            else:
                # Process YAML line: preserve key: structure, replace value
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
    
    return output_path


def process_directory(directory: Path, recursive: bool = False) -> int:
    """
    Process all .mdx files in a directory.
    Returns number of successfully processed files.
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    success_count = 0
    error_count = 0
    
    # Find all .mdx files
    if recursive:
        mdx_files = list(directory.rglob('*.mdx'))
    else:
        mdx_files = list(directory.glob('*.mdx'))
    
    # Filter out .skel.mdx files
    mdx_files = [f for f in mdx_files if not f.name.endswith('.skel.mdx')]
    
    if not mdx_files:
        print(f"No .mdx files found in {directory}", file=sys.stderr)
        return 0
    
    print(f"Found {len(mdx_files)} .mdx file(s) to process...")
    
    for mdx_file in mdx_files:
        try:
            output_path = convert_mdx_to_skeleton(mdx_file)
            print(f"Successfully created: {output_path}")
            success_count += 1
        except ValueError as e:
            # Skip .skel.mdx files silently
            if '.skel.mdx' in str(e):
                continue
            print(f"Error processing {mdx_file}: {e}", file=sys.stderr)
            error_count += 1
        except Exception as e:
            print(f"Error processing {mdx_file}: {e}", file=sys.stderr)
            error_count += 1
    
    print(f"\nProcessed: {success_count} successful, {error_count} errors")
    return success_count


def main():
    parser = argparse.ArgumentParser(
        description='Convert MDX file(s) to skeleton format by replacing text with _TEXT_'
    )
    parser.add_argument(
        'input_path',
        type=Path,
        help='Path to input MDX file or directory (if -r is specified)'
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Process directory recursively (treat input_path as directory)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.recursive:
            # Treat input_path as directory
            process_directory(args.input_path, recursive=True)
            return 0
        else:
            # Check if input_path is a directory or file
            if args.input_path.is_dir():
                print("Error: Input path is a directory. Use -r option for directory processing.", file=sys.stderr)
                return 1
            
            # Treat as single file
            output_path = convert_mdx_to_skeleton(args.input_path)
            print(f"Successfully created: {output_path}")
            return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
