#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA LangGraph Memory Processing Nodes

This module implements the LangGraph nodes for memory-related processing in the VANTA system,
including context retrieval, memory storage, and conversation summarization.
"""
# TASK-REF: INT_003 - Memory System Integration
# TASK-REF: LG_002 - LangGraph Node Implementation
# CONCEPT-REF: CON-VANTA-002 - Memory Engine
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from ..state.vanta_state import VANTAState, ActivationStatus
from ...memory.core import MemorySystem

logger = logging.getLogger(__name__)

# Global memory system instance (will be initialized by the application)
_memory_system: Optional[MemorySystem] = None

def initialize_memory_system(config: Optional[Dict[str, Any]] = None) -> None:
    """Initialize the global memory system instance."""
    global _memory_system
    _memory_system = MemorySystem(config)
    _memory_system.initialize()

def get_memory_system() -> MemorySystem:
    """Get the global memory system instance."""
    if _memory_system is None:
        raise RuntimeError("Memory system not initialized. Call initialize_memory_system() first.")
    return _memory_system

def estimate_token_count(text: Any) -> int:
    """Estimate token count for text (simple approximation)."""
    if isinstance(text, str):
        return len(text.split()) * 1.3  # Rough approximation
    elif isinstance(text, dict):
        return estimate_token_count(str(text))
    return 0


def retrieve_memory_context_node(state: VANTAState) -> Dict[str, Any]:
    """
    Retrieve relevant memory context for current input.
    
    This node uses the Memory System to retrieve relevant context based on the
    latest user message. It performs semantic search and retrieves conversations
    that might be relevant to the current query.
    
    Args:
        state: Current VANTA state containing messages and memory data
        
    Returns:
        Dict: Updates with retrieved context information and memory metadata
    """
    try:
        start_time = time.time()
        
        # Skip if no messages or not processing
        messages = state.get("messages", [])
        if not messages or state["activation"]["status"] != ActivationStatus.PROCESSING:
            return {
                "memory": {
                    **state.get("memory", {}),
                    "retrieved_context": {},
                    "context_retrieval_time": 0,
                    "last_retrieval": datetime.now()
                }
            }
        
        # Get the last user message for context retrieval
        last_user_message = None
        for message in reversed(messages):
            if hasattr(message, 'type') and message.type == 'human':
                last_message = message
                break
            elif message.__class__.__name__ == 'HumanMessage':
                last_message = message
                break
        
        if not last_message or not last_message.content:
            return {}
        
        # Initialize memory engine
        memory_engine = MemoryEngine()
        
        # Retrieve relevant context
        start_time = time.time()
        query_text = last_message.content
        
        # Get conversation context
        conversation_context = memory_engine.retrieve_conversation_context(
            query=query_text,
            max_results=5
        )
        
        # Get semantic context
        semantic_context = memory_engine.retrieve_semantic_context(
            query=query_text,
            max_results=3
        )
        
        retrieval_time = time.time() - start_time
        
        # Prepare retrieved context
        retrieved_context = {
            "query": query_text,
            "timestamp": datetime.now().isoformat(),
            "conversation_context": conversation_context,
            "semantic_context": semantic_context,
            "retrieval_time": retrieval_time,
            "total_results": len(conversation_context) + len(semantic_context),
        }
        
        # Return memory updates
        return {
            "memory": {
                "retrieved_context": retrieved_context,
                "last_retrieval_time": datetime.now().isoformat(),
            }
        }
    
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        
        # Return empty context on error
        return {
            "memory": {
                "retrieved_context": {
                    "query": state.get("messages", [])[-1].content if state.get("messages") else "",
                    "timestamp": datetime.now().isoformat(),
                    "conversation_context": [],
                    "semantic_context": [],
                    "error": str(e),
                    "total_results": 0,
                },
                "context_error": str(e),
            }
        }


def update_memory(state: VANTAState) -> Dict[str, Any]:
    """
    Updates memory system with the current conversation.
    
    This node updates the Memory System with the latest conversation exchange,
    storing both the user query and AI response along with metadata for
    future retrieval.
    
    Args:
        state: Current VANTA state containing messages and conversation data
        
    Returns:
        Dict: Updates with new conversation history
    """
    try:
        # Skip if no complete conversation pair
        messages = state.get("messages", [])
        if len(messages) < 2:
            return {}
        
        # Find the last user-assistant exchange
        user_message = None
        ai_message = None
        
        for i in range(len(messages) - 1, -1, -1):
            message = messages[i]
            
            if (hasattr(message, 'type') and message.type == 'ai') or message.__class__.__name__ == 'AIMessage':
                if ai_message is None:
                    ai_message = message
            elif (hasattr(message, 'type') and message.type == 'human') or message.__class__.__name__ == 'HumanMessage':
                if user_message is None and ai_message is not None:
                    user_message = message
                    break  # Found complete pair
        
        if not user_message or not ai_message:
            return {}
        
        # Initialize memory engine
        memory_engine = MemoryEngine()
        
        # Create conversation entry
        start_time = time.time()
        timestamp = datetime.now().isoformat()
        
        conversation_entry = {
            "id": f"conv_{int(time.time())}_{hash(user_message.content) % 10000}",
            "timestamp": timestamp,
            "user_message": user_message.content,
            "ai_message": ai_message.content,
            "context": state["memory"].get("retrieved_context", {}),
            "processing_metadata": state.get("processing", {}),
            "audio_reference": state["audio"].get("audio_path", ""),
        }
        
        # Store in memory system
        memory_engine.store_conversation(conversation_entry)
        
        # Update embeddings if configured
        try:
            memory_engine.update_embeddings(
                text=f"{user_message.content} {ai_message.content}",
                metadata=conversation_entry
            )
        except Exception as e:
            logger.warning(f"Failed to update embeddings: {e}")
        
        storage_time = time.time() - start_time
        
        # Get updated conversation history
        current_history = state["memory"].get("conversation_history", [])
        updated_history = current_history + [conversation_entry]
        
        # Limit history size to prevent memory bloat
        max_history = state["config"].get("max_conversation_history", 100)
        if len(updated_history) > max_history:
            updated_history = updated_history[-max_history:]
        
        # Return memory updates
        return {
            "memory": {
                "conversation_history": updated_history,
                "last_update_time": timestamp,
                "storage_time": storage_time,
                "total_conversations": len(updated_history),
            }
        }
    
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        
        # Return error information
        return {
            "memory": {
                "update_error": str(e),
                "last_update_time": datetime.now().isoformat(),
            }
        }


def prune_memory(state: VANTAState) -> Dict[str, Any]:
    """
    Prunes old memory entries to manage storage size.
    
    This node periodically cleans up old memory entries to prevent
    unlimited growth of the memory system while preserving important
    conversation history.
    
    Args:
        state: Current VANTA state containing memory data
        
    Returns:
        Dict: Updates with pruned memory information
    """
    try:
        # Check if pruning is needed
        conversation_history = state["memory"].get("conversation_history", [])
        max_conversations = state["config"].get("max_conversation_history", 100)
        
        if len(conversation_history) <= max_conversations:
            return {}  # No pruning needed
        
        # Initialize memory engine for advanced pruning
        memory_engine = MemoryEngine()
        
        # Perform intelligent pruning
        start_time = time.time()
        
        # Keep most recent conversations
        recent_conversations = conversation_history[-max_conversations:]
        
        # Archive old conversations
        archived_conversations = conversation_history[:-max_conversations]
        
        # Store archived conversations in long-term storage
        if archived_conversations:
            try:
                memory_engine.archive_conversations(archived_conversations)
            except Exception as e:
                logger.warning(f"Failed to archive conversations: {e}")
        
        pruning_time = time.time() - start_time
        
        # Return updated memory state
        return {
            "memory": {
                "conversation_history": recent_conversations,
                "archived_count": len(archived_conversations),
                "pruning_time": pruning_time,
                "last_pruning_time": datetime.now().isoformat(),
            }
        }
    
    except Exception as e:
        logger.error(f"Error pruning memory: {e}")
        
        # Return error information without changing memory
        return {
            "memory": {
                "pruning_error": str(e),
                "last_pruning_time": datetime.now().isoformat(),
            }
        }