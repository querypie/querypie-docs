---
name: confluence-mdx
description: "Confluence 문서를 QueryPie MDX 콘텐츠로 변환하거나 Confluence Space sync로 한국어 MDX를 갱신하고 영어/일본어 번역, Skeleton MDX 비교 검증, PR 갱신까지 수행할 때 사용합니다."
---

# Confluence에서 MDX로 변환 가이드라인

## 개요

이 skill은 Confluence에서 MDX로 변환하는 워크플로우에 대한 가이드라인을 제공합니다.

**상세 사용법**: [confluence-mdx/README.md](/confluence-mdx/README.md)를 반드시 참조하세요.

## 관련 Skill 및 CLI 문서

- **Confluence 자동 동기화 PR 보정**: [confluence-pr-update](../confluence-pr-update/SKILL.md)
- **번역 지침**: [translation](../translation/SKILL.md), [docs/translation.md](/docs/translation.md)
- **한국어 변경분의 en/ja 동기화**: [sync-ko-to-en-ja](../sync-ko-to-en-ja/SKILL.md)
- **Skeleton MDX 비교**: [mdx-skeleton-comparison](../mdx-skeleton-comparison/SKILL.md)
- **Commit 및 PR 작성**: [commit](../commit/SKILL.md), [docs/commit-pr-guide.md](/docs/commit-pr-guide.md)
- **Confluence 데이터 fetch CLI**: [bin/fetch_cli.py](/confluence-mdx/bin/fetch_cli.py)
- **전체 변환 CLI**: [bin/convert_all.py](/confluence-mdx/bin/convert_all.py)
- **Skeleton 비교 CLI**: [bin/skeleton/cli.py](/confluence-mdx/bin/skeleton/cli.py)
- **한국어 commit 동기화 CLI**: [bin/sync_ko_commit.py](/confluence-mdx/bin/sync_ko_commit.py)
- **이미지 alt 복원 CLI**: [bin/restore_alt_from_diff.py](/confluence-mdx/bin/restore_alt_from_diff.py)

## 프로젝트 컨텍스트

- **변환 스크립트**: `confluence-mdx/bin/`에 위치
- **Python 환경**: 가상 환경을 사용하는 Python 3
- **입력 형식**: Confluence XHTML 내보내기
- **출력 형식**: `src/content/ko/`의 MDX 파일

## 디렉토리 구조 요약

```
confluence-mdx/
├── bin/                    # 변환 스크립트
├── var/                    # Confluence 데이터용 작업 디렉토리
├── etc/                    # 설정 및 번역 파일
├── target/                 # 출력 디렉토리
└── tests/                  # 테스트 케이스
```

## 변환 워크플로우 개요

### Confluence Space sync 기반 PR 작업

Confluence Space 전체 또는 최근 변경분을 동기화해 MDX 문서 PR을 만들 때는 다음 순서를 따른다.

1. **branch 생성**
   - worktree가 아니라 일반 git branch를 만든다.
   - `confluence-mdx/var/` 아래 symlink와 변환 출력 경로가 정상 동작하려면 별도 worktree를 사용하지 않는다.
   - 최신 `origin/main` HEAD를 기준으로 branch를 생성하고 checkout한다.

   ```bash
   git fetch origin --prune
   git switch -c docs/<descriptive-mdx-update-name> origin/main
   ```

2. **Confluence Space 데이터 fetch**
   - 반드시 `confluence-mdx` 디렉토리에서 실행한다.
   - 최근 변경된 Confluence 데이터와 attachment를 로컬 `var/` 아래로 내려받는다.
   - 상세 옵션은 [bin/fetch_cli.py](/confluence-mdx/bin/fetch_cli.py) 및 [confluence-mdx/README.md](/confluence-mdx/README.md)의 `fetch_cli.py` 섹션을 확인한다.

   ```bash
   cd confluence-mdx
   source venv/bin/activate
   bin/fetch_cli.py --recent --attachments
   ```

3. **한국어 MDX 생성**
   - `convert_all.py`로 한국어 MDX와 public asset 출력을 갱신한다.
   - 상세 옵션은 [bin/convert_all.py](/confluence-mdx/bin/convert_all.py) 및 [confluence-mdx/README.md](/confluence-mdx/README.md)의 `convert_all.py` 섹션을 확인한다.

   ```bash
   bin/convert_all.py
   ```

4. **한국어 변경사항 PR 작성**
   - `git status --short`와 diff를 확인한다.
   - 변경된 한국어 MDX, attachment, 변환 metadata를 포함해 commit을 만든다.
   - repository의 [commit](../commit/SKILL.md) 및 [PR 작성 지침](/docs/commit-pr-guide.md)을 따른다.
   - 이 시점의 PR은 한국어 MDX 변환 결과를 먼저 리뷰 가능한 형태로 올리기 위한 중간 PR이다.

5. **영어/일본어 번역 반영**
   - 변경된 한국어 MDX 파일에 대응하는 `src/content/en/**`, `src/content/ja/**` 문서를 번역하거나 생성한다.
   - 기존 문서가 있으면 구조와 frontmatter를 유지하며 갱신한다.
   - 새 문서가 필요한 경우 한국어 문서와 대응되는 경로에 생성한다.
   - 번역 작업은 [translation](../translation/SKILL.md) 및 [sync-ko-to-en-ja](../sync-ko-to-en-ja/SKILL.md) skill 지침을 함께 따른다.
   - 한국어 commit을 기준으로 구조 변경을 먼저 반영할 때는 [bin/sync_ko_commit.py](/confluence-mdx/bin/sync_ko_commit.py)를 사용하고, 이미지 alt 복원은 [bin/restore_alt_from_diff.py](/confluence-mdx/bin/restore_alt_from_diff.py)를 확인한다.

6. **Skeleton MDX 비교 검증**
   - 변경된 한국어 문서와 대응 영어/일본어 문서를 Skeleton MDX 비교로 확인한다.
   - Skeleton 비교 시 `src/content/{lang}/`가 아니라 `confluence-mdx/target/{lang}/` 경로를 사용한다.
   - heading, list, table, admonition, code block, image, link 구조 차이를 확인하고 번역 MDX를 개선한다.
   - 상세 사용법은 [mdx-skeleton-comparison](../mdx-skeleton-comparison/SKILL.md) 및 [bin/skeleton/cli.py](/confluence-mdx/bin/skeleton/cli.py)를 확인한다.

   ```bash
   bin/skeleton/cli.py target/en/path/to/page.mdx
   bin/skeleton/cli.py target/ja/path/to/page.mdx
   ```

7. **PR에 번역 변경 포함 및 PR 갱신**
   - 영어/일본어 변경사항을 commit하고 기존 PR에 push한다.
   - PR title과 description을 최종 범위에 맞게 다시 작성한다.
   - PR 본문에는 Confluence fetch/convert, 번역 반영, Skeleton 비교 검증 결과를 요약한다.
   - 자동 동기화 PR 보정 흐름은 [confluence-pr-update](../confluence-pr-update/SKILL.md)를 함께 확인한다.

8. **완료 확인**
   - 최종 `git status --short`가 의도한 변경만 포함하는지 확인한다.
   - 실행한 검증 명령과 남은 리스크를 작업 결과에 기록한다.

### 빠른 시작

```bash
cd confluence-mdx
source venv/bin/activate

# 1. Confluence 데이터 수집
bin/fetch_cli.py --recent --attachments

# 2. pages.yaml 기준으로 전체 변환
bin/convert_all.py
```

### 변환 단계

1. **데이터 수집** (`fetch_cli.py`): Confluence API 또는 로컬 데이터에서 `var/` 갱신
2. **전체 변환** (`convert_all.py`): `var/pages.yaml` 기반으로 `target/ko` 및 `target/public`에 반영

## 일반적인 작업

### 특정 페이지만 업데이트

```bash
# 특정 페이지를 루트로 하위 트리 다운로드
bin/fetch_cli.py --remote --start-page-id <page_id> --attachments

# 단일 파일 수동 변환
bin/converter/cli.py var/<page_id>/page.xhtml target/ko/path/to/page.mdx
```

### 번역 문제 처리

제목이 번역되지 않은 경우:
1. `etc/korean-titles-translations.txt`에 번역 추가
2. `bin/convert_all.py --verify-translations`로 누락 여부 확인
3. `bin/convert_all.py` 재실행

### `src/content/` 로컬 변경이 있는 상태에서 깨끗하게 다시 시작

Confluence Space 기준으로 MDX 생성/업데이트를 다시 수행해야 하고, 사용자가 `src/content/` 아래 로컬 변경사항은 모두 무시해도 된다고 명시한 경우에만 다음 절차를 따른다.

1. `src/content/` 아래 tracked 로컬 변경사항을 reset한다.

   ```bash
   git restore --source=HEAD -- src/content
   ```

2. `src/content/` 아래 untracked 파일이 있으면 먼저 목록을 확인한 뒤, Confluence sync 작업 산출물로 버려도 되는 파일만 제거한다.

   ```bash
   git status --short -- src/content
   git clean -fd -- src/content
   ```

3. 최신 `main` HEAD를 가져오고, 이 기준으로 새 local branch를 만든다.

   ```bash
   git fetch origin --prune
   git switch -c docs/<descriptive-mdx-update-name> origin/main
   ```

4. 새 branch에서 Confluence Space 기준 MDX 생성/업데이트 절차를 다시 수행한다.

   ```bash
   cd confluence-mdx
   source venv/bin/activate
   bin/fetch_cli.py --recent --attachments
   bin/convert_all.py
   ```

## Python 환경 설정

```bash
cd confluence-mdx
python3 -m venv venv
source venv/bin/activate
pip install requests beautifulsoup4 pyyaml
```

## 테스트

```bash
cd confluence-mdx/tests
make test           # 모든 테스트 실행
make test-one TEST_ID=<test_id>  # 특정 테스트 실행
```

## 모범 사례

1. **변환 전 백업**: 기존 MDX 파일 백업
2. **로컬 테스트**: `npm run dev`로 변환 결과 확인
3. **점진적 업데이트**: `--start-page-id`로 특정 하위 트리만 업데이트

## 상세 문서

다음 문서에서 상세한 사용법을 확인하세요:

- **전체 사용법**: [confluence-mdx/README.md](/confluence-mdx/README.md)
- **Container 환경 설계**: [confluence-mdx/CONTAINER_DESIGN.md](/confluence-mdx/CONTAINER_DESIGN.md)
