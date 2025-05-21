"""
Memory System Configuration

This module provides the configuration definitions and validation for the memory system.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
from typing import Dict, Any, Optional


def get_default_config() -> Dict[str, Any]:
    """
    Get the default memory system configuration.
    
    Returns:
        Dictionary with default configuration values.
    """
    # Base data directory with environment-aware default
    base_data_dir = os.environ.get(
        "VANTA_DATA_DIR", 
        os.path.join(os.path.expanduser("~"), ".vanta", "data")
    )
    
    memory_dir = os.path.join(base_data_dir, "memory")
    
    return {
        "data_path": memory_dir,
        "max_relevant_memories": 5,
        "max_relevant_conversations": 3,
        "working_memory": {
            "max_tokens": 8000,
            "default_user": "user",
            "prune_strategy": "importance",  # Options: importance, recency, hybrid
        },
        "long_term_memory": {
            "storage_path": os.path.join(memory_dir, "conversations"),
            "max_age_days": 30,  # Default retention period
            "backup_enabled": True,
            "backup_interval_days": 7,
            "compression_enabled": True,
        },
        "vector_store": {
            "db_path": os.path.join(memory_dir, "vectors"),
            "collection_name": "vanta_memories",
            "embedding_model": "all-MiniLM-L6-v2",  # Default lightweight model
            "distance_metric": "cosine",
            "persist_directory": os.path.join(memory_dir, "vectors", "chroma"),
        }
    }


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize memory system configuration.
    
    Args:
        config: Configuration dictionary to validate.
        
    Returns:
        Validated and normalized configuration dictionary.
        
    Raises:
        ValueError: If configuration is invalid.
    """
    # Start with default config
    default_config = get_default_config()
    
    # Merge with provided config (shallow for top level, then per section)
    validated = {**default_config}
    
    for key, value in config.items():
        if key in validated and isinstance(validated[key], dict) and isinstance(value, dict):
            # For dict values, merge with defaults
            validated[key] = {**validated[key], **value}
        else:
            # For simple values, replace
            validated[key] = value
    
    # Validate specific values
    if validated["max_relevant_memories"] < 1:
        raise ValueError("max_relevant_memories must be at least 1")
    
    if validated["max_relevant_conversations"] < 1:
        raise ValueError("max_relevant_conversations must be at least 1")
    
    # Ensure working memory max_tokens is reasonable
    if validated["working_memory"]["max_tokens"] < 1000:
        raise ValueError("working_memory.max_tokens must be at least 1000")
    
    # Validate vector store configuration
    valid_distance_metrics = ["cosine", "l2", "ip"]
    if validated["vector_store"]["distance_metric"] not in valid_distance_metrics:
        raise ValueError(
            f"vector_store.distance_metric must be one of {valid_distance_metrics}"
        )
    
    # Ensure storage paths exist or can be created
    for path_key in ["data_path"]:
        os.makedirs(validated[path_key], exist_ok=True)
    
    return validated


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load memory system configuration from file.
    
    Args:
        config_path: Path to configuration file. If None, default
                     configuration is returned.
                     
    Returns:
        Configuration dictionary.
    """
    import json
    
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