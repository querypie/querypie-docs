#!/bin/bash
#
# create-mdx-pr.sh
#
# Confluence MDX 변경사항에 대한 PR을 자동으로 생성하는 스크립트
#
# 사용법:
#   ./create-mdx-pr.sh <event_name> <actor>
#
# 환경 변수:
#   GH_TOKEN: GitHub CLI 인증을 위한 토큰

set -o errexit -o nounset -o pipefail -o xtrace

EVENT_NAME="${1:-workflow_dispatch}"
ACTOR="${2:-github-actions[bot]}"

# Git 사용자 설정
if [[ "$EVENT_NAME" == "schedule" ]]; then
  git config user.name "github-actions[bot]"
  git config user.email "github-actions[bot]@users.noreply.github.com"
else
  git config user.name "$ACTOR"
  git config user.email "$ACTOR@users.noreply.github.com"
fi

# src/content/, public/, confluence-mdx/var/ 변경사항 확인 (unstaged 상태, untracked 파일 포함)
if ! git status --porcelain src/content/ public/ confluence-mdx/var/ | grep -q .; then
  echo "No changes in src/content/, public/, or confluence-mdx/var/ directory"
  exit 0
fi

# 브랜치 이름 생성 (타임스탬프)
BRANCH_NAME="mdx/confluence-updates-$(date +%Y%m%d-%H%M%S)"

# 브랜치 생성 및 체크아웃
git checkout -b "$BRANCH_NAME"

# src/content/, public/, confluence-mdx/var/ 변경사항 스테이징
git add src/content/ public/ confluence-mdx/var/

# 스테이징된 변경사항 확인
STAGED_FILES=$(git diff --cached --name-only)
if [[ -z "$STAGED_FILES" ]]; then
  echo "No staged changes in src/content/, public/, or confluence-mdx/var/"
  exit 0
fi

# 변경사항 정보 수집 (스테이징 후)
CHANGES_STATUS=$(git status --short src/content/ public/ confluence-mdx/var/)
CHANGES_STAT=$(git diff --cached --stat HEAD)

# 커밋
git commit -m "mdx: Updates from Confluence"

# 브랜치 푸시 (PR 생성 전에 필요)
if ! git push -u origin "$BRANCH_NAME"; then
  echo "Failed to push branch $BRANCH_NAME"
  exit 1
fi

# PR Description 생성
PR_BODY=$(cat <<EOF
## Description

This PR contains automatically generated MDX files from Confluence documentation.

> **Note for AI Agents**: This is an auto-generated PR by the workflow \`.github/workflows/generate-mdx-from-confluence.yml\`. The MDX files are synchronized from Confluence pages and should be reviewed before merging.

### Translation Required

If this PR includes changes to Korean (\`ko\`) documentation, corresponding translations to English (\`en\`) and Japanese (\`ja\`) are required before merging.

## Changes

$CHANGES_STATUS

## Change Statistics

$CHANGES_STAT
EOF
)

# PR 생성
if ! gh pr create \
  --title "mdx: Sync documentation updates from Confluence" \
  --body "$PR_BODY" \
  --base main \
  --head "$BRANCH_NAME"; then
  echo "Failed to create PR for branch $BRANCH_NAME"
  exit 1
fi

echo "Pull request created successfully for branch $BRANCH_NAME"
