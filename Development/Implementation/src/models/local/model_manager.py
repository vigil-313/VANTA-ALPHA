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
from .optimization import (
    OptimizationConfig,
    PerformanceMonitor,
    QuantizationManager,
    MetalAccelerationManager,
    MemoryManager,
    ThreadOptimizer
)
from .benchmarks import BenchmarkRunner

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
        
        # Initialize optimization components
        self.performance_monitor = PerformanceMonitor()
        self.quantization_manager = QuantizationManager()
        self.metal_manager = MetalAccelerationManager()
        self.thread_optimizer = ThreadOptimizer()
        self.memory_manager = MemoryManager(
            memory_limit_gb=self.config.get("memory_limit_gb", 8.0),
            enable_monitoring=self.config.get("monitor_memory", True)
        )
        
        # Set up benchmark runner
        self.benchmark_runner = None  # Initialize lazily when needed
        
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
            
        # Check if optimization should be applied
        if model_config.get("use_optimization", True) and "optimization" not in model_config:
            # Get model size from name
            model_name = model_info.get("name", model_id)
            model_size_billions = self.quantization_manager.get_model_size_from_name(model_name) / 1_000_000_000
            
            # Create optimized configuration
            opt_config = OptimizationConfig()
            opt_config = self.thread_optimizer.optimize_thread_config(
                config=opt_config,
                model_size_billions=model_size_billions
            )
            opt_config = self.metal_manager.update_optimization_config(
                config=opt_config,
                model_size_billions=model_size_billions
            )
            
            # Add optimization config to model configuration
            model_config["optimization"] = opt_config.to_dict()
            
            # Check if memory is sufficient
            memory_check = self.memory_manager.check_memory_sufficient(
                required_gb=opt_config.memory_limit_gb
            )
            
            if not memory_check["sufficient"]:
                logger.warning(
                    f"Low memory available ({memory_check['available_gb']:.2f} GB) for model requiring "
                    f"{memory_check['required_gb']:.2f} GB. Model may experience performance issues."
                )
        
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
                    "model_type": self._get_model_architecture(model_info),
                    "performance": adapter.performance_monitor.get_metrics() if hasattr(adapter, "performance_monitor") else None,
                    "optimization": adapter.optimization_config.to_dict() if hasattr(adapter, "optimization_config") else None
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
        adapter = model_data["adapter"]
        
        # Collect basic stats
        stats = {
            "model_id": model_id,
            "loaded_at": model_data["loaded_at"],
            "uptime_seconds": time.time() - model_data["loaded_at"],
            "model_type": model_data["model_type"],
            "model_path": adapter.model_path,
        }
        
        # Add optimization configuration if available
        if hasattr(adapter, "optimization_config") and adapter.optimization_config:
            stats["optimization"] = adapter.optimization_config.to_dict()
        elif "optimization" in model_data:
            stats["optimization"] = model_data["optimization"]
            
        # Add performance metrics if available
        if hasattr(adapter, "performance_monitor") and adapter.performance_monitor:
            stats["performance"] = adapter.performance_monitor.get_metrics()
        elif "performance" in model_data:
            stats["performance"] = model_data["performance"]
            
        # Add memory usage if available
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            stats["current_memory_gb"] = memory_info.rss / (1024 * 1024 * 1024)  # Convert to GB
        except ImportError:
            pass
        
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
        
        # Record start of processing in performance monitor
        self.performance_monitor.start_monitoring()
        
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
        
        # Update performance monitoring
        self.performance_monitor.stop_monitoring()
        
        # Update model_data with latest performance metrics if adapter has them
        if hasattr(adapter, "performance_monitor") and adapter.performance_monitor:
            model_data["performance"] = adapter.performance_monitor.get_metrics()
        
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
        
        # Stop memory monitoring if active
        if hasattr(self.memory_manager, 'stop_monitoring'):
            self.memory_manager.stop_monitoring()
        
        logger.info("LocalModelManager shutdown complete")
        return success
        
    def benchmark_model(self, 
                       model_id: str, 
                       benchmark_type: str = "latency",
                       save_results: bool = False,
                       results_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run benchmarks on a specific model.
        
        Args:
            model_id: ID of the model to benchmark
            benchmark_type: Type of benchmark to run ("latency", "memory", "throughput", "comprehensive")
            save_results: Whether to save benchmark results to a file
            results_path: Path to save results to (if save_results is True)
            
        Returns:
            Dictionary with benchmark results
            
        Raises:
            ModelNotFoundError: If the model is not found in the registry
        """
        # Check if model exists in registry
        if not self.get_model_info(model_id):
            raise ModelNotFoundError(f"Model {model_id} not found in registry")
            
        # Initialize benchmark runner if needed
        if self.benchmark_runner is None:
            self.benchmark_runner = BenchmarkRunner(self)
            
        # Run appropriate benchmark
        logger.info(f"Running {benchmark_type} benchmark for model {model_id}")
        
        if benchmark_type == "latency":
            results = self.benchmark_runner.run_latency_benchmark(model_id)
        elif benchmark_type == "memory":
            results = self.benchmark_runner.run_memory_benchmark(model_id)
        elif benchmark_type == "throughput":
            results = self.benchmark_runner.run_throughput_benchmark(model_id)
        elif benchmark_type == "comprehensive":
            results = self.benchmark_runner.run_comprehensive_benchmark(model_id)
        else:
            raise ValueError(f"Unknown benchmark type: {benchmark_type}")
            
        # Save results if requested
        if save_results and results_path:
            self.benchmark_runner.save_benchmark_results(results, results_path)
            logger.info(f"Benchmark results saved to {results_path}")
            
        return results
        
    def optimize_model(self, 
                      model_id: str, 
                      optimize_for: str = "balanced", 
                      custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create optimized configuration for a model.
        
        Args:
            model_id: ID of the model to optimize
            optimize_for: Optimization target ("speed", "quality", "memory", "balanced")
            custom_config: Optional custom configuration parameters
            
        Returns:
            Dictionary with optimized configuration
            
        Raises:
            ModelNotFoundError: If the model is not found in the registry
        """
        # Check if model exists in registry
        model_info = self.get_model_info(model_id)
        if not model_info:
            raise ModelNotFoundError(f"Model {model_id} not found in registry")
            
        # Get model size from name
        model_name = model_info.get("name", model_id)
        model_size_billions = self.quantization_manager.get_model_size_from_name(model_name) / 1_000_000_000
        
        # Create base configuration
        opt_config = OptimizationConfig()
        
        # Apply custom config if provided
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(opt_config, key):
                    setattr(opt_config, key, value)
        
        # Optimize based on target
        if optimize_for == "speed":
            # Prioritize speed
            opt_config.quantization = "q4_0"  # Fastest but less accurate
            opt_config = self.thread_optimizer.optimize_thread_config(
                config=opt_config,
                model_size_billions=model_size_billions,
                workload_type="batch"  # Use batch mode for speed
            )
        elif optimize_for == "quality":
            # Prioritize quality
            opt_config.quantization = "q5_k" if model_size_billions < 13 else "q4_1"  # Better quality quantization
            opt_config = self.thread_optimizer.optimize_thread_config(
                config=opt_config,
                model_size_billions=model_size_billions,
                workload_type="interactive"  # Interactive mode for better quality
            )
        elif optimize_for == "memory":
            # Prioritize memory efficiency
            opt_config.quantization = "q4_0"  # Most memory efficient
            opt_config.low_vram = True
            opt_config = self.thread_optimizer.optimize_thread_config(
                config=opt_config,
                model_size_billions=model_size_billions,
                workload_type="default"
            )
        else:  # balanced
            # Balanced approach
            recommended = self.quantization_manager.recommend_quantization(
                model_params=model_size_billions * 1_000_000_000,
                max_memory_gb=self.memory_manager.memory_limit_gb
            )
            opt_config.quantization = recommended["recommended"]
            opt_config = self.thread_optimizer.optimize_thread_config(
                config=opt_config,
                model_size_billions=model_size_billions,
                workload_type="default"
            )
            
        # Apply Metal acceleration if available
        opt_config = self.metal_manager.update_optimization_config(
            config=opt_config,
            model_size_billions=model_size_billions
        )
        
        # Return the configuration
        return {
            "model_id": model_id,
            "model_size_billions": model_size_billions,
            "optimization_target": optimize_for,
            "config": opt_config.to_dict(),
            "estimated_performance": self.thread_optimizer.estimate_performance(
                thread_count=opt_config.thread_count,
                batch_size=opt_config.batch_size,
                model_size_billions=model_size_billions
            ),
            "memory_estimate": self.quantization_manager.estimate_memory_usage(
                model_params=int(model_size_billions * 1_000_000_000),
                quant_type=opt_config.quantization,
                context_length=opt_config.context_size
            )
        }
    
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