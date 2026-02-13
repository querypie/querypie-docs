#!/usr/bin/env python3
"""
Skeleton Diff Module

This module handles recursive processing and comparison of skeleton MDX files.
It provides functions for comparing skeleton files across different languages
and processing directories recursively.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set

# Resolve project root (confluence-mdx/) from this module's location
# bin/skeleton/diff.py -> .parent=skeleton/ -> .parent=bin/ -> .parent=confluence-mdx/
_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent  # confluence-mdx/

try:
    import yaml
except ImportError:
    yaml = None

from skeleton.common import (
    extract_language_code,
    get_korean_equivalent_path,
    get_path_without_lang_dir,
    get_original_mdx_path,
)

# Global diff counter for tracking the number of diffs found
_diff_count: int = 0
_match_count: int = 0  # Counter for matching skeleton diffs
_max_diff: Optional[int] = None  # Will be set to 5 (default) when --recursive is used
_exclude_patterns: List[str] = ['/index.skel.mdx']  # Default exclude patterns
_ignore_rules: Dict[str, Set[int]] = {}  # Dictionary mapping file paths to sets of line numbers to ignore


def format_diff_with_original_content(
        diff_output: str,
        left_skel_path: Path,
        right_skel_path: Path
) -> str:
    """
    Formats diff output by replacing .skel.mdx file paths with .mdx paths
    and replacing diff content lines with original .mdx file content.

    Converts skeleton diff (with _TEXT_ placeholders) to original content diff.
    """
    # Get original .mdx file paths
    left_mdx_path = get_original_mdx_path(left_skel_path)
    right_mdx_path = get_original_mdx_path(right_skel_path)

    if left_mdx_path is None or right_mdx_path is None:
        return diff_output

    # Read original .mdx files
    try:
        left_lines = left_mdx_path.read_text(encoding='utf-8').split('\n')
        right_lines = right_mdx_path.read_text(encoding='utf-8').split('\n')
    except FileNotFoundError:
        return diff_output

    # Unified format chunk header pattern: @@ -start,count +start,count @@
    chunk_header_pattern = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')

    result_lines = []
    lines = diff_output.split('\n')
    left_line_num = None
    right_line_num = None

    for line in lines:
        # Replace file paths in headers
        if line.startswith('--- '):
            result_lines.append(line.replace(str(left_skel_path), str(left_mdx_path)))
            continue
        elif line.startswith('+++ '):
            result_lines.append(line.replace(str(right_skel_path), str(right_mdx_path)))
            continue

        # Process chunk header: initialize line number tracking
        match = chunk_header_pattern.match(line)
        if match:
            result_lines.append(line)
            left_line_num = int(match.group(1))
            right_line_num = int(match.group(3))
            continue

        # Process content lines within a chunk
        if left_line_num is not None and right_line_num is not None:
            if line.startswith('-'):
                # Deleted line from left file
                if 0 < left_line_num <= len(left_lines):
                    result_lines.append('-' + left_lines[left_line_num - 1])
                else:
                    result_lines.append(line)
                left_line_num += 1
            elif line.startswith('+'):
                # Added line to right file
                if 0 < right_line_num <= len(right_lines):
                    result_lines.append('+' + right_lines[right_line_num - 1])
                else:
                    result_lines.append(line)
                right_line_num += 1
            elif line.startswith(' '):
                # Context line (common to both files)
                if 0 < left_line_num <= len(left_lines):
                    result_lines.append(' ' + left_lines[left_line_num - 1])
                else:
                    result_lines.append(line)
                left_line_num += 1
                right_line_num += 1
            else:
                # Empty line or end of chunk - keep as is
                result_lines.append(line)
        else:
            # Outside chunk - keep as is
            result_lines.append(line)

    return '\n'.join(result_lines)


def load_ignore_rules(ignore_file_path: Optional[Path] = None) -> Dict[str, Set[int]]:
    """
    Load ignore rules from YAML file.
    
    Args:
        ignore_file_path: Path to ignore_skeleton_diff.yaml file. If None, uses default location.
    
    Returns:
        Dictionary mapping file paths (including target/{lang}/ prefix) to sets of line numbers to ignore.
    """
    if yaml is None:
        print("Warning: PyYAML not installed. Ignore rules will not be loaded.", file=sys.stderr)
        return {}
    
    if ignore_file_path is None:
        # Default location: same directory as this script
        script_dir = Path(__file__).parent
        ignore_file_path = script_dir / 'ignore_rules.yaml'
    
    if not ignore_file_path.exists():
        # File doesn't exist, return empty rules
        return {}
    
    try:
        with open(ignore_file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'ignores' not in data:
            return {}
        
        ignore_rules = {}
        for rule in data.get('ignores', []):
            file_path = rule.get('file')
            line_numbers = rule.get('line_numbers', [])
            
            if file_path:
                # Normalize path separators (use forward slashes)
                file_path = file_path.replace('\\', '/')
                # Remove leading slash if present (to handle both formats)
                if file_path.startswith('/'):
                    file_path = file_path[1:]
                
                # Convert line_numbers to set
                ignore_rules[file_path] = set(line_numbers)
        
        return ignore_rules
    except Exception as e:
        print(f"Warning: Failed to load ignore rules from {ignore_file_path}: {e}", file=sys.stderr)
        return {}


def filter_diff_output(
    diff_output: str,
    file_path: str,
    ignore_rules: Dict[str, Set[int]]
) -> str:
    """
    Filter diff output by removing lines that match ignore rules.
    
    Args:
        diff_output: Original diff output (unified format)
        file_path: File path including target/{lang}/ prefix (e.g., target/ja/path/to/file.mdx)
        ignore_rules: Dictionary mapping file paths to sets of line numbers to ignore
    
    Returns:
        Filtered diff output with ignored lines removed. Returns empty string if all differences are ignored.
    """
    # Normalize file path (use forward slashes, extract target/{lang}/... portion)
    file_path = file_path.replace('\\', '/')
    target_match = re.search(r'target/(?:ko|en|ja)/', file_path)
    if target_match:
        file_path = file_path[target_match.start():]
    elif file_path.startswith('/'):
        file_path = file_path[1:]

    # Get ignore line numbers for this file
    ignore_lines = ignore_rules.get(file_path, set())
    
    if not ignore_lines:
        # No ignore rules for this file
        return diff_output
    
    # Unified format chunk header pattern: @@ -start,count +start,count @@
    chunk_header_pattern = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
    
    result_lines = []
    lines = diff_output.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Keep file headers
        if line.startswith('--- ') or line.startswith('+++ '):
            result_lines.append(line)
            i += 1
            continue
        
        # Process chunk header
        match = chunk_header_pattern.match(line)
        if match:
            chunk_start_left = int(match.group(1))
            chunk_start_right = int(match.group(3))
            left_line_num = chunk_start_left
            right_line_num = chunk_start_right
            
            # Collect chunk lines
            chunk_lines = [line]
            chunk_has_non_ignored = False
            i += 1
            
            # Process chunk content
            while i < len(lines):
                chunk_line = lines[i]
                
                # Check if we've reached the end of the chunk
                if chunk_header_pattern.match(chunk_line):
                    break
                if chunk_line.startswith('--- ') or chunk_line.startswith('+++ '):
                    break
                
                # Process chunk content lines
                if chunk_line.startswith('-'):
                    # Deleted line from left file
                    if left_line_num not in ignore_lines:
                        chunk_has_non_ignored = True
                        chunk_lines.append(chunk_line)
                    left_line_num += 1
                elif chunk_line.startswith('+'):
                    # Added line to right file
                    if right_line_num not in ignore_lines:
                        chunk_has_non_ignored = True
                        chunk_lines.append(chunk_line)
                    right_line_num += 1
                elif chunk_line.startswith(' '):
                    # Context line - keep if there are non-ignored changes in this chunk
                    chunk_lines.append(chunk_line)
                    left_line_num += 1
                    right_line_num += 1
                else:
                    # Empty line or other content
                    chunk_lines.append(chunk_line)
                
                i += 1
            
            # Only add chunk if it has non-ignored changes
            if chunk_has_non_ignored:
                result_lines.extend(chunk_lines)
            # Otherwise, skip the entire chunk
            
            continue
        
        # Lines outside chunks (shouldn't happen in unified format, but handle just in case)
        result_lines.append(line)
        i += 1
    
    filtered_output = '\n'.join(result_lines)
    
    # If only file headers remain, return empty string
    non_header_lines = [l for l in filtered_output.split('\n') if l and not l.startswith('--- ') and not l.startswith('+++ ')]
    if not non_header_lines:
        return ''
    
    return filtered_output


def _compare_two_skeleton_files(
    korean_skel_path: Path,
    translation_skel_path: Path,
    translation_mdx_path: Path
) -> Tuple[bool, Optional[str], Optional[Path]]:
    """
    Internal function to compare two skeleton files.
    
    Args:
        korean_skel_path: Path to the Korean skeleton MDX file
        translation_skel_path: Path to the translation skeleton MDX file
        translation_mdx_path: Path to the original translation MDX file (for error reporting)
    
    Returns:
        Tuple of (should_continue, comparison_result, unmatched_file_path)
    """
    global _diff_count, _match_count, _max_diff, _ignore_rules
    
    # Check if max_diff is set and already reached
    if _max_diff is not None:
        if _diff_count >= _max_diff:
            return False, None, None
    
    # Run diff command
    try:
        # Build diff command with unified format (-U 2 for 2 lines of context, -b to ignore whitespace amount differences)
        # Note: -b ignores amount of whitespace but preserves line breaks and whitespace presence/absence
        diff_cmd = ['diff', '-u', '-U', '2', '-b', str(korean_skel_path), str(translation_skel_path)]
        
        # Run diff and capture output
        result = subprocess.run(
            diff_cmd,
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        # Check if files are different (exit code 1 means differences found)
        # Exit code 0 means files are identical
        if result.returncode == 1:
            # Get file path for ignore rules (use .mdx path, not .skel.mdx)
            # Use full path including target/{lang}/ prefix
            file_path_for_ignore = str(translation_mdx_path)
            
            # Filter diff output using ignore rules
            filtered_diff = result.stdout
            if file_path_for_ignore and _ignore_rules:
                filtered_diff = filter_diff_output(result.stdout, file_path_for_ignore, _ignore_rules)
            
            # Check if filtered diff is empty (all differences were ignored)
            # Remove file headers to check if there's actual content
            filtered_content = '\n'.join([l for l in filtered_diff.split('\n') 
                                         if l and not l.startswith('--- ') and not l.startswith('+++ ')])
            
            if filtered_content.strip():
                # Files are different (after filtering), increment diff count
                _diff_count += 1
                
                # Print command with "+ " prefix (only when there are actual differences)
                print(f"+ {' '.join(diff_cmd)}")
                
                # Print filtered diff output
                print(filtered_diff, end='')
                
                # Print original .mdx file diff (also filtered)
                original_diff = format_diff_with_original_content(
                    filtered_diff,
                    korean_skel_path,
                    translation_skel_path
                )
                if original_diff:
                    print(original_diff, end='')
            else:
                # All differences were ignored, treat as matched
                _match_count += 1
                return True, 'matched', None
            
            # Check if max_diff reached
            if _max_diff is not None:
                if _diff_count >= _max_diff:
                    return False, 'unmatched', translation_mdx_path
            return True, 'unmatched', translation_mdx_path
        elif result.returncode == 0:
            # Files are identical, increment match count
            _match_count += 1
            return True, 'matched', None
        
        # Print stderr if any (errors)
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
    
    except Exception as e:
        print(f"Error running diff: {e}", file=sys.stderr)
    
    return True, None, None


def compare_with_korean_skel(current_skel_path: Path) -> Tuple[bool, Optional[str], Optional[Path]]:
    """
    Compare current .skel.mdx file with Korean equivalent if it exists.
    This function only performs comparison and does not modify or regenerate skeleton files.
    
    Args:
        current_skel_path: Path to the current .skel.mdx file to compare

    Returns:
        Tuple of (should_continue, comparison_result, unmatched_file_path)
        - should_continue: True if it should continue processing, False if max_diff is reached and should stop
        - comparison_result: 'matched' if files are identical, 'unmatched' if different, None if not compared
        - unmatched_file_path: Path to the unmatched .mdx file (with target/{lang} prefix) if unmatched, None otherwise
    """
    global _diff_count, _match_count, _max_diff, _ignore_rules

    current_lang = extract_language_code(current_skel_path)

    # If current file is Korean, no need to compare
    if current_lang == 'ko':
        return True, None, None

    # Check if file path matches exclude patterns
    if should_exclude_file(current_skel_path):
        return True, None, None

    # Check if max_diff is set and already reached
    if _max_diff is not None:
        if _diff_count >= _max_diff:
            return False, None, None

    # Get Korean equivalent path
    korean_skel_path, korean_exists = get_korean_equivalent_path(current_skel_path)

    if korean_skel_path is None:
        return True, None, None

    # Check if skeleton files exist
    if not current_skel_path.exists():
        return True, None, None
    if not korean_exists:
        return True, None, None

    # Get the original .mdx file path for comparison
    current_mdx_path = get_original_mdx_path(current_skel_path)
    if current_mdx_path is None:
        return True, None, None

    # Use the common comparison function
    return _compare_two_skeleton_files(
        korean_skel_path,
        current_skel_path,
        current_mdx_path
    )


def process_directory(directory: Path, convert_func) -> Tuple[int, int, int, int, int, List[str], List[Path]]:
    """
    Process all .mdx files in a directory.
    Returns tuple of (success_count, error_count, matched_count, unmatched_count, not_compared_count, not_compared_files, unmatched_file_paths).
    
    Args:
        directory: Directory to process
        convert_func: Function to convert MDX to skeleton (takes Path, returns Tuple[Path, Optional[str], Optional[Path]])
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    success_count = 0
    error_count = 0
    matched_count = 0
    unmatched_count = 0
    not_compared_count = 0
    not_compared_files = []  # Track files that were not compared
    unmatched_file_paths = []  # Track paths of unmatched files

    # Find all .mdx files (recursively)
    mdx_files = list(directory.rglob('*.mdx'))

    # Filter out .skel.mdx files
    mdx_files = [f for f in mdx_files if not f.name.endswith('.skel.mdx')]

    if not mdx_files:
        return 0, 0, 0, 0, 0, [], []

    for mdx_file in mdx_files:
        # Check if max_diff reached before processing next file
        global _diff_count, _max_diff
        if _max_diff is not None and _diff_count >= _max_diff:
            break

        try:
            _, comparison_result, unmatched_file_path = convert_func(mdx_file)
            success_count += 1
            
            # Count matched/unmatched/not_compared
            if comparison_result == 'matched':
                matched_count += 1
            elif comparison_result == 'unmatched':
                unmatched_count += 1
                # Collect unmatched file path if available
                if unmatched_file_path is not None:
                    unmatched_file_paths.append(unmatched_file_path)
            elif comparison_result is None:
                # Comparison was not performed (e.g., Korean file, no Korean equivalent, etc.)
                not_compared_count += 1
                # Get relative path for display
                try:
                    rel_path = mdx_file.relative_to(directory)
                    not_compared_files.append(str(rel_path))
                except ValueError:
                    not_compared_files.append(str(mdx_file))

            # Check again after processing (compare_with_korean_skel may have incremented _diff_count)
            if _max_diff is not None and _diff_count >= _max_diff:
                break
        except ValueError as e:
            # Skip .skel.mdx files silently
            if '.skel.mdx' in str(e):
                continue
            print(f"{mdx_file}: {e}", file=sys.stderr)
            error_count += 1
        except Exception as e:
            print(f"{mdx_file}: {e}", file=sys.stderr)
            error_count += 1

    return success_count, error_count, matched_count, unmatched_count, not_compared_count, not_compared_files, unmatched_file_paths


def process_directories_recursive(directories: List[Path], convert_func) -> Tuple[int, List[Path]]:
    """
    Process multiple directories recursively.
    If directories list is empty, uses default directories (target/ko, target/ja, target/en).
    Returns tuple of (exit_code, unmatched_file_paths).
    
    Args:
        directories: List of directories to process
        convert_func: Function to convert MDX to skeleton (takes Path, returns Tuple[Path, Optional[str], Optional[Path]])
    
    Returns:
        Tuple of (exit_code, unmatched_file_paths)
        - exit_code: Exit code (0 for success)
        - unmatched_file_paths: List of paths to unmatched .mdx files (with target/{lang} prefix)
    """
    if len(directories) == 0:
        # No directories specified, use defaults (Korean, Japanese, English order)
        default_dirs = [
            _PROJECT_DIR / 'target/ko',
            _PROJECT_DIR / 'target/ja',
            _PROJECT_DIR / 'target/en',
        ]
        directories = default_dirs

    total_success = 0
    total_errors = 0
    total_matched = 0
    total_unmatched = 0
    total_not_compared = 0
    all_unmatched_file_paths = []  # Collect all unmatched file paths

    for directory in directories:
        # Check if max_diff reached before processing next directory
        global _diff_count, _max_diff
        if _max_diff is not None and _diff_count >= _max_diff:
            break

        if not directory.exists():
            print(f"Warning: Directory not found: {directory}", file=sys.stderr)
            continue
        if not directory.is_dir():
            print(f"Warning: Path is not a directory: {directory}", file=sys.stderr)
            continue
        success_count, error_count, matched_count, unmatched_count, not_compared_count, not_compared_files, unmatched_file_paths = process_directory(directory, convert_func)
        total_success += success_count
        total_errors += error_count
        total_matched += matched_count
        total_unmatched += unmatched_count
        total_not_compared += not_compared_count
        all_unmatched_file_paths.extend(unmatched_file_paths)

        # Print statistics for this directory
        # Verify: converted = matched + unmatched + not_compared
        print(f"{directory}: {success_count} converted, {error_count} errors, {matched_count} matched, {unmatched_count} unmatched, {not_compared_count} not_compared")
        
        # Print not_compared files if any
        if not_compared_files:
            print(f"  Not compared files ({len(not_compared_files)}):")
            for file_path in sorted(not_compared_files):
                print(f"    - {file_path}")

        # Check again after processing directory
        if _max_diff is not None and _diff_count >= _max_diff:
            break

    # Print overall summary statistics
    if len(directories) > 1:
        print(f"Total: {total_success} converted, {total_errors} errors, {total_matched} matched, {total_unmatched} unmatched, {total_not_compared} not_compared")

    return 0, all_unmatched_file_paths


def should_exclude_file(file_path: Path) -> bool:
    """
    Check if a file should be excluded from comparison based on exclude patterns.
    
    Args:
        file_path: Path to the file to check (can be .mdx or .skel.mdx)
    
    Returns:
        True if the file should be excluded, False otherwise
    """
    global _exclude_patterns
    
    # Convert .mdx to .skel.mdx path for pattern matching
    if file_path.name.endswith('.mdx') and not file_path.name.endswith('.skel.mdx'):
        # Create .skel.mdx path for pattern matching
        skel_path = file_path.parent / f"{file_path.stem}.skel.mdx"
    else:
        skel_path = file_path
    
    # Get relative path without lang dir
    relative_path = get_path_without_lang_dir(skel_path)
    if relative_path and relative_path in _exclude_patterns:
        return True
    
    return False


def initialize_config(max_diff: Optional[int], exclude_patterns: List[str], ignore_file_path: Optional[Path] = None):
    """
    Initialize global configuration for recursive processing.
    
    Args:
        max_diff: Maximum number of diffs to output before stopping (None for single file mode)
        exclude_patterns: List of paths to exclude from diff comparison
        ignore_file_path: Path to ignore_skeleton_diff.yaml file. If None, uses default location.
    """
    global _diff_count, _match_count, _max_diff, _exclude_patterns, _ignore_rules
    _max_diff = max_diff
    _diff_count = 0  # Reset counter
    _match_count = 0  # Reset match counter
    # Use exclude patterns from args, or default if empty
    _exclude_patterns = exclude_patterns if exclude_patterns and len(exclude_patterns) > 0 else ['/index.skel.mdx']
    # Load ignore rules
    _ignore_rules = load_ignore_rules(ignore_file_path)

