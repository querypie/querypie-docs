#!/usr/bin/env python3
"""
Find MDX files containing specific text and generate Confluence links

This script:
1. Searches for MDX files in src/content/ko/ containing a specific text
2. Matches found files with pages.yaml to get page information
3. Generates Confluence document links

Usage:
    python3 find_mdx_with_text.py [search_text]

Example:
    python3 find_mdx_with_text.py "Unsupported xhtml node:"
    python3 find_mdx_with_text.py "특정 문구"
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

# Confluence base URL
CONFLUENCE_BASE_URL = "https://querypie.atlassian.net/wiki/spaces/QM/pages"


def find_mdx_files_with_text(content_dir: Path, search_text: str) -> List[Path]:
    """
    Find all MDX files containing the search text
    
    Args:
        content_dir: Directory to search in (e.g., src/content/ko)
        search_text: Text to search for
        
    Returns:
        List of Path objects for matching MDX files
    """
    matching_files = []
    
    if not content_dir.exists():
        logging.error(f"Content directory does not exist: {content_dir}")
        return matching_files
    
    # Search all .mdx files recursively
    for mdx_file in content_dir.rglob("*.mdx"):
        try:
            with open(mdx_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if search_text in content:
                    matching_files.append(mdx_file)
                    logging.debug(f"Found match in: {mdx_file}")
        except Exception as e:
            logging.warning(f"Error reading {mdx_file}: {e}")
    
    return matching_files


def get_path_from_mdx_file(mdx_file: Path, content_base: Path) -> List[str]:
    """
    Extract path list from MDX file path
    
    Args:
        mdx_file: Path to the MDX file
        content_base: Base content directory (e.g., src/content/ko)
        
    Returns:
        List of path components (e.g., ["user-manual", "server-access-control"])
    """
    try:
        # Get relative path from content base
        relative_path = mdx_file.relative_to(content_base)
        
        # Remove file extension
        path_str = str(relative_path).replace('.mdx', '')
        
        # Split into components
        path_components = path_str.split(os.sep)
        
        # Filter out empty strings and special files
        path_components = [p for p in path_components if p and not p.startswith('_')]
        
        return path_components
    except Exception as e:
        logging.warning(f"Error extracting path from {mdx_file}: {e}")
        return []


def load_pages_yaml(yaml_path: Path) -> Dict[str, Dict]:
    """
    Load pages.yaml and create a mapping by path
    
    Args:
        yaml_path: Path to pages.yaml file
        
    Returns:
        Dictionary mapping path tuple to page info
    """
    pages_by_path = {}
    
    if not yaml_path.exists():
        logging.error(f"pages.yaml not found: {yaml_path}")
        return pages_by_path
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
            
            if isinstance(yaml_data, list):
                for page in yaml_data:
                    if not isinstance(page, dict):
                        continue
                    
                    path = page.get('path')
                    if not path or not isinstance(path, list):
                        continue
                    
                    # Convert path list to tuple for use as dictionary key
                    path_tuple = tuple(path)
                    pages_by_path[path_tuple] = page
                    
        logging.info(f"Loaded {len(pages_by_path)} pages from {yaml_path}")
    except Exception as e:
        logging.error(f"Error loading pages.yaml: {e}")
    
    return pages_by_path


def find_page_by_path(pages_by_path: Dict, mdx_path: List[str]) -> Optional[Dict]:
    """
    Find page information by matching path
    
    Args:
        pages_by_path: Dictionary mapping path tuples to page info
        mdx_path: Path components from MDX file
        
    Returns:
        Page info dictionary if found, None otherwise
    """
    # Try exact match first
    path_tuple = tuple(mdx_path)
    if path_tuple in pages_by_path:
        return pages_by_path[path_tuple]
    
    # Try matching from the end (in case of nested structures)
    # For example, if mdx_path is ["user-manual", "server-access-control"]
    # and pages.yaml has ["administrator-manual", "servers", "server-access-control"]
    # we might want to match the last component
    
    # Try matching the last N components
    for i in range(len(mdx_path)):
        partial_path = tuple(mdx_path[i:])
        if partial_path in pages_by_path:
            return pages_by_path[partial_path]
    
    return None


def generate_confluence_link(page_id: str) -> str:
    """
    Generate Confluence document link
    
    Args:
        page_id: Confluence page ID
        
    Returns:
        Confluence URL
    """
    return f"{CONFLUENCE_BASE_URL}/{page_id}"


def main():
    parser = argparse.ArgumentParser(
        description="Find MDX files containing specific text and generate Confluence links"
    )
    parser.add_argument(
        'search_text',
        nargs='?',
        default='Unsupported xhtml node:',
        help='Text to search for in MDX files (default: "Unsupported xhtml node:")'
    )
    parser.add_argument(
        '--content-dir',
        type=str,
        default='src/content/ko',
        help='Content directory to search (default: src/content/ko)'
    )
    parser.add_argument(
        '--pages-yaml',
        type=str,
        default='var/pages.yaml',
        help='Path to pages.yaml file (default: var/pages.yaml)'
    )
    parser.add_argument(
        '--workspace-root',
        type=str,
        help='Workspace root directory (default: script directory parent)'
    )
    
    args = parser.parse_args()
    
    # Determine workspace root
    if args.workspace_root:
        workspace_root = Path(args.workspace_root)
    else:
        # Default: assume script is in confluence-mdx/bin/, so workspace root is two levels up
        script_dir = Path(__file__).parent
        workspace_root = script_dir.parent.parent
    
    # Resolve paths
    content_dir = workspace_root / args.content_dir
    pages_yaml_path = workspace_root / 'confluence-mdx' / args.pages_yaml
    
    logging.info(f"Searching for text: '{args.search_text}'")
    logging.info(f"Content directory: {content_dir}")
    logging.info(f"Pages YAML: {pages_yaml_path}")
    
    # Find MDX files containing the search text
    matching_files = find_mdx_files_with_text(content_dir, args.search_text)
    
    if not matching_files:
        print(f"No MDX files found containing: '{args.search_text}'")
        return 0
    
    print(f"\nFound {len(matching_files)} MDX file(s) containing '{args.search_text}':\n")
    
    # Load pages.yaml
    pages_by_path = load_pages_yaml(pages_yaml_path)
    
    if not pages_by_path:
        logging.error("No pages loaded from pages.yaml. Cannot generate links.")
        return 1
    
    # Find matching pages and generate links
    results = []
    for mdx_file in matching_files:
        mdx_path = get_path_from_mdx_file(mdx_file, content_dir)
        page_info = find_page_by_path(pages_by_path, mdx_path)
        
        if page_info:
            page_id = page_info.get('page_id')
            title = page_info.get('title', 'Unknown')
            title_orig = page_info.get('title_orig', 'Unknown')
            confluence_link = generate_confluence_link(page_id)
            
            results.append({
                'mdx_file': mdx_file.relative_to(workspace_root),
                'path': mdx_path,
                'page_id': page_id,
                'title': title,
                'title_orig': title_orig,
                'link': confluence_link
            })
        else:
            results.append({
                'mdx_file': mdx_file.relative_to(workspace_root),
                'path': mdx_path,
                'page_id': None,
                'title': None,
                'title_orig': None,
                'link': None
            })
    
    # Print results
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['mdx_file']}")
        print(f"   Path: {'/'.join(result['path'])}")
        if result['page_id']:
            print(f"   Title: {result['title']} (orig: {result['title_orig']})")
            print(f"   Page ID: {result['page_id']}")
            print(f"   Confluence Link: {result['link']}")
        else:
            print(f"   ⚠️  No matching page found in pages.yaml")
        print()
    
    # Summary
    found_count = sum(1 for r in results if r['page_id'])
    not_found_count = len(results) - found_count
    
    print(f"\nSummary:")
    print(f"  Total files found: {len(results)}")
    print(f"  Pages matched: {found_count}")
    print(f"  Pages not found: {not_found_count}")
    
    return 0 if not_found_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

