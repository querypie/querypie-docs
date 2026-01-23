# Commit Log 작성 Skill

querypie-docs 저장소의 commit 관습에 맞게 commit message를 작성합니다.

> **상세 가이드**: [docs/commit-pr-guide.md](/docs/commit-pr-guide.md)

## 작업 순서

1. `git branch --show-current`로 현재 브랜치 확인
2. **main 브랜치인 경우**: feature branch 생성 후 checkout
3. **main 브랜치가 아닌 경우**: 현재 브랜치에서 작업 계속
4. `git status`와 `git diff --staged`로 변경사항 확인
5. 변경사항이 없으면 사용자에게 알림
6. 변경사항을 분석하여 commit message 초안 작성
7. 사용자에게 확인 후 commit 실행

## 브랜치 이름 형식

```
<username>/<type>-<간단한-설명>
```

**Username**: `jk`, `kelly`, `dave`, `jane` (git config에서 유추)

## 핵심 규칙

- **제목**: `<type>(<scope>): <한국어 설명>` 또는 `<prefix>: <한국어 설명>`
- **본문**: `## Summary`로 시작, 배경/이유/목적 한 문장 + bullet point로 변경사항 기술
- **언어**: 한국어, 경어체(~합니다), 능동태
- **제목 길이**: 50자 이내

## Claude 사용 시

```
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

## 참조

- Type/Prefix 종류: [docs/commit-pr-guide.md#type-종류](/docs/commit-pr-guide.md#type-종류)
- 본문 형식: [docs/commit-pr-guide.md#본문-형식](/docs/commit-pr-guide.md#본문-형식)
- 작성 지침: [docs/commit-pr-guide.md#작성-지침](/docs/commit-pr-guide.md#작성-지침)
- 예시: [docs/commit-pr-guide.md#예시](/docs/commit-pr-guide.md#예시)
