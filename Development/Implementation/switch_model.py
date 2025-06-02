#!/usr/bin/env python3
"""
Model Switching Script for VANTA
Easily switch between different local models.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from models.dual_track.model_manager import model_manager


def switch_model(model_key: str) -> bool:
    """Switch to a specific model."""
    if model_key not in model_manager.available_models:
        print(f"❌ Unknown model: {model_key}")
        print(f"Available models: {', '.join(model_manager.available_models.keys())}")
        return False
    
    if not model_manager.is_model_downloaded(model_key):
        print(f"❌ Model not downloaded: {model_key}")
        print(f"Download it first with: python download_models.py {model_key}")
        return False
    
    # Update the model manager
    success = model_manager.set_current_model(model_key)
    if not success:
        return False
    
    model_info = model_manager.get_model_info(model_key)
    print(f"✅ Switched to {model_info.name}")
    print(f"   Memory Usage: {model_info.memory_usage}")
    print(f"   Quality: {model_info.quality_tier}")
    print(f"   Context Window: {model_info.context_window} tokens")
    print()
    print("🔄 Restart VANTA to use the new model")
    
    return True


def show_available_models():
    """Show all available models with their status."""
    print("🤖 Available VANTA Models:")
    print("=" * 50)
    
    for key, model in model_manager.available_models.items():
        status = "✅ Downloaded" if model_manager.is_model_downloaded(key) else "❌ Not Downloaded"
        current = " 👈 CURRENT" if key == model_manager.current_model_key else ""
        
        print(f"\n{key}:")
        print(f"  Name: {model.name}")
        print(f"  Status: {status}{current}")
        print(f"  Memory: {model.memory_usage}")
        print(f"  Quality: {model.quality_tier}")
        print(f"  Description: {model.description}")


def main():
    """Main switching script."""
    print("🤖 VANTA Model Switcher")
    print("=" * 30)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python switch_model.py list                        # Show available models")
        print("  python switch_model.py llama2-7b-q2               # Switch to Llama 2 7B")
        print("  python switch_model.py llama31-70b-q8             # Switch to Llama 3.1 70B Q8")
        print("  python switch_model.py llama31-70b-base           # Switch to Llama 3.1 70B Base")
        print()
        show_available_models()
        return
    
    command = sys.argv[1].lower()
    
    if command in ["list", "ls", "status"]:
        show_available_models()
        
    elif command in model_manager.available_models:
        success = switch_model(command)
        if success:
            print("\n📝 Quick Test Commands:")
            print("  cd vanta-main/v01")
            print("  python main_vanta.py")
            
    else:
        print(f"❌ Unknown model: {command}")
        print(f"Available models: {', '.join(model_manager.available_models.keys())}")


if __name__ == "__main__":
    main()
