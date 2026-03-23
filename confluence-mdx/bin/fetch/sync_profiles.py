"""Sync profile definitions for each Confluence Space."""

from dataclasses import dataclass


@dataclass
class SyncProfile:
    """Configuration for a single Confluence Space sync target."""
    code: str
    space_key: str
    start_page_id: str
    root_content_type: str = "page"
    """Confluence content type of the root page ('page' or 'folder').

    Used by Stage 1 when page.v2.yaml does not yet exist (e.g. first run on a
    clean environment) so the correct API endpoint is called from the start.
    """


SYNC_PROFILES: dict[str, SyncProfile] = {
    "qm": SyncProfile(
        code="qm",
        space_key="QM",
        start_page_id="608501837",   # QueryPie Docs 루트
    ),
    "qcp": SyncProfile(
        code="qcp",
        space_key="QCP",
        start_page_id="887849063",   # QCP Space 루트 (https://querypie.atlassian.net/wiki/spaces/QCP/folder/887849063)
        root_content_type="folder",  # 887849063 is a Confluence folder, not a page
    ),
}
