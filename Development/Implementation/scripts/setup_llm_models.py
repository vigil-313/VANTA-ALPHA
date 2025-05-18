#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM model setup script for VANTA.
"""
# TASK-REF: ENV_003 - Model Preparation
# CONCEPT-REF: CON-IMP-012 - Model Preparation
# CONCEPT-REF: CON-HVA-010 - Local Model Processing
# DOC-REF: DOC-COMP-002 - Dual Track Processing
# DECISION-REF: DEC-004-001 - Adopt dual-track processing architecture

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