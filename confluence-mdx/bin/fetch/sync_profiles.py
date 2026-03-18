"""Sync profile definitions for each Confluence Space."""

from dataclasses import dataclass


@dataclass
class SyncProfile:
    """Configuration for a single Confluence Space sync target."""
    code: str
    space_key: str
    start_page_id: str


SYNC_PROFILES: dict[str, SyncProfile] = {
    "qm": SyncProfile(
        code="qm",
        space_key="QM",
        start_page_id="608501837",   # QueryPie Docs 루트
    ),
    "qcp": SyncProfile(
        code="qcp",
        space_key="QCP",
        start_page_id="",            # TBD: QCP Space 루트 페이지 ID
    ),
}
