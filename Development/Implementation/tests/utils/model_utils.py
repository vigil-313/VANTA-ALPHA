# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

import os
import json
from typing import Dict, Any, Optional, List

def get_test_models(model_type: str) -> List[Dict[str, Any]]:
    """
    Get available test models from the model registry.
    
    Args:
        model_type: Type of model to retrieve ('whisper', 'llm', 'embedding', 'tts')
        
    Returns:
        List of model information dictionaries
    """
    registry_path = os.path.abspath("models/registry/registry.json")
    
    if not os.path.exists(registry_path):
        return []
    
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    return [m for m in registry["models"] if m["type"] == model_type]

def get_smallest_model(model_type: str) -> Optional[Dict[str, Any]]:
    """
    Get the smallest available model of a given type for testing.
    
    Args:
        model_type: Type of model to retrieve ('whisper', 'llm', 'embedding', 'tts')
        
    Returns:
        Model information dictionary or None if no models available
    """
    models = get_test_models(model_type)
    
    if not models:
        return None
    
    # Find model with "tiny" or "small" in the name, or the first one
    for keyword in ["tiny", "small", "base", "mini"]:
        for model in models:
            if keyword in model["name"].lower():
                return model
    
    # If no preferred small model found, return the first one
    return models[0]

def skip_if_no_model(model_type: str) -> bool:
    """
    Check if a required model is available and skip test if not.
    
    Args:
        model_type: Type of model required ('whisper', 'llm', 'embedding', 'tts')
        
    Returns:
        True if a model is available, False if not
    """
    model = get_smallest_model(model_type)
    return model is not None