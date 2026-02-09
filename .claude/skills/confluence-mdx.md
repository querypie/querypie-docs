# Confluence에서 MDX로 변환 가이드라인

## 개요

이 skill은 Confluence에서 MDX로 변환하는 워크플로우에 대한 가이드라인을 제공합니다.

**상세 사용법**: [confluence-mdx/README.md](/confluence-mdx/README.md)를 반드시 참조하세요.

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

### 빠른 시작

```bash
cd confluence-mdx
source venv/bin/activate

# 1. Confluence 데이터 수집
python bin/pages_of_confluence.py --attachments

# 2. 제목 번역
python bin/translate_titles.py

# 3. 변환 스크립트 생성
python bin/generate_commands_for_xhtml2markdown.py var/list.en.txt >bin/xhtml2markdown.ko.sh

# 4. XHTML을 MDX로 변환
./bin/xhtml2markdown.ko.sh
```

### 변환 단계

1. **데이터 수집** (`pages_of_confluence.py`): Confluence API에서 페이지 다운로드
2. **제목 번역** (`translate_titles.py`): 한국어 제목을 영어로 번역
3. **명령어 생성** (`generate_commands_for_xhtml2markdown.py`): 변환 스크립트 생성
4. **변환 실행** (`xhtml2markdown.ko.sh`): XHTML을 MDX로 변환

## 일반적인 작업

### 특정 페이지만 업데이트

```bash
# 특정 페이지와 하위 페이지 다운로드
python bin/pages_of_confluence.py --page-id <page_id> --attachments

# 단일 파일 수동 변환
python bin/converter/cli.py var/<page_id>/page.xhtml target/ko/path/to/page.mdx
```

### 번역 문제 처리

제목이 번역되지 않은 경우:
1. `etc/korean-titles-translations.txt`에 번역 추가
2. `translate_titles.py` 재실행

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
3. **점진적 업데이트**: `--page-id`로 특정 페이지만 업데이트

## 상세 문서

다음 문서에서 상세한 사용법을 확인하세요:

- **전체 사용법**: [confluence-mdx/README.md](/confluence-mdx/README.md)
- **Container 환경 설계**: [confluence-mdx/CONTAINER_DESIGN.md](/confluence-mdx/CONTAINER_DESIGN.md)

