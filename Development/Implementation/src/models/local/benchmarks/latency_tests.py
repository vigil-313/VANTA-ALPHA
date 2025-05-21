"""
Latency benchmark tests for local model optimization.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import time
import logging
from typing import Dict, Any, Optional, List

from ..optimization import PerformanceMonitor

logger = logging.getLogger(__name__)


def run_latency_benchmark(model_manager, 
                          model_id: str, 
                          prompts: Optional[List[str]] = None,
                          max_tokens: int = 100,
                          performance_monitor: Optional[PerformanceMonitor] = None) -> Dict[str, Any]:
    """Run latency benchmark using specified prompts.
    
    Args:
        model_manager: Reference to LocalModelManager
        model_id: ID of the model to benchmark
        prompts: List of test prompts
        max_tokens: Maximum tokens to generate per prompt
        performance_monitor: Optional PerformanceMonitor instance
        
    Returns:
        Benchmark results
    """
    # Default prompts
    if not prompts:
        prompts = [
            "Explain quantum computing in simple terms.",
            "What are three ways to improve productivity?",
            "Write a short poem about artificial intelligence."
        ]
        
    # Use provided performance monitor or create a new one
    monitor = performance_monitor or PerformanceMonitor(model_id)
    
    results = {
        "model_id": model_id,
        "benchmark_type": "latency",
        "max_tokens": max_tokens,
        "test_cases": []
    }
    
    # Ensure model is loaded
    try:
        model_manager.load_model(model_id)
    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {e}")
        return {
            "model_id": model_id,
            "benchmark_type": "latency",
            "error": f"Failed to load model: {e}"
        }
    
    # Run benchmark for each prompt
    monitor.start_monitoring()
    
    for i, prompt in enumerate(prompts):
        try:
            logger.info(f"Testing prompt {i+1}/{len(prompts)}")
            
            # Generate with timing
            start_time = time.time()
            response = model_manager.generate(
                prompt, 
                model_id=model_id, 
                params={"max_tokens": max_tokens}
            )
            end_time = time.time()
            
            # Calculate metrics
            latency = end_time - start_time
            output_text = response.get("text", "")
            prompt_tokens = response.get("usage", {}).get("prompt_tokens", len(prompt.split()))
            completion_tokens = response.get("usage", {}).get("completion_tokens", 0)
            tokens_per_second = completion_tokens / latency if latency > 0 else 0
            
            # Record in performance monitor
            monitor.record_inference(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency=latency
            )
            
            # Add result
            results["test_cases"].append({
                "prompt": prompt,
                "latency": latency,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens, 
                "tokens_per_second": tokens_per_second,
                "output": output_text[:100] + "..." if len(output_text) > 100 else output_text
            })
            
        except Exception as e:
            logger.error(f"Error testing prompt: {e}")
            results["test_cases"].append({
                "prompt": prompt,
                "error": str(e)
            })
    
    # Stop monitoring and add summary
    monitor.stop_monitoring()
    results["summary"] = monitor.get_metrics()
    
    return results