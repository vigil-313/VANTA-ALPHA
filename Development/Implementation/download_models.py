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
    
    # Get download URLs
    urls = model_manager.get_download_urls(model_key)
    if not urls:
        print(f"❌ No download URLs available for {model_key}")
        return False
    
    model_path = models_dir / model_info.path
    
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
    
    print(f"❌ All download sources failed for {model_key}")
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
