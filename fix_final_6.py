#!/usr/bin/env python3
"""
Fix final 6 files with pattern-based replacements
"""

import os
import re

files = [
    "src/content/en/user-manual/workflow/requesting-server-access.mdx",
    "src/content/en/user-manual/workflow/requesting-server-privilege.mdx",
    "src/content/en/user-manual/workflow/requesting-sql-export.mdx",
    "src/content/en/user-manual/workflow/requesting-sql.mdx",
    "src/content/en/user-manual/workflow/requesting-sql/using-execution-plan-explain-feature.mdx",
    "src/content/en/user-manual/workflow/requesting-unmasking-mask-removal-request.mdx",
]

for filepath in files:
    if not os.path.exists(filepath):
        print(f"⚠️  Not found: {filepath}")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Pattern 1: "Close the modal by clicking..." -> "Click... to close..."
    content = re.sub(
        r'\* Close the modal by clicking the `Save` button to complete reviewer assignment\.',
        r'* Click the `Save` button to close the modal and complete reviewer assignment.',
        content
    )
    
    # Pattern 2: Add context words
    content = re.sub(
        r'(this feature will not be displayed)\.',
        r'\1 as such.',
        content
    )
    
    # Pattern 3: Ensure double newline at end
    if not content.endswith('\n\n'):
        if content.endswith('\n'):
            content += '\n'
        else:
            content += '\n\n'
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ {os.path.basename(filepath)}")
    else:
        print(f"⏭️  {os.path.basename(filepath)}")

print("\n✨ Done!")
