#!/usr/bin/env python3
"""
MDX to Skeleton Converter — backward-compatible shim.

The implementation has moved to the skeleton package (skeleton/cli.py).
This file re-exports all public symbols so that existing callers
(tests, run-tests.sh, review-skeleton-diff.sh) continue to work unchanged.
"""

import sys

# Re-export all public symbols from the skeleton package
from skeleton.cli import (
    # Classes
    ContentProtector,
    ProtectedSection,
    TextProcessor,
    # Core conversion functions
    convert_mdx_to_skeleton,
    convert_and_compare_mdx_to_skeleton,
    compare_skeleton_files,
    # Line processing functions
    process_yaml_frontmatter,
    process_text_line,
    process_markdown_line,
    # Utility functions
    delete_skeleton_files,
    # Entry point
    main,
)

if __name__ == '__main__':
    sys.exit(main())
