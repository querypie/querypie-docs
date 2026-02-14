# 한국어 MDX 변경사항을 영어/일본어에 동기화

## 개요

이 skill은 한국어 MDX 문서의 구조적 변경(이미지 태그, 테이블 속성 등)을 영어/일본어 문서에 동기화하는 워크플로우를 설명합니다.

## 배경

- **한국어 MDX**: Confluence XHTML에서 자동 변환됨 (원본)
- **영어/일본어 MDX**: 한국어를 번역한 것
- **문제**: 한국어에 기술적 변경이 발생하면 영어/일본어도 동기화 필요

## 도구

### 1. sync_ko_commit.py

한국어 커밋의 변경사항을 영어/일본어 파일에 덮어쓰는 도구입니다.

```bash
cd confluence-mdx

# 기본 사용법 - 한국어 커밋 변경을 en/ja에 덮어쓰기
python3 bin/sync_ko_commit.py <commit-hash>

# dry-run (미리보기)
python3 bin/sync_ko_commit.py <commit-hash> --dry-run

# 특정 언어만 적용
python3 bin/sync_ko_commit.py <commit-hash> --lang en
python3 bin/sync_ko_commit.py <commit-hash> --lang ja
```

### 2. restore_alt_from_diff.py

sync_ko_commit.py 실행 후, git diff에서 기존 영어/일본어 alt 텍스트를 추출하여 복원합니다.

```bash
cd confluence-mdx

# 미리보기 - 어떤 alt가 복원되는지 확인
python3 bin/restore_alt_from_diff.py --dry-run

# 실제 적용
python3 bin/restore_alt_from_diff.py --apply

# 특정 언어만
python3 bin/restore_alt_from_diff.py --apply --lang en
```

## 전체 워크플로우

### Step 1: 한국어 커밋 확인

```bash
# 동기화할 한국어 커밋 확인
git log --oneline src/content/ko/ | head -10
```

### Step 2: 한국어 변경을 영어/일본어에 덮어쓰기

```bash
cd confluence-mdx
python3 bin/sync_ko_commit.py <commit-hash>
```

이 단계에서 한국어 라인이 영어/일본어 파일의 같은 위치에 복사됩니다.

### Step 3: 기존 번역 텍스트 복원 (이미지 alt 등)

```bash
# git diff에서 기존 alt 텍스트 복원
python3 bin/restore_alt_from_diff.py --dry-run  # 미리보기
python3 bin/restore_alt_from_diff.py --apply    # 적용
```

### Step 4: 나머지 한국어 텍스트 번역

git diff를 확인하여 아직 한국어로 남아있는 부분을 번역합니다:

```bash
git diff src/content/en/
git diff src/content/ja/
```

번역 시 [translation.md](/docs/translation.md) 가이드를 따릅니다.

### Step 5: 검증

Skeleton 구조 일치를 확인합니다. 상세 사용법은 [mdx-skeleton-comparison.md](mdx-skeleton-comparison.md)를 참조하세요.

```bash
cd confluence-mdx
python3 bin/skeleton/cli.py --recursive --max-diff=10
```

## 예시: 이미지 태그 width 동기화

한국어 커밋 `ae93da7e`가 이미지 태그에 width 속성을 추가한 경우:

```bash
# 1. 한국어 변경 덮어쓰기
cd confluence-mdx
python3 bin/sync_ko_commit.py ae93da7e

# 2. 기존 영어/일본어 alt 텍스트 복원
python3 bin/restore_alt_from_diff.py --apply

# 3. 검증
python3 bin/skeleton/cli.py --recursive --max-diff=10
```

## 주의사항

1. **라인 번호 일치 가정**: ko/en/ja 파일의 구조가 동일해야 함
2. **skeleton 일치 필요**: 동기화 전 skeleton이 일치해야 함 (번역 완료 상태)
3. **커밋 전 검증**: 반드시 skeleton 비교와 빌드 확인 수행

## 관련 문서

- **번역 가이드**: [docs/translation.md](/docs/translation.md)
- **Skeleton 비교**: [mdx-skeleton-comparison.md](mdx-skeleton-comparison.md)
- **Confluence MDX 변환**: [confluence-mdx.md](confluence-mdx.md)
