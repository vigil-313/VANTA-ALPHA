#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Silero VAD model setup script for VANTA.

Downloads and configures Silero VAD models for voice activity detection.
"""
# TASK-REF: VOICE_002 - Voice Activity Detection
# CONCEPT-REF: CON-VOICE-012 - Silero VAD Model
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-004 - Support multiple activation modes

import os
import json
import hashlib
import argparse
import requests
import torch
import shutil
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Defines the models and their URLs
VAD_MODELS = {
    "silero": {
        "name": "Silero VAD",
        "description": "Lightweight Voice Activity Detection model from Silero Team",
        "versions": {
            "onnx": {
                "url": "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx",
                "backup_url": "https://huggingface.co/snakers4/silero-vad/resolve/main/silero_vad.onnx",
                "size": "small",
                "format": "onnx",
            },
            "pytorch": {
                "url": "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.pt",
                "backup_url": "https://huggingface.co/snakers4/silero-vad/resolve/main/silero_vad.pt",
                "size": "small",
                "format": "pytorch",
            }
        }
    }
}

def get_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_model(url, output_path):
    """Download a model using PyTorch Hub to the specified path."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    repo = model_info.get("repo", "snakers4/silero-vad")
    model_name = model_info.get("model_name", "silero_vad")
    use_onnx = format_id == "onnx"
    
    logger.info(f"Downloading model via PyTorch Hub from {repo}")
    
    try:
        # Load from PyTorch Hub
        model, utils = torch.hub.load(
            repo_or_dir=repo,
            model=model_name,
            force_reload=False,  # Set to True only when debugging
            onnx=use_onnx,
            verbose=False
        )
        
        if use_onnx and hasattr(model, '_model_path') and os.path.exists(model._model_path):
            # Copy the ONNX file
            logger.info(f"Copying ONNX model from {model._model_path} to {output_path}")
            shutil.copy(model._model_path, output_path)
        elif not use_onnx:
            # Save PyTorch model
            logger.info(f"Saving PyTorch model to {output_path}")
            torch.save({'model': model}, output_path)
        else:
            # If we can't find the path, try to download from the URL if available
            if hasattr(model, '_model_url'):
                logger.info(f"Downloading from URL: {model._model_url}")
                download_file(model._model_url, output_path)
            else:
                raise FileNotFoundError("Could not locate model file from PyTorch Hub")
        
        logger.info(f"Successfully obtained model: {output_path}")
        
        # Calculate and return hash
        file_hash = get_sha256(output_path)
        logger.info(f"File hash: {file_hash}")
        return file_hash
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        raise

def download_file(url, output_path):
    """Download a file from URL to the specified path."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    logger.info(f"Downloading from {url} to {output_path}")
    
    # Download with progress
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte
    
    progress_interval = max(1, total_size // (block_size * 100)) if total_size > 0 else 10
    
    with open(output_path, 'wb') as file:
        downloaded_size = 0
        last_print = 0
        
        for i, data in enumerate(response.iter_content(block_size)):
            file.write(data)
            downloaded_size += len(data)
            
            # Show progress every ~1%
            if i % progress_interval == 0 or downloaded_size == total_size:
                if total_size > 0:
                    percent = downloaded_size * 100 // total_size
                    if percent > last_print:
                        logger.info(f"Downloaded {downloaded_size}/{total_size} bytes ({percent}%)")
                        last_print = percent
                else:
                    logger.info(f"Downloaded {downloaded_size} bytes")
    
    logger.info(f"Download complete: {output_path}")
    
    # Calculate and return hash
    file_hash = get_sha256(output_path)
    logger.info(f"File hash: {file_hash}")
    return file_hash

def update_registry(registry_path, model_id, model_data):
    """Update the model registry with new model information."""
    # Create registry directory if it doesn't exist
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    # Load existing registry or create a new one
    if os.path.exists(registry_path):
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    else:
        registry = {"models": []}
    
    # Check if model already exists
    for i, model in enumerate(registry["models"]):
        if model["id"] == model_id:
            # Update existing model
            registry["models"][i] = model_data
            break
    else:
        # Add new model
        registry["models"].append(model_data)
    
    # Write registry back
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    logger.info(f"Updated registry with model {model_id}")

def setup_vad_models(args):
    """Setup VAD models based on command line arguments."""
    models_to_setup = []
    
    # Determine which models to download
    if args.models == "all":
        for model_id in VAD_MODELS:
            for format_id in VAD_MODELS[model_id]["versions"]:
                models_to_setup.append((model_id, format_id))
    else:
        model_id = args.models
        
        if model_id not in VAD_MODELS:
            logger.error(f"Unknown model: {model_id}")
            return False
        
        format_id = args.format
        
        if format_id == "all":
            for format_id in VAD_MODELS[model_id]["versions"]:
                models_to_setup.append((model_id, format_id))
        else:
            if format_id not in VAD_MODELS[model_id]["versions"]:
                logger.error(f"Unknown format: {format_id} for model {model_id}")
                return False
            
            models_to_setup.append((model_id, format_id))
    
    # Setup each model
    for model_id, format_id in models_to_setup:
        logger.info(f"Setting up {model_id} model in {format_id} format")
        
        # Get model info
        model_info = VAD_MODELS[model_id]
        version_info = model_info["versions"][format_id]
        
        # Determine model path
        if format_id == "onnx":
            model_filename = f"silero_vad.onnx"
        else:
            model_filename = f"silero_vad.pt"
        
        model_dir = os.path.join(args.base_dir, "vad", model_id)
        model_path = os.path.join(model_dir, model_filename)
        
        # Download model
        try:
            # Try primary URL first, then fallback to backup URL if available
            try:
                url = version_info["url"]
                file_hash = download_model(url, model_path)
            except Exception as e:
                if "backup_url" in version_info:
                    logger.warning(f"Primary URL failed: {e}. Trying backup URL.")
                    url = version_info["backup_url"]
                    file_hash = download_model(url, model_path)
                else:
                    raise
            
            # Update registry
            registry_model_id = f"vad-{model_id}-{format_id}"
            model_data = {
                "id": registry_model_id,
                "name": model_info["name"],
                "description": model_info["description"],
                "type": "vad",
                "size": version_info["size"],
                "format": version_info["format"],
                "path": model_path,
                "hash": file_hash,
                "parameters": {
                    "sample_rate": 16000,
                    "window_size_samples": 1536,
                    "threshold": 0.5
                },
                "date_added": datetime.utcnow().isoformat()
            }
            
            update_registry(args.registry, registry_model_id, model_data)
            logger.info(f"Successfully set up {model_id} model in {format_id} format")
        except Exception as e:
            logger.error(f"Error setting up {model_id} model in {format_id} format: {e}")
            continue
    
    return True

def main():
    """Main function for the script."""
    parser = argparse.ArgumentParser(description='VAD Model Setup for VANTA')
    parser.add_argument('--models', default="silero", choices=["all", "silero"],
                        help="Which models to download")
    parser.add_argument('--format', default="all", choices=["all", "onnx", "pytorch"],
                        help="Which format to download")
    parser.add_argument('--base-dir', default="models",
                        help="Base directory for model storage")
    parser.add_argument('--registry', default="models/registry/registry.json",
                        help="Path to model registry file")
    
    args = parser.parse_args()
    
    # Ensure base_dir is absolute
    args.base_dir = os.path.abspath(args.base_dir)
    
    # Ensure registry path is absolute
    args.registry = os.path.abspath(args.registry)
    
    # Setup models
    setup_vad_models(args)

if __name__ == "__main__":
    main()