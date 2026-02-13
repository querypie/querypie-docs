#!/usr/bin/env python3
"""
git diff에서 기존 alt 텍스트를 추출하여 덮어쓴 파일에 복원

사용법:
  bin/restore_alt_from_diff.py --dry-run
  bin/restore_alt_from_diff.py --apply
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Resolve repo root from this script's location
# Script is at confluence-mdx/bin/restore_alt_from_diff.py
_SCRIPT_DIR = Path(__file__).resolve().parent        # confluence-mdx/bin/
_PROJECT_DIR = _SCRIPT_DIR.parent                    # confluence-mdx/
_REPO_ROOT = _PROJECT_DIR.parent                     # repo root


def get_diff_for_lang(lang: str) -> str:
    """특정 언어의 git diff 가져오기"""
    result = subprocess.run(
        ['git', 'diff', f'src/content/{lang}/'],
        capture_output=True, text=True,
        cwd=str(_REPO_ROOT),
    )
    return result.stdout


def parse_diff_for_alt_mapping(diff_content: str) -> Dict[str, Dict[str, str]]:
    """
    diff에서 파일별 이미지 경로 → 기존 alt 텍스트 매핑 추출

    Returns:
        {file_path: {image_path: original_alt_text}}
    """
    file_mappings = {}
    current_file = None

    lines = diff_content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # 파일 경로 추출
        if line.startswith('--- a/'):
            current_file = line[6:]
            if current_file not in file_mappings:
                file_mappings[current_file] = {}

        # 삭제된 라인 (기존 Markdown 이미지)
        elif line.startswith('-') and not line.startswith('---'):
            # ![alt](path) 패턴 찾기
            match = re.search(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if match and current_file:
                alt_text = match.group(1)
                img_path = match.group(2)
                file_mappings[current_file][img_path] = alt_text

        i += 1

    return file_mappings


def restore_alt_in_file(file_path: Path, alt_mapping: Dict[str, str], dry_run: bool = True) -> List[Tuple[int, str, str]]:
    """
    파일에서 한국어 alt를 기존 번역으로 복원

    Returns:
        List of (line_number, before, after) tuples
    """
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    changes = []

    for i, line in enumerate(lines):
        # <img src="path" alt="..." .../> 패턴 찾기
        match = re.search(r'<img\s+src="([^"]+)"\s+alt="([^"]+)"', line)
        if match:
            img_path = match.group(1)
            current_alt = match.group(2)

            if img_path in alt_mapping:
                original_alt = alt_mapping[img_path]
                if current_alt != original_alt:
                    new_line = line.replace(f'alt="{current_alt}"', f'alt="{original_alt}"')
                    changes.append((i + 1, line, new_line))
                    if not dry_run:
                        lines[i] = new_line

    if not dry_run and changes:
        file_path.write_text('\n'.join(lines), encoding='utf-8')

    return changes


def main():
    import argparse

    parser = argparse.ArgumentParser(description='git diff에서 기존 alt 텍스트 복원')
    parser.add_argument('--dry-run', action='store_true', help='실제 변경 없이 미리보기')
    parser.add_argument('--apply', action='store_true', help='실제 변경 적용')
    parser.add_argument('--lang', choices=['en', 'ja', 'all'], default='all', help='대상 언어')

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("--dry-run 또는 --apply 옵션을 지정하세요.")
        sys.exit(1)

    dry_run = args.dry_run
    target_langs = ['en', 'ja'] if args.lang == 'all' else [args.lang]

    for lang in target_langs:
        print(f"\n=== Processing {lang} ===")

        # diff에서 매핑 추출
        diff_content = get_diff_for_lang(lang)
        file_mappings = parse_diff_for_alt_mapping(diff_content)

        print(f"Found {len(file_mappings)} files with alt text to restore")

        total_changes = 0

        for file_path_str, alt_mapping in file_mappings.items():
            file_path = _REPO_ROOT / file_path_str

            if not file_path.exists():
                continue

            changes = restore_alt_in_file(file_path, alt_mapping, dry_run=dry_run)

            if changes:
                total_changes += len(changes)
                print(f"\n{file_path}: {len(changes)} changes")
                for line_num, before, after in changes[:3]:
                    # alt 부분만 추출해서 표시
                    before_alt = re.search(r'alt="([^"]*)"', before)
                    after_alt = re.search(r'alt="([^"]*)"', after)
                    if before_alt and after_alt:
                        print(f"  Line {line_num}:")
                        print(f"    - alt=\"{before_alt.group(1)[:50]}{'...' if len(before_alt.group(1)) > 50 else ''}\"")
                        print(f"    + alt=\"{after_alt.group(1)[:50]}{'...' if len(after_alt.group(1)) > 50 else ''}\"")
                if len(changes) > 3:
                    print(f"  ... and {len(changes) - 3} more")

        print(f"\nTotal: {total_changes} alt texts {'would be' if dry_run else ''} restored for {lang}")

    if dry_run:
        print("\n[Dry run] No files were modified.")
        print("Run with --apply to apply changes.")


if __name__ == '__main__':
    main()
