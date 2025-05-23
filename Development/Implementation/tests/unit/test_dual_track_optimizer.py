#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the dual-track optimization system.
"""
# TASK-REF: DP-003 - Dual-Track Optimization
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Optimization

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, Any

from src.models.dual_track.optimizer import (
    DualTrackOptimizer,
    MetricsCollector,
    ResourceMonitor,
    AdaptiveOptimizer,
    PerformanceMetrics,
    ResourceConstraints,
    OptimizationConfig,
    OptimizationStrategy,
    create_default_optimizer,
    create_optimized_config
)
from src.models.dual_track.exceptions import (
    DualTrackOptimizationError,
    MetricsCollectionError,
    ResourceMonitoringError,
    AdaptationError
)


class TestPerformanceMetrics:
    """Test the PerformanceMetrics dataclass."""
    
    def test_performance_metrics_creation(self):
        """Test creating a performance metric."""
        metric = PerformanceMetrics(
            timestamp=time.time(),
            processing_path="local",
            request_id="test-123",
            latency_ms=500.0,
            tokens_processed=100,
            memory_usage_mb=1024.0,
            cpu_usage_percent=50.0,
            success=True
        )
        
        assert metric.processing_path == "local"
        assert metric.request_id == "test-123"
        assert metric.latency_ms == 500.0
        assert metric.tokens_processed == 100
        assert metric.memory_usage_mb == 1024.0
        assert metric.cpu_usage_percent == 50.0
        assert metric.success is True
        assert metric.error_type is None
    
    def test_performance_metrics_with_error(self):
        """Test creating a performance metric with error."""
        metric = PerformanceMetrics(
            timestamp=time.time(),
            processing_path="api",
            request_id="test-456",
            latency_ms=1000.0,
            tokens_processed=0,
            memory_usage_mb=2048.0,
            cpu_usage_percent=80.0,
            success=False,
            error_type="timeout"
        )
        
        assert metric.success is False
        assert metric.error_type == "timeout"


class TestResourceConstraints:
    """Test the ResourceConstraints dataclass."""
    
    def test_default_constraints(self):
        """Test default resource constraints."""
        constraints = ResourceConstraints()
        
        assert constraints.max_memory_mb == 4096.0
        assert constraints.max_cpu_percent == 80.0
        assert constraints.max_gpu_memory_mb == 2048.0
        assert constraints.max_concurrent_requests == 4
        assert constraints.target_latency_ms == 2000.0
        assert constraints.max_cost_per_request == 0.01
        assert constraints.battery_threshold_percent == 20.0
    
    def test_custom_constraints(self):
        """Test custom resource constraints."""
        constraints = ResourceConstraints(
            max_memory_mb=8192.0,
            max_cpu_percent=90.0,
            target_latency_ms=1000.0
        )
        
        assert constraints.max_memory_mb == 8192.0
        assert constraints.max_cpu_percent == 90.0
        assert constraints.target_latency_ms == 1000.0


class TestOptimizationConfig:
    """Test the OptimizationConfig dataclass."""
    
    def test_default_config(self):
        """Test default optimization configuration."""
        config = OptimizationConfig()
        
        assert config.strategy == OptimizationStrategy.ADAPTIVE
        assert isinstance(config.constraints, ResourceConstraints)
        assert config.metrics_window_size == 100
        assert config.adaptation_interval_seconds == 30.0
        assert config.enable_caching is True
        assert config.enable_resource_monitoring is True
    
    def test_custom_config(self):
        """Test custom optimization configuration."""
        constraints = ResourceConstraints(max_memory_mb=2048.0)
        config = OptimizationConfig(
            strategy=OptimizationStrategy.LATENCY_FOCUSED,
            constraints=constraints,
            metrics_window_size=50,
            adaptation_interval_seconds=15.0
        )
        
        assert config.strategy == OptimizationStrategy.LATENCY_FOCUSED
        assert config.constraints.max_memory_mb == 2048.0
        assert config.metrics_window_size == 50
        assert config.adaptation_interval_seconds == 15.0


class TestMetricsCollector:
    """Test the MetricsCollector class."""
    
    @pytest.fixture
    def config(self):
        """Fixture for optimization config."""
        return OptimizationConfig(metrics_window_size=5)
    
    @pytest.fixture
    def collector(self, config):
        """Fixture for metrics collector."""
        return MetricsCollector(config)
    
    def test_collector_initialization(self, collector):
        """Test metrics collector initialization."""
        assert len(collector.metrics) == 0
        assert len(collector.metrics_by_path) == 0
        assert collector.config.metrics_window_size == 5
    
    def test_record_metric(self, collector):
        """Test recording a metric."""
        metric = PerformanceMetrics(
            timestamp=time.time(),
            processing_path="local",
            request_id="test-1",
            latency_ms=100.0,
            tokens_processed=50,
            memory_usage_mb=512.0,
            cpu_usage_percent=30.0,
            success=True
        )
        
        collector.record_metric(metric)
        
        assert len(collector.metrics) == 1
        assert len(collector.metrics_by_path["local"]) == 1
        assert collector.metrics[0] == metric
    
    def test_metrics_window_size(self, collector):
        """Test that metrics window size is respected."""
        # Add more metrics than window size
        for i in range(10):
            metric = PerformanceMetrics(
                timestamp=time.time(),
                processing_path="local",
                request_id=f"test-{i}",
                latency_ms=100.0 + i,
                tokens_processed=50,
                memory_usage_mb=512.0,
                cpu_usage_percent=30.0,
                success=True
            )
            collector.record_metric(metric)
        
        # Should only keep the last 5 metrics
        assert len(collector.metrics) == 5
        assert len(collector.metrics_by_path["local"]) == 5
    
    def test_get_metrics_summary_empty(self, collector):
        """Test getting metrics summary when no metrics exist."""
        summary = collector.get_metrics_summary()
        assert summary == {}
    
    def test_get_metrics_summary_with_data(self, collector):
        """Test getting metrics summary with data."""
        # Add successful metrics
        for i in range(3):
            metric = PerformanceMetrics(
                timestamp=time.time(),
                processing_path="local",
                request_id=f"test-{i}",
                latency_ms=100.0 + i * 10,
                tokens_processed=50,
                memory_usage_mb=512.0,
                cpu_usage_percent=30.0,
                quality_score=0.8,
                success=True
            )
            collector.record_metric(metric)
        
        # Add failed metric
        failed_metric = PerformanceMetrics(
            timestamp=time.time(),
            processing_path="local",
            request_id="test-fail",
            latency_ms=200.0,
            tokens_processed=0,
            memory_usage_mb=512.0,
            cpu_usage_percent=30.0,
            success=False,
            error_type="timeout"
        )
        collector.record_metric(failed_metric)
        
        summary = collector.get_metrics_summary()
        
        assert summary["total_requests"] == 4
        assert summary["successful_requests"] == 3
        assert summary["success_rate"] == 0.75
        assert summary["avg_latency_ms"] == 110.0  # (100 + 110 + 120) / 3
        assert summary["avg_quality_score"] == 0.8
        assert "timeout" in summary["error_rate_by_type"]
        assert summary["error_rate_by_type"]["timeout"] == 0.25
    
    def test_get_metrics_summary_by_path(self, collector):
        """Test getting metrics summary filtered by path."""
        # Add metrics for different paths
        local_metric = PerformanceMetrics(
            timestamp=time.time(),
            processing_path="local",
            request_id="test-local",
            latency_ms=100.0,
            tokens_processed=50,
            memory_usage_mb=512.0,
            cpu_usage_percent=30.0,
            success=True
        )
        
        api_metric = PerformanceMetrics(
            timestamp=time.time(),
            processing_path="api",
            request_id="test-api",
            latency_ms=500.0,
            tokens_processed=100,
            memory_usage_mb=256.0,
            cpu_usage_percent=20.0,
            success=True
        )
        
        collector.record_metric(local_metric)
        collector.record_metric(api_metric)
        
        local_summary = collector.get_metrics_summary("local")
        api_summary = collector.get_metrics_summary("api")
        
        assert local_summary["total_requests"] == 1
        assert local_summary["avg_latency_ms"] == 100.0
        
        assert api_summary["total_requests"] == 1
        assert api_summary["avg_latency_ms"] == 500.0


class TestResourceMonitor:
    """Test the ResourceMonitor class."""
    
    @pytest.fixture
    def config(self):
        """Fixture for optimization config."""
        return OptimizationConfig(monitor_interval_seconds=0.1)
    
    @pytest.fixture
    def monitor(self, config):
        """Fixture for resource monitor."""
        return ResourceMonitor(config)
    
    def test_monitor_initialization(self, monitor):
        """Test resource monitor initialization."""
        assert monitor.current_usage == {}
        assert monitor._monitoring is False
        assert monitor._monitor_thread is None
    
    @patch('src.models.dual_track.optimizer.psutil')
    def test_collect_usage(self, mock_psutil, monitor):
        """Test collecting resource usage."""
        # Mock psutil responses
        mock_memory = Mock()
        mock_memory.used = 1024 * 1024 * 1024  # 1GB
        mock_memory.available = 3 * 1024 * 1024 * 1024  # 3GB
        mock_memory.percent = 25.0
        
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.getloadavg.return_value = [1.0, 1.5, 2.0]
        
        # Mock battery (not available)
        mock_psutil.sensors_battery.side_effect = AttributeError()
        
        usage = monitor._collect_usage()
        
        assert usage["memory_mb"] == 1024.0
        assert usage["memory_available_mb"] == 3072.0
        assert usage["memory_percent"] == 25.0
        assert usage["cpu_percent"] == 50.0
        assert usage["load_average"] == [1.0, 1.5, 2.0]
        assert usage["gpu_memory_mb"] == 0.0
        assert usage["gpu_percent"] == 0.0
        assert "timestamp" in usage
    
    def test_check_constraints_no_violations(self, monitor):
        """Test checking constraints with no violations."""
        monitor.current_usage = {
            "memory_mb": 1024.0,
            "cpu_percent": 50.0,
            "gpu_memory_mb": 512.0,
            "battery_percent": 80.0
        }
        
        constraints = ResourceConstraints(
            max_memory_mb=2048.0,
            max_cpu_percent=80.0,
            max_gpu_memory_mb=1024.0,
            battery_threshold_percent=20.0
        )
        
        violations = monitor.check_constraints(constraints)
        assert violations == {}
    
    def test_check_constraints_with_violations(self, monitor):
        """Test checking constraints with violations."""
        monitor.current_usage = {
            "memory_mb": 3072.0,
            "cpu_percent": 90.0,
            "gpu_memory_mb": 2048.0,
            "battery_percent": 15.0
        }
        
        constraints = ResourceConstraints(
            max_memory_mb=2048.0,
            max_cpu_percent=80.0,
            max_gpu_memory_mb=1024.0,
            battery_threshold_percent=20.0
        )
        
        violations = monitor.check_constraints(constraints)
        
        assert violations["memory"] is True
        assert violations["cpu"] is True
        assert violations["gpu_memory"] is True
        assert violations["battery"] is True
    
    def test_start_stop_monitoring(self, monitor):
        """Test starting and stopping monitoring."""
        assert monitor._monitoring is False
        
        monitor.start_monitoring()
        assert monitor._monitoring is True
        assert monitor._monitor_thread is not None
        
        # Wait a bit for thread to start
        time.sleep(0.05)
        
        monitor.stop_monitoring()
        assert monitor._monitoring is False


class TestAdaptiveOptimizer:
    """Test the AdaptiveOptimizer class."""
    
    @pytest.fixture
    def config(self):
        """Fixture for optimization config."""
        return OptimizationConfig(adaptation_interval_seconds=0.1)
    
    @pytest.fixture
    def metrics_collector(self, config):
        """Fixture for metrics collector."""
        return MetricsCollector(config)
    
    @pytest.fixture
    def resource_monitor(self, config):
        """Fixture for resource monitor."""
        return ResourceMonitor(config)
    
    @pytest.fixture
    def optimizer(self, config, metrics_collector, resource_monitor):
        """Fixture for adaptive optimizer."""
        return AdaptiveOptimizer(config, metrics_collector, resource_monitor)
    
    def test_optimizer_initialization(self, optimizer):
        """Test adaptive optimizer initialization."""
        assert optimizer.current_strategy == OptimizationStrategy.ADAPTIVE
        assert optimizer.routing_preferences["local_bias"] == 0.5
        assert optimizer.routing_preferences["parallel_threshold"] == 0.7
        assert optimizer.routing_preferences["timeout_multiplier"] == 1.0
        assert optimizer.routing_preferences["quality_threshold"] == 0.8
    
    def test_should_adapt_timing(self, optimizer):
        """Test adaptation timing logic."""
        # Initially should adapt (no previous adaptation)
        assert optimizer.should_adapt() is True
        
        # After setting recent adaptation time, should not adapt immediately
        optimizer.last_adaptation_time = time.time()
        assert optimizer.should_adapt() is False
        
        # After waiting, should adapt again
        time.sleep(0.12)  # Wait longer than adaptation interval
        assert optimizer.should_adapt() is True
    
    def test_adapt_strategy_too_soon(self, optimizer):
        """Test adaptation when called too soon."""
        optimizer.last_adaptation_time = time.time()
        
        result = optimizer.adapt_strategy()
        
        assert result["adapted"] is False
        assert result["reason"] == "Too soon since last adaptation"
    
    def test_get_routing_preferences(self, optimizer):
        """Test getting routing preferences."""
        preferences = optimizer.get_routing_preferences()
        
        assert isinstance(preferences, dict)
        assert "local_bias" in preferences
        assert "parallel_threshold" in preferences
        assert "timeout_multiplier" in preferences
        assert "quality_threshold" in preferences
    
    def test_get_optimization_state(self, optimizer):
        """Test getting optimization state."""
        state = optimizer.get_optimization_state()
        
        assert state["strategy"] == "adaptive"
        assert "routing_preferences" in state
        assert "last_adaptation_time" in state
        assert "adaptation_count" in state
        assert "recent_adaptations" in state


class TestDualTrackOptimizer:
    """Test the main DualTrackOptimizer class."""
    
    @pytest.fixture
    def config(self):
        """Fixture for optimization config."""
        return OptimizationConfig(enable_resource_monitoring=False)  # Disable for testing
    
    @pytest.fixture
    def optimizer(self, config):
        """Fixture for dual-track optimizer."""
        return DualTrackOptimizer(config)
    
    def test_optimizer_initialization(self, optimizer):
        """Test optimizer initialization."""
        assert isinstance(optimizer.metrics_collector, MetricsCollector)
        assert isinstance(optimizer.resource_monitor, ResourceMonitor)
        assert isinstance(optimizer.adaptive_optimizer, AdaptiveOptimizer)
        assert optimizer._started is False
        assert len(optimizer.active_requests) == 0
    
    def test_start_stop_optimizer(self, optimizer):
        """Test starting and stopping the optimizer."""
        assert optimizer._started is False
        
        optimizer.start()
        assert optimizer._started is True
        
        optimizer.stop()
        assert optimizer._started is False
    
    def test_record_request_lifecycle(self, optimizer):
        """Test recording request start and completion."""
        request_id = "test-request-123"
        query = "What is the capital of France?"
        context = {"user_id": "user123"}
        
        # Record request start
        optimizer.record_request_start(request_id, query, context)
        
        assert request_id in optimizer.active_requests
        assert optimizer.active_requests[request_id]["query"] == query
        assert optimizer.active_requests[request_id]["context"] == context
        
        # Record request completion
        result = {
            "tokens_used": 25,
            "cost_estimate": 0.005,
            "quality_score": 0.85
        }
        
        optimizer.record_request_completion(
            request_id, "local", result, success=True
        )
        
        assert request_id not in optimizer.active_requests
        assert len(optimizer.metrics_collector.metrics) == 1
        
        metric = optimizer.metrics_collector.metrics[0]
        assert metric.request_id == request_id
        assert metric.processing_path == "local"
        assert metric.tokens_processed == 25
        assert metric.cost_estimate == 0.005
        assert metric.quality_score == 0.85
        assert metric.success is True
    
    def test_get_optimization_recommendations(self, optimizer):
        """Test getting optimization recommendations."""
        query = "Test query"
        context = {"test": "context"}
        
        recommendations = optimizer.get_optimization_recommendations(query, context)
        
        assert "routing_preferences" in recommendations
        assert "resource_status" in recommendations
        assert "timeouts" in recommendations
        assert "caching" in recommendations
        assert "active_requests" in recommendations
        
        # Check timeout values
        timeouts = recommendations["timeouts"]
        assert "local_timeout_ms" in timeouts
        assert "api_timeout_ms" in timeouts
        assert "parallel_timeout_ms" in timeouts
    
    def test_get_metrics_summary(self, optimizer):
        """Test getting metrics summary."""
        # Add some metrics first
        request_id = "test-metrics"
        optimizer.record_request_start(request_id, "test query")
        optimizer.record_request_completion(
            request_id, "api", {"tokens_used": 100}, success=True
        )
        
        summary = optimizer.get_metrics_summary()
        
        assert summary["total_requests"] == 1
        assert summary["successful_requests"] == 1
        assert summary["success_rate"] == 1.0
    
    def test_get_optimization_status(self, optimizer):
        """Test getting comprehensive optimization status."""
        status = optimizer.get_optimization_status()
        
        assert "config" in status
        assert "current_state" in status
        assert "resource_usage" in status
        assert "metrics_summary" in status
        assert "active_requests" in status
        assert "started" in status
        
        # Check config section
        config = status["config"]
        assert "strategy" in config
        assert "constraints" in config
        assert "adaptation_interval_seconds" in config


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_default_optimizer(self):
        """Test creating default optimizer."""
        optimizer = create_default_optimizer()
        
        assert isinstance(optimizer, DualTrackOptimizer)
        assert optimizer.config.strategy == OptimizationStrategy.ADAPTIVE
    
    def test_create_optimized_config_latency_focused(self):
        """Test creating latency-focused config."""
        config = create_optimized_config(OptimizationStrategy.LATENCY_FOCUSED)
        
        assert config.strategy == OptimizationStrategy.LATENCY_FOCUSED
        assert config.constraints.target_latency_ms == 1000.0
        assert config.adaptation_interval_seconds == 15.0
        assert config.enable_preemption is True
    
    def test_create_optimized_config_resource_efficient(self):
        """Test creating resource-efficient config."""
        config = create_optimized_config(OptimizationStrategy.RESOURCE_EFFICIENT)
        
        assert config.strategy == OptimizationStrategy.RESOURCE_EFFICIENT
        assert config.constraints.max_memory_mb == 2048.0
        assert config.constraints.max_cpu_percent == 60.0
        assert config.enable_caching is True
        assert config.cache_ttl_seconds == 600.0
    
    def test_create_optimized_config_quality_focused(self):
        """Test creating quality-focused config."""
        config = create_optimized_config(OptimizationStrategy.QUALITY_FOCUSED)
        
        assert config.strategy == OptimizationStrategy.QUALITY_FOCUSED
        assert config.constraints.target_latency_ms == 5000.0
        assert config.constraints.max_cost_per_request == 0.05
        assert config.adaptation_interval_seconds == 60.0
    
    def test_create_optimized_config_adaptive(self):
        """Test creating adaptive config (default)."""
        config = create_optimized_config()
        
        assert config.strategy == OptimizationStrategy.ADAPTIVE


class TestThreadSafety:
    """Test thread safety of optimization components."""
    
    @pytest.fixture
    def config(self):
        """Fixture for optimization config."""
        return OptimizationConfig(metrics_window_size=100)
    
    @pytest.fixture
    def collector(self, config):
        """Fixture for metrics collector."""
        return MetricsCollector(config)
    
    def test_concurrent_metric_recording(self, collector):
        """Test concurrent metric recording is thread-safe."""
        def record_metrics(thread_id):
            for i in range(10):
                metric = PerformanceMetrics(
                    timestamp=time.time(),
                    processing_path=f"thread-{thread_id}",
                    request_id=f"thread-{thread_id}-req-{i}",
                    latency_ms=100.0 + i,
                    tokens_processed=50,
                    memory_usage_mb=512.0,
                    cpu_usage_percent=30.0,
                    success=True
                )
                collector.record_metric(metric)
                time.sleep(0.001)  # Small delay to increase chance of race conditions
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_metrics, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have recorded 50 metrics total (5 threads * 10 metrics each)
        assert len(collector.metrics) == 50
        
        # Check that all metrics were recorded correctly
        summary = collector.get_metrics_summary()
        assert summary["total_requests"] == 50
        assert summary["successful_requests"] == 50
        assert summary["success_rate"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__])