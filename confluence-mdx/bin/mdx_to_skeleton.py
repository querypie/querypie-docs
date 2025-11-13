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
            # For images with path URLs, keep URL as-is, alt text will be processed later
            return match.group(0)
        elif is_path_url:
            # For regular links with path URLs, preserve URL
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
    Process sentences: one sentence becomes _TEXT_. (comma is included in _TEXT_)
    """
    if not text.strip():
        return text
    
    # First, protect image links: replace alt text with _TEXT_ but preserve URL
    # Pattern: ![alt text](url) where url is a path
    # We need to protect these so they don't get processed again
    image_links = []
    placeholder_counter = 0
    
    def protect_image_link(match):
        nonlocal placeholder_counter
        alt_text = match.group(1)
        url = match.group(2)
        # If URL is a path (starts with / or is an image file), preserve it
        if url.startswith('/') or '://' in url or url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
            placeholder_counter += 1
            placeholder = f"__IMAGE_LINK_{placeholder_counter}__"
            image_links.append((placeholder, f'![_TEXT_]({url})'))
            return placeholder
        return match.group(0)
    
    # Match image links: ![alt](url) and protect them
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', protect_image_link, text)
    
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
    text = re.sub(r'(?<!!)\[([^\]]*)\]', r'[_TEXT_]', text)
    
    # Process sentences: replace each sentence with _TEXT_.
    # A sentence ends with . ! ? or end of text
    # Split text into sentences while preserving structure
    # Find all text segments and replace them sentence by sentence
    
    # Split by sentence boundaries (. ! ?) but keep them
    # Pattern to match sentences: text ending with . ! ? or end of string
    def process_sentences(content):
        # First, check if content is only a placeholder (image link only)
        if re.match(r'^\s*__IMAGE_LINK_\d+__\s*$', content):
            return content
        
        # First, split content by protected placeholders to preserve them
        # Split by image link placeholders
        placeholder_pattern = r'(__IMAGE_LINK_\d+__)'
        segments = re.split(placeholder_pattern, content)
        result = []
        
        for segment in segments:
            if re.match(placeholder_pattern, segment):
                # This is a protected placeholder, keep it as-is
                result.append(segment)
            else:
                # Process this segment for sentences
                # Split by sentence-ending punctuation, but keep the punctuation
                parts = re.split(r'([.!?]\s*)', segment)
                
                i = 0
                while i < len(parts):
                    part = parts[i]
                    # Check if next part is punctuation
                    if i + 1 < len(parts) and re.match(r'^[.!?]\s*$', parts[i + 1]):
                        punctuation = parts[i + 1]
                        i += 2
                    else:
                        punctuation = ''
                        i += 1
                    
                    if not part.strip():
                        result.append(part)
                        if punctuation:
                            result.append(punctuation)
                        continue
                    
                    # Check if part contains any text (Korean, English, numbers)
                    if re.search(r'[가-힣a-zA-Z0-9]', part):
                        # Extract leading whitespace
                        leading_match = re.match(r'^(\s*)', part)
                        leading_ws = leading_match.group(1) if leading_match else ''
                        
                        # Replace entire sentence with _TEXT_ + punctuation
                        if punctuation:
                            result.append(leading_ws + '_TEXT_' + punctuation)
                        else:
                            # Check if original ended with punctuation
                            if part.rstrip().endswith(('.', '!', '?')):
                                result.append(leading_ws + '_TEXT_.')
                            else:
                                result.append(leading_ws + '_TEXT_')
                    else:
                        result.append(part)
                        if punctuation:
                            result.append(punctuation)
        
        return ''.join(result)
    
    result = process_sentences(text)
    
    # Final cleanup: merge consecutive _TEXT_ and handle spacing
    result = re.sub(r'_TEXT_\s*_TEXT_', '_TEXT_', result)
    result = re.sub(r'_TEXT_\s*([.,;:!?])', r'_TEXT_\1', result)
    result = re.sub(r'([.,;:!?])\s*_TEXT_', r'\1 _TEXT_', result)
    
    # Restore protected image links
    for placeholder, replacement in image_links:
        result = result.replace(placeholder, replacement)
    
    return result


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


def process_directory(directory: Path, recursive: bool = False) -> Tuple[int, int]:
    """
    Process all .mdx files in a directory.
    Returns tuple of (success_count, error_count).
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
        return (0, 0)
    
    for mdx_file in mdx_files:
        try:
            convert_mdx_to_skeleton(mdx_file)
            success_count += 1
        except ValueError as e:
            # Skip .skel.mdx files silently
            if '.skel.mdx' in str(e):
                continue
            print(f"{mdx_file}: {e}", file=sys.stderr)
            error_count += 1
        except Exception as e:
            print(f"{mdx_file}: {e}", file=sys.stderr)
            error_count += 1
    
    return (success_count, error_count)


def get_mdx_files(directory: Path) -> set[str]:
    """
    Get all .mdx files in a directory (recursively), excluding .skel.mdx files.
    Returns a set of relative paths (as strings) from the directory root.
    """
    if not directory.exists() or not directory.is_dir():
        return set()
    
    mdx_files = list(directory.rglob('*.mdx'))
    # Filter out .skel.mdx files
    mdx_files = [f for f in mdx_files if not f.name.endswith('.skel.mdx')]
    
    # Convert to relative paths from directory root
    relative_paths = set()
    for mdx_file in mdx_files:
        try:
            rel_path = mdx_file.relative_to(directory)
            relative_paths.add(str(rel_path))
        except ValueError:
            # If relative_to fails, use absolute path
            relative_paths.add(str(mdx_file))
    
    return relative_paths


def compare_files(verbose: bool = False):
    """
    Compare .mdx files across target/en, target/ja, and target/ko directories.
    Outputs comparison results to stdout.
    
    Args:
        verbose: If False, skip files that exist in all three languages.
                 If True, output all files.
    """
    base_dir = Path('target')
    dirs = {
        'ko': base_dir / 'ko',
        'en': base_dir / 'en',
        'ja': base_dir / 'ja',
    }
    
    # Get file lists for each directory
    file_sets = {}
    for lang, dir_path in dirs.items():
        file_sets[lang] = get_mdx_files(dir_path)
    
    # Get all unique file paths (union of all three sets)
    all_files = file_sets['ko'] | file_sets['en'] | file_sets['ja']
    
    # Sort alphabetically
    sorted_files = sorted(all_files)
    
    # Output comparison results
    for file_path in sorted_files:
        # Check existence in each directory
        ko_exists = file_path in file_sets['ko']
        en_exists = file_path in file_sets['en']
        ja_exists = file_path in file_sets['ja']
        
        # Skip if all three languages exist and not verbose
        if not verbose and ko_exists and en_exists and ja_exists:
            continue
        
        # Format output: /path/to/file.mdx ko en ja
        ko_status = 'ko' if ko_exists else '-'
        en_status = 'en' if en_exists else '-'
        ja_status = 'ja' if ja_exists else '-'
        
        # Ensure path starts with /
        output_path = file_path if file_path.startswith('/') else f'/{file_path}'
        print(f"{output_path} {ko_status} {en_status} {ja_status}")


def process_directories_recursive(directories: List[Path]) -> int:
    """
    Process multiple directories recursively.
    If directories list is empty, uses default directories (target/en, target/ja, target/ko).
    Returns exit code (0 for success).
    """
    if len(directories) == 0:
        # No directories specified, use defaults
        default_dirs = [
            Path('target/en'),
            Path('target/ja'),
            Path('target/ko')
        ]
        directories = default_dirs
    
    total_success = 0
    total_errors = 0
    
    for directory in directories:
        if not directory.exists():
            print(f"Warning: Directory not found: {directory}", file=sys.stderr)
            continue
        if not directory.is_dir():
            print(f"Warning: Path is not a directory: {directory}", file=sys.stderr)
            continue
        success_count, error_count = process_directory(directory, recursive=True)
        total_success += success_count
        total_errors += error_count
        
        # Print statistics for this directory
        print(f"{directory}: {success_count} successful, {error_count} errors")
    
    # Print overall summary statistics
    if len(directories) > 1:
        print(f"Total: {total_success} successful, {total_errors} errors")
    
    return 0


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
        help='Process directory(ies) recursively. If no directories specified, defaults to target/en, target/ja, target/ko'
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
    
    args = parser.parse_args()
    
    try:
        if args.compare:
            # Compare mode
            compare_files(verbose=args.verbose)
            return 0
        elif args.recursive is not None:
            # Recursive mode: process directories
            return process_directories_recursive(args.recursive)
        elif args.input_path:
            # Single file mode
            if args.input_path.is_dir():
                print("Error: Input path is a directory. Use -r option for directory processing.", file=sys.stderr)
                return 1
            
            output_path = convert_mdx_to_skeleton(args.input_path)
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
