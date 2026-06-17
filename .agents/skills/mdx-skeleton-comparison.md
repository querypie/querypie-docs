# MDX 스켈레톤 비교 가이드라인

## 개요

이 skill은 `skeleton/cli.py` 도구를 사용하여 한국어 원본 MDX 파일과 번역본(영어/일본어) 간의 **구조적 불일치**를 감지하기 위한 가이드라인을 제공합니다.

MDX 파일에서 텍스트를 `_TEXT_` 플레이스홀더로 치환한 "스켈레톤"을 생성하고, 한국어(ko) 스켈레톤과 번역본(en/ja) 스켈레톤을 비교하여 문서 구조가 동일한지 검증합니다.

**Skeleton MDX 개념**: [docs/translation.md](/docs/translation.md)의 "Skeleton MDX 를 비교하기" 섹션을 참조하세요.

## 도구 위치

- **CLI 스크립트**: `confluence-mdx/bin/skeleton/cli.py`
- **지원 모듈**:
  - `confluence-mdx/bin/skeleton/diff.py` — 재귀 처리 및 diff 비교
  - `confluence-mdx/bin/skeleton/compare.py` — 파일 존재 여부 비교 (`--compare`)
  - `confluence-mdx/bin/skeleton/common.py` — 경로/언어코드 유틸리티
  - `confluence-mdx/bin/skeleton/ignore_rules.yaml` — diff 제외 규칙
- **리뷰 스크립트**: `confluence-mdx/bin/review-skeleton-diff.sh`
- **테스트**: `confluence-mdx/tests/test_mdx_to_skeleton.py`

## 빠른 시작

```bash
cd confluence-mdx/
source venv/bin/activate

# 전체 비교 실행 (기본: target/ko, target/ja, target/en)
bin/skeleton/cli.py -r

# 최대 20개 차이까지 출력
bin/skeleton/cli.py -r --max-diff=20

# 특정 파일 변환 + 한국어 스켈레톤과 비교
bin/skeleton/cli.py target/en/path/to/file.mdx

# ignore 규칙을 적용하여 비교
bin/skeleton/cli.py --use-ignore target/ja/path/to/file.mdx
```

## CLI 옵션 레퍼런스

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `input_path` | MDX 파일 경로 (단일 파일 모드) | — |
| `-r`, `--recursive [DIR...]` | 디렉토리 재귀 처리. 미지정 시 target/ko, target/ja, target/en | — |
| `--compare` | ko/en/ja 디렉토리 간 MDX 파일 존재 여부 비교 | — |
| `--verbose` | `--compare` 사용 시 모든 파일 출력 (3개 언어 모두 존재하는 파일 포함) | — |
| `--max-diff N` | 최대 diff 출력 수 (재귀 모드 전용) | 5 |
| `--exclude PATH` | diff 비교에서 제외할 경로 (복수 지정 가능) | `/index.skel.mdx` |
| `--output FILE` | unmatched 파일 목록 저장 경로 (재귀 모드 전용) | — |
| `--use-ignore` | `ignore_rules.yaml` 패턴 적용 (단일 파일 모드) | — |
| `--ignore-file FILE` | `ignore_rules.yaml` 경로 지정 | 스크립트 디렉토리 |
| `--reset [DIR...]` | `.skel.mdx` 파일 일괄 삭제. 미지정 시 target/ko, target/ja, target/en | — |

## 작동 방식

### 스켈레톤 변환 규칙

**보존되는 요소**:
- YAML frontmatter 구조 (텍스트 값은 `_TEXT_`로 치환)
- 코드블록 (` ``` ``` `) 전체 내용
- import 문
- URL, 이미지 경로
- HTML 엔티티 (`&amp;`, `&lt;`, `&gt;` 등)
- HTML 태그 구조 및 속성
- 마크다운 구조 (헤더, 리스트, 들여쓰기)

**치환되는 요소**:
- 모든 텍스트 → `_TEXT_`
- 인라인코드 텍스트 → `` `_TEXT_` ``
- 링크 텍스트 → `[_TEXT_](url)` (URL은 보존)
- 이미지 alt 텍스트 → `![_TEXT_](url)` (URL은 보존)
- Bold → `**_TEXT_**`, Italic → `*_TEXT_*`
- 구두점(마침표, 쉼표, 물음표 등) 제거

**정규화 규칙**:
- 인라인코드/링크/HTML 태그/Bold/Italic 뒤에 공백 없이 텍스트가 붙으면 공백 삽입
- 연속 `_TEXT_` 플레이스홀더는 하나로 병합
- 패턴 순서 통일: `_TEXT_` → `` `_TEXT_` `` → `**_TEXT_**` → `*_TEXT_*`
- 후행 `_TEXT_` 제거 (포맷팅 패턴 뒤의 단순 텍스트)

### 비교 흐름

1. 번역본 MDX → `.skel.mdx` 생성
2. 대응하는 한국어 MDX → `.skel.mdx` 생성
3. `diff -u -U 2 -b`로 두 스켈레톤 비교
4. `ignore_rules.yaml`로 허용된 차이 필터링
5. 차이가 있으면 스켈레톤 diff + 원본 내용 diff 모두 출력

## 사용 시나리오별 명령

### 전체 비교 실행

```bash
# 기본 실행 (max-diff=5)
bin/skeleton/cli.py -r

# 충분한 diff 출력으로 전체 현황 파악
bin/skeleton/cli.py -r --max-diff=50

# unmatched 파일 목록을 파일로 저장
bin/skeleton/cli.py -r --max-diff=100 --output /tmp/unmatched.txt
```

### 파일 존재 여부 비교 (구조 비교 없이)

```bash
# 3개 언어 중 누락된 파일만 표시
bin/skeleton/cli.py --compare

# 모든 파일 표시 (3개 언어 모두 존재하는 파일 포함)
bin/skeleton/cli.py --compare --verbose
```

출력 형식: `/path/to/file.mdx ko en ja` (누락 시 `-` 표시)

### 단일 파일 비교

```bash
# 변환 + 한국어 스켈레톤과 비교
bin/skeleton/cli.py target/ja/administrator-manual/databases/db-connections.mdx

# ignore 규칙 적용하여 비교
bin/skeleton/cli.py --use-ignore target/ja/administrator-manual/databases/db-connections.mdx
```

### 스켈레톤 파일 정리

```bash
# 모든 .skel.mdx 파일 삭제 (기본 디렉토리)
bin/skeleton/cli.py --reset

# 특정 디렉토리만 정리
bin/skeleton/cli.py --reset target/ja
```

### 순차 리뷰 (review-skeleton-diff.sh)

unmatched 파일 목록을 입력받아 파일별로 순차 리뷰합니다.

```bash
# 먼저 unmatched 목록 생성
bin/skeleton/cli.py -r --max-diff=100 --output /tmp/unmatched.txt

# 대화형 리뷰 (파일별 확인 후 계속)
bin/review-skeleton-diff.sh /tmp/unmatched.txt

# 자동 진행 (확인 없이 전체 실행)
bin/review-skeleton-diff.sh --yes /tmp/unmatched.txt
```

## ignore_rules.yaml

특정 파일의 특정 라인을 diff 비교에서 제외할 수 있습니다. 코드블록 내 번역 등 구조적으로 다를 수밖에 없는 경우에 사용합니다.

**파일 위치**: `confluence-mdx/bin/skeleton/ignore_rules.yaml`

**형식**:
```yaml
ignores:
  - file: target/ja/path/to/file.mdx    # target/{lang}/ 접두사 포함
    line_numbers: [41, 56, 92]           # 원본 .mdx 파일의 라인 번호
```

**사용 예시**: 코드블록 내 한국어 주석이 일본어로 번역된 경우

```yaml
ignores:
  # Code block 내부의 한국어 주석이 일본어로 번역된 경우
  # Line 251: KO: # 특정 하위 경로  →  JA: # 特定のサブパス
  - file: target/ja/administrator-manual/web-apps/wac-quickstart/1028-wac-rbac-guide.mdx
    line_numbers: [251, 252]
```

## 불일치 발견 시 처리 방법

### 사례 1: 원본 파일 변경

**증상**: 번역 완료 후 한국어 원본이 업데이트됨

**해결책**:
1. git 로그로 원본 변경 시점 확인:
   ```bash
   git log --follow --oneline --since="2025-09-25" src/content/ko/path/to/file.mdx
   ```
2. 원본과 번역 파일 비교하여 차이 파악
3. 번역 파일을 원본에 맞게 업데이트

### 사례 2: 번역 오류

**증상**: 공백, 포맷팅 차이, 누락/추가된 콘텐츠

**해결책**:
1. 번역 파일을 원본과 동일한 구조로 수정
2. 공백, 줄 바꿈을 원본과 정확히 일치시킴
3. 누락된 콘텐츠 번역, 추가된 콘텐츠 제거

**일반적인 공백 문제 예시**:
```markdown
# 원본 (ko)
**Setting** 문서

# 잘못된 번역 (ja) — 공백 누락
**Setting**文書

# 올바른 번역 (ja) — 공백 유지
**Setting** 文書
```

### 사례 3: 정상적인 차이 (ignore 처리)

**증상**: 코드블록 내 한국어가 번역된 경우, 어순 차이로 인한 구조 변경

**해결책**:
1. 차이가 불가피한지 확인
2. `ignore_rules.yaml`에 해당 파일/라인 추가
3. 주석으로 차이 사유 기록

## 비교에서 파일 제외

```bash
# 기본 제외: /index.skel.mdx
bin/skeleton/cli.py -r

# 추가 경로 제외
bin/skeleton/cli.py -r --exclude /index.skel.mdx /release-notes/overview.skel.mdx
```

## 번역 수정 시 주의사항

- `skeleton/cli.py` 스크립트를 수정하지 않음
- [docs/translation.md](/docs/translation.md)의 번역 규칙 준수
- 마크다운 포맷팅을 원본과 정확히 일치시킴
- 줄 바꿈, 공백 차이도 불일치로 감지됨

## 테스트

```bash
cd confluence-mdx/
source venv/bin/activate
python -m pytest tests/test_mdx_to_skeleton.py -v
```

## 상세 문서

- **Skeleton MDX 개념**: [docs/translation.md](/docs/translation.md)
- **번역 가이드라인**: [translation.md](translation.md)
