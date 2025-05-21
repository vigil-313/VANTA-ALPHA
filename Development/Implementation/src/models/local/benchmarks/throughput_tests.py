"""
Throughput benchmark tests for local model optimization.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import time
import logging
from typing import Dict, Any, Optional, List
import copy

from ..optimization import PerformanceMonitor

logger = logging.getLogger(__name__)


def run_throughput_benchmark(model_manager, 
                            model_id: str, 
                            batch_sizes: Optional[List[int]] = None,
                            performance_monitor: Optional[PerformanceMonitor] = None) -> Dict[str, Any]:
    """Run throughput benchmark with different batch sizes.
    
    Args:
        model_manager: Reference to LocalModelManager
        model_id: ID of the model to benchmark
        batch_sizes: List of batch sizes to test
        performance_monitor: Optional PerformanceMonitor instance
        
    Returns:
        Benchmark results
    """
    # Default batch sizes
    if not batch_sizes:
        batch_sizes = [64, 128, 256, 512, 1024]
        
    # Use provided performance monitor or create a new one
    monitor = performance_monitor or PerformanceMonitor(model_id)
    
    results = {
        "model_id": model_id,
        "benchmark_type": "throughput",
        "test_cases": []
    }
    
    # Use a standard prompt
    prompt = "Explain the concept of recursion in programming. Be comprehensive but concise."
    
    # Ensure model is loaded
    try:
        model_manager.load_model(model_id)
    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {e}")
        return {
            "model_id": model_id,
            "benchmark_type": "throughput",
            "error": f"Failed to load model: {e}"
        }
    
    # Get model adapter to modify batch size
    model_entry = model_manager.active_models.get(model_id)
    if not model_entry or "adapter" not in model_entry:
        return {
            "model_id": model_id,
            "benchmark_type": "throughput",
            "error": "Model adapter not found"
        }
    
    adapter = model_entry["adapter"]
    original_config = None
    
    # Test different batch sizes
    for batch_size in batch_sizes:
        try:
            logger.info(f"Testing batch size {batch_size}")
            
            # Modify adapter configuration if possible
            # Note: This approach may not work with all adapter implementations
            if hasattr(adapter, "model") and adapter.model:
                if not original_config and hasattr(adapter, "config"):
                    # Save original config for restoration
                    original_config = copy.deepcopy(adapter.config)
                
                # Try to update batch size
                if hasattr(adapter.model, "n_batch"):
                    original_batch = adapter.model.n_batch
                    adapter.model.n_batch = batch_size
                elif hasattr(adapter, "config"):
                    adapter.config["n_batch"] = batch_size
            
            # Generate with timing
            monitor.start_monitoring()
            
            start_time = time.time()
            response = model_manager.generate(
                prompt, 
                model_id=model_id, 
                params={"max_tokens": 200}
            )
            end_time = time.time()
            
            latency = end_time - start_time
            completion_tokens = response.get("usage", {}).get("completion_tokens", 0)
            tokens_per_second = completion_tokens / latency if latency > 0 else 0
            
            # Record metrics
            prompt_tokens = response.get("usage", {}).get("prompt_tokens", len(prompt.split()))
            monitor.record_inference(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency=latency
            )
            
            monitor.stop_monitoring()
            
            # Add result
            results["test_cases"].append({
                "batch_size": batch_size,
                "latency": latency,
                "tokens": completion_tokens,
                "tokens_per_second": tokens_per_second,
                "memory_gb": monitor.get_metrics().get("peak_memory_gb", 0)
            })
            
            # Restore original batch size if changed directly
            if hasattr(adapter.model, "n_batch") and "original_batch" in locals():
                adapter.model.n_batch = original_batch
            
        except Exception as e:
            logger.error(f"Error testing batch size {batch_size}: {e}")
            results["test_cases"].append({
                "batch_size": batch_size,
                "error": str(e)
            })
    
    # Restore original configuration if modified
    if original_config and hasattr(adapter, "config"):
        adapter.config = original_config
    
    # Find optimal batch size
    valid_cases = [case for case in results["test_cases"] if "error" not in case]
    if valid_cases:
        best_case = max(valid_cases, key=lambda x: x["tokens_per_second"])
        results["optimal_batch_size"] = best_case["batch_size"]
        results["optimal_tokens_per_second"] = best_case["tokens_per_second"]
    
    return results