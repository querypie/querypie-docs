"""Korean to English title translation service."""

import logging
import os
from typing import Protocol

from fetch.exceptions import TranslationError
from fetch.models import Page
from text_utils import slugify


class TranslationServiceProtocol(Protocol):
    """Protocol for translation operations"""

    def load_translations(self) -> None:
        ...

    def translate(self, content: str) -> str:
        ...

    def translate_page(self, page: 'Page') -> None:
        ...


class TranslationService:
    """Handles Korean to English title translations"""

    def __init__(self, translations_file: str, logger: logging.Logger):
        self.translations_file = translations_file
        self.logger = logger
        self.translations = {}

    def load_translations(self) -> None:
        """Load translations from the translations file"""
        if not os.path.exists(self.translations_file):
            self.logger.warning(f"Translations file not found: {self.translations_file}")
            return

        try:
            with open(self.translations_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '|' not in line:
                        continue

                    parts = line.split('|')
                    if len(parts) == 2:
                        korean = parts[0].strip()
                        english = parts[1].strip()
                        if korean and english:
                            self.translations[korean] = english

            self.logger.info(f"Loaded {len(self.translations)} translations from {self.translations_file}")
        except Exception as e:
            self.logger.error(f"Error loading translations from {self.translations_file}: {str(e)}")
            raise TranslationError(f"Failed to load translations: {str(e)}")

    def translate(self, content: str) -> str:
        """Translate Korean titles in content to English"""
        if not self.translations:
            return content

        # Sort translations by length (longest first) to avoid partial matches
        sorted_translations = sorted(self.translations.items(), key=lambda x: len(x[0]), reverse=True)

        # Replace Korean titles with English translations
        translated_content = content
        for korean, english in sorted_translations:
            # Replace in both the navigation path and the document title
            translated_content = translated_content.replace(f" />> {korean}", f" />> {english}")
            translated_content = translated_content.replace(f"\t{korean}", f"\t{english}")

        return translated_content

    def translate_page(self, page: Page) -> None:
        """Update English translations and path using the translator"""
        # Translate breadcrumbs to English
        page.breadcrumbs_en = []
        for crumb in page.breadcrumbs:
            translated = crumb
            for korean, english in self.translations.items():
                if korean == crumb:
                    translated = english
                    break
            page.breadcrumbs_en.append(translated)

        # Create path by slugifying English breadcrumbs
        page.path = [slugify(crumb) for crumb in page.breadcrumbs_en]
