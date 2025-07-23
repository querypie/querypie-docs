#!/bin/bash

# ============================================================================
# XHTML to Markdown Converter for Confluence Pages
# ============================================================================
#
# This script reads a list.txt file containing page_ids and converts any
# page.xhtml files found in directories named after those page_ids to page.md
# using the confluence_xhtml_to_markdown.py script.
#
# The list.txt file should have the following format:
#   <page_id>\t<navigation_path>\t<document_title>
# Where:
#   - page_id: A numeric identifier for the page
#   - navigation_path: The path to the page in the navigation hierarchy
#   - document_title: The title of the document
#
# The script will:
#   1. Read each line from the list.txt file
#   2. Extract the page_id from the first column
#   3. Check if a directory with that page_id exists and contains a page.xhtml file
#   4. If it does, convert the page.xhtml to page.md using confluence_xhtml_to_markdown.py
#
# Requirements:
#   - Python 3
#   - BeautifulSoup4 Python package (pip install beautifulsoup4)
#
# Usage: ./convert_xhtml_to_md.sh <list_file_path>

# Function to check if a Python package is installed
check_python_package() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

# Check for required Python packages
if ! check_python_package bs4; then
    echo "Error: BeautifulSoup4 package is not installed."
    echo "Please install it using: pip install beautifulsoup4"
    exit 1
fi

# Check if the list file path is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <list_file_path>"
    echo "Example: $0 docs/latest-ko-confluence/list.txt"
    exit 1
fi

LIST_FILE="$1"

# Check if the list file exists
if [[ ! -f "$LIST_FILE" ]]; then
    echo "Error: List file '$LIST_FILE' not found."
    exit 1
fi

# Get the directory of the list file to use as base directory for page_id directories
BASE_DIR=$(dirname "$LIST_FILE")

# Check if confluence_xhtml_to_markdown.py exists and is executable
CONVERTER_SCRIPT="$(dirname "$0")/confluence_xhtml_to_markdown.py"
if [[ ! -f "$CONVERTER_SCRIPT" ]]; then
    echo "Error: Converter script '$CONVERTER_SCRIPT' not found."
    exit 1
fi

if [[ ! -x "$CONVERTER_SCRIPT" ]]; then
    echo "Making converter script executable..."
    chmod +x "$CONVERTER_SCRIPT"
fi

# Counter for statistics
TOTAL_LINES=0
CONVERTED_COUNT=0
SKIPPED_COUNT=0

# Process each line in the list file
while IFS=$'\t' read -r page_id rest; do
    TOTAL_LINES=$((TOTAL_LINES + 1))
    
    # Skip empty lines
    if [[ -z "$page_id" ]]; then
        continue
    fi
    
    # Check if the directory with page_id exists
    PAGE_DIR="$BASE_DIR/$page_id"
    if [[ ! -d "$PAGE_DIR" ]]; then
        echo "Directory for page_id $page_id not found, skipping."
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi
    
    # Check if page.xhtml exists in the directory
    XHTML_FILE="$PAGE_DIR/page.xhtml"
    if [[ ! -f "$XHTML_FILE" ]]; then
        echo "page.xhtml not found in directory for page_id $page_id, skipping."
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi
    
    # Define the output markdown file
    MD_FILE="$PAGE_DIR/page.md"
    
    # Convert the file
    echo "Converting $XHTML_FILE to $MD_FILE..."
    python3 "$CONVERTER_SCRIPT" "$XHTML_FILE" "$MD_FILE"
    
    # Check if conversion was successful
    if [ $? -eq 0 ]; then
        echo "Successfully converted page_id $page_id"
        CONVERTED_COUNT=$((CONVERTED_COUNT + 1))
    else
        echo "Error converting page_id $page_id"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    fi
    
done < "$LIST_FILE"

# Print statistics
echo "Conversion completed."
echo "Total lines processed: $TOTAL_LINES"
echo "Files successfully converted: $CONVERTED_COUNT"
echo "Files skipped or failed: $SKIPPED_COUNT"