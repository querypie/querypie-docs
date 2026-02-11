# Plan: 변환 파이프라인 단순화

## 배경

현재 Confluence 문서를 MDX로 변환하려면 4개 명령을 순차 실행해야 합니다:

```bash
fetch_cli.py --recent                   # 1. 데이터 수집
translate_titles.py                      # 2. 제목 번역
generate_commands_for_xhtml2markdown.py var/list.en.txt > bin/generated/xhtml2markdown.ko.sh  # 3. 명령 생성
bash bin/generated/xhtml2markdown.ko.sh  # 4. 변환 실행
```

그런데 `fetch_cli.py`가 생성하는 `pages.yaml`에는 이미 영어 breadcrumbs(`breadcrumbs_en`)와
slugified path(`path`)가 포함되어 있습니다. 2~4단계는 이 정보를 텍스트 파일과 셸 스크립트로
다시 변환하는 중복 작업입니다.

## 목표

사용자가 실행해야 하는 명령을 2개로 줄입니다:

```bash
fetch_cli.py --recent    # 1. 데이터 수집
convert_all.py           # 2. 전체 변환 (pages.yaml 기반)
```

## 요구사항

### R1. `convert_all.py` — pages.yaml 기반 일괄 변환

- `var/pages.yaml`을 읽어 각 페이지의 출력 경로를 결정합니다 (`path` 필드 사용).
- 각 페이지에 대해 `converter/cli.py`의 변환 로직을 호출합니다.
- `translate_titles.py`, `generate_commands_for_xhtml2markdown.py`, `xhtml2markdown.ko.sh`를 대체합니다.
- 진행 상황을 stderr로 출력합니다 (예: `[42/290] 544375859 → target/ko/overview/system-architecture.mdx`).

### R2. 디버깅용 목록 파일 생성 (`--generate-list`)

- `convert_all.py --generate-list` 옵션으로 기존 `list.txt` / `list.en.txt`를 선택적으로 생성합니다.
- 기본 실행 시에는 생성하지 않습니다 (변환만 수행).
- 디버깅, 수동 검증 등 필요한 경우에만 사용합니다.

### R3. 번역 검증 (`--verify-translations`)

- `convert_all.py --verify-translations` 또는 별도 서브커맨드로, 변환 전에 번역 누락을 검출합니다.
- `pages.yaml`의 모든 한국어 제목을 `etc/korean-titles-translations.txt`와 대조합니다.
- 누락된 번역이 있으면 목록을 출력하고 비정상 종료합니다 (exit code 1).
- 모두 커버되면 통과 메시지를 출력합니다.
- `convert_all.py` 실행 시에도 변환 전 자동으로 검증을 수행합니다.

### R4. 불필요한 도구 삭제

- `translate_titles.py`, `generate_commands_for_xhtml2markdown.py`, `bin/generated/` 디렉토리를 삭제합니다.
- `converter/cli.py`는 단일 파일 변환 도구로 유지합니다 (인터페이스 변경 없음).

### R5. `entrypoint.sh` / `Dockerfile` 업데이트

- `full` 워크플로우: `fetch_cli.py` → `convert_all.py` 2단계로 변경합니다.
- `convert_all.py`를 컨테이너 명령으로 추가합니다.

### R6. 문서 업데이트

- `README.md`: 단순화된 사용법 반영.
