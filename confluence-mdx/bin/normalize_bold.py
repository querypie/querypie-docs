#!/usr/bin/env python3
"""
MDX 파일의 bold 서식을 정규화합니다.

## 처리 패턴

1. split bold 병합     : **word** **word**  → **word word**
2. stray bold 제거     : **:**               → :
3. bold 뒤 콜론 공백   : **label** :         → **label**:
4. 콜론을 bold 밖으로  : **label:**           → **label**:
5. 이중 공백/trailing  : 불필요한 공백 제거

## 사용법

    # dry-run (변경 사항만 출력)
    bin/normalize_bold.py src/content/ko/administrator-manual/kubernetes/

    # 실제 적용
    bin/normalize_bold.py --apply src/content/ko/administrator-manual/kubernetes/

    # 특정 파일만
    bin/normalize_bold.py --apply src/content/ko/some-file.mdx

    # 코드 블록 내부 패턴도 포함 (기본: 제외)
    bin/normalize_bold.py --include-code src/content/ko/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# 코드 블록 (fenced) — 내부는 건드리지 않기 위해 분리
_FENCED_CODE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)

# 인라인 코드 — 내부 보호
_INLINE_CODE = re.compile(r"`[^`]+`")

# 1) split bold 병합: **word** **word** → **word word**
#    연속으로 반복 가능 (**a** **b** **c** → **a b c**)
_SPLIT_BOLD = re.compile(r"\*\*([^*]+)\*\*(\s+\*\*[^*]+\*\*)+")

# 2) stray bold: 콜론·쉼표·마침표 등 단일 구두점만 감싼 bold
_STRAY_BOLD = re.compile(r"\*\*([:\.\,;])\*\*")

# 3) bold 뒤 콜론 공백: **label** : → **label**:
_BOLD_COLON_SPACE = re.compile(r"\*\*\s+:")

# 4) 콜론을 bold 밖으로: **label:** → **label**:
#    spec:allow, spec:deny 등 기술 용어는 제외 (콜론 뒤에 알파벳이 이어지는 경우)
_COLON_INSIDE_BOLD = re.compile(r"\*\*([^*]+?):\*\*(?![^\s])")

# 5a) 이중 공백 (줄 앞 인덴트 제외, 코드 블록 외부)
_DOUBLE_SPACE = re.compile(r"(?<=\S)  +(?=\S)")

# 5b) trailing whitespace
_TRAILING_WS = re.compile(r"[ \t]+$", re.MULTILINE)


def _merge_split_bold(m: re.Match) -> str:
    """**a** **b** **c** → **a b c**"""
    full = m.group(0)
    parts = re.findall(r"\*\*([^*]+)\*\*", full)
    return f"**{' '.join(parts)}**"


def _colon_outside_bold(m: re.Match) -> str:
    """**label:** → **label**: (단, 콜론 뒤에 알파벳이면 기술 용어로 보존)"""
    label = m.group(1).rstrip()
    return f"**{label}**:"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _protect_and_transform(
    text: str, include_code: bool = False
) -> str:
    """코드 영역을 보호하면서 bold 패턴을 정규화합니다."""

    if include_code:
        return _apply_rules(text)

    # fenced code block을 placeholder로 치환
    fenced_blocks: list[str] = []

    def _save_fenced(m: re.Match) -> str:
        fenced_blocks.append(m.group(0))
        return f"\x00FENCED{len(fenced_blocks) - 1}\x00"

    text = _FENCED_CODE.sub(_save_fenced, text)

    # inline code를 placeholder로 치환
    inline_codes: list[str] = []

    def _save_inline(m: re.Match) -> str:
        inline_codes.append(m.group(0))
        return f"\x00INLINE{len(inline_codes) - 1}\x00"

    text = _INLINE_CODE.sub(_save_inline, text)

    # 규칙 적용
    text = _apply_rules(text)

    # placeholder 복원 (역순)
    for i, code in enumerate(inline_codes):
        text = text.replace(f"\x00INLINE{i}\x00", code)
    for i, block in enumerate(fenced_blocks):
        text = text.replace(f"\x00FENCED{i}\x00", block)

    return text


def _apply_rules(text: str) -> str:
    """5가지 정규화 규칙을 순서대로 적용합니다."""
    # 규칙 1~4는 전체 텍스트에 적용
    text = _SPLIT_BOLD.sub(_merge_split_bold, text)
    text = _STRAY_BOLD.sub(r"\1", text)
    text = _BOLD_COLON_SPACE.sub("**:", text)
    text = _COLON_INSIDE_BOLD.sub(_colon_outside_bold, text)

    # 5a) 이중 공백 — 테이블 행(|로 시작) 제외 (가로 정렬 공백 보존 정책)
    lines = text.splitlines(keepends=True)
    result = []
    for line in lines:
        if not line.lstrip().startswith("|"):
            line = _DOUBLE_SPACE.sub(" ", line)
        result.append(line)
    text = "".join(result)

    # 5b) trailing whitespace
    text = _TRAILING_WS.sub("", text)
    return text


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------

def normalize_file(
    path: Path, *, apply: bool = False, include_code: bool = False
) -> list[tuple[int, str, str]]:
    """파일 하나를 정규화하고 변경된 줄 목록을 반환합니다.

    Returns:
        [(line_no, old_line, new_line), ...]
    """
    original = path.read_text(encoding="utf-8")
    normalized = _protect_and_transform(original, include_code=include_code)

    if original == normalized:
        return []

    changes: list[tuple[int, str, str]] = []
    old_lines = original.splitlines(keepends=True)
    new_lines = normalized.splitlines(keepends=True)

    for i, (old, new) in enumerate(zip(old_lines, new_lines)):
        if old != new:
            changes.append((i + 1, old.rstrip("\n"), new.rstrip("\n")))

    if apply:
        path.write_text(normalized, encoding="utf-8")

    return changes


def collect_mdx_files(target: Path) -> list[Path]:
    """대상 경로에서 MDX 파일 목록을 수집합니다."""
    if target.is_file():
        return [target] if target.suffix == ".mdx" else []
    return sorted(target.rglob("*.mdx"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MDX bold 서식 정규화",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "target",
        type=Path,
        help="MDX 파일 또는 디렉토리 경로",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제로 파일을 수정합니다 (기본: dry-run)",
    )
    parser.add_argument(
        "--include-code",
        action="store_true",
        help="코드 블록 내부도 처리합니다",
    )
    args = parser.parse_args()

    files = collect_mdx_files(args.target)
    if not files:
        print(f"MDX 파일을 찾을 수 없습니다: {args.target}", file=sys.stderr)
        return 1

    total_changes = 0
    changed_files = 0

    for path in files:
        changes = normalize_file(
            path, apply=args.apply, include_code=args.include_code
        )
        if not changes:
            continue
        changed_files += 1
        total_changes += len(changes)
        rel = path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path
        print(f"\n{'APPLY' if args.apply else 'DIFF'} {rel} ({len(changes)} lines)")
        for lineno, old, new in changes:
            print(f"  L{lineno}:")
            print(f"    - {old}")
            print(f"    + {new}")

    mode = "applied" if args.apply else "found (dry-run)"
    print(f"\n{changed_files} files, {total_changes} changes {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
