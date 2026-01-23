#!/usr/bin/env python3
"""
한국어 MDX 변경사항을 영어/일본어에 동기화하는 도구

## 배경

- 한국어 MDX는 Confluence XHTML에서 자동 변환됨
- 영어/일본어 MDX는 한국어를 번역한 것
- 한국어에 기술적 변경(이미지 태그, 테이블 속성 등)이 발생하면 영어/일본어도 동기화 필요

## 목표

한국어 commit의 변경사항을 영어/일본어 문서에 자동으로 동기화

## 워크플로우

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 한국어 commit 분석                                         │
│                                                                 │
│ 입력: commit hash (예: ae93da7e)                                 │
│ 출력: 변경된 파일 목록, 각 파일의 변경된 라인 번호                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 영어/일본어 파일에 한국어 라인 덮어쓰기                          │
│                                                                 │
│ - ko 파일의 변경된 라인을 en/ja 파일의 같은 위치에 복사                   │
│ - working directory에만 적용 (commit하지 않음)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: git diff로 번역 대상 식별                                   │
│                                                                 │
│ - git diff로 변경 전/후 비교                                        │
│ - (-) 라인: 기존 영어/일본어 (번역 참고용)                              │
│ - (+) 라인: 덮어쓴 한국어 (번역 대상)                                  │
│ - 컨텍스트: 주변 라인                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: LLM 번역                                                 │
│                                                                 │
│ - diff를 LLM에게 전달                                              │
│ - (+) 라인의 한국어를 영어/일본어로 번역                                │
│ - 구조(태그, 속성, 경로)는 유지, 텍스트만 번역                           │
│ - translation.md 가이드 적용                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: 번역 결과 적용 및 검증                                       │
│                                                                 │
│ - 번역된 라인으로 파일 업데이트                                        │
│ - mdx_to_skeleton.py로 구조 일치 확인                               │
│ - npm run build로 빌드 확인                                        │
└─────────────────────────────────────────────────────────────────┘
```

## 사용법

```bash
# 기본 사용법
$ python bin/sync_ko_commit.py ae93da7e

# dry-run (미리보기)
$ python bin/sync_ko_commit.py ae93da7e --dry-run

# 특정 언어만
$ python bin/sync_ko_commit.py ae93da7e --lang en

# 검증
$ cd confluence-mdx && bin/mdx_to_skeleton.py --recursive --max-diff=10
```

## 제약사항 및 가정

1. 라인 번호 일치: ko/en/ja 파일의 구조가 동일하다고 가정
2. skeleton 일치: 동기화 전 skeleton이 일치해야 함 (번역 완료 상태)
3. LLM 번역 품질: translation.md 가이드로 품질 보장
"""

import argparse
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


@dataclass
class LineChange:
    """변경된 라인 정보"""
    line_number: int
    old_content: Optional[str]  # 삭제된 라인 (None if added)
    new_content: Optional[str]  # 추가된 라인 (None if deleted)


@dataclass
class FileChange:
    """파일별 변경 정보"""
    ko_path: str
    changes: List[LineChange]


def get_repo_root() -> Path:
    """git 저장소 루트 경로 반환"""
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True, check=True
    )
    return Path(result.stdout.strip())


def get_commit_files(commit_hash: str) -> List[str]:
    """commit에서 변경된 ko 파일 목록 추출"""
    result = subprocess.run(
        ['git', 'show', '--name-only', '--pretty=format:', commit_hash],
        capture_output=True, text=True, check=True
    )
    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    # ko 파일만 필터링
    ko_files = [f for f in files if f.startswith('src/content/ko/') and f.endswith('.mdx')]
    return ko_files


def parse_commit_diff(commit_hash: str, file_path: str) -> List[LineChange]:
    """commit의 특정 파일 diff를 파싱하여 변경된 라인 정보 추출"""
    result = subprocess.run(
        ['git', 'show', '--unified=0', commit_hash, '--', file_path],
        capture_output=True, text=True, check=True
    )

    changes = []
    current_line = 0

    for line in result.stdout.split('\n'):
        # @@ -old_start,old_count +new_start,new_count @@ 형식 파싱
        if line.startswith('@@'):
            # +new_start 추출
            parts = line.split('+')
            if len(parts) >= 2:
                new_part = parts[1].split()[0]
                if ',' in new_part:
                    current_line = int(new_part.split(',')[0])
                else:
                    current_line = int(new_part)
        elif line.startswith('+') and not line.startswith('+++'):
            # 추가된 라인
            changes.append(LineChange(
                line_number=current_line,
                old_content=None,
                new_content=line[1:]  # '+' 제거
            ))
            current_line += 1
        elif line.startswith('-') and not line.startswith('---'):
            # 삭제된 라인은 old_content로 기록 (라인 번호는 new 기준이므로 별도 처리)
            pass

    return changes


def get_target_path(ko_path: str, lang: str) -> str:
    """ko 경로를 en/ja 경로로 변환"""
    return ko_path.replace('/ko/', f'/{lang}/')


def read_file_lines(file_path: Path) -> List[str]:
    """파일을 라인 단위로 읽기"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.readlines()


def write_file_lines(file_path: Path, lines: List[str]):
    """라인 단위로 파일 쓰기"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def overwrite_lines(ko_path: Path, target_path: Path, changes: List[LineChange], dry_run: bool = True) -> List[Tuple[int, str, str]]:
    """
    ko 파일의 변경된 라인을 target 파일에 덮어쓰기

    Returns:
        List of (line_number, old_content, new_content) tuples
    """
    if not target_path.exists():
        print(f"  Warning: Target file does not exist: {target_path}")
        return []

    ko_lines = read_file_lines(ko_path)
    target_lines = read_file_lines(target_path)

    overwrites = []

    for change in changes:
        line_idx = change.line_number - 1  # 0-based index

        if line_idx < 0 or line_idx >= len(ko_lines):
            continue
        if line_idx >= len(target_lines):
            continue

        ko_line = ko_lines[line_idx]
        target_line = target_lines[line_idx]

        if ko_line != target_line:
            overwrites.append((change.line_number, target_line.rstrip('\n'), ko_line.rstrip('\n')))
            if not dry_run:
                target_lines[line_idx] = ko_line

    if not dry_run and overwrites:
        write_file_lines(target_path, target_lines)

    return overwrites


def generate_diff(target_path: Path) -> str:
    """working directory의 변경사항에 대한 diff 생성"""
    result = subprocess.run(
        ['git', 'diff', '--unified=3', '--', str(target_path)],
        capture_output=True, text=True
    )
    return result.stdout


def analyze_commit(commit_hash: str) -> List[FileChange]:
    """commit 분석하여 파일별 변경 정보 추출"""
    ko_files = get_commit_files(commit_hash)

    file_changes = []
    for ko_file in ko_files:
        changes = parse_commit_diff(commit_hash, ko_file)
        if changes:
            file_changes.append(FileChange(ko_path=ko_file, changes=changes))

    return file_changes


def main():
    parser = argparse.ArgumentParser(
        description='한국어 MDX 변경사항을 영어/일본어에 동기화'
    )
    parser.add_argument('commit', help='동기화할 한국어 commit hash')
    parser.add_argument('--lang', choices=['en', 'ja', 'all'], default='all',
                        help='대상 언어 (기본값: all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='실제 변경 없이 미리보기만')
    parser.add_argument('--show-diff', action='store_true',
                        help='덮어쓰기 후 git diff 출력')

    args = parser.parse_args()

    repo_root = get_repo_root()

    # Step 1: commit 분석
    print(f"Analyzing commit {args.commit}...")
    file_changes = analyze_commit(args.commit)

    if not file_changes:
        print("No ko MDX files changed in this commit.")
        return

    print(f"Found {len(file_changes)} changed ko files")

    # 대상 언어 결정
    target_langs = ['en', 'ja'] if args.lang == 'all' else [args.lang]

    # Step 2 & 3: 각 언어별로 덮어쓰기 및 diff 생성
    for lang in target_langs:
        print(f"\n=== Processing {lang} ===")

        all_diffs = []

        for fc in file_changes:
            ko_path = repo_root / fc.ko_path
            target_path = repo_root / get_target_path(fc.ko_path, lang)

            print(f"\n{fc.ko_path} -> {get_target_path(fc.ko_path, lang)}")

            # 덮어쓰기
            overwrites = overwrite_lines(ko_path, target_path, fc.changes, dry_run=args.dry_run)

            if overwrites:
                print(f"  {len(overwrites)} lines to overwrite:")
                for line_num, old, new in overwrites[:5]:  # 처음 5개만 표시
                    print(f"    Line {line_num}:")
                    print(f"      - {old[:60]}{'...' if len(old) > 60 else ''}")
                    print(f"      + {new[:60]}{'...' if len(new) > 60 else ''}")
                if len(overwrites) > 5:
                    print(f"    ... and {len(overwrites) - 5} more")

                # diff 생성
                if args.show_diff and not args.dry_run:
                    diff = generate_diff(target_path)
                    if diff:
                        all_diffs.append((target_path, diff))
            else:
                print("  No changes needed (lines already match or file missing)")

        # diff 출력
        if args.show_diff and all_diffs:
            print(f"\n=== Git diff for {lang} ===")
            for path, diff in all_diffs:
                print(f"\n--- {path} ---")
                print(diff)

    # 안내 메시지
    if args.dry_run:
        print("\n[Dry run] No files were modified.")
        print("Run without --dry-run to apply changes.")
    else:
        print("\n[Done] Files have been modified in working directory.")
        print("Next steps:")
        print("  1. Review changes: git diff src/content/en src/content/ja")
        print("  2. Translate Korean text in changed lines to English/Japanese")
        print("  3. Verify: cd confluence-mdx && bin/mdx_to_skeleton.py --recursive --max-diff=10")
        print("  4. Build: npm run build")
        print("  5. Commit: git add src/content/en src/content/ja && git commit")


if __name__ == '__main__':
    main()
