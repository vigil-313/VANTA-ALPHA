#!/bin/bash
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment

# Start the development environment

# Start Docker containers
cd docker && docker-compose up -d

# Print status
echo "Development environment started."
echo "To open a shell in the container, run: ./scripts/dev_shell.sh"