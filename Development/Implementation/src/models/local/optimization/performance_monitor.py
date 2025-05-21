"""
Performance monitoring for local model inference.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import time
import logging
import json
import datetime
from typing import Dict, Any, Optional, List, Tuple
import threading
import statistics

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil not available, some memory metrics will be disabled")
    PSUTIL_AVAILABLE = False


class PerformanceMonitor:
    """Monitors and reports on model performance."""
    
    def __init__(self, model_id: Optional[str] = None):
        """Initialize the performance monitor.
        
        Args:
            model_id: Optional ID of the model being monitored
        """
        self.model_id = model_id
        self.metrics = self._create_empty_metrics()
        self.is_monitoring = False
        self.start_memory = 0
        self.monitoring_thread = None
        self.stop_monitoring_flag = threading.Event()
        
    def _create_empty_metrics(self) -> Dict[str, Any]:
        """Create empty metrics dictionary.
        
        Returns:
            Empty metrics dictionary with default values
        """
        return {
            "inference_count": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_latency": 0,
            "latencies": [],
            "tokens_per_second": [],
            "max_latency": 0,
            "min_latency": float('inf'),
            "start_time": None,
            "end_time": None,
            "start_memory_gb": 0,
            "current_memory_gb": 0,
            "peak_memory_gb": 0,
            "memory_samples": []
        }
        
    def start_monitoring(self, sample_memory: bool = True, sample_interval: float = 0.5) -> bool:
        """Begin collecting performance metrics.
        
        Args:
            sample_memory: Whether to periodically sample memory usage
            sample_interval: Interval in seconds between memory samples
            
        Returns:
            True if monitoring started successfully
        """
        if self.is_monitoring:
            logger.warning("Monitoring already started, resetting metrics")
            self.reset_metrics()
            return True
            
        self.metrics["start_time"] = time.time()
        self.is_monitoring = True
        
        # Sample initial memory
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            memory_info = process.memory_info()
            self.start_memory = memory_info.rss / (1024 * 1024 * 1024)  # GB
            self.metrics["start_memory_gb"] = self.start_memory
            self.metrics["current_memory_gb"] = self.start_memory
            self.metrics["peak_memory_gb"] = self.start_memory
            
            # Start memory sampling thread if requested
            if sample_memory:
                self.stop_monitoring_flag.clear()
                self.monitoring_thread = threading.Thread(
                    target=self._memory_sampling_thread,
                    args=(sample_interval,),
                    daemon=True
                )
                self.monitoring_thread.start()
                
        logger.debug(f"Started performance monitoring for {'model ' + self.model_id if self.model_id else 'unknown model'}")
        return True
        
    def _memory_sampling_thread(self, interval: float) -> None:
        """Background thread for sampling memory usage.
        
        Args:
            interval: Sampling interval in seconds
        """
        if not PSUTIL_AVAILABLE:
            return
            
        process = psutil.Process()
        
        while not self.stop_monitoring_flag.is_set() and self.is_monitoring:
            try:
                memory_info = process.memory_info()
                current_memory = memory_info.rss / (1024 * 1024 * 1024)  # GB
                
                self.metrics["current_memory_gb"] = current_memory
                self.metrics["peak_memory_gb"] = max(self.metrics["peak_memory_gb"], current_memory)
                
                # Add timestamped memory sample
                self.metrics["memory_samples"].append({
                    "timestamp": time.time() - self.metrics["start_time"],
                    "memory_gb": current_memory
                })
                
                # Sleep for specified interval
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in memory sampling thread: {e}")
                break
        
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop collecting performance metrics.
        
        Returns:
            Current metrics snapshot
        """
        if not self.is_monitoring:
            logger.warning("Monitoring not started, nothing to stop")
            return self.metrics
            
        self.metrics["end_time"] = time.time()
        self.is_monitoring = False
        
        # Stop memory sampling thread if running
        if self.monitoring_thread is not None and self.monitoring_thread.is_alive():
            self.stop_monitoring_flag.set()
            self.monitoring_thread.join(timeout=1.0)
            self.monitoring_thread = None
            
        # Calculate final derived metrics
        self._calculate_derived_metrics()
        
        logger.debug(f"Stopped performance monitoring for {'model ' + self.model_id if self.model_id else 'unknown model'}")
        return self.get_metrics()
        
    def record_inference(self, 
                        prompt_tokens: int,
                        completion_tokens: int, 
                        latency: float) -> None:
        """Record a single inference operation.
        
        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens generated
            latency: Time taken in seconds
        """
        if not self.is_monitoring:
            logger.warning("Monitoring not started, inference not recorded")
            return
            
        self.metrics["inference_count"] += 1
        self.metrics["prompt_tokens"] += prompt_tokens
        self.metrics["completion_tokens"] += completion_tokens
        self.metrics["total_tokens"] += prompt_tokens + completion_tokens
        self.metrics["total_latency"] += latency
        self.metrics["latencies"].append(latency)
        
        token_per_second = completion_tokens / latency if latency > 0 else 0
        self.metrics["tokens_per_second"].append(token_per_second)
        
        self.metrics["max_latency"] = max(self.metrics["max_latency"], latency)
        self.metrics["min_latency"] = min(self.metrics["min_latency"], latency)
        
        # Sample memory if psutil available
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                current_memory = memory_info.rss / (1024 * 1024 * 1024)  # GB
                
                self.metrics["current_memory_gb"] = current_memory
                self.metrics["peak_memory_gb"] = max(self.metrics["peak_memory_gb"], current_memory)
            except Exception as e:
                logger.error(f"Error sampling memory: {e}")
                
        logger.debug(f"Recorded inference: {completion_tokens} tokens in {latency:.4f}s ({token_per_second:.2f} tokens/sec)")
        
    def _calculate_derived_metrics(self) -> None:
        """Calculate derived metrics from raw measurements."""
        metrics = self.metrics
        
        # Only calculate if we have data
        if metrics["inference_count"] > 0:
            metrics["avg_latency"] = metrics["total_latency"] / metrics["inference_count"]
            
            # Calculate median and percentiles if we have multiple latencies
            if len(metrics["latencies"]) > 1:
                metrics["median_latency"] = statistics.median(metrics["latencies"])
                sorted_latencies = sorted(metrics["latencies"])
                metrics["p90_latency"] = sorted_latencies[int(len(sorted_latencies) * 0.9)]
                metrics["p95_latency"] = sorted_latencies[int(len(sorted_latencies) * 0.95)]
                metrics["p99_latency"] = sorted_latencies[int(len(sorted_latencies) * 0.99)]
                
                metrics["latency_std"] = statistics.stdev(metrics["latencies"]) if len(metrics["latencies"]) > 1 else 0
            else:
                metrics["median_latency"] = metrics["avg_latency"]
                metrics["p90_latency"] = metrics["avg_latency"]
                metrics["p95_latency"] = metrics["avg_latency"]
                metrics["p99_latency"] = metrics["avg_latency"]
                metrics["latency_std"] = 0
            
            # Token generation stats
            if metrics["total_latency"] > 0:
                metrics["avg_tokens_per_second"] = metrics["completion_tokens"] / metrics["total_latency"]
            
            # If we have token-per-second measurements
            if len(metrics["tokens_per_second"]) > 0:
                metrics["median_tokens_per_second"] = statistics.median(metrics["tokens_per_second"])
                
        # Calculate duration if timing available
        if metrics["start_time"] and metrics["end_time"]:
            metrics["duration"] = metrics["end_time"] - metrics["start_time"]
            
        # Calculate memory change
        if metrics["start_memory_gb"] > 0:
            metrics["memory_change_gb"] = metrics["peak_memory_gb"] - metrics["start_memory_gb"]
            
    def get_metrics(self, calculate_derived: bool = True) -> Dict[str, Any]:
        """Get current performance metrics.
        
        Args:
            calculate_derived: Whether to calculate derived metrics before returning
            
        Returns:
            Dictionary of current metrics
        """
        # Calculate derived metrics if requested
        if calculate_derived:
            self._calculate_derived_metrics()
            
        # Create a copy to avoid external modifications
        metrics = self.metrics.copy()
        
        # Add timestamp for when these metrics were retrieved
        metrics["retrieved_at"] = time.time()
        metrics["model_id"] = self.model_id
        
        return metrics
        
    def reset_metrics(self) -> None:
        """Reset all metrics to initial state.
        
        Note: This maintains the current monitoring state but clears all data.
        """
        # Store current monitoring state
        was_monitoring = self.is_monitoring
        
        # Stop monitoring if active
        if was_monitoring:
            self.stop_monitoring()
            
        # Reset metrics
        self.metrics = self._create_empty_metrics()
        
        # Restart monitoring if it was active
        if was_monitoring:
            self.start_monitoring()
            
        logger.debug("Performance metrics reset")
        
    def export_report(self, format: str = "json", include_samples: bool = True) -> str:
        """Export a performance report.
        
        Args:
            format: Output format ("json", "text", "csv")
            include_samples: Whether to include detailed sample data
            
        Returns:
            Formatted performance report
        """
        # Get current metrics
        metrics = self.get_metrics()
        
        # Remove sample data if not requested to keep output cleaner
        if not include_samples:
            if "latencies" in metrics:
                del metrics["latencies"]
            if "tokens_per_second" in metrics:
                del metrics["tokens_per_second"]
            if "memory_samples" in metrics:
                del metrics["memory_samples"]
        
        # Format as requested
        if format == "json":
            return json.dumps(metrics, indent=2)
            
        elif format == "text":
            report_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            duration = metrics.get("duration", 0)
            
            lines = [
                f"Performance Report ({report_time})",
                "=" * 50,
                f"Model: {self.model_id or 'Unknown'}",
                f"Duration: {duration:.2f}s",
                "",
                "Inference Statistics:",
                f"  Total inferences: {metrics['inference_count']}",
                f"  Prompt tokens: {metrics['prompt_tokens']}",
                f"  Completion tokens: {metrics['completion_tokens']}",
                f"  Total tokens: {metrics['total_tokens']}",
                "",
                "Latency:",
                f"  Average: {metrics.get('avg_latency', 0):.4f}s",
                f"  Median: {metrics.get('median_latency', 0):.4f}s",
                f"  Min: {metrics['min_latency']:.4f}s",
                f"  Max: {metrics['max_latency']:.4f}s",
                f"  P90: {metrics.get('p90_latency', 0):.4f}s",
                f"  P95: {metrics.get('p95_latency', 0):.4f}s",
                f"  P99: {metrics.get('p99_latency', 0):.4f}s",
                "",
                "Throughput:",
                f"  Average: {metrics.get('avg_tokens_per_second', 0):.2f} tokens/sec",
                f"  Median: {metrics.get('median_tokens_per_second', 0):.2f} tokens/sec",
                "",
                "Memory Usage:",
                f"  Starting: {metrics['start_memory_gb']:.2f} GB",
                f"  Peak: {metrics['peak_memory_gb']:.2f} GB",
                f"  Change: {metrics.get('memory_change_gb', 0):.2f} GB",
            ]
            return "\n".join(lines)
            
        elif format == "csv":
            # Basic CSV for the key metrics
            header = [
                "model_id", "inferences", "prompt_tokens", "completion_tokens", 
                "avg_latency", "median_latency", "p90_latency", "p95_latency", 
                "avg_tokens_per_second", "peak_memory_gb", "duration"
            ]
            
            values = [
                self.model_id or "Unknown",
                str(metrics["inference_count"]),
                str(metrics["prompt_tokens"]),
                str(metrics["completion_tokens"]),
                f"{metrics.get('avg_latency', 0):.4f}",
                f"{metrics.get('median_latency', 0):.4f}",
                f"{metrics.get('p90_latency', 0):.4f}",
                f"{metrics.get('p95_latency', 0):.4f}",
                f"{metrics.get('avg_tokens_per_second', 0):.2f}",
                f"{metrics['peak_memory_gb']:.2f}",
                f"{metrics.get('duration', 0):.2f}"
            ]
            
            return ",".join(header) + "\n" + ",".join(values)
            
        else:
            logger.warning(f"Unknown format '{format}', defaulting to JSON")
            return json.dumps(metrics, indent=2)