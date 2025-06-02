"""
Model Manager for switching between different local models.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a model configuration."""
    name: str
    path: str
    description: str
    memory_usage: str
    context_window: int
    max_tokens: int
    recommended_temp: float = 0.7
    quality_tier: str = "standard"  # basic, standard, high, premium


class ModelManager:
    """Manages multiple local models and switching between them."""
    
    def __init__(self, models_dir: str = "../../models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.config_file = self.models_dir / "current_model.json"
        
        # Predefined model configurations
        self.available_models = {
            "llama2-7b-q2": ModelInfo(
                name="Llama 2 7B (Q2_K)",
                path="llama-2-7b-chat.Q2_K.gguf",
                description="Fast, lightweight model for basic conversations",
                memory_usage="~4GB",
                context_window=2048,
                max_tokens=512,
                quality_tier="basic"
            ),
            "llama31-70b-q8": ModelInfo(
                name="Llama 3.1 70B (Q8_0)",
                path="Meta-Llama-3.1-70B-Instruct.Q8_0.gguf",
                description="Premium quality model with excellent reasoning",
                memory_usage="~70GB",
                context_window=8192,
                max_tokens=1024,
                recommended_temp=0.7,
                quality_tier="premium"
            ),
            "llama31-70b-base": ModelInfo(
                name="Llama 3.1 70B (Base)",
                path="Meta-Llama-3.1-70B.Q8_0.gguf",
                description="Base model without instruction tuning (for experimentation)",
                memory_usage="~70GB",
                context_window=8192,
                max_tokens=1024,
                recommended_temp=0.8,
                quality_tier="premium"
            ),
            "llama31-8b-q8": ModelInfo(
                name="Llama 3.1 8B (Q8_0)",
                path="Meta-Llama-3.1-8B-Instruct.Q8_0.gguf",
                description="Smaller but very capable model - great for testing (much faster download)",
                memory_usage="~8GB",
                context_window=8192,
                max_tokens=1024,
                recommended_temp=0.7,
                quality_tier="high"
            )
        }
        
        # Load persisted current model or use default
        self.current_model_key = self._load_current_model() or "llama31-8b-q8"
    
    def list_models(self) -> Dict[str, ModelInfo]:
        """List all available model configurations."""
        return self.available_models
    
    def get_model_info(self, model_key: str) -> Optional[ModelInfo]:
        """Get information about a specific model."""
        return self.available_models.get(model_key)
    
    def is_model_downloaded(self, model_key: str) -> bool:
        """Check if a model file exists."""
        model_info = self.get_model_info(model_key)
        if not model_info:
            return False
        
        # For split models, check if the first part exists
        if model_key == "llama31-70b-q8":
            # This is a split model, check for first part
            split_path = self.models_dir / "Meta-Llama-3.1-70B-Instruct-Q8_0" / "Meta-Llama-3.1-70B-Instruct-Q8_0-00001-of-00002.gguf"
            return split_path.exists()
        
        model_path = self.models_dir / model_info.path
        return model_path.exists()
    
    def get_model_path(self, model_key: str) -> Optional[str]:
        """Get the full path to a model file."""
        model_info = self.get_model_info(model_key)
        if not model_info:
            return None
        
        # For split models, return path to first part
        if model_key == "llama31-70b-q8":
            split_path = self.models_dir / "Meta-Llama-3.1-70B-Instruct-Q8_0" / "Meta-Llama-3.1-70B-Instruct-Q8_0-00001-of-00002.gguf"
            return str(split_path) if split_path.exists() else None
            
        model_path = self.models_dir / model_info.path
        return str(model_path) if model_path.exists() else None
    
    def get_download_urls(self, model_key: str) -> List[str]:
        """Get download URLs for a model."""
        urls = {
            "llama31-70b-q8": [
                "https://huggingface.co/QuantFactory/Meta-Llama-3.1-70B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-70B-Instruct.Q8_0.gguf",
                "https://huggingface.co/bartowski/Meta-Llama-3.1-70B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-70B-Instruct-Q8_0.gguf"
            ],
            "llama31-70b-base": [
                "https://huggingface.co/QuantFactory/Meta-Llama-3.1-70B-GGUF/resolve/main/Meta-Llama-3.1-70B.Q8_0.gguf",
                "https://huggingface.co/bartowski/Meta-Llama-3.1-70B-GGUF/resolve/main/Meta-Llama-3.1-70B.Q8_0.gguf"
            ]
        }
        return urls.get(model_key, [])
    
    def get_download_commands(self, model_key: str) -> List[str]:
        """Get download commands for a model."""
        model_info = self.get_model_info(model_key)
        if not model_info:
            return []
        
        commands = []
        urls = self.get_download_urls(model_key)
        
        for url in urls:
            # Using curl with resume capability
            cmd = f"curl -L -C - -o '{self.models_dir}/{model_info.path}' '{url}'"
            commands.append(cmd)
            
            # Alternative with wget
            wget_cmd = f"wget -c -O '{self.models_dir}/{model_info.path}' '{url}'"
            commands.append(f"# Alternative: {wget_cmd}")
        
        return commands
    
    def set_current_model(self, model_key: str) -> bool:
        """Set the current active model."""
        if model_key not in self.available_models:
            logger.error(f"Unknown model key: {model_key}")
            return False
        
        if not self.is_model_downloaded(model_key):
            logger.error(f"Model not downloaded: {model_key}")
            return False
        
        self.current_model_key = model_key
        self._save_current_model(model_key)
        logger.info(f"Switched to model: {self.available_models[model_key].name}")
        return True
    
    def get_current_model(self) -> ModelInfo:
        """Get the currently active model."""
        return self.available_models[self.current_model_key]
    
    def get_current_config(self) -> Dict:
        """Get LocalModelConfig for the current model."""
        model = self.get_current_model()
        model_path = self.get_model_path(self.current_model_key)
        
        return {
            "model_path": model_path,
            "max_tokens": model.max_tokens,
            "temperature": model.recommended_temp,
            "context_window": model.context_window,
            "preload": True
        }
    
    def status_report(self) -> str:
        """Generate a status report of all models."""
        report = []
        report.append("🤖 VANTA Model Manager Status")
        report.append("=" * 40)
        
        for key, model in self.available_models.items():
            status = "✅ Downloaded" if self.is_model_downloaded(key) else "❌ Not Downloaded"
            current = "👈 CURRENT" if key == self.current_model_key else ""
            
            report.append(f"\n{model.name} ({key})")
            report.append(f"  Status: {status} {current}")
            report.append(f"  Memory: {model.memory_usage}")
            report.append(f"  Quality: {model.quality_tier}")
            report.append(f"  Description: {model.description}")
        
        return "\n".join(report)
    
    def _load_current_model(self) -> Optional[str]:
        """Load the current model from persistence."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    model_key = data.get('current_model')
                    if model_key and model_key in self.available_models:
                        logger.info(f"Loaded persisted model: {model_key}")
                        return model_key
                    else:
                        logger.warning(f"Invalid persisted model: {model_key}")
        except Exception as e:
            logger.warning(f"Failed to load current model config: {e}")
        return None
    
    def _save_current_model(self, model_key: str) -> None:
        """Save the current model to persistence."""
        try:
            data = {
                'current_model': model_key,
                'last_updated': str(Path(__file__).stat().st_mtime)
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Persisted current model: {model_key}")
        except Exception as e:
            logger.error(f"Failed to save current model config: {e}")


# Global model manager instance
model_manager = ModelManager()
