# Docker 환경에서 Confluence-MDX 실행하기

## 개요

이 문서는 Python 스크립트들을 Docker 컨테이너 환경에서 실행하는 방법을 설명합니다.

## 파일 구조

```
confluence-mdx/
├── Dockerfile              # Docker 이미지 빌드 설정
├── compose.yml             # Docker Compose 설정
├── requirements.txt        # Python 의존성
├── bin/                    # Python 스크립트들
├── etc/                    # 번역 파일들
└── var/                    # 데이터 저장소 (볼륨으로 마운트)
```

## Docker 이미지 빌드

```bash
# confluence-mdx 디렉토리로 이동
cd confluence-mdx

# Docker 이미지 빌드
docker build -t confluence-mdx .
```

## Docker Compose를 사용한 실행

### 1. 기본 실행 (볼륨 사용)

```bash
# 컨테이너 시작
docker compose up -d

# 컨테이너 내부에서 스크립트 실행
docker compose exec confluence-mdx python bin/pages_of_confluence.py --help
```

## var 디렉토리 데이터 복사 방법

로컬에서 Docker 볼륨으로 데이터 파일을 복사합니다.
```bash
# 1. 컨테이너 시작
docker compose up -d

# 2. 로컬 ./var 데이터를 볼륨(/app/var)으로 복사 (권한/심볼릭링크 보존)
# macOS/Windows에서도 안전하게 동작
tar -C ./var -czf - . | docker compose exec -T confluence-mdx sh -c "tar -C /app/var -xzf -"

# 3. 컨테이너 내에서 확인
docker compose exec confluence-mdx ls -la /app/var
```

## Python 스크립트 실행 예제

### 1. Confluence 데이터 수집

```bash
# 컨테이너 내부에서 실행
docker compose exec confluence-mdx python bin/pages_of_confluence.py --local > var/list.txt

# 또는 직접 실행
docker compose exec confluence-mdx python bin/pages_of_confluence.py --email your-email --api-token your-token
```

### 2. 제목 번역

```bash
docker compose exec confluence-mdx python bin/translate_titles.py
```

### 3. 변환 명령어 생성

```bash
docker compose exec confluence-mdx python bin/generate_commands_for_xhtml2markdown.py var/list.en.txt > bin/xhtml2markdown.ko.sh
```

### 4. XHTML을 Markdown으로 변환

```bash
docker compose exec confluence-mdx chmod +x bin/xhtml2markdown.ko.sh
docker compose exec confluence-mdx ./bin/xhtml2markdown.ko.sh
```

## 환경 변수 설정

Confluence API 인증 정보를 환경 변수로 설정:

```bash
# .env 파일 생성
echo "CONFLUENCE_EMAIL=your-email@example.com" > .env
echo "CONFLUENCE_API_TOKEN=your-api-token" >> .env

# Docker Compose 실행
docker compose up -d
```

## 볼륨 관리

### 볼륨 목록 확인

```bash
docker volume ls
```

### 볼륨 상세 정보 확인

```bash
docker volume inspect confluence-var-data
```

### 볼륨 삭제

```bash
# 컨테이너 중지 및 삭제
docker compose down

# 볼륨 삭제 (주의: 데이터가 영구 삭제됩니다)
docker volume rm confluence-var-data
```

## 문제 해결

### 컨테이너 로그 확인

```bash
docker compose logs confluence-mdx
```

### 컨테이너 내부 접속

```bash
docker compose exec confluence-mdx bash
```

### 권한 문제 해결

```bash
# 컨테이너 내부에서 실행
docker compose exec confluence-mdx chmod +x bin/*.py
```
