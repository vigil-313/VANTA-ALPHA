# TASK-REF: DP-001 - Processing Router Implementation
# TASK-REF: DP-003 - Dual-Track Optimization
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Optimization
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification
# DECISION-REF: DEC-042-001 - Implement comprehensive conditional routing

"""
Dual-Track Processing Module

This module implements the core dual-track processing system that routes queries
between local and API models, coordinates their execution, and integrates responses.
"""

# Core classes
from .router import ProcessingRouter, RoutingDecision, QueryFeatures
from .local_model import LocalModel, LocalModelController, LocalModelResponse
from .api_client import APIClient, APIModelController, APIModelResponse
from .integrator import ResponseIntegrator, IntegrationResult
from .optimizer import (
    DualTrackOptimizer, MetricsCollector, ResourceMonitor, AdaptiveOptimizer,
    PerformanceMetrics, ResourceConstraints, OptimizationConfig, OptimizationStrategy,
    create_default_optimizer, create_optimized_config
)

# Configuration
from .config import (
    DualTrackConfig, RouterConfig, LocalModelConfig, APIModelConfig, IntegrationConfig,
    ProcessingPath, IntegrationStrategy, InterruptStyle, DEFAULT_CONFIG
)

# Exceptions
from .exceptions import (
    DualTrackError, RouterError, LocalModelError, ModelLoadError, GenerationError,
    APIModelError, APIConnectionError, APIRateLimitError, APITimeoutError,
    IntegrationError, ConfigurationError, TimeoutError, ResourceError,
    DualTrackOptimizationError, MetricsCollectionError, ResourceMonitoringError, AdaptationError
)

# Convenience functions
from .router import determine_path, calculate_query_features
from .integrator import integrate_responses

__all__ = [
    # Core classes
    "ProcessingRouter",
    "LocalModel", 
    "LocalModelController",
    "APIClient",
    "APIModelController", 
    "ResponseIntegrator",
    "DualTrackOptimizer",
    "MetricsCollector",
    "ResourceMonitor",
    "AdaptiveOptimizer",
    
    # Data classes
    "RoutingDecision",
    "QueryFeatures",
    "LocalModelResponse",
    "APIModelResponse", 
    "IntegrationResult",
    "PerformanceMetrics",
    "ResourceConstraints",
    "OptimizationConfig",
    
    # Configuration
    "DualTrackConfig",
    "RouterConfig",
    "LocalModelConfig", 
    "APIModelConfig",
    "IntegrationConfig",
    "DEFAULT_CONFIG",
    
    # Enums
    "ProcessingPath",
    "IntegrationStrategy",
    "InterruptStyle",
    "OptimizationStrategy",
    
    # Exceptions
    "DualTrackError",
    "RouterError", 
    "LocalModelError",
    "ModelLoadError",
    "GenerationError",
    "APIModelError",
    "APIConnectionError",
    "APIRateLimitError", 
    "APITimeoutError",
    "IntegrationError",
    "ConfigurationError",
    "TimeoutError",
    "ResourceError",
    "DualTrackOptimizationError",
    "MetricsCollectionError",
    "ResourceMonitoringError",
    "AdaptationError",
    
    # Convenience functions
    "determine_path",
    "calculate_query_features",
    "integrate_responses",
    "create_default_optimizer",
    "create_optimized_config"
]

__version__ = "0.1.0"