#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA Dual-Track Processing Optimizer

This module implements optimization strategies for the dual-track processing system,
focusing on resource allocation, performance monitoring, and adaptive tuning.
"""
# TASK-REF: DP-003 - Dual-Track Optimization
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Optimization
# DOC-REF: DOC-ARCH-003 - Dual-Track Processing Component

import time
import threading
import psutil
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import deque, defaultdict
from enum import Enum
import statistics
import json

from .exceptions import DualTrackOptimizationError


class OptimizationStrategy(Enum):
    """Available optimization strategies."""
    BALANCED = "balanced"
    LATENCY_FOCUSED = "latency_focused"
    RESOURCE_EFFICIENT = "resource_efficient"
    QUALITY_FOCUSED = "quality_focused"
    ADAPTIVE = "adaptive"


@dataclass
class PerformanceMetrics:
    """Performance metrics for dual-track processing."""
    timestamp: float
    processing_path: str
    request_id: str
    latency_ms: float
    tokens_processed: int
    memory_usage_mb: float
    cpu_usage_percent: float
    gpu_usage_percent: float = 0.0
    cost_estimate: float = 0.0
    quality_score: float = 0.0
    success: bool = True
    error_type: Optional[str] = None


@dataclass
class ResourceConstraints:
    """System resource constraints for optimization."""
    max_memory_mb: float = 4096.0
    max_cpu_percent: float = 80.0
    max_gpu_memory_mb: float = 2048.0
    max_concurrent_requests: int = 4
    target_latency_ms: float = 2000.0
    max_cost_per_request: float = 0.01
    battery_threshold_percent: float = 20.0


@dataclass
class OptimizationConfig:
    """Configuration for the optimization system."""
    strategy: OptimizationStrategy = OptimizationStrategy.ADAPTIVE
    constraints: ResourceConstraints = field(default_factory=ResourceConstraints)
    metrics_window_size: int = 100
    adaptation_interval_seconds: float = 30.0
    enable_caching: bool = True
    cache_ttl_seconds: float = 300.0
    enable_preemption: bool = True
    enable_resource_monitoring: bool = True
    monitor_interval_seconds: float = 1.0


class MetricsCollector:
    """Collects and analyzes performance metrics."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.metrics: deque = deque(maxlen=config.metrics_window_size)
        self.metrics_by_path: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=config.metrics_window_size)
        )
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__ + ".MetricsCollector")
    
    def record_metric(self, metric: PerformanceMetrics) -> None:
        """Record a performance metric."""
        with self.lock:
            self.metrics.append(metric)
            self.metrics_by_path[metric.processing_path].append(metric)
            
        self.logger.debug(f"Recorded metric: {metric.processing_path} - {metric.latency_ms}ms")
    
    def get_metrics_summary(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for metrics."""
        with self.lock:
            if path and path in self.metrics_by_path:
                metrics_to_analyze = list(self.metrics_by_path[path])
            else:
                metrics_to_analyze = list(self.metrics)
        
        if not metrics_to_analyze:
            return {}
        
        successful_metrics = [m for m in metrics_to_analyze if m.success]
        
        return {
            "total_requests": len(metrics_to_analyze),
            "successful_requests": len(successful_metrics),
            "success_rate": len(successful_metrics) / len(metrics_to_analyze),
            "avg_latency_ms": statistics.mean([m.latency_ms for m in successful_metrics]) if successful_metrics else 0,
            "median_latency_ms": statistics.median([m.latency_ms for m in successful_metrics]) if successful_metrics else 0,
            "p95_latency_ms": self._percentile([m.latency_ms for m in successful_metrics], 95) if successful_metrics else 0,
            "avg_memory_mb": statistics.mean([m.memory_usage_mb for m in successful_metrics]) if successful_metrics else 0,
            "avg_cpu_percent": statistics.mean([m.cpu_usage_percent for m in successful_metrics]) if successful_metrics else 0,
            "total_cost": sum([m.cost_estimate for m in successful_metrics]),
            "avg_quality_score": statistics.mean([m.quality_score for m in successful_metrics if m.quality_score > 0]) if successful_metrics else 0,
            "error_rate_by_type": self._get_error_rates(metrics_to_analyze),
            "path_distribution": self._get_path_distribution(metrics_to_analyze)
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _get_error_rates(self, metrics: List[PerformanceMetrics]) -> Dict[str, float]:
        """Get error rates by error type."""
        error_counts = defaultdict(int)
        for metric in metrics:
            if not metric.success and metric.error_type:
                error_counts[metric.error_type] += 1
        
        total_requests = len(metrics)
        if total_requests == 0:
            return {}
            
        return {
            error_type: count / total_requests
            for error_type, count in error_counts.items()
        }
    
    def _get_path_distribution(self, metrics: List[PerformanceMetrics]) -> Dict[str, float]:
        """Get distribution of processing paths."""
        path_counts = defaultdict(int)
        for metric in metrics:
            path_counts[metric.processing_path] += 1
        
        total_requests = len(metrics)
        if total_requests == 0:
            return {}
            
        return {
            path: count / total_requests
            for path, count in path_counts.items()
        }


class ResourceMonitor:
    """Monitors system resource usage."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.current_usage = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__ + ".ResourceMonitor")
        self._monitoring = False
        self._monitor_thread = None
    
    def start_monitoring(self) -> None:
        """Start continuous resource monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("Resource monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        self.logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                usage = self._collect_usage()
                with self.lock:
                    self.current_usage = usage
                
                time.sleep(self.config.monitor_interval_seconds)
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                time.sleep(5.0)
    
    def _collect_usage(self) -> Dict[str, Any]:
        """Collect current resource usage."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            usage = {
                "memory_mb": memory.used / (1024 * 1024),
                "memory_available_mb": memory.available / (1024 * 1024),
                "memory_percent": memory.percent,
                "cpu_percent": cpu_percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0],
                "timestamp": time.time()
            }
            
            # Add battery info if available
            try:
                battery = psutil.sensors_battery()
                if battery:
                    usage["battery_percent"] = battery.percent
                    usage["power_plugged"] = battery.power_plugged
            except (AttributeError, NotImplementedError):
                pass
            
            # Add GPU info if available (placeholder for future implementation)
            usage["gpu_memory_mb"] = 0.0
            usage["gpu_percent"] = 0.0
            
            return usage
        except Exception as e:
            self.logger.error(f"Error collecting resource usage: {e}")
            return {}
    
    def get_current_usage(self) -> Dict[str, Any]:
        """Get current resource usage."""
        with self.lock:
            return self.current_usage.copy()
    
    def check_constraints(self, constraints: ResourceConstraints) -> Dict[str, bool]:
        """Check if current usage violates constraints."""
        usage = self.get_current_usage()
        if not usage:
            return {}
        
        violations = {}
        
        if usage.get("memory_mb", 0) > constraints.max_memory_mb:
            violations["memory"] = True
        
        if usage.get("cpu_percent", 0) > constraints.max_cpu_percent:
            violations["cpu"] = True
        
        if usage.get("gpu_memory_mb", 0) > constraints.max_gpu_memory_mb:
            violations["gpu_memory"] = True
        
        battery_percent = usage.get("battery_percent")
        if battery_percent is not None and battery_percent < constraints.battery_threshold_percent:
            violations["battery"] = True
        
        return violations


class AdaptiveOptimizer:
    """Implements adaptive optimization strategies."""
    
    def __init__(self, config: OptimizationConfig, metrics_collector: MetricsCollector, resource_monitor: ResourceMonitor):
        self.config = config
        self.metrics_collector = metrics_collector
        self.resource_monitor = resource_monitor
        self.logger = logging.getLogger(__name__ + ".AdaptiveOptimizer")
        
        # Current optimization state
        self.current_strategy = config.strategy
        self.routing_preferences = {
            "local_bias": 0.5,  # 0 = prefer API, 1 = prefer local
            "parallel_threshold": 0.7,  # confidence threshold for parallel processing
            "timeout_multiplier": 1.0,  # multiplier for timeouts
            "quality_threshold": 0.8  # minimum quality threshold
        }
        
        # Adaptation tracking
        self.last_adaptation_time = time.time()
        self.adaptation_history = deque(maxlen=50)
    
    def should_adapt(self) -> bool:
        """Check if adaptation should occur."""
        return (
            time.time() - self.last_adaptation_time >= self.config.adaptation_interval_seconds
        )
    
    def adapt_strategy(self) -> Dict[str, Any]:
        """Adapt optimization strategy based on current metrics."""
        if not self.should_adapt():
            return {"adapted": False, "reason": "Too soon since last adaptation"}
        
        try:
            # Collect current metrics and resource usage
            overall_metrics = self.metrics_collector.get_metrics_summary()
            local_metrics = self.metrics_collector.get_metrics_summary("local")
            api_metrics = self.metrics_collector.get_metrics_summary("api")
            parallel_metrics = self.metrics_collector.get_metrics_summary("parallel")
            
            resource_usage = self.resource_monitor.get_current_usage()
            violations = self.resource_monitor.check_constraints(self.config.constraints)
            
            # Determine optimal strategy
            adaptation_result = self._determine_optimal_strategy(
                overall_metrics, local_metrics, api_metrics, parallel_metrics,
                resource_usage, violations
            )
            
            # Apply adaptations
            if adaptation_result["should_adapt"]:
                self._apply_adaptations(adaptation_result["adaptations"])
                self.adaptation_history.append({
                    "timestamp": time.time(),
                    "adaptations": adaptation_result["adaptations"],
                    "reason": adaptation_result["reason"]
                })
                self.last_adaptation_time = time.time()
                
                self.logger.info(f"Applied adaptations: {adaptation_result['adaptations']}")
            
            return adaptation_result
            
        except Exception as e:
            self.logger.error(f"Error during strategy adaptation: {e}")
            return {"adapted": False, "error": str(e)}
    
    def _determine_optimal_strategy(
        self, overall: Dict, local: Dict, api: Dict, parallel: Dict,
        resources: Dict, violations: Dict
    ) -> Dict[str, Any]:
        """Determine optimal strategy based on current conditions."""
        adaptations = {}
        reasons = []
        
        # Check for resource violations - highest priority
        if violations:
            if "memory" in violations or "cpu" in violations:
                adaptations["local_bias"] = max(0.0, self.routing_preferences["local_bias"] - 0.2)
                reasons.append("Reducing local model usage due to resource constraints")
                
            if "battery" in violations:
                adaptations["local_bias"] = min(1.0, self.routing_preferences["local_bias"] + 0.3)
                adaptations["timeout_multiplier"] = max(0.5, self.routing_preferences["timeout_multiplier"] - 0.2)
                reasons.append("Optimizing for battery conservation")
        
        # Check latency performance
        if overall.get("p95_latency_ms", 0) > self.config.constraints.target_latency_ms:
            # Latency is too high
            if api.get("avg_latency_ms", 0) < local.get("avg_latency_ms", 0):
                adaptations["local_bias"] = max(0.0, self.routing_preferences["local_bias"] - 0.15)
                reasons.append("Favoring API due to better latency")
            else:
                adaptations["local_bias"] = min(1.0, self.routing_preferences["local_bias"] + 0.15)
                reasons.append("Favoring local model due to better latency")
        
        # Check success rates
        overall_success_rate = overall.get("success_rate", 1.0)
        if overall_success_rate < 0.9:
            # Low success rate, be more conservative
            adaptations["parallel_threshold"] = min(0.9, self.routing_preferences["parallel_threshold"] + 0.1)
            adaptations["timeout_multiplier"] = min(2.0, self.routing_preferences["timeout_multiplier"] + 0.2)
            reasons.append("Increasing timeouts and reducing parallel processing due to low success rate")
        
        # Check quality scores
        overall_quality = overall.get("avg_quality_score", 0.0)
        if overall_quality > 0 and overall_quality < self.routing_preferences["quality_threshold"]:
            # Quality is low, favor API models
            adaptations["local_bias"] = max(0.0, self.routing_preferences["local_bias"] - 0.2)
            reasons.append("Favoring API models due to quality concerns")
        
        # Check cost efficiency
        total_cost = overall.get("total_cost", 0.0)
        if total_cost > 0:
            avg_cost_per_request = total_cost / max(1, overall.get("total_requests", 1))
            if avg_cost_per_request > self.config.constraints.max_cost_per_request:
                adaptations["local_bias"] = min(1.0, self.routing_preferences["local_bias"] + 0.25)
                reasons.append("Favoring local model to reduce costs")
        
        # Strategy-specific adaptations
        if self.current_strategy == OptimizationStrategy.LATENCY_FOCUSED:
            adaptations.update(self._adapt_for_latency_focus(overall, local, api, parallel))
        elif self.current_strategy == OptimizationStrategy.RESOURCE_EFFICIENT:
            adaptations.update(self._adapt_for_resource_efficiency(overall, resources, violations))
        elif self.current_strategy == OptimizationStrategy.QUALITY_FOCUSED:
            adaptations.update(self._adapt_for_quality_focus(overall, local, api))
        
        should_adapt = len(adaptations) > 0
        return {
            "should_adapt": should_adapt,
            "adaptations": adaptations,
            "reason": "; ".join(reasons) if reasons else "No adaptation needed"
        }
    
    def _adapt_for_latency_focus(self, overall: Dict, local: Dict, api: Dict, parallel: Dict) -> Dict[str, Any]:
        """Optimize specifically for minimal latency."""
        adaptations = {}
        
        # Favor faster processing path
        local_latency = local.get("avg_latency_ms", float("inf"))
        api_latency = api.get("avg_latency_ms", float("inf"))
        
        if api_latency < local_latency * 0.8:  # API significantly faster
            adaptations["local_bias"] = max(0.1, self.routing_preferences["local_bias"] - 0.2)
        elif local_latency < api_latency * 0.8:  # Local significantly faster
            adaptations["local_bias"] = min(0.9, self.routing_preferences["local_bias"] + 0.2)
        
        # Reduce parallel threshold for faster decisions
        adaptations["parallel_threshold"] = max(0.5, self.routing_preferences["parallel_threshold"] - 0.1)
        
        return adaptations
    
    def _adapt_for_resource_efficiency(self, overall: Dict, resources: Dict, violations: Dict) -> Dict[str, Any]:
        """Optimize for resource conservation."""
        adaptations = {}
        
        # If resource usage is high, favor local models
        memory_percent = resources.get("memory_percent", 0)
        cpu_percent = resources.get("cpu_percent", 0)
        
        if memory_percent > 70 or cpu_percent > 70:
            adaptations["local_bias"] = max(0.2, self.routing_preferences["local_bias"] - 0.15)
            adaptations["parallel_threshold"] = min(0.8, self.routing_preferences["parallel_threshold"] + 0.1)
        
        # Battery conservation
        battery_percent = resources.get("battery_percent")
        if battery_percent and battery_percent < 30:
            adaptations["local_bias"] = min(0.9, self.routing_preferences["local_bias"] + 0.3)
            adaptations["timeout_multiplier"] = max(0.7, self.routing_preferences["timeout_multiplier"] - 0.2)
        
        return adaptations
    
    def _adapt_for_quality_focus(self, overall: Dict, local: Dict, api: Dict) -> Dict[str, Any]:
        """Optimize for response quality."""
        adaptations = {}
        
        # Compare quality between local and API
        local_quality = local.get("avg_quality_score", 0)
        api_quality = api.get("avg_quality_score", 0)
        
        if api_quality > local_quality + 0.1:  # API significantly better quality
            adaptations["local_bias"] = max(0.1, self.routing_preferences["local_bias"] - 0.2)
        elif local_quality > api_quality + 0.1:  # Local significantly better quality
            adaptations["local_bias"] = min(0.9, self.routing_preferences["local_bias"] + 0.2)
        
        # Increase timeouts for better quality
        adaptations["timeout_multiplier"] = min(1.5, self.routing_preferences["timeout_multiplier"] + 0.1)
        adaptations["quality_threshold"] = min(0.9, self.routing_preferences["quality_threshold"] + 0.05)
        
        return adaptations
    
    def _apply_adaptations(self, adaptations: Dict[str, Any]) -> None:
        """Apply the determined adaptations."""
        for key, value in adaptations.items():
            if key in self.routing_preferences:
                old_value = self.routing_preferences[key]
                self.routing_preferences[key] = value
                self.logger.debug(f"Updated {key}: {old_value} -> {value}")
    
    def get_routing_preferences(self) -> Dict[str, float]:
        """Get current routing preferences."""
        return self.routing_preferences.copy()
    
    def get_optimization_state(self) -> Dict[str, Any]:
        """Get current optimization state."""
        return {
            "strategy": self.current_strategy.value,
            "routing_preferences": self.routing_preferences,
            "last_adaptation_time": self.last_adaptation_time,
            "adaptation_count": len(self.adaptation_history),
            "recent_adaptations": list(self.adaptation_history)[-5:]  # Last 5 adaptations
        }


class DualTrackOptimizer:
    """Main optimizer for dual-track processing system."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__ + ".DualTrackOptimizer")
        
        # Initialize components
        self.metrics_collector = MetricsCollector(config)
        self.resource_monitor = ResourceMonitor(config)
        self.adaptive_optimizer = AdaptiveOptimizer(config, self.metrics_collector, self.resource_monitor)
        
        # Cache for optimization decisions
        self.decision_cache = {}
        self.cache_lock = threading.Lock()
        
        # Active request tracking
        self.active_requests = {}
        self.request_lock = threading.Lock()
        
        self._started = False
    
    def start(self) -> None:
        """Start the optimization system."""
        if self._started:
            return
        
        if self.config.enable_resource_monitoring:
            self.resource_monitor.start_monitoring()
        
        self._started = True
        self.logger.info("Dual-track optimizer started")
    
    def stop(self) -> None:
        """Stop the optimization system."""
        if not self._started:
            return
        
        self.resource_monitor.stop_monitoring()
        self._started = False
        self.logger.info("Dual-track optimizer stopped")
    
    def record_request_start(self, request_id: str, query: str, context: Optional[Dict] = None) -> None:
        """Record the start of a request for tracking."""
        with self.request_lock:
            self.active_requests[request_id] = {
                "start_time": time.time(),
                "query": query,
                "context": context,
                "resource_snapshot": self.resource_monitor.get_current_usage()
            }
    
    def record_request_completion(
        self, request_id: str, processing_path: str, result: Dict[str, Any], 
        success: bool = True, error_type: Optional[str] = None
    ) -> None:
        """Record the completion of a request."""
        with self.request_lock:
            if request_id not in self.active_requests:
                self.logger.warning(f"Request {request_id} not found in active requests")
                return
            
            request_info = self.active_requests.pop(request_id)
        
        # Calculate metrics
        end_time = time.time()
        latency_ms = (end_time - request_info["start_time"]) * 1000
        
        current_usage = self.resource_monitor.get_current_usage()
        memory_usage_mb = current_usage.get("memory_mb", 0)
        cpu_usage_percent = current_usage.get("cpu_percent", 0)
        gpu_usage_percent = current_usage.get("gpu_percent", 0)
        
        # Extract result information
        tokens_processed = result.get("tokens_used", 0) if result else 0
        cost_estimate = result.get("cost_estimate", 0.0) if result else 0.0
        quality_score = result.get("quality_score", 0.0) if result else 0.0
        
        # Create and record metric
        metric = PerformanceMetrics(
            timestamp=end_time,
            processing_path=processing_path,
            request_id=request_id,
            latency_ms=latency_ms,
            tokens_processed=tokens_processed,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent,
            gpu_usage_percent=gpu_usage_percent,
            cost_estimate=cost_estimate,
            quality_score=quality_score,
            success=success,
            error_type=error_type
        )
        
        self.metrics_collector.record_metric(metric)
    
    def get_optimization_recommendations(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Get optimization recommendations for a query."""
        try:
            # Check if we should adapt strategy
            if self.adaptive_optimizer.should_adapt():
                adaptation_result = self.adaptive_optimizer.adapt_strategy()
                if adaptation_result.get("adapted"):
                    self.logger.info(f"Strategy adapted: {adaptation_result.get('reason')}")
            
            # Get current routing preferences
            preferences = self.adaptive_optimizer.get_routing_preferences()
            
            # Check resource constraints
            resource_usage = self.resource_monitor.get_current_usage()
            violations = self.resource_monitor.check_constraints(self.config.constraints)
            
            # Check active request count
            with self.request_lock:
                active_count = len(self.active_requests)
            
            # Generate recommendations
            recommendations = {
                "routing_preferences": preferences,
                "resource_status": {
                    "current_usage": resource_usage,
                    "violations": violations,
                    "can_use_local": "memory" not in violations and "cpu" not in violations,
                    "can_use_parallel": len(violations) == 0 and active_count < self.config.constraints.max_concurrent_requests
                },
                "timeouts": {
                    "local_timeout_ms": int(1000 * preferences["timeout_multiplier"]),
                    "api_timeout_ms": int(5000 * preferences["timeout_multiplier"]),
                    "parallel_timeout_ms": int(3000 * preferences["timeout_multiplier"])
                },
                "caching": {
                    "enabled": self.config.enable_caching,
                    "ttl_seconds": self.config.cache_ttl_seconds
                },
                "active_requests": active_count,
                "max_concurrent": self.config.constraints.max_concurrent_requests
            }
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating optimization recommendations: {e}")
            return {
                "error": str(e),
                "routing_preferences": self.adaptive_optimizer.get_routing_preferences(),
                "resource_status": {"violations": {}, "can_use_local": True, "can_use_parallel": True},
                "timeouts": {"local_timeout_ms": 1000, "api_timeout_ms": 5000, "parallel_timeout_ms": 3000},
                "active_requests": 0
            }
    
    def get_metrics_summary(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics summary."""
        return self.metrics_collector.get_metrics_summary(path)
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get comprehensive optimization status."""
        return {
            "config": {
                "strategy": self.config.strategy.value,
                "constraints": {
                    "max_memory_mb": self.config.constraints.max_memory_mb,
                    "max_cpu_percent": self.config.constraints.max_cpu_percent,
                    "target_latency_ms": self.config.constraints.target_latency_ms,
                    "max_cost_per_request": self.config.constraints.max_cost_per_request,
                    "max_concurrent_requests": self.config.constraints.max_concurrent_requests
                },
                "adaptation_interval_seconds": self.config.adaptation_interval_seconds,
                "enable_caching": self.config.enable_caching,
                "enable_resource_monitoring": self.config.enable_resource_monitoring
            },
            "current_state": self.adaptive_optimizer.get_optimization_state(),
            "resource_usage": self.resource_monitor.get_current_usage(),
            "metrics_summary": self.metrics_collector.get_metrics_summary(),
            "active_requests": len(self.active_requests),
            "started": self._started
        }


# Utility functions for integration with existing dual-track system
def create_default_optimizer() -> DualTrackOptimizer:
    """Create a dual-track optimizer with default configuration."""
    config = OptimizationConfig()
    return DualTrackOptimizer(config)


def create_optimized_config(strategy: OptimizationStrategy = OptimizationStrategy.ADAPTIVE) -> OptimizationConfig:
    """Create an optimization config optimized for specific strategy."""
    config = OptimizationConfig(strategy=strategy)
    
    if strategy == OptimizationStrategy.LATENCY_FOCUSED:
        config.constraints.target_latency_ms = 1000.0
        config.adaptation_interval_seconds = 15.0
        config.enable_preemption = True
        
    elif strategy == OptimizationStrategy.RESOURCE_EFFICIENT:
        config.constraints.max_memory_mb = 2048.0
        config.constraints.max_cpu_percent = 60.0
        config.enable_caching = True
        config.cache_ttl_seconds = 600.0
        
    elif strategy == OptimizationStrategy.QUALITY_FOCUSED:
        config.constraints.target_latency_ms = 5000.0
        config.constraints.max_cost_per_request = 0.05
        config.adaptation_interval_seconds = 60.0
        
    return config