# LM_002: Local Model Optimization Prompt

## Task Metadata
- Task ID: LM_002
- Component: Local Model Optimization
- Phase: 1 (Core Components)
- Priority: High
- Estimated Effort: 2 days
- Prerequisites: 
  - LM_001 (Local Model Integration) - In Progress

## Task Overview

Optimize the Local Model integration for VANTA to achieve maximum performance on target hardware, particularly focusing on macOS Metal acceleration, model quantization, and memory efficiency. This task ensures that local model inference meets latency targets while staying within memory constraints, which is critical for the dual-track processing architecture.

## Success Criteria

1. Model quantization is correctly applied with various precision options
2. Metal acceleration is properly configured and utilized on macOS
3. Memory usage is optimized and stays below defined thresholds
4. Inference speed meets or exceeds targets (<1.5s for simple queries)
5. Performance benchmarks provide clear metrics for various configurations
6. System scales gracefully across different hardware profiles

## Implementation Details

### Requirements

1. **Model Quantization**
   - Implement support for multiple quantization levels (F16, Q4_0, Q4_1, Q5_K, Q8_0)
   - Create configuration options for selecting quantization type
   - Develop utilities for comparing quantization quality vs. performance
   - Add documentation on quantization tradeoffs
   - Support runtime selection of precision based on hardware capabilities

2. **Metal Acceleration**
   - Configure llama.cpp for Metal Performance Shaders (MPS) on macOS
   - Optimize thread count and batch size for Metal execution
   - Implement fallback to CPU when Metal is unavailable
   - Add performance monitoring for GPU utilization
   - Ensure proper resource cleanup for GPU resources

3. **Memory Optimization**
   - Implement efficient memory mapping for model weights
   - Optimize context management to reduce memory fragmentation
   - Add memory usage monitoring and reporting
   - Implement graceful degradation under memory pressure
   - Create configurable memory limits

4. **Thread Management**
   - Optimize thread count based on available cores
   - Implement thread affinity options
   - Add batch processing for higher throughput
   - Create thread pool for handling multiple requests
   - Monitor and report thread utilization

5. **Benchmark Suite**
   - Create comprehensive benchmarking tools
   - Measure and report inference latency
   - Track memory usage profiles
   - Compare different optimization configurations
   - Generate performance reports

### Architecture

The optimization enhancements should maintain the existing architecture while adding:

```python
# Enhanced Interfaces
class OptimizationConfig:
    """Configuration for model optimization options."""
    def __init__(self, 
                 quantization="q4_0", 
                 use_metal=True, 
                 thread_count=4, 
                 batch_size=512,
                 memory_limit_gb=8): pass
    def validate(self): pass
    def to_dict(self): pass
    @classmethod
    def from_dict(cls, config_dict): pass

class PerformanceMonitor:
    """Monitors and reports on model performance."""
    def start_monitoring(self): pass
    def stop_monitoring(self): pass
    def record_inference(self, tokens, latency): pass
    def get_metrics(self): pass
    def reset_metrics(self): pass
    def export_report(self, format="json"): pass

class BenchmarkRunner:
    """Runs standardized benchmarks against model configurations."""
    def run_latency_benchmark(self, model_id, prompts): pass
    def run_memory_benchmark(self, model_id, context_sizes): pass
    def run_throughput_benchmark(self, model_id, batch_sizes): pass
    def compare_configurations(self, model_id, configs): pass
    def export_results(self, format="json"): pass
```

### Component Design

1. **Quantization Manager**
   - Selection of quantization schemes
   - Quality vs. performance tradeoff utilities
   - Conversion between quantization formats
   - Automated testing of quantization accuracy

2. **Metal Acceleration Manager**
   - GPU feature detection
   - Metal configuration optimization
   - Resource allocation and deallocation
   - Error handling for GPU operations

3. **Memory Manager**
   - Memory usage tracking
   - Garbage collection optimization
   - Resource constraint enforcement
   - Memory map optimization

4. **Thread Optimizer**
   - CPU core detection and thread allocation
   - Workload distribution
   - Batch size optimization
   - Thread pool management

5. **Benchmark System**
   - Standardized test suites
   - Performance measurement utilities
   - Comparison and reporting tools
   - Hardware profile detection

### Implementation Approach

1. **Phase 1: Quantization Implementation**
   - Add support for multiple quantization formats
   - Create configuration options for quantization
   - Test accuracy and performance tradeoffs
   - Document quantization options

2. **Phase 2: Metal Acceleration**
   - Configure Metal backend for llama.cpp
   - Optimize Metal performance parameters
   - Implement detection and fallback mechanisms
   - Test across different macOS hardware

3. **Phase 3: Memory Optimization**
   - Profile memory usage during inference
   - Implement memory usage constraints
   - Optimize context management
   - Test with different model sizes

4. **Phase 4: Thread Management**
   - Optimize thread count configuration
   - Implement batch processing
   - Create thread pool
   - Test under various load conditions

5. **Phase 5: Benchmarking and Validation**
   - Create comprehensive benchmark suite
   - Measure optimization improvements
   - Document performance characteristics
   - Generate optimization recommendations

## Technical Details

### Directory Structure

```
/src/models/
  local/
    __init__.py                    # Package initialization
    optimization/
      __init__.py                  # Optimization subpackage
      quantization.py              # Quantization utilities
      metal_config.py              # Metal acceleration configuration
      memory_manager.py            # Memory optimization
      thread_optimizer.py          # Thread management
      performance_monitor.py       # Performance tracking
    benchmarks/
      __init__.py                  # Benchmark subpackage
      latency_tests.py             # Latency benchmarks
      memory_tests.py              # Memory usage benchmarks
      throughput_tests.py          # Throughput benchmarks
      benchmark_suite.py           # Complete benchmark suite
      test_prompts.py              # Standard test prompts
```

### Core Classes

```python
# Optimization Configuration
class OptimizationConfig:
    """Configuration for model optimization options."""
    
    QUANT_OPTIONS = ["f16", "q4_0", "q4_1", "q5_k", "q8_0"]
    
    def __init__(self, 
                 quantization="q4_0", 
                 use_metal=True, 
                 thread_count=4, 
                 batch_size=512,
                 memory_limit_gb=8):
        """Initialize optimization configuration.
        
        Args:
            quantization: Quantization format (f16, q4_0, q4_1, q5_k, q8_0)
            use_metal: Whether to use Metal acceleration on macOS
            thread_count: Number of CPU threads for inference
            batch_size: Batch size for processing
            memory_limit_gb: Maximum memory usage in GB
        """
        self.quantization = quantization
        self.use_metal = use_metal
        self.thread_count = thread_count
        self.batch_size = batch_size
        self.memory_limit_gb = memory_limit_gb
        
    def validate(self):
        """Validate the configuration settings."""
        if self.quantization not in self.QUANT_OPTIONS:
            raise ValueError(f"Invalid quantization: {self.quantization}")
            
        if self.thread_count < 1:
            raise ValueError(f"Thread count must be at least 1")
            
        if self.batch_size < 32:
            raise ValueError(f"Batch size must be at least 32")
            
        if self.memory_limit_gb < 1 or self.memory_limit_gb > 64:
            raise ValueError(f"Memory limit must be between 1-64 GB")
            
        return True
        
    def to_dict(self):
        """Convert configuration to dictionary."""
        return {
            "quantization": self.quantization,
            "use_metal": self.use_metal,
            "thread_count": self.thread_count,
            "batch_size": self.batch_size,
            "memory_limit_gb": self.memory_limit_gb
        }
        
    @classmethod
    def from_dict(cls, config_dict):
        """Create configuration from dictionary."""
        return cls(
            quantization=config_dict.get("quantization", "q4_0"),
            use_metal=config_dict.get("use_metal", True),
            thread_count=config_dict.get("thread_count", 4),
            batch_size=config_dict.get("batch_size", 512),
            memory_limit_gb=config_dict.get("memory_limit_gb", 8)
        )
        
    def get_llama_params(self):
        """Get parameters for llama.cpp initialization."""
        params = {}
        
        # Quantization mapping to llama.cpp params
        if self.quantization == "f16":
            params["f16_kv"] = True
        
        # Metal configuration
        if self.use_metal:
            params["n_gpu_layers"] = 32  # Number of layers to offload to GPU
            
        # CPU thread configuration
        params["n_threads"] = self.thread_count
        params["n_batch"] = self.batch_size
        
        return params
```

```python
# Performance Monitoring
class PerformanceMonitor:
    """Monitors and reports on model performance."""
    
    def __init__(self):
        """Initialize the performance monitor."""
        self.metrics = {
            "inference_count": 0,
            "total_tokens": 0,
            "total_latency": 0,
            "max_latency": 0,
            "min_latency": float('inf'),
            "start_time": None,
            "end_time": None,
            "peak_memory": 0,
            "current_memory": 0
        }
        self.is_monitoring = False
        
    def start_monitoring(self):
        """Begin collecting performance metrics."""
        import time
        import psutil
        
        self.metrics["start_time"] = time.time()
        self.is_monitoring = True
        self.reset_metrics()
        
    def stop_monitoring(self):
        """Stop collecting performance metrics."""
        import time
        
        if self.is_monitoring:
            self.metrics["end_time"] = time.time()
            self.is_monitoring = False
            
    def record_inference(self, tokens, latency):
        """Record a single inference operation.
        
        Args:
            tokens: Number of tokens generated
            latency: Time taken in seconds
        """
        if not self.is_monitoring:
            return
            
        self.metrics["inference_count"] += 1
        self.metrics["total_tokens"] += tokens
        self.metrics["total_latency"] += latency
        self.metrics["max_latency"] = max(self.metrics["max_latency"], latency)
        self.metrics["min_latency"] = min(self.metrics["min_latency"], latency)
        
        # Update memory usage
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        current_memory = memory_info.rss / (1024 * 1024 * 1024)  # GB
        
        self.metrics["current_memory"] = current_memory
        self.metrics["peak_memory"] = max(self.metrics["peak_memory"], current_memory)
        
    def get_metrics(self):
        """Get current performance metrics."""
        metrics = self.metrics.copy()
        
        # Calculate derived metrics
        if metrics["inference_count"] > 0:
            metrics["avg_latency"] = metrics["total_latency"] / metrics["inference_count"]
            metrics["tokens_per_second"] = metrics["total_tokens"] / metrics["total_latency"]
            
        if metrics["start_time"] and metrics["end_time"]:
            metrics["duration"] = metrics["end_time"] - metrics["start_time"]
            
        return metrics
        
    def reset_metrics(self):
        """Reset all metrics."""
        import time
        
        self.metrics = {
            "inference_count": 0,
            "total_tokens": 0,
            "total_latency": 0,
            "max_latency": 0,
            "min_latency": float('inf'),
            "start_time": time.time() if self.is_monitoring else None,
            "end_time": None,
            "peak_memory": 0,
            "current_memory": 0
        }
        
    def export_report(self, format="json"):
        """Export a performance report.
        
        Args:
            format: Output format ("json", "text")
            
        Returns:
            Formatted performance report
        """
        metrics = self.get_metrics()
        
        if format == "json":
            import json
            return json.dumps(metrics, indent=2)
            
        elif format == "text":
            lines = [
                "Performance Report",
                "=================",
                f"Inferences: {metrics['inference_count']}",
                f"Total tokens: {metrics['total_tokens']}",
                f"Tokens per second: {metrics.get('tokens_per_second', 0):.2f}",
                f"Average latency: {metrics.get('avg_latency', 0):.4f}s",
                f"Min/Max latency: {metrics['min_latency']:.4f}s / {metrics['max_latency']:.4f}s",
                f"Peak memory usage: {metrics['peak_memory']:.2f} GB",
                f"Duration: {metrics.get('duration', 0):.2f}s"
            ]
            return "\n".join(lines)
            
        return None
```

```python
# Benchmark Suite
class BenchmarkRunner:
    """Runs standardized benchmarks against model configurations."""
    
    def __init__(self, model_manager, test_prompts=None):
        """Initialize benchmark runner.
        
        Args:
            model_manager: Reference to LocalModelManager
            test_prompts: Optional list of test prompts
        """
        self.model_manager = model_manager
        self.test_prompts = test_prompts or self._default_test_prompts()
        self.performance_monitor = PerformanceMonitor()
        
    def _default_test_prompts(self):
        """Get default test prompts."""
        return [
            "Explain quantum computing in simple terms.",
            "What are three ways to improve productivity?",
            "Write a short poem about artificial intelligence.",
            "Summarize the history of space exploration.",
            "How do you make a perfect omelette?"
        ]
        
    def run_latency_benchmark(self, model_id, prompts=None):
        """Run latency benchmark using specified prompts.
        
        Args:
            model_id: ID of the model to benchmark
            prompts: Optional list of test prompts
            
        Returns:
            Benchmark results
        """
        prompts = prompts or self.test_prompts
        results = {
            "model_id": model_id,
            "benchmark_type": "latency",
            "test_cases": []
        }
        
        # Ensure model is loaded
        self.model_manager.load_model(model_id)
        model = self.model_manager.active_models.get(model_id)
        
        if not model:
            raise ValueError(f"Model {model_id} could not be loaded")
            
        # Run benchmark for each prompt
        self.performance_monitor.start_monitoring()
        
        for i, prompt in enumerate(prompts):
            import time
            
            start_time = time.time()
            response = model.generate(prompt, {"max_tokens": 100})
            end_time = time.time()
            
            latency = end_time - start_time
            output_tokens = len(model.tokenize(response)) if response else 0
            
            self.performance_monitor.record_inference(output_tokens, latency)
            
            results["test_cases"].append({
                "prompt": prompt,
                "latency": latency,
                "tokens": output_tokens,
                "tokens_per_second": output_tokens / latency if latency > 0 else 0
            })
            
        self.performance_monitor.stop_monitoring()
        results["summary"] = self.performance_monitor.get_metrics()
        
        return results
        
    def run_memory_benchmark(self, model_id, context_sizes=None):
        """Run memory usage benchmark with different context sizes.
        
        Args:
            model_id: ID of the model to benchmark
            context_sizes: List of context sizes to test
            
        Returns:
            Benchmark results
        """
        context_sizes = context_sizes or [512, 1024, 2048, 4096, 8192]
        results = {
            "model_id": model_id,
            "benchmark_type": "memory",
            "test_cases": []
        }
        
        # Generate a long context prompt by repeating
        base_prompt = "This is a test prompt for memory benchmarking. " * 10
        
        # Ensure model is loaded
        self.model_manager.load_model(model_id)
        model = self.model_manager.active_models.get(model_id)
        
        if not model:
            raise ValueError(f"Model {model_id} could not be loaded")
            
        # Test with different context sizes
        import psutil
        process = psutil.Process()
        
        for context_size in context_sizes:
            # Create prompt of appropriate size
            tokens_needed = context_size
            prompt = base_prompt
            
            while len(model.tokenize(prompt)) < tokens_needed:
                prompt += base_prompt
                
            prompt = prompt[:tokens_needed * 4]  # Approximate truncation
            token_count = len(model.tokenize(prompt))
            
            # Measure memory before
            memory_before = process.memory_info().rss / (1024 * 1024 * 1024)  # GB
            
            # Generate with this context
            response = model.generate(prompt, {"max_tokens": 50})
            
            # Measure memory after
            memory_after = process.memory_info().rss / (1024 * 1024 * 1024)  # GB
            
            results["test_cases"].append({
                "context_size": token_count,
                "memory_before_gb": memory_before,
                "memory_after_gb": memory_after,
                "memory_delta_gb": memory_after - memory_before
            })
            
        return results
        
    def run_throughput_benchmark(self, model_id, batch_sizes=None):
        """Run throughput benchmark with different batch sizes.
        
        Args:
            model_id: ID of the model to benchmark
            batch_sizes: List of batch sizes to test
            
        Returns:
            Benchmark results
        """
        batch_sizes = batch_sizes or [32, 64, 128, 256, 512, 1024]
        results = {
            "model_id": model_id,
            "benchmark_type": "throughput",
            "test_cases": []
        }
        
        # Use a standard prompt
        prompt = "Explain the concept of recursion in programming."
        
        # Ensure model is loaded
        self.model_manager.load_model(model_id)
        model = self.model_manager.active_models.get(model_id)
        
        if not model:
            raise ValueError(f"Model {model_id} could not be loaded")
            
        # Test with different batch sizes
        for batch_size in batch_sizes:
            # Configure model with this batch size
            original_config = model.config.copy()
            model.config["batch_size"] = batch_size
            
            # Run benchmark
            import time
            
            start_time = time.time()
            response = model.generate(prompt, {"max_tokens": 200})
            end_time = time.time()
            
            latency = end_time - start_time
            output_tokens = len(model.tokenize(response)) if response else 0
            
            results["test_cases"].append({
                "batch_size": batch_size,
                "latency": latency,
                "tokens": output_tokens,
                "tokens_per_second": output_tokens / latency if latency > 0 else 0
            })
            
            # Restore original configuration
            model.config = original_config
            
        return results
        
    def compare_configurations(self, model_id, configs):
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
        prompts = self.test_prompts[:3]  # Limit to 3 prompts for brevity
        
        # Test each configuration
        for i, config in enumerate(configs):
            config_name = f"Config {i+1}: {config.quantization}, metal={config.use_metal}, threads={config.thread_count}"
            results["configurations"].append({
                "name": config_name,
                "config": config.to_dict()
            })
            
            # Load model with this configuration
            self.model_manager.load_model(model_id, config=config.to_dict())
            model = self.model_manager.active_models.get(model_id)
            
            if not model:
                results["test_cases"].append({
                    "config_name": config_name,
                    "error": f"Failed to load model with configuration"
                })
                continue
                
            # Run benchmark
            self.performance_monitor.reset_metrics()
            self.performance_monitor.start_monitoring()
            
            config_results = {
                "config_name": config_name,
                "prompts": []
            }
            
            for prompt in prompts:
                import time
                
                start_time = time.time()
                response = model.generate(prompt, {"max_tokens": 100})
                end_time = time.time()
                
                latency = end_time - start_time
                output_tokens = len(model.tokenize(response)) if response else 0
                
                self.performance_monitor.record_inference(output_tokens, latency)
                
                config_results["prompts"].append({
                    "prompt": prompt,
                    "latency": latency,
                    "tokens": output_tokens,
                    "tokens_per_second": output_tokens / latency if latency > 0 else 0
                })
                
            self.performance_monitor.stop_monitoring()
            config_results["metrics"] = self.performance_monitor.get_metrics()
            
            results["test_cases"].append(config_results)
            
            # Unload model after testing
            self.model_manager.unload_model(model_id)
            
        return results
        
    def export_results(self, results, format="json"):
        """Export benchmark results.
        
        Args:
            results: Benchmark results
            format: Output format ("json", "text")
            
        Returns:
            Formatted results
        """
        if format == "json":
            import json
            return json.dumps(results, indent=2)
            
        elif format == "text":
            lines = [
                f"Benchmark Results: {results['benchmark_type']}",
                "======================================",
                f"Model: {results['model_id']}",
                ""
            ]
            
            if results["benchmark_type"] == "configuration_comparison":
                lines.append("Configuration Comparison:")
                for config in results["configurations"]:
                    lines.append(f"- {config['name']}")
                
                lines.append("\nPerformance Summary:")
                for test_case in results["test_cases"]:
                    metrics = test_case.get("metrics", {})
                    lines.append(f"- {test_case['config_name']}:")
                    lines.append(f"  - Avg. Latency: {metrics.get('avg_latency', 0):.4f}s")
                    lines.append(f"  - Tokens/sec: {metrics.get('tokens_per_second', 0):.2f}")
                    lines.append(f"  - Peak Memory: {metrics.get('peak_memory', 0):.2f} GB")
            else:
                for i, test_case in enumerate(results["test_cases"]):
                    lines.append(f"Test Case {i+1}:")
                    for key, value in test_case.items():
                        if key != "prompt":
                            lines.append(f"  - {key}: {value}")
                    lines.append("")
                
                if "summary" in results:
                    lines.append("Summary:")
                    for key, value in results["summary"].items():
                        lines.append(f"  - {key}: {value}")
            
            return "\n".join(lines)
            
        return None
```

## Testing Requirements

Create comprehensive tests for Local Model optimization:

1. **Unit Tests**
   - Test optimization configuration handling
   - Test Metal detection and setup
   - Test memory management utilities
   - Test threading configuration
   - Test performance monitoring

2. **Integration Tests**
   - Test model loading with different optimization settings
   - Test generation with Metal acceleration
   - Test memory limits enforcement
   - Test thread count configuration effects

3. **Performance Tests**
   - Benchmark suite for standardized testing
   - Quantization comparison tests
   - Thread scaling tests
   - Metal vs. CPU comparison
   - Memory efficiency tests

## Performance Targets

1. Metal acceleration: >2x speedup vs CPU-only
2. Quantized models: <50% memory usage vs. F16
3. Optimal thread count: Auto-detection for >90% of max performance
4. Memory efficiency: <8GB usage for 7B parameter models at Q4_0
5. Generation speed: >25 tokens/second on M2 MacBook Pro

## Acceptance Criteria

1. All unit and integration tests pass
2. Performance targets are met on test hardware
3. Metal acceleration correctly functions on macOS
4. Memory usage remains within configured constraints
5. Thread optimization shows measurable performance improvement
6. Benchmark suite provides clear performance metrics

## Resources and References

1. llama.cpp Metal integration: https://github.com/ggerganov/llama.cpp/blob/master/examples/metal/README.md
2. Quantization techniques: https://github.com/ggerganov/llama.cpp/blob/master/docs/quantization.md
3. Thread optimization: https://github.com/ggerganov/llama.cpp/blob/master/docs/performance.md
4. Apple Metal Performance Shaders: https://developer.apple.com/documentation/metalperformanceshaders
5. Memory profiling tools: https://pypi.org/project/memory-profiler/

## Implementation Notes

1. Begin optimization with functional baseline from LM_001
2. Focus on measurable improvements and benchmarking
3. Create configuration options with good defaults
4. Document performance characteristics for different hardware
5. Provide clear guidance on optimization selection for users
6. Consider fallback options for systems without Metal support

## Deliverables

1. Enhanced Local Model integration with optimization features
2. Comprehensive benchmark suite for performance testing
3. Documentation of optimization options and their effects
4. Performance reports for target hardware
5. Configuration guidelines for different use cases

## Version History

- v0.1.0 - 2025-05-25 - Initial creation [SES-V0-032]