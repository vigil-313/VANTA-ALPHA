#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Model Configuration for VANTA.

This module handles configuration for API-based language models.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

# Default configuration values
DEFAULT_CONFIG = {
    "default_provider": "anthropic",
    "default_models": {
        "anthropic": "claude-3-opus-20240229",
        "openai": "gpt-4o"
    },
    "timeout": 30,
    "retry_attempts": 3,
    "backoff_factor": 1.5,
    "request_logging": True,
    "log_pii": False,
    "log_dir": None
}


def get_config_dir() -> Path:
    """Get the configuration directory path.
    
    Returns:
        Path to the configuration directory
    """
    # Check for an explicit config directory in environment
    config_dir_env = os.environ.get("VANTA_CONFIG_DIR")
    if config_dir_env:
        config_dir = Path(config_dir_env)
    else:
        # Default to a .vanta directory in the user's home
        config_dir = Path.home() / ".vanta"
    
    # Ensure directory exists
    config_dir.mkdir(parents=True, exist_ok=True)
    
    return config_dir


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load API model configuration.
    
    Args:
        config_path: Optional explicit path to config file
        
    Returns:
        Configuration dictionary
    """
    if config_path:
        config_file = Path(config_path)
    else:
        # Use default location
        config_dir = get_config_dir()
        config_file = config_dir / "api_config.json"
    
    # Start with default configuration
    config = DEFAULT_CONFIG.copy()
    
    # Load from file if it exists
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)
                # Update the default config with file values
                config.update(file_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config from {config_file}: {str(e)}")
    
    # Override with environment variables if present
    if os.environ.get("VANTA_API_DEFAULT_PROVIDER"):
        config["default_provider"] = os.environ.get("VANTA_API_DEFAULT_PROVIDER")
    
    if os.environ.get("VANTA_API_TIMEOUT"):
        try:
            config["timeout"] = int(os.environ.get("VANTA_API_TIMEOUT", "30"))
        except ValueError:
            pass
    
    if os.environ.get("VANTA_API_RETRY_ATTEMPTS"):
        try:
            config["retry_attempts"] = int(os.environ.get("VANTA_API_RETRY_ATTEMPTS", "3"))
        except ValueError:
            pass
    
    if os.environ.get("VANTA_API_REQUEST_LOGGING"):
        config["request_logging"] = os.environ.get("VANTA_API_REQUEST_LOGGING", "true").lower() == "true"
    
    return config


def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> None:
    """Save API model configuration.
    
    Args:
        config: Configuration dictionary to save
        config_path: Optional explicit path to config file
    """
    if config_path:
        config_file = Path(config_path)
    else:
        # Use default location
        config_dir = get_config_dir()
        config_file = config_dir / "api_config.json"
    
    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Warning: Failed to save config to {config_file}: {str(e)}")


def get_api_log_dir() -> Path:
    """Get the API log directory path.
    
    Returns:
        Path to the API log directory
    """
    config = load_config()
    
    if config.get("log_dir"):
        log_dir = Path(config["log_dir"])
    else:
        # Default to a logs directory inside the config dir
        log_dir = get_config_dir() / "logs" / "api"
    
    # Ensure directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    
    return log_dir