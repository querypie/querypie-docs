#!/usr/bin/env python3
"""
Regenerate all original.mdx files for test cases in tests/reverse-sync/.

Usage (from confluence-mdx/ directory):
    python3 tests/reverse-sync/regen-original.py
"""
import subprocess
import yaml
import os
import sys

# Determine paths relative to this script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
confluence_mdx_dir = os.path.dirname(os.path.dirname(script_dir))

# Accept confluence-mdx/ as cwd or derive it from script location
cwd = os.getcwd()
if os.path.basename(cwd) == 'confluence-mdx':
    confluence_mdx_dir = cwd
    tests_dir = os.path.join(cwd, 'tests', 'reverse-sync')
else:
    # Fallback: run from anywhere, use script-relative paths
    confluence_mdx_dir = os.path.dirname(os.path.dirname(script_dir))
    tests_dir = script_dir

pages_yaml_path = os.path.join(tests_dir, 'pages.yaml')

with open(pages_yaml_path) as f:
    pages = yaml.safe_load(f)

skipped = 0
converted = 0
errors = 0

for page in pages:
    if 'failure_type' not in page:
        continue  # 테스트케이스 아닌 항목 건너뜀

    pid = page['page_id']
    mdx_path = page.get('mdx_path')
    if not mdx_path:
        print(f"[SKIP] {pid}: mdx_path 없음")
        skipped += 1
        continue

    xhtml_path = os.path.join(tests_dir, str(pid), 'page.xhtml')
    if not os.path.exists(xhtml_path):
        print(f"[SKIP] {pid}: page.xhtml 없음")
        skipped += 1
        continue

    attachment_dir = '/' + mdx_path.removesuffix('.mdx')
    output_path = os.path.join(tests_dir, str(pid), 'original.mdx')

    # Use paths relative to confluence_mdx_dir for the subprocess
    rel_xhtml = os.path.relpath(xhtml_path, confluence_mdx_dir)
    rel_output = os.path.relpath(output_path, confluence_mdx_dir)

    print(f"[CONV] {pid}: {mdx_path}")
    result = subprocess.run(
        [
            sys.executable, 'bin/converter/cli.py',
            '--skip-image-copy', '--language', 'ko',
            '--attachment-dir', attachment_dir,
            '--log-level', 'warning',
            rel_xhtml, rel_output,
        ],
        cwd=confluence_mdx_dir,
    )
    if result.returncode != 0:
        print(f"[ERROR] {pid}: 변환 실패 (returncode={result.returncode})")
        errors += 1
    else:
        converted += 1

print(f"\n완료: {converted}건 변환, {skipped}건 건너뜀, {errors}건 실패")
