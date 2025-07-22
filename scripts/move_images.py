#!/usr/bin/env python3

import os
import shutil
import re
import sys
from pathlib import Path

def get_mdx_path_from_breadcrumb(breadcrumb_line):
    """Extract the target MDX file path from a breadcrumb line."""
    parts = breadcrumb_line.strip().split('\t')
    if len(parts) < 2:
        return None
    
    # Extract the last URI from the breadcrumb path
    breadcrumb_path = parts[1]
    matches = re.findall(r'\[.*?\]\((.*?)\)', breadcrumb_path)
    if not matches:
        return None
    
    last_uri = matches[-1]
    # Convert /querypie-docs/... to src/content/ko/pam/...
    if last_uri.startswith('/querypie-docs'):
        path_parts = last_uri.split('/')
        # Remove empty first element and 'querypie-docs'
        path_parts = path_parts[2:]
        mdx_path = os.path.join('src', 'content', 'ko', 'pam', *path_parts) + '.mdx'
        return mdx_path
    
    return None

def is_screenshot(image_filename):
    """Determine if an image is a screenshot based on filename patterns."""
    # Common screenshot patterns
    screenshot_patterns = [
        'screenshot', 'screen', 'image-20', 'capture'
    ]
    
    lower_filename = image_filename.lower()
    for pattern in screenshot_patterns:
        if pattern in lower_filename:
            return True
    
    return False

def process_images(line_number, mdx_path):
    """Process images for a specific line number and MDX file."""
    # Check if the MDX file exists
    if not os.path.exists(mdx_path):
        print(f"Warning: MDX file {mdx_path} does not exist. Skipping.")
        return
    
    # Get the prefix from the MDX filename (without extension)
    prefix = os.path.splitext(os.path.basename(mdx_path))[0]
    
    # Source directory for images
    source_dir = os.path.join('docs', '11.0.0-ko', str(line_number))
    
    # Target directory for images (same as MDX file directory)
    target_dir = os.path.dirname(mdx_path)
    
    # Ensure target directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    # Check if source directory exists
    if not os.path.exists(source_dir):
        print(f"Warning: Source directory {source_dir} does not exist. Skipping.")
        return
    
    # Get all image files in the source directory
    image_files = [f for f in os.listdir(source_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]
    
    # Counter for screenshot and image types
    screenshot_count = 1
    image_count = 1
    
    for image_file in image_files:
        source_path = os.path.join(source_dir, image_file)
        
        # Determine if it's a screenshot or regular image
        if is_screenshot(image_file):
            new_filename = f"{prefix}-screenshot-{screenshot_count}{os.path.splitext(image_file)[1]}"
            screenshot_count += 1
        else:
            new_filename = f"{prefix}-image-{image_count}{os.path.splitext(image_file)[1]}"
            image_count += 1
        
        target_path = os.path.join(target_dir, new_filename)
        
        # Copy the file
        shutil.copy2(source_path, target_path)
        print(f"Copied {source_path} to {target_path}")

def main():
    # Path to breadcrumbs.revised.txt
    breadcrumbs_file = os.path.join('docs', '11.0.0-ko', 'breadcrumbs.revised.txt')
    
    if not os.path.exists(breadcrumbs_file):
        print(f"Error: Breadcrumbs file {breadcrumbs_file} not found.")
        return
    
    with open(breadcrumbs_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        mdx_path = get_mdx_path_from_breadcrumb(line)
        if mdx_path:
            print(f"Processing line {i}: {mdx_path}")
            process_images(i, mdx_path)
        else:
            print(f"Warning: Could not determine MDX path for line {i}")

if __name__ == "__main__":
    main()