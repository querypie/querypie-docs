#!/usr/bin/env python3
"""
Confluence Page Tree Generator

This script generates a list of all subpages from a specified document in a Confluence space.
Output format: page_id \t breadcrumbs \t title

The document processing follows 4 distinct stages:
1. API Data Collection: Fetch and save API responses to YAML files
2. Content Extraction: Extract and save page content (XHTML, HTML, ADF)
3. Attachment Download: Download attachments if specified
4. Document Listing: Generate and output document list with breadcrumbs

Usage examples:
  python pages_of_confluence.py
  python pages_of_confluence.py --page-id 123456789 --space-key DOCS
  python pages_of_confluence.py --email user@example.com --api-token your-api-token
  python pages_of_confluence.py --attachments  # Download page content with attachments
  python pages_of_confluence.py --local  # Use local YAML files instead of making API calls
"""
import unicodedata

import requests
from requests.auth import HTTPBasicAuth
import sys
import os
import argparse
import traceback
import yaml
import logging
from typing import Dict, List, Optional, Any, Generator

# Configuration constants
BASE_URL = "https://querypie.atlassian.net/wiki"
SPACE_KEY = "QM"
DEFAULT_START_PAGE_ID = "608501837"  # Root Page ID of "QueryPie Docs"
QUICK_START_PAGE_ID = "544375784"  # QueryPie Overview having less children
DEFAULT_OUTPUT_DIR = "docs/latest-ko-confluence"

# Environment variables for authentication
EMAIL = os.environ.get('ATLASSIAN_USERNAME', 'your-email@example.com')
API_TOKEN = os.environ.get('ATLASSIAN_API_TOKEN', 'your-api-token')

# Hidden characters for text cleaning
HIDDEN_CHARACTERS = {
    '\u00A0': ' ',  # Non-Breaking Space
    '\u202f': ' ',  # Narrow No-Break Space
    '\u200b': '',  # Zero Width Space
    '\u200e': '',  # Left-to-Right Mark
    '\u3164': ''  # Hangul Filler
}


class ConfluencePageProcessor:
    """Main class for Confluence page processing"""

    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.auth = HTTPBasicAuth(args.email, args.api_token)
        self.headers = {"Accept": "application/json"}

        # Handle quick-start option
        if args.quick_start:
            args.page_id = QUICK_START_PAGE_ID
            self.logger.info(f"Quick start mode enabled, using page ID: {QUICK_START_PAGE_ID}")

    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean text by removing hidden characters"""
        if text is None:
            return None

        # Apply unicodedata.normalize to prevent unmatched string comparison.
        # Use Normalization Form Canonical Composition for the unicode normalization.
        cleaned_text = unicodedata.normalize('NFC', text)
        for hidden_char, replacement in HIDDEN_CHARACTERS.items():
            cleaned_text = cleaned_text.replace(hidden_char, replacement)
        return cleaned_text

    def _save_file(self, filepath: str, content: Any, is_binary: bool = False) -> bool:
        """Save content to file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            mode = 'wb' if is_binary else 'w'
            encoding = None if is_binary else 'utf-8'
            
            with open(filepath, mode, encoding=encoding) as f:
                f.write(content)
            
            self.logger.debug(f"Saved {len(content)} bytes to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving file {filepath}: {str(e)}")
            return False

    def _save_yaml(self, filepath: str, data: Any) -> bool:
        """Save YAML data to a file"""
        return self._save_file(filepath, yaml.dump(data, allow_unicode=True, sort_keys=False))

    def _load_yaml(self, filepath: str) -> Optional[Dict]:
        """Read YAML from a file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading YAML from {filepath}: {str(e)}")
        return None

    def _make_api_request(self, url: str, description: str) -> Optional[Dict]:
        """Make API request and return response"""
        try:
            self.logger.debug(f"Making {description} request to: {url}")
            response = requests.get(url, headers=self.headers, auth=self.auth)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error making {description} request to {url}: {str(e)}")
            return None

    def _get_page_directory(self, page_id: str) -> str:
        """Get page directory path"""
        return os.path.join(self.args.output_dir, page_id)

    # ============================================================================
    # STAGE 1: API Data Collection - Fetch and save API responses to YAML files
    # ============================================================================

    def stage1_collect_api_data(self, page_id: str) -> None:
        """Stage 1: API Data Collection - Fetch and save API responses to YAML files"""
        self.logger.info(f"Stage 1: Collecting API data for page ID {page_id}")

        if self.args.local:
            self.logger.info(f"Stage 1 skipped for page ID {page_id} (local mode)")
            return

        directory = self._get_page_directory(page_id)

        # Define API endpoints to fetch
        api_endpoints = [
            {
                'url': f"{self.args.base_url}/rest/api/content/{page_id}?expand=title,ancestors,body.storage,body.view",
                'description': "V1 API page data",
                'filename': "page.v1.yaml"
            },
            {
                'url': f"{self.args.base_url}/api/v2/pages/{page_id}?body-format=atlas_doc_format",
                'description': "V2 API page data",
                'filename': "page.v2.yaml"
            },
            {
                'url': f"{self.args.base_url}/api/v2/pages/{page_id}/children?type=page&limit=100",
                'description': "V2 API child pages",
                'filename': "children.v2.yaml"
            },
            {
                'url': f"{self.args.base_url}/rest/api/content/{page_id}/child/attachment",
                'description': "V1 API attachments",
                'filename': "attachments.v1.yaml"
            }
        ]

        # Fetch all API data
        for endpoint in api_endpoints:
            data = self._make_api_request(endpoint['url'], endpoint['description'])
            if data:
                filepath = os.path.join(directory, endpoint['filename'])
                self._save_yaml(filepath, data)
                
                # Log specific information for children and attachments
                if 'children' in endpoint['filename']:
                    child_count = len(data.get("results", []))
                    self.logger.info(f"Saved {child_count} children for page ID {page_id}")
                elif 'attachments' in endpoint['filename']:
                    attachment_count = len(data.get("results", []))
                    self.logger.info(f"Saved metadata for {attachment_count} attachments for page ID {page_id}")
                else:
                    self.logger.info(f"Saved {endpoint['description']} for ID {page_id}")

        self.logger.info(f"Stage 1 completed for page ID {page_id}")

    # ============================================================================
    # STAGE 2: Content Extraction - Extract and save page content
    # ============================================================================

    def stage2_extract_content(self, page_id: str) -> bool:
        """Stage 2: Content Extraction - Extract and save page content"""
        self.logger.info(f"Stage 2: Extracting content for page ID {page_id}")
        directory = self._get_page_directory(page_id)

        # Extract V1 content
        v1_data = self._load_yaml(os.path.join(directory, "page.v1.yaml"))
        if v1_data:
            self._extract_v1_content(page_id, v1_data, directory)

        # Extract V2 content
        v2_data = self._load_yaml(os.path.join(directory, "page.v2.yaml"))
        if v2_data:
            self._extract_v2_content(page_id, v2_data, directory)

        self.logger.info(f"Stage 2 completed for page ID {page_id}")
        return True

    def _extract_v1_content(self, page_id: str, v1_data: Dict, directory: str) -> None:
        """Extract content from V1 API data"""
        body = v1_data.get("body", {})
        
        # Extract XHTML content
        xhtml_content = body.get("storage", {}).get("value", "")
        if xhtml_content:
            self._save_file(os.path.join(directory, "page.xhtml"), xhtml_content)
            self.logger.info(f"Extracted XHTML content for page ID {page_id} ({len(xhtml_content)} characters)")

        # Extract HTML content
        html_content = body.get("view", {}).get("value", "")
        if html_content:
            self._save_file(os.path.join(directory, "page.html"), html_content)
            self.logger.info(f"Extracted HTML content for page ID {page_id} ({len(html_content)} characters)")

        # Extract ancestors
        ancestors = v1_data.get("ancestors", [])
        if ancestors:
            self._save_yaml(os.path.join(directory, "ancestors.v1.yaml"), {'results': ancestors})
            self.logger.info(f"Extracted {len(ancestors)} ancestors for page ID {page_id}")

    def _extract_v2_content(self, page_id: str, v2_data: Dict, directory: str) -> None:
        """Extract content from V2 API data"""
        adf_content = v2_data.get("body", {}).get("atlas_doc_format", {}).get("value", "")
        if adf_content:
            self._save_file(os.path.join(directory, "page.adf"), adf_content)
            self.logger.info(f"Extracted ADF content for page ID {page_id} ({len(adf_content)} characters)")

    # ============================================================================
    # STAGE 3: Attachment Download - Download attachments if specified
    # ============================================================================

    def stage3_download_attachments(self, page_id: str) -> bool:
        """Stage 3: Attachment Download - Download attachments if specified"""
        if not self.args.attachments or self.args.local:
            return True

        self.logger.info(f"Stage 3: Downloading attachments for page ID {page_id}")
        directory = self._get_page_directory(page_id)
        attachments_filepath = os.path.join(directory, "attachments.v1.yaml")

        if not os.path.exists(attachments_filepath):
            return True

        attachments_data = self._load_yaml(attachments_filepath)
        if not attachments_data:
            return True

        attachments = attachments_data.get("results", [])
        self.logger.info(f"Found {len(attachments)} attachments for page ID {page_id}")

        # Download each attachment
        for attachment in attachments:
            self._download_single_attachment(page_id, attachment, directory)

        self.logger.info(f"Stage 3 completed for page ID {page_id}")
        return True

    def _download_single_attachment(self, page_id: str, attachment: Dict, directory: str) -> None:
        """Download a single attachment"""
        try:
            attachment_id = attachment["id"]
            filename = self.clean_text(attachment["title"])
            download_url = f"{self.args.base_url}/rest/api/content/{page_id}/child/attachment/{attachment_id}/download"

            response = requests.get(download_url, headers={"Accept": "*/*"}, auth=self.auth)
            response.raise_for_status()

            filepath = os.path.join(directory, filename)
            self._save_file(filepath, response.content, is_binary=True)
            self.logger.info(f"Downloaded attachment: {filename}")
        except Exception as e:
            self.logger.error(f"Error downloading attachment {attachment.get('title', 'unknown')}: {str(e)}")

    # ============================================================================
    # STAGE 4: Document Listing - Generate and output document list
    # ============================================================================

    def stage4_generate_document_list(self, page_id: str, start_page_id: Optional[str] = None) -> Optional[Dict]:
        """Stage 4: Document Listing - Generate document information for output listing"""
        self.logger.info(f"Stage 4: Generating document list for page ID {page_id}")

        directory = self._get_page_directory(page_id)
        v1_data = self._load_yaml(os.path.join(directory, "page.v1.yaml"))

        if not v1_data:
            self.logger.error(f"V1 data not available for document listing for page ID {page_id}")
            return None

        # Extract title from V1 data
        title = self.clean_text(v1_data.get("title"))
        if not title:
            return None

        # Extract ancestors from V1 data
        ancestors = v1_data.get("ancestors", []) if v1_data else []

        # Build breadcrumbs
        breadcrumbs = self._build_breadcrumbs(page_id, ancestors, title, start_page_id)

        self.logger.info(f"Stage 4 completed for page ID {page_id}: {title}")

        return {
            "id": page_id,
            "breadcrumbs": breadcrumbs,
            "title": title
        }

    def _build_breadcrumbs(self, page_id: str, ancestors: List[Dict], title: str,
                          start_page_id: Optional[str] = None) -> str:
        """Build breadcrumb string"""
        try:
            # Special case for the start page
            if start_page_id and page_id == start_page_id:
                return title

            # Filter ancestors based on start_page_id
            if start_page_id:
                filtered_ancestors = []
                found_start_page = False
                for ancestor in ancestors:
                    if ancestor.get("type") == "page":
                        if ancestor["id"] == start_page_id:
                            found_start_page = True
                            continue
                        elif not found_start_page:
                            continue
                        if "title" in ancestor:
                            filtered_ancestors.append(self.clean_text(ancestor["title"]))

                path = filtered_ancestors + [title]
            else:
                # Include all ancestors
                ancestor_titles = [self.clean_text(ancestor["title"]) for ancestor in ancestors
                                 if ancestor.get("type") == "page" and "title" in ancestor]
                path = ancestor_titles + [title]

            return " > ".join(path)
        except Exception as e:
            self.logger.error(f"Error building breadcrumbs for page {page_id}: {str(e)}")
            return title

    # ============================================================================
    # Main Processing Functions
    # ============================================================================

    def process_page_complete(self, page_id: str, start_page_id: Optional[str] = None) -> Optional[Dict]:
        """Process a single page through all 4 stages"""
        try:
            self.logger.info(f"Processing page ID {page_id} through all stages")

            # Stage 1: API Data Collection
            self.stage1_collect_api_data(page_id)

            # Stage 2: Content Extraction
            self.stage2_extract_content(page_id)

            # Stage 3: Attachment Download
            self.stage3_download_attachments(page_id)

            # Stage 4: Document Listing
            document_info = self.stage4_generate_document_list(page_id, start_page_id)

            self.logger.info(f"Completed all stages for page ID {page_id}")
            return document_info

        except Exception as e:
            self.logger.error(f"Error processing page ID {page_id}: {str(e)}")
            return None

    def get_child_page_ids(self, page_id: str) -> List[str]:
        """Get child page IDs for recursive processing"""
        try:
            directory = self._get_page_directory(page_id)
            yaml_filepath = os.path.join(directory, "children.v2.yaml")

            if os.path.exists(yaml_filepath):
                data = self._load_yaml(yaml_filepath)
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

    def fetch_page_tree_recursive(self, page_id: str, start_page_id: Optional[str] = None) -> Generator[Dict, None, None]:
        """Recursively fetch page tree through all 4 stages"""
        try:
            self.logger.info(f"Processing page tree for page ID {page_id}")

            # If start_page_id is not provided, use the current page_id as the starting point
            if start_page_id is None:
                start_page_id = page_id

            # Process current page through all 4 stages
            document_info = self.process_page_complete(page_id, start_page_id)

            if document_info:
                yield document_info

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
            self.logger.info(f"Starting to fetch page tree from page ID: {self.args.page_id}")

            # Check if output directory exists
            if not os.path.exists(self.args.output_dir):
                error_msg = f"Error: Output directory '{self.args.output_dir}' does not exist. Please create it first."
                self.logger.critical(error_msg)
                print(error_msg, file=sys.stderr)
                sys.exit(1)

            # Fetch page tree through all 4 stages
            page_count = 0
            for page_info in self.fetch_page_tree_recursive(self.args.page_id):
                if page_info:
                    print(f"{page_info['id']}\t{page_info['breadcrumbs']}\t{page_info['title']}")
                    page_count += 1

            self.logger.info(f"Completed processing {page_count} pages through all 4 stages")
        except Exception as e:
            self.logger.error(f"Error in main execution: {str(e)}")
            self.logger.debug(traceback.format_exc())
            sys.exit(1)


def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate a list of all subpages from a specified Confluence document")
    parser.add_argument("--page-id", default=DEFAULT_START_PAGE_ID,
                        help="ID of the starting page (default: %(default)s)")
    parser.add_argument("--quick-start", action="store_true",
                        help=f"Use QUICK_START_PAGE_ID ({QUICK_START_PAGE_ID}) for faster testing")
    parser.add_argument("--space-key", default=SPACE_KEY, help="Confluence space key (default: %(default)s)")
    parser.add_argument("--base-url", default=BASE_URL, help="Confluence base URL (default: %(default)s)")
    parser.add_argument("--email", default=EMAIL, help="Confluence email for authentication")
    parser.add_argument("--api-token", default=API_TOKEN, help="Confluence API token for authentication")
    parser.add_argument("--attachments", action="store_true", help="Download page content with attachments")
    parser.add_argument("--local", action="store_true",
                        help="Use local page.v1.yaml and page.v2.yaml files instead of making API calls")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
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

    # Create processor and run
    processor = ConfluencePageProcessor(args)
    processor.run()


if __name__ == "__main__":
    main()
