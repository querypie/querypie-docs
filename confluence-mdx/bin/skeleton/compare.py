#!/usr/bin/env python3
"""
Skeleton Compare Module

This module handles the --compare functionality for comparing .mdx files
across different language directories (target/ko, target/ja, target/en).
"""

from pathlib import Path

# Resolve project root (confluence-mdx/) from this module's location
# bin/skeleton/compare.py -> .parent=skeleton/ -> .parent=bin/ -> .parent=confluence-mdx/
_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent  # confluence-mdx/


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
    base_dir = _PROJECT_DIR / 'target'
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

