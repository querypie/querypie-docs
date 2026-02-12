#!/usr/bin/env python3
"""
Sync confluenceUrl from Korean MDX frontmatter to English/Japanese translations.

Korean MDX files contain a `confluenceUrl` field in their YAML frontmatter,
but the corresponding en/ja translation files do not. This script copies the
`confluenceUrl` value from each ko source file into the matching en/ja file,
inserting it right after the `title:` line.

Usage:
    # Individual files (en/ja paths only; ko paths are silently skipped)
    python bin/sync_confluence_url.py src/content/en/overview.mdx src/content/ja/overview.mdx

    # Recursive – default targets: src/content/en + src/content/ja
    python bin/sync_confluence_url.py -r

    # Recursive – specific directory
    python bin/sync_confluence_url.py -r src/content/en/administrator-manual

    # Dry-run (no files written)
    python bin/sync_confluence_url.py -r --dry-run
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_korean_source_path(file_path: Path) -> Optional[Path]:
    """Replace the language segment (en/ja) with 'ko' to derive the source path."""
    parts = list(file_path.parts)
    for i, part in enumerate(parts):
        if part in ('en', 'ja'):
            parts[i] = 'ko'
            return Path(*parts)
    return None


def is_ko_path(file_path: Path) -> bool:
    """Return True if *file_path* contains a 'ko' language segment."""
    return 'ko' in file_path.parts


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def _find_frontmatter_bounds(lines: List[str]) -> Optional[Tuple[int, int]]:
    """Return (start, end) line indices of the ``---`` fences, or None."""
    start: Optional[int] = None
    for i, line in enumerate(lines):
        if line.rstrip() == '---':
            if start is None:
                start = i
            else:
                return (start, i)
    return None


def extract_confluence_url(lines: List[str]) -> Optional[str]:
    """Extract the confluenceUrl value from frontmatter lines."""
    bounds = _find_frontmatter_bounds(lines)
    if bounds is None:
        return None
    start, end = bounds
    for i in range(start + 1, end):
        stripped = lines[i].strip()
        if stripped.startswith('confluenceUrl:'):
            value = stripped[len('confluenceUrl:'):].strip()
            # Strip surrounding quotes if present
            if (value.startswith("'") and value.endswith("'")) or \
               (value.startswith('"') and value.endswith('"')):
                value = value[1:-1]
            return value
    return None


def sync_confluence_url(lines: List[str], url: str) -> Tuple[List[str], bool]:
    """Insert or update ``confluenceUrl`` in *lines*.

    Returns (new_lines, changed).
    """
    bounds = _find_frontmatter_bounds(lines)
    if bounds is None:
        return lines, False

    start, end = bounds
    new_line = f"confluenceUrl: '{url}'\n"

    # Check if confluenceUrl already exists
    for i in range(start + 1, end):
        stripped = lines[i].strip()
        if stripped.startswith('confluenceUrl:'):
            existing = extract_confluence_url(lines)
            if existing == url:
                return lines, False  # already identical
            result = lines[:i] + [new_line] + lines[i + 1:]
            return result, True

    # Not present – insert after `title:` line
    for i in range(start + 1, end):
        if lines[i].strip().startswith('title:'):
            result = lines[:i + 1] + [new_line] + lines[i + 1:]
            return result, True

    # title: not found – insert as first frontmatter field
    result = lines[:start + 1] + [new_line] + lines[start + 1:]
    return result, True


def remove_confluence_url(lines: List[str]) -> Tuple[List[str], bool]:
    """Remove ``confluenceUrl`` line from frontmatter if present.

    Returns (new_lines, changed).
    """
    bounds = _find_frontmatter_bounds(lines)
    if bounds is None:
        return lines, False

    start, end = bounds
    for i in range(start + 1, end):
        if lines[i].strip().startswith('confluenceUrl:'):
            result = lines[:i] + lines[i + 1:]
            return result, True
    return lines, False


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def collect_mdx_files(directories: List[Path]) -> List[Path]:
    """Recursively collect ``*.mdx`` files (excluding ``.skel.mdx``) sorted."""
    files: List[Path] = []
    for directory in directories:
        if not directory.is_dir():
            print(f"Warning: not a directory, skipping: {directory}", file=sys.stderr)
            continue
        for p in sorted(directory.rglob('*.mdx')):
            if p.name.endswith('.skel.mdx'):
                continue
            files.append(p)
    return sorted(files)


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_file(target_path: Path, dry_run: bool = False) -> str:
    """Process a single en/ja file. Returns a status string."""
    if is_ko_path(target_path):
        return 'skipped_ko'

    ko_path = get_korean_source_path(target_path)
    if ko_path is None:
        return 'skipped_ko'  # can't determine ko path

    if not ko_path.exists():
        print(f"Warning: Korean source not found: {ko_path}", file=sys.stderr)
        return 'missing_ko'

    ko_lines = ko_path.read_text(encoding='utf-8').splitlines(keepends=True)
    ko_url = extract_confluence_url(ko_lines)

    target_lines = target_path.read_text(encoding='utf-8').splitlines(keepends=True)
    bounds = _find_frontmatter_bounds(target_lines)
    if bounds is None:
        print(f"Warning: no frontmatter in {target_path}", file=sys.stderr)
        return 'error'

    if ko_url is None:
        # ko has no confluenceUrl → remove from target if present
        new_lines, changed = remove_confluence_url(target_lines)
    else:
        new_lines, changed = sync_confluence_url(target_lines, ko_url)

    if not changed:
        return 'unchanged'

    if not dry_run:
        target_path.write_text(''.join(new_lines), encoding='utf-8')

    return 'updated'


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Sync confluenceUrl from Korean MDX frontmatter to en/ja translations',
    )
    parser.add_argument(
        'files',
        nargs='*',
        type=Path,
        help='en/ja MDX file paths to sync (ko paths are ignored)',
    )
    parser.add_argument(
        '-r', '--recursive',
        nargs='*',
        type=Path,
        metavar='DIR',
        help='Recursively process directories. Defaults to src/content/en + src/content/ja',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would change without writing files',
    )
    args = parser.parse_args()

    # Collect target files
    targets: List[Path] = []
    if args.recursive is not None:
        dirs = args.recursive if args.recursive else [
            Path('src/content/en'),
            Path('src/content/ja'),
        ]
        targets = collect_mdx_files(dirs)
    elif args.files:
        targets = args.files
    else:
        parser.print_help()
        return 1

    # Counters
    counts = {
        'updated': 0,
        'unchanged': 0,
        'skipped_ko': 0,
        'missing_ko': 0,
        'error': 0,
    }

    for path in targets:
        status = process_file(path, dry_run=args.dry_run)
        counts[status] += 1
        if status == 'updated':
            prefix = '[DRY-RUN] ' if args.dry_run else ''
            print(f"{prefix}updated: {path}")

    # Summary
    print(
        f"\nDone: {counts['updated']} updated, {counts['unchanged']} unchanged, "
        f"{counts['skipped_ko']} skipped(ko), {counts['missing_ko']} missing(ko), "
        f"{counts['error']} errors"
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
