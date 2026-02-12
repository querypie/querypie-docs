#!/usr/bin/env python3
"""
Confluence XHTML beautify-diff 도구.

두 XHTML 파일(또는 fragment)을 BeautifulSoup으로 노드 단위 줄바꿈한 뒤
unified diff를 출력한다. XML serializer 부산물(속성 순서, self-closing 태그,
entity 인코딩)은 양쪽 모두 동일하게 정규화되어 소거되고, 실제 구조/텍스트
변경만 diff에 남는다.

Usage:
    bin/xhtml_beautify_diff.py <file_a> <file_b>

Exit codes:
    0 — 차이 없음
    1 — 차이 있음
    2 — 오류 (파일 없음 등)
"""

import argparse
import difflib
import sys
from pathlib import Path

from bs4 import BeautifulSoup


def beautify_xhtml(html: str) -> str:
    """XHTML(fragment)을 노드 단위 줄바꿈으로 정규화한다.

    html.parser + prettify(formatter='minimal') 조합:
    - 노드별 줄바꿈 (prettify)
    - 속성 순서 보존 (html.parser는 삽입순서 유지)
    - self-closing 통일 (<p /> → <p></p>)
    - &amp; / &lt; / &gt; 보존, 나머지 entity는 유니코드로 디코딩
    """
    soup = BeautifulSoup(html, "html.parser")
    return soup.prettify(formatter="minimal")


def xhtml_diff(text_a: str, text_b: str,
               label_a: str = "a", label_b: str = "b") -> list[str]:
    """두 XHTML 문자열을 beautify 후 unified diff 라인 리스트를 반환한다.

    차이가 없으면 빈 리스트를 반환한다.
    """
    lines_a = beautify_xhtml(text_a).splitlines()
    lines_b = beautify_xhtml(text_b).splitlines()
    return list(difflib.unified_diff(
        lines_a, lines_b,
        fromfile=label_a, tofile=label_b,
        lineterm="",
    ))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Confluence XHTML beautify-diff: 두 XHTML 파일의 의미적 차이를 비교",
    )
    parser.add_argument("file_a", help="비교 대상 XHTML 파일 A")
    parser.add_argument("file_b", help="비교 대상 XHTML 파일 B")
    args = parser.parse_args()

    path_a = Path(args.file_a)
    path_b = Path(args.file_b)

    for p in (path_a, path_b):
        if not p.is_file():
            print(f"Error: {p} not found", file=sys.stderr)
            sys.exit(2)

    text_a = path_a.read_text(encoding="utf-8")
    text_b = path_b.read_text(encoding="utf-8")

    diff_lines = xhtml_diff(text_a, text_b,
                            label_a=str(path_a), label_b=str(path_b))

    if diff_lines:
        print("\n".join(diff_lines))
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
