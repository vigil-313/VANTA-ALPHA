"""
Serialization Utilities

This module provides utilities for serializing and deserializing memory objects.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Union, cast

from ..exceptions import SerializationError

logger = logging.getLogger(__name__)

T = TypeVar('T')


def serialize_to_json(obj: Any) -> str:
    """
    Serialize an object to JSON with special handling for certain types.
    
    Args:
        obj: Object to serialize.
        
    Returns:
        JSON string representation.
        
    Raises:
        SerializationError: If serialization fails.
    """
    try:
        # Define custom encoder to handle special types
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                # Handle other special types as needed
                return super().default(obj)
        
        # Serialize with custom encoder
        return json.dumps(obj, cls=CustomJSONEncoder)
    except Exception as e:
        error_msg = f"Failed to serialize object: {e}"
        logger.error(error_msg)
        raise SerializationError(error_msg) from e


def deserialize_from_json(json_str: str, expected_type: Optional[type] = None) -> Any:
    """
    Deserialize JSON to an object with special handling for certain types.
    
    Args:
        json_str: JSON string to deserialize.
        expected_type: Optional expected type for validation.
        
    Returns:
        Deserialized object.
        
    Raises:
        SerializationError: If deserialization fails or type validation fails.
    """
    try:
        # Deserialize JSON
        obj = json.loads(json_str)
        
        # Validate type if expected_type is provided
        if expected_type is not None and not isinstance(obj, expected_type):
            error_msg = f"Deserialized object is not of expected type {expected_type.__name__}"
            logger.error(error_msg)
            raise SerializationError(error_msg)
        
        return obj
    except json.JSONDecodeError as e:
        error_msg = f"Failed to deserialize JSON: {e}"
        logger.error(error_msg)
        raise SerializationError(error_msg) from e


def load_json_file(file_path: str, expected_type: Optional[type] = None) -> Any:
    """
    Load a JSON file and deserialize its contents.
    
    Args:
        file_path: Path to the JSON file.
        expected_type: Optional expected type for validation.
        
    Returns:
        Deserialized object.
        
    Raises:
        SerializationError: If file cannot be read or deserialization fails.
    """
    try:
        with open(file_path, 'r') as f:
            json_str = f.read()
        return deserialize_from_json(json_str, expected_type)
    except (FileNotFoundError, IOError) as e:
        error_msg = f"Failed to read JSON file {file_path}: {e}"
        logger.error(error_msg)
        raise SerializationError(error_msg) from e


def save_json_file(obj: Any, file_path: str) -> None:
    """
    Serialize an object to JSON and save to a file.
    
    Args:
        obj: Object to serialize.
        file_path: Path to save the JSON file.
        
    Raises:
        SerializationError: If serialization or file writing fails.
    """
    try:
        json_str = serialize_to_json(obj)
        with open(file_path, 'w') as f:
            f.write(json_str)
    except (IOError, OSError) as e:
        error_msg = f"Failed to write JSON to file {file_path}: {e}"
        logger.error(error_msg)
        raise SerializationError(error_msg) from e