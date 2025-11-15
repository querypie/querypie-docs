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
from typing import List, Tuple, Optional

from skeleton_common import (
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


def compare_with_korean_skel(current_skel_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Compare current .skel.mdx file with Korean equivalent if it exists.
    If current file is not Korean, find Korean equivalent and run diff.

    Returns:
        Tuple of (should_continue, comparison_result)
        should_continue: True if it should continue processing, False if max_diff is reached and should stop
        comparison_result: 'matched' if files are identical, 'unmatched' if different, None if not compared
    """
    global _diff_count, _match_count, _max_diff, _exclude_patterns

    current_lang = extract_language_code(current_skel_path)

    # If current file is Korean, no need to compare
    if current_lang == 'ko':
        return True, None

    # Check if file path matches exclude patterns
    relative_path = get_path_without_lang_dir(current_skel_path)
    if relative_path and relative_path in _exclude_patterns:
        return True, None

    # Check if max_diff is set and already reached
    if _max_diff is not None:
        if _diff_count >= _max_diff:
            return False, None

    # Get Korean equivalent path
    korean_skel_path = get_korean_equivalent_path(current_skel_path)

    if korean_skel_path is None:
        return True, None

    # Check if Korean .skel.mdx file exists
    if not korean_skel_path.exists():
        return True, None

    # Run diff command
    try:
        # Build diff command with unified format (-U 2 for 2 lines of context)
        diff_cmd = ['diff', '-U', '2', str(korean_skel_path), str(current_skel_path)]

        # Print command with "+ " prefix
        print(f"+ {' '.join(diff_cmd)}")

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
            # Files are different, increment diff count
            _diff_count += 1

            # Print diff output
            if result.stdout:
                print(result.stdout, end='')

            # Print original .mdx file diff
            original_diff = format_diff_with_original_content(
                result.stdout,
                korean_skel_path,
                current_skel_path
            )
            if original_diff:
                print(original_diff, end='')

            # Check if max_diff reached
            if _max_diff is not None:
                if _diff_count >= _max_diff:
                    return False, 'unmatched'
            return True, 'unmatched'
        elif result.returncode == 0:
            # Files are identical, increment match count
            _match_count += 1
            return True, 'matched'

        # Print stderr if any (errors)
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)

    except Exception as e:
        print(f"Error running diff: {e}", file=sys.stderr)

    return True, None


def process_directory(directory: Path, convert_func) -> Tuple[int, int, int, int, int, List[str]]:
    """
    Process all .mdx files in a directory.
    Returns tuple of (success_count, error_count, matched_count, unmatched_count, not_compared_count, not_compared_files).
    
    Args:
        directory: Directory to process
        convert_func: Function to convert MDX to skeleton (takes Path, returns Tuple[Path, Optional[str]])
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

    # Find all .mdx files (recursively)
    mdx_files = list(directory.rglob('*.mdx'))

    # Filter out .skel.mdx files
    mdx_files = [f for f in mdx_files if not f.name.endswith('.skel.mdx')]

    if not mdx_files:
        return 0, 0, 0, 0, 0, []

    for mdx_file in mdx_files:
        # Check if max_diff reached before processing next file
        global _diff_count, _max_diff
        if _max_diff is not None and _diff_count >= _max_diff:
            break

        try:
            _, comparison_result = convert_func(mdx_file)
            success_count += 1
            
            # Count matched/unmatched/not_compared
            if comparison_result == 'matched':
                matched_count += 1
            elif comparison_result == 'unmatched':
                unmatched_count += 1
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

    return success_count, error_count, matched_count, unmatched_count, not_compared_count, not_compared_files


def process_directories_recursive(directories: List[Path], convert_func) -> int:
    """
    Process multiple directories recursively.
    If directories list is empty, uses default directories (target/ko, target/ja, target/en).
    Returns exit code (0 for success).
    
    Args:
        directories: List of directories to process
        convert_func: Function to convert MDX to skeleton (takes Path, returns Tuple[Path, Optional[str]])
    """
    if len(directories) == 0:
        # No directories specified, use defaults (Korean, Japanese, English order)
        default_dirs = [
            Path('target/ko'),
            Path('target/ja'),
            Path('target/en')
        ]
        directories = default_dirs

    total_success = 0
    total_errors = 0
    total_matched = 0
    total_unmatched = 0
    total_not_compared = 0

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
        success_count, error_count, matched_count, unmatched_count, not_compared_count, not_compared_files = process_directory(directory, convert_func)
        total_success += success_count
        total_errors += error_count
        total_matched += matched_count
        total_unmatched += unmatched_count
        total_not_compared += not_compared_count

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

    return 0


def initialize_config(max_diff: int, exclude_patterns: List[str]):
    """
    Initialize global configuration for recursive processing.
    
    Args:
        max_diff: Maximum number of diffs to output before stopping
        exclude_patterns: List of paths to exclude from diff comparison
    """
    global _diff_count, _match_count, _max_diff, _exclude_patterns
    _max_diff = max_diff
    _diff_count = 0  # Reset counter
    _match_count = 0  # Reset match counter
    # Use exclude patterns from args, or default if empty
    _exclude_patterns = exclude_patterns if exclude_patterns and len(exclude_patterns) > 0 else ['/index.skel.mdx']

