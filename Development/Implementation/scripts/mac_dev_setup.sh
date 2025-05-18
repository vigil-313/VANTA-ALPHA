#!/bin/bash
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# CONCEPT-REF: CON-HVA-003 - Hardware Optimization
# DECISION-REF: DEC-004-002 - Target M4 MacBook Pro as reference hardware

# Initial setup script for Mac development environment

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.template .env
    echo "Created .env file from template. Please edit it with your API keys."
fi

# Create necessary directories
mkdir -p data/chromadb logs models

# Build using Mac-specific Dockerfile
docker build -f docker/Dockerfile.mac -t vanta-dev .

echo "Development environment setup complete."
echo "To start a shell in the container, run: ./scripts/mac_dev_shell.sh"