# MDX 스켈레톤 비교 가이드라인

## 개요

이 skill은 `mdx_to_skeleton.py` 도구를 사용하여 한국어 원본 MDX 파일과 번역본(영어/일본어) 간의 불일치를 감지하기 위한 가이드라인을 제공합니다.

**Skeleton MDX 개념**: [docs/translation.md](/docs/translation.md)의 "Skeleton MDX 를 비교하기" 섹션을 참조하세요.

## 도구 위치

- **스크립트**: `confluence-mdx/bin/mdx_to_skeleton.py`
- **지원 모듈**: `confluence-mdx/bin/skeleton_diff.py`, `skeleton_common.py`

## 빠른 시작

```bash
cd confluence-mdx/
source venv/bin/activate

# 전체 비교 실행 (최대 20개 차이까지 출력)
bin/mdx_to_skeleton.py --recursive --max-diff=20

# 특정 파일 비교
bin/mdx_to_skeleton.py target/en/path/to/file.mdx
```

## 작동 방식

1. MDX 파일에서 텍스트 콘텐츠를 `_TEXT_` 플레이스홀더로 대체
2. 문서 구조만 남긴 `.skel.mdx` 파일 생성
3. 한국어 원본과 번역본의 스켈레톤 비교
4. 구조적 차이 보고 (공백, 줄 바꿈, 포맷팅)

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

# 잘못된 번역 (ja)
**Setting**文書

# 올바른 번역 (ja)
**Setting** 文書
```

## 비교에서 파일 제외

```bash
bin/mdx_to_skeleton.py --recursive --max-diff=5 --exclude /index.skel.mdx
```

## 정상적인 차이 예외

다음 경우는 구조 차이가 발생할 수 있으며 정상으로 간주합니다:
- 어순/표현 방식 차이로 인한 자연스러운 번역
- 코드 블록 내 한국어를 영어/일본어로 번역한 경우

## 번역 수정 시 주의사항

- `mdx_to_skeleton.py` 스크립트를 수정하지 않음
- [docs/translation.md](/docs/translation.md)의 번역 규칙 준수
- 마크다운 포맷팅을 원본과 정확히 일치시킴

## 상세 문서

- **Skeleton MDX 개념**: [docs/translation.md](/docs/translation.md)
- **번역 가이드라인**: [.claude/skills/translation.md](/.claude/skills/translation.md)

