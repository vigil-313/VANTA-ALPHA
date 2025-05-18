# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

import time
import psutil
import numpy as np
from typing import Dict, Any, List, Optional, Callable, Tuple
from functools import wraps

def measure_execution_time(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """
    Measure the execution time of a function.
    
    Args:
        func: Function to measure
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Tuple of (function result, execution time in seconds)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    
    return result, end_time - start_time

def measure_memory_usage(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """
    Measure the peak memory usage of a function.
    
    Args:
        func: Function to measure
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Tuple of (function result, peak memory usage in MB)
    """
    process = psutil.Process()
    start_memory = process.memory_info().rss / (1024 * 1024)  # Convert to MB
    
    result = func(*args, **kwargs)
    
    end_memory = process.memory_info().rss / (1024 * 1024)  # Convert to MB
    
    return result, end_memory - start_memory

def performance_benchmark(repeat: int = 5) -> Callable:
    """
    Decorator to benchmark the performance of a function.
    
    Args:
        repeat: Number of times to repeat the measurement
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            times = []
            memory_usages = []
            
            for _ in range(repeat):
                # Time measurement
                result, execution_time = measure_execution_time(func, *args, **kwargs)
                times.append(execution_time)
                
                # Memory measurement
                _, memory_usage = measure_memory_usage(func, *args, **kwargs)
                memory_usages.append(memory_usage)
            
            # Calculate statistics
            avg_time = np.mean(times)
            min_time = np.min(times)
            max_time = np.max(times)
            std_time = np.std(times)
            
            avg_memory = np.mean(memory_usages)
            max_memory = np.max(memory_usages)
            
            return {
                "result": result,
                "time": {
                    "avg": avg_time,
                    "min": min_time,
                    "max": max_time,
                    "std": std_time
                },
                "memory": {
                    "avg": avg_memory,
                    "max": max_memory
                }
            }
        
        return wrapper
    
    return decorator