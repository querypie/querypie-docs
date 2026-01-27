#!/usr/bin/env python3
"""
Auto-update test expectations in test_mdx_to_skeleton.py

This script automatically updates the expected values in test_mdx_to_skeleton.py
to match the actual output from convert_mdx_to_skeleton.

Usage:
    cd confluence-mdx/tests
    python3 update_test_expectations.py
"""

import sys
import os
import re
import tempfile
import shutil
from pathlib import Path

# Add the bin directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from mdx_to_skeleton import convert_mdx_to_skeleton


def extract_test_input(test_code: str) -> str:
    """Extract input text from test code"""
    # Pattern: input_file.write_text("""...""")
    pattern = r'input_file\.write_text\("""(.*?)"""\)'
    match = re.search(pattern, test_code, re.DOTALL)
    if match:
        return match.group(1)

    # Pattern: input_file.write_text("...")
    pattern = r'input_file\.write_text\("(.*?)"\)'
    match = re.search(pattern, test_code, re.DOTALL)
    if match:
        return match.group(1).replace('\\n', '\n')

    return None


def extract_expected_value(test_code: str) -> str:
    """Extract expected value from test code"""
    # Pattern: expected = """..."""
    pattern = r'expected = """(.*?)"""'
    match = re.search(pattern, test_code, re.DOTALL)
    if match:
        return match.group(1)
    return None


def get_actual_output(input_text: str) -> str:
    """Get actual output from convert_mdx_to_skeleton"""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_file = tmp_dir / "test.mdx"
        input_file.write_text(input_text)

        output_path = convert_mdx_to_skeleton(input_file)
        return output_path.read_text()
    finally:
        shutil.rmtree(tmp_dir)


def update_test_expectation(test_code: str, new_expected: str) -> str:
    """Update expected value in test code"""
    # Escape special characters for regex
    # Pattern: expected = """..."""
    pattern = r'(expected = """).*?(""")'

    # Replace with new expected value
    new_code = re.sub(pattern, r'\g<1>' + new_expected + r'\g<2>', test_code, flags=re.DOTALL)

    return new_code


def process_test_file(test_file_path: Path):
    """Process test file and update all expectations"""
    print(f"Processing {test_file_path}")

    # Read test file
    content = test_file_path.read_text()

    # Find all test functions that use convert_mdx_to_skeleton
    # Pattern: def test_xxx(): ... output_path = convert_mdx_to_skeleton(input_file)
    test_pattern = r'(def (test_\w+)\(\):.*?(?=\ndef |$))'
    tests = re.findall(test_pattern, content, re.DOTALL)

    updated_count = 0
    skipped_count = 0

    for full_test, test_name in tests:
        # Skip tests that don't use convert_mdx_to_skeleton
        if 'convert_mdx_to_skeleton' not in full_test:
            continue

        # Skip tests that don't have expected values
        if 'expected = """' not in full_test:
            continue

        print(f"\nProcessing test: {test_name}")

        # Extract input
        input_text = extract_test_input(full_test)
        if not input_text:
            print(f"  ⚠ Could not extract input, skipping")
            skipped_count += 1
            continue

        # Extract current expected
        current_expected = extract_expected_value(full_test)
        if not current_expected:
            print(f"  ⚠ Could not extract expected value, skipping")
            skipped_count += 1
            continue

        # Get actual output
        try:
            actual_output = get_actual_output(input_text)
        except Exception as e:
            print(f"  ⚠ Error getting actual output: {e}, skipping")
            skipped_count += 1
            continue

        # Check if update is needed
        if actual_output == current_expected:
            print(f"  ✓ Already matches, no update needed")
            continue

        # Update test code
        updated_test = update_test_expectation(full_test, actual_output)

        # Replace in content
        content = content.replace(full_test, updated_test)

        print(f"  ✓ Updated")
        print(f"    Old: {repr(current_expected[:50])}...")
        print(f"    New: {repr(actual_output[:50])}...")
        updated_count += 1

    # Write updated content
    if updated_count > 0:
        test_file_path.write_text(content)
        print(f"\n✓ Updated {updated_count} test(s), skipped {skipped_count} test(s)")
        print(f"✓ File written: {test_file_path}")
    else:
        print(f"\n✓ No tests needed updating, skipped {skipped_count} test(s)")


def main():
    """Main function"""
    test_file = Path(__file__).parent / "test_mdx_to_skeleton.py"

    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        return 1

    # Backup original file
    backup_file = test_file.parent / "test_mdx_to_skeleton.py.backup"
    shutil.copy(test_file, backup_file)
    print(f"Backup created: {backup_file}")

    try:
        process_test_file(test_file)
        print("\n✓ All done!")
        print(f"✓ Review changes with: git diff {test_file}")
        print(f"✓ Restore backup if needed: mv {backup_file} {test_file}")
        return 0
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

        # Restore backup on error
        shutil.copy(backup_file, test_file)
        print(f"✓ Backup restored due to error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
