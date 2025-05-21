"""
Local model manager for VANTA.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-001 - Local Model Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Generator, Union

from .config import get_default_config, validate_config, load_config
from .llama_adapter import LlamaModelAdapter
from .prompt_formatter import PromptFormatter
from .exceptions import (
    ModelNotFoundError,
    ModelLoadError,
    ModelNotInitializedError,
    UnsupportedModelTypeError
)

logger = logging.getLogger(__name__)


class LocalModelManager:
    """Manages local model loading and inference."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the local model manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or get_default_config()
        self.model_registry = self._load_registry()
        self.active_models = {}  # Map of model_id to model adapter
        self.prompt_formatter = PromptFormatter()
        
        logger.info(f"LocalModelManager initialized with {len(self.model_registry.get('models', []))} models in registry")
    
    def _load_registry(self) -> Dict[str, Any]:
        """
        Load model registry data.
        
        Returns:
            Model registry dictionary
        """
        registry_path = self.config.get("registry_path")
        
        if not registry_path or not os.path.exists(registry_path):
            logger.warning(f"Registry file not found at {registry_path}, using empty registry")
            return {"version": "1.0.0", "models": []}
        
        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)
                logger.info(f"Loaded model registry with {len(registry.get('models', []))} models")
                return registry
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {"version": "1.0.0", "models": []}
    
    def list_available_models(self, model_type: Optional[str] = "llm") -> List[Dict[str, Any]]:
        """
        List all available models in the registry.
        
        Args:
            model_type: Optional model type to filter by (default: "llm")
            
        Returns:
            List of model information dictionaries
        """
        models = self.model_registry.get("models", [])
        
        if model_type:
            return [m for m in models if m.get("type") == model_type]
        return models
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.
        
        Args:
            model_id: ID of the model to retrieve info for
            
        Returns:
            Model information dictionary, or None if not found
        """
        for model in self.model_registry.get("models", []):
            if model.get("id") == model_id:
                return model
        return None
    
    def load_model(self, model_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Load a specific model or the default model.
        
        Args:
            model_id: ID of the model to load, or None for default
            config: Optional configuration overrides
            
        Returns:
            ID of the loaded model
            
        Raises:
            ModelNotFoundError: If the model is not found in the registry
            ModelLoadError: If the model fails to load
        """
        # Use default model if none specified
        if not model_id:
            model_id = self.config.get("default_model")
            if not model_id:
                raise ModelLoadError("No model ID provided and no default model configured")
        
        # Check if model is already loaded
        if model_id in self.active_models:
            logger.info(f"Model {model_id} already loaded")
            return model_id
        
        # Get model info from registry
        model_info = self.get_model_info(model_id)
        if not model_info:
            raise ModelNotFoundError(f"Model {model_id} not found in registry")
        
        # Check if we need to unload any models due to max_models constraint
        max_models = self.config.get("max_models_loaded", 1)
        if len(self.active_models) >= max_models and max_models > 0:
            # Unload the oldest model
            oldest_model_id = next(iter(self.active_models))
            logger.info(f"Max models reached, unloading {oldest_model_id}")
            self.unload_model(oldest_model_id)
        
        # Construct full model path
        model_path = model_info.get("path")
        if not os.path.isabs(model_path):
            model_dir = self.config.get("model_dir")
            model_path = os.path.join(model_dir, model_path)
        
        # Prepare model configuration
        model_config = self.config.copy()
        if config:
            model_config.update(config)
        
        # Apply model-specific parameters from registry if available
        if "parameters" in model_info:
            model_config.update(model_info["parameters"])
        
        try:
            # Load the model based on its type
            model_type = model_info.get("type", "llm")
            model_format = model_info.get("format", "gguf")
            
            if model_type != "llm":
                raise UnsupportedModelTypeError(f"Model type {model_type} not supported by LocalModelManager")
            
            if model_format in ["gguf", "ggml"]:
                logger.info(f"Loading {model_format} model {model_id} from {model_path}")
                
                # Create and initialize adapter
                adapter = LlamaModelAdapter()
                adapter.initialize(model_path, model_config)
                
                # Store in active models
                self.active_models[model_id] = {
                    "adapter": adapter,
                    "info": model_info,
                    "loaded_at": time.time(),
                    "model_type": self._get_model_architecture(model_info)
                }
                
                logger.info(f"Successfully loaded model {model_id}")
                return model_id
            else:
                raise UnsupportedModelTypeError(f"Model format {model_format} not supported")
                
        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            raise ModelLoadError(f"Failed to load model {model_id}: {e}")
    
    def unload_model(self, model_id: str) -> bool:
        """
        Unload a model to free resources.
        
        Args:
            model_id: ID of the model to unload
            
        Returns:
            True if successful, False otherwise
        """
        if model_id not in self.active_models:
            logger.warning(f"Model {model_id} not loaded, nothing to unload")
            return False
        
        try:
            # Get adapter and shut it down
            adapter = self.active_models[model_id]["adapter"]
            adapter.shutdown()
            
            # Remove from active models
            del self.active_models[model_id]
            logger.info(f"Successfully unloaded model {model_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload model {model_id}: {e}")
            return False
    
    def get_model_stats(self, model_id: str) -> Dict[str, Any]:
        """
        Get performance stats for a loaded model.
        
        Args:
            model_id: ID of the model to get stats for
            
        Returns:
            Dictionary of model statistics
            
        Raises:
            ModelNotInitializedError: If the model is not loaded
        """
        if model_id not in self.active_models:
            raise ModelNotInitializedError(f"Model {model_id} not loaded")
        
        model_data = self.active_models[model_id]
        
        # Collect basic stats
        stats = {
            "model_id": model_id,
            "loaded_at": model_data["loaded_at"],
            "uptime_seconds": time.time() - model_data["loaded_at"],
            "model_type": model_data["model_type"],
            "model_path": model_data["adapter"].model_path,
        }
        
        return stats
    
    def generate(self, 
                 prompt: str, 
                 model_id: Optional[str] = None,
                 params: Optional[Dict[str, Any]] = None,
                 format_prompt: bool = True,
                 system_prompt: Optional[str] = None,
                 messages: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Generate a response from the specified model.
        
        Args:
            prompt: The prompt text to generate from
            model_id: ID of the model to use, or None for default
            params: Optional generation parameters
            format_prompt: Whether to format the prompt using templates
            system_prompt: Optional system prompt to use if formatting
            messages: Optional message list to format instead of raw prompt
            
        Returns:
            Dictionary containing the generated text and metadata
            
        Raises:
            ModelNotInitializedError: If the model is not loaded
        """
        # Load or get the model
        model_id = self._ensure_model_loaded(model_id)
        
        if model_id not in self.active_models:
            raise ModelNotInitializedError(f"Model {model_id} not loaded")
        
        model_data = self.active_models[model_id]
        adapter = model_data["adapter"]
        model_type = model_data["model_type"]
        
        # Format prompt if requested
        input_prompt = prompt
        if format_prompt:
            if messages:
                # Format from message list
                input_prompt = self.prompt_formatter.format_prompt(messages, model_type)
            elif system_prompt:
                # Format with system prompt + user prompt
                input_prompt = self.prompt_formatter.format_prompt([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ], model_type)
        
        # Generate response
        result = adapter.generate(input_prompt, params)
        
        # Extract assistant response if prompt was formatted
        if format_prompt:
            result["text"] = self.prompt_formatter.extract_response(result["text"], model_type)
        
        # Add model information
        result["model_id"] = model_id
        
        return result
    
    def generate_stream(self, 
                        prompt: str, 
                        model_id: Optional[str] = None,
                        params: Optional[Dict[str, Any]] = None,
                        format_prompt: bool = True,
                        system_prompt: Optional[str] = None,
                        messages: Optional[List[Dict[str, str]]] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Stream a response from the specified model.
        
        Args:
            prompt: The prompt text to generate from
            model_id: ID of the model to use, or None for default
            params: Optional generation parameters
            format_prompt: Whether to format the prompt using templates
            system_prompt: Optional system prompt to use if formatting
            messages: Optional message list to format instead of raw prompt
            
        Yields:
            Chunks of the generated text with metadata
            
        Raises:
            ModelNotInitializedError: If the model is not loaded
        """
        # Load or get the model
        model_id = self._ensure_model_loaded(model_id)
        
        if model_id not in self.active_models:
            raise ModelNotInitializedError(f"Model {model_id} not loaded")
        
        model_data = self.active_models[model_id]
        adapter = model_data["adapter"]
        model_type = model_data["model_type"]
        
        # Format prompt if requested
        input_prompt = prompt
        if format_prompt:
            if messages:
                # Format from message list
                input_prompt = self.prompt_formatter.format_prompt(messages, model_type)
            elif system_prompt:
                # Format with system prompt + user prompt
                input_prompt = self.prompt_formatter.format_prompt([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ], model_type)
        
        # Generate response stream
        full_text = ""
        for chunk in adapter.generate_stream(input_prompt, params):
            chunk_text = chunk["text"]
            full_text += chunk_text
            
            # Extract assistant response if prompt was formatted
            if format_prompt:
                extracted_response = self.prompt_formatter.extract_response(full_text, model_type)
                # Determine what's new compared to the previous extraction
                if len(extracted_response) > 0:
                    chunk["text"] = extracted_response[-len(chunk_text):]
                else:
                    chunk["text"] = ""
            
            # Add model information
            chunk["model_id"] = model_id
            
            yield chunk
    
    def shutdown(self) -> bool:
        """
        Shutdown all models and free resources.
        
        Returns:
            True if successful, False otherwise
        """
        success = True
        for model_id in list(self.active_models.keys()):
            if not self.unload_model(model_id):
                success = False
        
        logger.info("LocalModelManager shutdown complete")
        return success
    
    def _ensure_model_loaded(self, model_id: Optional[str] = None) -> str:
        """
        Ensure a model is loaded, loading it if necessary.
        
        Args:
            model_id: ID of the model to ensure is loaded, or None for default
            
        Returns:
            ID of the loaded model
        """
        # Use default model if none specified
        if not model_id:
            model_id = self.config.get("default_model")
            if not model_id:
                raise ModelLoadError("No model ID provided and no default model configured")
        
        # Load the model if not already loaded
        if model_id not in self.active_models:
            logger.info(f"Model {model_id} not loaded, loading now")
            return self.load_model(model_id)
        
        return model_id
    
    def _get_model_architecture(self, model_info: Dict[str, Any]) -> str:
        """
        Determine the model architecture for prompt formatting.
        
        Args:
            model_info: Model information dictionary
            
        Returns:
            Model architecture identifier (llama2, mistral, etc.)
        """
        # Check for explicit architecture in model parameters
        if "parameters" in model_info and "architecture" in model_info["parameters"]:
            return model_info["parameters"]["architecture"]
        
        # Try to infer from model name
        name = model_info.get("name", "").lower()
        
        if "llama-2" in name or "llama2" in name:
            return "llama2"
        elif "mistral" in name:
            return "mistral"
        elif "vicuna" in name:
            return "vicuna"
        elif "mpt" in name:
            return "chatml"
        elif "zephyr" in name:
            return "mistral"  # Zephyr uses Mistral-like format
        
        # Default to mistral as it's a common format
        return "mistral"