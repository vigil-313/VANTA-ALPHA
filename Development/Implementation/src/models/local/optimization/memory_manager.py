"""
Memory management for local model optimization.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import os
import platform
import logging
import time
import threading
import gc
from typing import Dict, Any, Optional, List, Tuple, Union, Callable

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil not available, some memory features will be limited")
    PSUTIL_AVAILABLE = False


class MemoryManager:
    """Manages memory usage for local models."""
    
    def __init__(self, 
                memory_limit_gb: float = 8.0, 
                warning_threshold: float = 0.8,
                critical_threshold: float = 0.95,
                enable_monitoring: bool = True,
                monitoring_interval: float = 2.0):
        """Initialize the memory manager.
        
        Args:
            memory_limit_gb: Maximum allowed memory usage in GB
            warning_threshold: Threshold for warning (fraction of limit)
            critical_threshold: Threshold for critical warning (fraction of limit)
            enable_monitoring: Whether to enable background monitoring
            monitoring_interval: Interval between monitoring checks in seconds
        """
        self.memory_limit_gb = memory_limit_gb
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.enable_monitoring = enable_monitoring
        self.monitoring_interval = monitoring_interval
        
        # Memory monitoring
        self.peak_memory_gb = 0.0
        self.current_memory_gb = 0.0
        self.start_memory_gb = 0.0
        self.memory_samples = []
        
        # Warning handlers
        self.warning_handlers = []
        self.critical_handlers = []
        
        # Background monitoring thread
        self.monitoring_thread = None
        self.stop_monitoring_flag = threading.Event()
        
        # Start monitoring if enabled
        if self.enable_monitoring and PSUTIL_AVAILABLE:
            self.start_monitoring()
            
        logger.debug(f"MemoryManager initialized with {memory_limit_gb}GB limit")
        
    def start_monitoring(self) -> bool:
        """Start memory usage monitoring.
        
        Returns:
            True if monitoring started successfully
        """
        if not PSUTIL_AVAILABLE:
            logger.warning("Cannot start memory monitoring: psutil not available")
            return False
            
        if self.monitoring_thread is not None and self.monitoring_thread.is_alive():
            logger.warning("Memory monitoring already running")
            return True
            
        # Sample initial memory
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            self.start_memory_gb = memory_info.rss / (1024 * 1024 * 1024)
            self.current_memory_gb = self.start_memory_gb
            self.peak_memory_gb = self.start_memory_gb
            
            # Start monitoring thread
            self.stop_monitoring_flag.clear()
            self.monitoring_thread = threading.Thread(
                target=self._memory_monitoring_thread,
                daemon=True
            )
            self.monitoring_thread.start()
            
            logger.debug(f"Started memory monitoring thread, initial memory: {self.start_memory_gb:.2f}GB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start memory monitoring: {e}")
            return False
            
    def _memory_monitoring_thread(self) -> None:
        """Background thread for monitoring memory usage."""
        if not PSUTIL_AVAILABLE:
            return
            
        process = psutil.Process()
        start_time = time.time()
        
        while not self.stop_monitoring_flag.is_set():
            try:
                # Sample memory usage
                memory_info = process.memory_info()
                current_memory = memory_info.rss / (1024 * 1024 * 1024)  # GB
                
                self.current_memory_gb = current_memory
                
                # Update peak memory
                if current_memory > self.peak_memory_gb:
                    self.peak_memory_gb = current_memory
                
                # Add sample
                self.memory_samples.append({
                    "timestamp": time.time() - start_time,
                    "memory_gb": current_memory
                })
                
                # Keep only the most recent 1000 samples
                if len(self.memory_samples) > 1000:
                    self.memory_samples = self.memory_samples[-1000:]
                
                # Check for warning threshold
                if current_memory >= self.memory_limit_gb * self.warning_threshold:
                    self._trigger_warning_handlers(current_memory)
                    
                # Check for critical threshold
                if current_memory >= self.memory_limit_gb * self.critical_threshold:
                    self._trigger_critical_handlers(current_memory)
                
                # Sleep for the monitoring interval
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in memory monitoring thread: {e}")
                break
    
    def _trigger_warning_handlers(self, current_memory_gb: float) -> None:
        """Trigger warning handlers when memory usage exceeds warning threshold.
        
        Args:
            current_memory_gb: Current memory usage in GB
        """
        for handler in self.warning_handlers:
            try:
                handler(current_memory_gb, self.memory_limit_gb)
            except Exception as e:
                logger.error(f"Error in memory warning handler: {e}")
    
    def _trigger_critical_handlers(self, current_memory_gb: float) -> None:
        """Trigger critical handlers when memory usage exceeds critical threshold.
        
        Args:
            current_memory_gb: Current memory usage in GB
        """
        for handler in self.critical_handlers:
            try:
                handler(current_memory_gb, self.memory_limit_gb)
            except Exception as e:
                logger.error(f"Error in memory critical handler: {e}")
    
    def stop_monitoring(self) -> None:
        """Stop memory usage monitoring."""
        if self.monitoring_thread is not None and self.monitoring_thread.is_alive():
            self.stop_monitoring_flag.set()
            self.monitoring_thread.join(timeout=1.0)
            self.monitoring_thread = None
            logger.debug("Stopped memory monitoring thread")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory usage statistics.
        
        Returns:
            Dictionary with memory usage statistics
        """
        stats = {
            "current_memory_gb": self.current_memory_gb,
            "peak_memory_gb": self.peak_memory_gb,
            "memory_limit_gb": self.memory_limit_gb,
            "start_memory_gb": self.start_memory_gb,
            "memory_growth_gb": self.peak_memory_gb - self.start_memory_gb,
            "utilization_percent": (self.current_memory_gb / self.memory_limit_gb) * 100,
            "peak_utilization_percent": (self.peak_memory_gb / self.memory_limit_gb) * 100,
            "warning_threshold_gb": self.memory_limit_gb * self.warning_threshold,
            "critical_threshold_gb": self.memory_limit_gb * self.critical_threshold,
            "monitoring_active": self.monitoring_thread is not None and self.monitoring_thread.is_alive(),
        }
        
        # Add system memory info if psutil is available
        if PSUTIL_AVAILABLE:
            try:
                system_memory = psutil.virtual_memory()
                stats.update({
                    "system_total_memory_gb": system_memory.total / (1024 * 1024 * 1024),
                    "system_available_memory_gb": system_memory.available / (1024 * 1024 * 1024),
                    "system_used_memory_gb": (system_memory.total - system_memory.available) / (1024 * 1024 * 1024),
                    "system_memory_percent": system_memory.percent
                })
            except Exception as e:
                logger.error(f"Error getting system memory info: {e}")
                
        return stats
    
    def register_warning_handler(self, handler: Callable[[float, float], None]) -> None:
        """Register a handler for memory warning events.
        
        Args:
            handler: Function to call with (current_memory_gb, memory_limit_gb)
        """
        if handler not in self.warning_handlers:
            self.warning_handlers.append(handler)
    
    def register_critical_handler(self, handler: Callable[[float, float], None]) -> None:
        """Register a handler for memory critical events.
        
        Args:
            handler: Function to call with (current_memory_gb, memory_limit_gb)
        """
        if handler not in self.critical_handlers:
            self.critical_handlers.append(handler)
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Attempt to optimize memory usage.
        
        Returns:
            Dictionary with the results of optimization
        """
        start_memory = self.current_memory_gb
        
        # Force garbage collection
        gc.collect()
        
        # Update current memory
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                self.current_memory_gb = memory_info.rss / (1024 * 1024 * 1024)
            except Exception as e:
                logger.error(f"Error updating memory usage: {e}")
        
        # Calculate memory freed
        memory_freed = start_memory - self.current_memory_gb
        
        return {
            "action": "optimize_memory",
            "memory_before_gb": start_memory,
            "memory_after_gb": self.current_memory_gb,
            "memory_freed_gb": memory_freed,
            "successful": memory_freed > 0
        }
    
    def get_system_memory_info(self) -> Dict[str, Any]:
        """Get system-wide memory information.
        
        Returns:
            Dictionary with system memory information
        """
        if not PSUTIL_AVAILABLE:
            return {
                "error": "psutil not available",
                "psutil_available": False
            }
            
        try:
            system_memory = psutil.virtual_memory()
            swap_memory = psutil.swap_memory()
            
            return {
                "psutil_available": True,
                "total_memory_gb": system_memory.total / (1024 * 1024 * 1024),
                "available_memory_gb": system_memory.available / (1024 * 1024 * 1024),
                "used_memory_gb": (system_memory.total - system_memory.available) / (1024 * 1024 * 1024),
                "memory_percent": system_memory.percent,
                "swap_total_gb": swap_memory.total / (1024 * 1024 * 1024),
                "swap_used_gb": swap_memory.used / (1024 * 1024 * 1024),
                "swap_percent": swap_memory.percent
            }
        except Exception as e:
            logger.error(f"Error getting system memory info: {e}")
            return {
                "psutil_available": True,
                "error": str(e)
            }
    
    def default_warning_handler(self, current_memory_gb: float, memory_limit_gb: float) -> None:
        """Default handler for memory warnings.
        
        Args:
            current_memory_gb: Current memory usage in GB
            memory_limit_gb: Memory usage limit in GB
        """
        percent = (current_memory_gb / memory_limit_gb) * 100
        logger.warning(f"Memory usage warning: {current_memory_gb:.2f}GB ({percent:.1f}% of {memory_limit_gb:.2f}GB limit)")
        
        # Force garbage collection
        gc.collect()
    
    def default_critical_handler(self, current_memory_gb: float, memory_limit_gb: float) -> None:
        """Default handler for critical memory warnings.
        
        Args:
            current_memory_gb: Current memory usage in GB
            memory_limit_gb: Memory usage limit in GB
        """
        percent = (current_memory_gb / memory_limit_gb) * 100
        logger.error(f"CRITICAL memory usage: {current_memory_gb:.2f}GB ({percent:.1f}% of {memory_limit_gb:.2f}GB limit)")
        
        # Force garbage collection
        gc.collect()
        
        # Sleep briefly to allow other threads to free memory
        time.sleep(0.1)
        
    def memory_usage_report(self) -> str:
        """Generate a memory usage report.
        
        Returns:
            Formatted memory usage report
        """
        stats = self.get_memory_stats()
        
        lines = [
            "Memory Usage Report",
            "===================="
        ]
        
        # Process memory
        lines.extend([
            f"Process Memory:",
            f"  Current usage: {stats['current_memory_gb']:.2f}GB",
            f"  Peak usage: {stats['peak_memory_gb']:.2f}GB",
            f"  Memory limit: {stats['memory_limit_gb']:.2f}GB",
            f"  Current utilization: {stats['utilization_percent']:.1f}%",
            f"  Peak utilization: {stats['peak_utilization_percent']:.1f}%",
            f"  Memory growth: {stats['memory_growth_gb']:.2f}GB since start"
        ])
        
        # System memory
        if "system_total_memory_gb" in stats:
            lines.extend([
                f"\nSystem Memory:",
                f"  Total memory: {stats['system_total_memory_gb']:.2f}GB",
                f"  Available memory: {stats['system_available_memory_gb']:.2f}GB",
                f"  Used memory: {stats['system_used_memory_gb']:.2f}GB",
                f"  Memory utilization: {stats['system_memory_percent']:.1f}%"
            ])
            
        return "\n".join(lines)
        
    def check_memory_sufficient(self, required_gb: float) -> Dict[str, Any]:
        """Check if sufficient memory is available.
        
        Args:
            required_gb: Required memory in GB
            
        Returns:
            Dictionary with check results
        """
        result = {
            "required_gb": required_gb,
            "memory_limit_gb": self.memory_limit_gb,
            "current_usage_gb": self.current_memory_gb,
            "available_gb": self.memory_limit_gb - self.current_memory_gb,
            "sufficient": (self.memory_limit_gb - self.current_memory_gb) >= required_gb
        }
        
        if PSUTIL_AVAILABLE:
            try:
                system_memory = psutil.virtual_memory()
                result.update({
                    "system_available_gb": system_memory.available / (1024 * 1024 * 1024),
                    "system_sufficient": (system_memory.available / (1024 * 1024 * 1024)) >= required_gb
                })
            except Exception as e:
                logger.error(f"Error checking system memory: {e}")
                
        return result