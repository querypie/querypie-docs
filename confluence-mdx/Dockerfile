# Confluence-MDX Container Image
# Use Python 3.12 based image
# Platform: linux/amd64
# Build with: docker build --platform linux/amd64 -t <image-name> .

# ── Stage 1: Builder ─────────────────────────────────
# cache 복원 + fetch를 수행하여 var/ 최종 상태를 생성
FROM python:3.12-slim AS builder
WORKDIR /workdir

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bin/ ./bin/
RUN chmod +x bin/*.py bin/*.sh
COPY etc/ ./etc/

# Restore cache at its expected path (for Stage 3 attachment fallback)
COPY cache/ ./cache/

# Populate var/ baseline from cache and fetch recent updates in one step.
# cp -a creates var/ with all cached YAML/content/attachment files,
# then fetch_cli.py downloads only recently modified pages.
RUN cp -a cache/. var/ && python3 bin/fetch_cli.py --recent --attachments

# ── Stage 2: Final image ────────────────────────────
FROM python:3.12-slim
WORKDIR /workdir

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bin/ ./bin/
RUN chmod +x bin/*.py bin/*.sh
COPY etc/ ./etc/
COPY tests/ ./tests/

# var/ 최종 상태를 단일 레이어로 복사 (builder의 cache+fetch 결과)
COPY --from=builder /workdir/var/ ./var/

# Create target/ directory
RUN mkdir -p target/ko target/en target/ja target/public

# Set entrypoint
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["help"]
