#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Model Response Parser for VANTA.

This module handles parsing and processing responses from API models.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import logging
from typing import Any, Dict, List, Optional, Union

from .exceptions import APIInvalidResponseError

logger = logging.getLogger(__name__)


def parse_anthropic_response(response: Any) -> str:
    """Parse a response from the Anthropic Claude API.
    
    Args:
        response: API response object
        
    Returns:
        Extracted text content
        
    Raises:
        APIInvalidResponseError: If the response format is invalid
    """
    try:
        # Modern Messages API response format
        if hasattr(response, "content") and response.content:
            # Extract text from the first content block
            if isinstance(response.content, list) and len(response.content) > 0:
                # Handle different content types
                for content_block in response.content:
                    if hasattr(content_block, "text") and content_block.text:
                        return content_block.text
                    if isinstance(content_block, dict) and "text" in content_block:
                        return content_block["text"]
                
                # No text content found
                raise APIInvalidResponseError("No text content found in Anthropic response")
            
            # Handle direct content attribute
            if isinstance(response.content, str):
                return response.content
        
        # Legacy Completion API response format
        if hasattr(response, "completion") and response.completion:
            return response.completion
            
        # Handle dictionary response
        if isinstance(response, dict):
            if "content" in response and isinstance(response["content"], list):
                for block in response["content"]:
                    if "text" in block:
                        return block["text"]
            if "completion" in response:
                return response["completion"]
        
        # If we get here, we couldn't parse the response
        logger.error(f"Unknown Anthropic response format: {type(response)}")
        
        # Last resort, convert to string
        return str(response)
    except Exception as e:
        raise APIInvalidResponseError(f"Failed to parse Anthropic response: {str(e)}")


def parse_openai_response(response: Any) -> str:
    """Parse a response from the OpenAI GPT API.
    
    Args:
        response: API response object
        
    Returns:
        Extracted text content
        
    Raises:
        APIInvalidResponseError: If the response format is invalid
    """
    try:
        # Standard completion response format
        if hasattr(response, "choices") and response.choices:
            # Extract text from the first choice
            if len(response.choices) > 0:
                choice = response.choices[0]
                
                # Chat completion format
                if hasattr(choice, "message") and choice.message:
                    if hasattr(choice.message, "content") and choice.message.content is not None:
                        return choice.message.content
                    if isinstance(choice.message, dict) and "content" in choice.message:
                        return choice.message["content"]
                
                # Legacy completion format
                if hasattr(choice, "text") and choice.text:
                    return choice.text
                
                # Delta format for streaming
                if hasattr(choice, "delta") and choice.delta:
                    if hasattr(choice.delta, "content") and choice.delta.content:
                        return choice.delta.content
                    if isinstance(choice.delta, dict) and "content" in choice.delta:
                        return choice.delta["content"]
        
        # Handle dictionary response
        if isinstance(response, dict):
            if "choices" in response and isinstance(response["choices"], list) and len(response["choices"]) > 0:
                choice = response["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
                if "text" in choice:
                    return choice["text"]
                if "delta" in choice and "content" in choice["delta"]:
                    return choice["delta"]["content"]
        
        # If we get here, we couldn't parse the response
        logger.error(f"Unknown OpenAI response format: {type(response)}")
        
        # Last resort, convert to string
        return str(response)
    except Exception as e:
        raise APIInvalidResponseError(f"Failed to parse OpenAI response: {str(e)}")


def check_for_content_filter(response: Any) -> bool:
    """Check if content was filtered by the API's content policy.
    
    Args:
        response: API response object
        
    Returns:
        True if content was filtered, False otherwise
    """
    # Check for Anthropic content filtering
    if hasattr(response, "stop_reason") and response.stop_reason == "content_filtered":
        return True
    
    # Check for OpenAI content filtering
    if hasattr(response, "choices") and response.choices:
        for choice in response.choices:
            if hasattr(choice, "finish_reason") and choice.finish_reason == "content_filter":
                return True
    
    # Check dictionary format
    if isinstance(response, dict):
        if response.get("stop_reason") == "content_filtered":
            return True
        if "choices" in response and isinstance(response["choices"], list):
            for choice in response["choices"]:
                if isinstance(choice, dict) and choice.get("finish_reason") == "content_filter":
                    return True
    
    return False


def extract_response_metadata(response: Any) -> Dict[str, Any]:
    """Extract metadata from an API response.
    
    Args:
        response: API response object
        
    Returns:
        Dictionary with response metadata
    """
    metadata = {}
    
    # Extract common metadata fields
    if hasattr(response, "id"):
        metadata["response_id"] = response.id
    elif isinstance(response, dict) and "id" in response:
        metadata["response_id"] = response["id"]
    
    # Extract model information
    if hasattr(response, "model"):
        metadata["model"] = response.model
    elif isinstance(response, dict) and "model" in response:
        metadata["model"] = response["model"]
    
    # Extract token usage
    if hasattr(response, "usage"):
        usage = response.usage
        metadata["token_usage"] = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None)
        }
    elif isinstance(response, dict) and "usage" in response:
        usage = response["usage"]
        metadata["token_usage"] = {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens")
        }
    
    # Extract finish reason
    if hasattr(response, "choices") and response.choices and len(response.choices) > 0:
        if hasattr(response.choices[0], "finish_reason"):
            metadata["finish_reason"] = response.choices[0].finish_reason
    elif isinstance(response, dict) and "choices" in response and response["choices"]:
        if "finish_reason" in response["choices"][0]:
            metadata["finish_reason"] = response["choices"][0]["finish_reason"]
    
    # Extract Anthropic-specific fields
    if hasattr(response, "stop_reason"):
        metadata["stop_reason"] = response.stop_reason
    elif isinstance(response, dict) and "stop_reason" in response:
        metadata["stop_reason"] = response["stop_reason"]
    
    return metadata