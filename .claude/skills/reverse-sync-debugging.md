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
bin/fetch_cli.py --recent

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

## 디버깅 절차

실패하는 문서가 발견된 경우, 다음 절차를 통해 원인을 분석하고 수정한다.

(디버깅 세부 절차는 추후 추가 예정)
