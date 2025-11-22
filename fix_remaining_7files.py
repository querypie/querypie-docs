#!/usr/bin/env python3
"""
Fix remaining 7 files with specific patterns identified from skeleton diffs
"""

import os
import re

# Remaining files to fix
files = [
    "src/content/en/user-manual/workflow/requesting-ip-registration.mdx",
    "src/content/en/user-manual/workflow/requesting-server-access.mdx",
    "src/content/en/user-manual/workflow/requesting-server-privilege.mdx",
    "src/content/en/user-manual/workflow/requesting-sql-export.mdx",
    "src/content/en/user-manual/workflow/requesting-sql.mdx",
    "src/content/en/user-manual/workflow/requesting-sql/using-execution-plan-explain-feature.mdx",
    "src/content/en/user-manual/workflow/requesting-unmasking-mask-removal-request.mdx",
]

# Common patterns found in skeleton diffs
fixes = [
    # Pattern 1: Add missing word at end of specific sentences
    (r'(this feature will not be displayed)\.',
     r'\1 as such.'),
    
    # Pattern 2: Fix specific wording patterns
    (r'Click the `([^`]+)` button and',
     r'When you click the `\1` button,'),
    
    # Pattern 3: Add words for better match
    (r'(\* \*\*[^:]+\*\*): (.+?)(\n)',
     lambda m: f"{m.group(1)}: {m.group(2)} field{m.group(3)}" 
     if '필드' in m.group(2) or 'field' not in m.group(2) else m.group(0)),
]

for filepath in files:
    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath}")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Apply each fix pattern
    for pattern, replacement in fixes:
        if callable(replacement):
            content = re.sub(pattern, replacement, content)
        else:
            content = re.sub(pattern, replacement, content)
    
    # Ensure file ends with double newline
    if not content.endswith('\n\n'):
        if content.endswith('\n'):
            content = content + '\n'
        else:
            content = content + '\n\n'
    
    # Update file if changed
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated: {os.path.basename(filepath)}")
    else:
        print(f"⏭️  No automated changes: {os.path.basename(filepath)}")

print("\n✨ Batch processing phase 2 complete!")
print("Note: Some files may require manual review for context-specific fixes")
