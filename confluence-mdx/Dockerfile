# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python scripts
COPY bin/ ./bin/

# Copy etc directory for translation files
COPY etc/ ./etc/

# Create var directory for data storage
RUN mkdir -p var

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Make Python scripts executable
RUN chmod +x bin/*.py

# Create a volume mount point for var directory
VOLUME ["/app/var"]

# Set default command
CMD ["python", "bin/pages_of_confluence.py", "--help"]
