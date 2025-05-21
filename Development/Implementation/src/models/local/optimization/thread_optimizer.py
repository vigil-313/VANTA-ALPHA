"""
Thread optimization for local model inference.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import platform
import logging
import time
import multiprocessing
import threading
from typing import Dict, Any, Optional, List, Tuple, Union

from .optimization_config import OptimizationConfig

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil not available, some thread optimization features will be limited")
    PSUTIL_AVAILABLE = False


class ThreadOptimizer:
    """Optimizes threading configuration for local model inference."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the thread optimizer.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # System info
        self.cpu_info = self._get_cpu_info()
        self.thread_defaults = self._compute_thread_defaults()
        
        logger.debug(f"ThreadOptimizer initialized with {self.cpu_info['total_cores']} cores")
        
    def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information.
        
        Returns:
            Dictionary with CPU information
        """
        info = {
            "system": platform.system(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "total_cores": os.cpu_count() or 4,
            "logical_cores": os.cpu_count() or 4,
            "physical_cores": os.cpu_count() or 4  # Default fallback
        }
        
        # Try to get physical vs logical core count
        if PSUTIL_AVAILABLE:
            try:
                info["physical_cores"] = psutil.cpu_count(logical=False) or info["total_cores"]
                info["logical_cores"] = psutil.cpu_count(logical=True) or info["total_cores"]
            except Exception as e:
                logger.warning(f"Failed to get detailed CPU info: {e}")
        
        # Try to detect if running on Apple Silicon
        if info["system"] == "Darwin" and ("arm" in info["machine"].lower() or "apple" in info["processor"].lower()):
            info["is_apple_silicon"] = True
            # Apple Silicon has efficiency and performance cores
            # Try to identify these
            try:
                if PSUTIL_AVAILABLE:
                    # This is a heuristic - on Apple Silicon, typically half or fewer
                    # of the cores are performance cores
                    performance_cores = max(2, info["physical_cores"] // 2)
                    info["performance_cores"] = performance_cores
                    info["efficiency_cores"] = info["physical_cores"] - performance_cores
                else:
                    # Conservative guess
                    info["performance_cores"] = 2
                    info["efficiency_cores"] = max(0, info["physical_cores"] - 2)
            except Exception:
                # Default fallback
                info["performance_cores"] = 2
                info["efficiency_cores"] = max(0, info["physical_cores"] - 2)
        else:
            info["is_apple_silicon"] = False
            info["performance_cores"] = info["physical_cores"]
            info["efficiency_cores"] = 0
        
        return info
    
    def _compute_thread_defaults(self) -> Dict[str, int]:
        """Compute default thread settings.
        
        Returns:
            Dictionary with default thread settings
        """
        info = self.cpu_info
        
        # Get system load to adjust thread count
        cpu_load = 0.0
        if PSUTIL_AVAILABLE:
            try:
                cpu_load = psutil.cpu_percent(interval=0.1) / 100.0
            except Exception:
                cpu_load = 0.0
        
        # Decide based on system and load
        if info["is_apple_silicon"]:
            # Apple Silicon optimization - use performance cores by default
            performance_cores = info["performance_cores"]
            
            # Conservative setting for interactive use
            interactive_threads = max(1, performance_cores - 1)
            
            # Higher for batch processing
            batch_threads = performance_cores
            
            # Maximum for performance testing
            max_threads = info["physical_cores"]
        else:
            # For other systems, base on total physical cores but leave some free
            physical_cores = info["physical_cores"]
            
            # For interactive use, use about 75% of cores, accounting for load
            interactive_threads = max(1, int(physical_cores * 0.75 * (1 - cpu_load)))
            
            # For batch, use more cores
            batch_threads = max(1, int(physical_cores * 0.9))
            
            # Maximum for testing
            max_threads = info["logical_cores"]
        
        return {
            "interactive": interactive_threads,
            "batch": batch_threads,
            "max": max_threads,
            # Default balance of throughput vs latency
            "default": interactive_threads
        }
    
    def get_optimal_thread_count(self, 
                                workload_type: str = "default", 
                                model_size_billions: Optional[float] = None) -> int:
        """Get optimal thread count for the given workload.
        
        Args:
            workload_type: Type of workload ("interactive", "batch", "max", "default")
            model_size_billions: Optional model size in billions of parameters
            
        Returns:
            Recommended thread count
        """
        # Get basic recommendation based on workload type
        if workload_type in self.thread_defaults:
            thread_count = self.thread_defaults[workload_type]
        else:
            thread_count = self.thread_defaults["default"]
            
        # Adjust based on model size if provided
        if model_size_billions is not None:
            # Very large models benefit from more threads
            if model_size_billions >= 30:
                thread_count = max(thread_count, min(self.thread_defaults["max"], 8))
            # Large models (13B)
            elif model_size_billions >= 13:
                thread_count = max(thread_count, min(self.thread_defaults["max"], 6))
            # Medium models (7B)
            elif model_size_billions >= 7:
                # Keep the default recommendation
                pass
            # Small models may not benefit from many threads
            else:
                thread_count = min(thread_count, 4)
        
        # Ensure at least 1 thread
        return max(1, thread_count)
    
    def get_optimal_batch_size(self, 
                              thread_count: int, 
                              model_size_billions: Optional[float] = None,
                              metal_enabled: bool = False) -> int:
        """Get optimal batch size for the given configuration.
        
        Args:
            thread_count: Number of threads to use
            model_size_billions: Optional model size in billions of parameters
            metal_enabled: Whether Metal acceleration is enabled
            
        Returns:
            Recommended batch size
        """
        # Base batch size on thread count
        base_batch_size = 512
        
        # Adjust batch size based on model size
        if model_size_billions is not None:
            # Smaller batch sizes for large models
            if model_size_billions >= 30:
                base_batch_size = 256
            elif model_size_billions >= 13:
                base_batch_size = 384
                
        # Increase batch size for Metal acceleration
        if metal_enabled:
            base_batch_size = int(base_batch_size * 1.5)
            
        # Adjust batch size based on thread count
        if thread_count <= 2:
            # Small thread count, reduce batch size
            batch_size = max(64, base_batch_size // 2)
        elif thread_count <= 4:
            # Medium thread count, use base batch size
            batch_size = base_batch_size
        else:
            # Large thread count, increase batch size
            batch_size = int(base_batch_size * min(2, thread_count / 4))
            
        return batch_size
    
    def optimize_thread_config(self, 
                              config: OptimizationConfig, 
                              model_size_billions: Optional[float] = None,
                              workload_type: str = "default") -> OptimizationConfig:
        """Optimize threading configuration in the provided config.
        
        Args:
            config: OptimizationConfig to update
            model_size_billions: Optional model size in billions of parameters
            workload_type: Type of workload ("interactive", "batch", "max", "default")
            
        Returns:
            Updated configuration
        """
        # Update thread count
        config.thread_count = self.get_optimal_thread_count(
            workload_type=workload_type,
            model_size_billions=model_size_billions
        )
        
        # Update batch size
        config.batch_size = self.get_optimal_batch_size(
            thread_count=config.thread_count,
            model_size_billions=model_size_billions,
            metal_enabled=config.use_metal
        )
        
        return config
    
    def estimate_performance(self, 
                            thread_count: int, 
                            batch_size: int,
                            model_size_billions: float) -> Dict[str, Any]:
        """Estimate performance with the given configuration.
        
        Args:
            thread_count: Number of threads to use
            batch_size: Batch size for processing
            model_size_billions: Model size in billions of parameters
            
        Returns:
            Dictionary with performance estimates
        """
        # Base performance characteristics (tokens per second)
        # These are approximate and will vary by hardware
        if self.cpu_info["is_apple_silicon"]:
            # Apple Silicon base performance per core
            base_tps_per_core = 8.0  # tokens per second per core
        else:
            # Generic x86 performance
            base_tps_per_core = 5.0  # tokens per second per core
            
        # Adjust for model size
        if model_size_billions >= 30:
            size_factor = 0.3  # 30B+ models are much slower
        elif model_size_billions >= 13:
            size_factor = 0.5  # 13B models
        elif model_size_billions >= 7:
            size_factor = 0.7  # 7B models
        else:
            size_factor = 1.0  # Smaller models
            
        # Thread scaling is not linear
        if thread_count <= 2:
            thread_scaling = 1.0
        elif thread_count <= 4:
            thread_scaling = 0.9
        elif thread_count <= 8:
            thread_scaling = 0.8
        else:
            thread_scaling = 0.7
            
        # Batch size scaling
        if batch_size <= 128:
            batch_scaling = 0.8
        elif batch_size <= 256:
            batch_scaling = 0.9
        elif batch_size <= 512:
            batch_scaling = 1.0
        else:
            batch_scaling = 1.1
            
        # Calculate estimated tokens per second
        estimated_tps = (
            base_tps_per_core * 
            thread_count * 
            thread_scaling * 
            size_factor * 
            batch_scaling
        )
        
        return {
            "thread_count": thread_count,
            "batch_size": batch_size,
            "model_size_billions": model_size_billions,
            "estimated_tokens_per_second": estimated_tps,
            "estimated_latency_per_token_ms": 1000.0 / estimated_tps,
            "estimated_time_for_100_tokens_s": 100.0 / estimated_tps,
            "thread_scaling_factor": thread_scaling,
            "batch_scaling_factor": batch_scaling,
            "size_scaling_factor": size_factor
        }
    
    def benchmark_thread_configurations(self, 
                                       model_generator: Any, 
                                       test_threads: Optional[List[int]] = None, 
                                       test_batches: Optional[List[int]] = None) -> Dict[str, Any]:
        """Benchmark different thread configurations on an actual model.
        
        Args:
            model_generator: Model generator function to benchmark (llama.create_completion)
            test_threads: List of thread counts to test, or None for defaults
            test_batches: List of batch sizes to test, or None for defaults
            
        Returns:
            Dictionary with benchmark results
        """
        if model_generator is None:
            logger.warning("No model generator provided for benchmark")
            return {"error": "No model generator provided"}
            
        # Default thread counts to test
        if test_threads is None:
            test_threads = [1, 2, 4]
            if self.cpu_info["physical_cores"] > 4:
                test_threads.append(self.cpu_info["physical_cores"])
                
        # Default batch sizes to test
        if test_batches is None:
            test_batches = [128, 256, 512, 1024]
            
        results = {
            "thread_results": [],
            "batch_results": [],
            "best_thread_count": None,
            "best_batch_size": None,
            "best_tokens_per_second": 0
        }
        
        # Test prompt
        prompt = "Once upon a time in a land far away, there lived a"
        
        try:
            # Benchmark different thread counts (with default batch size)
            batch_size = 512
            best_thread_tps = 0
            best_thread = test_threads[0]
            
            for thread_count in test_threads:
                # Create completion with this thread count
                start_time = time.time()
                response = model_generator(
                    prompt=prompt,
                    max_tokens=50,
                    temperature=0.7,
                    n_threads=thread_count,
                    n_batch=batch_size
                )
                elapsed = time.time() - start_time
                
                # Get token count
                tokens = response.get("usage", {}).get("completion_tokens", 50)
                tokens_per_second = tokens / elapsed if elapsed > 0 else 0
                
                # Record result
                thread_result = {
                    "thread_count": thread_count,
                    "batch_size": batch_size,
                    "tokens_generated": tokens,
                    "time_seconds": elapsed,
                    "tokens_per_second": tokens_per_second
                }
                results["thread_results"].append(thread_result)
                
                # Update best thread count
                if tokens_per_second > best_thread_tps:
                    best_thread_tps = tokens_per_second
                    best_thread = thread_count
                    
            results["best_thread_count"] = best_thread
            
            # Benchmark different batch sizes (with best thread count)
            thread_count = best_thread
            best_batch_tps = 0
            best_batch = test_batches[0]
            
            for batch_size in test_batches:
                # Create completion with this batch size
                start_time = time.time()
                response = model_generator(
                    prompt=prompt,
                    max_tokens=50,
                    temperature=0.7,
                    n_threads=thread_count,
                    n_batch=batch_size
                )
                elapsed = time.time() - start_time
                
                # Get token count
                tokens = response.get("usage", {}).get("completion_tokens", 50)
                tokens_per_second = tokens / elapsed if elapsed > 0 else 0
                
                # Record result
                batch_result = {
                    "thread_count": thread_count,
                    "batch_size": batch_size,
                    "tokens_generated": tokens,
                    "time_seconds": elapsed,
                    "tokens_per_second": tokens_per_second
                }
                results["batch_results"].append(batch_result)
                
                # Update best batch size
                if tokens_per_second > best_batch_tps:
                    best_batch_tps = tokens_per_second
                    best_batch = batch_size
                    
            results["best_batch_size"] = best_batch
            results["best_tokens_per_second"] = best_batch_tps
            
            return results
            
        except Exception as e:
            logger.error(f"Error during thread benchmark: {e}")
            return {
                "error": str(e),
                "thread_results": results["thread_results"],
                "batch_results": results["batch_results"]
            }
    
    def print_thread_recommendations(self) -> str:
        """Generate a human-readable thread recommendation report.
        
        Returns:
            Formatted thread recommendation report
        """
        lines = [
            "Thread Optimization Recommendations",
            "==================================="
        ]
        
        # System info
        lines.extend([
            f"System: {self.cpu_info['system']} {self.cpu_info['machine']}",
            f"Processor: {self.cpu_info['processor']}",
            f"Physical cores: {self.cpu_info['physical_cores']}",
            f"Logical cores: {self.cpu_info['logical_cores']}",
            f"Apple Silicon: {self.cpu_info['is_apple_silicon']}"
        ])
        
        if self.cpu_info['is_apple_silicon']:
            lines.extend([
                f"Performance cores: ~{self.cpu_info.get('performance_cores', 'Unknown')}",
                f"Efficiency cores: ~{self.cpu_info.get('efficiency_cores', 'Unknown')}"
            ])
            
        # Thread recommendations
        lines.extend([
            "\nThread Count Recommendations:",
            f"  Interactive workloads: {self.thread_defaults['interactive']} threads",
            f"  Batch processing: {self.thread_defaults['batch']} threads",
            f"  Maximum performance: {self.thread_defaults['max']} threads",
            f"  Default setting: {self.thread_defaults['default']} threads"
        ])
        
        # Batch size recommendations
        lines.extend([
            "\nBatch Size Recommendations:",
            f"  Small models: 512-1024",
            f"  Medium models (7B): 384-512",
            f"  Large models (13B+): 256-384",
            f"  Very large models (30B+): 128-256"
        ])
        
        # Generate example configurations
        lines.append("\nExample Configurations:")
        
        for model_size in [3, 7, 13, 30]:
            for workload in ["interactive", "batch"]:
                config = OptimizationConfig()
                config = self.optimize_thread_config(
                    config=config,
                    model_size_billions=model_size,
                    workload_type=workload
                )
                
                estimate = self.estimate_performance(
                    thread_count=config.thread_count,
                    batch_size=config.batch_size,
                    model_size_billions=model_size
                )
                
                lines.append(
                    f"  {model_size}B model, {workload}: "
                    f"{config.thread_count} threads, "
                    f"{config.batch_size} batch size, "
                    f"~{estimate['estimated_tokens_per_second']:.1f} tokens/sec"
                )
                
        return "\n".join(lines)