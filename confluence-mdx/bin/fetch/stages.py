"""Multi-stage processors for Confluence page data collection."""

import logging
import os
import shutil
from typing import Dict, List, Optional

from fetch.config import Config
from fetch.api_client import ApiClient
from fetch.file_manager import FileManager
from fetch.models import Page
from text_utils import clean_text


class StageBase:
    """Base class for stage processors providing shared utilities and dependencies."""

    def __init__(self, config: Config, api_client: ApiClient, file_manager: FileManager, logger: logging.Logger):
        self.config = config
        self.api_client = api_client
        self.file_manager = file_manager
        self.logger = logger

    def get_page_directory(self, page_id: str) -> str:
        """Return the directory path for a specific page."""
        return os.path.join(self.config.default_output_dir, page_id)

    def get_cache_page_directory(self, page_id: str) -> str:
        """Return the cache directory path for a specific page."""
        return os.path.join(self.config.cache_dir, page_id)


class Stage1Processor(StageBase):
    """Stage 1: API Data Collection - Fetch and save API responses to YAML files."""

    def process(self, page_id: str) -> None:
        self.logger.info(f"Stage 1: Collecting API data for page ID {page_id}")

        # Skip API calls if using local mode
        if self.config.mode == "local":
            self.logger.info(f"Stage 1 skipped for page ID {page_id} (local mode)")
            return

        directory = self.get_page_directory(page_id)
        self.file_manager.ensure_directory(directory)

        api_operations = [
            {
                'operation': lambda: self.api_client.get_page_data_v1(page_id),
                'description': "V1 API page data",
                'filename': "page.v1.yaml"
            },
            {
                'operation': lambda: self.api_client.get_page_data_v2(page_id),
                'description': "V2 API page data",
                'filename': "page.v2.yaml"
            },
            {
                'operation': lambda: self.api_client.get_child_pages(page_id),
                'description': "V2 API child pages",
                'filename': "children.v2.yaml"
            },
            {
                'operation': lambda: self.api_client.get_attachments(page_id),
                'description': "V1 API attachments",
                'filename': "attachments.v1.yaml"
            },
        ]

        for operation_info in api_operations:
            try:
                data = operation_info['operation']()
                if data:
                    filepath = os.path.join(directory, operation_info['filename'])
                    self.file_manager.save_yaml(filepath, data)
                    self._log_operation_result(page_id, operation_info['description'], data)
            except Exception as e:
                self.logger.error(f"Failed to collect {operation_info['description']} for page ID {page_id}: {str(e)}")

        self.logger.info(f"Stage 1 completed for page ID {page_id}")

    def _log_operation_result(self, page_id: str, description: str, data: Dict) -> None:
        """Log specific information for different operations."""
        if 'children' in description:
            child_count = len(data.get("results", []))
            self.logger.info(f"Saved {child_count} children for page ID {page_id}")
        elif 'attachments' in description:
            attachment_count = len(data.get("results", []))
            self.logger.info(f"Saved metadata for {attachment_count} attachments for page ID {page_id}")
        else:
            self.logger.info(f"Saved {description} for ID {page_id}")


class Stage2Processor(StageBase):
    """Stage 2: Content Extraction - Extract and save page content."""

    def process(self, page_id: str) -> bool:
        self.logger.info(f"Stage 2: Extracting content for page ID {page_id}")
        directory = self.get_page_directory(page_id)

        # Extract V1 content
        v1_data = self.file_manager.load_yaml(os.path.join(directory, "page.v1.yaml"))
        if v1_data:
            self._extract_v1_content(page_id, v1_data, directory)

        # Extract V2 content
        v2_data = self.file_manager.load_yaml(os.path.join(directory, "page.v2.yaml"))
        if v2_data:
            self._extract_v2_content(page_id, v2_data, directory)

        self.logger.info(f"Stage 2 completed for page ID {page_id}")
        return True

    def _extract_v1_content(self, page_id: str, v1_data: Dict, directory: str) -> None:
        """Extract content from V1 API data."""
        body = v1_data.get("body", {})

        # Extract XHTML content
        xhtml_content = body.get("storage", {}).get("value", "")
        if xhtml_content:
            self.file_manager.save_file(os.path.join(directory, "page.xhtml"), xhtml_content)
            self.logger.info(f"Extracted XHTML content for page ID {page_id} ({len(xhtml_content)} characters)")

        # Extract HTML content
        html_content = body.get("view", {}).get("value", "")
        if html_content:
            self.file_manager.save_file(os.path.join(directory, "page.html"), html_content)
            self.logger.info(f"Extracted HTML content for page ID {page_id} ({len(html_content)} characters)")

        # Extract ancestors
        ancestors = v1_data.get("ancestors", [])
        if ancestors:
            self.file_manager.save_yaml(os.path.join(directory, "ancestors.v1.yaml"), {'results': ancestors})
            self.logger.info(f"Extracted {len(ancestors)} ancestors for page ID {page_id}")

    def _extract_v2_content(self, page_id: str, v2_data: Dict, directory: str) -> None:
        """Extract content from V2 API data."""
        adf_content = v2_data.get("body", {}).get("atlas_doc_format", {}).get("value", "")
        if adf_content:
            self.file_manager.save_file(os.path.join(directory, "page.adf"), adf_content)
            self.logger.info(f"Extracted ADF content for page ID {page_id} ({len(adf_content)} characters)")


class Stage3Processor(StageBase):
    """Stage 3: Attachment Download - Download attachments if specified."""

    def process(self, page_id: str) -> bool:
        # Check if attachments should be downloaded
        if not self.config.download_attachments:
            self.logger.info(f"Stage 3 skipped for page ID {page_id} (attachments not requested)")
            return True

        # Skip attachment download if using local mode
        if self.config.mode == "local":
            self.logger.info(f"Stage 3 skipped for page ID {page_id} (local mode)")
            return True

        self.logger.info(f"Stage 3: Downloading attachments for page ID {page_id}")
        directory = self.get_page_directory(page_id)
        attachments_filepath = os.path.join(directory, "attachments.v1.yaml")

        if not os.path.exists(attachments_filepath):
            return True

        attachments_data = self.file_manager.load_yaml(attachments_filepath)
        if not attachments_data:
            return True

        attachments = attachments_data.get("results", [])
        self.logger.info(f"Found {len(attachments)} attachments for page ID {page_id}")

        for attachment in attachments:
            self._download_single_attachment(page_id, attachment, directory)

        self.logger.info(f"Stage 3 completed for page ID {page_id}")
        return True

    def _download_single_attachment(self, page_id: str, attachment: Dict, directory: str) -> None:
        """Download a single attachment."""
        try:
            attachment_id = attachment["id"]
            filename = clean_text(attachment["title"])
            filepath = os.path.join(directory, filename)

            # Get expected file size from API metadata
            expected_size = None
            extensions = attachment.get("extensions", {})
            if "fileSize" in extensions:
                expected_size = extensions["fileSize"]

            # Check cache directory for the file before downloading from API
            cache_page_dir = self.get_cache_page_directory(page_id)
            cache_filepath = os.path.join(cache_page_dir, filename)
            if os.path.exists(cache_filepath):
                cache_file_size = os.path.getsize(cache_filepath)
                if cache_file_size > 0:
                    # Verify size if expected size is available
                    if expected_size is not None:
                        if cache_file_size == expected_size:
                            # Copy from cache
                            shutil.copy2(cache_filepath, filepath)
                            self.logger.info(f"Copied attachment from cache: {filename} (size: {cache_file_size} bytes, matches expected size)")
                            return
                        else:
                            self.logger.warning(f"Cache file size mismatch for {filename}: cache={cache_file_size}, expected={expected_size}. Downloading from API.")
                    else:
                        # Copy from cache if no expected size available
                        shutil.copy2(cache_filepath, filepath)
                        self.logger.info(f"Copied attachment from cache: {filename} (size: {cache_file_size} bytes)")
                        return

            # Download from API if not found in cache (always overwrite existing files in var directory)
            content = self.api_client.download_attachment(page_id, attachment_id)
            if content:
                self.file_manager.save_file(filepath, content, is_binary=True)
                downloaded_size = len(content)
                size_info = f" (size: {downloaded_size} bytes"
                if expected_size is not None:
                    if downloaded_size == expected_size:
                        size_info += ", matches expected size"
                    else:
                        size_info += f", expected: {expected_size} bytes"
                size_info += ")"
                self.logger.warning(f"Downloaded attachment from API: {filename}{size_info}")
        except Exception as e:
            self.logger.error(f"Error downloading attachment {attachment.get('title', 'unknown')}: {str(e)}")


class Stage4Processor(StageBase):
    """Stage 4: Document Listing - Generate document information for output listing."""

    def process(self, page_id: str, start_page_id: Optional[str] = None) -> Optional[Page]:
        self.logger.info(f"Stage 4: Generating document list for page ID {page_id}")

        directory = self.get_page_directory(page_id)
        v1_data = self.file_manager.load_yaml(os.path.join(directory, "page.v1.yaml"))

        if not v1_data:
            self.logger.error(f"V1 data not available for document listing for page ID {page_id}")
            return None

        # Extract title from V1 data
        title_orig = v1_data.get("title")
        if not title_orig:
            return None

        title = clean_text(title_orig)
        if not title:
            return None

        # Extract ancestors from V1 data
        ancestors = v1_data.get("ancestors", []) if v1_data else []

        # Build breadcrumbs
        breadcrumbs = self._build_breadcrumbs(page_id, ancestors, title, start_page_id)

        self.logger.info(f"Stage 4 completed for page ID {page_id}: {title}")

        return Page(
            page_id=page_id,
            title=title,
            title_orig=title_orig,
            breadcrumbs=breadcrumbs,
        )

    def _build_breadcrumbs(
            self,
            page_id: str,
            ancestors: List[Dict],
            title: str,
            start_page_id: Optional[str] = None,
    ) -> List[str]:
        """Build breadcrumb list of page titles."""
        try:
            # Special case for the start page
            if start_page_id and page_id == start_page_id:
                return [title]

            # Filter ancestors based on start_page_id
            if start_page_id:
                filtered_ancestors: List[str] = []
                found_start_page = False
                for ancestor in ancestors:
                    if ancestor.get("type") == "page":
                        if ancestor["id"] == start_page_id:
                            found_start_page = True
                            continue
                        elif not found_start_page:
                            continue
                        if "title" in ancestor:
                            filtered_ancestors.append(clean_text(ancestor["title"]))

                path = filtered_ancestors + [title]
            else:
                # Include all ancestors
                ancestor_titles = [
                    clean_text(ancestor["title"]) for ancestor in ancestors if ancestor.get("type") == "page" and "title" in ancestor
                ]
                path = ancestor_titles + [title]

            return path
        except Exception as e:
            self.logger.error(f"Error building breadcrumbs for page {page_id}: {str(e)}")
            return [title]
