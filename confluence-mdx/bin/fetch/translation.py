"""Korean to English title translation service."""

import logging
import os
from typing import List, Optional, Protocol

import yaml

from fetch.exceptions import TranslationError
from fetch.models import Page
from text_utils import slugify


class TranslationServiceProtocol(Protocol):
    """Protocol for translation operations"""

    def load_translations(self) -> None:
        ...

    def load_slug_overrides(self) -> None:
        ...

    def translate(self, content: str) -> str:
        ...

    def translate_page(
        self,
        page: 'Page',
        parent_path: Optional[List[str]] = None,
    ) -> None:
        ...


class TranslationService:
    """Handles Korean to English title translations"""

    def __init__(
        self,
        translations_file: str,
        slug_overrides_file: str,
        logger: logging.Logger,
    ):
        self.translations_file = translations_file
        self.slug_overrides_file = slug_overrides_file
        self.logger = logger
        self.translations = {}
        self.slug_overrides = {}

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

    def load_slug_overrides(self) -> None:
        """Load content ID to canonical slug overrides."""
        if not os.path.exists(self.slug_overrides_file):
            self.logger.warning(
                f"Slug overrides file not found: {self.slug_overrides_file}"
            )
            return

        try:
            with open(self.slug_overrides_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data is None:
                return
            if not isinstance(data, dict):
                raise TranslationError(
                    "Slug overrides must be a content ID to slug mapping"
                )

            for content_id_value, slug_value in data.items():
                content_id = str(content_id_value).strip()
                if not content_id or not isinstance(slug_value, str):
                    raise TranslationError(
                        f"Invalid slug override: {content_id_value!r}: {slug_value!r}"
                    )
                slug = slug_value.strip()
                if not slug or slugify(slug) != slug:
                    raise TranslationError(
                        f"Slug override must be a canonical slug: {slug_value!r}"
                    )
                self.slug_overrides[content_id] = slug

            self.logger.info(
                f"Loaded {len(self.slug_overrides)} slug overrides "
                f"from {self.slug_overrides_file}"
            )
        except TranslationError:
            raise
        except Exception as e:
            self.logger.error(
                f"Error loading slug overrides from "
                f"{self.slug_overrides_file}: {str(e)}"
            )
            raise TranslationError(
                f"Failed to load slug overrides: {str(e)}"
            ) from e

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

    def translate_page(
        self,
        page: Page,
        parent_path: Optional[List[str]] = None,
    ) -> None:
        """Update display translations and build the canonical path."""
        # Translate breadcrumbs to English
        page.breadcrumbs_en = []
        for crumb in page.breadcrumbs:
            translated = crumb
            for korean, english in self.translations.items():
                if korean == crumb:
                    translated = english
                    break
            page.breadcrumbs_en.append(translated)

        if parent_path is None:
            page.path = [slugify(crumb) for crumb in page.breadcrumbs_en]
        elif page.breadcrumbs_en:
            page.path = [
                *parent_path,
                slugify(page.breadcrumbs_en[-1]),
            ]
        else:
            page.path = list(parent_path)

        slug_override = self.slug_overrides.get(str(page.page_id))
        if slug_override:
            if not page.path:
                raise TranslationError(
                    f"Cannot apply slug override to content without a path: "
                    f"{page.page_id}"
                )
            page.path[-1] = slug_override
