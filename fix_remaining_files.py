#!/usr/bin/env python3
"""
영어 번역 파일의 줄바꿈 및 문장 구조 수정 스크립트
"""

import re

# 공통 수정 패턴 정의
fixes = [
    # 패턴 1: "Click the `Save` button to..." -> "Close the modal by clicking the `Save` button to..."
    (r'\* Click the `Save` button to close the modal and complete reviewer assignment\.',
     r'* Close the modal by clicking the `Save` button to complete reviewer assignment.'),
    
    # 패턴 2: 문장 끝에 추가 단어 필요한 경우
    (r'(this feature will not be displayed)\.',
     r'\1 as such.'),
]

# 파일별 특정 수정사항 (필요한 경우)
file_specific_fixes = {
    'src/content/en/user-manual/workflow/requesting-db-policy-exception.mdx': [
        # 특정 수정이 필요한 경우 여기에 추가
    ],
}

print("Script prepared for manual review")
print("Due to the complexity of changes, each file should be reviewed individually")
