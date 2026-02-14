# Reverse Sync 사용 가이드

## 개요

`reverse-sync`는 MDX 변경사항을 Confluence XHTML에 역반영하는 파이프라인이다.
교정/교열한 한국어 MDX 파일의 텍스트 변경을 Confluence 원본 XHTML에 패치하고,
round-trip 검증(MDX → XHTML 패치 → MDX 재변환 → 비교)을 통해 패치 정확성을 보장한다.

**소스 코드**: [confluence-mdx/bin/reverse_sync_cli.py](/confluence-mdx/bin/reverse_sync_cli.py)

## 파이프라인 단계

1. original / improved MDX를 블록 단위로 파싱
2. 블록 diff 추출
3. 원본 XHTML 블록 매핑 생성
4. XHTML 패치 적용
5. 패치된 XHTML을 다시 MDX로 forward 변환 (round-trip)
6. improved MDX와 비교하여 pass/fail 판정
7. pass인 경우 Confluence API로 업데이트 (`push` 시)

## 커맨드

| 커맨드 | 설명 |
|--------|------|
| `verify` | round-trip 검증만 수행 (`push --dry-run`의 alias) |
| `debug` | verify + MDX diff, XHTML diff, Verify diff 상세 출력 |
| `push` | verify 수행 후 Confluence에 반영 (`--dry-run`으로 검증만 가능) |

## 사용법

```bash
cd confluence-mdx

# 단일 파일 검증
python3 bin/reverse_sync_cli.py verify \
  "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

# 브랜치 전체 배치 검증
python3 bin/reverse_sync_cli.py verify --branch proofread/fix-typo

# 상세 디버그 출력
python3 bin/reverse_sync_cli.py debug \
  "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

# 검증 + Confluence 반영
python3 bin/reverse_sync_cli.py push \
  "proofread/fix-typo:src/content/ko/user-manual/user-agent.mdx"

# 브랜치 전체 배치 push
python3 bin/reverse_sync_cli.py push --branch proofread/fix-typo
```

## MDX 소스 지정

두 가지 형식을 사용할 수 있다:

| 형식 | 설명 | 예시 |
|------|------|------|
| `ref:path` | git ref와 파일 경로를 콜론으로 구분 | `proofread/fix-typo:src/content/ko/overview.mdx` |
| `path` | 로컬 파일 시스템 경로 | `src/content/ko/overview.mdx` |

`page-id`는 경로의 `src/content/ko/` 부분에서 `var/pages.yaml`을 통해 자동 유도된다.

## 옵션

### 공통 옵션

| 옵션 | 설명 |
|------|------|
| `--branch <branch>` | 브랜치의 모든 변경 ko MDX 파일을 자동 발견하여 배치 처리. `<mdx>`와 동시에 사용할 수 없다. |
| `--original-mdx <mdx>` | 원본 MDX 소스 (기본: `main:<improved 경로>`) |
| `--xhtml <path>` | 원본 XHTML 경로 (기본: `var/<page-id>/page.xhtml`) |
| `--limit N` | 배치 모드에서 최대 처리 파일 수 (기본: 0=전체) |
| `--failures-only` | 실패(fail/error) 결과만 출력. `--limit`과 함께 사용 시 실패 건수 기준으로 제한. |
| `--json` | 결과를 JSON 형식으로 출력 |

### push 전용 옵션

| 옵션 | 설명 |
|------|------|
| `--dry-run` | 검증만 수행, Confluence 반영 안 함 (= `verify`) |

## 배치 모드 옵션 조합

`--branch` 사용 시 `--limit`과 `--failures-only`의 동작:

| 조합 | 처리 범위 | 출력 범위 |
|------|-----------|-----------|
| (기본) | 전체 파일 | 전체 결과 |
| `--failures-only` | 전체 파일 | 실패 결과만 |
| `--limit N` | 처음 N개 파일 | 전체 결과 |
| `--failures-only --limit N` | 실패 N건 수집될 때까지 | 실패 결과만 (최대 N건) |

`--failures-only` 사용 시에도 Summary는 실제 처리한 전체 건수 기준으로 출력된다.

## 검증 결과 상태

| 상태 | 의미 |
|------|------|
| `pass` | round-trip 검증 통과 — improved MDX와 verify MDX가 일치 |
| `fail` | round-trip 검증 실패 — 패치 후 재변환 결과가 다름 |
| `no_changes` | MDX에 변경사항 없음 |
| `error` | 처리 중 오류 발생 |

## 중간 산출물

`verify`/`debug`/`push` 실행 시 `var/<page_id>/`에 중간 파일이 생성된다:

```
var/<page_id>/
├── page.xhtml                          # Confluence 원본 XHTML
├── reverse-sync.diff.yaml             # MDX 블록 변경 목록
├── reverse-sync.mapping.original.yaml # 원본 XHTML 블록 매핑
├── reverse-sync.patched.xhtml         # 패치된 XHTML
├── reverse-sync.mapping.patched.yaml  # 패치 후 매핑
├── reverse-sync.result.yaml           # 검증 결과
└── verify.mdx                         # 패치된 XHTML → MDX 재변환 결과
```

## 실전 시나리오

### 교정 브랜치의 전체 파일 검증

```bash
python3 bin/reverse_sync_cli.py verify --branch proofread/fix-typo
```

모든 변경 파일의 PASS/FAIL 상태와 Summary가 출력된다.

### 실패 건만 빠르게 확인

```bash
python3 bin/reverse_sync_cli.py verify --branch proofread/fix-typo --failures-only
```

pass/no_changes 결과를 생략하고 fail/error만 출력한다.

### 실패 3건만 수집 후 중단

```bash
python3 bin/reverse_sync_cli.py verify --branch proofread/fix-typo --failures-only --limit 3
```

실패가 3건 수집되면 나머지 파일 처리를 건너뛴다.

### FAIL 원인 분석 (debug 모드)

```bash
python3 bin/reverse_sync_cli.py debug \
  "proofread/fix-typo:src/content/ko/administrator-manual.mdx"
```

세 가지 diff가 출력된다:
1. **MDX diff** (original → improved): 입력 변경 내용
2. **XHTML diff** (page.xhtml → patched.xhtml): XHTML에 적용된 패치
3. **Verify diff** (improved.mdx → verify.mdx): round-trip 불일치 부분

### XHTML 패치 상세 비교

`xhtml_beautify_diff.py`와 함께 사용하여 XHTML 레벨의 변경을 정밀 분석:

```bash
python3 bin/xhtml_beautify_diff.py \
  var/<page_id>/page.xhtml \
  var/<page_id>/reverse-sync.patched.xhtml
```

### JSON 출력으로 후처리

```bash
# 전체 결과를 JSON으로
python3 bin/reverse_sync_cli.py verify --branch proofread/fix-typo --json

# 실패 건만 JSON으로
python3 bin/reverse_sync_cli.py verify --branch proofread/fix-typo --failures-only --json
```

### 검증 후 Confluence 반영

```bash
# 전체 PASS 시에만 push 실행 (일부라도 FAIL이면 중단)
python3 bin/reverse_sync_cli.py push --branch proofread/fix-typo
```

## Confluence 인증 설정

`push` 커맨드 사용 시 `~/.config/atlassian/confluence.conf` 파일이 필요하다:

```
email:api_token
```

## 관련 Skill

- [xhtml-beautify-diff.md](xhtml-beautify-diff.md) — XHTML 패치 결과의 의미적 diff 분석
- [confluence-mdx.md](confluence-mdx.md) — Confluence에서 MDX로의 forward 변환 워크플로우
