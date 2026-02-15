#!/usr/bin/env python3
"""
Batch converter: pages.yaml 기반으로 모든 Confluence 페이지를 MDX로 변환합니다.

translate_titles.py, generate_commands_for_xhtml2markdown.py, xhtml2markdown.ko.sh를
하나의 명령으로 대체합니다.

Usage:
  bin/convert_all.py                       # 전체 변환
  bin/convert_all.py --verify-translations  # 번역 검증만 수행
  bin/convert_all.py --generate-list        # list.txt / list.en.txt 생성
"""

import argparse
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import yaml

# Resolve project root (confluence-mdx/) from this script's location
_SCRIPT_DIR = Path(__file__).resolve().parent        # confluence-mdx/bin/
_PROJECT_DIR = _SCRIPT_DIR.parent                    # confluence-mdx/

# Ensure bin/ is on sys.path
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def _resolve(rel: str) -> str:
    """Resolve a relative path against _PROJECT_DIR (confluence-mdx/)."""
    p = Path(rel)
    if p.is_absolute():
        return rel
    return str(_PROJECT_DIR / rel)


def load_pages_yaml(pages_yaml_path: str) -> List[Dict]:
    """Load pages.yaml and return list of page entries."""
    with open(pages_yaml_path, 'r', encoding='utf-8') as f:
        pages = yaml.safe_load(f)
    if not isinstance(pages, list):
        raise ValueError(f"pages.yaml should contain a list, got {type(pages)}")
    return pages


def load_translations(translations_file: str) -> Dict[str, str]:
    """Load korean-titles-translations.txt into a dict."""
    translations = {}
    if not os.path.exists(translations_file):
        return translations
    with open(translations_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '|' not in line:
                continue
            parts = line.split('|')
            if len(parts) == 2:
                korean, english = parts[0].strip(), parts[1].strip()
                if korean and english:
                    translations[korean] = english
    return translations


def verify_translations(pages: List[Dict], translations: Dict[str, str]) -> List[Dict]:
    """Check that all Korean titles have translations. Returns list of missing entries."""
    korean_re = re.compile('[가-힣]')
    missing = []
    for page in pages:
        title = page.get('title', '')
        if korean_re.search(title) and title not in translations:
            missing.append(page)
    return missing


def generate_list_files(pages: List[Dict], output_dir: str) -> None:
    """Generate list.txt (Korean) and list.en.txt (English) from pages.yaml."""
    list_txt_lines = []
    list_en_lines = []

    # Skip the root page (first entry, single breadcrumb)
    root_page_id = pages[0]['page_id'] if pages else None

    for page in pages:
        if page['page_id'] == root_page_id:
            continue
        breadcrumbs = page.get('breadcrumbs', [])
        breadcrumbs_en = page.get('breadcrumbs_en', [])
        list_txt_lines.append(f"{page['page_id']}\t{' />> '.join(breadcrumbs)}\n")
        list_en_lines.append(f"{page['page_id']}\t{' />> '.join(breadcrumbs_en)}\n")

    list_txt_path = os.path.join(output_dir, 'list.txt')
    list_en_path = os.path.join(output_dir, 'list.en.txt')

    with open(list_txt_path, 'w', encoding='utf-8') as f:
        f.writelines(list_txt_lines)
    print(f"Generated {list_txt_path} ({len(list_txt_lines)} entries)", file=sys.stderr)

    with open(list_en_path, 'w', encoding='utf-8') as f:
        f.writelines(list_en_lines)
    print(f"Generated {list_en_path} ({len(list_en_lines)} entries)", file=sys.stderr)


def convert_all(pages: List[Dict], var_dir: str, output_base_dir: str, public_dir: str,
                log_level: str) -> int:
    """Run converter/cli.py for each page. Returns number of failures."""
    # Skip the root page
    root_page_id = pages[0]['page_id'] if pages else None
    targets = [p for p in pages if p['page_id'] != root_page_id]

    total = len(targets)
    failures = 0

    for i, page in enumerate(targets, 1):
        page_id = page['page_id']
        path_parts = page.get('path', [])
        if not path_parts:
            print(f"[{i}/{total}] SKIP {page_id} (no path)", file=sys.stderr)
            continue

        # Compute paths (same logic as generate_commands_for_xhtml2markdown.py)
        if len(path_parts) == 1:
            rel_dir = '.'
            filename = f"{path_parts[0]}.mdx"
        else:
            rel_dir = os.path.join(*path_parts[:-1])
            filename = f"{path_parts[-1]}.mdx"

        input_file = os.path.join(var_dir, page_id, 'page.xhtml')
        output_dir = os.path.join(output_base_dir, rel_dir)
        output_file = os.path.normpath(os.path.join(output_dir, filename))
        attachment_dir = os.path.normpath(os.path.join('/', rel_dir, Path(filename).stem))

        if not os.path.exists(input_file):
            print(f"[{i}/{total}] SKIP {page_id} (no page.xhtml)", file=sys.stderr)
            continue

        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            sys.executable, str(_SCRIPT_DIR / 'converter' / 'cli.py'),
            input_file, output_file,
            f'--public-dir={public_dir}',
            f'--attachment-dir={attachment_dir}',
            f'--log-level={log_level}',
        ]

        print(f"[{i}/{total}] {page_id} → {output_file}", file=sys.stderr)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            failures += 1
            print(f"  ERROR: {result.stderr.strip()}", file=sys.stderr)

    return failures


def main():
    parser = argparse.ArgumentParser(
        description='Batch convert all Confluence pages to MDX using pages.yaml'
    )
    parser.add_argument('--pages-yaml', default='var/pages.yaml',
                        help='Path to pages.yaml (default: var/pages.yaml)')
    parser.add_argument('--var-dir', default='var',
                        help='Directory containing page data (default: var)')
    parser.add_argument('--output-dir', default='target/ko',
                        help='Output directory for MDX files (default: target/ko)')
    parser.add_argument('--public-dir', default='target/public',
                        help='Public assets directory (default: target/public)')
    parser.add_argument('--translations', default='etc/korean-titles-translations.txt',
                        help='Path to translations file')
    parser.add_argument('--verify-translations', action='store_true',
                        help='Verify translation coverage and exit')
    parser.add_argument('--generate-list', action='store_true',
                        help='Generate list.txt / list.en.txt for debugging')
    parser.add_argument('--log-level', default='warning',
                        choices=['debug', 'info', 'warning', 'error', 'critical'],
                        help='Log level for converter/cli.py (default: warning)')
    args = parser.parse_args()

    # Resolve relative paths against project root (confluence-mdx/)
    args.pages_yaml = _resolve(args.pages_yaml)
    args.var_dir = _resolve(args.var_dir)
    args.output_dir = _resolve(args.output_dir)
    args.public_dir = _resolve(args.public_dir)
    args.translations = _resolve(args.translations)

    # Load data
    pages = load_pages_yaml(args.pages_yaml)
    translations = load_translations(args.translations)
    print(f"Loaded {len(pages)} pages, {len(translations)} translations", file=sys.stderr)

    # Verify translations (always run before conversion)
    missing = verify_translations(pages, translations)
    if missing:
        print(f"\nERROR: {len(missing)} Korean titles missing translations:", file=sys.stderr)
        for page in missing:
            print(f"  {page['page_id']}\t{page['title']}", file=sys.stderr)
        print(f"\nAdd translations to {args.translations} and retry.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Translation check passed: all Korean titles covered", file=sys.stderr)

    # --verify-translations: exit after check
    if args.verify_translations:
        sys.exit(0)

    # --generate-list: generate list files
    if args.generate_list:
        generate_list_files(pages, args.var_dir)

    # Run conversions
    failures = convert_all(pages, args.var_dir, args.output_dir, args.public_dir, args.log_level)

    if failures:
        print(f"\nCompleted with {failures} failure(s) out of {len(pages)} pages", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\nAll pages converted successfully", file=sys.stderr)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
