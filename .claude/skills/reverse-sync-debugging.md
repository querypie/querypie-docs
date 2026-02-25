# Reverse Sync 디버깅 가이드

## 개요

`reverse_sync_cli.py verify` 실행 시 실패하는 문서를 발견했을 때, 원인을 분석하고 수정하는 디버깅 워크플로우이다.

**소스 코드**: [confluence-mdx/bin/reverse_sync_cli.py](/confluence-mdx/bin/reverse_sync_cli.py)
**관련 Skill**: [reverse-sync.md](reverse-sync.md) — Reverse Sync 기본 사용 가이드

## 사전 준비

### 1. Confluence 원문 최신화

`reverse_sync_cli.py`를 실행하려면 Confluence 원본 XHTML이 로컬에 있어야 한다.

```bash
cd confluence-mdx

# 방법 A: 최근 변경 페이지만 가져오기 (빠름)
bin/fetch_cli.py --recent --attachments

# 방법 B: 전체 페이지를 첨부파일과 함께 가져오기 (완전)
bin/fetch_cli.py --remote --attachments
```

main 브랜치가 최신인지 먼저 확인한다:

```bash
git fetch origin main
git log HEAD..origin/main --oneline   # 뒤처진 커밋이 있는지 확인
```

### 2. 대상 브랜치 준비

디버깅 대상 브랜치를 로컬에 체크아웃하고 remote 변경사항을 반영한다:

```bash
git checkout {branch}
git pull origin {branch}   # remote 변경사항 반영
```

## 검증 실행

```bash
git checkout main   # 검증 명령을 수행하는 것은 main 브랜치에서 수행한다.
cd confluence-mdx
bin/reverse_sync_cli.py verify --branch={branch}
```

### 결과 판정

- **모든 파일이 `pass` 또는 `no_changes`**: 디버깅할 것이 없다. 작업 완료.
- **`fail` 또는 `error`가 있는 경우**: 아래 디버깅 절차를 진행한다.

실패 건만 빠르게 확인하려면:

```bash
bin/reverse_sync_cli.py verify --branch={branch} --failures-only
```

## 용어와 개념

- original.mdx: main 브랜치의 MDX 파일.
  - Confluence 원문의 XHTML 을 Forward Convert 로 변환한 파일이다.
  - 일반적으로, Confluence 원문은 original.mdx 와 동일한 내용을 가진다.
- improved.mdx: 대상 브랜치의 변경된 MDX 파일. 사람 또는 AI Agent 가 변경한 MDX 파일이다.
- verified.mdx: Reverse Sync 를 위해 Round-Trip Verification 과정에서 생성된 MDX 파일이다. 
  - original.mdx 와 improved.mdx 의 차이를 기반으로, Confluence XHTML (page.xhtml) 파일을 변경(Patch)한 후,
    이 patched.xhtml 을 다시 Forward Convert 로 변환한 파일이다.
  - verified.mdx 와 improved.mdx 과 동일하면, verify 에 성공한 것이다.
- Forward Convert:
  - Confluence 원문의 XHTML (page.xhtml)을 Markdown(정확히는 MDX) 형식으로 변환하는 코드의 실행
  - 이 코드는 가능한 XHTML 원문의 구조와 특성을 Markdown 으로 그대로 변환하는 것을 목표로 한다.
  - XHTML 의 컨텐츠, 문구의 오류, 오기, 불필요한 요소를 제거하거나 변경하는 행위를 최소화하는 것을 지향한다.
  - XHTML 컨텐츠, 문구의 오류, 오기, 불필요한 요소가 발견되면, 이것을 교정/교열 과정을 통해 수정하고, Reverse Sync 를 수행하여, Confluence XHTML 원문을 수정하는 것을 지향한다.
- XHTML Patch:
  - original.mdx 와 improved.mdx 의 차이를 기반으로, Confluence XHTML (page.xhtml) 파일을 변경(Patch)하는 코드의 실행
- Reverse Sync:
  - original.mdx 를 수정한 경우, 이 변경사항을 Confluence XHTML 로 변환하고, Confluence 원문에 적용하는 것
  - Reverse Sync 과정의 오류를 방지하기 위해, Round Trip Verification 과정으로 검증한다.
- Round-Trip Verification:
  - improved.mdx 와 verified.mdx 가 동일한지 여부를 검증하는 것
  - Confluence 원문을 변경하지 않고, 원문 변경의 효과를 미리 확인하는 과정이다.
  - XHTML Patch, Forward Convert 과정의 오류를 발견할 수 있다.
- verify 에 실패하는 원인: 다음의 두 가지 사항이 있으며, 이 가운데 XHTML Patch 코드의 버그일 가능성이 높다.
  - XHTML Patch 를 수행하는 코드의 버그
  - Forward Convert 를 수행하는 코드의 버그

## 디버깅 절차

실패하는 문서가 발견된 경우, 다음 절차를 통해 원인을 분석하고 수정한다.

### 1. 실패 문서에 대해 검증 결과 확인하기

특정 MDX 문서에 대해 Round-Trip Verification 과정을 통해 검증 결과를 확인한다.
```bash
bin/reverse_sync_cli.py verify {branch}:{path/to/failed.mdx}
```

(설명 추가 필요)
```bash
bin/reverse_sync_cli.py debug {branch}:{path/to/failed.mdx}
```

### 2. 실패 결과를 재현하는 테스트케이스를 추가하기

### 3. commit 하고 PR 을 생성하기

Draft PR 을 생성한다.

### 4. 실패 원인을 분석하고 수정하기

### 5. 로컬 테스트 수행하기

### 6. commit 하고 PR 을 업데이트하기

Review 가능하다고 PR 상태를 전환한다.
최종 commit 을 포함한 상태를 반영하여, PR title, description 을 재작성한다.

