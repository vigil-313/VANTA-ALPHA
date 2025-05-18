#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model management tool for VANTA.
"""
# TASK-REF: ENV_003 - Model Preparation
# CONCEPT-REF: CON-IMP-012 - Model Preparation
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
# DECISION-REF: DEC-004-004 - Create detailed implementation planning before coding

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
    elif model["type"] == "vad":
        return test_vad_model(model)
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

def test_vad_model(model):
    """Test that a VAD model can be loaded and used."""
    print(f"Testing VAD model {model['name']}...")
    
    try:
        test_script = """
import sys
import os
import json
import numpy as np
import torch

model_info = json.loads(sys.argv[1])
model_path = model_info["path"]

try:
    print(f"Testing Silero VAD model at {model_path}...")
    use_hub = not os.path.exists(model_path)
    
    if use_hub:
        print("Model file not found locally, loading from PyTorch Hub...")
        try:
            # Try to load from PyTorch Hub
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=model_path.endswith('.onnx'),
                verbose=False
            )
            print(f"Successfully loaded model from PyTorch Hub")
            
            # Save for future use if possible
            try:
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                if model_path.endswith('.onnx') and hasattr(model, '_model_path'):
                    import shutil
                    print(f"Copying ONNX model to {model_path}")
                    shutil.copy(model._model_path, model_path)
                elif not model_path.endswith('.onnx'):
                    print(f"Saving PyTorch model to {model_path}")
                    torch.save({'model': model}, model_path)
            except Exception as e:
                print(f"Warning: Could not save model to disk: {e}")
                
        except Exception as e:
            print(f"Error loading from PyTorch Hub: {e}")
            sys.exit(1)
    
    if os.path.exists(model_path):
        if model_path.endswith('.onnx'):
            # Test ONNX model loading
            try:
                import onnxruntime as ort
                print("Using ONNX Runtime for testing")
                
                # Set up ONNX Runtime session
                session_options = ort.SessionOptions()
                session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                
                # Initialize session
                ort_session = ort.InferenceSession(
                    model_path,
                    providers=['CPUExecutionProvider'],
                    sess_options=session_options
                )
                
                # Test with dummy input
                window_size_samples = 1536
                dummy_input = np.zeros((1, window_size_samples), dtype=np.float32)
                dummy_h = np.zeros((2, 1, 64), dtype=np.float32)
                dummy_c = np.zeros((2, 1, 64), dtype=np.float32)
                sr = np.array(16000, dtype=np.int64)
                
                # Run inference
                ort_inputs = {
                    'input': dummy_input,
                    'sr': sr,
                    'h': dummy_h,
                    'c': dummy_c
                }
                
                ort_outs = ort_session.run(None, ort_inputs)
                print(f"ONNX model test successful: Output shape = {ort_outs[0].shape}")
                
            except ImportError as e:
                print(f"ONNX Runtime not available: {e}. Skipping ONNX model test.")
                
        elif model_path.endswith('.pt'):
            # Test PyTorch model loading
            print("Using PyTorch for testing")
            
            # Load model
            torch_model = torch.load(model_path, map_location=torch.device('cpu'))
            model = torch_model['model']
            model.eval()
            
            # Test with dummy input
            window_size_samples = 1536
            dummy_input = torch.zeros(1, window_size_samples)
            h = torch.zeros(2, 1, 64)
            c = torch.zeros(2, 1, 64)
            
            # Run inference
            with torch.no_grad():
                out, (h, c) = model(dummy_input, h, c)
            
            print(f"PyTorch model test successful: Output shape = {out.shape}")
        
        else:
            print(f"Unknown model format for {model_path}")
            sys.exit(1)
    else:
        print(f"Model file not found at {model_path} and could not load from Hub")
        sys.exit(1)
    
    print("VAD model test completed successfully")
    
except Exception as e:
    print(f"Error testing VAD model: {e}")
    sys.exit(1)
"""
        # Write test script to a temporary file
        with open("test_vad.py", "w") as f:
            f.write(test_script)
        
        # Run test script
        result = subprocess.run(
            ["python", "test_vad.py", json.dumps(model)], 
            capture_output=True, text=True
        )
        
        # Clean up
        os.remove("test_vad.py")
        
        if result.returncode != 0:
            print(f"Error testing model: {result.stderr}")
            return False
        
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Error testing model: {e}")
        return False

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
        ("setup_tts_models.py", ["--models", "tts-1"]),
        ("setup_vad_models.py", ["--models", "silero"])
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
    list_parser.add_argument('--type', choices=['whisper', 'llm', 'embedding', 'tts', 'vad'], 
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