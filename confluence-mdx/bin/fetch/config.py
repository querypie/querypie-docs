"""Centralized configuration management."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Resolve project root (confluence-mdx/) from this module's location
# bin/fetch/config.py -> .parent=fetch/ -> .parent=bin/ -> .parent=confluence-mdx/
_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent  # confluence-mdx/


@dataclass
class Config:
    """Centralized configuration management"""
    base_url: str = "https://querypie.atlassian.net/wiki"
    space_key: str = "QM"  # Confluence space key
    days: Optional[int] = None  # Number of days to look back (None = auto-detect from .fetch_state.yaml)
    default_start_page_id: str = "608501837"  # Root Page ID of "QueryPie Docs" (for breadcrumbs)
    quick_start_page_id: str = "544375784"  # QueryPie Overview having less children
    default_output_dir: str = "var"
    cache_dir: str = "cache"
    translations_file: str = "etc/korean-titles-translations.txt"
    email: Optional[str] = None
    api_token: Optional[str] = None
    download_attachments: bool = False
    mode: str = "recent"  # Mode: "local", "remote", or "recent"

    def __post_init__(self):
        if self.email is None:
            self.email = os.environ.get('ATLASSIAN_USERNAME', 'your-email@example.com')
        if self.api_token is None:
            self.api_token = os.environ.get('ATLASSIAN_TOKEN', 'your-api-token')

        # Resolve relative paths against project root (confluence-mdx/)
        for field in ('default_output_dir', 'cache_dir', 'translations_file'):
            value = getattr(self, field)
            if not os.path.isabs(value):
                setattr(self, field, str(_PROJECT_DIR / value))
