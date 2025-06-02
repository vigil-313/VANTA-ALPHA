# TASK-REF: DP-001 - Processing Router Implementation
# TASK-REF: DP-003 - Dual-Track Optimization
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Optimization
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
Configuration classes for the dual-track processing system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class ProcessingPath(Enum):
    """Available processing paths for dual-track system."""
    LOCAL = "local"
    API = "api"
    PARALLEL = "parallel"
    STAGED = "staged"  # Local first, API if needed


class IntegrationStrategy(Enum):
    """Strategies for integrating responses from multiple sources."""
    PREFERENCE = "preference"  # Prefer one source over another
    COMBINE = "combine"  # Combine responses intelligently
    INTERRUPT = "interrupt"  # Allow one to interrupt the other
    FASTEST = "fastest"  # Use whichever completes first


class InterruptStyle(Enum):
    """Styles for interrupting responses."""
    SMOOTH = "smooth"  # Smooth transitions
    ABRUPT = "abrupt"  # Abrupt interruptions


@dataclass
class RouterConfig:
    """Configuration for the processing router."""
    default_path: ProcessingPath = ProcessingPath.PARALLEL
    threshold_simple: int = 20  # Token threshold for simple queries
    threshold_complex: int = 50  # Token threshold for complex queries
    time_sensitivity: float = 0.7  # Priority for fast responses (0-1)
    quality_priority: float = 0.6  # Priority for response quality (0-1)
    
    # Feature weights for routing decisions
    weights: Dict[str, float] = field(default_factory=lambda: {
        "token_count": 0.3,
        "entity_count": 0.2,
        "reasoning_steps": 0.25,
        "context_dependency": 0.15,
        "creativity_required": 0.1
    })


@dataclass 
class LocalModelConfig:
    """Configuration for local model processing."""
    model_path: str = "../../models/llama-2-7b-chat.Q2_K.gguf"
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    context_window: int = 2048
    preload: bool = True
    
    # Performance settings
    n_threads: Optional[int] = None  # Auto-detect if None
    n_gpu_layers: int = -1  # Use all GPU layers if available
    memory_limit: Optional[int] = None  # Memory limit in MB
    
    # Timeout settings
    generation_timeout: float = 15.0  # Max time for generation in seconds
    loading_timeout: float = 30.0  # Max time for model loading


@dataclass
class APIModelConfig:
    """Configuration for API model processing."""
    provider: str = "anthropic"  # "anthropic" or "openai"
    model: str = "claude-3-7-sonnet-20250219"
    max_tokens: int = 1024
    temperature: float = 0.7
    stream: bool = True
    timeout: float = 30.0  # Request timeout in seconds
    retry_attempts: int = 3
    
    # Cost and rate limiting
    max_cost_per_request: Optional[float] = None  # Max cost in dollars
    requests_per_minute: Optional[int] = None  # Rate limit
    
    # Fallback configuration
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None


@dataclass
class IntegrationConfig:
    """Configuration for response integration."""
    strategy: IntegrationStrategy = IntegrationStrategy.PREFERENCE
    interrupt_style: InterruptStyle = InterruptStyle.SMOOTH
    similarity_threshold: float = 0.8
    api_preference_weight: float = 0.7
    
    # Timing configuration
    local_timeout: float = 2.0  # Max wait for local response
    api_timeout: float = 8.0  # Max wait for API response
    integration_delay: float = 0.5  # Delay before integrating responses
    
    # Quality thresholds
    min_response_length: int = 10  # Minimum response length to consider
    max_response_length: int = 2000  # Maximum response length


@dataclass
class DualTrackConfig:
    """Main configuration for the dual-track processing system."""
    router: RouterConfig = field(default_factory=RouterConfig)
    local_model: LocalModelConfig = field(default_factory=LocalModelConfig)
    api_model: APIModelConfig = field(default_factory=APIModelConfig)
    integration: IntegrationConfig = field(default_factory=IntegrationConfig)
    
    # Global settings
    enable_caching: bool = True
    cache_ttl: int = 3600  # Cache time-to-live in seconds
    enable_metrics: bool = True
    log_level: str = "INFO"
    
    # Resource management
    max_concurrent_requests: int = 5
    memory_warning_threshold: float = 0.8  # Warn at 80% memory usage
    cpu_usage_threshold: float = 0.9  # Throttle at 90% CPU usage
    
    # Optimization settings
    enable_optimization: bool = True
    optimization_strategy: str = "adaptive"  # adaptive, latency_focused, resource_efficient, quality_focused, balanced
    adaptation_interval_seconds: float = 30.0
    metrics_window_size: int = 100
    enable_resource_monitoring: bool = True
    monitor_interval_seconds: float = 1.0
    
    # Performance constraints
    target_latency_ms: float = 2000.0
    max_memory_mb: float = 4096.0
    max_cpu_percent: float = 80.0
    max_cost_per_request: float = 0.01
    battery_threshold_percent: float = 20.0
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "DualTrackConfig":
        """Create configuration from dictionary."""
        router_config = RouterConfig(**config_dict.get("router", {}))
        local_config = LocalModelConfig(**config_dict.get("local_model", {}))
        api_config = APIModelConfig(**config_dict.get("api_model", {}))
        integration_config = IntegrationConfig(**config_dict.get("integration", {}))
        
        # Remove nested configs from main dict
        main_config = {k: v for k, v in config_dict.items() 
                      if k not in ["router", "local_model", "api_model", "integration"]}
        
        return cls(
            router=router_config,
            local_model=local_config, 
            api_model=api_config,
            integration=integration_config,
            **main_config
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "router": self.router.__dict__,
            "local_model": self.local_model.__dict__,
            "api_model": self.api_model.__dict__,
            "integration": self.integration.__dict__,
            "enable_caching": self.enable_caching,
            "cache_ttl": self.cache_ttl,
            "enable_metrics": self.enable_metrics,
            "log_level": self.log_level,
            "max_concurrent_requests": self.max_concurrent_requests,
            "memory_warning_threshold": self.memory_warning_threshold,
            "cpu_usage_threshold": self.cpu_usage_threshold
        }


# Default configuration instance
DEFAULT_CONFIG = DualTrackConfig()
