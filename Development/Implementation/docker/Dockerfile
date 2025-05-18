# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
# DECISION-REF: DEC-002-005 - Use Docker for development environment

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:$PYTHONPATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/models

# Default command
CMD ["bash"]