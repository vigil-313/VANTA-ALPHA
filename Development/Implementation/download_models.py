#!/usr/bin/env python3
"""
Model Download Script for VANTA
Downloads and manages local LLM models.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

try:
    from huggingface_hub import hf_hub_download
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from models.dual_track.model_manager import model_manager


def download_model(model_key: str) -> bool:
    """Download a specific model."""
    model_info = model_manager.get_model_info(model_key)
    if not model_info:
        print(f"❌ Unknown model: {model_key}")
        return False
    
    if model_manager.is_model_downloaded(model_key):
        print(f"✅ Model already downloaded: {model_info.name}")
        return True
    
    print(f"📥 Downloading {model_info.name}...")
    print(f"   Memory Usage: {model_info.memory_usage}")
    print(f"   Quality: {model_info.quality_tier}")
    print()
    
    # Create models directory
    models_dir = Path("../../models")
    models_dir.mkdir(exist_ok=True)
    model_path = models_dir / model_info.path
    
    # Try Hugging Face Hub first (most reliable)
    if HF_AVAILABLE:
        try:
            return download_with_hf_hub(model_key, model_info, model_path)
        except Exception as e:
            print(f"⚠️  Hugging Face download failed: {e}")
            print(f"🔄 Trying alternative methods...")
    else:
        print(f"💡 Install huggingface_hub for better downloads: pip install huggingface_hub")
    
    # Fallback to direct download
    return download_with_curl(model_key, model_info, model_path)


def download_with_hf_hub(model_key: str, model_info, model_path: Path) -> bool:
    """Download using Hugging Face Hub (most reliable)."""
    # Map our model keys to HF repo info (verified working repos)
    hf_models = {
        "llama31-70b-q8": ("bartowski/Meta-Llama-3.1-70B-Instruct-GGUF", [
            "Meta-Llama-3.1-70B-Instruct-Q8_0/Meta-Llama-3.1-70B-Instruct-Q8_0-00001-of-00002.gguf",
            "Meta-Llama-3.1-70B-Instruct-Q8_0/Meta-Llama-3.1-70B-Instruct-Q8_0-00002-of-00002.gguf"
        ]),
        "llama31-70b-base": ("QuantFactory/Meta-Llama-3.1-70B-GGUF", "Meta-Llama-3.1-70B.Q8_0.gguf"),
        "llama31-8b-q8": ("QuantFactory/Meta-Llama-3.1-8B-Instruct-GGUF", "Meta-Llama-3.1-8B-Instruct.Q8_0.gguf")
    }
    
    if model_key not in hf_models:
        raise Exception(f"No Hugging Face mapping for {model_key}")
    
    repo_id, filenames = hf_models[model_key]
    if isinstance(filenames, str):
        filenames = [filenames]  # Single file
    
    print(f"🤗 Using Hugging Face Hub...")
    print(f"   Repository: {repo_id}")
    if len(filenames) > 1:
        print(f"   Files: {len(filenames)} parts (split model)")
        for i, f in enumerate(filenames):
            print(f"     Part {i+1}: {f.split('/')[-1]}")
    else:
        print(f"   File: {filenames[0]}")
    
    try:
        # Check if user is logged in
        from huggingface_hub import whoami
        try:
            user_info = whoami()
            print(f"✅ Logged in as: {user_info['name']}")
        except Exception:
            print(f"⚠️  Not logged in to Hugging Face")
            print(f"💡 Run: huggingface-cli login")
            print(f"🔄 Continuing with anonymous access...")
        
        print(f"🔄 Starting download (this may take a while)...")
        
        downloaded_files = []
        for i, filename in enumerate(filenames):
            if len(filenames) > 1:
                print(f"📥 Downloading part {i+1}/{len(filenames)}: {filename.split('/')[-1]}")
            
            # Download each file
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=model_path.parent,
                local_dir_use_symlinks=False,
                resume_download=True
            )
            downloaded_files.append(Path(downloaded_path))
        
        # Handle single vs split models
        if len(downloaded_files) == 1:
            # Single file - move to expected location if needed
            if downloaded_files[0] != model_path:
                downloaded_files[0].rename(model_path)
            final_path = model_path
        else:
            # Split model - keep first part as main file reference
            final_path = downloaded_files[0]
            print(f"✅ Split model downloaded to: {final_path.parent}")
        
        # Check if download was successful
        total_size = sum(f.stat().st_size for f in downloaded_files if f.exists())
        if total_size > 1024*1024:  # At least 1MB total
            print(f"✅ Successfully downloaded {model_info.name}")
            print(f"   Total size: {total_size / (1024**3):.1f} GB")
            if len(downloaded_files) > 1:
                print(f"   Files: {len(downloaded_files)} parts")
                print(f"   Main file for VANTA: {final_path}")
            return True
        else:
            print(f"❌ Download completed but files seem incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Hugging Face download failed: {e}")
        if "login" in str(e).lower() or "auth" in str(e).lower():
            print(f"💡 Try: pip install huggingface_hub && huggingface-cli login")
        return False


def download_with_curl(model_key: str, model_info, model_path: Path) -> bool:
    """Fallback download using curl."""
    # Get download URLs
    urls = model_manager.get_download_urls(model_key)
    if not urls:
        print(f"❌ No download URLs available for {model_key}")
        return False
    
    # Try each URL until one works
    for i, url in enumerate(urls):
        print(f"🌐 Trying download source {i+1}/{len(urls)}...")
        print(f"   URL: {url}")
        
        try:
            # Use curl with resume capability and progress bar
            cmd = [
                "curl", "-L", "-C", "-",  # Resume downloads
                "--progress-bar",         # Show progress
                "-o", str(model_path),    # Output file
                url                       # Source URL
            ]
            
            print(f"🔄 Starting download (this may take a while for ~70GB files)...")
            result = subprocess.run(cmd, check=True)
            
            if model_path.exists() and model_path.stat().st_size > 1024*1024:  # At least 1MB
                print(f"✅ Successfully downloaded {model_info.name}")
                print(f"   File size: {model_path.stat().st_size / (1024**3):.1f} GB")
                return True
            else:
                print(f"❌ Download completed but file seems incomplete")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Download failed: {e}")
            if model_path.exists():
                print(f"🗑️  Cleaning up partial download...")
                model_path.unlink()
        except KeyboardInterrupt:
            print(f"\n⚠️  Download interrupted by user")
            if model_path.exists():
                print(f"📂 Partial download saved - you can resume later")
            return False
    
    return False


def show_status():
    """Show current model status."""
    print(model_manager.status_report())


def main():
    """Main download script."""
    print("🤖 VANTA Model Download Manager")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python download_models.py status                    # Show model status")
        print("  python download_models.py llama31-70b-q8           # Download Llama 3.1 70B Q8")
        print("  python download_models.py llama31-70b-base         # Download Llama 3.1 70B Base")
        print("  python download_models.py all                      # Download all models")
        print()
        show_status()
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        show_status()
        
    elif command == "all":
        print("📥 Downloading all premium models...")
        print("⚠️  Warning: This will download ~140GB of data!")
        
        response = input("\nContinue? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Download cancelled")
            return
        
        models_to_download = ["llama31-70b-q8", "llama31-70b-base"]
        
        for model_key in models_to_download:
            print(f"\n{'='*60}")
            success = download_model(model_key)
            if not success:
                print(f"❌ Failed to download {model_key}")
                break
        
        print(f"\n{'='*60}")
        print("📊 Final Status:")
        show_status()
        
    elif command in model_manager.available_models:
        success = download_model(command)
        if success:
            print(f"\n✅ {command} is ready to use!")
            print("\nTo switch VANTA to use this model:")
            print(f"  python switch_model.py {command}")
        
    else:
        print(f"❌ Unknown command: {command}")
        print(f"Available models: {', '.join(model_manager.available_models.keys())}")


if __name__ == "__main__":
    main()
