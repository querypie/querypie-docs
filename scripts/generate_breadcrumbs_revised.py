#!/usr/bin/env python3
import argparse
import re
import os

# Convert English title to slug (remove articles, lowercase, hyphenate)
def slugify(title):
    title = title.lower()
    # Remove articles and unnecessary words
    title = re.sub(r'\b(a|the|an|to|of|in|for|and|by|on|at|with|from|as|is|are|was|were|be|has|have|had|will|shall|can|may|do|does|did|but|or|nor|so|yet|that|this|these|those|it|its|their|his|her|our|your|my|mine|yours|ours|theirs|hers|him|them|us|you|i|he|she|we|they)\b', '', title)
    title = re.sub(r'[^a-z0-9\s-]', '', title)
    title = re.sub(r'\s+', '-', title.strip())
    title = re.sub(r'-+', '-', title)
    return title

# Parse breadcrumbs: extract [title](uri) as list of (title, uri)
def parse_breadcrumbs(breadcrumbs):
    return re.findall(r'\[([^\]]+)\]\([^\)]*\)', breadcrumbs)

def main():
    parser = argparse.ArgumentParser(description='Generate revised breadcrumbs file.')
    parser.add_argument('--breadcrumbs', required=True, help='Input breadcrumbs.txt path')
    parser.add_argument('--titles', required=True, help='Input titles.txt path')
    parser.add_argument('--titles_en', required=True, help='Input titles.en.txt path')
    parser.add_argument('--output', required=True, help='Output breadcrumbs.revised.txt path')
    args = parser.parse_args()

    # URL -> Korean title
    url2title_ko = {}
    with open(args.titles, encoding='utf-8') as f:
        for line in f:
            if '\t' not in line:
                continue
            url, title = line.rstrip().split('\t', 1)
            url2title_ko[url] = title.strip()

    # URL -> English title
    url2title_en = {}
    with open(args.titles_en, encoding='utf-8') as f:
        for line in f:
            if '\t' not in line:
                continue
            url, title = line.rstrip().split('\t', 1)
            url2title_en[url] = title.strip()

    # Read breadcrumbs.txt
    with open(args.breadcrumbs, encoding='utf-8') as f:
        lines = [line.rstrip() for line in f if line.strip()]

    results = []
    for line in lines:
        if '\t' not in line:
            url = line.strip()
            breadcrumbs = ''
        else:
            url, breadcrumbs = line.split('\t', 1)

        # Parse breadcrumbs: list of Korean titles
        items_ko = parse_breadcrumbs(breadcrumbs) if breadcrumbs else []
        # For each, get English title for slug
        # For root, use the first item, for next, accumulate
        # Add last item (the page itself)
        page_title_ko = url2title_ko.get(url, '')
        page_title_en = url2title_en.get(url, '')
        items_ko.append(page_title_ko)
        items_en = [url2title_en.get(url, '') for url in [url]*len(items_ko)]
        # Actually, for each breadcrumb, we need to get the English title for slug
        # But only the last one is the current page, others are from the breadcrumb itself
        # So, for each breadcrumb, use the Korean title for display, and English for slug
        # For the breadcrumb path, we need to build the URI step by step
        uri_parts = []
        breadcrumbs_new = []
        for i, title_ko in enumerate(items_ko):
            # For slug, use English title if available, else slugify Korean
            if i < len(items_ko)-1:
                # For breadcrumb, try to get English translation for this breadcrumb
                # If not available, fallback to slugify Korean
                title_en = ''
                # Try to find the corresponding English title for this breadcrumb
                # We can only do this if the breadcrumb matches a known title
                for url_key, t_ko in url2title_ko.items():
                    if t_ko == title_ko:
                        title_en = url2title_en.get(url_key, '')
                        break
                slug = slugify(title_en) if title_en else slugify(title_ko)
            else:
                # Last item: current page
                slug = slugify(page_title_en) if page_title_en else slugify(page_title_ko)
            if slug:
                uri_parts.append(slug)
            uri = '/' + '/'.join(uri_parts)
            breadcrumbs_new.append(f'[{title_ko}]({uri})')
        results.append(f'{url}\t' + '/'.join(breadcrumbs_new))

    with open(args.output, 'w', encoding='utf-8') as f:
        for line in results:
            f.write(line + '\n')

if __name__ == '__main__':
    main()
