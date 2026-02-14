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
python3 bin/fetch_cli.py --recent --attachments

# 2. pages.yaml 기준으로 전체 변환
python3 bin/convert_all.py
```

### 변환 단계

1. **데이터 수집** (`fetch_cli.py`): Confluence API 또는 로컬 데이터에서 `var/` 갱신
2. **전체 변환** (`convert_all.py`): `var/pages.yaml` 기반으로 `target/ko` 및 `target/public`에 반영

## 일반적인 작업

### 특정 페이지만 업데이트

```bash
# 특정 페이지를 루트로 하위 트리 다운로드
python3 bin/fetch_cli.py --remote --start-page-id <page_id> --attachments

# 단일 파일 수동 변환
python3 bin/converter/cli.py var/<page_id>/page.xhtml target/ko/path/to/page.mdx
```

### 번역 문제 처리

제목이 번역되지 않은 경우:
1. `etc/korean-titles-translations.txt`에 번역 추가
2. `python3 bin/convert_all.py --verify-translations`로 누락 여부 확인
3. `python3 bin/convert_all.py` 재실행

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
3. **점진적 업데이트**: `--start-page-id`로 특정 하위 트리만 업데이트

## 상세 문서

다음 문서에서 상세한 사용법을 확인하세요:

- **전체 사용법**: [confluence-mdx/README.md](/confluence-mdx/README.md)
- **Container 환경 설계**: [confluence-mdx/CONTAINER_DESIGN.md](/confluence-mdx/CONTAINER_DESIGN.md)
