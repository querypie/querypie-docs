"""Confluence page processing orchestrator."""

import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Dict, Generator, List, Optional

from fetch.config import Config
from fetch.api_client import ApiClient
from fetch.file_manager import FileManager
from fetch.translation import TranslationService
from fetch.stages import Stage1Processor, Stage2Processor, Stage3Processor, Stage4Processor
from fetch.models import Page
from text_utils import slugify


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

    def fetch_page_tree_recursive(self, page_id: str, start_page_id: Optional[str] = None, use_local: bool = False) -> Generator[Page, None, None]:
        """Recursively fetch page tree through all 4 stages"""
        try:
            self.logger.info(f"Processing page tree for page ID {page_id}")

            # If start_page_id is not provided, use the current page_id as the starting point
            if start_page_id is None:
                start_page_id = page_id

            # Process current page through all 4 stages
            if use_local:
                # In local mode, skip Stage 1 (API calls) and Stage 3 (attachment download)
                # Only process Stage 2 (content extraction) and Stage 4 (document listing)
                self.stage2.process(page_id)
                page = self.stage4.process(page_id, start_page_id)
            else:
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
                    yield from self.fetch_page_tree_recursive(child_id, start_page_id, use_local)
        except Exception as e:
            self.logger.error(f"Error processing page ID {page_id}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def _get_fetch_state_path(self, start_page_id: str) -> str:
        """Return the path to the fetch state file for a specific start_page_id."""
        return os.path.join(self.config.default_output_dir, start_page_id, "fetch_state.yaml")

    def _load_fetch_state(self, start_page_id: str) -> Dict:
        """Load fetch state from var/<start_page_id>/fetch_state.yaml."""
        state_path = self._get_fetch_state_path(start_page_id)
        state = self.file_manager.load_yaml(state_path)
        return state if state else {}

    def _save_fetch_state(self, start_page_id: str, state: Dict) -> None:
        """Save fetch state to var/<start_page_id>/fetch_state.yaml."""
        state_path = self._get_fetch_state_path(start_page_id)
        self.file_manager.save_yaml(state_path, state)
        self.logger.warning(f"Fetch state saved to {state_path}")

    def _is_page_current(self, page_id: str, api_version_number: int) -> bool:
        """Check if local page data matches the API version number."""
        v2_path = os.path.join(self.config.default_output_dir, page_id, "page.v2.yaml")
        try:
            v2_data = self.file_manager.load_yaml(v2_path)
            if not v2_data or "version" not in v2_data:
                return False
            local_version = v2_data["version"].get("number")
            if local_version is not None and int(local_version) == int(api_version_number):
                self.logger.info(f"Skipped page {page_id} (local version {local_version} matches API)")
                return True
            self.logger.info(f"Page {page_id} needs update: local version {local_version} != API version {api_version_number}")
            return False
        except Exception:
            return False

    def _compute_max_modified_date(self, page_ids: List[str]) -> Optional[str]:
        """Scan page.v2.yaml files for the given page IDs and return the maximum version.createdAt."""
        max_date = None
        for page_id in page_ids:
            v2_path = os.path.join(self.config.default_output_dir, page_id, "page.v2.yaml")
            try:
                v2_data = self.file_manager.load_yaml(v2_path)
                if v2_data and "version" in v2_data:
                    created_at = v2_data["version"].get("createdAt")
                    if created_at and (max_date is None or created_at > max_date):
                        max_date = created_at
            except Exception:
                continue
        return max_date

    def run(self) -> None:
        """Main execution function"""
        try:
            # Check if output directory exists
            if not os.path.exists(self.config.default_output_dir):
                self.file_manager.ensure_directory(self.config.default_output_dir)
                self.logger.info(f"Created output directory: {self.config.default_output_dir}")

            # Prepare output file path
            output_yaml_path = os.path.join(self.config.default_output_dir, "pages.yaml")
            output_list_path = os.path.join(self.config.default_output_dir, "list.txt")

            start_page_id = self.config.default_start_page_id

            # Handle different modes
            if self.config.mode == "recent":
                # --recent mode: Download recently modified pages first, then process like --local
                since_date = None
                effective_days = 21  # default fallback

                if self.config.days is not None:
                    # User explicitly specified --days, use it directly
                    effective_days = self.config.days
                    self.logger.warning(f"Recent mode: Fetching pages modified in last {effective_days} days (--days specified)")
                else:
                    # Auto-detect from fetch state
                    fetch_state = self._load_fetch_state(start_page_id)
                    since_date = fetch_state.get("last_modified_seen")
                    if since_date:
                        try:
                            parsed = datetime.fromisoformat(since_date.replace("Z", "+00:00"))
                            days_ago = (datetime.now(timezone.utc) - parsed).days
                            self.logger.warning(f"Recent mode: Auto-detected since_date {since_date} from fetch_state.yaml (~{days_ago} days ago)")
                        except Exception:
                            self.logger.warning(f"Recent mode: Auto-detected since_date {since_date} from fetch_state.yaml")
                    else:
                        self.logger.warning(f"Recent mode: No fetch state for start_page_id {start_page_id}, using default {effective_days} days")

                modified_pages = self.api_client.get_recently_modified_pages(
                    days=effective_days,
                    space_key=self.config.space_key,
                    since_date=since_date
                )

                # Exclude specific page_id from collection (576585864)
                # 576585864 - https://querypie.atlassian.net/wiki/spaces/QM/overview
                excluded_page_id = "576585864"
                original_count = len(modified_pages)
                modified_pages = [p for p in modified_pages if p["id"] != excluded_page_id]
                if original_count != len(modified_pages):
                    self.logger.info(f"Excluded page ID {excluded_page_id} from collection ({original_count} -> {len(modified_pages)} pages)")

                # Download each page through all 4 stages and output to stdout
                # Store downloaded pages for list.txt
                self.logger.warning(f"Downloading {len(modified_pages)} recently modified pages")
                downloaded_list_lines = []
                skipped_count = 0
                for entry in modified_pages:
                    page_id = entry["id"]
                    api_version = entry.get("version_number")
                    try:
                        # Skip if local data already matches the latest version
                        if api_version is not None and self._is_page_current(page_id, api_version):
                            skipped_count += 1
                            continue

                        page = self.process_page_complete(page_id, start_page_id)
                        if page:
                            # Update translations if available
                            if self.translation_service.translations:
                                self.translation_service.translate_page(page)
                            else:
                                page.breadcrumbs_en = page.breadcrumbs
                                page.path = [slugify(crumb) for crumb in page.breadcrumbs]

                            # Output to stdout during download
                            breadcrumbs_str = " />> ".join(page.breadcrumbs) if page.breadcrumbs else ""
                            print(f"{page.page_id}\t{breadcrumbs_str}")
                            # Store for list.txt (only downloaded pages)
                            downloaded_list_lines.append(f"{page.page_id}\t{breadcrumbs_str}\n")
                    except Exception as e:
                        self.logger.error(f"Error downloading page ID {page_id}: {str(e)}")
                        continue

                if skipped_count > 0:
                    self.logger.warning(f"Skipped {skipped_count} pages (already up-to-date)")

                # After downloading, process like local mode (hierarchical traversal from start_page_id)
                # Generate pages.yaml and list.txt with full hierarchical tree (like --local mode)
                # No stdout output in this phase (like --local mode)
                self.logger.warning(f"Processing page tree from start page ID {start_page_id} (local mode)")
                page_count = 0
                yaml_entries = []
                list_lines = []

                for page in self.fetch_page_tree_recursive(start_page_id, start_page_id, use_local=True):
                    if page:
                        breadcrumbs_str = " />> ".join(page.breadcrumbs) if page.breadcrumbs else ""
                        # No stdout output in local mode
                        # Exclude start_page_id from list.txt (root page is not converted to MDX)
                        if page.page_id != start_page_id:
                            list_lines.append(f"{page.page_id}\t{breadcrumbs_str}\n")
                        page_count += 1
                        yaml_entries.append(page.to_dict())

            elif self.config.mode == "local":
                # --local mode: Process existing local files hierarchically from start_page_id
                # No stdout output in local mode
                self.logger.warning(f"Local mode: Processing page tree from start page ID {start_page_id}")
                page_count = 0
                yaml_entries = []
                list_lines = []

                for page in self.fetch_page_tree_recursive(start_page_id, start_page_id, use_local=True):
                    if page:
                        breadcrumbs_str = " />> ".join(page.breadcrumbs) if page.breadcrumbs else ""
                        # No stdout output in local mode
                        # Exclude start_page_id from list.txt (root page is not converted to MDX)
                        if page.page_id != start_page_id:
                            list_lines.append(f"{page.page_id}\t{breadcrumbs_str}\n")
                        page_count += 1
                        yaml_entries.append(page.to_dict())

            elif self.config.mode == "remote":
                # --remote mode: Download and process hierarchically from start_page_id via API
                # Output to stdout during download
                self.logger.warning(f"Remote mode: Processing page tree from start page ID {start_page_id} via API")
                page_count = 0
                yaml_entries = []
                list_lines = []

                for page in self.fetch_page_tree_recursive(start_page_id, start_page_id, use_local=False):
                    if page:
                        breadcrumbs_str = " />> ".join(page.breadcrumbs) if page.breadcrumbs else ""
                        # Exclude start_page_id from stdout and list.txt (root page is not converted to MDX)
                        if page.page_id != start_page_id:
                            print(f"{page.page_id}\t{breadcrumbs_str}")
                            list_lines.append(f"{page.page_id}\t{breadcrumbs_str}\n")
                        page_count += 1
                        yaml_entries.append(page.to_dict())

            # Update fetch state for remote and recent modes
            if self.config.mode in ("remote", "recent") and yaml_entries:
                all_page_ids = [entry['page_id'] for entry in yaml_entries]
                max_modified = self._compute_max_modified_date(all_page_ids)
                if max_modified:
                    prev_state = self._load_fetch_state(start_page_id)
                    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

                    new_state = {
                        "last_modified_seen": max_modified,
                        "pages_fetched": len(yaml_entries),
                    }

                    if self.config.mode == "remote":
                        new_state["last_full_fetch"] = now
                        new_state["last_recent_fetch"] = prev_state.get("last_recent_fetch")
                    else:  # recent
                        new_state["last_full_fetch"] = prev_state.get("last_full_fetch")
                        new_state["last_recent_fetch"] = now

                    self._save_fetch_state(start_page_id, new_state)
                    self.logger.info(f"Updated fetch state: last_modified_seen={max_modified}, pages_fetched={len(yaml_entries)}")

            # Save YAML file
            if yaml_entries:
                self.file_manager.save_yaml(output_yaml_path, yaml_entries)
                self.logger.info(f"YAML data saved to {output_yaml_path}")

            # Save list.txt file
            if list_lines:
                self.file_manager.save_file(output_list_path, "".join(list_lines))
                self.logger.info(f"List file saved to {output_list_path}")

            self.logger.info(f"Completed processing {page_count} pages")
        except Exception as e:
            self.logger.error(f"Error in main execution: {str(e)}")
            self.logger.debug(traceback.format_exc())
            sys.exit(1)
