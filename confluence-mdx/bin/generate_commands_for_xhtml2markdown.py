#!/usr/bin/env python3
"""
Generate commands to convert Confluence XHTML to Markdown

This script reads a list of Confluence pages from a file (list.en.txt),
extracts the Page_ID, breadcrumbs, and document titles, and generates
commands to run confluence_xhtml_to_markdown.py for each document.

The commands will convert the XHTML files to Markdown files in the
appropriate directory structure based on the breadcrumbs.
"""

import os
import argparse
import re
from pathlib import Path

def slugify(text):
    """
    Convert text to a URL-friendly slug format.
    Replace spaces with hyphens and remove special characters.
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)
    # Remove special characters
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading and trailing hyphens
    text = text.strip('-')
    return text

def process_breadcrumbs(breadcrumbs):
    """
    Process breadcrumbs to determine the output path.
    
    Args:
        breadcrumbs: A string containing breadcrumbs separated by ' />> '
    
    Returns:
        A tuple containing (directory_path, filename)
    """
    parts = breadcrumbs.split(' />> ')
    
    # Create slugified path components
    path_components = [slugify(part) for part in parts]
    
    # Determine directory path and filename
    if len(path_components) == 1:
        # Root level document
        return '.', f"{path_components[0]}.mdx"
    else:
        # Nested document
        directory = os.path.join(*path_components[:-1])
        filename = f"{path_components[-1]}.mdx"
        return directory, filename

def print_bash_header():
    """
    Print the bash script header.
    """
    print("#!/usr/bin/env bash")
    print("# cd querypie-docs")
    print("# ./confluence-mdx/bin/generate_commands_for_xhtml2markdown.py confluence-mdx/var/list.en.txt")
    print()

def generate_commands(list_file, confluence_dir='confluence-mdx/var/', output_base_dir='src/content/ko/'):
    """
    Generate commands to convert Confluence XHTML to Markdown.
    
    Args:
        list_file: Path to the list.en.txt file
        confluence_dir: Directory containing the Confluence XHTML files (default: confluence-mdx/var/)
        output_base_dir: Base directory for the output Markdown files
    """
    commands = []
    
    with open(list_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Split the line into Page_ID, breadcrumbs, and title
            parts = line.strip().split('\t')
            if len(parts) < 2:
                print(f"Warning: Invalid line format: {line}")
                continue
            
            page_id = parts[0]
            breadcrumbs = parts[1]
            
            # Process breadcrumbs to determine output path
            rel_dir, filename = process_breadcrumbs(breadcrumbs)
            
            # Create full paths
            input_file = os.path.join(confluence_dir, page_id, 'page.xhtml')
            output_dir = os.path.join(output_base_dir, rel_dir)
            output_file = os.path.normpath(os.path.join(output_dir, filename))
            
            # Generate attachment directory based on breadcrumbs
            # Use the same path structure as the output file but for attachments
            attachment_dir = os.path.normpath(os.path.join('/', rel_dir, Path(filename).stem))
            
            # Generate mkdir command
            mkdir_cmd = f"mkdir -p {output_dir}"
            
            # Generate conversion command with new options
            convert_cmd = f"python scripts/confluence_xhtml_to_markdown.py {input_file} {output_file} --public-dir=public --attachment-dir={attachment_dir}"
            
            # Add commands to the list
            commands.append(mkdir_cmd)
            commands.append(convert_cmd)
            
            # Add a message indicating the conversion
            commands.append(f"echo 'Converted {page_id} to {output_file}'")
            commands.append("")  # Empty line for readability
    
    return commands

def main():
    parser = argparse.ArgumentParser(description='Generate commands to convert Confluence XHTML to Markdown')
    parser.add_argument('list_file', help='Path to the list.en.txt file')
    parser.add_argument('--confluence-dir', default='confluence-mdx/var/', 
                        help='Directory containing the Confluence XHTML files (default: confluence-mdx/var/)')
    parser.add_argument('--output-dir', default='src/content/ko/', 
                        help='Base directory for the output Markdown files (default: src/content/ko/)')
    
    args = parser.parse_args()
    
    # Print the bash header
    print_bash_header()
    
    commands = generate_commands(args.list_file, args.confluence_dir, args.output_dir)
    
    # Print all commands
    for cmd in commands:
        print(cmd)

if __name__ == "__main__":
    main()