"""
Token counting utilities for model management.

# TASK-REF: LM_001 - Local Model Integration
# CONCEPT-REF: CON-VANTA-002 - Local Model Integration
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


def estimate_token_count(text: str, model_type: str = "llama2") -> int:
    """
    Estimate the number of tokens in text for a given model type.
    This is an approximate method when the model isn't loaded yet.
    
    Args:
        text: The text to count tokens for
        model_type: The model type to estimate for
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    # Simple estimator based on average token lengths for different model types
    # These are rough estimates and should be replaced with actual tokenization when possible
    avg_chars_per_token = {
        "llama2": 4.0,
        "mistral": 4.0,
        "vicuna": 4.0,
        "chatml": 4.0,
        "gpt2": 4.0,  # GPT-2 tokenizer (used by many models)
        "tiktoken": 3.75,  # OpenAI models
    }
    
    # Use the right average value based on model type
    chars_per_token = avg_chars_per_token.get(model_type, 4.0)
    
    # Estimate token count
    return max(1, int(len(text) / chars_per_token))


def count_message_tokens(messages: List[Dict[str, str]], model_type: str = "llama2") -> Dict[str, int]:
    """
    Count tokens in a list of messages.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model_type: Model type to count tokens for
        
    Returns:
        Dictionary with token counts by role and total
    """
    result = {
        "system": 0,
        "user": 0,
        "assistant": 0,
        "total": 0,
        "formatting": 0,  # Overhead for formatting
    }
    
    # Formatting overhead based on model type (approximate)
    formatting_overhead = {
        "llama2": 15,  # tokens for [INST], [/INST], etc.
        "mistral": 10,
        "vicuna": 8,
        "chatml": 20,  # ChatML has more formatting
    }
    
    # Add base formatting overhead
    result["formatting"] = formatting_overhead.get(model_type, 10)
    
    # Count tokens in each message
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        
        # Count tokens in the message
        token_count = estimate_token_count(content, model_type)
        
        # Add to the appropriate category
        if role in result:
            result[role] += token_count
        else:
            # Default to user if unknown role
            result["user"] += token_count
        
        # Add a small overhead for each message
        result["formatting"] += 4
    
    # Calculate total
    result["total"] = result["system"] + result["user"] + result["assistant"] + result["formatting"]
    
    return result


def check_context_limit(token_count: int, context_size: int, max_new_tokens: int = 0) -> bool:
    """
    Check if a token count fits within context limits.
    
    Args:
        token_count: Number of tokens to check
        context_size: Maximum context size of the model
        max_new_tokens: Maximum number of new tokens to generate
        
    Returns:
        True if within limits, False otherwise
    """
    # If max_new_tokens is provided, we need to ensure there's room for generation
    if max_new_tokens > 0:
        return token_count + max_new_tokens <= context_size
    
    # Otherwise just check against context size
    return token_count <= context_size


def optimize_prompt_for_length(
    messages: List[Dict[str, str]],
    max_tokens: int,
    model_type: str = "llama2",
    preserve_system: bool = True
) -> List[Dict[str, str]]:
    """
    Optimize a prompt to fit within token limits by removing older messages.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        max_tokens: Maximum number of tokens allowed
        model_type: Model type to count tokens for
        preserve_system: Whether to preserve the system message
        
    Returns:
        Optimized list of messages
    """
    if not messages:
        return []
    
    # Count tokens in the full message list
    token_counts = count_message_tokens(messages, model_type)
    total_tokens = token_counts["total"]
    
    # If already within limits, return as is
    if total_tokens <= max_tokens:
        return messages
    
    # If we need to optimize
    optimized_messages = []
    remaining_tokens = max_tokens
    
    # First, handle system message if it exists and should be preserved
    if preserve_system:
        system_messages = [m for m in messages if m.get("role") == "system"]
        if system_messages:
            system_message = system_messages[0]
            system_tokens = estimate_token_count(system_message.get("content", ""), model_type)
            # Add formatting overhead
            system_tokens += 10
            
            # Add system message if it fits
            if system_tokens < remaining_tokens * 0.75:  # Reserve at least 25% for conversation
                optimized_messages.append(system_message)
                remaining_tokens -= system_tokens
    
    # Then, add most recent messages until we hit the limit
    # Start from the end (most recent) and work backwards
    conversation_messages = [m for m in messages if m.get("role") != "system"]
    
    # Calculate base formatting overhead
    formatting_overhead = 10  # Base overhead
    
    for message in reversed(conversation_messages):
        content = message.get("content", "")
        message_tokens = estimate_token_count(content, model_type) + 5  # 5 tokens for formatting
        
        if message_tokens <= remaining_tokens:
            optimized_messages.insert(0 if message.get("role") == "system" else len(optimized_messages), message)
            remaining_tokens -= message_tokens
        else:
            # No more space
            break
    
    # If we couldn't fit any conversation messages, try truncating the last one
    if not optimized_messages or all(m.get("role") == "system" for m in optimized_messages):
        last_message = conversation_messages[-1]
        content = last_message.get("content", "")
        
        # Estimate how much we can keep
        keepable_chars = int(remaining_tokens * 4)  # rough chars-to-tokens conversion
        if keepable_chars > 50:  # Only if we can keep a meaningful amount
            truncated_content = content[-keepable_chars:]
            truncated_message = {
                "role": last_message.get("role", "user"),
                "content": "... " + truncated_content
            }
            optimized_messages.append(truncated_message)
    
    return optimized_messages