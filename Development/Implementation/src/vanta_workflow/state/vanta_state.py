#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA LangGraph State Definition

This module defines the core state structure used by the LangGraph workflow
in the VANTA system. It includes the VANTAState TypedDict, enums for different
system states, and utility functions for state management.
"""
# TASK-REF: LG_001 - LangGraph State Definition
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

from typing import Annotated, Dict, List, Optional, Sequence, TypedDict, Union, Any
from enum import Enum
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

# Import the add_messages reducer for proper message accumulation
from langgraph.graph.message import add_messages
import json


def merge_processing_updates(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Custom reducer for processing field that merges updates from parallel nodes.
    
    This reducer handles updates from both local and API processing nodes
    when running in parallel mode, merging their results appropriately.
    
    Args:
        left: Existing processing state
        right: New processing updates
        
    Returns:
        Merged processing state
    """
    if not left:
        return right.copy() if right else {}
    if not right:
        return left.copy()
    
    # Start with the existing state
    result = left.copy()
    
    # Merge in the new updates
    for key, value in right.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # For nested dictionaries, merge recursively
            result[key] = {**result[key], **value}
        else:
            # For other values, update directly
            result[key] = value
    
    return result


class ActivationMode(str, Enum):
    """Modes for activating the VANTA system.
    
    These modes determine when the system should activate and begin processing.
    
    Attributes:
        CONTINUOUS: Always active and listening
        WAKE_WORD: Activate only on wake word detection
        SCHEDULED: Activate at scheduled times
    """
    CONTINUOUS = "continuous"
    WAKE_WORD = "wake_word"
    SCHEDULED = "scheduled"


class ActivationStatus(str, Enum):
    """Current activation status of the VANTA system.
    
    These states represent the current processing phase of the system.
    
    Attributes:
        INACTIVE: Not currently active
        LISTENING: Actively listening for input
        PROCESSING: Processing a query
        SPEAKING: Generating or speaking a response
    """
    INACTIVE = "inactive"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


class ProcessingPath(str, Enum):
    """Processing paths for the dual-track architecture.
    
    These paths determine which models (local, API, or both) are used for processing.
    
    Attributes:
        LOCAL: Use only the local model
        API: Use only the API model
        PARALLEL: Use both models in parallel
        STAGED: Start with local model, potentially escalate to API
    """
    LOCAL = "local"
    API = "api"
    PARALLEL = "parallel"
    STAGED = "staged"


class VANTAState(TypedDict):
    """Full state definition for the VANTA system.
    
    This TypedDict defines the complete state structure used by all LangGraph
    nodes in the VANTA system. It contains all data necessary for the system's
    operation, including conversation history, audio processing metadata,
    memory references, system configuration, activation status, and processing state.
    
    Each component has access to the complete state but typically only updates
    the portions relevant to its function.
    
    Attributes:
        messages: Conversation history (will be handled by LangGraph add_messages reducer)
        audio: Audio processing metadata including transcription and synthesis data
        memory: Memory references and retrieved context
        config: System configuration including model settings and activation modes
        activation: Current system state including status and activation metadata
        processing: Dual-track processing state including path and responses (uses custom reducer)
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    audio: Dict[str, Any]
    memory: Dict[str, Any]
    config: Dict[str, Any]
    activation: Dict[str, Any]
    processing: Annotated[Dict[str, Any], merge_processing_updates]


def create_empty_state() -> VANTAState:
    """Create an empty state with default values.
    
    This function initializes a new VANTAState object with all required
    fields set to appropriate default values. It's used when starting a
    new conversation or session.
    
    Returns:
        A new VANTAState object with default values
    """
    return {
        "messages": [],
        "audio": {
            "current_audio": None,
            "last_transcription": None,
            "metadata": {},
            "last_synthesis": None,
        },
        "memory": {
            "audio_entries": [],
            "conversation_history": [],
            "retrieved_context": {},
            "embeddings": {},
        },
        "config": {
            "activation_mode": ActivationMode.WAKE_WORD,
            "model_settings": {
                "local": {
                    "max_tokens": 512,
                    "temperature": 0.7,
                },
                "api": {
                    "max_tokens": 1024,
                    "temperature": 0.7,
                    "stream": True,
                },
            },
            "voice_settings": {
                "voice_id": "default",
                "speed": 1.0,
                "pitch": 1.0,
            },
            "scheduled_times": [],
        },
        "activation": {
            "status": ActivationStatus.INACTIVE,
            "last_activation_time": None,
            "wake_word_detected": False,
        },
        "processing": {
            "path": None,
            "local_response": None,
            "api_response": None,
            "local_completed": False,
            "api_completed": False,
            "local_time": 0,
            "api_time": 0,
        }
    }


def update_nested_dict(original: Dict, updates: Dict) -> Dict:
    """Recursively update a nested dictionary.
    
    This function performs a deep update of a nested dictionary, merging
    the updates into the original dictionary at all levels rather than
    simply overwriting top-level keys.
    
    Args:
        original: The original dictionary to update
        updates: The dictionary containing updates to apply
        
    Returns:
        The updated dictionary
    """
    result = original.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = update_nested_dict(result[key], value)
        else:
            result[key] = value
            
    return result


def update_state(state: VANTAState, updates: Dict) -> VANTAState:
    """Update state with changes, handling special cases.
    
    This function updates the state dictionary with the provided updates,
    handling special cases like messages which use a reducer and nested
    dictionaries which should be merged rather than overwritten.
    
    Args:
        state: The current state
        updates: The updates to apply to the state
        
    Returns:
        The updated state
    """
    result = state.copy()
    
    for key, value in updates.items():
        if key == "messages" and "messages" in result:
            # Special case for messages which use a reducer
            # Don't handle here as LangGraph will apply the reducer
            result[key] = value
        elif key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # For dictionaries, perform a deep update
            result[key] = update_nested_dict(result[key], value)
        else:
            # For other fields, simply update
            result[key] = value
            
    return result


def serialize_state(state: VANTAState) -> Dict:
    """Convert state to a serializable dictionary.
    
    This function converts the state to a form that can be serialized to JSON,
    handling special cases like datetime objects and messages.
    
    Args:
        state: The state to serialize
        
    Returns:
        A serializable dictionary
    """
    result = {}
    
    for key, value in state.items():
        if key == "messages":
            # Convert messages to a serializable format
            result[key] = [
                {
                    "type": type(msg).__name__,
                    "content": msg.content,
                    "additional_kwargs": msg.additional_kwargs,
                }
                for msg in value
            ]
        elif isinstance(value, dict):
            # Recursively serialize nested dictionaries
            result[key] = serialize_nested_dict(value)
        else:
            # Copy other values directly
            result[key] = value
            
    return result


def serialize_nested_dict(d: Dict) -> Dict:
    """Recursively serialize a nested dictionary.
    
    This function handles serialization of special types within nested dictionaries.
    
    Args:
        d: The dictionary to serialize
        
    Returns:
        A serializable dictionary
    """
    result = {}
    
    for key, value in d.items():
        if isinstance(value, datetime):
            # Convert datetime to ISO format string
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            # Recursively serialize nested dictionaries
            result[key] = serialize_nested_dict(value)
        elif isinstance(value, (list, tuple)):
            # Recursively serialize lists
            result[key] = [
                serialize_nested_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            # Copy other values directly
            result[key] = value
            
    return result


def deserialize_state(serialized: Dict) -> VANTAState:
    """Convert serialized dictionary back to state.
    
    This function converts a serialized dictionary back to a VANTAState object,
    handling special cases like datetime strings and messages.
    
    Args:
        serialized: The serialized state
        
    Returns:
        A VANTAState object
    """
    result = {}
    
    for key, value in serialized.items():
        if key == "messages":
            # Convert serialized messages back to message objects
            result[key] = [
                _deserialize_message(msg) for msg in value
            ]
        elif isinstance(value, dict):
            # Recursively deserialize nested dictionaries
            result[key] = deserialize_nested_dict(value)
        else:
            # Copy other values directly
            result[key] = value
            
    return result


def deserialize_nested_dict(d: Dict) -> Dict:
    """Recursively deserialize a nested dictionary.
    
    This function handles deserialization of special types within nested dictionaries.
    
    Args:
        d: The serialized dictionary
        
    Returns:
        A deserialized dictionary
    """
    result = {}
    
    for key, value in d.items():
        if isinstance(value, str) and key.endswith("_time"):
            # Try to convert ISO format strings back to datetime objects
            try:
                result[key] = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                result[key] = value
        elif isinstance(value, dict):
            # Recursively deserialize nested dictionaries
            result[key] = deserialize_nested_dict(value)
        elif isinstance(value, (list, tuple)):
            # Recursively deserialize lists
            result[key] = [
                deserialize_nested_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            # Copy other values directly
            result[key] = value
            
    return result


def _deserialize_message(msg_dict: Dict) -> BaseMessage:
    """Convert a serialized message dictionary back to a message object.
    
    Args:
        msg_dict: The serialized message
        
    Returns:
        A BaseMessage object
    """
    msg_type = msg_dict.get("type", "")
    content = msg_dict.get("content", "")
    additional_kwargs = msg_dict.get("additional_kwargs", {})
    
    if msg_type == "HumanMessage":
        return HumanMessage(content=content, additional_kwargs=additional_kwargs)
    elif msg_type == "AIMessage":
        return AIMessage(content=content, additional_kwargs=additional_kwargs)
    elif msg_type == "SystemMessage":
        return SystemMessage(content=content, additional_kwargs=additional_kwargs)
    else:
        # Default to BaseMessage
        return BaseMessage(content=content, additional_kwargs=additional_kwargs)
