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

# Copy cache/ data (included in image)
COPY cache/ ./cache/

# Populate var/ directory by running pages_of_confluence.py --remote --attachments
RUN python3 bin/pages_of_confluence.py --remote --attachments

# Create target/ directory
RUN mkdir -p target/ko target/en target/ja target/public

# Set entrypoint
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["help"]

