# Confluence XHTML 변환 테스트케이스 추가 가이드

## 개요

이 skill은 `confluence_xhtml_to_markdown.py` 스크립트의 테스트케이스를 추가하는 방법을 안내합니다.

**상세 사용법**: [confluence-mdx/tests/README.md](/confluence-mdx/tests/README.md)를 참조하세요.

## 테스트케이스 추가 워크플로우

### 사전 준비

```bash
cd confluence-mdx/tests
source ../venv/bin/activate
```

### 방법 1: 기존 Confluence 페이지로 테스트케이스 추가

Confluence에서 다운로드된 페이지를 테스트케이스로 사용하는 경우:

```bash
# 1. 테스트케이스 디렉토리 생성
mkdir -p testcases/<page-id>

# 2. Confluence 데이터 복사
./copy-files-to-testcases.sh

# 3. 예상 출력 생성
python ../bin/confluence_xhtml_to_markdown.py \
  testcases/<page-id>/page.xhtml \
  testcases/<page-id>/output.mdx

# 4. 출력 검토 후 예상 파일로 저장
./update-expected-mdx.sh
```

### 방법 2: 합성 테스트케이스 추가

특정 변환 케이스를 테스트하기 위해 XHTML을 직접 작성하는 경우:

```bash
# 1. 테스트케이스 디렉토리 생성
mkdir -p testcases/<descriptive-name>

# 2. page.xhtml 수동 작성
# testcases/<descriptive-name>/page.xhtml 파일 생성

# 3. 예상 출력 생성 및 검토
python ../bin/confluence_xhtml_to_markdown.py \
  testcases/<descriptive-name>/page.xhtml \
  testcases/<descriptive-name>/output.mdx

# 4. 검토 후 예상 파일로 복사
cp testcases/<descriptive-name>/output.mdx \
   testcases/<descriptive-name>/expected.mdx
```

## 테스트 실행

```bash
# 모든 테스트 실행
make test

# 특정 테스트만 실행
make test-one TEST_ID=<page-id>

# 출력 파일 정리
make clean
```

## 테스트케이스 업데이트

변환 스크립트 수정 후 예상 출력을 업데이트해야 하는 경우:

```bash
# 1. 새 출력 생성
make test-xhtml

# 2. 출력 검토 후 예상 파일로 반영
./update-expected-mdx.sh
```

## 테스트케이스 구조

```
testcases/<page-id>/
├── page.xhtml        # 입력 (필수)
├── page.yaml         # 페이지 메타데이터 (선택)
├── expected.mdx      # 예상 출력 (필수)
└── output.mdx        # 실제 출력 (테스트 시 생성)
```

## 모범 사례

1. **설명적인 이름 사용**: 합성 테스트케이스는 테스트 목적을 설명하는 이름 사용
2. **최소한의 XHTML**: 테스트하려는 기능만 포함하는 간결한 XHTML 작성
3. **출력 검토**: `expected.mdx`로 저장하기 전에 `output.mdx`를 반드시 검토
4. **회귀 테스트**: 버그 수정 시 해당 케이스를 테스트케이스로 추가