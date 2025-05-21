#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Model Request Builder for VANTA.

This module handles formatting and building requests for API models.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import logging
from typing import Any, Dict, List, Optional, Union

from .exceptions import APIInvalidRequestError

logger = logging.getLogger(__name__)

# Type definitions
PromptType = Union[str, List[Dict[str, str]]]
MessageType = Dict[str, str]


def sanitize_parameters(params: Dict[str, Any], allowed_params: List[str]) -> Dict[str, Any]:
    """Filter parameters to only include allowed ones.
    
    Args:
        params: Parameters to filter
        allowed_params: List of allowed parameter names
        
    Returns:
        Filtered parameters dictionary
    """
    return {k: v for k, v in params.items() if k in allowed_params}


def format_anthropic_request(
    prompt: PromptType, 
    model_id: str, 
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format a request for the Anthropic Claude API.
    
    Args:
        prompt: Input prompt (string or message list)
        model_id: Model identifier
        params: Optional generation parameters
        
    Returns:
        Dictionary with formatted request parameters
        
    Raises:
        APIInvalidRequestError: If the prompt format is invalid
    """
    params = params or {}
    
    # Base parameters
    request = {
        "model": model_id,
        "max_tokens": params.get("max_tokens", 1024),
        "temperature": params.get("temperature", 0.7),
        "top_p": params.get("top_p", 0.9),
        "stream": params.get("stream", False),
    }
    
    # Add optional parameters if present
    optional_params = [
        "top_k", "stop_sequences", "system", "metadata"
    ]
    
    for param in optional_params:
        if param in params:
            request[param] = params[param]
    
    # Format prompt based on type
    if isinstance(prompt, str):
        # Simple string prompt (legacy format - converted to messages)
        request["messages"] = [{"role": "user", "content": prompt}]
    elif isinstance(prompt, list):
        # Message list format
        messages = []
        system_content = None
        
        for msg in prompt:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise APIInvalidRequestError(
                    "Messages must be dictionaries with 'role' and 'content' keys"
                )
            
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            if role == "system":
                # Extract system message for special handling
                system_content = content
            elif role == "user":
                messages.append({"role": "user", "content": content})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": content})
            else:
                logger.warning(f"Ignoring message with unknown role: {role}")
        
        # Set system content if present
        if system_content:
            request["system"] = system_content
        
        # Set messages
        request["messages"] = messages
    else:
        raise APIInvalidRequestError(
            f"Invalid prompt format. Expected string or message list, got {type(prompt)}"
        )
    
    return request


def format_openai_request(
    prompt: PromptType, 
    model_id: str, 
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format a request for the OpenAI GPT API.
    
    Args:
        prompt: Input prompt (string or message list)
        model_id: Model identifier
        params: Optional generation parameters
        
    Returns:
        Dictionary with formatted request parameters
        
    Raises:
        APIInvalidRequestError: If the prompt format is invalid
    """
    params = params or {}
    
    # Base parameters
    request = {
        "model": model_id,
        "max_tokens": params.get("max_tokens", 1024),
        "temperature": params.get("temperature", 0.7),
        "top_p": params.get("top_p", 0.9),
        "stream": params.get("stream", False),
    }
    
    # Add optional parameters if present
    optional_params = [
        "n", "stop", "presence_penalty", "frequency_penalty", "logit_bias",
        "user", "response_format", "seed"
    ]
    
    for param in optional_params:
        if param in params:
            request[param] = params[param]
    
    # Format prompt based on type
    if isinstance(prompt, str):
        # Simple string prompt - convert to messages format
        request["messages"] = [{"role": "user", "content": prompt}]
    elif isinstance(prompt, list):
        # Message list format - convert to OpenAI format
        messages = []
        
        for msg in prompt:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise APIInvalidRequestError(
                    "Messages must be dictionaries with 'role' and 'content' keys"
                )
            
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            if role in ["system", "user", "assistant", "function", "tool"]:
                messages.append({"role": role, "content": content})
                
                # Handle function/tool responses
                if "name" in msg and role in ["function", "tool"]:
                    messages[-1]["name"] = msg["name"]
            else:
                logger.warning(f"Ignoring message with unknown role: {role}")
        
        # Set messages
        request["messages"] = messages
    else:
        raise APIInvalidRequestError(
            f"Invalid prompt format. Expected string or message list, got {type(prompt)}"
        )
    
    # Handle function/tool calling if present
    if "tools" in params:
        request["tools"] = params["tools"]
    if "tool_choice" in params:
        request["tool_choice"] = params["tool_choice"]
    if "functions" in params:
        request["functions"] = params["functions"]
    if "function_call" in params:
        request["function_call"] = params["function_call"]
    
    return request


def format_normalized_messages(messages: List[MessageType]) -> List[MessageType]:
    """Format messages into a normalized format that works across providers.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Normalized message list
    """
    normalized = []
    
    for msg in messages:
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            raise APIInvalidRequestError(
                "Messages must be dictionaries with 'role' and 'content' keys"
            )
        
        role = msg.get("role", "").lower()
        content = msg.get("content", "")
        
        # Only include standard roles
        if role in ["system", "user", "assistant"]:
            normalized.append({
                "role": role,
                "content": content
            })
    
    return normalized


def extract_system_message(messages: List[MessageType]) -> Optional[str]:
    """Extract system message from a list of messages.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        System message content or None if not found
    """
    for msg in messages:
        if msg.get("role", "").lower() == "system":
            return msg.get("content", "")
    
    return None