#!/usr/bin/env python3

import os
import re
import glob
from pathlib import Path

def is_screenshot(image_filename):
    """Determine if an image is a screenshot based on filename patterns."""
    screenshot_patterns = [
        'screenshot', 'screen', 'image-20', 'capture'
    ]
    
    lower_filename = image_filename.lower()
    for pattern in screenshot_patterns:
        if pattern in lower_filename:
            return True
    
    return False

def update_image_references(mdx_file_path):
    """Update image references in an MDX file to point to the new image locations."""
    # Get the directory and filename (without extension)
    mdx_dir = os.path.dirname(mdx_file_path)
    mdx_filename = os.path.splitext(os.path.basename(mdx_file_path))[0]
    
    # Read the content of the MDX file
    with open(mdx_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all image references in the content
    # This pattern matches markdown image syntax: ![alt text](image_path)
    image_pattern = r'!\[(.*?)\]\((.*?)\)'
    
    # Keep track of screenshot and image counts
    screenshot_count = 1
    image_count = 1
    
    # Dictionary to store original paths and their replacements
    replacements = {}
    
    # Find all image references
    for match in re.finditer(image_pattern, content):
        alt_text = match.group(1)
        image_path = match.group(2)
        
        # Skip if the image path doesn't contain __attachments or __theme
        if not ('__attachments' in image_path or '__theme' in image_path):
            continue
        
        # Extract the image filename from the path
        image_filename = os.path.basename(image_path.split('?')[0])
        
        # Determine if it's a screenshot or regular image
        if is_screenshot(image_filename):
            new_filename = f"{mdx_filename}-screenshot-{screenshot_count}{os.path.splitext(image_filename)[1]}"
            screenshot_count += 1
        else:
            new_filename = f"{mdx_filename}-image-{image_count}{os.path.splitext(image_filename)[1]}"
            image_count += 1
        
        # Create the new relative path (in the same directory as the MDX file)
        new_path = new_filename
        
        # Add to replacements dictionary
        replacements[image_path] = new_path
    
    # Replace all image paths in the content
    for old_path, new_path in replacements.items():
        content = content.replace(old_path, new_path)
    
    # Write the updated content back to the file
    with open(mdx_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return len(replacements)

def main():
    # Find all MDX files in the src/content/ko/pam directory and its subdirectories
    mdx_files = glob.glob('src/content/ko/pam/**/*.mdx', recursive=True)
    
    total_files = len(mdx_files)
    total_replacements = 0
    
    print(f"Found {total_files} MDX files to process.")
    
    for i, mdx_file in enumerate(mdx_files, 1):
        replacements = update_image_references(mdx_file)
        total_replacements += replacements
        print(f"[{i}/{total_files}] Processed {mdx_file}: {replacements} image references updated.")
    
    print(f"Completed! Updated {total_replacements} image references across {total_files} files.")

if __name__ == "__main__":
    main()