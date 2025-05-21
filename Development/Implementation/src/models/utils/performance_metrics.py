"""
Performance monitoring utilities for model inference.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import time
import logging
import threading
import psutil
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class InferenceStats:
    """Simple class to track statistics for model inference."""
    
    def __init__(self):
        """Initialize inference statistics tracking."""
        self.total_inferences = 0
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.total_time_ms = 0
        self.max_time_ms = 0
        self.min_time_ms = float('inf')
        
        # Keep track of recent inferences for moving averages
        self.recent_times = []
        self.max_recent = 100  # Number of recent inferences to track
    
    def record_inference(self, tokens_in: int, tokens_out: int, time_ms: float) -> None:
        """
        Record statistics for an inference.
        
        Args:
            tokens_in: Number of input tokens
            tokens_out: Number of output tokens
            time_ms: Time taken in milliseconds
        """
        self.total_inferences += 1
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out
        self.total_time_ms += time_ms
        
        self.max_time_ms = max(self.max_time_ms, time_ms)
        if time_ms > 0:
            self.min_time_ms = min(self.min_time_ms, time_ms)
        
        # Add to recent times
        self.recent_times.append(time_ms)
        if len(self.recent_times) > self.max_recent:
            self.recent_times.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current inference statistics.
        
        Returns:
            Dictionary of inference statistics
        """
        stats = {
            "total_inferences": self.total_inferences,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "avg_tokens_per_inference": (self.total_tokens_out / self.total_inferences) if self.total_inferences > 0 else 0,
            "avg_time_ms": (self.total_time_ms / self.total_inferences) if self.total_inferences > 0 else 0,
            "avg_tokens_per_second": (self.total_tokens_out / (self.total_time_ms / 1000)) if self.total_time_ms > 0 else 0,
            "max_time_ms": self.max_time_ms,
            "min_time_ms": self.min_time_ms if self.min_time_ms != float('inf') else 0,
        }
        
        # Add recent stats if available
        if self.recent_times:
            stats["recent_avg_time_ms"] = sum(self.recent_times) / len(self.recent_times)
        
        return stats
    
    def reset(self) -> None:
        """Reset all statistics."""
        self.__init__()


class ResourceMonitor:
    """Monitor system resources during model inference."""
    
    def __init__(self, polling_interval: float = 1.0):
        """
        Initialize the resource monitor.
        
        Args:
            polling_interval: Interval in seconds between resource checks
        """
        self.polling_interval = polling_interval
        self.monitoring = False
        self.monitor_thread = None
        
        self.cpu_usage = []
        self.memory_usage = []
        self.timestamps = []
        
        self.peak_memory = 0
        self.peak_cpu = 0
    
    def start(self) -> None:
        """Start resource monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Resource monitoring started")
    
    def stop(self) -> None:
        """Stop resource monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
            self.monitor_thread = None
        
        logger.info("Resource monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Internal monitoring loop."""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                # Get current resource usage
                cpu_percent = process.cpu_percent(interval=None)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                
                # Update peaks
                self.peak_cpu = max(self.peak_cpu, cpu_percent)
                self.peak_memory = max(self.peak_memory, memory_mb)
                
                # Add to history
                self.cpu_usage.append(cpu_percent)
                self.memory_usage.append(memory_mb)
                self.timestamps.append(time.time())
                
                # Limit the size of history lists
                max_history = 1000
                if len(self.cpu_usage) > max_history:
                    self.cpu_usage = self.cpu_usage[-max_history:]
                    self.memory_usage = self.memory_usage[-max_history:]
                    self.timestamps = self.timestamps[-max_history:]
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
            
            # Sleep for polling interval
            time.sleep(self.polling_interval)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current resource statistics.
        
        Returns:
            Dictionary of resource statistics
        """
        if not self.memory_usage:
            return {
                "current_memory_mb": 0,
                "peak_memory_mb": 0,
                "current_cpu_percent": 0,
                "peak_cpu_percent": 0,
                "avg_memory_mb": 0,
                "avg_cpu_percent": 0,
            }
        
        current_memory = self.memory_usage[-1] if self.memory_usage else 0
        current_cpu = self.cpu_usage[-1] if self.cpu_usage else 0
        
        return {
            "current_memory_mb": current_memory,
            "peak_memory_mb": self.peak_memory,
            "current_cpu_percent": current_cpu,
            "peak_cpu_percent": self.peak_cpu,
            "avg_memory_mb": sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0,
            "avg_cpu_percent": sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0,
        }
    
    def reset(self) -> None:
        """Reset statistics."""
        self.cpu_usage = []
        self.memory_usage = []
        self.timestamps = []
        self.peak_memory = 0
        self.peak_cpu = 0


class PerformanceTracker:
    """Track performance metrics for model inference."""
    
    def __init__(self):
        """Initialize the performance tracker."""
        self.inference_stats = InferenceStats()
        self.resource_monitor = ResourceMonitor()
        self.started = False
    
    def start_tracking(self) -> None:
        """Start performance tracking."""
        if not self.started:
            self.resource_monitor.start()
            self.started = True
    
    def stop_tracking(self) -> None:
        """Stop performance tracking."""
        if self.started:
            self.resource_monitor.stop()
            self.started = False
    
    def reset(self) -> None:
        """Reset all statistics."""
        self.inference_stats.reset()
        self.resource_monitor.reset()
    
    def record_inference(self, tokens_in: int, tokens_out: int, time_ms: float) -> None:
        """
        Record an inference event.
        
        Args:
            tokens_in: Number of input tokens
            tokens_out: Number of output tokens
            time_ms: Time taken in milliseconds
        """
        self.inference_stats.record_inference(tokens_in, tokens_out, time_ms)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics.
        
        Returns:
            Dictionary of performance statistics
        """
        stats = {
            "inference": self.inference_stats.get_stats(),
            "resources": self.resource_monitor.get_stats(),
            "timestamp": time.time(),
        }
        
        return stats