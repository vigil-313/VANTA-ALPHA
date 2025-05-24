#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph Conditional Routing Functions

This module implements the conditional routing logic for VANTA's LangGraph workflow.
The routing functions determine the flow between nodes based on system state,
query characteristics, and resource availability.
"""
# TASK-REF: LG_003 - LangGraph Graph Definition and Conditional Routing
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration
# CONCEPT-REF: CON-VANTA-007 - Dual-Track Processing
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

import time
import logging
from typing import Dict, Any

from .state import VANTAState, ActivationStatus

logger = logging.getLogger(__name__)


def should_process(state: VANTAState) -> str:
    """
    Determines if we should process audio based on activation status.
    
    This function checks if the system is currently activated and should
    proceed with processing the audio input, or if it should end the workflow.
    
    Args:
        state: Current VANTA state
        
    Returns:
        str: "continue" if processing should continue, "end" otherwise
    """
    try:
        if state["activation"]["status"] == ActivationStatus.INACTIVE:
            logger.debug("Activation status is INACTIVE, ending workflow")
            return "end"
        
        logger.debug(f"Activation status is {state['activation']['status']}, continuing workflow")
        return "continue"
    except KeyError as e:
        # If activation status is missing, assume inactive
        logger.warning(f"Activation status missing from state: {e}, ending workflow")
        return "end"
    except Exception as e:
        logger.error(f"Error checking activation status: {e}, ending workflow")
        return "end"


def determine_processing_path(state: VANTAState) -> str:
    """
    Determines which processing path to take based on routing decision.
    
    This function examines the routing decision made by the router_node
    and directs the workflow to the appropriate processing path (local,
    API, or parallel).
    
    Args:
        state: Current VANTA state
        
    Returns:
        str: "local", "api", or "parallel" based on processing path
    """
    try:
        path = state["memory"]["processing"]["path"]
        
        if path == "local":
            logger.debug("Routing to local model processing")
            return "local"
        elif path == "api":
            logger.debug("Routing to API model processing")
            return "api"
        else:  # "parallel" or any other value
            logger.debug(f"Routing to parallel processing (path was: {path})")
            return "parallel"
            
    except (KeyError, TypeError) as e:
        # Default to parallel if path not specified
        logger.warning(f"Processing path not specified ({e}), defaulting to parallel")
        return "parallel"
    except Exception as e:
        logger.error(f"Error determining processing path: {e}, defaulting to parallel")
        return "parallel"


def check_processing_complete(state: VANTAState) -> str:
    """
    Checks if processing is complete and we can integrate responses.
    
    This function examines the processing state to determine if the
    required models have completed their processing and we can proceed
    to response integration.
    
    Args:
        state: Current VANTA state
        
    Returns:
        str: "ready" if processing is complete, "waiting" otherwise
    """
    try:
        processing = state["memory"]["processing"]
        path = processing.get("path", "parallel")
        
        # Check appropriate completion flags based on path
        if path == "local":
            if processing.get("local_completed", False):
                logger.debug("Local processing complete, ready for integration")
                return "ready"
            else:
                logger.debug("Local processing not complete, waiting")
                return "waiting"
                
        elif path == "api":
            if processing.get("api_completed", False):
                logger.debug("API processing complete, ready for integration")
                return "ready"
            else:
                logger.debug("API processing not complete, waiting")
                return "waiting"
                
        elif path == "parallel":
            local_complete = processing.get("local_completed", False)
            api_complete = processing.get("api_completed", False)
            
            # For parallel, we can proceed if either is complete
            if local_complete or api_complete:
                logger.debug(f"Parallel processing ready (local: {local_complete}, api: {api_complete})")
                return "ready"
            
            # Check timeout for parallel processing
            start_time = processing.get("start_time")
            if start_time:
                current_time = time.time()
                timeout = processing.get("timeout", 10.0)  # Default 10 second timeout
                if current_time - start_time > timeout:
                    # If we've waited too long, use whatever we have
                    logger.warning(f"Processing timeout ({timeout}s) reached, proceeding with available results")
                    return "ready"
            
            logger.debug("Parallel processing not complete, waiting")
            return "waiting"
        
        # Unknown path, default to waiting
        logger.warning(f"Unknown processing path: {path}, waiting")
        return "waiting"
        
    except (KeyError, TypeError) as e:
        logger.error(f"Error checking processing completion: {e}, waiting")
        return "waiting"
    except Exception as e:
        logger.error(f"Unexpected error checking processing completion: {e}, waiting")
        return "waiting"


def should_synthesize_speech(state: VANTAState) -> str:
    """
    Determines if we should synthesize speech based on response availability.
    
    Args:
        state: Current VANTA state
        
    Returns:
        str: "synthesize" if we should create speech, "skip" otherwise
    """
    try:
        # Check if we have a response to synthesize
        messages = state.get("messages", [])
        if not messages:
            logger.debug("No messages to synthesize, skipping speech synthesis")
            return "skip"
            
        # Get the last message (should be our response)
        last_message = messages[-1]
        if last_message.get("role") != "assistant":
            logger.debug("Last message is not from assistant, skipping speech synthesis")
            return "skip"
            
        content = last_message.get("content", "")
        if not content or content.strip() == "":
            logger.debug("Empty response content, skipping speech synthesis")
            return "skip"
            
        # Check if synthesis is enabled
        config = state.get("config", {})
        if not config.get("tts_enabled", True):
            logger.debug("TTS disabled in config, skipping speech synthesis")
            return "skip"
            
        logger.debug("Response available and TTS enabled, proceeding with synthesis")
        return "synthesize"
        
    except Exception as e:
        logger.error(f"Error checking speech synthesis conditions: {e}, skipping synthesis")
        return "skip"


def should_update_memory(state: VANTAState) -> str:
    """
    Determines if we should update memory based on conversation state.
    
    Args:
        state: Current VANTA state
        
    Returns:
        str: "update" if we should update memory, "skip" otherwise
    """
    try:
        # Check if we have new conversation content to store
        messages = state.get("messages", [])
        if len(messages) < 2:  # Need at least user input and assistant response
            logger.debug("Insufficient messages for memory update, skipping")
            return "skip"
            
        # Check if memory updates are enabled
        config = state.get("config", {})
        if not config.get("memory_enabled", True):
            logger.debug("Memory updates disabled in config, skipping")
            return "skip"
            
        # Check if this conversation has already been stored
        memory = state.get("memory", {})
        last_stored_count = memory.get("last_stored_message_count", 0)
        current_count = len(messages)
        
        if current_count <= last_stored_count:
            logger.debug(f"No new messages to store (current: {current_count}, last stored: {last_stored_count})")
            return "skip"
            
        logger.debug(f"New messages available for storage (current: {current_count}, last stored: {last_stored_count})")
        return "update"
        
    except Exception as e:
        logger.error(f"Error checking memory update conditions: {e}, updating anyway")
        return "update"


def should_summarize_conversation(state: VANTAState) -> str:
    """
    Determine if conversation summarization is needed.
    
    This function checks if the conversation history has grown beyond the
    configured threshold and needs to be summarized to manage memory usage.
    
    Args:
        state: Current VANTA state
        
    Returns:
        "summarize" if summarization is needed, "continue" otherwise
    """
    try:
        memory = state.get("memory", {})
        conversation_history = memory.get("conversation_history", [])
        summarization_threshold = state.get("config", {}).get("summarization_threshold", 10)
        
        if len(conversation_history) >= summarization_threshold:
            logger.info(f"Conversation history length ({len(conversation_history)}) exceeds threshold ({summarization_threshold}), triggering summarization")
            return "summarize"
        
        logger.debug(f"Conversation history length ({len(conversation_history)}) below threshold ({summarization_threshold}), continuing normally")
        return "continue"
        
    except Exception as e:
        logger.error(f"Error in should_summarize_conversation: {e}")
        return "continue"  # Default to continue on error


# Mapping of routing function names to functions for easy access
ROUTING_FUNCTIONS = {
    "should_process": should_process,
    "determine_processing_path": determine_processing_path, 
    "check_processing_complete": check_processing_complete,
    "should_synthesize_speech": should_synthesize_speech,
    "should_update_memory": should_update_memory,
    "should_summarize_conversation": should_summarize_conversation,
}


def get_routing_function(name: str):
    """
    Get a routing function by name.
    
    Args:
        name: Name of the routing function
        
    Returns:
        The routing function, or None if not found
    """
    return ROUTING_FUNCTIONS.get(name)


def list_routing_functions():
    """
    List all available routing functions.
    
    Returns:
        List of routing function names
    """
    return list(ROUTING_FUNCTIONS.keys())