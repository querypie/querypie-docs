"""Lost info patcher — emitter 출력에 lost_info를 적용하여 원본에 가까운 XHTML을 생성한다."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import emoji as emoji_lib

if TYPE_CHECKING:
    from reverse_sync.mapping_recorder import BlockMapping
    from reverse_sync.sidecar import SidecarBlock

_LINK_ERROR_RE = re.compile(r'<a\s+href="#link-error"[^>]*>.*?</a>', re.DOTALL)

# emitter의 Callout type → macro name 매핑의 역방향
_MACRO_NAME_TO_PANEL_TYPE = {
    'tip': 'default',
    'info': 'info',
    'note': 'note',
    'warning': 'warning',
}

_STRUCTURED_MACRO_RE = re.compile(
    r'<ac:structured-macro\s+ac:name="(tip|info|note|warning)">'
    r'.*?</ac:structured-macro>',
    re.DOTALL,
)


def apply_lost_info(emitted_xhtml: str, lost_info: dict) -> str:
    """Emitter 출력에 lost_info를 적용한다."""
    if not lost_info:
        return emitted_xhtml

    result = emitted_xhtml

    if 'emoticons' in lost_info:
        result = _patch_emoticons(result, lost_info['emoticons'])

    if 'links' in lost_info:
        result = _patch_links(result, lost_info['links'])

    if 'filenames' in lost_info:
        result = _patch_filenames(result, lost_info['filenames'])

    if 'adf_extensions' in lost_info:
        result = _patch_adf_extensions(result, lost_info['adf_extensions'])

    if 'images' in lost_info:
        result = _patch_images(result, lost_info['images'])

    return result


def _resolve_emoticon_char(entry: dict) -> str | None:
    """lost_info emoticon 엔트리에서 MDX에 들어간 유니코드 문자를 역산한다."""
    fallback = entry.get('fallback', '')
    shortname = entry.get('shortname', '')

    # Case 1: fallback이 이미 유니코드 문자 (: 으로 시작하지 않음)
    if fallback and not fallback.startswith(':'):
        return fallback

    # Case 2: shortname → emoji 변환
    if shortname:
        char = emoji_lib.emojize(shortname, language='alias')
        if char != shortname:
            return char

    # Case 3: fallback이 shortname 형식
    if fallback:
        char = emoji_lib.emojize(fallback, language='alias')
        if char != fallback:
            return char

    return None


def _patch_emoticons(xhtml: str, emoticons: list[dict]) -> str:
    """유니코드 이모지를 원본 <ac:emoticon> 태그로 복원한다."""
    result = xhtml
    for entry in emoticons:
        char = _resolve_emoticon_char(entry)
        if char is None:
            continue
        raw = entry.get('raw', '')
        if not raw:
            continue
        # 첫 번째 매칭만 치환 (순차 소비)
        if char in result:
            result = result.replace(char, raw, 1)
    return result


def _patch_links(xhtml: str, links: list[dict]) -> str:
    """#link-error 앵커를 원본 <ac:link> 태그로 복원한다."""
    result = xhtml
    for entry in links:
        raw = entry.get('raw', '')
        if not raw:
            continue
        match = _LINK_ERROR_RE.search(result)
        if match:
            result = result[:match.start()] + raw + result[match.end():]
    return result


def _patch_filenames(xhtml: str, filenames: list[dict]) -> str:
    """정규화된 파일명을 원본 파일명으로 복원한다."""
    result = xhtml
    for entry in filenames:
        original = entry.get('original', '')
        normalized = entry.get('normalized', '')
        if not original or not normalized:
            continue
        old = f'ri:filename="{normalized}"'
        new = f'ri:filename="{original}"'
        result = result.replace(old, new)
    return result


def _patch_adf_extensions(xhtml: str, adf_extensions: list[dict]) -> str:
    """<ac:structured-macro>를 원본 <ac:adf-extension>으로 복원한다."""
    result = xhtml
    for entry in adf_extensions:
        panel_type = entry.get('panel_type', '')
        raw = entry.get('raw', '')
        if not raw or not panel_type:
            continue

        match = _STRUCTURED_MACRO_RE.search(result)
        if not match:
            continue

        macro_name = match.group(1)
        expected_panel_type = _MACRO_NAME_TO_PANEL_TYPE.get(macro_name, '')
        if expected_panel_type != panel_type:
            continue

        result = result[:match.start()] + raw + result[match.end():]

    return result


def _patch_images(xhtml: str, images: list[dict]) -> str:
    """<img> 태그를 원본 <ac:image> 태그로 복원한다.

    lost_info의 src 필드로 <img> 태그를 찾아 원본 <ac:image> raw로 교체한다.
    """
    result = xhtml
    for entry in images:
        src = entry.get('src', '')
        raw = entry.get('raw', '')
        if not src or not raw:
            continue
        # src 속성이 일치하는 <img> 태그를 찾아 교체
        pattern = re.compile(
            r'<img\s[^>]*src="' + re.escape(src) + r'"[^>]*/?>',
        )
        match = pattern.search(result)
        if match:
            result = result[:match.start()] + raw + result[match.end():]
    return result


def distribute_lost_info(blocks: list[SidecarBlock], page_lost_info: dict) -> None:
    """페이지 레벨 lost_info를 각 블록에 분배한다.

    각 항목의 raw 필드가 블록의 xhtml_fragment에 포함되는지로 판별한다.
    블록의 lost_info dict를 in-place로 갱신한다.
    """
    if not page_lost_info:
        return

    for category in ('emoticons', 'links', 'images', 'adf_extensions'):
        entries = page_lost_info.get(category, [])
        for entry in entries:
            raw = entry.get('raw', '')
            if not raw:
                continue
            for block in blocks:
                if raw in block.xhtml_fragment:
                    block.lost_info.setdefault(category, []).append(entry)
                    break

    # filenames: raw가 없으므로 original filename으로 매칭
    for entry in page_lost_info.get('filenames', []):
        original = entry.get('original', '')
        if not original:
            continue
        for block in blocks:
            if original in block.xhtml_fragment:
                block.lost_info.setdefault('filenames', []).append(entry)
                break


def distribute_lost_info_to_mappings(
    mappings: list[BlockMapping],
    page_lost_info: dict,
) -> dict[str, dict]:
    """페이지 레벨 lost_info를 BlockMapping별로 분배한다.

    각 항목의 raw 필드가 매핑의 xhtml_text에 포함되는지로 판별한다.

    Returns:
        block_id → block-level lost_info dict
    """
    if not page_lost_info:
        return {}

    result: dict[str, dict] = {}

    for category in ('emoticons', 'links', 'images', 'adf_extensions'):
        for entry in page_lost_info.get(category, []):
            raw = entry.get('raw', '')
            if not raw:
                continue
            for m in mappings:
                if raw in m.xhtml_text:
                    result.setdefault(m.block_id, {}).setdefault(
                        category, []).append(entry)
                    break

    # filenames: raw가 없으므로 original filename으로 매칭
    for entry in page_lost_info.get('filenames', []):
        original = entry.get('original', '')
        if not original:
            continue
        for m in mappings:
            if original in m.xhtml_text:
                result.setdefault(m.block_id, {}).setdefault(
                    'filenames', []).append(entry)
                break

    return result
