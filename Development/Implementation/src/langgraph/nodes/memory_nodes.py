#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced VANTA LangGraph Memory Processing Nodes

This module implements enhanced memory integration nodes for the VANTA system,
including context retrieval, conversation storage, and conversation summarization.
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

def build_prompt_with_memory(user_input: str, memory_context: Optional[Dict], conversation_summary: Optional[str] = None) -> str:
    """Build enhanced prompt with memory context."""
    prompt_parts = []
    
    if conversation_summary:
        prompt_parts.append(f"Conversation Summary: {conversation_summary}")
    
    if memory_context and memory_context.get("results"):
        prompt_parts.append("Relevant Context:")
        for i, result in enumerate(memory_context["results"][:3]):  # Limit to top 3
            prompt_parts.append(f"- {result.get('content', '')}")
    
    prompt_parts.append(f"User: {user_input}")
    
    return "\n\n".join(prompt_parts)


async def retrieve_memory_context_node(state: VANTAState) -> Dict[str, Any]:
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
                    "last_retrieval": datetime.now(),
                    "status": "no_input_to_process"
                }
            }
        
        # Get the last user message for context retrieval
        last_user_message = None
        for message in reversed(messages):
            if isinstance(message, HumanMessage) or (hasattr(message, 'type') and message.type == 'human'):
                last_user_message = message
                break
        
        if not last_user_message or not last_user_message.content:
            return {
                "memory": {
                    **state.get("memory", {}),
                    "retrieved_context": {},
                    "context_retrieval_time": 0,
                    "last_retrieval": datetime.now(),
                    "status": "no_user_message"
                }
            }
        
        # Get memory system
        memory_system = get_memory_system()
        
        # Retrieve context using working memory
        user_input = last_user_message.content
        context_results = memory_system.working_memory.retrieve_context(
            query=user_input,
            max_results=5
        )
        
        # Calculate context window usage
        context_tokens = estimate_token_count(context_results)
        context_window_size = state.get("config", {}).get("context_window_size", 4000)
        available_window = context_window_size - context_tokens
        
        retrieval_time = time.time() - start_time
        
        # Extract memory references
        memory_refs = []
        if context_results and isinstance(context_results, dict):
            for result in context_results.get("results", []):
                if result.get("memory_id"):
                    memory_refs.append(result["memory_id"])
        
        # Prepare enhanced memory context
        enhanced_context = {
            "query": user_input,
            "results": context_results.get("results", []) if context_results else [],
            "retrieval_time": retrieval_time,
            "timestamp": datetime.now(),
            "memory_references": memory_refs,
            "context_tokens": context_tokens,
            "available_tokens": available_window
        }
        
        return {
            "memory": {
                **state.get("memory", {}),
                "retrieved_context": enhanced_context,
                "memory_references": memory_refs,
                "context_window_size": available_window,
                "last_retrieval": datetime.now(),
                "status": "context_retrieved"
            }
        }
        
    except Exception as e:
        logger.error(f"Memory context retrieval failed: {e}")
        return {
            "memory": {
                **state.get("memory", {}),
                "retrieved_context": {"error": str(e)},
                "context_retrieval_time": 0,
                "last_retrieval": datetime.now(),
                "status": "retrieval_error",
                "error": f"Memory retrieval error: {str(e)}"
            }
        }


async def store_conversation_node(state: VANTAState) -> Dict[str, Any]:
    """
    Store conversation turn in memory system.
    
    This node stores the current conversation exchange in the memory system
    for future retrieval and context building.
    
    Args:
        state: Current VANTA state containing conversation data
        
    Returns:
        Dict: Updates with memory storage results
    """
    try:
        start_time = time.time()
        
        # Check if we have both user input and response
        messages = state.get("messages", [])
        if len(messages) < 2:
            return {
                "memory": {
                    **state.get("memory", {}),
                    "last_storage_status": "insufficient_messages",
                    "last_storage_time": datetime.now()
                }
            }
        
        # Find the last user-assistant exchange
        user_message = None
        ai_message = None
        
        for i in range(len(messages) - 1, -1, -1):
            message = messages[i]
            if isinstance(message, AIMessage) or (hasattr(message, 'type') and message.type == 'ai'):
                if ai_message is None:
                    ai_message = message
            elif isinstance(message, HumanMessage) or (hasattr(message, 'type') and message.type == 'human'):
                if user_message is None and ai_message is not None:
                    user_message = message
                    break
        
        if not user_message or not ai_message:
            return {
                "memory": {
                    **state.get("memory", {}),
                    "last_storage_status": "incomplete_conversation_pair",
                    "last_storage_time": datetime.now()
                }
            }
        
        # Get memory system
        memory_system = get_memory_system()
        
        # Create conversation message with enhanced metadata
        conversation_message = {
            "user_message": user_message.content,
            "assistant_message": ai_message.content,
            "timestamp": datetime.now(),
            "processing_path": state.get("processing", {}).get("path"),
            "metadata": {
                "dual_track_results": state.get("processing", {}).get("dual_track_results"),
                "memory_context_used": bool(state.get("memory", {}).get("retrieved_context")),
                "activation_mode": state.get("activation", {}).get("status"),
                "audio_reference": state.get("audio", {}).get("current_audio")
            }
        }
        
        # Store in working memory
        memory_id = memory_system.working_memory.store_conversation(conversation_message)
        
        # Update conversation history in state
        current_history = list(state.get("memory", {}).get("conversation_history", []))
        current_history.append({
            "memory_id": memory_id,
            "timestamp": conversation_message["timestamp"],
            "user_message": conversation_message["user_message"],
            "assistant_message": conversation_message["assistant_message"]
        })
        
        # Track memory operation
        current_operations = list(state.get("memory", {}).get("memory_operations", []))
        current_operations.append({
            "operation": "store",
            "memory_id": memory_id,
            "timestamp": datetime.now(),
            "processing_time": time.time() - start_time
        })
        
        storage_time = time.time() - start_time
        
        return {
            "memory": {
                **state.get("memory", {}),
                "conversation_history": current_history,
                "memory_operations": current_operations,
                "last_storage_time": datetime.now(),
                "last_storage_status": "success",
                "storage_processing_time": storage_time
            }
        }
        
    except Exception as e:
        logger.error(f"Memory storage failed: {e}")
        return {
            "memory": {
                **state.get("memory", {}),
                "last_storage_status": "error",
                "last_storage_time": datetime.now(),
                "storage_error": f"Memory storage error: {str(e)}"
            }
        }


async def summarize_conversation_node(state: VANTAState) -> Dict[str, Any]:
    """
    Generate conversation summary when history exceeds limits.
    
    This node generates a summary of the conversation history when it becomes
    too long, helping to maintain context while managing memory usage.
    
    Args:
        state: Current VANTA state with conversation history
        
    Returns:
        Dict: Updates with summarized conversation data
    """
    try:
        start_time = time.time()
        
        conversation_history = state.get("memory", {}).get("conversation_history", [])
        summarization_threshold = state.get("config", {}).get("summarization_threshold", 10)
        
        # Check if summarization is needed
        if len(conversation_history) < summarization_threshold:
            return {
                "memory": {
                    **state.get("memory", {}),
                    "summarization_status": "not_needed",
                    "last_summarization_check": datetime.now()
                }
            }
        
        # Get memory system
        memory_system = get_memory_system()
        
        # Generate summary of older conversations
        messages_to_summarize = conversation_history[:-5]  # Keep last 5 messages
        
        if not messages_to_summarize:
            return {
                "memory": {
                    **state.get("memory", {}),
                    "summarization_status": "no_messages_to_summarize",
                    "last_summarization_check": datetime.now()
                }
            }
        
        # Create summary text
        summary_text = memory_system.working_memory.generate_summary(messages_to_summarize)
        
        # Keep recent messages and summary
        trimmed_history = conversation_history[-5:]  # Keep recent messages
        
        summarization_time = time.time() - start_time
        
        return {
            "memory": {
                **state.get("memory", {}),
                "conversation_history": trimmed_history,
                "conversation_summary": summary_text,
                "last_summarization_time": datetime.now(),
                "summarization_status": "completed",
                "summarization_processing_time": summarization_time,
                "summarized_message_count": len(messages_to_summarize)
            }
        }
        
    except Exception as e:
        logger.error(f"Memory summarization failed: {e}")
        return {
            "memory": {
                **state.get("memory", {}),
                "summarization_status": "error",
                "last_summarization_time": datetime.now(),
                "summarization_error": f"Memory summarization error: {str(e)}"
            }
        }


async def handle_memory_error(state: VANTAState, error: Exception) -> Dict[str, Any]:
    """
    Handle memory system errors gracefully.
    
    This function provides fallback behavior when the memory system encounters
    errors, ensuring the conversation can continue even if memory is unavailable.
    
    Args:
        state: Current VANTA state
        error: The exception that occurred
        
    Returns:
        Dict: Fallback memory state
    """
    logger.error(f"Memory system error: {error}")
    
    # Provide fallback behavior using existing conversation history
    conversation_history = state.get("memory", {}).get("conversation_history", [])
    fallback_context = {
        "conversation_history": conversation_history[-3:],  # Last 3 messages
        "retrieved_context": {},
        "conversation_summary": "Memory system temporarily unavailable",
        "status": "fallback_mode",
        "error": f"Memory error (using fallback): {str(error)}",
        "last_error_time": datetime.now()
    }
    
    return {"memory": fallback_context}


# Legacy function names for backward compatibility
def retrieve_context(state: VANTAState) -> Dict[str, Any]:
    """Legacy wrapper for retrieve_memory_context_node."""
    import asyncio
    return asyncio.run(retrieve_memory_context_node(state))

def update_memory(state: VANTAState) -> Dict[str, Any]:
    """Legacy wrapper for store_conversation_node."""
    import asyncio
    return asyncio.run(store_conversation_node(state))

def prune_memory(state: VANTAState) -> Dict[str, Any]:
    """Legacy wrapper for summarize_conversation_node."""
    import asyncio
    return asyncio.run(summarize_conversation_node(state))