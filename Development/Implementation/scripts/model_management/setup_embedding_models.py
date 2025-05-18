#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding model setup script for VANTA.
"""
# TASK-REF: ENV_003 - Model Preparation
# CONCEPT-REF: CON-IMP-012 - Model Preparation
# CONCEPT-REF: CON-VANTA-007 - Layered Memory
# DOC-REF: DOC-ARCH-002 - Memory Storage Structure
# DECISION-REF: DEC-002-003 - Hybrid memory approach using files and databases

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