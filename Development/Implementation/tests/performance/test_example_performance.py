# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

"""Example performance tests to demonstrate testing approach."""

import pytest
import time
import numpy as np
from tests.utils.performance_utils import performance_benchmark

@performance_benchmark(repeat=3)
def process_large_array(size):
    """Example function for performance testing."""
    arr = np.random.random((size, size))
    result = np.dot(arr, arr.T)
    return result.sum()

class TestExamplePerformance:
    """Example performance tests."""
    
    def test_array_processing_performance(self):
        """Test the performance of array processing."""
        # Run benchmark
        result = process_large_array(1000)
        
        # Assert performance criteria
        assert result["time"]["avg"] < 10.0, "Processing took too long"
        assert result["memory"]["avg"] < 1000, "Processing used too much memory"