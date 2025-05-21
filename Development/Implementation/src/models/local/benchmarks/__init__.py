"""
Local model benchmarking subpackage.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

from .benchmark_suite import BenchmarkRunner
from .latency_tests import run_latency_benchmark
from .memory_tests import run_memory_benchmark
from .throughput_tests import run_throughput_benchmark
