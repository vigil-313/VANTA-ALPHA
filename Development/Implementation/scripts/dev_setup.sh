#!/bin/bash
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

# Initial setup script for development environment

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.template .env
    echo "Created .env file from template. Please edit it with your API keys."
fi

# Create necessary directories
mkdir -p data/chromadb logs models

# Build Docker images
cd docker && docker-compose build

echo "Development environment setup complete."
echo "To start the environment, run: ./scripts/dev_start.sh"