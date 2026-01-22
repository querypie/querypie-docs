# Confluence에서 MDX로 변환 가이드라인

## 개요

이 skill은 QueryPie 문서 저장소에서 Confluence에서 MDX로 변환하는 워크플로우에 대한 가이드라인을 제공합니다.

## 프로젝트 컨텍스트

- **변환 스크립트**: `confluence-mdx/bin/`에 위치
- **Python 환경**: 가상 환경을 사용하는 Python 3
- **입력 형식**: Confluence XHTML 내보내기
- **출력 형식**: `src/content/{lang}/`의 MDX 파일
- **워크플로우**: Confluence에서 최종 MDX까지 다단계 프로세스

## 디렉토리 구조

```
confluence-mdx/
├── bin/                    # 변환 스크립트
│   ├── pages_of_confluence.py
│   ├── translate_titles.py
│   ├── generate_commands_for_xhtml2markdown.py
│   ├── confluence_xhtml_to_markdown.py
│   └── xhtml2markdown.ko.sh
├── var/                    # Confluence 데이터용 작업 디렉토리
│   ├── list.txt           # 페이지 목록 (한국어 제목)
│   ├── list.en.txt        # 페이지 목록 (영어 제목)
│   └── {page_id}/         # 페이지별 데이터
│       ├── page.yaml      # 페이지 메타데이터
│       └── page.xhtml     # 페이지 콘텐츠
├── etc/                    # 설정 및 번역 파일
│   └── korean-titles-translations.txt
├── target/                 # 출력 디렉토리
│   ├── en/
│   ├── ja/
│   ├── ko/
│   └── public/            # 공용 자산
└── tests/                  # 테스트 케이스
    └── testcases/
```

## 변환 워크플로우

### 1단계: Confluence 데이터 수집

**스크립트**: `pages_of_confluence.py`

**목적**: Confluence API에서 페이지와 메타데이터 다운로드

**사용법**:
```bash
cd confluence-mdx
source venv/bin/activate

# 첨부파일 포함 전체 다운로드 (처음 또는 첨부파일 변경 시)
python bin/pages_of_confluence.py --attachments

# 일반 업데이트 (페이지만)
python bin/pages_of_confluence.py

# 특정 페이지와 하위 페이지 업데이트
python bin/pages_of_confluence.py --page-id 123456789 --attachments

# 로컬 데이터에서 list.txt 생성/업데이트
python bin/pages_of_confluence.py --local >var/list.txt
```

**출력**:
- `var/list.txt`: 탭으로 구분된 페이지 목록 (ID, 경로, 제목)
- `var/{page_id}/page.yaml`: 페이지 메타데이터
- `var/{page_id}/page.xhtml`: XHTML 형식의 페이지 콘텐츠
- `var/{page_id}/attachments/`: 다운로드된 첨부파일 (`--attachments` 사용 시)

### 2단계: 제목 번역

**스크립트**: `translate_titles.py`

**목적**: 한국어 페이지 제목을 영어로 번역

**사용법**:
```bash
python bin/translate_titles.py
```

**입력**: `var/list.txt` (한국어 제목)
**출력**: `var/list.en.txt` (영어 제목)
**번역 소스**: `etc/korean-titles-translations.txt`

**참고**: 제목이 번역되지 않으면 `etc/korean-titles-translations.txt`를 업데이트하세요.

### 3단계: 변환 명령어 생성

**스크립트**: `generate_commands_for_xhtml2markdown.py`

**목적**: 변환 명령어가 포함된 셸 스크립트 생성

**사용법**:
```bash
python bin/generate_commands_for_xhtml2markdown.py var/list.en.txt >bin/xhtml2markdown.ko.sh
chmod +x bin/xhtml2markdown.ko.sh
```

**출력**: `bin/xhtml2markdown.ko.sh` - 변환 명령어가 포함된 실행 가능한 스크립트

### 4단계: XHTML을 MDX로 변환

**스크립트**: `xhtml2markdown.ko.sh` (3단계에서 생성됨)

**목적**: 모든 XHTML 파일을 MDX로 변환 실행

**사용법**:
```bash
./bin/xhtml2markdown.ko.sh
```

**프로세스**:
- 각 페이지에 대해 `confluence_xhtml_to_markdown.py` 호출
- XHTML을 Markdown/MDX 형식으로 변환
- 특수 케이스 처리: 코드 블록, 테이블, 매크로 등

**출력**:
- `target/ko/`: 한국어 콘텐츠용 MDX 파일
- `target/public/`: 공용 자산 (이미지, 첨부파일)

## 핵심 변환 스크립트

### confluence_xhtml_to_markdown.py

**목적**: 개별 XHTML 파일을 Markdown/MDX로 변환

**사용법**:
```bash
python bin/confluence_xhtml_to_markdown.py input.xhtml output.mdx
```

**기능**:
- 코드 블록의 CDATA 섹션 처리
- colspan/rowspan이 있는 테이블 변환
- Confluence 전용 매크로 처리
- 구조 및 포맷팅 보존

## 테스트

### 테스트 프레임워크

**위치**: `confluence-mdx/tests/`

**테스트 케이스**: `tests/testcases/`
- 각 테스트 케이스에 포함:
  - `page.xhtml`: 입력 XHTML
  - `expected.mdx`: 예상 출력
  - `output.mdx`: 생성된 출력 (테스트 중 생성)

### 테스트 실행

```bash
cd confluence-mdx/tests

# 모든 테스트 실행
make test

# 특정 테스트 실행
make test-one TEST_ID=<test_id>

# 디버그 로깅과 함께 실행
make debug

# 출력 파일 정리
make clean
```

## 일반적인 작업

### Confluence에서 새 페이지 추가

1. 새 페이지 다운로드:
   ```bash
   python bin/pages_of_confluence.py --page-id <new_page_id> --attachments
   ```

2. 목록 업데이트:
   ```bash
   python bin/pages_of_confluence.py --local >var/list.txt
   ```

3. 제목 번역:
   ```bash
   python bin/translate_titles.py
   ```

4. 변환 스크립트 재생성:
   ```bash
   python bin/generate_commands_for_xhtml2markdown.py var/list.en.txt >bin/xhtml2markdown.ko.sh
   ```

5. 변환:
   ```bash
   ./bin/xhtml2markdown.ko.sh
   ```

### 기존 페이지 업데이트

1. 업데이트된 페이지 다운로드:
   ```bash
   python bin/pages_of_confluence.py --page-id <page_id>
   ```

2. 변경된 페이지만 변환:
   ```bash
   # 특정 페이지 수동 변환
   python bin/confluence_xhtml_to_markdown.py \
     var/{page_id}/page.xhtml \
     target/ko/path/to/page.mdx
   ```

### 번역 문제 처리

제목이 제대로 번역되지 않은 경우:

1. `etc/korean-titles-translations.txt` 확인
2. 다음 형식으로 누락된 번역 추가:
   ```
   한국어 제목<TAB>영어 제목
   ```
3. `translate_titles.py` 재실행

## Python 환경 설정

### 초기 설정

```bash
cd confluence-mdx
python3 -m venv venv
source venv/bin/activate
pip install requests beautifulsoup4 pyyaml
```

### 환경 활성화

```bash
cd confluence-mdx
source venv/bin/activate
```

### 환경 비활성화

```bash
deactivate
```

## 모범 사례

1. **변환 전 백업**: 변환 실행 전 기존 MDX 파일 항상 백업
2. **로컬 테스트**: 커밋 전 `npm run dev`로 변환된 파일 테스트
3. **변경 사항 검토**: 변환된 콘텐츠 수동 검토, 특히:
   - 코드 블록
   - 테이블
   - 이미지 및 링크
   - 특수 포맷팅
4. **점진적 업데이트**: 전체 변환 대신 `--page-id`로 특정 페이지 업데이트
5. **첨부파일 처리**: 첨부파일이 업데이트된 경우 `--attachments` 플래그 사용
6. **버전 관리**: 추적을 위해 `var/list.txt`와 `var/list.en.txt` 커밋
7. **번역 유지 관리**: `korean-titles-translations.txt` 최신 상태 유지

## 문제 해결

### 일반적인 문제

1. **누락된 번역**: `etc/korean-titles-translations.txt` 업데이트
2. **깨진 링크**: 변환 후 이미지 경로 및 내부 링크 확인
3. **포맷팅 문제**: `confluence_xhtml_to_markdown.py`의 특수 케이스 검토
4. **API 오류**: Confluence API 자격 증명 및 속도 제한 확인
5. **테스트 실패**: 문제 파악을 위해 `output.mdx`와 `expected.mdx` 비교

### 디버그 모드

디버그 로깅 활성화:
```bash
python bin/confluence_xhtml_to_markdown.py input.xhtml output.mdx --log-level debug
```

## 문서 워크플로우와의 통합

변환 후:

1. `target/ko/`의 변환된 MDX 파일 검토
2. 필요시 `src/content/ko/`로 복사
3. 로컬 개발 서버로 테스트: `npm run dev`
4. 필요시 수동 조정
5. 구조가 변경된 경우 다른 언어 버전 (en, ja) 업데이트

## 참고사항

- 변환은 주로 한국어 (ko) 콘텐츠용
- 영어 및 일본어 버전은 별도 워크플로우가 필요할 수 있음
- 변환 후 수동 편집이 종종 필요
- 테스트 케이스가 변환 품질을 보장하는 데 도움

