#!/usr/bin/env python3
"""
Confluence Page Tree Generator

This script generates a list of all subpages from a specified document in a Confluence space.
Output format: page_id \t breadcrumbs \t title

By default, the script creates a directory for each page_id and saves:
- The document content in XHTML format as page.xhtml
- Page information in YAML format as page.yaml
- Child page information in YAML format as children.yaml
- Attachments are not downloaded by default

In local mode (--local flag), the script reads from the local YAML files instead of making API calls:
- Page information is read from page.yaml
- Child page information is read from children.yaml
- Navigation is performed using the information in these files

Usage examples:
  python pages_of_confluence.py
  python pages_of_confluence.py --page-id 123456789 --space-key DOCS
  python pages_of_confluence.py --email user@example.com --api-token your-api-token
  python pages_of_confluence.py --attachments  # Download page content with attachments
  python pages_of_confluence.py --local  # Use local YAML files instead of making API calls
"""

import requests
from requests.auth import HTTPBasicAuth
import sys
import os
import io
import argparse
import traceback
import yaml
import logging
import re

# Hidden characters constants
NBSP = '\u00A0'  # Non-Breaking Space
ZWSP = '\u200b'  # Zero Width Space
LRM = '\u200e'   # Left-to-Right Mark
HANGUL_FILLER = '\u3164'  # Hangul Filler

# Function to clean text by removing or replacing hidden characters
def clean_text(text):
    if text is None:
        return None
    
    # Replace NBSP with regular space
    text = text.replace(NBSP, ' ')
    
    # Remove ZWSP, LRM, and HANGUL_FILLER
    text = text.replace(ZWSP, '')
    text = text.replace(LRM, '')
    text = text.replace(HANGUL_FILLER, '')
    
    return text

# User configuration
BASE_URL = "https://querypie.atlassian.net/wiki"
SPACE_KEY = "QM"
DEFAULT_START_PAGE_ID = "608501837"  # Root Page ID of "QueryPie Docs"
EMAIL = "your-email@example.com"
API_TOKEN = "your-api-token"

# Parse command line arguments
parser = argparse.ArgumentParser(description="Generate a list of all subpages from a specified Confluence document")
parser.add_argument("--page-id", default=DEFAULT_START_PAGE_ID, help="ID of the starting page (default: %(default)s)")
parser.add_argument("--space-key", default=SPACE_KEY, help="Confluence space key (default: %(default)s)")
parser.add_argument("--base-url", default=BASE_URL, help="Confluence base URL (default: %(default)s)")
parser.add_argument("--email", default=EMAIL, help="Confluence email for authentication")
parser.add_argument("--api-token", default=API_TOKEN, help="Confluence API token for authentication")
parser.add_argument("--attachments", action="store_true", help="Download page content with attachments")
parser.add_argument("--local", action="store_true", help="Use local page.yaml files instead of making API calls")
parser.add_argument("--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    help="Set the logging level (default: %(default)s)")
args = parser.parse_args()

# Set up logging configuration
logging.basicConfig(
    level=getattr(logging, args.log_level),
    format='%(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Log the current configuration
logger.debug(f"Logging initialized with level: {args.log_level}")
logger.debug(f"Using base URL: {args.base_url}")
logger.debug(f"Using space key: {args.space_key}")
logger.debug(f"Starting with page ID: {args.page_id}")
logger.debug(f"Download attachments: {args.attachments}")
logger.debug(f"Using local mode: {args.local}")

# Set up authentication
auth = HTTPBasicAuth(args.email, args.api_token)
headers = {
    "Accept": "application/json"
}

# Function to save content to a file
def save_to_file(directory, filename, content):
    try:
        filepath = os.path.join(directory, filename)
        logger.info(f"Saving content to file: {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Error saving file {filepath}: {str(e)}")
        return False

# Function to download and save attachments
def download_attachments(page_id, directory):
    try:
        # Get attachments list
        attachment_url = f"{args.base_url}/rest/api/content/{page_id}/child/attachment"
        logger.info(f"Fetching attachments list from: {attachment_url}")
        response = requests.get(attachment_url, headers=headers, auth=auth)
        response.raise_for_status()
        attachments = response.json().get("results", [])
        logger.info(f"Found {len(attachments)} attachments for page ID {page_id}")
        
        # Save attachment information as YAML
        try:
            yaml_filepath = os.path.join(directory, "attachments.yaml")
            logger.info(f"Saving attachment information to: {yaml_filepath}")
            with open(yaml_filepath, 'w', encoding='utf-8') as f:
                yaml.dump(attachments, f, allow_unicode=True, sort_keys=False)
            logger.info(f"Saved attachment information to: {yaml_filepath}")
        except Exception as e:
            logger.error(f"Error saving attachment information as YAML: {str(e)}")
        
        for attachment in attachments:
            try:
                attachment_id = attachment["id"]
                filename = attachment["title"]
                download_url = f"{args.base_url}/rest/api/content/{page_id}/child/attachment/{attachment_id}/download"
                
                # Download attachment
                logger.info(f"Downloading attachment: {filename} from {download_url}")
                download_response = requests.get(download_url, headers={"Accept": "*/*"}, auth=auth)
                download_response.raise_for_status()
                
                # Save attachment
                filepath = os.path.join(directory, filename)
                logger.info(f"Saving attachment to: {filepath}")
                with open(filepath, 'wb') as f:
                    f.write(download_response.content)
                
                logger.info(f"Saved attachment: {filename}")
            except Exception as e:
                logger.error(f"Error downloading attachment {attachment.get('title', 'unknown')}: {str(e)}")
                # Continue with next attachment
        
        return True
    except Exception as e:
        logger.error(f"Error processing attachments for page ID {page_id}: {str(e)}")
        return False

# Function to process page data and generate output
# This function handles the common logic for processing page data from both API and local files
def process_page_data(page_id, data, directory=None, start_page_id=None):
    try:
        # Clean title by removing/replacing hidden characters
        title = clean_text(data["title"])
        ancestors = data.get("ancestors", [])
        
        # If this is the starting page or we don't have a start_page_id, use all ancestors
        if start_page_id is None or page_id == start_page_id:
            # Clean ancestor titles before adding them to the path
            path = [clean_text(a["title"]) for a in ancestors if a["type"] == "page"] + [title]
        else:
            # Filter out the starting page and its parent from the breadcrumbs
            filtered_ancestors = []
            found_start_page = False
            for ancestor in ancestors:
                if ancestor["type"] == "page":
                    if ancestor["id"] == start_page_id:
                        # Found the starting page
                        found_start_page = True
                        # Skip the starting page
                        continue
                    if not found_start_page:
                        # Skip ancestors that come before the starting page (parent documents)
                        continue
                    # Include ancestors that come after the starting page (sub-documents)
                    # Clean ancestor title before adding it to filtered_ancestors
                    filtered_ancestors.append(clean_text(ancestor["title"]))
            
            path = filtered_ancestors + [title]
        
        # Create breadcrumbs by joining the path elements
        breadcrumbs = " > ".join(path)
        
        logger.info(f"Processing page: {title} (ID: {page_id})")
        
        # Process file operations if directory is provided
        if directory:
            # Create directory for the page if it doesn't exist
            try:
                if not os.path.exists(directory):
                    logger.info(f"Creating directory: {directory}")
                    os.makedirs(directory)
            except Exception as e:
                logger.error(f"Error creating directory for page ID {page_id}: {str(e)}")
                # Continue processing even if directory creation fails
            
            # Save the data as YAML if not in local mode (already saved in local mode)
            if not args.local:
                try:
                    yaml_filepath = os.path.join(directory, "page.yaml")
                    logger.info(f"Saving page information to: {yaml_filepath}")
                    with open(yaml_filepath, 'w', encoding='utf-8') as f:
                        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
                    logger.info(f"Saved page information to: {yaml_filepath}")
                except Exception as e:
                    logger.error(f"Error saving page information as YAML: {str(e)}")
            
            # Save page content in XHTML format
            try:
                logger.info(f"Extracting XHTML content for page ID {page_id}")
                xhtml_content = data.get("body", {}).get("storage", {}).get("value", "")
                save_to_file(directory, "page.xhtml", xhtml_content)
            except Exception as e:
                logger.error(f"Error saving XHTML content for page ID {page_id}: {str(e)}")
            
            
            # Download and save attachments if specified and not in local mode
            if args.attachments and not args.local:
                logger.info(f"Downloading attachments for page ID {page_id}")
                download_attachments(page_id, directory)

        return {
            "id": page_id,
            "breadcrumbs": breadcrumbs,
            "title": title
        }
    except Exception as e:
        logger.error(f"Error processing page data for ID {page_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

# Function to read page data from local YAML file
# This function reads and returns the page data from the local page.yaml file
def read_local_page_data(page_id):
    try:
        directory = os.path.join(os.getcwd(), page_id)
        yaml_filepath = os.path.join(directory, "page.yaml")
        
        logger.info(f"Reading local page data from: {yaml_filepath}")
        
        if not os.path.exists(yaml_filepath):
            logger.error(f"Error: page.yaml not found for page ID {page_id}")
            return None
            
        logger.info(f"Opening file for reading: {yaml_filepath}")
        with open(yaml_filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        logger.info(f"Successfully loaded page data for ID {page_id}")
        return data
    except Exception as e:
        logger.error(f"Error reading local page data for ID {page_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

# Function to read children data from local YAML file
def read_local_children_data(page_id):
    try:
        directory = os.path.join(os.getcwd(), page_id)
        yaml_filepath = os.path.join(directory, "children.yaml")
        
        logger.info(f"Reading local children data from: {yaml_filepath}")
        
        if not os.path.exists(yaml_filepath):
            logger.warning(f"Warning: children.yaml not found for page ID {page_id}")
            # Create an empty children.yaml file with proper structure
            try:
                if not os.path.exists(directory):
                    logger.info(f"Creating directory: {directory}")
                    os.makedirs(directory)
                
                # Create empty children data structure
                empty_data = {"results": []}
                
                logger.info(f"Creating empty children.yaml for page ID {page_id}")
                with open(yaml_filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(empty_data, f, allow_unicode=True, sort_keys=False)
                
                logger.info(f"Created empty children.yaml for page ID {page_id}")
                return empty_data
            except Exception as e:
                logger.error(f"Error creating empty children.yaml for page ID {page_id}: {str(e)}")
                return None
            
        logger.info(f"Opening file for reading: {yaml_filepath}")
        with open(yaml_filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        logger.info(f"Successfully loaded children data for ID {page_id}")
        return data
    except Exception as e:
        logger.error(f"Error reading local children data for ID {page_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

# Function to find child pages from local directories
# This function reads children information from children.yaml
def find_local_child_pages(page_id):
    try:
        child_ids = []
        
        logger.info(f"Finding local child pages for page ID {page_id}")
        
        # Read the children.yaml file to get child page information
        children_data = read_local_children_data(page_id)
        
        if children_data and "results" in children_data:
            logger.info(f"Reading children information from children.yaml for {page_id}")
            for child in children_data["results"]:
                if "id" in child:
                    child_ids.append(child["id"])
                    logger.info(f"Found child page: {child['id']}")
        else:
            # Fallback to legacy method: try to read from page.yaml
            logger.info(f"Falling back to page.yaml for children information")
            data = read_local_page_data(page_id)
            if data and "children" in data and "page" in data["children"] and "results" in data["children"]["page"]:
                logger.info(f"Reading children information from page.yaml for {page_id}")
                for child in data["children"]["page"]["results"]:
                    if "id" in child:
                        child_ids.append(child["id"])
                        logger.info(f"Found child page: {child['id']}")
        
        # If no child pages were found, log a warning
        if not child_ids:
            logger.info(f"No child pages found for page ID {page_id}")
        else:
            logger.info(f"Found {len(child_ids)} child pages for page ID {page_id}")
        
        return child_ids
    except Exception as e:
        logger.error(f"Error finding local child pages for ID {page_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return []

# Function to get page data from API
def get_page_data_from_api(page_id):
    try:
        # Get page details with expanded content
        expand_params = "title,ancestors,body.storage,body.view"
        
        url = f"{args.base_url}/rest/api/content/{page_id}?expand={expand_params}"
        logger.info(f"Fetching page data from API: {url}")
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
        logger.info(f"Successfully fetched page data for ID {page_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching page data from API for ID {page_id}: {str(e)}")
        return None

# Function to get child page IDs from API
def get_child_page_ids_from_api(page_id):
    try:
        child_url = f"{args.base_url}/rest/api/content/{page_id}/child/page?limit=100"
        logger.info(f"Fetching child pages from API: {child_url}")
        child_response = requests.get(child_url, headers=headers, auth=auth)
        child_response.raise_for_status()
        child_data = child_response.json()
        
        # Save child data to children.yaml (even if there are no children)
        try:
            directory = os.path.join(os.getcwd(), page_id)
            if not os.path.exists(directory):
                logger.info(f"Creating directory: {directory}")
                os.makedirs(directory)
                
            yaml_filepath = os.path.join(directory, "children.yaml")
            logger.info(f"Saving children information to: {yaml_filepath}")
            with open(yaml_filepath, 'w', encoding='utf-8') as f:
                yaml.dump(child_data, f, allow_unicode=True, sort_keys=False)
            logger.info(f"Saved children information to: {yaml_filepath}")
        except Exception as e:
            logger.error(f"Error saving children information as YAML: {str(e)}")
        
        child_ids = [child["id"] for child in child_data.get("results", [])]
        if not child_ids:
            logger.info(f"No child pages found for page ID {page_id}, but children.yaml was still created")
        else:
            logger.info(f"Found {len(child_ids)} child pages for page ID {page_id}")
        return child_ids
    except Exception as e:
        logger.error(f"Error fetching child pages from API for ID {page_id}: {str(e)}")
        return []

# Generic recursive function to fetch page tree
def fetch_page_tree_generic(page_id, get_data_func, get_children_func, start_page_id=None):
    try:
        logger.info(f"Processing page tree for page ID {page_id}")
        
        # If start_page_id is not provided, use the current page_id as the starting point
        if start_page_id is None:
            start_page_id = page_id
        
        # Get page data using the provided function
        data = get_data_func(page_id)
        
        if data:
            # Process the page data
            directory = os.path.join(os.getcwd(), page_id)
            page_info = process_page_data(page_id, data, directory, start_page_id)
            
            if page_info:
                yield page_info

                # Find and process child pages using the provided function
                child_ids = get_children_func(page_id)
                for child_id in child_ids:
                    yield from fetch_page_tree_generic(child_id, get_data_func, get_children_func, start_page_id)
    except Exception as e:
        logger.error(f"Error processing page ID {page_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        # Continue with next pages

# Recursive function to fetch page tree from API
def fetch_page_tree_api(page_id, start_page_id=None):
    yield from fetch_page_tree_generic(
        page_id,
        get_page_data_from_api,
        get_child_page_ids_from_api,
        start_page_id
    )

# Recursive function to fetch page tree from local files
def fetch_page_tree_local(page_id, start_page_id=None):
    yield from fetch_page_tree_generic(
        page_id,
        read_local_page_data,
        find_local_child_pages,
        start_page_id
    )

# Main function to fetch page tree (decides which mode to use)
def fetch_page_tree(page_id, start_page_id=None):
    # If start_page_id is not provided, use the page_id as the starting point
    if start_page_id is None:
        start_page_id = page_id
        
    if args.local:
        # Use local mode: read from local page.yaml files
        yield from fetch_page_tree_local(page_id, start_page_id)
    else:
        # Use API mode: fetch data from the Confluence API
        yield from fetch_page_tree_api(page_id, start_page_id)

# Output to stdout in tab-separated format
try:
    logger.info(f"Starting to fetch page tree from page ID: {args.page_id}")
    page_count = 0
    for page in fetch_page_tree(args.page_id):
        print(f"{page['id']}\t{page['breadcrumbs']}\t{page['title']}")
        page_count += 1
    logger.info(f"Completed processing {page_count} pages")
except Exception as e:
    logger.critical(f"Fatal error: {str(e)}")
    print(f"Fatal error: {str(e)}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

