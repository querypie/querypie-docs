# Confluence-MDX Container Image
# Use Python 3.12 based image
# Platform: linux/amd64
# Build with: docker build --platform linux/amd64 -t <image-name> .
FROM python:3.12-slim

# Set working directory
WORKDIR /workdir

# Update system packages and install essential tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY bin/ ./bin/
RUN chmod +x bin/*.py bin/*.sh
COPY etc/ ./etc/
COPY tests/ ./tests/

# Restore var/ from previous image cache (baseline for --recent mode)
COPY cache/ ./var/

# Update var/ with recently modified pages only
RUN python3 bin/fetch_cli.py --recent --attachments

# Create target/ directory
RUN mkdir -p target/ko target/en target/ja target/public

# Set entrypoint
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["help"]

