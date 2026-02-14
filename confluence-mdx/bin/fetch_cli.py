#!/usr/bin/env python3
"""
Confluence Page Tree Generator — CLI entry point.

This script generates a list of pages from a Confluence space.
Output format: page_id \t breadcrumbs

The document processing follows 4 distinct stages:
1. API Data Collection: Fetch and save API responses to YAML files
2. Content Extraction: Extract and save page content (XHTML, HTML, ADF)
3. Attachment Download: Download attachments if specified
4. Document Listing: Generate and output a document list with breadcrumbs

Modes:
  --local: Process local files only, starting from default_start_page_id hierarchically
  --remote: Download and process via API, starting from default_start_page_id hierarchically
  --recent: Download recently modified pages, then process like --local (default)

Usage examples:
  bin/fetch_cli.py  # Same as --recent: download recent pages then process locally
  bin/fetch_cli.py --local  # Process existing local files hierarchically
  bin/fetch_cli.py --remote  # Download and process via API hierarchically
  bin/fetch_cli.py --recent  # Download recent pages then process locally
  bin/fetch_cli.py --days 14  # Fetch pages modified in last 14 days (with --recent)
  bin/fetch_cli.py --attachments  # Download page content with attachments
"""

import argparse
import logging
import sys
from pathlib import Path

# 스크립트 위치 기반 경로 상수
_SCRIPT_DIR = Path(__file__).resolve().parent   # confluence-mdx/bin/
_PROJECT_DIR = _SCRIPT_DIR.parent               # confluence-mdx/

# Ensure bin/ is on sys.path so local package imports resolve without PYTHONPATH
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from fetch.config import Config
from fetch.processor import ConfluencePageProcessor


def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate a list of pages from a Confluence space"
    )
    parser.add_argument("--space-key", default=Config().space_key,
                        help=f"Confluence space key (default: %(default)s)")
    parser.add_argument("--days", type=int, default=None,
                        help="Number of days to look back for modified pages (default: auto-detect from .fetch_state.yaml, fallback: 21)")
    parser.add_argument("--start-page-id", default=Config().default_start_page_id,
                        help="Root page ID for building breadcrumbs (default: %(default)s)")
    parser.add_argument("--base-url", default=Config().base_url, help="Confluence base URL (default: %(default)s)")
    parser.add_argument("--email", default=Config().email, help="Confluence email for authentication")
    parser.add_argument("--api-token", default=Config().api_token, help="Confluence API token for authentication")
    parser.add_argument("--attachments", action="store_true", help="Download page content with attachments")

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--local", action="store_const", dest="mode", const="local",
                            help="Process local files only, starting from default_start_page_id hierarchically")
    mode_group.add_argument("--remote", action="store_const", dest="mode", const="remote",
                            help="Download and process via API, starting from default_start_page_id hierarchically")
    mode_group.add_argument("--recent", action="store_const", dest="mode", const="recent",
                            help="Download recently modified pages, then process like --local")

    parser.add_argument("--output-dir", default=Config().default_output_dir,
                        help="Directory to store output files (default: %(default)s)")
    parser.add_argument("--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level (default: %(default)s)")
    args = parser.parse_args()

    # Set up logging configuration
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        stream=sys.stderr
    )

    # Determine mode (default to "recent" if not specified)
    mode = args.mode if args.mode else "recent"

    # Create configuration
    config = Config(
        base_url=args.base_url,
        space_key=args.space_key,
        days=args.days,
        email=args.email,
        api_token=args.api_token,
        default_output_dir=args.output_dir,
        default_start_page_id=args.start_page_id,
        download_attachments=args.attachments,
        mode=mode
    )

    # Create processor and run
    logger = logging.getLogger(__name__)
    processor = ConfluencePageProcessor(config, logger)
    processor.run()


if __name__ == "__main__":
    main()
