"""
Exceptions for the local model integration.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""


class LocalModelError(Exception):
    """Base exception for all local model errors."""
    pass


class ModelNotFoundError(LocalModelError):
    """Raised when a model file or directory cannot be found."""
    pass


class ModelInitializationError(LocalModelError):
    """Raised when a model fails to initialize."""
    pass


class ModelGenerationError(LocalModelError):
    """Raised when model generation fails."""
    pass


class ModelNotInitializedError(LocalModelError):
    """Raised when operations are attempted on an uninitialized model."""
    pass


class TokenizationError(LocalModelError):
    """Raised when tokenization fails."""
    pass


class ModelLoadError(LocalModelError):
    """Raised when loading a model from the registry fails."""
    pass


class ModelResourceError(LocalModelError):
    """Raised when a model exceeds available resources."""
    pass


class UnsupportedModelTypeError(LocalModelError):
    """Raised when an operation is attempted on an unsupported model type."""
    pass