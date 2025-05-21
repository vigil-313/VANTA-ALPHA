"""
Memory System Exceptions

This module defines the custom exceptions used throughout the memory system.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

class MemoryError(Exception):
    """Base exception for all memory-related errors."""
    pass


class StorageError(MemoryError):
    """Exception raised for errors in the storage system."""
    pass


class VectorStoreError(MemoryError):
    """Exception raised for errors in the vector storage system."""
    pass


class ResourceExceededError(MemoryError):
    """Exception raised when a resource limit (memory, tokens) is exceeded."""
    pass


class SerializationError(MemoryError):
    """Exception raised for errors in serialization or deserialization."""
    pass


class ValidationError(MemoryError):
    """Exception raised for errors in data validation."""
    pass