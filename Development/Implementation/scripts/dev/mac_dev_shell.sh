#!/bin/bash
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# CONCEPT-REF: CON-HVA-003 - Hardware Optimization
# DECISION-REF: DEC-004-002 - Target M4 MacBook Pro as reference hardware

# Run the container with necessary volume mounts
docker run -it --rm \
  -v "$(pwd):/app" \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/models:/app/models" \
  -p 8000:8000 \
  -p 8501:8501 \
  --env-file .env \
  vanta-dev bash