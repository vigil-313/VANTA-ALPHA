#!/bin/bash
# scripts/setup_all_models.sh
# TASK-REF: ENV_003 - Model Preparation
# CONCEPT-REF: CON-IMP-012 - Model Preparation
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
# DECISION-REF: DEC-004-004 - Create detailed implementation planning before coding

set -e

echo "Setting up all models for VANTA development..."

# Create the models directory structure
mkdir -p models/whisper
mkdir -p models/llm
mkdir -p models/embeddings
mkdir -p models/tts
mkdir -p models/registry

# Create registry if it doesn't exist
if [ ! -f models/registry/registry.json ]; then
    echo '{"models": []}' > models/registry/registry.json
fi

# Ensure dependencies are installed
pip install sentence-transformers huggingface_hub openai-whisper tabulate

# Download Whisper model
echo "Setting up Whisper models..."
python scripts/setup_whisper_models.py --models base

# Download LLM model
echo "Setting up LLM models..."
python scripts/setup_llm_models.py --models mistral-7b

# Download embedding model
echo "Setting up embedding models..."
python scripts/setup_embedding_models.py --models all-MiniLM-L6-v2

# Set up TTS models
echo "Setting up TTS models..."
python scripts/setup_tts_models.py --models tts-1

echo "Model setup complete."
echo "You can use scripts/model_manager.py to manage and test models."

# List all models
python scripts/model_manager.py list