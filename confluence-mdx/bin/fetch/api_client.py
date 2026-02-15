"""Confluence REST API client."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Protocol
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

from fetch.config import Config
from fetch.exceptions import ApiError


class ApiClientProtocol(Protocol):
    """Protocol for API client operations"""

    def make_request(self, url: str, description: str) -> Optional[Dict]:
        ...

    def get_page_data(self, page_id: str) -> Optional[Dict]:
        ...

    def get_child_pages(self, page_id: str) -> Optional[Dict]:
        ...

    def get_attachments(self, page_id: str) -> Optional[Dict]:
        ...


class ApiClient:
    """Handles all API-related operations"""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.auth = HTTPBasicAuth(config.email, config.api_token)
        self.headers = {"Accept": "application/json"}

    def make_request(self, url: str, description: str) -> Optional[Dict]:
        """Make API request and return response"""
        try:
            self.logger.debug(f"Making {description} request to: {url}")
            response = requests.get(url, headers=self.headers, auth=self.auth)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error making {description} request to {url}: {str(e)}")
            raise ApiError(f"Failed to make {description} request: {str(e)}")

    def get_page_data_v1(self, page_id: str) -> Optional[Dict]:
        """Get page data using V1 API"""
        url = f"{self.config.base_url}/rest/api/content/{page_id}?expand=title,ancestors,body.storage,body.view"
        return self.make_request(url, "V1 API page data")

    def get_page_data_v2(self, page_id: str) -> Optional[Dict]:
        """Get page data using V2 API"""
        url = f"{self.config.base_url}/api/v2/pages/{page_id}?body-format=atlas_doc_format"
        return self.make_request(url, "V2 API page data")

    def get_child_pages(self, page_id: str) -> Optional[Dict]:
        """Get child pages using V2 API"""
        url = f"{self.config.base_url}/api/v2/pages/{page_id}/children?type=page&limit=100"
        return self.make_request(url, "V2 API child pages")

    def get_attachments(self, page_id: str) -> Optional[Dict]:
        """Get attachments using V1 API"""
        url = f"{self.config.base_url}/rest/api/content/{page_id}/child/attachment"
        return self.make_request(url, "V1 API attachments")

    CQL_SEARCH_LIMIT = 500
    """Maximum number of results per CQL search request."""

    def get_recently_modified_pages(self, days: int, space_key: str, since_date: Optional[str] = None) -> List[Dict]:
        """Get recently modified pages with version info using sliding window.

        Uses CQL datetime precision ("yyyy-MM-dd HH:mm") and a sliding window
        approach to collect all modified pages even when limited to CQL_SEARCH_LIMIT results
        per request (unauthenticated API).

        Args:
            days: Number of days to look back (used when since_date is not provided)
            space_key: Confluence space key
            since_date: ISO 8601 date string (e.g. version.createdAt from page.v2.yaml).
                        If provided, overrides days parameter. A 1-hour safety margin is subtracted.

        Returns:
            List of dicts with keys: "id" (str), "version_number" (int or None),
            "title" (str or None), "last_modified" (str or None).
        """
        try:
            if since_date:
                # Parse ISO 8601 date and apply 1-hour safety margin
                parsed_date = datetime.fromisoformat(since_date.replace("Z", "+00:00"))
                threshold_date = parsed_date - timedelta(hours=1)
                self.logger.info(f"Using since_date: {since_date} (with 1-hour margin: {threshold_date.strftime('%Y-%m-%d %H:%M')})")
            else:
                # Calculate the date threshold from days
                threshold_date = datetime.now() - timedelta(days=days)
                self.logger.info(f"Searching for pages modified in last {days} days in space {space_key}")

            seen_ids: set[str] = set()
            pages: list[Dict] = []
            window_start = threshold_date
            window_round = 0

            while True:
                window_round += 1
                # CQL supports "yyyy-MM-dd HH:mm" format (minute precision)
                date_str = window_start.strftime("%Y-%m-%d %H:%M")
                cql_query = f'lastModified >= "{date_str}" AND type = page AND space = "{space_key}" order by lastModified asc'

                url = f"{self.config.base_url}/rest/api/content/search?cql={quote(cql_query)}&expand=version&limit={self.CQL_SEARCH_LIMIT}"

                self.logger.info(f"CQL query (round {window_round}): {cql_query}")

                response_data = self.make_request(url, f"CQL search (round {window_round})")

                if not response_data:
                    break

                results = response_data.get("results", [])
                if not results:
                    break

                # Extract page info and track the latest lastModified for sliding window
                batch_max_when: Optional[str] = None
                new_count = 0
                for result in results:
                    page_id = result.get("id")
                    if page_id and page_id not in seen_ids:
                        seen_ids.add(page_id)
                        version = result.get("version", {})
                        when = version.get("when")
                        pages.append({
                            "id": page_id,
                            "version_number": version.get("number"),
                            "title": result.get("title"),
                            "last_modified": when,
                        })
                        new_count += 1
                    # Track max across all results (including duplicates) for window advance
                    when = result.get("version", {}).get("when")
                    if when and (batch_max_when is None or when > batch_max_when):
                        batch_max_when = when

                self.logger.info(
                    f"Round {window_round}: {len(results)} results returned, "
                    f"{new_count} new pages (total: {len(pages)})"
                )

                # If fewer than CQL_SEARCH_LIMIT results, we've collected everything
                if len(results) < self.CQL_SEARCH_LIMIT:
                    break

                # Sliding window: advance start to the latest lastModified in this batch
                if batch_max_when:
                    next_start = datetime.fromisoformat(batch_max_when.replace("Z", "+00:00"))
                    if next_start <= window_start:
                        # No progress — CQL minute precision causes the same results.
                        # Advance by 1 minute to skip past the stuck window.
                        window_start = window_start + timedelta(minutes=1)
                        self.logger.warning(
                            f"Sliding window stuck at {date_str} with {len(results)} results. "
                            f"Advancing by 1 minute to {window_start.strftime('%Y-%m-%d %H:%M')}"
                        )
                        continue
                    window_start = next_start
                else:
                    break

            # Log result set summary
            if pages:
                sorted_pages = sorted(pages, key=lambda p: p.get("last_modified") or "")
                oldest = sorted_pages[0]
                newest = sorted_pages[-1]
                self.logger.info(
                    f"Result summary — total: {len(pages)} pages, "
                    f"oldest: {oldest.get('last_modified')} \"{oldest.get('title')}\", "
                    f"newest: {newest.get('last_modified')} \"{newest.get('title')}\""
                )

            self.logger.info(f"Found {len(pages)} recently modified pages in {window_round} round(s)")
            return pages

        except Exception as e:
            self.logger.error(f"Error getting recently modified pages: {str(e)}")
            raise ApiError(f"Failed to get recently modified pages: {str(e)}")

    def download_attachment(self, page_id: str, attachment_id: str) -> Optional[bytes]:
        """Download attachment content"""
        try:
            url = f"{self.config.base_url}/rest/api/content/{page_id}/child/attachment/{attachment_id}/download"
            response = requests.get(url, headers={"Accept": "*/*"}, auth=self.auth)
            response.raise_for_status()
            return response.content
        except Exception as e:
            self.logger.error(f"Error downloading attachment {attachment_id}: {str(e)}")
            raise ApiError(f"Failed to download attachment: {str(e)}")
