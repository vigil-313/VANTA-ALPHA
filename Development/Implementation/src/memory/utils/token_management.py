"""
Token Management Utilities

This module provides utilities for managing tokens in the context window.

# TASK-REF: MEM_001 - Memory System Implementation
# CONCEPT-REF: CON-VANTA-004 - Memory System
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable

logger = logging.getLogger(__name__)


# Type for messages with required fields
MessageLike = Dict[str, Any]


def count_tokens(messages: List[MessageLike]) -> int:
    """
    Count the number of tokens in a list of messages.
    
    Args:
        messages: List of message objects with 'content' field.
        
    Returns:
        Estimated token count.
    """
    try:
        # First try to use tiktoken for accurate counting if available
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")  # Default for recent models
        
        token_count = 0
        for msg in messages:
            # Count tokens in the message content
            content = msg.get('content', '')
            if content:
                token_count += len(encoding.encode(content))
            
            # Count tokens in role (typically small)
            role = msg.get('role', '')
            if role:
                token_count += len(encoding.encode(role))
            
            # Add overhead for message formatting (varies by model)
            token_count += 4  # Approximate overhead per message
        
        # Add base overhead for the conversation
        token_count += 2
        
        return token_count
    
    except ImportError:
        # Fall back to a simple approximation if tiktoken is not available
        logger.warning("tiktoken not available, using approximate token counting")
        return _approximate_token_count(messages)


def _approximate_token_count(messages: List[MessageLike]) -> int:
    """
    Approximate the number of tokens in a list of messages.
    
    Args:
        messages: List of message objects with 'content' field.
        
    Returns:
        Estimated token count.
    """
    # Simple approximation: ~4 characters per token on average
    chars_per_token = 4.0
    
    total_chars = 0
    for msg in messages:
        content = msg.get('content', '')
        if isinstance(content, str):
            total_chars += len(content)
        
        # Add a small overhead for message metadata
        total_chars += 10
    
    # Convert character count to token count
    return int(total_chars / chars_per_token) + (len(messages) * 4)


def truncate_messages_to_token_limit(
    messages: List[MessageLike], 
    max_tokens: int, 
    preserve_latest: bool = True
) -> List[MessageLike]:
    """
    Truncate a list of messages to fit within a token limit.
    
    Args:
        messages: List of message objects with 'content' field.
        max_tokens: Maximum number of tokens allowed.
        preserve_latest: If True, remove older messages first. If False, remove newest.
        
    Returns:
        Truncated list of messages.
    """
    if not messages:
        return []
    
    # If we're already under the limit, return the original list
    current_tokens = count_tokens(messages)
    if current_tokens <= max_tokens:
        return messages.copy()
    
    # Clone the message list
    if preserve_latest:
        # Remove from beginning (oldest first)
        working_messages = messages.copy()
        result = []
        
        # Add messages from newest to oldest until we hit the limit
        token_count = 0
        for msg in reversed(working_messages):
            msg_tokens = count_tokens([msg])
            if token_count + msg_tokens <= max_tokens:
                result.insert(0, msg)
                token_count += msg_tokens
            else:
                break
    else:
        # Remove from end (newest first)
        working_messages = messages.copy()
        result = []
        
        # Add messages from oldest to newest until we hit the limit
        token_count = 0
        for msg in working_messages:
            msg_tokens = count_tokens([msg])
            if token_count + msg_tokens <= max_tokens:
                result.append(msg)
                token_count += msg_tokens
            else:
                break
    
    logger.debug(f"Truncated messages from {len(messages)} to {len(result)} to fit within {max_tokens} tokens")
    return result


def estimate_max_response_tokens(prompt_tokens: int, model_max_tokens: int = 4096) -> int:
    """
    Estimate the maximum number of tokens available for model response.
    
    Args:
        prompt_tokens: Number of tokens in the prompt.
        model_max_tokens: Maximum context length for the model.
        
    Returns:
        Estimated maximum response tokens.
    """
    # Default to leave 20% of the max tokens for the response (minimum 100)
    default_response_portion = max(100, int(model_max_tokens * 0.2))
    
    # Calculate the remaining tokens
    remaining = max(0, model_max_tokens - prompt_tokens)
    
    # Use the larger of remaining or default portion
    return max(remaining, default_response_portion)


def optimize_prompt_for_tokens(
    prompt: str, 
    max_tokens: int,
    tokenizer: Optional[Callable[[str], List[int]]] = None
) -> str:
    """
    Optimize a prompt to fit within a token limit.
    
    Args:
        prompt: The prompt text to optimize.
        max_tokens: Maximum number of tokens allowed.
        tokenizer: Optional tokenizer function. If None, will use tiktoken or approximation.
        
    Returns:
        Optimized prompt text.
    """
    # Define a function to count tokens in a string
    def count_string_tokens(text: str) -> int:
        if tokenizer:
            return len(tokenizer(text))
        
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # Fall back to character approximation
            return int(len(text) / 4.0)
    
    # Check if we're already under the limit
    current_tokens = count_string_tokens(prompt)
    if current_tokens <= max_tokens:
        return prompt
    
    # Perform truncation to fit the token limit
    # This is a simple implementation that tries to preserve sentence boundaries
    sentences = prompt.split('. ')
    result = []
    token_count = 0
    
    for sentence in sentences:
        sentence_tokens = count_string_tokens(sentence + '. ')
        if token_count + sentence_tokens <= max_tokens:
            result.append(sentence)
            token_count += sentence_tokens
        else:
            break
    
    # Join sentences and ensure it ends with a period
    optimized_prompt = '. '.join(result)
    if optimized_prompt and not optimized_prompt.endswith('.'):
        optimized_prompt += '.'
    
    logger.debug(f"Optimized prompt from {current_tokens} tokens to {count_string_tokens(optimized_prompt)} tokens")
    return optimized_prompt