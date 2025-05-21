"""
Memory benchmark tests for local model optimization.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import time
import logging
import gc
from typing import Dict, Any, Optional, List

from ..optimization import PerformanceMonitor

logger = logging.getLogger(__name__)

# Check if psutil is available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil not available, memory measurements will be limited")
    PSUTIL_AVAILABLE = False


def run_memory_benchmark(model_manager, 
                         model_id: str, 
                         context_sizes: Optional[List[int]] = None,
                         performance_monitor: Optional[PerformanceMonitor] = None) -> Dict[str, Any]:
    """Run memory usage benchmark with different context sizes.
    
    Args:
        model_manager: Reference to LocalModelManager
        model_id: ID of the model to benchmark
        context_sizes: List of context sizes to test
        performance_monitor: Optional PerformanceMonitor instance
        
    Returns:
        Benchmark results
    """
    # Default context sizes
    if not context_sizes:
        context_sizes = [512, 1024, 2048, 4096]
        
    # Use provided performance monitor or create a new one
    monitor = performance_monitor or PerformanceMonitor(model_id)
    
    results = {
        "model_id": model_id,
        "benchmark_type": "memory",
        "test_cases": []
    }
    
    # Ensure model is loaded
    try:
        model_manager.load_model(model_id)
    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {e}")
        return {
            "model_id": model_id,
            "benchmark_type": "memory",
            "error": f"Failed to load model: {e}"
        }
    
    # Generate a long context prompt
    base_prompt = "This is a test prompt for memory benchmarking. This sentence will be repeated to create different context lengths for testing memory usage with different context window sizes. " * 5
    
    # Run benchmark for each context size
    for context_size in context_sizes:
        try:
            logger.info(f"Testing context size {context_size}")
            
            # Force garbage collection before test
            gc.collect()
            
            # Measure memory before
            memory_before = _get_memory_usage()
            
            # Create prompt of appropriate size by repeating the base prompt
            # This is an approximation, actual token count will vary
            prompt = base_prompt
            target_length = context_size // 4  # Roughly 4 chars per token
            
            while len(prompt) < target_length:
                prompt += base_prompt
                
            # Truncate to approximately match the target context size
            prompt = prompt[:target_length]
            
            # Count actual tokens
            model = model_manager.active_models.get(model_id)
            if model and hasattr(model["adapter"], "tokenize"):
                tokens = model["adapter"].tokenize(prompt)
                actual_token_count = len(tokens)
            else:
                # Rough approximation if tokenize not available
                actual_token_count = len(prompt.split()) * 1.3
            
            # Generate with this context
            monitor.start_monitoring()
            
            start_time = time.time()
            response = model_manager.generate(
                prompt, 
                model_id=model_id, 
                params={"max_tokens": 50}
            )
            latency = time.time() - start_time
            
            monitor.stop_monitoring()
            
            # Measure memory after
            memory_after = _get_memory_usage()
            
            # Record result
            results["test_cases"].append({
                "context_size": int(actual_token_count),
                "target_size": context_size,
                "memory_before_gb": memory_before,
                "memory_after_gb": memory_after,
                "memory_delta_gb": memory_after - memory_before,
                "response_time": latency,
                "prompt_length_chars": len(prompt)
            })
            
        except Exception as e:
            logger.error(f"Error testing context size {context_size}: {e}")
            results["test_cases"].append({
                "context_size": context_size,
                "error": str(e)
            })
            
        # Short delay to allow memory to stabilize
        time.sleep(1)
        gc.collect()
    
    # Add summary
    if results["test_cases"]:
        valid_cases = [case for case in results["test_cases"] if "error" not in case]
        if valid_cases:
            memory_usage = [case["memory_after_gb"] for case in valid_cases]
            memory_deltas = [case["memory_delta_gb"] for case in valid_cases]
            
            results["summary"] = {
                "min_memory_gb": min(memory_usage) if memory_usage else 0,
                "max_memory_gb": max(memory_usage) if memory_usage else 0,
                "avg_memory_gb": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                "min_delta_gb": min(memory_deltas) if memory_deltas else 0,
                "max_delta_gb": max(memory_deltas) if memory_deltas else 0,
                "avg_delta_gb": sum(memory_deltas) / len(memory_deltas) if memory_deltas else 0
            }
    
    return results


def _get_memory_usage() -> float:
    """Get current memory usage in GB.
    
    Returns:
        Current memory usage in GB
    """
    if PSUTIL_AVAILABLE:
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024 * 1024)  # Convert bytes to GB
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 0.0
    else:
        # Fallback to basic memory info
        return 0.0  # Unable to get memory usage