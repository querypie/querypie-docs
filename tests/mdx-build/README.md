# MDX Build Tests

`src/content/` 아래의 MDX 문서들을 독립적으로 빌드하여 테스트하는 도구입니다.

## 사용법

### 기본 사용법
```bash
# 단일 MDX 파일 테스트
./tests/mdx-build/test-mdx-build.sh src/content/ko/release-notes/1020-10212.mdx

# 다중 MDX 파일 테스트
./tests/mdx-build/test-mdx-build.sh src/content/ko/release-notes/1020-10212.mdx src/content/en/release-notes/1020-10212.mdx

# 모든 MDX 파일 테스트
./tests/mdx-build/test-mdx-build.sh $(find src/content -name "*.mdx")
```

### 파일 목록 확인
```bash
# 모든 MDX 파일 목록
find src/content -name "*.mdx" | sort

# 언어별 MDX 파일 목록
find src/content/ko -name "*.mdx" | sort  # 한국어
find src/content/en -name "*.mdx" | sort  # 영어
find src/content/ja -name "*.mdx" | sort  # 일본어
```

## 사용 예시

### 특정 문서 테스트
```bash
# QueryPie 개요 테스트
./tests/mdx-build/test-mdx-build.sh src/content/ko/querypie-overview.mdx

# 릴리즈 노트 테스트
./tests/mdx-build/test-mdx-build.sh src/content/ko/release-notes/1020-10212.mdx

# 관리자 매뉴얼 테스트
./tests/mdx-build/test-mdx-build.sh src/content/en/administrator-manual/databases/monitoring.mdx
```

### 카테고리별 테스트
```bash
# 릴리즈 노트만 테스트
./tests/mdx-build/test-mdx-build.sh $(find src/content -path "*/release-notes/*.mdx")

# 관리자 매뉴얼만 테스트
./tests/mdx-build/test-mdx-build.sh $(find src/content -path "*/administrator-manual/*.mdx")

# 사용자 매뉴얼만 테스트
./tests/mdx-build/test-mdx-build.sh $(find src/content -path "*/user-manual/*.mdx")
```

## 문제 해결

### 빌드 실패 시
1. MDX 파일 문법 오류 확인
2. 의존성 문제인 경우: `npm install`
3. 이미지 경로 문제 확인

### 테스트 환경 정리
```bash
# 테스트 디렉토리 정리 (tests/mdx-build/ 내부 파일들)
rm -rf tests/mdx-build/node_modules tests/mdx-build/.next tests/mdx-build/build.log
```