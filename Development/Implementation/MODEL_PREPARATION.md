# VANTA Model Preparation Guide

<!-- 
TASK-REF: ENV_003 - Model Preparation
CONCEPT-REF: CON-IMP-012 - Model Preparation
DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
DECISION-REF: DEC-007-003 - Proceed with implementation of Phase 0 (Setup) tasks
-->

This document provides guidance on managing machine learning models for the VANTA system. VANTA uses various models for speech recognition, language understanding, semantic memory, and text-to-speech functionality.

## Overview

The model preparation system consists of:

1. A structured model directory
2. A registry for tracking model metadata
3. Scripts for downloading and preparing models
4. Tools for managing and testing models

## Model Types

VANTA uses the following types of models:

- **Whisper Models**: Speech-to-text conversion (STT)
- **LLM Models**: Local language models for the dual-track processing system
- **Embedding Models**: For semantic memory and retrieval
- **TTS Models**: Text-to-speech synthesis

## Directory Structure

```
models/
├── whisper/         # Speech-to-text models
├── llm/             # Local language models
├── embeddings/      # Embedding models for memory
├── tts/             # Text-to-speech models
└── registry/        # Model registry files
    ├── registry.json  # Current model registry
    └── schema.json    # JSON schema for registry
```

## Model Registry

The model registry (`models/registry/registry.json`) tracks all models in a standardized format. Each model entry includes:

- ID and name
- Type (whisper, llm, embedding, tts)
- Version
- File path
- Size and format
- Quantization information (if applicable)
- Date added
- Hash (for integrity verification)
- Parameters (model-specific information)
- Hardware requirements
- Metadata

## Setup Instructions

### Prerequisites

- Docker environment set up using VANTA's Docker setup
- Python 3.8+ with pip
- Internet connection for downloading models
- Sufficient disk space (approx 10GB for base models)

### Setting Up All Models

The easiest way to set up all required models is to use the master setup script:

```bash
cd Development/Implementation
./scripts/setup_all_models.sh
```

This will:
1. Create the necessary directory structure
2. Install required Python dependencies
3. Download and prepare all default models
4. Update the model registry

### Setting Up Individual Model Types

If you prefer to set up models individually:

#### Whisper (STT) Models

```bash
# Available models: tiny, base, small, medium
python scripts/setup_whisper_models.py --models base
```

#### LLM Models

```bash
# Available models: mistral-7b, phi-2, llama2-7b
python scripts/setup_llm_models.py --models mistral-7b
```

#### Embedding Models

```bash
# Available models: all-MiniLM-L6-v2, all-mpnet-base-v2
python scripts/setup_embedding_models.py --models all-MiniLM-L6-v2
```

#### TTS Models

```bash
# Available models: tts-1, coqui-XTTS-v2
python scripts/setup_tts_models.py --models tts-1
```

## Model Management

The `model_manager.py` script provides tools for managing models:

### Listing Models

```bash
# List all models
python scripts/model_manager.py list

# List models of a specific type
python scripts/model_manager.py list --type whisper
```

### Verifying Models

```bash
# Verify a specific model
python scripts/model_manager.py verify whisper-base
```

### Testing Models

```bash
# Test a specific model
python scripts/model_manager.py test whisper-base

# Test all models
./scripts/test_all_models.sh
```

## Models and Hardware Optimization

VANTA models are selected and configured for optimal performance on the target hardware (M4 MacBook Pro). Key optimizations include:

1. **Whisper Models**: The "base" model offers a good balance of accuracy and speed for M4 hardware.
2. **LLM Models**: Quantized versions (Q4_K_M) of 7B parameter models, optimized for Metal acceleration.
3. **Embedding Models**: Lightweight models like all-MiniLM-L6-v2 provide fast embedding generation.
4. **TTS Models**: API-based models reduce local resource usage.

## Adding Custom Models

To add a custom model:

1. Place the model in the appropriate subdirectory under `models/`
2. Update the registry with the new model's information:
   ```bash
   # Example: Add an entry for a custom LLM
   # Use the appropriate setup script or manually edit registry.json
   ```

## Troubleshooting

### Common Issues

1. **Insufficient Disk Space**: Ensure you have at least 10GB available for all models.
2. **Download Failures**: Check internet connection and try again. Some models may require HuggingFace authentication.
3. **Memory Issues**: If models fail to load, ensure your hardware meets the minimum requirements for the specific model.

### Fixing Registry Issues

If the registry becomes corrupted or out of sync:

```bash
# Verify all models and update registry
for model_id in $(python scripts/model_manager.py list | awk 'NR>2 {print $1}'); do
  python scripts/model_manager.py verify $model_id
done
```

## Model Specifications

### Default Models

| Model Type | Default Model | Size | Parameters | Requirements |
|------------|---------------|------|------------|--------------|
| STT | whisper-base | ~150MB | 74M | 8GB RAM |
| LLM | mistral-7b | ~4.1GB | 7B | 16GB RAM, Metal |
| Embedding | all-MiniLM-L6-v2 | ~90MB | - | 4GB RAM |
| TTS | tts-1 (API) | - | - | API key |

## References

- [Whisper Documentation](https://github.com/openai/whisper)
- [Mistral AI](https://huggingface.co/mistralai)
- [Sentence Transformers](https://www.sbert.net/)
- [OpenAI TTS API](https://platform.openai.com/docs/guides/text-to-speech)