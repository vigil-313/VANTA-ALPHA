"""
Local model optimization subpackage.

# TASK-REF: LM_002 - Local Model Optimization
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# CONCEPT-REF: CON-LM-002 - Local Model Optimization
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

from .optimization_config import OptimizationConfig
from .performance_monitor import PerformanceMonitor
from .quantization import QuantizationManager
from .metal_config import MetalAccelerationManager
from .memory_manager import MemoryManager
from .thread_optimizer import ThreadOptimizer
