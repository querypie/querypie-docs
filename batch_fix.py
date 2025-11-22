#!/usr/bin/env python3
"""
Batch fix remaining English translation files based on common patterns
"""

import os
import re

# 파일 목록
files = [
    "src/content/en/user-manual/workflow/requesting-db-policy-exception.mdx",
    "src/content/en/user-manual/workflow/requesting-ip-registration.mdx",
    "src/content/en/user-manual/workflow/requesting-restricted-data-access.mdx",
    "src/content/en/user-manual/workflow/requesting-server-access.mdx",
    "src/content/en/user-manual/workflow/requesting-server-privilege.mdx",
    "src/content/en/user-manual/workflow/requesting-sql-export.mdx",
    "src/content/en/user-manual/workflow/requesting-sql.mdx",
    "src/content/en/user-manual/workflow/requesting-sql/using-execution-plan-explain-feature.mdx",
    "src/content/en/user-manual/workflow/requesting-unmasking-mask-removal-request.mdx",
]

for filepath in files:
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 공통 패턴 1: "Click the `Save` button to close..." -> "Close the modal by clicking the `Save` button to complete..."
    content = re.sub(
        r'\* Click the `Save` button to close the modal and complete reviewer assignment\.',
        r'* Close the modal by clicking the `Save` button to complete reviewer assignment.',
        content
    )
    
    # 공통 패턴 2: 빈 줄 정규화 (파일 끝에 빈 줄 2개 확인)
    if not content.endswith('\n\n'):
        if content.endswith('\n'):
            content = content + '\n'
        else:
            content = content + '\n\n'
    
    # 변경사항이 있으면 파일 업데이트
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated: {filepath}")
    else:
        print(f"⏭️  No changes needed: {filepath}")

print("\n✨ Batch processing complete!")
