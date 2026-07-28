"""Data models for Confluence content."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class ContentRef:
    """A typed reference returned by the Confluence direct-children API."""

    id: str
    type: str
    title: str = ""
    child_position: int = 0


@dataclass
class ContentNode:
    """A page or folder represented in the serialized content catalog."""

    page_id: str
    title: str
    title_orig: str
    content_type: str = "page"
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
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentNode':
        """Create a content node from a catalog dictionary."""
        return cls(
            page_id=data.get('page_id', ''),
            title=data.get('title', ''),
            title_orig=data.get('title_orig', ''),
            content_type=data.get('type', data.get('content_type', 'page')),
            breadcrumbs=data.get('breadcrumbs', []),
            breadcrumbs_en=data.get('breadcrumbs_en', []),
            path=data.get('path', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Page instance to dictionary"""
        return {
            'page_id': self.page_id,
            'type': self.content_type,
            'title': self.title,
            'title_orig': self.title_orig,
            'breadcrumbs': self.breadcrumbs,
            'breadcrumbs_en': self.breadcrumbs_en,
            'path': self.path
        }

    def to_output_line(self) -> str:
        """Convert to output line format: page_id \t breadcrumbs \t title."""
        breadcrumbs_str = " />> ".join(self.breadcrumbs) if self.breadcrumbs else ""
        return f"{self.page_id}\t{breadcrumbs_str}\t{self.title}"


# Backward-compatible import for callers that still refer to the old model name.
Page = ContentNode
