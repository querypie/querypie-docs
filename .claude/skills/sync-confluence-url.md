# sync_confluence_url 사용 가이드

## 개요

`sync_confluence_url.py`는 한국어 MDX 파일의 `confluenceUrl` frontmatter를
영어/일본어 번역 파일에 동기화하는 도구다.
Skeleton 비교 시 frontmatter 구조 불일치(ko에만 `confluenceUrl` 존재)를 해소한다.

**소스 코드**: [confluence-mdx/bin/sync_confluence_url.py](/confluence-mdx/bin/sync_confluence_url.py)

## 사용법

```bash
# en + ja 전체 재귀 (기본)
python3 confluence-mdx/bin/sync_confluence_url.py -r

# 특정 디렉토리만
python3 confluence-mdx/bin/sync_confluence_url.py -r src/content/en/administrator-manual

# 개별 파일
python3 confluence-mdx/bin/sync_confluence_url.py src/content/en/overview.mdx src/content/ja/overview.mdx

# 변경 없이 미리보기
python3 confluence-mdx/bin/sync_confluence_url.py -r --dry-run
```

## CLI 옵션

| 옵션 | 설명 |
|------|------|
| `files` (positional) | en/ja MDX 파일 경로. ko 파일은 자동으로 무시된다. |
| `-r`, `--recursive [DIR ...]` | 디렉토리 재귀 탐색. 인자 없으면 `src/content/en` + `src/content/ja` 전체. |
| `--dry-run` | 파일을 수정하지 않고 변경 예정 목록만 출력. |

## 동작 원리

### 경로 해석

en/ja 파일 경로의 언어 세그먼트를 `ko`로 교체하여 소스 파일을 결정한다:
- `src/content/en/overview.mdx` → `src/content/ko/overview.mdx`
- `src/content/ja/overview.mdx` → `src/content/ko/overview.mdx`

### 동기화 규칙

| ko 상태 | en/ja 상태 | 동작 |
|---------|-----------|------|
| `confluenceUrl` 있음 | 없음 | `title:` 뒤에 삽입 |
| `confluenceUrl` 있음 | 다른 값 | 값 교체 |
| `confluenceUrl` 있음 | 동일 값 | 변경 없음 (idempotent) |
| `confluenceUrl` 없음 | 있음 | en/ja에서 제거 |
| `confluenceUrl` 없음 | 없음 | 변경 없음 |

### 결과 상태

| 상태 | 의미 |
|------|------|
| `updated` | 파일이 수정됨 (또는 dry-run 시 수정 예정) |
| `unchanged` | 이미 동일하여 변경 없음 |
| `skipped_ko` | ko 경로가 입력되어 무시됨 |
| `missing_ko` | 대응하는 ko 소스 파일이 존재하지 않음 |
| `error` | frontmatter가 없는 등 처리 불가 |

## 실전 시나리오

### Confluence 동기화 후 en/ja frontmatter 일괄 업데이트

Confluence에서 MDX를 동기화하면 ko 파일에 `confluenceUrl`이 포함되지만
en/ja에는 반영되지 않는다. 이때 일괄 동기화:

```bash
python3 confluence-mdx/bin/sync_confluence_url.py -r
```

### 변경 전 미리보기

```bash
python3 confluence-mdx/bin/sync_confluence_url.py -r --dry-run
```

출력 예시:
```
[DRY-RUN] updated: src/content/en/overview.mdx
[DRY-RUN] updated: src/content/ja/overview.mdx
...

Done: 578 updated, 4 unchanged, 0 skipped(ko), 0 missing(ko), 0 errors
```

### Idempotency 검증

2회 연속 실행하면 두 번째는 모든 파일이 `unchanged`여야 한다:

```bash
python3 confluence-mdx/bin/sync_confluence_url.py -r
# Done: 578 updated, ...

python3 confluence-mdx/bin/sync_confluence_url.py -r
# Done: 0 updated, 582 unchanged, ...
```

## 관련 Skill

- **mdx-skeleton-comparison.md** — Skeleton 비교를 통한 번역 일관성 검증
- **confluence-mdx.md** — Confluence에서 MDX로의 변환 워크플로우
- **sync-ko-to-en-ja.md** — 한국어 MDX 변경사항을 영어/일본어에 동기화
