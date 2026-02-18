"""텍스트 전이 — MDX 블록 간의 텍스트 변경을 XHTML plain text에 전이."""
import difflib


def align_chars(source: str, target: str) -> dict:
    """source와 target의 문자를 정렬하여 source index → target index 맵을 반환한다.

    1단계: 비공백 문자를 SequenceMatcher로 전역 정렬 (이모지 drift 방지)
    2단계: 인접 비공백 앵커 사이의 공백을 위치순으로 매핑
    """
    src_nonspace = [(i, c) for i, c in enumerate(source) if not c.isspace()]
    tgt_nonspace = [(i, c) for i, c in enumerate(target) if not c.isspace()]

    src_chars = ''.join(c for _, c in src_nonspace)
    tgt_chars = ''.join(c for _, c in tgt_nonspace)

    matcher = difflib.SequenceMatcher(None, src_chars, tgt_chars, autojunk=False)
    mapping = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                mapping[src_nonspace[i1 + k][0]] = tgt_nonspace[j1 + k][0]

    # 2단계: 인접 앵커 사이의 공백을 위치순으로 매핑
    anchors = sorted(mapping.items())
    boundaries = [(-1, -1)] + anchors + [(len(source), len(target))]
    for idx in range(len(boundaries) - 1):
        s_lo, t_lo = boundaries[idx]
        s_hi, t_hi = boundaries[idx + 1]
        s_spaces = [j for j in range(s_lo + 1, s_hi) if source[j].isspace()]
        t_spaces = [j for j in range(t_lo + 1, t_hi) if target[j].isspace()]
        for s, t in zip(s_spaces, t_spaces):
            mapping[s] = t

    return mapping


def find_insert_pos(char_map: dict, mdx_pos: int) -> int:
    """MDX 삽입 위치에 대응하는 XHTML 위치를 찾는다."""
    for k in range(mdx_pos - 1, -1, -1):
        if k in char_map:
            return char_map[k] + 1
    return 0


def transfer_text_changes(mdx_old: str, mdx_new: str, xhtml_text: str) -> str:
    """MDX 블록 간의 텍스트 변경을 XHTML plain text에 전이한다.

    MDX old와 XHTML text의 문자 정렬(alignment)을 구축하고,
    MDX old→new 변경의 위치를 XHTML 상의 위치로 매핑하여 적용한다.
    이를 통해 XHTML의 공백 구조를 보존하면서 콘텐츠만 업데이트한다.
    """
    # 1. MDX old ↔ XHTML text 문자 정렬
    char_map = align_chars(mdx_old, xhtml_text)

    # 2. MDX old → new 변경 추출
    # autojunk=False: 한국어 등 반복 문자가 많은 텍스트에서
    # autojunk이 로컬 매칭을 건너뛰어 대규모 insert/delete를 생성하는 것을 방지
    matcher = difflib.SequenceMatcher(None, mdx_old, mdx_new, autojunk=False)

    # 3. 변경을 XHTML 위치로 매핑
    edits = []  # (xhtml_start, xhtml_end, replacement)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        replacement = mdx_new[j1:j2] if tag != 'delete' else ''
        if tag in ('replace', 'delete'):
            mapped = sorted(char_map[k] for k in range(i1, i2) if k in char_map)
            if not mapped:
                continue  # MDX 전용 공백 — XHTML에 대응 없음
            edits.append((mapped[0], mapped[-1] + 1, replacement))
        elif tag == 'insert':
            xpos = find_insert_pos(char_map, i1)
            edits.append((xpos, xpos, replacement))

    # 4. 역순 적용 (위치 보존)
    chars = list(xhtml_text)
    for xstart, xend, repl in reversed(edits):
        chars[xstart:xend] = list(repl)
    return ''.join(chars)
