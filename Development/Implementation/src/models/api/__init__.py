#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Model Client package for VANTA.

This package provides integration with cloud-based language models like Claude and GPT-4.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Processing
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

from .interface import APIModelInterface
from .api_manager import APIModelManager
from .anthropic_client import AnthropicClient
from .openai_client import OpenAIClient
from .exceptions import (
    APIModelError,
    APIInitializationError,
    APICredentialError,
    APIRequestError,
    APIResponseError,
    APITimeoutError,
    APIRateLimitError,
    APIQuotaExceededError,
    APIServiceUnavailableError,
    APIAuthenticationError,
    APIInvalidRequestError,
    APIInvalidResponseError,
    APIContentFilterError,
    APIConfigurationError
)
from .credentials import (
    load_credential,
    save_credential,
    remove_credential,
    get_credential
)
from .config import load_config, save_config
from .token_counter import (
    count_tokens_anthropic,
    count_tokens_openai,
    count_prompt_tokens
)

__all__ = [
    # Core interfaces and managers
    'APIModelInterface',
    'APIModelManager',
    
    # Client implementations
    'AnthropicClient',
    'OpenAIClient',
    
    # Exceptions
    'APIModelError',
    'APIInitializationError',
    'APICredentialError',
    'APIRequestError',
    'APIResponseError',
    'APITimeoutError',
    'APIRateLimitError',
    'APIQuotaExceededError',
    'APIServiceUnavailableError',
    'APIAuthenticationError',
    'APIInvalidRequestError',
    'APIInvalidResponseError',
    'APIContentFilterError',
    'APIConfigurationError',
    
    # Credential management
    'load_credential',
    'save_credential',
    'remove_credential',
    'get_credential',
    
    # Configuration
    'load_config',
    'save_config',
    
    # Token counting
    'count_tokens_anthropic',
    'count_tokens_openai',
    'count_prompt_tokens'
]