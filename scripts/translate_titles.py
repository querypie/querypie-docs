#!/usr/bin/env python3
"""
Script to translate Korean titles in list.txt to English
using the translations from korean-titles-translations.txt

Structure of list.txt in Korean
- <page_id> \t <first-breadcrumb> ' />> ' <second-breadcrumb> ' />> ' ...
"""

# Paths
TRANSLATIONS_FILE = "docs/korean-titles-translations.txt"
INPUT_FILE = "docs/latest-ko-confluence/list.txt"
OUTPUT_FILE = "docs/latest-ko-confluence/list.en.txt"


def load_translations():
    """Load translations from the translations file"""
    translations = {}
    with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
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


def translate_file(translations):
    """Translate Korean titles in list.en.txt to English"""
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Sort translations by length (longest first) to avoid partial matches
    sorted_translations = sorted(translations.items(), key=lambda x: len(x[0]), reverse=True)

    # Replace Korean titles with English translations
    for korean, english in sorted_translations:
        # Replace in both the navigation path and the document title
        content = content.replace(f" />> {korean}", f" />> {english}")
        content = content.replace(f"\t{korean}", f"\t{english}")

    # Write the translated content to the output file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    """Main function"""
    translations = load_translations()
    print(f"Loaded {len(translations)} translations")

    translate_file(translations)
    print(f"Translated file saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
