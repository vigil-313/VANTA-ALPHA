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
from .optimization import (
    OptimizationConfig,
    PerformanceMonitor,
    QuantizationManager,
    MetalAccelerationManager,
    MemoryManager,
    ThreadOptimizer
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
        self.performance_monitor = None
        self.optimization_config = None
        
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
            
            # Initialize optimization components if needed
            thread_optimizer = ThreadOptimizer()
            metal_manager = MetalAccelerationManager()
            quant_manager = QuantizationManager()
            
            # Extract model size from path for better optimization
            model_name = os.path.basename(model_path)
            model_size_billions = quant_manager.get_model_size_from_name(model_name) / 1_000_000_000
            
            # Create or use optimization config
            if "optimization" in self.config and isinstance(self.config["optimization"], dict):
                # Use provided optimization configuration
                opt_config = OptimizationConfig.from_dict(self.config["optimization"])
            elif self.config.get("use_optimization", True):
                # Create and automatically optimize config
                opt_config = OptimizationConfig(
                    quantization=self.config.get("quantization", "q4_0"),
                    use_metal=self.config.get("metal_enabled"),
                    thread_count=self.config.get("thread_count"),
                    batch_size=self.config.get("batch_size"),
                    context_size=self.config.get("context_size", 4096)
                )
                
                # Apply automatic optimizations
                opt_config = thread_optimizer.optimize_thread_config(
                    config=opt_config,
                    model_size_billions=model_size_billions
                )
                opt_config = metal_manager.update_optimization_config(
                    config=opt_config,
                    model_size_billions=model_size_billions
                )
            else:
                # Use basic configuration from provided config
                opt_config = OptimizationConfig(
                    quantization=self.config.get("quantization", "q4_0"),
                    use_metal=self.config.get("metal_enabled", False),
                    thread_count=self.config.get("thread_count", os.cpu_count() or 4),
                    batch_size=self.config.get("batch_size", 512),
                    context_size=self.config.get("context_size", 4096),
                )
            
            # Validate configuration
            opt_config.validate()
            
            # Get llama parameters
            llama_params = opt_config.get_llama_params()
            
            # Add parameters that aren't covered by OptimizationConfig
            llama_params.update({
                "vocab_only": False,
                "last_n_tokens_size": self.config.get("last_n_tokens_size", 64),
                "seed": self.config.get("seed", -1),
            })
            
            # Set metal_device if using Metal
            if opt_config.use_metal:
                metal_device = self.config.get("metal_device")
                if metal_device is not None:
                    llama_params["metal_device"] = metal_device
            
            # Log initialization parameters
            logger.info(f"Initializing llama.cpp model: {model_path}")
            logger.info(f"  Size: ~{model_size_billions:.1f}B parameters")
            logger.info(f"  Quantization: {opt_config.quantization}")
            logger.info(f"  Context size: {opt_config.context_size}")
            logger.info(f"  Batch size: {opt_config.batch_size}")
            logger.info(f"  Threads: {opt_config.thread_count}")
            logger.info(f"  Metal enabled: {opt_config.use_metal}")
            logger.info(f"  GPU layers: {opt_config.n_gpu_layers if opt_config.use_metal else 0}")
            
            # Initialize performance monitor
            self.performance_monitor = PerformanceMonitor()
            self.performance_monitor.start_monitoring()
            
            # Initialize the model
            start_time = time.time()
            self.model = Llama(
                model_path=model_path,
                **llama_params
            )
            load_time = time.time() - start_time
            
            # Stop performance monitor
            self.performance_monitor.stop_monitoring()
            memory_usage = self.performance_monitor.get_metrics()["peak_memory_gb"]
            
            logger.info(f"Model loaded in {load_time:.2f} seconds, memory usage: {memory_usage:.2f} GB")
            
            # Store optimization config for reference
            self.optimization_config = opt_config
            
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
            # Set up performance monitoring
            monitor = self.performance_monitor or PerformanceMonitor()
            monitor.start_monitoring()
            
            # Count prompt tokens
            if hasattr(self, 'tokenize'):
                prompt_tokens = len(self.tokenize(prompt))
            else:
                prompt_tokens = len(prompt.split()) # Rough approximation
            
            # Generate response
            start_time = time.time()
            result = self.model.create_completion(
                prompt=prompt,
                **generation_params
            )
            generation_time = time.time() - start_time
            
            # Record performance metrics
            completion_tokens = result.get("usage", {}).get("completion_tokens", 0)
            monitor.record_inference(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency=generation_time
            )
            
            # Stop monitoring and get metrics
            monitor.stop_monitoring()
            perf_metrics = monitor.get_metrics()
            
            # Extract and return the result
            output = {
                "text": result["choices"][0]["text"],
                "finish_reason": result["choices"][0].get("finish_reason", "length"),
                "usage": {
                    "prompt_tokens": result.get("usage", {}).get("prompt_tokens", prompt_tokens),
                    "completion_tokens": completion_tokens,
                    "total_tokens": result.get("usage", {}).get("total_tokens", prompt_tokens + completion_tokens),
                },
                "generation_time": generation_time,
                "model_path": self.model_path,
                "tokens_per_second": perf_metrics.get("avg_tokens_per_second", 0),
                "peak_memory_gb": perf_metrics.get("peak_memory_gb", 0),
            }
            
            tokens_per_second = completion_tokens / generation_time if generation_time > 0 else 0
            logger.debug(f"Generated {completion_tokens} tokens in {generation_time:.2f}s ({tokens_per_second:.2f} tokens/sec)")
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
            # Get memory usage before shutdown
            memory_before = 0
            if self.performance_monitor:
                metrics = self.performance_monitor.get_metrics()
                memory_before = metrics.get("current_memory_gb", 0)
            
            # Delete the model to free resources
            # The Python garbage collector should handle actual resource cleanup
            self.model = None
            self.is_initialized = False
            
            # Force garbage collection to clean up memory
            import gc
            gc.collect()
            
            # Get memory after shutdown if possible
            memory_after = 0
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_after = memory_info.rss / (1024 * 1024 * 1024)  # GB
            except ImportError:
                pass
            
            # Log memory freed
            if memory_before > 0 and memory_after > 0:
                logger.info(f"Model resources freed successfully. Memory released: {memory_before - memory_after:.2f} GB")
            else:
                logger.info("Model resources freed successfully.")
                
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