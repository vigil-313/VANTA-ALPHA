#!/bin/bash
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

# Install the vanta package in development mode inside the Docker container

cd /app && pip install -e .
echo "Installed vanta package in development mode"