#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Model Retry Strategy for VANTA.

This module implements retry strategies for API requests.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# CONCEPT-REF: CON-AM-003 - API Fallback Mechanisms
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import time
import logging
import random
from typing import Any, Callable, List, Optional, Type, TypeVar

from .exceptions import (
    APIModelError, 
    APITimeoutError,
    APIRateLimitError,
    APIServiceUnavailableError
)

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Generic type for function return value


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error should trigger a retry.
    
    Args:
        error: The exception to check
        
    Returns:
        True if the error is retryable, False otherwise
    """
    # Timeout errors are always retryable
    if isinstance(error, APITimeoutError):
        return True
    
    # Rate limit errors are retryable with backoff
    if isinstance(error, APIRateLimitError):
        return True
    
    # Service unavailable errors are retryable
    if isinstance(error, APIServiceUnavailableError):
        return True
    
    # Check for network-related errors by string matching
    error_str = str(error).lower()
    retryable_patterns = [
        "timeout", 
        "connection error",
        "connection reset",
        "temporary failure",
        "service unavailable",
        "server error",
        "internal server error",
        "502",
        "503",
        "504"
    ]
    
    return any(pattern in error_str for pattern in retryable_patterns)


def with_retry(
    func: Callable[[], T],
    max_attempts: int = 3,
    backoff_factor: float = 1.5,
    jitter: bool = True,
    retryable_errors: Optional[List[Type[Exception]]] = None
) -> T:
    """Execute a function with exponential backoff retry.
    
    Args:
        func: Function to execute
        max_attempts: Maximum number of attempts
        backoff_factor: Factor to increase delay between attempts
        jitter: Whether to add random jitter to delay
        retryable_errors: List of exception types that should trigger a retry
            
    Returns:
        Result of the function
        
    Raises:
        Exception: The last exception encountered if all attempts fail
    """
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_error = e
            
            # Check if this error is retryable
            retry = False
            
            if retryable_errors and isinstance(e, tuple(retryable_errors)):
                retry = True
            elif is_retryable_error(e):
                retry = True
                
            if not retry or attempt == max_attempts - 1:
                # Not retryable or last attempt
                raise
                
            # Calculate delay with exponential backoff
            delay = backoff_factor ** attempt
            
            # Add jitter to prevent thundering herd problem
            if jitter:
                delay *= (0.5 + random.random())
                
            logger.warning(
                f"Attempt {attempt + 1}/{max_attempts} failed with error: {str(e)}. "
                f"Retrying in {delay:.2f} seconds..."
            )
            
            time.sleep(delay)
    
    # This should never happen due to the raise in the loop
    raise last_error if last_error else RuntimeError("All retry attempts failed")