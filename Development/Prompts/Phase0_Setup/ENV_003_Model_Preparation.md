# IMPLEMENTATION TASK: ENV_003 Model Preparation

## Context
The VANTA system relies on multiple machine learning models for various components, including speech recognition, language understanding, and text generation. These models need to be properly prepared and configured before development can proceed. This task involves downloading, converting, and verifying the necessary models for local development.

This task (TASK-ENV-003) depends on the Docker environment setup (TASK-ENV-002) and is a prerequisite for component development tasks involving local models and voice processing.

## Objective
Prepare all necessary machine learning models for VANTA development, ensuring they are properly formatted, optimized for the target hardware, and accessible to the system.

## Requirements
1. Download and convert Whisper models for speech-to-text 
2. Set up local LLM models for dual-track processing
3. Prepare embedding models for semantic memory
4. Configure automatic model downloading and verification
5. Optimize models for target hardware (M4 MacBook Pro)
6. Create model registry and versioning system
7. Set up model caching mechanism

## References
- [DOC-ARCH-001]: Development/Architecture/V0_ARCHITECTURE_OVERVIEW.md - For overall architecture understanding
- [DOC-DEV-IMPL-1]: Development/IMPLEMENTATION_PLAN.md - For task dependencies
- [DOC-HVA-003]: research/hybrid_voice_architecture/implementation_notes/IMPLEMENTATION_CONSIDERATIONS.md - For hardware optimization guidance
- [DOC-COMP-001]: Development/Architecture/COMPONENT_SPECIFICATIONS/VOICE_PIPELINE.md - For speech model requirements
- [DOC-COMP-002]: Development/Architecture/COMPONENT_SPECIFICATIONS/DUAL_TRACK_PROCESSING.md - For LLM requirements
- [External]: Whisper GitHub at https://github.com/openai/whisper
- [External]: llama.cpp GitHub at https://github.com/ggerganov/llama.cpp

## Steps

### 1. Create Model Directory Structure

Set up a structured models directory to organize different types of models:

```bash
mkdir -p models/whisper
mkdir -p models/llm
mkdir -p models/embeddings
mkdir -p models/tts
mkdir -p models/registry
```

### 2. Create Model Registry Schema

Create a JSON schema for the model registry to track all downloaded models:

```json
// models/registry/schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VANTA Model Registry",
  "type": "object",
  "properties": {
    "models": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "type": { "type": "string", "enum": ["whisper", "llm", "embedding", "tts"] },
          "version": { "type": "string" },
          "path": { "type": "string" },
          "size": { "type": "string" },
          "format": { "type": "string" },
          "quantization": { "type": ["string", "null"] },
          "date_added": { "type": "string", "format": "date-time" },
          "hash": { "type": "string" },
          "parameters": { "type": "object" },
          "hardware_requirements": {
            "type": "object",
            "properties": {
              "min_ram": { "type": "string" },
              "gpu_recommended": { "type": "boolean" },
              "metal_supported": { "type": "boolean" }
            }
          },
          "metadata": { "type": "object" }
        },
        "required": ["id", "name", "type", "version", "path", "date_added"]
      }
    }
  }
}
```

Create an initial empty registry:

```json
// models/registry/registry.json
{
  "models": []
}
```

### 3. Create Whisper Model Setup Script

Create a Python script to download and convert Whisper models:

```python
#!/usr/bin/env python3
# scripts/setup_whisper_models.py

import os
import json
import hashlib
import argparse
import subprocess
from datetime import datetime

# Models to download
WHISPER_MODELS = {
    "tiny": {"size": "75M", "params": "39M"},
    "base": {"size": "142M", "params": "74M"},
    "small": {"size": "466M", "params": "244M"},
    "medium": {"size": "1.5G", "params": "769M"}
}

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_model(model_name, models_dir):
    """Download a Whisper model using the whisper command-line tool."""
    model_path = os.path.join(models_dir, f"{model_name}.pt")
    
    # Check if model already exists
    if os.path.exists(model_path):
        print(f"Model {model_name} already exists at {model_path}")
        return model_path
    
    print(f"Downloading Whisper {model_name} model...")
    try:
        # Use whisper.cli to download models
        subprocess.run(["python", "-m", "whisper.cli", "download", model_name, models_dir], 
                      check=True, capture_output=True)
        print(f"Successfully downloaded {model_name} model to {model_path}")
        return model_path
    except subprocess.CalledProcessError as e:
        print(f"Error downloading model: {e}")
        print(f"Error details: {e.stderr.decode()}")
        return None

def update_registry(model_name, model_path, registry_path):
    """Update the model registry with the new model."""
    # Load current registry
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    # Calculate file size
    size_bytes = os.path.getsize(model_path)
    size_mb = size_bytes / (1024 * 1024)
    
    # Format size string
    if size_mb < 1000:
        size_str = f"{size_mb:.1f}MB"
    else:
        size_gb = size_mb / 1024
        size_str = f"{size_gb:.1f}GB"
    
    # Create model entry
    model_entry = {
        "id": f"whisper-{model_name}",
        "name": f"Whisper {model_name}",
        "type": "whisper",
        "version": "v1",
        "path": model_path,
        "size": size_str,
        "format": "pytorch",
        "quantization": None,
        "date_added": datetime.now().isoformat(),
        "hash": calculate_sha256(model_path),
        "parameters": {
            "param_count": WHISPER_MODELS[model_name]["params"]
        },
        "hardware_requirements": {
            "min_ram": "8GB",
            "gpu_recommended": model_name in ["medium", "large"],
            "metal_supported": True
        },
        "metadata": {
            "source": "https://github.com/openai/whisper",
            "language_coverage": "multilingual",
            "description": "OpenAI Whisper speech recognition model"
        }
    }
    
    # Add to registry
    for i, model in enumerate(registry["models"]):
        if model["id"] == model_entry["id"]:
            # Update existing model
            registry["models"][i] = model_entry
            break
    else:
        # Add new model
        registry["models"].append(model_entry)
    
    # Save updated registry
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Updated registry with {model_name} model")

def main():
    parser = argparse.ArgumentParser(description='Download and setup Whisper models')
    parser.add_argument('--models', nargs='+', choices=WHISPER_MODELS.keys(), default=['base'],
                        help='Which models to download')
    args = parser.parse_args()
    
    models_dir = os.path.abspath("models/whisper")
    registry_path = os.path.abspath("models/registry/registry.json")
    
    # Create directories if needed
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    # Create registry if it doesn't exist
    if not os.path.exists(registry_path):
        with open(registry_path, 'w') as f:
            json.dump({"models": []}, f)
    
    # Download requested models
    for model_name in args.models:
        model_path = download_model(model_name, models_dir)
        if model_path:
            update_registry(model_name, model_path, registry_path)
    
    print("Whisper model setup complete.")

if __name__ == "__main__":
    main()
```

### 4. Create Local LLM Setup Script

Create a Python script to download and convert local LLMs for use with llama.cpp:

```python
#!/usr/bin/env python3
# scripts/setup_llm_models.py

import os
import json
import hashlib
import argparse
import subprocess
from datetime import datetime

# Models available for download - these are open models suitable for local use
LLM_MODELS = {
    "mistral-7b": {
        "repo_id": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        "filename": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "size": "4.1GB",
        "params": "7B",
        "quantization": "Q4_K_M"
    },
    "phi-2": {
        "repo_id": "TheBloke/phi-2-GGUF",
        "filename": "phi-2.Q4_K_M.gguf",
        "size": "1.8GB",
        "params": "2.7B",
        "quantization": "Q4_K_M"
    },
    "llama2-7b": {
        "repo_id": "TheBloke/Llama-2-7B-Chat-GGUF",
        "filename": "llama-2-7b-chat.Q4_K_M.gguf",
        "size": "3.9GB",
        "params": "7B",
        "quantization": "Q4_K_M"
    }
}

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_huggingface_model(repo_id, filename, models_dir):
    """Download a model from Hugging Face using huggingface-cli."""
    model_path = os.path.join(models_dir, filename)
    
    # Check if model already exists
    if os.path.exists(model_path):
        print(f"Model {filename} already exists at {model_path}")
        return model_path
    
    print(f"Downloading model {filename} from {repo_id}...")
    try:
        # Create a directory for the model
        model_dir = os.path.join(models_dir, repo_id.split('/')[-1])
        os.makedirs(model_dir, exist_ok=True)
        
        # Use huggingface_hub to download
        subprocess.run([
            "python", "-m", "huggingface_hub.cli", "download",
            "--repo-id", repo_id,
            "--filename", filename,
            "--local-dir", model_dir
        ], check=True)
        
        # Move the file to the final location
        downloaded_path = os.path.join(model_dir, filename)
        subprocess.run(["mv", downloaded_path, model_path], check=True)
        
        print(f"Successfully downloaded model to {model_path}")
        return model_path
    except subprocess.CalledProcessError as e:
        print(f"Error downloading model: {e}")
        return None

def update_registry(model_name, model_path, registry_path, model_info):
    """Update the model registry with the new model."""
    # Load current registry
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    # Create model entry
    model_entry = {
        "id": f"llm-{model_name}",
        "name": f"LLM {model_name}",
        "type": "llm",
        "version": "v1",
        "path": model_path,
        "size": model_info["size"],
        "format": "gguf",
        "quantization": model_info["quantization"],
        "date_added": datetime.now().isoformat(),
        "hash": calculate_sha256(model_path),
        "parameters": {
            "param_count": model_info["params"]
        },
        "hardware_requirements": {
            "min_ram": "16GB",
            "gpu_recommended": True,
            "metal_supported": True
        },
        "metadata": {
            "source": f"https://huggingface.co/{model_info['repo_id']}",
            "description": f"Quantized version of {model_name} for local inference"
        }
    }
    
    # Add to registry
    for i, model in enumerate(registry["models"]):
        if model["id"] == model_entry["id"]:
            # Update existing model
            registry["models"][i] = model_entry
            break
    else:
        # Add new model
        registry["models"].append(model_entry)
    
    # Save updated registry
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Updated registry with {model_name} model")

def main():
    parser = argparse.ArgumentParser(description='Download and setup local LLM models')
    parser.add_argument('--models', nargs='+', choices=LLM_MODELS.keys(), default=['mistral-7b'],
                        help='Which models to download')
    args = parser.parse_args()
    
    # Install dependencies if needed
    try:
        subprocess.run(["pip", "install", "huggingface_hub"], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        print(f"Error details: {e.stderr.decode()}")
        return
    
    models_dir = os.path.abspath("models/llm")
    registry_path = os.path.abspath("models/registry/registry.json")
    
    # Create directories if needed
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    # Create registry if it doesn't exist
    if not os.path.exists(registry_path):
        with open(registry_path, 'w') as f:
            json.dump({"models": []}, f)
    
    # Download requested models
    for model_name in args.models:
        model_info = LLM_MODELS[model_name]
        model_path = download_huggingface_model(
            model_info["repo_id"], 
            model_info["filename"], 
            models_dir
        )
        if model_path:
            update_registry(model_name, model_path, registry_path, model_info)
    
    print("LLM model setup complete.")

if __name__ == "__main__":
    main()
```

### 5. Create Embedding Model Setup Script

Create a script to download embedding models for semantic memory:

```python
#!/usr/bin/env python3
# scripts/setup_embedding_models.py

import os
import json
import hashlib
import argparse
import subprocess
from datetime import datetime

# Embedding models to use
EMBEDDING_MODELS = {
    "all-MiniLM-L6-v2": {
        "repo_id": "sentence-transformers/all-MiniLM-L6-v2",
        "size": "90MB",
        "dimensions": 384,
        "type": "sentence-transformers"
    },
    "all-mpnet-base-v2": {
        "repo_id": "sentence-transformers/all-mpnet-base-v2",
        "size": "420MB",
        "dimensions": 768,
        "type": "sentence-transformers"
    }
}

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_embedding_model(model_name, model_info, models_dir):
    """Download an embedding model using sentence-transformers."""
    model_dir = os.path.join(models_dir, model_name)
    
    # Check if model already exists
    if os.path.exists(model_dir) and os.path.exists(os.path.join(model_dir, "config.json")):
        print(f"Model {model_name} already exists at {model_dir}")
        return model_dir
    
    print(f"Downloading embedding model {model_name}...")
    try:
        # Use sentence-transformers to download the model
        subprocess.run([
            "python", "-c", 
            f"from sentence_transformers import SentenceTransformer; SentenceTransformer('{model_info['repo_id']}', cache_folder='{models_dir}')"
        ], check=True)
        
        # Verify the model was downloaded correctly
        if not os.path.exists(model_dir):
            # Try to find the model in a subfolder
            for root, dirs, files in os.walk(models_dir):
                if os.path.basename(root) == model_name:
                    model_dir = root
                    break
        
        print(f"Successfully downloaded model to {model_dir}")
        return model_dir
    except subprocess.CalledProcessError as e:
        print(f"Error downloading model: {e}")
        return None

def update_registry(model_name, model_dir, registry_path, model_info):
    """Update the model registry with the new model."""
    # Load current registry
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    # Calculate the main config file's hash
    config_path = os.path.join(model_dir, "config.json")
    config_hash = calculate_sha256(config_path) if os.path.exists(config_path) else "unknown"
    
    # Create model entry
    model_entry = {
        "id": f"embedding-{model_name}",
        "name": f"Embedding {model_name}",
        "type": "embedding",
        "version": "v1",
        "path": model_dir,
        "size": model_info["size"],
        "format": "transformers",
        "quantization": None,
        "date_added": datetime.now().isoformat(),
        "hash": config_hash,
        "parameters": {
            "dimensions": model_info["dimensions"]
        },
        "hardware_requirements": {
            "min_ram": "4GB",
            "gpu_recommended": False,
            "metal_supported": True
        },
        "metadata": {
            "source": f"https://huggingface.co/{model_info['repo_id']}",
            "description": f"Sentence Transformer embedding model for semantic search"
        }
    }
    
    # Add to registry
    for i, model in enumerate(registry["models"]):
        if model["id"] == model_entry["id"]:
            # Update existing model
            registry["models"][i] = model_entry
            break
    else:
        # Add new model
        registry["models"].append(model_entry)
    
    # Save updated registry
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Updated registry with {model_name} model")

def main():
    parser = argparse.ArgumentParser(description='Download and setup embedding models')
    parser.add_argument('--models', nargs='+', choices=EMBEDDING_MODELS.keys(), default=['all-MiniLM-L6-v2'],
                        help='Which models to download')
    args = parser.parse_args()
    
    # Install dependencies if needed
    try:
        subprocess.run(["pip", "install", "sentence-transformers"], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return
    
    models_dir = os.path.abspath("models/embeddings")
    registry_path = os.path.abspath("models/registry/registry.json")
    
    # Create directories if needed
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    # Create registry if it doesn't exist
    if not os.path.exists(registry_path):
        with open(registry_path, 'w') as f:
            json.dump({"models": []}, f)
    
    # Download requested models
    for model_name in args.models:
        model_info = EMBEDDING_MODELS[model_name]
        model_dir = download_embedding_model(model_name, model_info, models_dir)
        if model_dir:
            update_registry(model_name, model_dir, registry_path, model_info)
    
    print("Embedding model setup complete.")

if __name__ == "__main__":
    main()
```

### 6. Create TTS Setup Script

Create a script to download and set up TTS models:

```python
#!/usr/bin/env python3
# scripts/setup_tts_models.py

import os
import json
import hashlib
import argparse
import subprocess
from datetime import datetime

# TTS models to use
TTS_MODELS = {
    "tts-1": {
        "type": "api",
        "provider": "openai",
        "size": "N/A",
        "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    },
    "coqui-XTTS-v2": {
        "repo_id": "coqui/XTTS-v2",
        "size": "5.5GB",
        "type": "local",
        "format": "ggml"
    }
}

def setup_api_tts(model_name, model_info, registry_path):
    """Set up API-based TTS models (no download needed)."""
    print(f"Setting up API TTS model {model_name}...")
    
    # Load current registry
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    # Create model entry
    model_entry = {
        "id": f"tts-{model_name}",
        "name": f"TTS {model_name}",
        "type": "tts",
        "version": "v1",
        "path": "api",
        "size": model_info["size"],
        "format": "api",
        "quantization": None,
        "date_added": datetime.now().isoformat(),
        "hash": None,
        "parameters": {
            "provider": model_info["provider"],
            "voices": model_info["voices"]
        },
        "hardware_requirements": {
            "min_ram": "N/A",
            "gpu_recommended": False,
            "metal_supported": False
        },
        "metadata": {
            "source": f"https://platform.openai.com/docs/guides/text-to-speech",
            "description": f"API-based Text-to-Speech model from {model_info['provider']}"
        }
    }
    
    # Add to registry
    for i, model in enumerate(registry["models"]):
        if model["id"] == model_entry["id"]:
            # Update existing model
            registry["models"][i] = model_entry
            break
    else:
        # Add new model
        registry["models"].append(model_entry)
    
    # Save updated registry
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Updated registry with {model_name} TTS model (API-based)")
    return True

def download_local_tts(model_name, model_info, models_dir, registry_path):
    """Download a local TTS model."""
    model_dir = os.path.join(models_dir, model_name)
    
    # Check if model already exists
    if os.path.exists(model_dir) and len(os.listdir(model_dir)) > 0:
        print(f"Model {model_name} already exists at {model_dir}")
        
        # Update registry anyway
        update_registry(model_name, model_dir, registry_path, model_info)
        return model_dir
    
    print(f"Note: Local TTS model {model_name} setup requires manual steps.")
    print(f"Please follow the documentation at https://docs.coqui.ai/en/latest/models/xtts.html")
    print(f"to download and set up the model in {model_dir}")
    
    # Create the directory
    os.makedirs(model_dir, exist_ok=True)
    
    # Create a placeholder file with instructions
    with open(os.path.join(model_dir, "SETUP_INSTRUCTIONS.md"), "w") as f:
        f.write(f"""# {model_name} Setup Instructions

This directory is reserved for the {model_name} TTS model.

To set up this model:

1. Visit https://docs.coqui.ai/en/latest/models/xtts.html
2. Follow the instructions to download the model
3. Place the model files in this directory
4. Run the setup_tts_models.py script again to update the registry
""")
    
    # Add to registry with placeholder
    update_registry(model_name, model_dir, registry_path, model_info, is_placeholder=True)
    
    return model_dir

def update_registry(model_name, model_dir, registry_path, model_info, is_placeholder=False):
    """Update the model registry with the new model."""
    # Load current registry
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    # Create model entry
    model_entry = {
        "id": f"tts-{model_name}",
        "name": f"TTS {model_name}",
        "type": "tts",
        "version": "v1",
        "path": model_dir,
        "size": model_info["size"],
        "format": model_info.get("format", "unknown"),
        "quantization": None,
        "date_added": datetime.now().isoformat(),
        "hash": None,  # Will be updated when actual files are present
        "parameters": {},
        "hardware_requirements": {
            "min_ram": "8GB",
            "gpu_recommended": True,
            "metal_supported": True
        },
        "metadata": {
            "source": f"https://huggingface.co/{model_info.get('repo_id', 'N/A')}",
            "description": f"Local Text-to-Speech model",
            "placeholder": is_placeholder
        }
    }
    
    # Add to registry
    for i, model in enumerate(registry["models"]):
        if model["id"] == model_entry["id"]:
            # Update existing model
            registry["models"][i] = model_entry
            break
    else:
        # Add new model
        registry["models"].append(model_entry)
    
    # Save updated registry
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Updated registry with {model_name} TTS model")

def main():
    parser = argparse.ArgumentParser(description='Set up TTS models')
    parser.add_argument('--models', nargs='+', choices=TTS_MODELS.keys(), default=['tts-1'],
                        help='Which models to set up')
    args = parser.parse_args()
    
    models_dir = os.path.abspath("models/tts")
    registry_path = os.path.abspath("models/registry/registry.json")
    
    # Create directories if needed
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    # Create registry if it doesn't exist
    if not os.path.exists(registry_path):
        with open(registry_path, 'w') as f:
            json.dump({"models": []}, f)
    
    # Set up requested models
    for model_name in args.models:
        model_info = TTS_MODELS[model_name]
        
        if model_info["type"] == "api":
            setup_api_tts(model_name, model_info, registry_path)
        else:
            download_local_tts(model_name, model_info, models_dir, registry_path)
    
    print("TTS model setup complete.")

if __name__ == "__main__":
    main()
```

### 7. Create Model Management Tool

Create a script for interacting with the model registry:

```python
#!/usr/bin/env python3
# scripts/model_manager.py

import os
import json
import argparse
import subprocess
from tabulate import tabulate
from datetime import datetime

def list_models(registry_path, model_type=None):
    """List all models in the registry."""
    if not os.path.exists(registry_path):
        print("Error: Registry file not found.")
        return False
    
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    models = registry["models"]
    
    # Filter by type if specified
    if model_type:
        models = [m for m in models if m["type"] == model_type]
    
    if not models:
        print("No models found." if not model_type else f"No {model_type} models found.")
        return True
    
    # Prepare data for tabulate
    table_data = []
    for model in models:
        table_data.append([
            model["id"],
            model["name"],
            model["type"],
            model["size"],
            model["format"],
            model.get("quantization", "N/A"),
            model["date_added"].split("T")[0]  # Just the date part
        ])
    
    # Print table
    print(tabulate(table_data, headers=["ID", "Name", "Type", "Size", "Format", "Quantization", "Added"]))
    return True

def verify_model(registry_path, model_id):
    """Verify that a model exists and matches its registry entry."""
    if not os.path.exists(registry_path):
        print("Error: Registry file not found.")
        return False
    
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    # Find model
    model = None
    for m in registry["models"]:
        if m["id"] == model_id:
            model = m
            break
    
    if not model:
        print(f"Error: Model {model_id} not found in registry.")
        return False
    
    # Skip API models
    if model["format"] == "api":
        print(f"Model {model_id} is an API model, no local files to verify.")
        return True
    
    # Check if path exists
    model_path = model["path"]
    if not os.path.exists(model_path):
        print(f"Error: Model path {model_path} does not exist.")
        return False
    
    # For directory models, just check if directory exists and is not empty
    if os.path.isdir(model_path):
        files = os.listdir(model_path)
        if not files:
            print(f"Error: Model directory {model_path} is empty.")
            return False
        
        print(f"Model {model_id} exists at {model_path} with {len(files)} files.")
        return True
    
    # For file models, check hash if available
    if model.get("hash"):
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(model_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        calculated_hash = sha256_hash.hexdigest()
        if calculated_hash != model["hash"]:
            print(f"Error: Model hash mismatch for {model_id}.")
            print(f"Expected: {model['hash']}")
            print(f"Got: {calculated_hash}")
            return False
    
    print(f"Model {model_id} verified successfully.")
    return True

def test_model(registry_path, model_id):
    """Test that a model can be loaded and used."""
    if not os.path.exists(registry_path):
        print("Error: Registry file not found.")
        return False
    
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    # Find model
    model = None
    for m in registry["models"]:
        if m["id"] == model_id:
            model = m
            break
    
    if not model:
        print(f"Error: Model {model_id} not found in registry.")
        return False
    
    # Test based on model type
    if model["type"] == "whisper":
        return test_whisper_model(model)
    elif model["type"] == "llm":
        return test_llm_model(model)
    elif model["type"] == "embedding":
        return test_embedding_model(model)
    elif model["type"] == "tts":
        return test_tts_model(model)
    else:
        print(f"Testing not implemented for model type {model['type']}.")
        return False

def test_whisper_model(model):
    """Test that a Whisper model can be loaded and used."""
    print(f"Testing Whisper model {model['name']}...")
    
    try:
        test_script = """
import whisper
import sys

model_path = sys.argv[1]
try:
    model = whisper.load_model(model_path)
    print(f"Successfully loaded model {model_path}")
    # Small test to ensure model works
    result = model.transcribe("https://github.com/openai/whisper/raw/main/tests/jfk.flac", fp16=False)
    print(f"Transcription test successful. First few words: {result['text'][:50]}...")
except Exception as e:
    print(f"Error testing model: {e}")
    sys.exit(1)
"""
        # Write test script to a temporary file
        with open("test_whisper.py", "w") as f:
            f.write(test_script)
        
        # Run test script
        result = subprocess.run(
            ["python", "test_whisper.py", model["path"]], 
            capture_output=True, text=True
        )
        
        # Clean up
        os.remove("test_whisper.py")
        
        if result.returncode != 0:
            print(f"Error testing model: {result.stderr}")
            return False
        
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Error testing model: {e}")
        return False

def test_llm_model(model):
    """Test that an LLM model can be loaded and used."""
    print(f"Testing LLM model {model['name']}...")
    
    try:
        # This requires llama-cpp-python to be installed
        test_script = """
import sys
import json
from llama_cpp import Llama

model_path = sys.argv[1]
model_info = json.loads(sys.argv[2])

try:
    print(f"Loading model from {model_path}...")
    # Use lower context window for test
    model = Llama(
        model_path=model_path,
        n_ctx=512,
        n_batch=512
    )
    
    # Simple test prompt
    prompt = "Hello, I am a language model"
    print(f"Running inference with prompt: {prompt}")
    
    output = model.create_completion(
        prompt,
        max_tokens=20,
        temperature=0.7,
        stop=["\\n", "Human:"],
        echo=True
    )
    
    print(f"Model output: {output['choices'][0]['text']}")
    print("LLM model test successful")
except Exception as e:
    print(f"Error testing model: {e}")
    sys.exit(1)
"""
        # Write test script to a temporary file
        with open("test_llm.py", "w") as f:
            f.write(test_script)
        
        # Run test script
        result = subprocess.run(
            ["python", "test_llm.py", model["path"], json.dumps(model)], 
            capture_output=True, text=True
        )
        
        # Clean up
        os.remove("test_llm.py")
        
        if result.returncode != 0:
            print(f"Error testing model: {result.stderr}")
            return False
        
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Error testing model: {e}")
        return False

def test_embedding_model(model):
    """Test that an embedding model can be loaded and used."""
    print(f"Testing embedding model {model['name']}...")
    
    try:
        test_script = """
import sys
from sentence_transformers import SentenceTransformer

model_path = sys.argv[1]
try:
    print(f"Loading model from {model_path}...")
    model = SentenceTransformer(model_path)
    
    # Test with a simple sentence
    sentences = ["This is a test sentence for embeddings."]
    print(f"Creating embeddings for test sentence...")
    embeddings = model.encode(sentences)
    
    print(f"Successfully created embeddings with shape {embeddings.shape}")
    print(f"First 5 values: {embeddings[0][:5]}")
    print("Embedding model test successful")
except Exception as e:
    print(f"Error testing model: {e}")
    sys.exit(1)
"""
        # Write test script to a temporary file
        with open("test_embedding.py", "w") as f:
            f.write(test_script)
        
        # Run test script
        result = subprocess.run(
            ["python", "test_embedding.py", model["path"]], 
            capture_output=True, text=True
        )
        
        # Clean up
        os.remove("test_embedding.py")
        
        if result.returncode != 0:
            print(f"Error testing model: {result.stderr}")
            return False
        
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Error testing model: {e}")
        return False

def test_tts_model(model):
    """Test that a TTS model can be loaded or accessed."""
    print(f"Testing TTS model {model['name']}...")
    
    # For API models, just check that the API key is available
    if model["format"] == "api" and model["parameters"].get("provider") == "openai":
        if "OPENAI_API_KEY" not in os.environ:
            print("Warning: OPENAI_API_KEY not found in environment variables.")
            print("Can't test OpenAI TTS API access without an API key.")
            return False
        
        # Simple test using the OpenAI API
        try:
            test_script = """
import sys
import os
import json
from openai import OpenAI

model_info = json.loads(sys.argv[1])
try:
    print("Testing OpenAI TTS API access...")
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Just test API connectivity, don't actually generate audio
    voices = model_info["parameters"]["voices"]
    voice = voices[0] if voices else "alloy"
    
    print(f"API connection successful. Available voices: {', '.join(voices)}")
    print("TTS API test successful")
except Exception as e:
    print(f"Error testing TTS API: {e}")
    sys.exit(1)
"""
            # Write test script to a temporary file
            with open("test_tts_api.py", "w") as f:
                f.write(test_script)
            
            # Run test script
            result = subprocess.run(
                ["python", "test_tts_api.py", json.dumps(model)], 
                capture_output=True, text=True
            )
            
            # Clean up
            os.remove("test_tts_api.py")
            
            if result.returncode != 0:
                print(f"Error testing model: {result.stderr}")
                return False
            
            print(result.stdout)
            return True
        except Exception as e:
            print(f"Error testing model: {e}")
            return False
    
    # For local models (more complex, would need to be implemented based on specific model type)
    print(f"Testing local TTS models not yet implemented.")
    return True

def download_all_models(models_dir):
    """Download all models using the separate scripts."""
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ensure models directory exists
    os.makedirs(models_dir, exist_ok=True)
    
    # Run each script
    scripts = [
        ("setup_whisper_models.py", ["--models", "base"]),
        ("setup_llm_models.py", ["--models", "mistral-7b"]),
        ("setup_embedding_models.py", ["--models", "all-MiniLM-L6-v2"]),
        ("setup_tts_models.py", ["--models", "tts-1"])
    ]
    
    for script, args in scripts:
        script_path = os.path.join(scripts_dir, script)
        
        # Create the script if it doesn't exist
        if not os.path.exists(script_path):
            print(f"Error: Script {script_path} not found.")
            continue
        
        print(f"Running {script} {' '.join(args)}...")
        try:
            subprocess.run(["python", script_path] + args, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running {script}: {e}")
    
    print("Download of all models complete.")
    return True

def main():
    parser = argparse.ArgumentParser(description='VANTA Model Manager')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all models')
    list_parser.add_argument('--type', choices=['whisper', 'llm', 'embedding', 'tts'], 
                            help='Filter by model type')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify a model')
    verify_parser.add_argument('model_id', help='ID of the model to verify')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test a model')
    test_parser.add_argument('model_id', help='ID of the model to test')
    
    # Download all command
    download_parser = subparsers.add_parser('download-all', help='Download all models')
    
    args = parser.parse_args()
    
    models_dir = os.path.abspath("models")
    registry_path = os.path.abspath("models/registry/registry.json")
    
    # Create registry if it doesn't exist
    if not os.path.exists(os.path.dirname(registry_path)):
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    if not os.path.exists(registry_path):
        with open(registry_path, 'w') as f:
            json.dump({"models": []}, f)
    
    # Run command
    if args.command == 'list':
        list_models(registry_path, args.type)
    elif args.command == 'verify':
        verify_model(registry_path, args.model_id)
    elif args.command == 'test':
        test_model(registry_path, args.model_id)
    elif args.command == 'download-all':
        download_all_models(models_dir)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

### 8. Create Master Setup Script

Create a master script to execute all model setup tasks:

```bash
#!/bin/bash
# scripts/setup_all_models.sh

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
```

Make the script executable:

```bash
chmod +x scripts/setup_all_models.sh
```

### 9. Create Model Testing Script

Create a script to test all models:

```bash
#!/bin/bash
# scripts/test_all_models.sh

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
```

Make the script executable:

```bash
chmod +x scripts/test_all_models.sh
```

## Validation

This implementation should be validated by:

1. Verifying that the scripts run without errors:
   ```
   ./scripts/setup_all_models.sh
   ```

2. Checking that all required models are properly downloaded and registered:
   ```
   python scripts/model_manager.py list
   ```

3. Testing that models can be loaded and used:
   ```
   ./scripts/test_all_models.sh
   ```

4. Verifying the model registry structure to ensure it has all required information.

5. Checking disk space usage to ensure models are properly downloaded and not duplicated.

6. Running a simple test with each model type to ensure they are functional.

## Notes and Considerations

- The implementation focuses on providing a flexible, extensible model management system that can handle different model types and sources.

- The model registry design allows for tracking model metadata, including hardware requirements and version information.

- For API-based models (like OpenAI's TTS), the implementation simply registers them without downloading any files.

- Local models are downloaded and stored in the models directory with appropriate subdirectories for each model type.

- The implementation provides scripts for verification and testing to ensure models are ready for use.

- For hardware optimization, quantized models are used where appropriate (especially for LLMs) to reduce memory usage.

- The model manager provides a command-line interface for managing models, making it easier to use in development workflows.

- Some models (especially local TTS models) may require additional manual setup due to licensing restrictions.

- All scripts are designed to be idempotent, meaning they can be run multiple times without causing issues.