"""
Llama.cpp model adapter for VANTA.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-001 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Metal Acceleration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import platform
import logging
import time
from typing import Dict, Any, Optional, Generator, List, Union

from .interface import LocalModelInterface
from .exceptions import (
    ModelNotFoundError, 
    ModelInitializationError,
    ModelGenerationError,
    ModelNotInitializedError,
    TokenizationError
)

logger = logging.getLogger(__name__)


class LlamaModelAdapter(LocalModelInterface):
    """Adapter for llama.cpp models."""
    
    def __init__(self, model_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the llama.cpp model adapter.
        
        Args:
            model_path: Path to the model file
            config: Optional configuration dictionary
        """
        self.model_path = model_path
        self.config = config or {}
        self.model = None
        self.is_initialized = False
        
        # Initialize if model_path is provided
        if model_path:
            self.initialize(model_path, config)
    
    def initialize(self, model_path: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the model.
        
        Args:
            model_path: Path to the model file
            config: Optional configuration dictionary
            
        Returns:
            True if initialization was successful, False otherwise
            
        Raises:
            ModelNotFoundError: If the model file doesn't exist
            ModelInitializationError: If initialization fails
        """
        # Update config if provided
        if config:
            self.config.update(config)
        
        # Ensure model file exists
        if not os.path.exists(model_path):
            raise ModelNotFoundError(f"Model file not found: {model_path}")
        
        self.model_path = model_path
        
        try:
            # Import here to avoid dependency issues if llama_cpp is not installed
            from llama_cpp import Llama
            
            # Get configuration parameters with defaults
            n_ctx = self.config.get("context_size", 4096)
            n_batch = self.config.get("batch_size", 512)
            n_threads = self.config.get("thread_count", os.cpu_count() or 4)
            metal_enabled = self.config.get("metal_enabled", False)
            metal_device = self.config.get("metal_device", None)  # None means default device
            
            # Check if running on macOS and Metal is enabled
            system = platform.system()
            if system == "Darwin" and metal_enabled:
                logger.info("Initializing llama.cpp with Metal acceleration")
                
                # Metal acceleration parameters
                use_metal = True
                n_gpu_layers = self.config.get("n_gpu_layers", 1)  # Higher for more GPU offloading
            else:
                use_metal = False
                n_gpu_layers = 0
            
            # Log initialization parameters
            logger.info(f"Initializing llama.cpp model: {model_path}")
            logger.info(f"  Context size: {n_ctx}")
            logger.info(f"  Batch size: {n_batch}")
            logger.info(f"  Threads: {n_threads}")
            logger.info(f"  Metal enabled: {use_metal}")
            logger.info(f"  GPU layers: {n_gpu_layers}")
            
            # Initialize the model
            start_time = time.time()
            self.model = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_batch=n_batch,
                n_threads=n_threads,
                n_gpu_layers=n_gpu_layers,
                use_mlock=self.config.get("use_mlock", True),
                use_mmap=self.config.get("use_mmap", True),
                vocab_only=False,
                offload_kqv=self.config.get("offload_kqv", True),
                metal_device=metal_device if use_metal else None,
                last_n_tokens_size=self.config.get("last_n_tokens_size", 64),
                seed=self.config.get("seed", -1),
                verbose=self.config.get("verbose", False)
            )
            load_time = time.time() - start_time
            logger.info(f"Model loaded in {load_time:.2f} seconds")
            
            self.is_initialized = True
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import llama_cpp: {e}")
            raise ModelInitializationError(f"llama_cpp Python package not installed: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise ModelInitializationError(f"Model initialization failed: {e}")
    
    def generate(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a response for the given prompt.
        
        Args:
            prompt: The prompt text to generate from
            params: Optional generation parameters (temperature, top_p, etc.)
            
        Returns:
            Dictionary containing the generated text and metadata
            
        Raises:
            ModelNotInitializedError: If model is not initialized
            ModelGenerationError: If generation fails
        """
        if not self.is_initialized or self.model is None:
            raise ModelNotInitializedError("Model not initialized. Call initialize() first.")
        
        generation_params = self._prepare_generation_params(params)
        
        try:
            start_time = time.time()
            result = self.model.create_completion(
                prompt=prompt,
                **generation_params
            )
            generation_time = time.time() - start_time
            
            # Extract and return the result
            output = {
                "text": result["choices"][0]["text"],
                "finish_reason": result["choices"][0].get("finish_reason", "length"),
                "usage": {
                    "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": result.get("usage", {}).get("total_tokens", 0),
                },
                "generation_time": generation_time,
                "model_path": self.model_path,
            }
            
            logger.debug(f"Generated {output['usage']['completion_tokens']} tokens in {generation_time:.2f}s")
            return output
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise ModelGenerationError(f"Model generation failed: {e}")
    
    def generate_stream(self, 
                        prompt: str, 
                        params: Optional[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Stream a response for the given prompt.
        
        Args:
            prompt: The prompt text to generate from
            params: Optional generation parameters (temperature, top_p, etc.)
            
        Yields:
            Chunks of the generated text with metadata
            
        Raises:
            ModelNotInitializedError: If model is not initialized
            ModelGenerationError: If generation fails
        """
        if not self.is_initialized or self.model is None:
            raise ModelNotInitializedError("Model not initialized. Call initialize() first.")
        
        generation_params = self._prepare_generation_params(params)
        
        try:
            start_time = time.time()
            completion_tokens = 0
            
            # Create streaming completion
            for chunk in self.model.create_completion(
                prompt=prompt,
                stream=True,
                **generation_params
            ):
                chunk_text = chunk["choices"][0]["text"]
                completion_tokens += 1
                current_time = time.time()
                
                yield {
                    "text": chunk_text,
                    "finish_reason": chunk["choices"][0].get("finish_reason"),
                    "usage": {
                        "completion_tokens": completion_tokens,
                    },
                    "generation_time": current_time - start_time,
                }
                
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise ModelGenerationError(f"Model streaming generation failed: {e}")
    
    def tokenize(self, text: str) -> List[int]:
        """
        Tokenize the given text.
        
        Args:
            text: The text to tokenize
            
        Returns:
            List of token IDs
            
        Raises:
            ModelNotInitializedError: If model is not initialized
            TokenizationError: If tokenization fails
        """
        if not self.is_initialized or self.model is None:
            raise ModelNotInitializedError("Model not initialized. Call initialize() first.")
        
        try:
            return self.model.tokenize(text.encode("utf-8"))
        except Exception as e:
            logger.error(f"Tokenization failed: {e}")
            raise TokenizationError(f"Failed to tokenize text: {e}")
    
    def get_token_count(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens
            
        Raises:
            ModelNotInitializedError: If model is not initialized
            TokenizationError: If tokenization fails
        """
        if not self.is_initialized or self.model is None:
            raise ModelNotInitializedError("Model not initialized. Call initialize() first.")
        
        try:
            tokens = self.model.tokenize(text.encode("utf-8"))
            return len(tokens)
        except Exception as e:
            logger.error(f"Token counting failed: {e}")
            raise TokenizationError(f"Failed to count tokens: {e}")
    
    def shutdown(self) -> bool:
        """
        Free model resources.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        if not self.is_initialized or self.model is None:
            logger.warning("Model not initialized, nothing to shut down")
            return True
        
        try:
            # Delete the model to free resources
            # The Python garbage collector should handle actual resource cleanup
            self.model = None
            self.is_initialized = False
            logger.info("Model resources freed successfully")
            return True
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return False
    
    def _prepare_generation_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Prepare generation parameters with defaults.
        
        Args:
            params: User-provided generation parameters
            
        Returns:
            Dictionary of generation parameters
        """
        # Default generation parameters
        defaults = {
            "max_tokens": self.config.get("max_tokens", 256),
            "temperature": self.config.get("generation", {}).get("temperature", 0.7),
            "top_p": self.config.get("generation", {}).get("top_p", 0.9),
            "top_k": self.config.get("generation", {}).get("top_k", 40),
            "repeat_penalty": self.config.get("generation", {}).get("repeat_penalty", 1.1),
            "presence_penalty": self.config.get("generation", {}).get("presence_penalty", 0.0),
            "frequency_penalty": self.config.get("generation", {}).get("frequency_penalty", 0.0),
            "echo": False,
        }
        
        # Add stop sequences if provided in config
        stop_sequences = self.config.get("generation", {}).get("stop_sequences")
        if stop_sequences:
            defaults["stop"] = stop_sequences
        
        # Override with user-provided parameters
        if params:
            defaults.update(params)
        
        return defaults