#!/usr/bin/env python3
"""
Confluence Page Tree Generator

This script generates a list of all subpages from a specified document in a Confluence space.
Output format: page_id \t breadcrumbs

The document processing follows 4 distinct stages:
1. API Data Collection: Fetch and save API responses to YAML files
2. Content Extraction: Extract and save page content (XHTML, HTML, ADF)
3. Attachment Download: Download attachments if specified
4. Document Listing: Generate and output a document list with breadcrumbs

The script outputs the page list to stdout and saves the structured data to pages.yaml.

Usage examples:
  python pages_of_confluence.py
  python pages_of_confluence.py --page-id 123456789
  python pages_of_confluence.py --email user@example.com --api-token your-api-token
  python pages_of_confluence.py --attachments # Download page content with attachments
  python pages_of_confluence.py --local # Use local YAML files instead of making API calls
"""
import argparse
import logging
import os
import re
import sys
import traceback
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Generator, Protocol

import requests
import yaml
from requests.auth import HTTPBasicAuth


# ============================================================================
# Configuration Management
# ============================================================================

@dataclass
class Config:
    """Centralized configuration management"""
    base_url: str = "https://querypie.atlassian.net/wiki"
    default_start_page_id: str = "608501837"  # Root Page ID of "QueryPie Docs"
    quick_start_page_id: str = "544375784"  # QueryPie Overview having less children
    default_output_dir: str = "docs/latest-ko-confluence"
    translations_file: str = "docs/korean-titles-translations.txt"
    email: str = None
    api_token: str = None
    download_attachments: bool = False
    use_local_files: bool = False

    def __post_init__(self):
        if self.email is None:
            self.email = os.environ.get('ATLASSIAN_USERNAME', 'your-email@example.com')
        if self.api_token is None:
            self.api_token = os.environ.get('ATLASSIAN_API_TOKEN', 'your-api-token')


# ============================================================================
# Custom Exceptions
# ============================================================================

class ConfluenceError(Exception):
    """Base exception for Confluence operations"""
    pass


class ApiError(ConfluenceError):
    """Exception for API-related errors"""
    pass


class FileError(ConfluenceError):
    """Exception for file operation errors"""
    pass


class TranslationError(ConfluenceError):
    """Exception for translation-related errors"""
    pass


# ============================================================================
# Interfaces and Protocols
# ============================================================================

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


class FileManagerProtocol(Protocol):
    """Protocol for file operations"""

    def save_file(self, filepath: str, content: Any, is_binary: bool = False) -> bool:
        ...

    def save_yaml(self, filepath: str, data: Any) -> bool:
        ...

    def load_yaml(self, filepath: str) -> Optional[Dict]:
        ...

    def ensure_directory(self, directory: str) -> bool:
        ...


class TranslationServiceProtocol(Protocol):
    """Protocol for translation operations"""

    def load_translations(self) -> None:
        ...

    def translate(self, content: str) -> str:
        ...

    def translate_page(self, page: 'Page') -> None:
        ...


# ============================================================================
# Utility Functions
# ============================================================================

def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug format.
    Replace spaces with hyphens and remove special characters.
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)
    # Remove special characters
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading and trailing hyphens
    text = text.strip('-')
    return text


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean text by removing hidden characters"""
    if text is None:
        return None

    # Hidden characters for text cleaning
    hidden_characters = {
        '\u00A0': ' ',  # Non-Breaking Space
        '\u202f': ' ',  # Narrow No-Break Space
        '\u200b': '',  # Zero Width Space
        '\u200e': '',  # Left-to-Right Mark
        '\u3164': ''  # Hangul Filler
    }

    # Apply unicodedata.normalize to prevent unmatched string comparison.
    # Use Normalization Form Canonical Composition for the unicode normalization.
    cleaned_text = unicodedata.normalize('NFC', text)
    for hidden_char, replacement in hidden_characters.items():
        cleaned_text = cleaned_text.replace(hidden_char, replacement)
    return cleaned_text


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Page:
    """Class to represent a Confluence page with its metadata and content"""
    page_id: str
    title: str
    breadcrumbs: List[str] = None
    breadcrumbs_en: List[str] = None
    path: List[str] = None

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
            page_id=data.get('id', ''),
            title=data.get('title', ''),
            breadcrumbs=data.get('breadcrumbs', []),
            breadcrumbs_en=data.get('breadcrumbs_en', []),
            path=data.get('path', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Page instance to dictionary"""
        return {
            'page_id': self.page_id,
            'title': self.title,
            'breadcrumbs': self.breadcrumbs,
            'breadcrumbs_en': self.breadcrumbs_en,
            'path': self.path
        }

    def to_output_line(self) -> str:
        """Convert to output line format: page_id \t breadcrumbs \t title"""
        breadcrumbs_str = " />> ".join(self.breadcrumbs) if self.breadcrumbs else ""
        return f"{self.page_id}\t{breadcrumbs_str}\t{self.title}"


# ============================================================================
# Service Classes
# ============================================================================

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


class FileManager:
    """Handles all file I/O operations"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def ensure_directory(self, directory: str) -> bool:
        """Ensure directory exists"""
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Error creating directory {directory}: {str(e)}")
            raise FileError(f"Failed to create directory: {str(e)}")

    def save_file(self, filepath: str, content: Any, is_binary: bool = False) -> bool:
        """Save content to file"""
        try:
            self.ensure_directory(os.path.dirname(filepath))
            mode = 'wb' if is_binary else 'w'
            encoding = None if is_binary else 'utf-8'

            with open(filepath, mode, encoding=encoding) as f:
                f.write(content)

            self.logger.debug(f"Saved {len(content)} bytes to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving file {filepath}: {str(e)}")
            raise FileError(f"Failed to save file: {str(e)}")

    def save_yaml(self, filepath: str, data: Any) -> bool:
        """Save YAML data to a file"""
        return self.save_file(filepath, yaml.dump(data, allow_unicode=True, sort_keys=False))

    def load_yaml(self, filepath: str) -> Optional[Dict]:
        """Read YAML from a file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading YAML from {filepath}: {str(e)}")
            raise FileError(f"Failed to load YAML: {str(e)}")
        return None


class TranslationService:
    """Handles Korean to English title translations"""

    def __init__(self, translations_file: str, logger: logging.Logger):
        self.translations_file = translations_file
        self.logger = logger
        self.translations = {}

    def load_translations(self) -> None:
        """Load translations from the translations file"""
        if not os.path.exists(self.translations_file):
            self.logger.warning(f"Translations file not found: {self.translations_file}")
            return

        try:
            with open(self.translations_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '|' not in line:
                        continue

                    parts = line.split('|')
                    if len(parts) == 2:
                        korean = parts[0].strip()
                        english = parts[1].strip()
                        if korean and english:
                            self.translations[korean] = english

            self.logger.info(f"Loaded {len(self.translations)} translations from {self.translations_file}")
        except Exception as e:
            self.logger.error(f"Error loading translations from {self.translations_file}: {str(e)}")
            raise TranslationError(f"Failed to load translations: {str(e)}")

    def translate(self, content: str) -> str:
        """Translate Korean titles in content to English"""
        if not self.translations:
            return content

        # Sort translations by length (longest first) to avoid partial matches
        sorted_translations = sorted(self.translations.items(), key=lambda x: len(x[0]), reverse=True)

        # Replace Korean titles with English translations
        translated_content = content
        for korean, english in sorted_translations:
            # Replace in both the navigation path and the document title
            translated_content = translated_content.replace(f" />> {korean}", f" />> {english}")
            translated_content = translated_content.replace(f"\t{korean}", f"\t{english}")

        return translated_content

    def translate_page(self, page: Page) -> None:
        """Update English translations and path using the translator"""
        # Translate breadcrumbs to English
        page.breadcrumbs_en = []
        for crumb in page.breadcrumbs:
            translated = crumb
            for korean, english in self.translations.items():
                if korean == crumb:
                    translated = english
                    break
            page.breadcrumbs_en.append(translated)

        # Create path by slugifying English breadcrumbs
        page.path = [slugify(crumb) for crumb in page.breadcrumbs_en]


# ============================================================================
# Processing Stages (Refactored per stage)
# ============================================================================

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


class Stage1Processor(StageBase):
    """Stage 1: API Data Collection - Fetch and save API responses to YAML files."""

    def process(self, page_id: str) -> None:
        self.logger.info(f"Stage 1: Collecting API data for page ID {page_id}")

        # Skip API calls if using local files
        if self.config.use_local_files:
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

        # Skip attachment download if using local files
        if self.config.use_local_files:
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

            content = self.api_client.download_attachment(page_id, attachment_id)
            if content:
                filepath = os.path.join(directory, filename)
                self.file_manager.save_file(filepath, content, is_binary=True)
                self.logger.info(f"Downloaded attachment: {filename}")
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
        title = clean_text(v1_data.get("title"))
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


# ============================================================================
# Main Processor
# ============================================================================

class ConfluencePageProcessor:
    """Main class for Confluence page processing with improved structure"""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger

        # Initialize services with dependency injection
        self.api_client = ApiClient(config, logger)
        self.file_manager = FileManager(logger)
        self.translation_service = TranslationService(config.translations_file, logger)

        # Initialize stage processors
        self.stage1 = Stage1Processor(config, self.api_client, self.file_manager, logger)
        self.stage2 = Stage2Processor(config, self.api_client, self.file_manager, logger)
        self.stage3 = Stage3Processor(config, self.api_client, self.file_manager, logger)
        self.stage4 = Stage4Processor(config, self.api_client, self.file_manager, logger)

        # Load translations
        self.translation_service.load_translations()

    def process_page_complete(self, page_id: str, start_page_id: Optional[str] = None) -> Optional[Page]:
        """Process a single page through all 4 stages"""
        try:
            self.logger.info(f"Processing page ID {page_id} through all stages")

            # Stage 1: API Data Collection
            self.stage1.process(page_id)

            # Stage 2: Content Extraction
            self.stage2.process(page_id)

            # Stage 3: Attachment Download
            self.stage3.process(page_id)

            # Stage 4: Document Listing
            page = self.stage4.process(page_id, start_page_id)

            self.logger.info(f"Completed all stages for page ID {page_id}")
            return page

        except Exception as e:
            self.logger.error(f"Error processing page ID {page_id}: {str(e)}")
            return None

    def get_child_page_ids(self, page_id: str) -> List[str]:
        """Get child page IDs for recursive processing"""
        try:
            directory = self.stage1.get_page_directory(page_id)
            yaml_filepath = os.path.join(directory, "children.v2.yaml")

            if os.path.exists(yaml_filepath):
                data = self.file_manager.load_yaml(yaml_filepath)
                if data:
                    child_ids = [child["id"] for child in data.get("results", [])]
                    self.logger.info(f"Found {len(child_ids)} child pages for page ID {page_id}")
                    return child_ids
            else:
                self.logger.warning(f"No children.v2.yaml found for page ID {page_id}")
                return []
        except Exception as e:
            self.logger.error(f"Error getting child page IDs for page ID {page_id}: {str(e)}")
            return []

    def fetch_page_tree_recursive(self, page_id: str, start_page_id: Optional[str] = None) -> Generator[Page, None, None]:
        """Recursively fetch page tree through all 4 stages"""
        try:
            self.logger.info(f"Processing page tree for page ID {page_id}")

            # If start_page_id is not provided, use the current page_id as the starting point
            if start_page_id is None:
                start_page_id = page_id

            # Process current page through all 4 stages
            page = self.process_page_complete(page_id, start_page_id)

            if page:
                # Update translations if available
                if self.translation_service.translations:
                    self.translation_service.translate_page(page)
                else:
                    # If no translations available, use original breadcrumbs for English and path
                    page.breadcrumbs_en = page.breadcrumbs
                    page.path = [slugify(crumb) for crumb in page.breadcrumbs]

                yield page

                # Process child pages recursively
                child_ids = self.get_child_page_ids(page_id)
                for child_id in child_ids:
                    yield from self.fetch_page_tree_recursive(child_id, start_page_id)
        except Exception as e:
            self.logger.error(f"Error processing page ID {page_id}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def run(self) -> None:
        """Main execution function"""
        try:
            self.logger.info(f"Starting to fetch page tree from page ID: {self.config.default_start_page_id}")

            # Check if output directory exists
            if not os.path.exists(self.config.default_output_dir):
                self.file_manager.ensure_directory(self.config.default_output_dir)
                self.logger.info(f"Created output directory: {self.config.default_output_dir}")

            # Prepare output file path
            output_yaml_path = os.path.join(self.config.default_output_dir, "pages.yaml")

            # Fetch a page tree through all 4 stages
            page_count = 0
            yaml_entries = []

            for page in self.fetch_page_tree_recursive(self.config.default_start_page_id):
                if page:
                    # Print to stdout for backward compatibility (page_id and breadcrumbs only)
                    breadcrumbs_str = " />> ".join(page.breadcrumbs) if page.breadcrumbs else ""
                    print(f"{page.page_id}\t{breadcrumbs_str}")
                    page_count += 1

                    # Add to YAML entries
                    yaml_entries.append(page.to_dict())

            # Save YAML file
            self.file_manager.save_yaml(output_yaml_path, yaml_entries)
            self.logger.info(f"YAML data saved to {output_yaml_path}")

            self.logger.info(f"Completed processing {page_count} pages through all 4 stages")
        except Exception as e:
            self.logger.error(f"Error in main execution: {str(e)}")
            self.logger.debug(traceback.format_exc())
            sys.exit(1)


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate a list of all subpages from a specified Confluence document")
    parser.add_argument("--page-id", default=Config().default_start_page_id,
                        help="ID of the starting page (default: %(default)s)")
    parser.add_argument("--quick-start", action="store_true",
                        help=f"Use QUICK_START_PAGE_ID ({Config().quick_start_page_id}) for faster testing")

    parser.add_argument("--base-url", default=Config().base_url, help="Confluence base URL (default: %(default)s)")
    parser.add_argument("--email", default=Config().email, help="Confluence email for authentication")
    parser.add_argument("--api-token", default=Config().api_token, help="Confluence API token for authentication")
    parser.add_argument("--attachments", action="store_true", help="Download page content with attachments")
    parser.add_argument("--local", action="store_true",
                        help="Use local page.v1.yaml and page.v2.yaml files instead of making API calls")
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

    # Create configuration
    config = Config(
        base_url=args.base_url,
        email=args.email,
        api_token=args.api_token,
        default_output_dir=args.output_dir,
        download_attachments=args.attachments,
        use_local_files=args.local
    )

    # Handle page-id and quick-start options
    if args.quick_start:
        config.default_start_page_id = config.quick_start_page_id
        logging.getLogger(__name__).info(f"Quick start mode enabled, using page ID: {config.quick_start_page_id}")
    elif args.page_id != Config().default_start_page_id:
        # Only update if page-id was explicitly provided and different from default
        config.default_start_page_id = args.page_id
        logging.getLogger(__name__).info(f"Using custom page ID: {args.page_id}")

    # Create processor and run
    logger = logging.getLogger(__name__)
    processor = ConfluencePageProcessor(config, logger)
    processor.run()


if __name__ == "__main__":
    main()
