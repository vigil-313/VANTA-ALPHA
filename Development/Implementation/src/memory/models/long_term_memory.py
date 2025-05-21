"""
Long-term Memory Data Models

This module defines the data models for long-term memory storage.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, TypedDict, Union
from uuid import uuid4


class ConversationEntry(TypedDict, total=False):
    """A single conversation turn in long-term memory."""
    id: str  # Unique identifier
    user_message: str  # User's message content
    assistant_message: str  # VANTA's response
    timestamp: str  # ISO format timestamp
    audio_reference: Optional[str]  # Path to audio recording
    metadata: Dict[str, Any]  # Additional metadata
    embedding: Optional[List[float]]  # Vector embedding for retrieval


class SemanticMemory(TypedDict, total=False):
    """Semantic memory entry for vector storage."""
    id: str  # Unique identifier
    content: str  # Memory content
    source: str  # Source of the memory
    timestamp: str  # When the memory was created
    importance: float  # Importance score (0-1)
    embedding: List[float]  # Vector embedding for retrieval
    metadata: Dict[str, Any]  # Additional context and tags


class UserPreference(TypedDict, total=False):
    """Stored user preference."""
    id: str  # Preference identifier
    category: str  # Preference category
    value: Any  # Preference value
    confidence: float  # Confidence in this preference
    last_updated: str  # ISO timestamp of last update
    source_references: List[str]  # References to source interactions


def create_conversation_entry(
    user_message: str,
    assistant_message: str,
    metadata: Optional[Dict[str, Any]] = None,
    audio_reference: Optional[str] = None,
    timestamp: Optional[str] = None,
    id: Optional[str] = None
) -> ConversationEntry:
    """
    Create a conversation entry object with generated defaults for missing fields.
    
    Args:
        user_message: The user's message.
        assistant_message: VANTA's response message.
        metadata: Optional metadata about the conversation.
        audio_reference: Optional path to audio recording.
        timestamp: Optional timestamp. Defaults to current time.
        id: Optional identifier. Defaults to generated UUID.
        
    Returns:
        A ConversationEntry object.
    """
    return {
        "id": id or str(uuid4()),
        "user_message": user_message,
        "assistant_message": assistant_message,
        "timestamp": timestamp or datetime.now().isoformat(),
        "audio_reference": audio_reference,
        "metadata": metadata or {},
    }


def create_semantic_memory(
    content: str,
    source: str,
    importance: float = 0.5,
    metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
    id: Optional[str] = None
) -> SemanticMemory:
    """
    Create a semantic memory object with generated defaults for missing fields.
    
    Args:
        content: The memory content.
        source: The source of the memory.
        importance: Importance score from 0 to 1.
        metadata: Optional additional context and tags.
        timestamp: Optional timestamp. Defaults to current time.
        id: Optional identifier. Defaults to generated UUID.
        
    Returns:
        A SemanticMemory object.
    """
    return {
        "id": id or str(uuid4()),
        "content": content,
        "source": source,
        "importance": max(0.0, min(1.0, importance)),  # Clamp to 0-1 range
        "timestamp": timestamp or datetime.now().isoformat(),
        "metadata": metadata or {},
    }


def create_user_preference(
    category: str,
    value: Any,
    confidence: float = 0.5,
    source_references: Optional[List[str]] = None,
    last_updated: Optional[str] = None,
    id: Optional[str] = None
) -> UserPreference:
    """
    Create a user preference object with generated defaults for missing fields.
    
    Args:
        category: The preference category.
        value: The preference value.
        confidence: Confidence in this preference from 0 to 1.
        source_references: Optional references to source interactions.
        last_updated: Optional timestamp. Defaults to current time.
        id: Optional identifier. Defaults to generated UUID.
        
    Returns:
        A UserPreference object.
    """
    return {
        "id": id or str(uuid4()),
        "category": category,
        "value": value,
        "confidence": max(0.0, min(1.0, confidence)),  # Clamp to 0-1 range
        "last_updated": last_updated or datetime.now().isoformat(),
        "source_references": source_references or [],
    }