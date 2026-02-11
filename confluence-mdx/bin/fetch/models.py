"""Data models for Confluence pages."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class Page:
    """Class to represent a Confluence page with its metadata and content"""
    page_id: str
    title: str
    title_orig: str
    breadcrumbs: Optional[List[str]] = None
    breadcrumbs_en: Optional[List[str]] = None
    path: Optional[List[str]] = None

    def __post_init__(self):
        if self.breadcrumbs is None:
            self.breadcrumbs = []
        if self.breadcrumbs_en is None:
            self.breadcrumbs_en = []
        if self.path is None:
            self.path = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Page':
        """Create a Page instance from a dictionary"""
        return cls(
            page_id=data.get('page_id', ''),
            title=data.get('title', ''),
            title_orig=data.get('title_orig', ''),
            breadcrumbs=data.get('breadcrumbs', []),
            breadcrumbs_en=data.get('breadcrumbs_en', []),
            path=data.get('path', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Page instance to dictionary"""
        return {
            'page_id': self.page_id,
            'title': self.title,
            'title_orig': self.title_orig,
            'breadcrumbs': self.breadcrumbs,
            'breadcrumbs_en': self.breadcrumbs_en,
            'path': self.path
        }

    def to_output_line(self) -> str:
        """Convert to output line format: page_id \t breadcrumbs \t title"""
        breadcrumbs_str = " />> ".join(self.breadcrumbs) if self.breadcrumbs else ""
        return f"{self.page_id}\t{breadcrumbs_str}\t{self.title}"
