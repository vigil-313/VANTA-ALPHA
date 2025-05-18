#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS model setup script for VANTA.
"""
# TASK-REF: ENV_003 - Model Preparation
# CONCEPT-REF: CON-IMP-012 - Model Preparation
# CONCEPT-REF: CON-VANTA-006 - Text-to-Speech
# DOC-REF: DOC-COMP-001 - Voice Pipeline
# DECISION-REF: DEC-002-002 - Design for swappable TTS/STT components

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