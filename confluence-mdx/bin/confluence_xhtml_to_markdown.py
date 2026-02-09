#!/usr/bin/env python3
"""
Confluence XHTML to Markdown Converter — backward-compatible shim.

The implementation has moved to the converter package (converter/cli.py).
This file preserves the original entry point so that existing callers
(entrypoint.sh, run-tests.sh, reverse_sync_cli.py) continue to work unchanged.
"""

import sys
from converter.cli import main

if __name__ == '__main__':
    sys.exit(main())
