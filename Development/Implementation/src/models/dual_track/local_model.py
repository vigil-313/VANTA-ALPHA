# TASK-REF: DP-001 - Processing Router Implementation
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
Local model controller for dual-track processing system.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from .config import LocalModelConfig, DEFAULT_CONFIG
from .exceptions import LocalModelError, ModelLoadError, GenerationError, TimeoutError as DualTrackTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class LocalModelResponse:
    """Response from local model generation."""
    text: str
    tokens_used: int
    generation_time: float
    finish_reason: str
    model_info: Dict[str, Any]
    error: Optional[str] = None


class LocalModel:
    """Interface to local language model using llama.cpp or similar."""
    
    def __init__(self, config: Optional[LocalModelConfig] = None):
        """Initialize the local model."""
        self.config = config or DEFAULT_CONFIG.local_model
        self.logger = logging.getLogger(__name__)
        
        self.model = None
        self.model_info = {}
        self.is_loaded = False
        self.loading_lock = threading.Lock()
        
        # Performance tracking
        self.generation_count = 0
        self.total_tokens = 0
        self.total_time = 0.0
        
        # Thread pool for generation
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="local-model")
        
        if self.config.preload:
            try:
                self.load_model()
            except Exception as e:
                self.logger.warning(f"Failed to preload model: {e}")
    
    def load_model(self) -> bool:
        """Load the local model."""
        with self.loading_lock:
            if self.is_loaded:
                return True
            
            try:
                self.logger.info(f"Loading local model from {self.config.model_path}")
                start_time = time.time()
                
                # Import llama-cpp-python (lazy import)
                try:
                    from llama_cpp import Llama
                except ImportError:
                    raise ModelLoadError(
                        "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
                    )
                
                # Configure model parameters
                model_params = {
                    "model_path": self.config.model_path,
                    "n_ctx": self.config.context_window,
                    "verbose": False,
                    "seed": -1,  # Random seed
                }
                
                # Add optional parameters
                if self.config.n_threads:
                    model_params["n_threads"] = self.config.n_threads
                
                if self.config.n_gpu_layers != -1:
                    model_params["n_gpu_layers"] = self.config.n_gpu_layers
                
                # Load the model
                self.model = Llama(**model_params)
                
                # Store model information
                load_time = time.time() - start_time
                self.model_info = {
                    "model_path": self.config.model_path,
                    "context_window": self.config.context_window,
                    "load_time": load_time,
                    "n_threads": getattr(self.model, 'n_threads', None),
                    "n_gpu_layers": getattr(self.model, 'n_gpu_layers', None),
                }
                
                self.is_loaded = True
                self.logger.info(f"Model loaded successfully in {load_time:.2f}s")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to load model: {e}")
                raise ModelLoadError(f"Failed to load model: {str(e)}")
    
    def generate(self, query: str, context: Optional[Dict[str, Any]] = None) -> LocalModelResponse:
        """Generate a response to the given query."""
        if not self.is_loaded:
            if not self.load_model():
                raise LocalModelError("Model not loaded and failed to load")
        
        try:
            # Submit generation task to thread pool with timeout
            future = self.executor.submit(self._generate_sync, query, context)
            response = future.result(timeout=self.config.generation_timeout)
            
            # Track statistics
            self.generation_count += 1
            self.total_tokens += response.tokens_used
            self.total_time += response.generation_time
            
            return response
            
        except TimeoutError:
            error_msg = f"Generation timed out after {self.config.generation_timeout}s"
            self.logger.warning(error_msg)
            raise DualTrackTimeoutError(error_msg)
        except Exception as e:
            error_msg = f"Generation failed: {str(e)}"
            self.logger.error(error_msg)
            raise GenerationError(error_msg)
    
    def _generate_sync(self, query: str, context: Optional[Dict[str, Any]]) -> LocalModelResponse:
        """Synchronous generation method."""
        start_time = time.time()
        
        try:
            # Build prompt with context
            prompt = self._build_prompt(query, context)
            
            # Set generation parameters
            params = {
                "prompt": prompt,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
                "repeat_penalty": self.config.repeat_penalty,
                "stop": ["USER:", "Human:", "\n\n"],  # Stop sequences
                "echo": False
            }
            
            # Generate response
            result = self.model(**params)
            
            # Extract response text
            response_text = result["choices"][0]["text"].strip()
            
            # Calculate metrics
            generation_time = time.time() - start_time
            tokens_used = result["usage"]["total_tokens"]
            finish_reason = result["choices"][0]["finish_reason"]
            
            return LocalModelResponse(
                text=response_text,
                tokens_used=tokens_used,
                generation_time=generation_time,
                finish_reason=finish_reason,
                model_info=self.model_info.copy()
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            error_msg = str(e)
            
            return LocalModelResponse(
                text="I apologize, but I encountered an issue generating a response.",
                tokens_used=0,
                generation_time=generation_time,
                finish_reason="error",
                model_info=self.model_info.copy(),
                error=error_msg
            )
    
    def _build_prompt(self, query: str, context: Optional[Dict[str, Any]]) -> str:
        """Build a prompt with query and optional context."""
        # Basic chat template
        if not context:
            return f"USER: {query}\nASSISTANT:"
        
        # Include relevant context
        context_parts = []
        if isinstance(context, dict):
            for key, value in context.items():
                if isinstance(value, (str, int, float)):
                    context_parts.append(f"- {key}: {value}")
                elif isinstance(value, list) and value:
                    context_parts.append(f"- {key}: {', '.join(map(str, value[:3]))}")
        
        if context_parts:
            context_str = "Context information:\n" + "\n".join(context_parts)
            return f"{context_str}\n\nUSER: {query}\nASSISTANT:"
        else:
            return f"USER: {query}\nASSISTANT:"
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get model performance statistics."""
        avg_time = self.total_time / self.generation_count if self.generation_count > 0 else 0
        avg_tokens = self.total_tokens / self.generation_count if self.generation_count > 0 else 0
        
        return {
            "is_loaded": self.is_loaded,
            "model_info": self.model_info,
            "generation_count": self.generation_count,
            "total_tokens": self.total_tokens,
            "total_time": self.total_time,
            "average_generation_time": avg_time,
            "average_tokens_per_generation": avg_tokens,
            "tokens_per_second": self.total_tokens / self.total_time if self.total_time > 0 else 0
        }
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.generation_count = 0
        self.total_tokens = 0
        self.total_time = 0.0
    
    def unload_model(self):
        """Unload the model to free memory."""
        with self.loading_lock:
            if self.model is not None:
                del self.model
                self.model = None
                self.is_loaded = False
                self.logger.info("Model unloaded")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        if hasattr(self, 'model') and self.model is not None:
            del self.model


class LocalModelController:
    """High-level controller for local model operations."""
    
    def __init__(self, config: Optional[LocalModelConfig] = None):
        """Initialize the local model controller."""
        self.config = config or DEFAULT_CONFIG.local_model
        self.logger = logging.getLogger(__name__)
        
        self.model = LocalModel(config)
        self.request_count = 0
        
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a query with the local model."""
        self.request_count += 1
        
        try:
            self.logger.debug(f"Processing query with local model: {query[:50]}...")
            
            # Generate response
            response = self.model.generate(query, context)
            
            # Format response for dual-track system
            return {
                "text": response.text,
                "source": "local_model",
                "metadata": {
                    "tokens_used": response.tokens_used,
                    "generation_time": response.generation_time,
                    "finish_reason": response.finish_reason,
                    "model_info": response.model_info,
                    "request_id": self.request_count
                },
                "error": response.error,
                "success": response.error is None
            }
            
        except Exception as e:
            self.logger.error(f"Local model processing failed: {e}")
            return {
                "text": "I'm sorry, but I'm having trouble processing your request right now.",
                "source": "local_model",
                "metadata": {
                    "tokens_used": 0,
                    "generation_time": 0.0,
                    "finish_reason": "error",
                    "model_info": {},
                    "request_id": self.request_count
                },
                "error": str(e),
                "success": False
            }
    
    def is_available(self) -> bool:
        """Check if the local model is available."""
        return self.model.is_loaded or self.model.load_model()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the local model."""
        stats = self.model.get_model_stats()
        
        return {
            "available": self.is_available(),
            "request_count": self.request_count,
            "model_stats": stats,
            "config": self.config.__dict__
        }