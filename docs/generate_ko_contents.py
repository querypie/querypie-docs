#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

# Helper to parse breadcrumbs line
BREADCRUMB_RE = re.compile(r"\[([^\]]+)\]\(([^\)]+)\)")

def parse_breadcrumbs(breadcrumbs_str):
    """Parse breadcrumbs string into list of (title, uri) tuples."""
    return BREADCRUMB_RE.findall(breadcrumbs_str)

def breadcrumbs_to_path(breadcrumbs):
    """
    Convert breadcrumbs to output path (directory, filename).
    '[QueryPie Docs](/querypie-docs)' → Maps to 'pam' directory.
    The last part of the last URI becomes the filename.
    """
    # breadcrumbs: list of (title, uri)
    # uri: /querypie-docs/admin-manual/databases/connection-management/db-connections
    # → src/content/ko/pam/admin-manual/databases/connection-management/db-connections.mdx
    uri = breadcrumbs[-1][1]
    parts = uri.strip('/').split('/')
    if parts and parts[0] == 'querypie-docs':
        parts[0] = 'pam'
    # The last part is the filename
    filename = parts[-1] + '.mdx'
    dirpath = os.path.join(*parts[:-1]) if len(parts) > 1 else ''
    return dirpath, filename

def find_images_in_html(html_path):
    """Return list of (src, type) for images in html (type: screenshot/image/other)."""
    imgs = []
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    for m in re.finditer(r'<img [^>]*src=["\']([^"\']+)["\'][^>]*>', html):
        src = m.group(1)
        # Heuristic: screenshot/image/other
        if 'screenshot' in src.lower():
            typ = 'screenshot'
        elif 'diagram' in src.lower() or 'illustration' in src.lower() or 'image' in src.lower():
            typ = 'image'
        else:
            typ = 'image'
        imgs.append((src, typ))
    return imgs

def copy_and_rename_images(imgs, html_dir, out_dir, prefix):
    """Copy images to out_dir with new names, return mapping old->new."""
    mapping = {}
    count = {'screenshot': 1, 'image': 1}
    for src, typ in imgs:
        ext = os.path.splitext(src)[1]
        if typ == 'screenshot':
            newname = f"{prefix}-screenshot-{count['screenshot']}{ext}"
            count['screenshot'] += 1
        else:
            newname = f"{prefix}-image-{count['image']}{ext}"
            count['image'] += 1
        src_path = os.path.join(html_dir, src)
        dst_path = os.path.join(out_dir, newname)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            mapping[src] = newname
    return mapping

def replace_img_srcs(md_path, mapping):
    """Replace image srcs in mdx file according to mapping."""
    with open(md_path, encoding='utf-8') as f:
        content = f.read()
    for old, new in mapping.items():
        content = content.replace(f']({old})', f']({new})')
        content = content.replace(f'src=\"{old}\"', f'src=\"{new}\"')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    parser = argparse.ArgumentParser(description='Generate .mdx files from breadcrumbs and html.')
    parser.add_argument('--breadcrumbs', required=True, help='Path to breadcrumbs.revised.txt')
    parser.add_argument('--html_dir', required=True, help='Directory containing <no>.html files and images')
    parser.add_argument('--output_dir', required=True, help='Output root directory (src/content/ko)')
    args = parser.parse_args()

    breadcrumbs_path = args.breadcrumbs
    html_dir = args.html_dir
    output_dir = args.output_dir

    with open(breadcrumbs_path, encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f if line.strip()]

    for idx, line in enumerate(lines):
        try:
            url, breadcrumbs_str = line.split('\t', 1)
        except ValueError:
            print(f"[SKIP] Malformed line: {line}")
            continue
        breadcrumbs = parse_breadcrumbs(breadcrumbs_str)
        dirpath, filename = breadcrumbs_to_path(breadcrumbs)
        out_dir = os.path.join(output_dir, dirpath)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, filename)
        html_path = os.path.join(html_dir, f"{idx+1}.html")
        # Convert HTML to MDX
        if not os.path.exists(html_path):
            print(f"[SKIP] HTML not found: {html_path}")
            continue
        subprocess.run([
            'pandoc', '-f', 'html', '-t', 'markdown', '-o', out_path, html_path
        ], check=True)
        # Handle images
        imgs = find_images_in_html(html_path)
        prefix = os.path.splitext(filename)[0]
        mapping = copy_and_rename_images(imgs, html_dir, out_dir, prefix)
        if mapping:
            replace_img_srcs(out_path, mapping)
        print(f"[Done] {html_path} → {out_path}")

if __name__ == '__main__':
    main() 