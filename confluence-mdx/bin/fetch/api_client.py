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

    def get_recently_modified_pages(self, days: int, space_key: str, since_date: Optional[str] = None) -> List[str]:
        """Get a list of page IDs modified since a date or in the last N days.

        Args:
            days: Number of days to look back (used when since_date is not provided)
            space_key: Confluence space key
            since_date: ISO 8601 date string (e.g. version.createdAt from page.v2.yaml).
                        If provided, overrides days parameter. A 1-day safety margin is subtracted.
        """
        try:
            if since_date:
                # Parse ISO 8601 date and apply 1-day safety margin
                parsed_date = datetime.fromisoformat(since_date.replace("Z", "+00:00"))
                threshold_date = parsed_date - timedelta(days=1)
                date_str = threshold_date.strftime("%Y-%m-%d")
                self.logger.info(f"Using since_date: {since_date} (with 1-day margin: {date_str})")
            else:
                # Calculate the date threshold from days
                threshold_date = datetime.now() - timedelta(days=days)
                date_str = threshold_date.strftime("%Y-%m-%d")
                self.logger.info(f"Searching for pages modified in last {days} days in space {space_key}")

            # Build CQL query
            cql_query = f'lastModified >= "{date_str}" AND type = page AND space = "{space_key}"'
            encoded_query = quote(cql_query)

            # Use CQL search API
            url = f"{self.config.base_url}/rest/api/content/search?cql={encoded_query}"

            self.logger.debug(f"CQL query: {cql_query}")

            seen_ids: set[str] = set()
            page_ids: list[str] = []
            start = 0
            limit = 100

            while True:
                paginated_url = f"{url}&start={start}&limit={limit}"
                response_data = self.make_request(paginated_url, "CQL search for recently modified pages")

                if not response_data:
                    break

                results = response_data.get("results", [])
                if not results:
                    break

                new_count = 0
                for result in results:
                    page_id = result.get("id")
                    if page_id and page_id not in seen_ids:
                        seen_ids.add(page_id)
                        page_ids.append(page_id)
                        new_count += 1

                # Stop if no new results (API ignoring pagination) or last page
                if new_count == 0 or len(results) < limit:
                    break

                start += limit

            self.logger.info(f"Found {len(page_ids)} recently modified pages")
            return page_ids

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
