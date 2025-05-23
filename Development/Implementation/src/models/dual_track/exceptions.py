# TASK-REF: DP-001 - Processing Router Implementation
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
Exception classes for the dual-track processing system.
"""


class DualTrackError(Exception):
    """Base exception for dual-track processing errors."""
    pass


class RouterError(DualTrackError):
    """Exception raised by the processing router."""
    pass


class LocalModelError(DualTrackError):
    """Exception raised by local model operations."""
    pass


class ModelLoadError(LocalModelError):
    """Exception raised when model loading fails."""
    pass


class GenerationError(LocalModelError):
    """Exception raised during text generation."""
    pass


class APIModelError(DualTrackError):
    """Exception raised by API model operations."""
    pass


class APIConnectionError(APIModelError):
    """Exception raised for API connection issues."""
    pass


class APIRateLimitError(APIModelError):
    """Exception raised when API rate limits are exceeded."""
    pass


class APITimeoutError(APIModelError):
    """Exception raised when API requests timeout."""
    pass


class IntegrationError(DualTrackError):
    """Exception raised during response integration."""
    pass


class ConfigurationError(DualTrackError):
    """Exception raised for configuration issues."""
    pass


class TimeoutError(DualTrackError):
    """Exception raised when operations timeout."""
    pass


class ResourceError(DualTrackError):
    """Exception raised when system resources are insufficient."""
    pass