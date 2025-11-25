# Confluence-MDX Container Image
# Use Python 3.9 based image
FROM python:3.9-slim

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
COPY etc/ ./etc/
COPY tests/ ./tests/

# Copy var/ data (included in image)
COPY var/ ./var/

# Create target/ directory
RUN mkdir -p target/ko target/en target/ja target/public

# Grant execute permissions
RUN chmod +x bin/*.py bin/*.sh 2>/dev/null || true

# Set entrypoint
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["help"]

