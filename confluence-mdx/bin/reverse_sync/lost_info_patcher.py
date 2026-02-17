"""Lost info patcher — emitter 출력에 lost_info를 적용하여 원본에 가까운 XHTML을 생성한다."""
from __future__ import annotations

import emoji as emoji_lib


def apply_lost_info(emitted_xhtml: str, lost_info: dict) -> str:
    """Emitter 출력에 lost_info를 적용한다."""
    if not lost_info:
        return emitted_xhtml

    result = emitted_xhtml

    if 'emoticons' in lost_info:
        result = _patch_emoticons(result, lost_info['emoticons'])

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
