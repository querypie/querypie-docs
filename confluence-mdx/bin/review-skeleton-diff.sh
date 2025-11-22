#!/bin/bash
# Review skeleton diff for files listed in todo file

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <todo-file>"
    exit 1
fi

TODO_FILE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFLUENCE_MDX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$CONFLUENCE_MDX_DIR"

# Process each file
while IFS= read -r file || [ -n "$file" ]; do
    echo "=========================================="
    echo "Processing: $file"
    echo "=========================================="
    echo ""
    
    # Step 1: Run without --use-ignore
    echo "--- Step 1: mdx_to_skeleton.py (without --use-ignore) ---"
    bin/mdx_to_skeleton.py "$file" 2>&1
    echo ""
    
    # Step 2: Run with --use-ignore
    echo "--- Step 2: mdx_to_skeleton.py (with --use-ignore) ---"
    bin/mdx_to_skeleton.py --use-ignore "$file" 2>&1
    echo ""
    
    # Ask for user confirmation
    read -p "Continue to next file? (yes/no/quit): " answer < /dev/tty
    case "$answer" in
        [Yy]es|[Yy])
            echo ""
            ;;
        *)
            exit 0
            ;;
    esac
    
done < "$TODO_FILE"

echo "Review completed for all files!"
