#!/usr/bin/env python3
"""
Script to translate Korean titles in list.txt to English
using the translations from korean-titles-translations.txt

Structure of list.txt in Korean
- <page_id> \t <first-breadcrumb> ' />> ' <second-breadcrumb> ' />> ' ...
"""

import argparse
import sys


def load_translations(translations_file: str) -> dict:
    """Load translations from the translations file"""
    translations = {}
    with open(translations_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '|' not in line:
                continue

            parts = line.split('|')
            if len(parts) == 2:
                korean = parts[0].strip()
                english = parts[1].strip()
                if korean and english:
                    translations[korean] = english

    return translations


def translate_file(translations: dict, input_file: str, output_file: str) -> None:
    """Translate Korean titles in input file to English and write to output file"""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Sort translations by length (longest first) to avoid partial matches
    sorted_translations = sorted(translations.items(), key=lambda x: len(x[0]), reverse=True)

    # Replace Korean titles with English translations
    for korean, english in sorted_translations:
        # Replace in both the navigation path and the document title
        content = content.replace(f" />> {korean}", f" />> {english}")
        content = content.replace(f"\t{korean}", f"\t{english}")

    # Write the translated content to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Translate Korean titles in list.txt to English')
    parser.add_argument('--translations', default='etc/korean-titles-translations.txt',
                        help='Path to translations file (default: etc/korean-titles-translations.txt)')
    parser.add_argument('--input', default='var/list.txt',
                        help='Path to input file (default: var/list.txt)')
    parser.add_argument('--output', default='var/list.en.txt',
                        help='Path to output file (default: var/list.en.txt)')
    args = parser.parse_args()

    translations = load_translations(args.translations)
    print(f"Loaded {len(translations)} translations")

    translate_file(translations, args.input, args.output)
    print(f"Translated file saved to {args.output}")


if __name__ == "__main__":
    sys.exit(main())
