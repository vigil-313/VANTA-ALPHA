#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token Counting Utilities for API Models.

This module provides utilities for estimating token usage in API models.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import json
import logging
import importlib.util
from typing import Dict, List, Optional, Union, Any

logger = logging.getLogger(__name__)

PromptType = Union[str, List[Dict[str, str]]]

# Default tokens per character ratios for estimation
DEFAULT_TOKENS_PER_CHAR = {
    "anthropic": 0.25,  # ~4 characters per token for Claude
    "openai": 0.25,     # ~4 characters per token for GPT models
    "default": 0.25     # Default fallback
}


def _has_tiktoken() -> bool:
    """Check if tiktoken is available.
    
    Returns:
        True if tiktoken is available, False otherwise
    """
    return importlib.util.find_spec("tiktoken") is not None


def estimate_token_count(text: str, provider: str = "default") -> int:
    """Estimate token count for a text string.
    
    Args:
        text: Text to estimate tokens for
        provider: Provider name for ratio selection
        
    Returns:
        Estimated token count
    """
    # Calculate based on character count and provider-specific ratio
    ratio = DEFAULT_TOKENS_PER_CHAR.get(provider, DEFAULT_TOKENS_PER_CHAR["default"])
    return max(1, int(len(text) * ratio))


def count_tokens_anthropic(text: str) -> int:
    """Count tokens for Anthropic Claude using correct tokenizer if available.
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Token count
    """
    try:
        # Try to use Anthropic's tokenizer if it's available
        import anthropic
        if hasattr(anthropic, 'count_tokens'):
            return anthropic.count_tokens(text)
    except ImportError:
        logger.debug("Anthropic package not available for token counting")
    
    # Fallback to estimation
    return estimate_token_count(text, "anthropic")


def count_tokens_openai(text: str, model: str = "gpt-4") -> int:
    """Count tokens for OpenAI models using tiktoken if available.
    
    Args:
        text: Text to count tokens for
        model: Model name for encoding selection
        
    Returns:
        Token count
    """
    if _has_tiktoken():
        try:
            import tiktoken
            
            # Select the right encoding based on model
            if model.startswith("gpt-4"):
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif model.startswith("gpt-3.5"):
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                encoding = tiktoken.get_encoding("cl100k_base")  # Default to cl100k
                
            # Count tokens
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Error using tiktoken: {str(e)}")
    
    # Fallback to estimation
    return estimate_token_count(text, "openai")


def count_message_tokens(
    messages: List[Dict[str, str]], provider: str = "openai", model: Optional[str] = None
) -> int:
    """Count tokens for a list of messages.
    
    Args:
        messages: List of message dictionaries
        provider: Provider name
        model: Optional model name
        
    Returns:
        Token count
    """
    if not messages:
        return 0
    
    total_tokens = 0
    
    # Format-specific token counting
    if provider == "openai":
        # Use tiktoken for precise counting if available
        if _has_tiktoken():
            try:
                import tiktoken
                
                # Select encoding based on model
                if model and model.startswith("gpt-4"):
                    encoding = tiktoken.encoding_for_model("gpt-4")
                elif model and model.startswith("gpt-3.5"):
                    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
                else:
                    encoding = tiktoken.get_encoding("cl100k_base")
                
                # Count per OpenAI's formula: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
                # Every message follows <im_start>{role/name}\n{content}<im_end>\n
                # 3 tokens for im_start and im_end, 1 for \n after role
                tokens_per_message = 3
                
                for message in messages:
                    total_tokens += tokens_per_message
                    
                    for key, value in message.items():
                        if isinstance(value, str):
                            total_tokens += len(encoding.encode(value))
                        elif isinstance(value, (dict, list)):
                            # Handle JSON objects by serializing
                            value_str = json.dumps(value)
                            total_tokens += len(encoding.encode(value_str))
                    
                    # Add tokens for the name if present
                    if message.get("name"):
                        total_tokens += 1  # Extra token for name
                
                # Add 3 tokens for assistant label at the end
                total_tokens += 3
                
                return total_tokens
            except Exception as e:
                logger.warning(f"Error counting tokens with tiktoken: {str(e)}")
    
    # Fallback: convert to strings and estimate
    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")
        
        # Add tokens for role
        total_tokens += estimate_token_count(role, provider)
        
        # Add tokens for content
        if isinstance(content, str):
            total_tokens += estimate_token_count(content, provider)
        elif isinstance(content, (dict, list)):
            # Handle structured content
            content_str = json.dumps(content)
            total_tokens += estimate_token_count(content_str, provider)
    
    # Add overhead for message formatting
    message_overhead = len(messages) * 4  # Approximate overhead per message
    total_tokens += message_overhead
    
    return total_tokens


def count_prompt_tokens(prompt: PromptType, provider: str = "openai", model: Optional[str] = None) -> int:
    """Count tokens for a prompt (string or message list).
    
    Args:
        prompt: Prompt to count tokens for
        provider: Provider name
        model: Optional model name
        
    Returns:
        Token count
    """
    if isinstance(prompt, str):
        # Simple string prompt
        if provider == "anthropic":
            return count_tokens_anthropic(prompt)
        elif provider == "openai":
            return count_tokens_openai(prompt, model or "gpt-4")
        else:
            return estimate_token_count(prompt, provider)
    elif isinstance(prompt, list):
        # Message list format
        return count_message_tokens(prompt, provider, model)
    else:
        # Unsupported format
        logger.warning(f"Unsupported prompt type for token counting: {type(prompt)}")
        return 0