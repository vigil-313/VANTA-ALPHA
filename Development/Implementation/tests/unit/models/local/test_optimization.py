"""
Unit tests for local model optimization components.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import time
import pytest

# Import optimization components
from src.models.local.optimization import (
    OptimizationConfig,
    PerformanceMonitor,
    QuantizationManager,
    MetalAccelerationManager,
    MemoryManager,
    ThreadOptimizer,
)


class TestOptimizationConfig(unittest.TestCase):
    """Test the OptimizationConfig class."""
    
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        config = OptimizationConfig()
        
        # Check default values
        self.assertEqual(config.quantization, "q4_0")
        self.assertEqual(config.thread_count, os.cpu_count() or 4)
        self.assertEqual(config.batch_size, 512)
        self.assertEqual(config.memory_limit_gb, 8.0)
        
    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        config = OptimizationConfig(
            quantization="f16",
            use_metal=True,
            thread_count=8,
            batch_size=1024,
            memory_limit_gb=16.0
        )
        
        # Check custom values
        self.assertEqual(config.quantization, "f16")
        self.assertEqual(config.use_metal, True)
        self.assertEqual(config.thread_count, 8)
        self.assertEqual(config.batch_size, 1024)
        self.assertEqual(config.memory_limit_gb, 16.0)
        
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = OptimizationConfig(quantization="q5_k", thread_count=6)
        config_dict = config.to_dict()
        
        # Check dictionary values
        self.assertEqual(config_dict["quantization"], "q5_k")
        self.assertEqual(config_dict["thread_count"], 6)
        
    def test_from_dict(self):
        """Test creation from dictionary."""
        config_dict = {
            "quantization": "q8_0",
            "thread_count": 12,
            "use_metal": False
        }
        
        config = OptimizationConfig.from_dict(config_dict)
        
        # Check values from dictionary
        self.assertEqual(config.quantization, "q8_0")
        self.assertEqual(config.thread_count, 12)
        self.assertEqual(config.use_metal, False)
        
    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = OptimizationConfig(
            quantization="q4_0",
            thread_count=4,
            batch_size=512,
            memory_limit_gb=8.0
        )
        
        # Should not raise any exceptions
        self.assertTrue(config.validate())
        
    def test_validate_invalid_quantization(self):
        """Test validation rejects invalid quantization."""
        config = OptimizationConfig(quantization="invalid")
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            config.validate()
            
    def test_get_llama_params(self):
        """Test generation of llama.cpp parameters."""
        config = OptimizationConfig(
            quantization="q4_0",
            use_metal=True,
            thread_count=6,
            batch_size=512,
            context_size=2048
        )
        
        params = config.get_llama_params()
        
        # Check parameter values
        self.assertEqual(params["n_ctx"], 2048)
        self.assertEqual(params["n_batch"], 512)
        self.assertEqual(params["n_threads"], 6)
        self.assertEqual(params["n_gpu_layers"], 32)
        

class TestPerformanceMonitor(unittest.TestCase):
    """Test the PerformanceMonitor class."""
    
    def test_init(self):
        """Test initialization."""
        monitor = PerformanceMonitor("test_model")
        
        # Check initial state
        self.assertEqual(monitor.model_id, "test_model")
        self.assertFalse(monitor.is_monitoring)
        
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        monitor = PerformanceMonitor()
        
        # Start monitoring
        monitor.start_monitoring()
        self.assertTrue(monitor.is_monitoring)
        self.assertIsNotNone(monitor.metrics["start_time"])
        
        # Stop monitoring
        metrics = monitor.stop_monitoring()
        self.assertFalse(monitor.is_monitoring)
        self.assertIsNotNone(metrics["end_time"])
        
    def test_record_inference(self):
        """Test recording inference metrics."""
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        
        # Record an inference
        monitor.record_inference(
            prompt_tokens=10,
            completion_tokens=20,
            latency=0.5
        )
        
        # Check recorded metrics
        metrics = monitor.get_metrics()
        self.assertEqual(metrics["inference_count"], 1)
        self.assertEqual(metrics["prompt_tokens"], 10)
        self.assertEqual(metrics["completion_tokens"], 20)
        self.assertEqual(metrics["total_tokens"], 30)
        self.assertEqual(metrics["total_latency"], 0.5)
        
    def test_reset_metrics(self):
        """Test resetting metrics."""
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        
        # Record some data
        monitor.record_inference(
            prompt_tokens=10,
            completion_tokens=20,
            latency=0.5
        )
        
        # Reset metrics
        monitor.reset_metrics()
        
        # Check metrics were reset
        metrics = monitor.get_metrics()
        self.assertEqual(metrics["inference_count"], 0)
        self.assertEqual(metrics["total_tokens"], 0)
        
    def test_derived_metrics(self):
        """Test calculation of derived metrics."""
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        
        # Record multiple inferences
        monitor.record_inference(
            prompt_tokens=10,
            completion_tokens=20,
            latency=0.5
        )
        monitor.record_inference(
            prompt_tokens=15,
            completion_tokens=30,
            latency=0.7
        )
        
        # Get metrics with derived values
        metrics = monitor.get_metrics()
        
        # Check derived metrics
        self.assertIn("avg_latency", metrics)
        self.assertIn("median_latency", metrics)
        self.assertIn("avg_tokens_per_second", metrics)
        

class TestQuantizationManager(unittest.TestCase):
    """Test the QuantizationManager class."""
    
    def test_init(self):
        """Test initialization."""
        manager = QuantizationManager()
        
        # Check initialization
        self.assertIsNotNone(manager.QUANT_INFO)
        self.assertGreater(len(manager.QUANT_INFO), 0)
        
    def test_get_quantization_options(self):
        """Test getting quantization options."""
        manager = QuantizationManager()
        options = manager.get_quantization_options()
        
        # Check options
        self.assertIsNotNone(options)
        self.assertGreater(len(options), 0)
        self.assertIn("type", options[0])
        
    def test_get_quantization_details(self):
        """Test getting details for a specific quantization."""
        manager = QuantizationManager()
        
        # Get details for a valid type
        details = manager.get_quantization_details("q4_0")
        self.assertIsNotNone(details)
        self.assertEqual(details["type"], "q4_0")
        
        # Try with invalid type
        details = manager.get_quantization_details("invalid")
        self.assertIsNone(details)
        
    def test_estimate_memory_usage(self):
        """Test memory usage estimation."""
        manager = QuantizationManager()
        
        # Estimate for a 7B model with q4_0
        estimate = manager.estimate_memory_usage(
            model_params=7_000_000_000,
            quant_type="q4_0",
            context_length=4096
        )
        
        # Check estimation fields
        self.assertIn("model_parameters", estimate)
        self.assertIn("quantization_type", estimate)
        self.assertIn("model_size_gb", estimate)
        self.assertIn("total_memory_gb", estimate)
        
        # Ensure memory savings are positive for q4_0
        self.assertGreater(estimate["memory_savings_pct"], 50)
        
    def test_recommend_quantization(self):
        """Test quantization recommendation."""
        manager = QuantizationManager()
        
        # Get recommendation for a 7B model with 4GB memory
        recommendation = manager.recommend_quantization(
            model_params=7_000_000_000,
            max_memory_gb=4.0
        )
        
        # Check recommendation
        self.assertIn("recommended", recommendation)
        self.assertIn("fits_in_memory", recommendation)
        self.assertIn("alternatives", recommendation)
        

class TestThreadOptimizer(unittest.TestCase):
    """Test the ThreadOptimizer class."""
    
    def test_init(self):
        """Test initialization."""
        optimizer = ThreadOptimizer()
        
        # Check initialization
        self.assertIsNotNone(optimizer.cpu_info)
        self.assertIsNotNone(optimizer.thread_defaults)
        
    def test_get_optimal_thread_count(self):
        """Test getting optimal thread count."""
        optimizer = ThreadOptimizer()
        
        # Get thread count for different workloads
        interactive = optimizer.get_optimal_thread_count("interactive")
        batch = optimizer.get_optimal_thread_count("batch")
        
        # Check thread counts
        self.assertGreaterEqual(interactive, 1)
        self.assertGreaterEqual(batch, 1)
        self.assertGreaterEqual(batch, interactive)  # Batch should use more threads
        
    def test_get_optimal_batch_size(self):
        """Test getting optimal batch size."""
        optimizer = ThreadOptimizer()
        
        # Get batch size for different configurations
        size1 = optimizer.get_optimal_batch_size(thread_count=2, model_size_billions=7)
        size2 = optimizer.get_optimal_batch_size(thread_count=8, model_size_billions=7)
        
        # Check batch sizes
        self.assertGreaterEqual(size1, 64)
        self.assertGreaterEqual(size2, size1)  # More threads should allow larger batch size
        

@pytest.mark.skipif(not hasattr(MetalAccelerationManager, "metal_supported") or 
                   not MetalAccelerationManager().metal_supported, 
                   reason="Metal acceleration not supported on this platform")
class TestMetalAccelerationManager(unittest.TestCase):
    """Test the MetalAccelerationManager class (if supported)."""
    
    def test_init(self):
        """Test initialization."""
        manager = MetalAccelerationManager()
        
        # Check initialization
        self.assertIsNotNone(manager.metal_supported)
        self.assertIsNotNone(manager.metal_devices)
        
    def test_is_metal_available(self):
        """Test checking if Metal is available."""
        manager = MetalAccelerationManager()
        
        # Check Metal availability
        availability = manager.is_metal_available()
        self.assertIsInstance(availability, bool)
        
    def test_get_recommended_config(self):
        """Test getting recommended Metal configuration."""
        manager = MetalAccelerationManager()
        
        # Get recommendation for a 7B model
        config = manager.get_recommended_config(model_size_billions=7.0)
        
        # Check configuration
        self.assertIn("use_metal", config)
        self.assertIn("n_gpu_layers", config)
        self.assertIn("offload_kqv", config)


def test_memory_manager_basic():
    """Basic test for MemoryManager."""
    manager = MemoryManager(memory_limit_gb=4.0)
    
    # Check initialization
    assert manager.memory_limit_gb == 4.0
    assert manager.warning_threshold == 0.8
    assert manager.critical_threshold == 0.95
    
    # Get memory stats
    stats = manager.get_memory_stats()
    assert "memory_limit_gb" in stats
    assert stats["memory_limit_gb"] == 4.0
    

def test_performance_monitor_export():
    """Test exporting performance metrics."""
    monitor = PerformanceMonitor("test_model")
    monitor.start_monitoring()
    
    # Record some data
    monitor.record_inference(
        prompt_tokens=10,
        completion_tokens=20,
        latency=0.5
    )
    
    # Stop monitoring
    monitor.stop_monitoring()
    
    # Export metrics
    json_report = monitor.export_report(format="json")
    text_report = monitor.export_report(format="text")
    
    # Check exports
    assert isinstance(json_report, str)
    assert isinstance(text_report, str)
    assert "Performance Report" in text_report
    assert "test_model" in text_report


def test_optimization_config_device_optimization():
    """Test device optimization for OptimizationConfig."""
    config = OptimizationConfig()
    
    # Optimize for device
    optimized = config.optimize_for_device(detect_hardware=True)
    
    # Check that optimization happened
    assert optimized is config  # Should return self
    assert config.thread_count > 0


def test_quantization_model_size_detection():
    """Test model size detection from model name."""
    manager = QuantizationManager()
    
    # Test different model names
    size_7b = manager.get_model_size_from_name("llama-7b-v0.1")
    size_13b = manager.get_model_size_from_name("mistral-13B-v0.1")
    size_30b = manager.get_model_size_from_name("llama2-30b-chat")
    
    # Check sizes
    assert size_7b == 7_000_000_000
    assert size_13b == 13_000_000_000
    assert size_30b == 30_000_000_000


def test_thread_optimizer_performance_estimation():
    """Test performance estimation for ThreadOptimizer."""
    optimizer = ThreadOptimizer()
    
    # Estimate performance for different configurations
    estimate1 = optimizer.estimate_performance(
        thread_count=4,
        batch_size=512,
        model_size_billions=7.0
    )
    
    estimate2 = optimizer.estimate_performance(
        thread_count=8,
        batch_size=512,
        model_size_billions=7.0
    )
    
    # Check estimates
    assert "estimated_tokens_per_second" in estimate1
    assert "estimated_tokens_per_second" in estimate2
    # More threads should generally give better performance (up to a point)
    if estimate1["thread_scaling_factor"] == estimate2["thread_scaling_factor"]:
        assert estimate2["estimated_tokens_per_second"] >= estimate1["estimated_tokens_per_second"]


if __name__ == "__main__":
    unittest.main()