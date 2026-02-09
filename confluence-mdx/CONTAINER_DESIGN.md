# Confluence-MDX Container 설계 및 계획

## 1. 개요

이 문서는 `confluence-mdx` 프로젝트를 Containerize하기 위한 설계와 계획을 설명합니다.

### 목표
- Python venv 설치 과정을 Container 이미지로 대체
- `var/` 디렉토리의 데이터를 컨테이너 내부에 저장
- 이미지를 빌드하여 다른 컴퓨터에서 재사용 가능하도록 구성

## 2. 현재 프로젝트 구조 분석

### 2.1 의존성
- Python 3.9.6 (venv 기준)
- 필수 Python 패키지:
  - `requests`: Confluence API 호출
  - `beautifulsoup4`: HTML/XHTML 파싱
  - `pyyaml`: YAML 파일 처리
  - `emoji` (선택사항): 이모지 처리

### 2.2 주요 디렉토리 구조
```
confluence-mdx/
├── bin/                    # 실행 스크립트들
│   ├── pages_of_confluence.py
│   ├── translate_titles.py
│   ├── generate_commands_for_xhtml2markdown.py
│   ├── converter/
│   │   └── cli.py
│   └── generated/
│       └── xhtml2markdown.ko.sh
├── var/                    # 입력 데이터 (컨테이너 내부 저장)
│   ├── list.txt
│   ├── list.en.txt
│   ├── pages.yaml
│   └── <page_id>/         # 각 페이지별 디렉토리
│       ├── page.xhtml
│       ├── page.yaml
│       └── attachments/
├── target/                 # 출력 디렉토리
│   ├── ko/
│   ├── en/
│   ├── ja/
│   └── public/
├── etc/                    # 설정 파일
│   └── korean-titles-translations.txt
└── tests/                  # 테스트 파일
```

### 2.3 주요 워크플로우
1. **데이터 수집**: `pages_of_confluence.py` → `var/`에 저장
2. **제목 번역**: `translate_titles.py` → `var/list.en.txt` 생성
3. **명령어 생성**: `generate_commands_for_xhtml2markdown.py` → `bin/generated/xhtml2markdown.ko.sh` 생성
4. **변환 실행**: `xhtml2markdown.ko.sh` → `target/`에 MDX 파일 생성

## 3. Container 설계

### 3.1 이미지 구조

#### Base Image
- `python:3.12-slim`: 경량화된 Python 3.12 이미지 사용

#### 레이어 구성
1. **Base Layer**: Python 3.12 설치
2. **Dependencies Layer**: Python 패키지 설치
3. **Application Layer**: 스크립트 및 설정 파일 복사
4. **Data Layer**: `var/` 디렉토리 데이터 포함

### 3.2 데이터 관리 전략

#### 옵션 A: 이미지에 포함 (권장)
- **장점**: 
  - 완전한 이식성 (다른 컴퓨터에서 바로 사용 가능)
  - 버전 관리 용이 (이미지 태그로 관리)
- **단점**:
  - 이미지 크기 증가
  - 데이터 업데이트 시 이미지 재빌드 필요

#### 옵션 B: Volume 마운트
- **장점**:
  - 이미지 크기 작음
  - 데이터 업데이트 용이
- **단점**:
  - 다른 컴퓨터에서 사용 시 데이터 별도 관리 필요
  - 이식성 저하

**선택: 옵션 A (이미지에 포함)**
- 사용자 요구사항에 따라 `var/` 데이터를 컨테이너 내부에 저장

### 3.3 디렉토리 구조 (컨테이너 내부)

```
/workdir/
├── bin/                    # 실행 스크립트
├── var/                    # 입력 데이터 (이미지에 포함)
├── target/                 # 출력 디렉토리 (볼륨 마운트 가능)
├── etc/                    # 설정 파일
└── tests/                  # 테스트 파일
```

### 3.4 실행 모드

#### 모드 1: 전체 워크플로우 실행
```bash
docker run docker.io/querypie/confluence-mdx:latest full
```

#### 모드 2: 개별 스크립트 실행
```bash
# 데이터 수집
docker run docker.io/querypie/confluence-mdx:latest pages_of_confluence.py --attachments

# 제목 번역
docker run docker.io/querypie/confluence-mdx:latest translate_titles.py

# 명령어 생성
docker run docker.io/querypie/confluence-mdx:latest generate_commands var/list.en.txt

# 변환 실행
docker run docker.io/querypie/confluence-mdx:latest convert
```

#### 모드 3: 대화형 실행
```bash
docker run -it docker.io/querypie/confluence-mdx:latest bash
```

## 4. 구현 계획

### 4.1 파일 구조

```
confluence-mdx/
├── Dockerfile
├── .dockerignore (또는 .containerignore)
├── requirements.txt
├── compose.yml (선택사항)
└── scripts/
    └── entrypoint.sh
```

### 4.2 Dockerfile 설계

```dockerfile
# Multi-stage build 고려 (필요시)
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /workdir

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY bin/ ./bin/
COPY etc/ ./etc/
COPY tests/ ./tests/

# var/ 데이터 복사 (이미지에 포함)
COPY var/ ./var/

# target/ 디렉토리 생성
RUN mkdir -p target/ko target/en target/ja target/public

# 실행 권한 부여
RUN chmod +x bin/*.py bin/*.sh

# Entrypoint 설정
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# 기본 명령어
CMD ["help"]
```

### 4.3 requirements.txt

```
requests>=2.31.0
beautifulsoup4>=4.12.0
pyyaml>=6.0
emoji>=2.8.0
```

### 4.4 .dockerignore (또는 .containerignore)

```
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/
.git/
.gitignore
*.log
target/
```

### 4.5 entrypoint.sh 설계

```bash
#!/bin/bash
set -e

case "$1" in
  pages_of_confluence.py|translate_titles.py|generate_commands_for_xhtml2markdown.py|converter/cli.py)
    exec python "bin/$@"
    ;;
  generate_commands)
    shift
    python bin/generate_commands_for_xhtml2markdown.py "$@"
    ;;
  convert)
    exec bash bin/generated/xhtml2markdown.ko.sh
    ;;
  full)
    # 전체 워크플로우 실행
    python bin/pages_of_confluence.py --attachments || true
    python bin/translate_titles.py
    python bin/generate_commands_for_xhtml2markdown.py var/list.en.txt > bin/generated/xhtml2markdown.ko.sh
    chmod +x bin/generated/xhtml2markdown.ko.sh
    bash bin/generated/xhtml2markdown.ko.sh
    ;;
  bash|sh)
    exec "$@"
    ;;
  help|--help|-h)
    cat << EOF
Confluence-MDX Container

Usage:
  docker run <image> <command> [args...]

Commands:
  pages_of_confluence.py [args...]  - Confluence 데이터 수집
  translate_titles.py               - 제목 번역
  generate_commands <list_file>     - 변환 명령어 생성
  convert                           - XHTML을 MDX로 변환
  full                              - 전체 워크플로우 실행
  bash                              - 대화형 쉘 실행
  help                              - 이 도움말 표시

Examples:
  docker run docker.io/querypie/confluence-mdx:latest pages_of_confluence.py --attachments
  docker run docker.io/querypie/confluence-mdx:latest translate_titles.py
  docker run docker.io/querypie/confluence-mdx:latest generate_commands var/list.en.txt
  docker run docker.io/querypie/confluence-mdx:latest convert
  docker run -v \$(pwd)/target:/workdir/target docker.io/querypie/confluence-mdx:latest convert
EOF
    ;;
  *)
    exec "$@"
    ;;
esac
```

## 5. 빌드 및 사용 방법

### 5.1 이미지 빌드

```bash
cd confluence-mdx
docker build -t docker.io/querypie/confluence-mdx:latest .
```

### 5.2 이미지 태그 및 푸시

```bash
# Container Registry에 푸시
docker push docker.io/querypie/confluence-mdx:latest

# 또는 Private Registry에 푸시
docker tag docker.io/querypie/confluence-mdx:latest <registry>/confluence-mdx:latest
docker push <registry>/confluence-mdx:latest
```

### 5.3 다른 컴퓨터에서 사용

```bash
# 이미지 다운로드
docker pull docker.io/querypie/confluence-mdx:latest

# 실행 (출력은 볼륨으로 마운트)
docker run -v $(pwd)/output:/workdir/target \
  docker.io/querypie/confluence-mdx:latest convert
```

## 6. 고려사항

### 6.1 이미지 크기
- `var/` 디렉토리가 크면 이미지 크기가 증가할 수 있음
- 필요시 `.dockerignore` 또는 `.containerignore`에서 불필요한 파일 제외
- Multi-stage build로 최적화 가능

### 6.2 데이터 업데이트
- `var/` 데이터 업데이트 시 이미지 재빌드 필요
- 버전 태그 사용 권장: `docker.io/querypie/confluence-mdx:v1.0.0`, `docker.io/querypie/confluence-mdx:v1.1.0`

### 6.3 출력 데이터 관리
- `target/` 디렉토리는 볼륨 마운트 권장
- 컨테이너 삭제 시 출력 데이터 보존

### 6.4 환경 변수
- Confluence API 인증 정보는 환경 변수로 전달:
  ```bash
  docker run -e ATLASSIAN_USERNAME=user@example.com \
             -e ATLASSIAN_API_TOKEN=token \
             docker.io/querypie/confluence-mdx:latest pages_of_confluence.py
  ```

## 7. 향후 개선 사항

1. **Multi-stage build**: 빌드 도구와 런타임 분리
2. **Health check**: 컨테이너 상태 확인
3. **compose.yml**: 복잡한 워크플로우 자동화
4. **CI/CD 통합**: 자동 빌드 및 푸시
5. **데이터 버전 관리**: var/ 데이터를 별도 레이어로 분리하여 캐싱 최적화

## 8. 마이그레이션 체크리스트

- [ ] `requirements.txt` 생성
- [ ] `Dockerfile` 작성
- [ ] `.dockerignore` (또는 `.containerignore`) 작성
- [ ] `entrypoint.sh` 작성
- [ ] 이미지 빌드 테스트
- [ ] 각 스크립트 실행 테스트
- [ ] `var/` 데이터 포함 확인
- [ ] 이미지 크기 확인 및 최적화
- [ ] 다른 컴퓨터에서 테스트
- [ ] 문서화 업데이트

