#!/usr/bin/env python3
"""
Confluence Page Tree Generator

This script generates a list of all subpages from a specified document in a Confluence space.
Output format: page_id \t breadcrumbs \t title

By default, the script also creates a directory for each page_id and saves:
- The document content in XHTML format as page.xhtml
- The document content in Markdown format as page.md
- All attachments, if any

Usage examples:
  python pages_of_confluence.py
  python pages_of_confluence.py --page-id 123456789 --space-key DOCS
  python pages_of_confluence.py --email user@example.com --api-token your-api-token
  python pages_of_confluence.py --list-only  # Only output the list without downloading files
"""

import requests
from requests.auth import HTTPBasicAuth
import sys
import os
import io
import argparse
import traceback

# User configuration
BASE_URL = "https://querypie.atlassian.net/wiki"
SPACE_KEY = "QM"
DEFAULT_START_PAGE_ID = "608501837"  # Root Page ID for "QueryPie Docs"
EMAIL = "your-email@example.com"
API_TOKEN = "your-api-token"

# Parse command line arguments
parser = argparse.ArgumentParser(description="Generate a list of all subpages from a specified Confluence document")
parser.add_argument("--page-id", default=DEFAULT_START_PAGE_ID, help="ID of the starting page (default: %(default)s)")
parser.add_argument("--space-key", default=SPACE_KEY, help="Confluence space key (default: %(default)s)")
parser.add_argument("--base-url", default=BASE_URL, help="Confluence base URL (default: %(default)s)")
parser.add_argument("--email", default=EMAIL, help="Confluence email for authentication")
parser.add_argument("--api-token", default=API_TOKEN, help="Confluence API token for authentication")
parser.add_argument("--list-only", action="store_true", help="Only output the list of pages without downloading content or attachments")
args = parser.parse_args()

# Set up authentication
auth = HTTPBasicAuth(args.email, args.api_token)
headers = {
    "Accept": "application/json"
}

# Function to save content to a file
def save_to_file(directory, filename, content):
    try:
        filepath = os.path.join(directory, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error saving file {filepath}: {str(e)}", file=sys.stderr)
        return False

# Function to download and save attachments
def download_attachments(page_id, directory):
    try:
        # Get attachments list
        attachment_url = f"{args.base_url}/rest/api/content/{page_id}/child/attachment"
        response = requests.get(attachment_url, headers=headers, auth=auth)
        response.raise_for_status()
        attachments = response.json().get("results", [])
        
        for attachment in attachments:
            try:
                attachment_id = attachment["id"]
                filename = attachment["title"]
                download_url = f"{args.base_url}/rest/api/content/{page_id}/child/attachment/{attachment_id}/download"
                
                # Download attachment
                download_response = requests.get(download_url, headers={"Accept": "*/*"}, auth=auth)
                download_response.raise_for_status()
                
                # Save attachment
                filepath = os.path.join(directory, filename)
                with open(filepath, 'wb') as f:
                    f.write(download_response.content)
                
                print(f"Saved attachment: {filename}", file=sys.stderr)
            except Exception as e:
                print(f"Error downloading attachment {attachment.get('title', 'unknown')}: {str(e)}", file=sys.stderr)
                # Continue with next attachment
        
        return True
    except Exception as e:
        print(f"Error processing attachments for page ID {page_id}: {str(e)}", file=sys.stderr)
        return False

# Recursive function to track navigation path
def fetch_page_tree(page_id):
    try:
        # Get page details with expanded content
        # Only fetch body content if not in list-only mode
        expand_params = "title,ancestors"
        if not args.list_only:
            expand_params += ",body.storage,body.view"
        
        url = f"{args.base_url}/rest/api/content/{page_id}?expand={expand_params}"
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
        data = response.json()
        
        title = data["title"]
        ancestors = data.get("ancestors", [])
        path = [a["title"] for a in ancestors if a["type"] == "page"] + [title]
        breadcrumbs = " > ".join(path)
        
        # Skip file operations if list-only mode is enabled
        if not args.list_only:
            # Create directory for the page
            directory = os.path.join(os.getcwd(), page_id)
            try:
                if not os.path.exists(directory):
                    os.makedirs(directory)
            except Exception as e:
                print(f"Error creating directory for page ID {page_id}: {str(e)}", file=sys.stderr)
                # Continue processing even if directory creation fails
            
            # Save page content in XHTML format
            try:
                xhtml_content = data.get("body", {}).get("storage", {}).get("value", "")
                save_to_file(directory, "page.xhtml", xhtml_content)
            except Exception as e:
                print(f"Error saving XHTML content for page ID {page_id}: {str(e)}", file=sys.stderr)
            
            # Get and save page content in Markdown format
            try:
                # Use the Confluence API to get content in Markdown format
                view_content = data.get("body", {}).get("view", {}).get("value", "")
                
                # For simplicity, we're using the view content as a basic approximation
                # A more accurate conversion would require a proper HTML to Markdown converter
                save_to_file(directory, "page.md", view_content)
            except Exception as e:
                print(f"Error saving Markdown content for page ID {page_id}: {str(e)}", file=sys.stderr)
            
            # Download and save attachments
            download_attachments(page_id, directory)

        yield {
            "id": page_id,
            "breadcrumbs": breadcrumbs,
            "title": title
        }

        # Explore child pages
        child_url = f"{args.base_url}/rest/api/content/{page_id}/child/page?limit=100"
        child_response = requests.get(child_url, headers=headers, auth=auth)
        child_response.raise_for_status()
        child_data = child_response.json()

        for child in child_data.get("results", []):
            child_id = child["id"]
            yield from fetch_page_tree(child_id)
    except Exception as e:
        print(f"Error processing page ID {page_id}: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # Continue with next pages

# Output to stdout in tab-separated format
try:
    for page in fetch_page_tree(args.page_id):
        print(f"{page['id']}\t{page['breadcrumbs']}\t{page['title']}")
except Exception as e:
    print(f"Fatal error: {str(e)}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

