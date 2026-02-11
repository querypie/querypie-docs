#!/usr/bin/env python3
"""Deprecated: Use fetch_cli.py instead."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

print("WARNING: pages_of_confluence.py is deprecated. Use fetch_cli.py instead.", file=sys.stderr)

from fetch_cli import main

main()
