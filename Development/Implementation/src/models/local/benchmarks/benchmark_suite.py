"""
Benchmark suite for local model optimization.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Callable

from ..optimization import (
    OptimizationConfig,
    PerformanceMonitor,
    QuantizationManager,
    MetalAccelerationManager,
    MemoryManager,
    ThreadOptimizer
)

from .latency_tests import run_latency_benchmark
from .memory_tests import run_memory_benchmark
from .throughput_tests import run_throughput_benchmark

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Runs standardized benchmarks against model configurations."""
    
    def __init__(self, model_manager, test_prompts=None):
        """
        Initialize benchmark runner.
        
        Args:
            model_manager: Reference to LocalModelManager
            test_prompts: Optional list of test prompts
        """
        self.model_manager = model_manager
        self.test_prompts = test_prompts or self._default_test_prompts()
        self.performance_monitor = PerformanceMonitor()
        self.quantization_manager = QuantizationManager()
        self.metal_manager = MetalAccelerationManager()
        self.thread_optimizer = ThreadOptimizer()
        
    def _default_test_prompts(self) -> List[str]:
        """Get default test prompts.
        
        Returns:
            List of standard test prompts
        """
        return [
            "Explain quantum computing in simple terms.",
            "What are three ways to improve productivity?",
            "Write a short poem about artificial intelligence.",
            "Summarize the history of space exploration.",
            "How do you make a perfect omelette?"
        ]
        
    def run_latency_benchmark(self, 
                              model_id: str, 
                              prompts: Optional[List[str]] = None,
                              max_tokens: int = 100) -> Dict[str, Any]:
        """Run latency benchmark using specified prompts.
        
        Args:
            model_id: ID of the model to benchmark
            prompts: Optional list of test prompts
            max_tokens: Maximum tokens to generate per prompt
            
        Returns:
            Benchmark results
        """
        return run_latency_benchmark(
            model_manager=self.model_manager,
            model_id=model_id,
            prompts=prompts or self.test_prompts[:3],  # Limit to 3 for brevity
            max_tokens=max_tokens,
            performance_monitor=self.performance_monitor
        )
        
    def run_memory_benchmark(self, 
                             model_id: str, 
                             context_sizes: Optional[List[int]] = None) -> Dict[str, Any]:
        """Run memory usage benchmark with different context sizes.
        
        Args:
            model_id: ID of the model to benchmark
            context_sizes: List of context sizes to test
            
        Returns:
            Benchmark results
        """
        return run_memory_benchmark(
            model_manager=self.model_manager,
            model_id=model_id,
            context_sizes=context_sizes or [512, 1024, 2048, 4096],
            performance_monitor=self.performance_monitor
        )
        
    def run_throughput_benchmark(self, 
                                model_id: str, 
                                batch_sizes: Optional[List[int]] = None) -> Dict[str, Any]:
        """Run throughput benchmark with different batch sizes.
        
        Args:
            model_id: ID of the model to benchmark
            batch_sizes: List of batch sizes to test
            
        Returns:
            Benchmark results
        """
        return run_throughput_benchmark(
            model_manager=self.model_manager,
            model_id=model_id,
            batch_sizes=batch_sizes or [128, 256, 512, 1024],
            performance_monitor=self.performance_monitor
        )
        
    def compare_configurations(self, 
                               model_id: str, 
                               configs: List[OptimizationConfig]) -> Dict[str, Any]:
        """Compare different optimization configurations.
        
        Args:
            model_id: Base model ID to test
            configs: List of OptimizationConfig objects
            
        Returns:
            Comparison results
        """
        results = {
            "model_id": model_id,
            "benchmark_type": "configuration_comparison",
            "configurations": [],
            "test_cases": []
        }
        
        # Use a standard prompt set
        prompts = self.test_prompts[:2]  # Limit to 2 prompts for brevity
        
        # Get model size for more accurate reporting
        model_info = self.model_manager.get_model_info(model_id)
        model_name = model_info.get("name", model_id) if model_info else model_id
        model_size_billions = self.quantization_manager.get_model_size_from_name(model_name) / 1_000_000_000
        
        # Test each configuration
        for i, config in enumerate(configs):
            config_name = f"Config {i+1}: {config.quantization}, metal={config.use_metal}, threads={config.thread_count}"
            results["configurations"].append({
                "name": config_name,
                "config": config.to_dict()
            })
            
            # Load model with this configuration
            try:
                self.model_manager.load_model(model_id, config=config.to_dict())
                model_loaded = True
            except Exception as e:
                logger.error(f"Failed to load model with configuration: {e}")
                results["test_cases"].append({
                    "config_name": config_name,
                    "error": f"Failed to load model with configuration: {e}"
                })
                model_loaded = False
                
            if not model_loaded:
                continue
                
            # Run benchmark
            self.performance_monitor.reset_metrics()
            self.performance_monitor.start_monitoring()
            
            config_results = {
                "config_name": config_name,
                "prompts": []
            }
            
            # Test with each prompt
            for prompt in prompts:
                try:
                    # Generate with this configuration
                    start_time = time.time()
                    response = self.model_manager.generate(prompt, model_id=model_id, params={"max_tokens": 100})
                    end_time = time.time()
                    
                    # Calculate metrics
                    latency = end_time - start_time
                    output_text = response.get("text", "")
                    output_tokens = response.get("usage", {}).get("completion_tokens", 0)
                    
                    # Record metrics
                    prompt_tokens = response.get("usage", {}).get("prompt_tokens", len(prompt.split()))
                    self.performance_monitor.record_inference(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=output_tokens,
                        latency=latency
                    )
                    
                    # Record prompt result
                    config_results["prompts"].append({
                        "prompt": prompt,
                        "latency": latency,
                        "tokens": output_tokens,
                        "tokens_per_second": output_tokens / latency if latency > 0 else 0
                    })
                    
                except Exception as e:
                    logger.error(f"Error testing prompt with configuration: {e}")
                    config_results["prompts"].append({
                        "prompt": prompt,
                        "error": str(e)
                    })
                    
            self.performance_monitor.stop_monitoring()
            config_results["metrics"] = self.performance_monitor.get_metrics()
            
            # Add expected metrics based on model size
            expected_metrics = self.thread_optimizer.estimate_performance(
                thread_count=config.thread_count,
                batch_size=config.batch_size,
                model_size_billions=model_size_billions
            )
            config_results["expected_metrics"] = expected_metrics
            
            results["test_cases"].append(config_results)
            
            # Unload model after testing
            self.model_manager.unload_model(model_id)
            
        return results
        
    def run_comprehensive_benchmark(self, model_id: str) -> Dict[str, Any]:
        """Run a comprehensive benchmark suite on a model.
        
        Args:
            model_id: ID of the model to benchmark
            
        Returns:
            Comprehensive benchmark results
        """
        benchmark_start = time.time()
        
        # Get model info
        model_info = self.model_manager.get_model_info(model_id)
        model_name = model_info.get("name", model_id) if model_info else model_id
        model_size_billions = self.quantization_manager.get_model_size_from_name(model_name) / 1_000_000_000
        
        # Create results container
        results = {
            "model_id": model_id,
            "model_name": model_name,
            "model_size_billions": model_size_billions,
            "benchmark_type": "comprehensive",
            "timestamp": time.time(),
            "system_info": self._get_system_info(),
            "tests": {}
        }
        
        # 1. Generate optimal configurations
        configs = self._generate_test_configurations(model_size_billions)
        
        # 2. Latency test with default config
        logger.info(f"Running latency benchmark for {model_id}")
        default_config = configs[0]  # First config is the default
        try:
            self.model_manager.load_model(model_id, config=default_config.to_dict())
            latency_results = self.run_latency_benchmark(model_id)
            results["tests"]["latency"] = latency_results
            self.model_manager.unload_model(model_id)
        except Exception as e:
            logger.error(f"Error in latency test: {e}")
            results["tests"]["latency"] = {"error": str(e)}
            
        # 3. Memory test
        logger.info(f"Running memory benchmark for {model_id}")
        try:
            self.model_manager.load_model(model_id, config=default_config.to_dict())
            memory_results = self.run_memory_benchmark(model_id)
            results["tests"]["memory"] = memory_results
            self.model_manager.unload_model(model_id)
        except Exception as e:
            logger.error(f"Error in memory test: {e}")
            results["tests"]["memory"] = {"error": str(e)}
            
        # 4. Throughput test
        logger.info(f"Running throughput benchmark for {model_id}")
        try:
            self.model_manager.load_model(model_id, config=default_config.to_dict())
            throughput_results = self.run_throughput_benchmark(model_id)
            results["tests"]["throughput"] = throughput_results
            self.model_manager.unload_model(model_id)
        except Exception as e:
            logger.error(f"Error in throughput test: {e}")
            results["tests"]["throughput"] = {"error": str(e)}
            
        # 5. Configuration comparison (limited configurations for efficiency)
        logger.info(f"Running configuration comparison for {model_id}")
        try:
            # Limit to 3 configurations for efficiency
            comparison_configs = configs[:min(3, len(configs))]
            comparison_results = self.compare_configurations(model_id, comparison_configs)
            results["tests"]["configurations"] = comparison_results
        except Exception as e:
            logger.error(f"Error in configuration comparison: {e}")
            results["tests"]["configurations"] = {"error": str(e)}
            
        # Calculate total benchmark time
        benchmark_end = time.time()
        results["benchmark_duration"] = benchmark_end - benchmark_start
        
        return results
        
    def _generate_test_configurations(self, model_size_billions: float) -> List[OptimizationConfig]:
        """Generate test configurations for benchmarking.
        
        Args:
            model_size_billions: Model size in billions of parameters
            
        Returns:
            List of OptimizationConfig objects for testing
        """
        configs = []
        
        # 1. Default optimized configuration
        default_config = OptimizationConfig()
        default_config = self.thread_optimizer.optimize_thread_config(
            config=default_config,
            model_size_billions=model_size_billions,
            workload_type="default"
        )
        default_config = self.metal_manager.update_optimization_config(
            config=default_config,
            model_size_billions=model_size_billions
        )
        configs.append(default_config)
        
        # 2. Faster configuration (prioritize speed)
        fast_config = OptimizationConfig(quantization="q4_0")
        fast_config = self.thread_optimizer.optimize_thread_config(
            config=fast_config,
            model_size_billions=model_size_billions,
            workload_type="batch"
        )
        fast_config.use_metal = default_config.use_metal
        configs.append(fast_config)
        
        # 3. Quality configuration
        if model_size_billions < 13:
            # Only add higher quality for smaller models
            quality_config = OptimizationConfig(quantization="q5_k")
            quality_config = self.thread_optimizer.optimize_thread_config(
                config=quality_config,
                model_size_billions=model_size_billions,
                workload_type="interactive"
            )
            quality_config.use_metal = default_config.use_metal
            configs.append(quality_config)
            
        # 4. CPU-only configuration (for comparison)
        cpu_config = OptimizationConfig(
            quantization="q4_0",
            use_metal=False,
            n_gpu_layers=0
        )
        cpu_config = self.thread_optimizer.optimize_thread_config(
            config=cpu_config,
            model_size_billions=model_size_billions,
            workload_type="batch"  # Use batch mode for CPU to maximize performance
        )
        configs.append(cpu_config)
        
        return configs
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for benchmark context.
        
        Returns:
            Dictionary with system information
        """
        import platform
        
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count()
        }
        
        # Get more detailed GPU/Metal info if available
        if self.metal_manager.is_metal_available():
            info["metal_available"] = True
            info["metal_devices"] = self.metal_manager.get_devices()
        else:
            info["metal_available"] = False
            
        return info
        
    def export_results(self, results: Dict[str, Any], format: str = "json") -> str:
        """Export benchmark results.
        
        Args:
            results: Benchmark results
            format: Output format ("json", "text")
            
        Returns:
            Formatted results
        """
        if format == "json":
            return json.dumps(results, indent=2)
            
        elif format == "text":
            lines = [
                f"Benchmark Results: {results.get('benchmark_type', 'unknown')}",
                "=======================================",
                f"Model: {results.get('model_id', 'unknown')}",
                f"Size: {results.get('model_size_billions', 'unknown')}B parameters",
                ""
            ]
            
            # Add system info
            if "system_info" in results:
                lines.append("System Information:")
                for key, value in results["system_info"].items():
                    if key != "metal_devices":  # Skip detailed device info
                        lines.append(f"  {key}: {value}")
                lines.append("")
                
            # Add test results summaries
            if "tests" in results:
                tests = results["tests"]
                
                # Latency summary
                if "latency" in tests:
                    latency = tests["latency"]
                    if "summary" in latency:
                        summary = latency["summary"]
                        lines.append("Latency Test Summary:")
                        lines.append(f"  Average latency: {summary.get('avg_latency', 0):.4f}s")
                        lines.append(f"  Tokens per second: {summary.get('avg_tokens_per_second', 0):.2f}")
                        lines.append("")
                        
                # Throughput summary
                if "throughput" in tests:
                    throughput = tests["throughput"]
                    if "test_cases" in throughput:
                        lines.append("Throughput Test Summary:")
                        for case in throughput["test_cases"]:
                            lines.append(f"  Batch size {case.get('batch_size')}: {case.get('tokens_per_second', 0):.2f} tokens/sec")
                        lines.append("")
                        
                # Memory summary
                if "memory" in tests:
                    memory = tests["memory"]
                    if "test_cases" in memory:
                        lines.append("Memory Test Summary:")
                        for case in memory["test_cases"]:
                            lines.append(f"  Context size {case.get('context_size')}: {case.get('memory_after_gb', 0):.2f} GB")
                        lines.append("")
                        
                # Configuration comparison
                if "configurations" in tests:
                    configs = tests["configurations"]
                    if "test_cases" in configs:
                        lines.append("Configuration Comparison:")
                        for test_case in configs["test_cases"]:
                            metrics = test_case.get("metrics", {})
                            lines.append(f"  {test_case.get('config_name', 'Unknown')}:")
                            lines.append(f"    Tokens/sec: {metrics.get('avg_tokens_per_second', 0):.2f}")
                            lines.append(f"    Avg latency: {metrics.get('avg_latency', 0):.4f}s")
                            lines.append(f"    Peak memory: {metrics.get('peak_memory_gb', 0):.2f} GB")
                        lines.append("")
                            
            # Add benchmark duration
            if "benchmark_duration" in results:
                duration = results["benchmark_duration"]
                lines.append(f"Total benchmark duration: {duration:.2f} seconds")
                
            return "\n".join(lines)
            
        else:
            logger.warning(f"Unsupported format '{format}', defaulting to JSON")
            return json.dumps(results, indent=2)
        
    def save_benchmark_results(self, results: Dict[str, Any], file_path: str) -> bool:
        """Save benchmark results to a file.
        
        Args:
            results: Benchmark results
            file_path: Path to save results to
            
        Returns:
            True if saved successfully
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Determine format from file extension
            format = "json" if file_path.endswith(".json") else "text"
            
            # Export results
            output = self.export_results(results, format=format)
            
            # Write to file
            with open(file_path, "w") as f:
                f.write(output)
                
            logger.info(f"Benchmark results saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save benchmark results: {e}")
            return False