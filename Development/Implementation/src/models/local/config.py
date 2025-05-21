"""
Configuration for local model integration.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import platform
import json
from typing import Dict, Any, Optional


def get_default_config() -> Dict[str, Any]:
    """
    Get the default configuration for local models.
    
    Returns:
        Dictionary with default configuration values.
    """
    # Get base directory from environment or use default
    base_model_dir = os.environ.get(
        "VANTA_MODEL_DIR", 
        os.path.join(os.path.expanduser("~"), ".vanta", "models", "llm")
    )
    
    # Detect platform
    system = platform.system()
    metal_supported = system == "Darwin" and platform.processor() != "i386"
    default_threads = os.cpu_count() or 4
    
    return {
        "model_dir": base_model_dir,
        "default_model": "mistral-7b-v0.1-q4_0",
        "max_models_loaded": 1,
        "metal_enabled": metal_supported,
        "thread_count": default_threads,
        "context_size": 4096,
        "max_tokens": 8192,
        "generation": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "repeat_penalty": 1.1,
            "stop_sequences": ["\n\nHuman:", "\n\nUser:"],
        },
        "registry_path": os.path.join(os.path.dirname(base_model_dir), "registry", "registry.json"),
    }


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize the local model configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        Validated and normalized configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Start with default config
    default_config = get_default_config()
    
    # Merge with provided config
    validated = {**default_config}
    
    for key, value in config.items():
        if key in validated and isinstance(validated[key], dict) and isinstance(value, dict):
            # For dict values, merge with defaults
            validated[key] = {**validated[key], **value}
        else:
            # For simple values, replace
            validated[key] = value
    
    # Validate specific values
    if validated["thread_count"] < 1:
        validated["thread_count"] = 1
    
    if validated["context_size"] < 512:
        raise ValueError("context_size must be at least 512")
    
    if validated["max_tokens"] < 1:
        raise ValueError("max_tokens must be at least 1")
    
    if "temperature" in validated["generation"] and (
        validated["generation"]["temperature"] < 0 or validated["generation"]["temperature"] > 2
    ):
        raise ValueError("temperature must be between 0 and 2")
    
    return validated


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file.
    
    Args:
        config_path: Path to configuration file. If None, default
                     configuration is returned.
                     
    Returns:
        Configuration dictionary.
    """
    # If no config file specified, return default
    if not config_path:
        return get_default_config()
    
    # Load config from file
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to load configuration: {e}")
    
    # Validate and return
    return validate_config(config)