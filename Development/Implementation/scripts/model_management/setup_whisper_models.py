#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper model setup script for VANTA.
"""
# TASK-REF: ENV_003 - Model Preparation
# CONCEPT-REF: CON-IMP-012 - Model Preparation
# DOC-REF: DOC-COMP-001 - Voice Pipeline
# DECISION-REF: DEC-002-001 - Use Whisper for speech-to-text conversion

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