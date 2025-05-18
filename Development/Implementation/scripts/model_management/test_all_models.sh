#!/bin/bash
# scripts/test_all_models.sh
# TASK-REF: ENV_003 - Model Preparation
# CONCEPT-REF: CON-IMP-012 - Model Preparation
# CONCEPT-REF: CON-IMP-014 - Validation Criteria
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
# DECISION-REF: DEC-004-004 - Create detailed implementation planning before coding

set -e

echo "Testing all models for VANTA development..."

# Load models from registry
REGISTRY_FILE="models/registry/registry.json"
if [ ! -f "$REGISTRY_FILE" ]; then
    echo "Error: Registry file not found. Run setup_all_models.sh first."
    exit 1
fi

# Test each model
MODEL_IDS=$(python -c "import json; f=open('$REGISTRY_FILE'); data=json.load(f); print(' '.join([m['id'] for m in data['models']]))")

for MODEL_ID in $MODEL_IDS; do
    echo "Testing model $MODEL_ID..."
    python scripts/model_manager.py test "$MODEL_ID"
    echo "----------------------------------------"
done

echo "Model testing complete."