"""Forward conversion 시 손실되는 정보를 블록 단위로 수집한다."""
from __future__ import annotations

from bs4 import Tag


class LostInfoCollector:
    """현재 블록 변환 중 손실되는 정보를 수집한다."""

    def __init__(self) -> None:
        self._emoticons: list[dict] = []
        self._links: list[dict] = []
        self._filenames: list[dict] = []
        self._adf_extensions: list[dict] = []

    def add_emoticon(self, node: Tag) -> None:
        self._emoticons.append({
            'name': node.get('ac:name', ''),
            'shortname': node.get('ac:emoji-shortname', ''),
            'emoji_id': node.get('ac:emoji-id', ''),
            'fallback': node.get('ac:emoji-fallback', ''),
            'raw': str(node),
        })

    def add_link(self, node: Tag) -> None:
        ri_page = node.find('ri:page')
        self._links.append({
            'content_title': ri_page.get('ri:content-title', '') if ri_page else '',
            'space_key': ri_page.get('ri:space-key', '') if ri_page else '',
            'raw': str(node),
        })

    def add_filename(self, original: str, normalized: str) -> None:
        if original != normalized:
            self._filenames.append({
                'original': original,
                'normalized': normalized,
            })

    def add_adf_extension(self, node: Tag, panel_type: str) -> None:
        self._adf_extensions.append({
            'panel_type': panel_type,
            'raw': str(node),
        })

    def to_dict(self) -> dict:
        """빈 카테고리를 제외하고 반환한다."""
        result: dict = {}
        if self._emoticons:
            result['emoticons'] = self._emoticons
        if self._links:
            result['links'] = self._links
        if self._filenames:
            result['filenames'] = self._filenames
        if self._adf_extensions:
            result['adf_extensions'] = self._adf_extensions
        return result
