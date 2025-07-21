#!/usr/bin/env python3
import argparse
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
import sys
import os
from collections import defaultdict

ZWSP = '\u200b'

# Parse sitemap.xml and extract all URLs
def parse_sitemap(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    ns = {'ns': root.tag.split('}')[0].strip('{')}
    urls = [url.find('ns:loc', ns).text.strip() for url in root.findall('ns:url', ns)]
    return urls

# Extract and format breadcrumbs from soup object and current url
# Returns a formatted breadcrumb string
def extract_breadcrumbs(soup, current_url):
    """
    Extract and format breadcrumbs from soup object and current url.
    Returns a formatted breadcrumb string.
    - Each breadcrumb is formatted as [Title](/uri/path)
    - The first breadcrumb 'QueryPie Docs for v10' is removed if present
    - The path '/querypie-manual/11.0.0/' is replaced with './'
    - Any '../../../ko' or similar parent references are removed
    - All paths are made relative to './'
    - ZWSP (U+200B) is removed from titles
    - Newline characters in breadcrumb items are replaced with space
    """
    breadcrumbs = []
    ol = soup.find('ol', class_='breadcrumbs')
    if ol:
        for li in ol.find_all('li'):
            a = li.find('a')
            if a:
                text = a.get_text(separator=' ', strip=True).replace('\n', ' ').replace('\r', ' ')
                href = a.get('href', '')
                # Remove parent directory references and 'ko' from href
                # Also remove any ../../../ko or similar
                parts = [part for part in href.split('/') if part not in ('..', '.', '', 'ko', 'en', 'ja')]
                href_clean = '/' + '/'.join(parts) if parts else '/'
                # Replace /querypie-manual/11.0.0/ with ./
                href_clean = href_clean.replace('/querypie-manual/11.0.0/', './')
                breadcrumbs.append(f'[{text}]({href_clean})')
    # Remove first breadcrumb if it is 'QueryPie Docs for v10'
    if breadcrumbs and breadcrumbs[0].startswith('[QueryPie Docs for v10]'):
        breadcrumbs = breadcrumbs[1:]
    # Replace any newline in breadcrumb items with space and remove ZWSP
    breadcrumbs = [b.replace('\n', ' ').replace('\r', ' ').replace(ZWSP, '') for b in breadcrumbs]
    breadcrumb_str = '/'.join(breadcrumbs)
    return breadcrumb_str

# Visit the URL and extract the document title and breadcrumbs
# Returns (title, breadcrumb_str, error_message)
def fetch_title_and_breadcrumbs(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        # Extract the document title
        title = soup.title.string if soup.title else ''
        if title:
            title = title.replace('\n', ' ').replace('\r', ' ').strip()
        else:
            title = ''
        # Remove any newline characters from title
        title = title.replace('\n', ' ').replace('\r', ' ')
        # Remove ZWSP from title
        title = title.replace(ZWSP, '')
        # Extract breadcrumbs using the refactored function
        breadcrumb_str = extract_breadcrumbs(soup, url)
        return title, breadcrumb_str, None
    except Exception as e:
        # Return error message if any exception occurs
        return '', '', str(e)

# Main function for CLI
# Handles argument parsing, file writing, and error counting
def main():
    parser = argparse.ArgumentParser(description='TOC generator based on sitemap.xml')
    parser.add_argument('filename', help='Path to sitemap.xml file')
    args = parser.parse_args()

    urls = parse_sitemap(args.filename)
    total = len(urls)
    error_count = 0
    error_types = defaultdict(int)

    # Output files in the same directory as sitemap.xml
    base_dir = os.path.dirname(os.path.abspath(args.filename))
    urls_path = os.path.join(base_dir, 'urls.txt')
    titles_path = os.path.join(base_dir, 'titles.txt')
    breadcrumbs_path = os.path.join(base_dir, 'breadcrumbs.txt')

    # Write all URLs to urls.txt
    with open(urls_path, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(url.strip() + '\n')

    # For each URL, fetch title and breadcrumbs, and write to files
    with open(titles_path, 'w', encoding='utf-8') as ft, \
         open(breadcrumbs_path, 'w', encoding='utf-8') as fb:
        for idx, url in enumerate(urls, 1):
            title, breadcrumb, error = fetch_title_and_breadcrumbs(url)
            if error:
                error_count += 1
                error_type = error.split(':')[0] if ':' in error else error
                error_types[error_type] += 1
                title = ''
                breadcrumb = ''
            ft.write(title + '\n')
            fb.write(breadcrumb + '\n')
            # Print progress for each URL
            print(f'[{idx}/{total}] {url} - {"ERROR" if error else "OK"}')

    # Print summary of results
    print(f'Total documents: {total}')
    print(f'Error count: {error_count}')
    if error_count > 0:
        print('Error types:')
        for etype, cnt in error_types.items():
            print(f'  {etype}: {cnt}')
    print('Done')

if __name__ == '__main__':
    main() 