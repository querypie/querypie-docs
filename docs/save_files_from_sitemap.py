#!/usr/bin/env python3
import argparse
import os
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import defaultdict


def download_image(img_url, save_dir):
    try:
        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.basename(urlparse(img_url).path)
        save_path = os.path.join(save_dir, filename)
        resp = requests.get(img_url, timeout=10)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)
        print(f"  → Image saved: {save_path}")
        return filename, None
    except Exception as e:
        print(f"  Failed to download image: {img_url} ({e})")
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Save <section id=main-content> from URLs in sitemap.xml as 1.html, 2.html, ... and download referenced images.")
    parser.add_argument("sitemap_path", help="Path to sitemap.xml file")
    args = parser.parse_args()

    sitemap_path = args.sitemap_path
    base_dir = os.path.dirname(os.path.abspath(sitemap_path))

    # Parse sitemap.xml
    tree = ET.parse(sitemap_path)
    root = tree.getroot()

    # Handle XML namespace
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = [loc.text for loc in root.findall('.//ns:loc', ns)]

    error_counts = defaultdict(int)

    for idx, url in enumerate(urls, 1):
        print(f"{idx}. Downloading HTML: {url} ...")
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            # Explicitly set the encoding to UTF-8
            resp.encoding = 'utf-8' # NOTE(JK): This is important to ensure proper encoding
            # Save the response with proper UTF-8 encoding
            html_path = os.path.join(base_dir, f"{idx}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"  → Saved main content to {html_path}")

            soup = BeautifulSoup(resp.text, "html.parser", from_encoding="utf-8")
            main_section = soup.find("section", id="main-content")
            if not main_section:
                print(f"  No <section id=main-content> found in {url}")
                error_counts['no_main_content'] += 1
                continue
            # Download images referenced in the main section
            img_tags = main_section.find_all("img")
            for img in img_tags:
                img_src = img.get("src")
                if not img_src:
                    continue
                img_url = urljoin(url, img_src)
                img_dir = os.path.join(base_dir, str(idx))
                filename, img_err = download_image(img_url, img_dir)
                if filename:
                    # Update img src to local path
                    img["src"] = os.path.join(str(idx), filename)
                else:
                    error_counts['image_download'] += 1
        except Exception as e:
            print(f"  Failed to process: {url} ({e})")
            error_counts['html_download'] += 1
            continue

    # Print error summary
    print("\nSummary of errors:")
    if not error_counts:
        print("  No errors occurred.")
    else:
        for err_type, count in error_counts.items():
            print(f"  {err_type}: {count}")

if __name__ == "__main__":
    main()