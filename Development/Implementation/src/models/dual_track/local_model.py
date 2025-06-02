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
from .model_manager import model_manager

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
        # Use model manager configuration if available, otherwise fall back to config
        if config is None:
            try:
                # Get current model configuration from model manager
                manager_config = model_manager.get_current_config()
                self.config = LocalModelConfig(**manager_config)
                self.logger.info(f"Using model manager config: {model_manager.get_current_model().name}")
            except Exception as e:
                self.logger.warning(f"Could not use model manager config: {e}")
                self.config = DEFAULT_CONFIG.local_model
        else:
            self.config = config
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
        """Build a prompt with query and LangGraph conversation context."""
        # VANTA system prompt for natural conversation with memory safety
        system_prompt = """You are VANTA, a helpful AI assistant. Instructions:

- Be conversational, helpful, and proactive in your responses
- When recalling user information, ONLY use facts explicitly mentioned in the conversation history
- If asked about user details not in the conversation, say "I don't have that information from our conversation"
- For general questions or conversation, respond naturally without needing prior information
- When user asks you to ask them something, be specific and direct (e.g., "What's your name?" or "What do you do for work?")
- Keep responses concise but friendly
- Be honest about memory limitations only when relevant

Be natural and helpful in conversation while being factual about user information."""
        
        # Build conversation history from LangGraph messages
        conversation_str = ""
        if context and isinstance(context, dict):
            # Handle LangGraph messages format (preferred)
            messages = context.get("messages", [])
            if messages:
                from langchain_core.messages import HumanMessage, AIMessage
                conversation_str = "\n\nConversation History:"
                
                # Process LangGraph messages - exclude the current user message
                for i, message in enumerate(messages[:-1]):  # Skip last message (current query)
                    if isinstance(message, HumanMessage):
                        conversation_str += f"\nUSER: {message.content}"
                    elif isinstance(message, AIMessage):
                        conversation_str += f"\nASSISTANT: {message.content}"
            
            # Fallback: Handle old conversation_history format (backward compatibility)
            elif "conversation_history" in context:
                conversation_history = context.get("conversation_history", [])
                if conversation_history:
                    conversation_str = "\n\nConversation History:"
                    for conv in conversation_history:
                        if isinstance(conv, dict):
                            user_msg = conv.get("user_message", "")
                            ai_msg = conv.get("assistant_message", "")
                            if user_msg and ai_msg:
                                conversation_str += f"\nUSER: {user_msg}\nASSISTANT: {ai_msg}"
            
            # Add other context if provided
            other_context = []
            for key, value in context.items():
                if key not in ["messages", "conversation_history"] and isinstance(value, (str, int, float)) and value:
                    other_context.append(f"- {key}: {value}")
                elif key not in ["messages", "conversation_history"] and isinstance(value, list) and value:
                    other_context.append(f"- {key}: {', '.join(map(str, value[:3]))}")
            
            if other_context:
                conversation_str += "\n\nAdditional Context:\n" + "\n".join(other_context)
        
        # Build the complete prompt with conversation context
        return f"{system_prompt}{conversation_str}\n\nUSER: {query}\nASSISTANT:"
    
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
