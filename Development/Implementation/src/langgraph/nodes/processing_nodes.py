#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA LangGraph Dual-Track Processing Nodes

This module implements the LangGraph nodes for dual-track processing in the VANTA system,
including routing decisions, local model processing, API model processing, and response integration.
"""
# TASK-REF: LG_002 - LangGraph Node Implementation
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Processing
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from langchain_core.messages import AIMessage, HumanMessage

from ..state.vanta_state import VANTAState, ActivationStatus, ProcessingPath
from ...models.local_model import LocalModelClient
from ...models.api_model import APIModelClient
from ...models.dual_track.router import ProcessingRouter

logger = logging.getLogger(__name__)


def router_node(state: VANTAState) -> Dict[str, Any]:
    """
    Analyzes input and determines processing path (local, API, or both).
    
    This node examines the current query and context to determine the optimal
    processing strategy. It considers query complexity, context requirements,
    and system configuration to route to the appropriate model(s).
    
    Args:
        state: Current VANTA state containing messages and retrieved context
        
    Returns:
        Dict: Updates with processing path and routing metadata
    """
    try:
        # Skip if inactive or no messages
        if state["activation"]["status"] != ActivationStatus.PROCESSING:
            return {}
        
        messages = state.get("messages", [])
        if not messages:
            return {}
        
        # Get the last user message
        last_message = None
        for message in reversed(messages):
            if (hasattr(message, 'type') and message.type == 'human') or message.__class__.__name__ == 'HumanMessage':
                last_message = message
                break
        
        if not last_message or not last_message.content:
            return {}
        
        # Initialize processing router
        router = ProcessingRouter()
        
        # Get context for routing decision
        retrieved_context = state["memory"].get("retrieved_context", {})
        conversation_history = state["memory"].get("conversation_history", [])
        
        # Analyze query and determine processing path
        start_time = time.time()
        
        routing_decision = router.determine_processing_path(
            query=last_message.content,
            context=retrieved_context,
            conversation_history=conversation_history[-5:],  # Last 5 conversations
            system_config=state["config"]
        )
        
        routing_time = time.time() - start_time
        
        # Prepare processing metadata
        processing_metadata = {
            "path": routing_decision.path,
            "reasoning": routing_decision.reasoning,
            "confidence": routing_decision.confidence,
            "estimated_complexity": routing_decision.complexity_score,
            "routing_time": routing_time,
            "timestamp": datetime.now().isoformat(),
            "local_response": None,
            "api_response": None,
            "local_completed": False,
            "api_completed": False,
            "local_time": 0,
            "api_time": 0,
        }
        
        # Return processing updates
        return {
            "processing": processing_metadata
        }
    
    except Exception as e:
        logger.error(f"Error in routing decision: {e}")
        
        # Default to local processing on error
        return {
            "processing": {
                "path": ProcessingPath.LOCAL,
                "reasoning": f"Defaulted to local processing due to routing error: {str(e)}",
                "confidence": 0.5,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "local_completed": False,
                "api_completed": False,
            }
        }


def local_model_node(state: VANTAState) -> Dict[str, Any]:
    """
    Processes the query with the local model.
    
    This node handles processing using the local LLM when the routing decision
    indicates local processing should be used. It constructs the appropriate
    prompt and generates a response using the local model infrastructure.
    
    Args:
        state: Current VANTA state containing messages, context, and processing metadata
        
    Returns:
        Dict: Updates with local model response and processing metadata
    """
    try:
        # Skip if not using local processing path
        processing_path = state["processing"].get("path")
        if processing_path not in [ProcessingPath.LOCAL, ProcessingPath.PARALLEL, ProcessingPath.STAGED]:
            return {}
        
        # Skip if already completed
        if state["processing"].get("local_completed", False):
            return {}
        
        # Get required data
        messages = state.get("messages", [])
        if not messages:
            return {}
        
        # Get the last user message
        last_message = None
        for message in reversed(messages):
            if (hasattr(message, 'type') and message.type == 'human') or message.__class__.__name__ == 'HumanMessage':
                last_message = message
                break
        
        if not last_message:
            return {}
        
        # Initialize local model client
        local_client = LocalModelClient()
        
        # Prepare context for local model
        retrieved_context = state["memory"].get("retrieved_context", {})
        conversation_history = state["memory"].get("conversation_history", [])
        
        # Construct prompt for local model
        start_time = time.time()
        
        # Get model settings
        model_settings = state["config"].get("model_settings", {}).get("local", {})
        max_tokens = model_settings.get("max_tokens", 512)
        temperature = model_settings.get("temperature", 0.7)
        
        # Generate response
        local_response = local_client.generate_response(
            query=last_message.content,
            context=retrieved_context,
            conversation_history=conversation_history[-3:],  # Last 3 for local model
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        local_time = time.time() - start_time
        
        # Prepare processing updates
        processing_updates = {
            "local_response": local_response,
            "local_completed": True,
            "local_time": local_time,
            "local_metadata": {
                "model_name": local_client.model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "processing_time": local_time,
                "timestamp": datetime.now().isoformat(),
            }
        }
        
        # Return processing updates
        return {
            "processing": processing_updates
        }
    
    except Exception as e:
        logger.error(f"Error in local model processing: {e}")
        
        # Return error response
        return {
            "processing": {
                "local_response": f"I apologize, but I encountered an error while processing your request locally: {str(e)}",
                "local_completed": True,
                "local_time": 0,
                "local_error": str(e),
            }
        }


def api_model_node(state: VANTAState) -> Dict[str, Any]:
    """
    Processes the query with the API model.
    
    This node handles processing using cloud-based API models when the routing
    decision indicates API processing should be used. It manages the API request
    and handles streaming responses if configured.
    
    Args:
        state: Current VANTA state containing messages, context, and processing metadata
        
    Returns:
        Dict: Updates with API model response and processing metadata
    """
    try:
        # Skip if not using API processing path
        processing_path = state["processing"].get("path")
        if processing_path not in [ProcessingPath.API, ProcessingPath.PARALLEL, ProcessingPath.STAGED]:
            return {}
        
        # Skip if already completed
        if state["processing"].get("api_completed", False):
            return {}
        
        # For staged processing, wait for local completion first
        if processing_path == ProcessingPath.STAGED:
            if not state["processing"].get("local_completed", False):
                return {}  # Wait for local processing to complete
            
            # Check if local response is sufficient
            local_response = state["processing"].get("local_response", "")
            if local_response and len(local_response) > 50:  # Simple sufficiency check
                return {}  # Local response is sufficient
        
        # Get required data
        messages = state.get("messages", [])
        if not messages:
            return {}
        
        # Initialize API model client
        api_client = APIModelClient()
        
        # Prepare conversation for API
        retrieved_context = state["memory"].get("retrieved_context", {})
        conversation_history = state["memory"].get("conversation_history", [])
        
        # Construct conversation for API model
        start_time = time.time()
        
        # Get model settings
        model_settings = state["config"].get("model_settings", {}).get("api", {})
        max_tokens = model_settings.get("max_tokens", 1024)
        temperature = model_settings.get("temperature", 0.7)
        stream = model_settings.get("stream", True)
        
        # Prepare messages for API
        api_messages = []
        
        # Add system context if available
        if retrieved_context:
            context_summary = _format_context_for_api(retrieved_context)
            api_messages.append({
                "role": "system",
                "content": f"Relevant context: {context_summary}"
            })
        
        # Add recent conversation history
        for conv in conversation_history[-5:]:  # Last 5 conversations for API
            api_messages.extend([
                {"role": "user", "content": conv["user_message"]},
                {"role": "assistant", "content": conv["ai_message"]}
            ])
        
        # Add current query
        last_user_message = None
        for message in reversed(messages):
            if (hasattr(message, 'type') and message.type == 'human') or message.__class__.__name__ == 'HumanMessage':
                last_user_message = message
                break
        
        if last_user_message:
            api_messages.append({
                "role": "user",
                "content": last_user_message.content
            })
        
        # Generate response
        api_response = api_client.generate_response(
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream
        )
        
        api_time = time.time() - start_time
        
        # Prepare processing updates
        processing_updates = {
            "api_response": api_response,
            "api_completed": True,
            "api_time": api_time,
            "api_metadata": {
                "model_name": api_client.model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": stream,
                "processing_time": api_time,
                "timestamp": datetime.now().isoformat(),
            }
        }
        
        # Return processing updates
        return {
            "processing": processing_updates
        }
    
    except Exception as e:
        logger.error(f"Error in API model processing: {e}")
        
        # Return error response
        return {
            "processing": {
                "api_response": f"I apologize, but I encountered an error while processing your request: {str(e)}",
                "api_completed": True,
                "api_time": 0,
                "api_error": str(e),
            }
        }


def integration_node(state: VANTAState) -> Dict[str, Any]:
    """
    Integrates responses from both processing tracks.
    
    This node combines responses from local and API models based on the
    processing path and configured integration strategy. It handles the
    final response selection and formatting.
    
    Args:
        state: Current VANTA state containing processing results
        
    Returns:
        Dict: Updates with final AI message and activation status
    """
    try:
        processing = state.get("processing", {})
        processing_path = processing.get("path")
        
        if not processing_path:
            return {}
        
        # Check completion status based on path
        local_completed = processing.get("local_completed", False)
        api_completed = processing.get("api_completed", False)
        
        # Determine if processing is complete
        processing_complete = False
        
        if processing_path == ProcessingPath.LOCAL:
            processing_complete = local_completed
        elif processing_path == ProcessingPath.API:
            processing_complete = api_completed
        elif processing_path == ProcessingPath.PARALLEL:
            processing_complete = local_completed and api_completed
        elif processing_path == ProcessingPath.STAGED:
            processing_complete = local_completed or api_completed
        
        if not processing_complete:
            return {}  # Wait for processing to complete
        
        # Get responses
        local_response = processing.get("local_response", "")
        api_response = processing.get("api_response", "")
        
        # Choose final response based on strategy
        final_response = _integrate_responses(
            local_response=local_response,
            api_response=api_response,
            processing_path=processing_path,
            config=state["config"]
        )
        
        if not final_response:
            final_response = "I apologize, but I wasn't able to generate a response to your query."
        
        # Create AI message
        ai_message = AIMessage(content=final_response)
        
        # Prepare integration metadata
        integration_metadata = {
            "selected_response": "local" if local_response and not api_response else "api" if api_response and not local_response else "integrated",
            "processing_path": processing_path,
            "local_time": processing.get("local_time", 0),
            "api_time": processing.get("api_time", 0),
            "total_time": processing.get("local_time", 0) + processing.get("api_time", 0),
            "timestamp": datetime.now().isoformat(),
        }
        
        # Return final updates
        return {
            "messages": [ai_message],
            "activation": {
                "status": ActivationStatus.SPEAKING,  # Move to speaking phase
            },
            "processing": {
                **processing,
                "integration_metadata": integration_metadata,
                "final_response": final_response,
            }
        }
    
    except Exception as e:
        logger.error(f"Error in response integration: {e}")
        
        # Return error response
        error_message = "I apologize, but I encountered an error while preparing my response."
        return {
            "messages": [AIMessage(content=error_message)],
            "activation": {
                "status": ActivationStatus.SPEAKING,
            },
            "processing": {
                **state.get("processing", {}),
                "integration_error": str(e),
                "final_response": error_message,
            }
        }


def _format_context_for_api(context: Dict[str, Any]) -> str:
    """
    Format retrieved context for API model consumption.
    
    Args:
        context: Retrieved context dictionary
        
    Returns:
        Formatted context string
    """
    try:
        context_parts = []
        
        # Add conversation context
        conv_context = context.get("conversation_context", [])
        if conv_context:
            context_parts.append("Previous conversations:")
            for conv in conv_context[:3]:  # Limit to 3 most relevant
                context_parts.append(f"- {conv.get('user_message', '')[:100]}...")
        
        # Add semantic context
        sem_context = context.get("semantic_context", [])
        if sem_context:
            context_parts.append("Related information:")
            for sem in sem_context[:2]:  # Limit to 2 most relevant
                context_parts.append(f"- {str(sem)[:100]}...")
        
        return "\n".join(context_parts) if context_parts else "No additional context available."
    
    except Exception as e:
        logger.warning(f"Error formatting context: {e}")
        return "Context formatting error."


def _integrate_responses(local_response: str, api_response: str, processing_path: ProcessingPath, config: Dict[str, Any]) -> str:
    """
    Integrate responses from local and API models.
    
    Args:
        local_response: Response from local model
        api_response: Response from API model
        processing_path: Processing path used
        config: System configuration
        
    Returns:
        Final integrated response
    """
    try:
        if processing_path == ProcessingPath.LOCAL:
            return local_response
        elif processing_path == ProcessingPath.API:
            return api_response
        elif processing_path == ProcessingPath.STAGED:
            # Prefer API response if available, otherwise use local
            return api_response if api_response else local_response
        elif processing_path == ProcessingPath.PARALLEL:
            # Use integration strategy from config
            strategy = config.get("integration_strategy", "prefer_api")
            
            if strategy == "prefer_local":
                return local_response if local_response else api_response
            elif strategy == "prefer_api":
                return api_response if api_response else local_response
            elif strategy == "combine":
                # Simple combination strategy
                if local_response and api_response:
                    return f"{local_response}\n\n[Enhanced with additional context: {api_response[:200]}...]"
                else:
                    return local_response or api_response
            else:
                return api_response if api_response else local_response
        
        # Fallback
        return local_response or api_response or ""
    
    except Exception as e:
        logger.error(f"Error integrating responses: {e}")
        return local_response or api_response or ""