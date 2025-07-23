#!/usr/bin/env python3
import os
import argparse
import re
from pathlib import Path

# Unicode characters to remove
ZWSP = '\u200b'  # Zero Width Space
LRM = '\u200e'   # Left-to-Right Mark
HANGUL_FILLER = '\u3164'  # Hangul Filler

def find_files_with_chars(directory, extensions, chars, exclude_dirs=None):
    """
    Find files containing any of the specified characters.
    
    Args:
        directory: Root directory to search
        extensions: List of file extensions to search
        chars: List of characters to search for
        exclude_dirs: List of directories to exclude from search
    
    Returns:
        List of file paths containing any of the characters
    """
    files_with_chars = []
    exclude_dirs = exclude_dirs or []
    
    for ext in extensions:
        for file_path in Path(directory).rglob(f'*.{ext}'):
            # Skip files in excluded directories
            if any(exclude_dir in str(file_path) for exclude_dir in exclude_dirs):
                continue
            
            # Print the name of the document being examined
            print(f"Examining document: {file_path}")
                
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if any(char in content for char in chars):
                    files_with_chars.append(file_path)
                    print(f"  Hidden characters found: Yes")
                else:
                    print(f"  Hidden characters found: No")
    
    return files_with_chars

def remove_chars_from_file(file_path, chars):
    """
    Remove specified characters from a file.
    
    Args:
        file_path: Path to the file
        chars: List of characters to remove
    
    Returns:
        Tuple of (number of replacements, updated content)
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original_content = content
    for char in chars:
        content = content.replace(char, '')
    
    replacements = len(original_content) - len(content)
    
    return replacements, content

def main():
    parser = argparse.ArgumentParser(description='Find and remove specified Unicode characters from files')
    parser.add_argument('--dir', default='.', help='Root directory to search (default: current directory)')
    parser.add_argument('--extensions', default='xhtml,md,mdx', help='Comma-separated list of file extensions to search (default: md,mdx)')
    parser.add_argument('--exclude-dirs', default='node_modules', help='Comma-separated list of directories to exclude (default: node_modules)')
    parser.add_argument('--dry-run', action='store_true', help='Only find files, don\'t modify them')
    args = parser.parse_args()
    
    extensions = args.extensions.split(',')
    exclude_dirs = args.exclude_dirs.split(',')
    chars = [ZWSP, LRM, HANGUL_FILLER]
    
    print(f"Searching for files with Unicode characters: ZWSP (\\u200b), LRM (\\u200e), HANGUL_FILLER (\\u3164)")
    print(f"Excluding directories: {', '.join(exclude_dirs)}")
    files = find_files_with_chars(args.dir, extensions, chars, exclude_dirs)
    
    if not files:
        print("No files found containing the specified characters.")
        return
    
    print(f"Found {len(files)} files containing the specified characters.")
    
    if args.dry_run:
        print("Dry run mode - no files were modified.")
        return
    
    total_replacements = 0
    modified_files = 0
    
    for file_path in files:
        replacements, updated_content = remove_chars_from_file(file_path, chars)
        
        if replacements > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"Modified {file_path}: removed {replacements} characters")
            total_replacements += replacements
            modified_files += 1
    
    print(f"Summary: Modified {modified_files} files, removed {total_replacements} characters in total.")

if __name__ == '__main__':
    main()