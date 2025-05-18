#!/bin/bash
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment

# Stop the development environment
cd docker && docker-compose down
echo "Development environment stopped."