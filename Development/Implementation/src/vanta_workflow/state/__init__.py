"""
VANTA LangGraph State Definition

This module provides the state definition for the VANTA LangGraph integration.
It includes a typed state structure and utility functions for state management.
"""
# TASK-REF: LG_001 - LangGraph State Definition
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration

from .vanta_state import (
    VANTAState,
    ActivationMode,
    ActivationStatus,
    ProcessingPath,
    create_empty_state,
    update_state,
    serialize_state,
    deserialize_state,
)

__all__ = [
    "VANTAState",
    "ActivationMode",
    "ActivationStatus",
    "ProcessingPath",
    "create_empty_state",
    "update_state",
    "serialize_state",
    "deserialize_state",
]