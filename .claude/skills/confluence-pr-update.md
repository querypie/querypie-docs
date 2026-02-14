# Confluence MDX PR 수정 가이드라인

## 개요

이 skill은 `generate-mdx-from-confluence.yml` GitHub Actions 워크플로우에서 생성된 PR을 수정하는 작업 절차를 설명합니다.

## 배경

- **워크플로우**: `.github/workflows/generate-mdx-from-confluence.yml`
- **목적**: Confluence에서 한국어 MDX 문서를 자동 동기화
- **PR 브랜치 형식**: `mdx/confluence-updates-YYYYMMDD-HHMMSS`
- **추가 작업 필요**: 이미지 첨부 확인, 영어/일본어 번역

## 전체 워크플로우

### Step 1: PR 브랜치 체크아웃

```bash
# PR 브랜치 확인 및 체크아웃
git fetch origin
git checkout mdx/confluence-updates-YYYYMMDD-HHMMSS
```

### Step 2: 첨부파일 누락 확인 및 동기화 재실행

MDX 파일에서 참조하는 이미지가 `public/` 디렉토리에 존재하는지 확인합니다. **첨부파일이 누락된 경우에만** 로컬에서 동기화를 재실행합니다.

```bash
# 변경된 MDX 파일에서 참조하는 이미지 경로 확인
# 예: <figure src="/path/to/image.png" ... />

# 해당 이미지가 public/ 디렉토리에 존재하는지 확인
ls public/path/to/image.png
```

**첨부파일이 누락된 경우에만** 다음을 실행합니다:

```bash
cd confluence-mdx
source venv/bin/activate

# 이미지 첨부 포함하여 재실행
bin/fetch_cli.py --recent --attachments
bin/convert_all.py
```

**참고**: `--attachments` 옵션은 Confluence 페이지의 첨부 이미지를 `public/` 디렉토리에 복사합니다. 이미 모든 첨부파일이 존재하면 이 단계를 건너뜁니다.

### Step 3: 변경된 한국어 문서 확인

```bash
# 한국어 문서 변경 확인
git diff src/content/ko/

# 새로 추가된 이미지 확인
git status public/
```

### Step 4: 영어/일본어 번역 수행

변경된 한국어 문서에 대응하는 영어/일본어 파일을 번역합니다.

**파일 경로 규칙**:
- 한국어: `src/content/ko/path/to/file.mdx`
- 영어: `src/content/en/path/to/file.mdx`
- 일본어: `src/content/ja/path/to/file.mdx`

**번역 지침**:
- [docs/translation.md](/docs/translation.md) 및 [translation.md](translation.md)의 번역 규칙 준수

### Step 5: Skeleton MDX 비교로 검증

번역 후 구조 일치를 확인합니다. 사용법은 [mdx-skeleton-comparison.md](mdx-skeleton-comparison.md)를 참조하세요.

```bash
cd confluence-mdx
source venv/bin/activate
bin/skeleton/cli.py --recursive --max-diff=10
```

**중요**: 빈 줄의 누락/추가 차이도 감지합니다. 번역 파일은 한국어 원본과 **라인 수와 빈 줄 위치가 정확히 일치**해야 합니다.

### Step 6: 코드 블록 일치 확인

**중요**: 코드 블록 내용은 한국어/영어/일본어 문서에서 **동일**해야 합니다.

**잘못된 예** - 코드 블록 내 주석을 번역함:

```bash
# クラスタアクセス確認  ← 일본어로 번역 (잘못됨)
kubectl get nodes
```

**올바른 예** - 코드 블록 내용 동일:

```bash
# Verify cluster access  ← 원본 그대로 유지
kubectl get nodes
```

코드 블록 내 주석은 번역하지 않고 원본(주로 영어) 그대로 유지합니다.

### Step 7: 변경사항 커밋

```bash
# 변경사항 확인
git status
git diff

# 스테이징 및 커밋
git add src/content/en/ src/content/ja/ public/
git commit -m "$(cat <<'EOF'
mdx: 영어/일본어 번역 추가 (한국어 문서 변경 대응)

- 한국어 문서 변경에 대응하는 영어/일본어 번역을 추가합니다.
- Skeleton MDX 비교로 구조 일치를 확인합니다.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"

# 푸시
git push origin HEAD
```

### Step 8: PR 제목/설명 업데이트 (필요 시)

**PR title prefix 규칙**:
- `mdx:` — MDX 콘텐츠 파일(`src/content/`)의 추가/수정/번역. Confluence 동기화, 번역, 교정/교열 등.
- `docs:` — 저장소 내부 문서/지침(`docs/`, `.claude/skills/`, `README.md` 등)의 추가/수정. 콘텐츠가 아닌 개발/운영 문서.
- `feat:`, `fix:`, `chore:` 등 — 코드/인프라 변경에 대한 일반적인 conventional commit prefix.

```bash
# PR 제목 업데이트
gh pr edit <PR번호> --title "mdx: <변경 내용 요약>"

# PR 설명 업데이트
gh pr edit <PR번호> --body "$(cat <<'EOF'
## Summary
- Confluence에서 한국어 MDX 문서를 동기화합니다.
- 영어/일본어 번역을 추가합니다.

## Changes
- `src/content/ko/path/to/file.mdx`: 변경 내용
- `src/content/en/path/to/file.mdx`: 영어 번역
- `src/content/ja/path/to/file.mdx`: 일본어 번역

🤖 Generated with {Codex|[Claude Code](https://claude.com/claude-code)}
EOF
)"
```

## 체크리스트

- [ ] PR 브랜치 체크아웃
- [ ] 첨부파일 누락 시 `--attachments` 옵션으로 동기화 재실행
- [ ] 영어 번역 완료
- [ ] 일본어 번역 완료
- [ ] Skeleton MDX 비교 통과 (빈 줄 차이 포함)
- [ ] 코드 블록 내용 일치 확인
- [ ] 커밋 및 푸시
- [ ] PR 제목/설명 업데이트

## 일반적인 문제 해결

### 이미지가 누락된 경우

```bash
# 이미지 포함하여 재실행
cd confluence-mdx
bin/fetch_cli.py --recent --attachments
bin/convert_all.py

# 새 이미지 확인
git status public/
```

### Skeleton 불일치가 발생한 경우

[mdx-skeleton-comparison.md](mdx-skeleton-comparison.md)의 "불일치 발견 시 처리 방법"을 참조하세요.

### 코드 블록 내 주석이 번역된 경우

코드 블록 내용을 한국어 원본(또는 영어 원본)과 동일하게 복원합니다.

## 관련 문서

- **Confluence MDX 변환**: [confluence-mdx.md](confluence-mdx.md)
- **Skeleton MDX 비교**: [mdx-skeleton-comparison.md](mdx-skeleton-comparison.md)
- **번역 가이드라인**: [translation.md](translation.md)
- **한국어→영어/일본어 동기화**: [sync-ko-to-en-ja.md](sync-ko-to-en-ja.md)
