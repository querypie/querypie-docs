"""MDX Block Parser — MDX 파일을 블록 시퀀스로 파싱한다."""
from dataclasses import dataclass
from typing import List


@dataclass
class MdxBlock:
    type: str           # frontmatter | import_statement | heading | paragraph |
                        # code_block | list | html_block | empty
    content: str        # 원본 텍스트 (줄바꿈 포함)
    line_start: int     # 1-indexed
    line_end: int       # 1-indexed, inclusive


def parse_mdx_blocks(text: str) -> List[MdxBlock]:
    """MDX 텍스트를 블록 시퀀스로 파싱한다."""
    lines = text.split('\n')
    # 텍스트가 \n으로 끝나면 split 결과 마지막이 빈 문자열 — 제거하여 처리
    if lines and lines[-1] == '':
        lines = lines[:-1]

    blocks: List[MdxBlock] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Frontmatter
        if line == '---' and i == 0:
            start = i
            i += 1
            while i < n and lines[i] != '---':
                i += 1
            i += 1  # closing ---
            content = '\n'.join(lines[start:i]) + '\n'
            blocks.append(MdxBlock('frontmatter', content, start + 1, i))
            continue

        # Empty line
        if line == '':
            blocks.append(MdxBlock('empty', '\n', i + 1, i + 1))
            i += 1
            continue

        # Code block
        if line.startswith('```'):
            start = i
            i += 1
            while i < n and not lines[i].startswith('```'):
                i += 1
            i += 1  # closing ```
            content = '\n'.join(lines[start:i]) + '\n'
            blocks.append(MdxBlock('code_block', content, start + 1, i))
            continue

        # Heading
        if line.startswith('#'):
            blocks.append(MdxBlock('heading', line + '\n', i + 1, i + 1))
            i += 1
            continue

        # Import statement
        if line.startswith('import '):
            blocks.append(MdxBlock('import_statement', line + '\n', i + 1, i + 1))
            i += 1
            continue

        # HTML block
        if line.startswith('<') and not line.startswith('<Badge') and not line.startswith('<Callout'):
            start = i
            i += 1
            while i < n and lines[i] != '':
                i += 1
            content = '\n'.join(lines[start:i]) + '\n'
            blocks.append(MdxBlock('html_block', content, start + 1, i))
            continue

        # List
        if _is_list_line(line):
            start = i
            i += 1
            while i < n and (lines[i] == '' or _is_list_continuation(lines[i])):
                # 빈 줄 다음에 리스트가 아니면 종료
                if lines[i] == '':
                    if i + 1 < n and _is_list_continuation(lines[i + 1]):
                        i += 1
                        continue
                    else:
                        break
                i += 1
            content = '\n'.join(lines[start:i]) + '\n'
            blocks.append(MdxBlock('list', content, start + 1, i))
            continue

        # Paragraph (fallback)
        start = i
        i += 1
        while i < n and lines[i] != '' and not lines[i].startswith('#') \
                and not lines[i].startswith('```') and not lines[i].startswith('<') \
                and not _is_list_line(lines[i]) and not lines[i].startswith('import '):
            i += 1
        content = '\n'.join(lines[start:i]) + '\n'
        blocks.append(MdxBlock('paragraph', content, start + 1, i))
        continue

    return blocks


def _is_list_line(line: str) -> bool:
    """줄이 리스트 항목으로 시작하는지 확인."""
    stripped = line.lstrip()
    if stripped.startswith('* ') or stripped.startswith('- '):
        return True
    # 번호 리스트: "1. ", "2. ", etc.
    parts = stripped.split('. ', 1)
    if len(parts) == 2 and parts[0].isdigit():
        return True
    return False


def _is_list_continuation(line: str) -> bool:
    """줄이 리스트의 연속(들여쓰기 또는 새 리스트 항목)인지 확인."""
    if _is_list_line(line):
        return True
    # 들여쓰기된 줄 (2칸 이상)
    if line.startswith('  ') or line.startswith('\t'):
        return True
    return False
