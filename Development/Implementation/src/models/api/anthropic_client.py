#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anthropic Claude API Client for VANTA.

This module provides integration with the Anthropic Claude API.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import os
import logging
import importlib.util
from typing import Any, Dict, Iterator, List, Optional, Union

from .interface import APIModelInterface, PromptType, ParamsType
from .credentials import get_credential
from .token_counter import count_tokens_anthropic
from .request_builder import format_anthropic_request
from .response_parser import parse_anthropic_response, check_for_content_filter
from .retry_strategy import with_retry
from .exceptions import (
    APIInitializationError,
    APICredentialError,
    APIRequestError,
    APITimeoutError,
    APIRateLimitError,
    APIContentFilterError,
    APIInvalidResponseError
)

logger = logging.getLogger(__name__)


class MockAnthropicClient:
    """Mock implementation for the Anthropic client when SDK is not available."""
    
    def __init__(self, api_key: str):
        """Initialize the mock client.
        
        Args:
            api_key: Anthropic API key
        """
        self.api_key = api_key
    
    def messages(self):
        """Return a mock messages object."""
        return MockAnthropicMessages()
    
    def count_tokens(self, text: str) -> int:
        """Mock token counting.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        # Simple character-based estimate
        return max(1, len(text) // 4)


class MockAnthropicMessages:
    """Mock implementation for Anthropic messages API."""
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Mock message creation.
        
        Args:
            **kwargs: API parameters
            
        Returns:
            Mock response
        """
        # Create a minimal mock response
        return {
            "id": "msg_mock_12345",
            "content": [{"type": "text", "text": "This is a mock response from Claude."}],
            "model": kwargs.get("model", "claude-3-opus-20240229"),
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 10
            }
        }


class AnthropicClient(APIModelInterface):
    """Client for Anthropic Claude API."""
    
    def __init__(self):
        """Initialize Anthropic Claude client."""
        self.config = None
        self.api_key = None
        self.model_id = None
        self.client = None
        self.initialized = False
        self._anthropic_available = self._check_anthropic_available()
    
    def _check_anthropic_available(self) -> bool:
        """Check if the Anthropic Python SDK is available.
        
        Returns:
            True if available, False otherwise
        """
        return importlib.util.find_spec("anthropic") is not None
    
    def initialize(self, config: ParamsType = None) -> None:
        """Initialize the client with configuration.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            APIInitializationError: If initialization fails
        """
        self.config = config or {}
        
        try:
            # Get API key
            self.api_key = get_credential("anthropic", self.config)
            
            # Set model ID
            self.model_id = self.config.get("model_id", "claude-3-opus-20240229")
            
            # Set up client
            self.client = self._setup_client()
            
            self.initialized = True
            logger.info(f"Initialized Anthropic client with model: {self.model_id}")
        except APICredentialError as e:
            raise APIInitializationError(f"Anthropic API key not found: {str(e)}")
        except Exception as e:
            raise APIInitializationError(f"Failed to initialize Anthropic client: {str(e)}")
    
    def _setup_client(self) -> Any:
        """Set up the Anthropic API client.
        
        Returns:
            Anthropic API client
            
        Raises:
            APIInitializationError: If client setup fails
        """
        # Import the Anthropic SDK if available
        if self._anthropic_available:
            try:
                import anthropic
                return anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to create Anthropic client with SDK: {str(e)}")
                logger.warning("Falling back to mock implementation")
        else:
            logger.warning("Anthropic SDK not available, using mock implementation")
        
        # Fall back to mock implementation
        return MockAnthropicClient(self.api_key)
    
    def _ensure_initialized(self) -> None:
        """Ensure client is initialized before use.
        
        Raises:
            APIInitializationError: If client is not initialized
        """
        if not self.initialized:
            raise APIInitializationError("Anthropic client not initialized. Call initialize() first.")
    
    def generate(self, prompt: PromptType, params: ParamsType = None) -> str:
        """Generate a response from Claude.
        
        Args:
            prompt: Prompt data (string or message list)
            params: Optional generation parameters
            
        Returns:
            Generated response
            
        Raises:
            APIRequestError: If the request fails
            APIContentFilterError: If content is filtered
            APIInvalidResponseError: If the response cannot be parsed
        """
        self._ensure_initialized()
        
        # Process parameters
        params = params or {}
        
        # Format the request
        anthropic_params = format_anthropic_request(prompt, self.model_id, params)
        
        # Call API with retry
        try:
            response = with_retry(
                lambda: self.client.messages.create(**anthropic_params),
                max_attempts=self.config.get("retry_attempts", 3),
                backoff_factor=self.config.get("backoff_factor", 1.5)
            )
            
            # Check for content filtering
            if check_for_content_filter(response):
                raise APIContentFilterError("Response was filtered by Anthropic's content policy")
            
            # Parse response
            return parse_anthropic_response(response)
        except APIContentFilterError:
            raise  # Re-raise content filter errors
        except (APITimeoutError, APIRateLimitError):
            raise  # Re-raise specific API errors
        except Exception as e:
            if isinstance(e, APIRequestError):
                raise
            else:
                raise APIRequestError(f"Anthropic API request failed: {str(e)}")
    
    def generate_stream(self, prompt: PromptType, params: ParamsType = None) -> Iterator[str]:
        """Generate a streaming response from Claude.
        
        Args:
            prompt: Prompt data (string or message list)
            params: Optional generation parameters
            
        Returns:
            Iterator for streaming response
            
        Raises:
            APIRequestError: If the request fails
            APIContentFilterError: If content is filtered
        """
        self._ensure_initialized()
        
        # Process parameters
        params = params or {}
        stream_params = params.copy()
        stream_params["stream"] = True
        
        # Format the request
        anthropic_params = format_anthropic_request(prompt, self.model_id, stream_params)
        
        try:
            # Call streaming API
            stream = self.client.messages.create(**anthropic_params)
            
            # Process stream
            for chunk in stream:
                # Check for content filtering
                if check_for_content_filter(chunk):
                    raise APIContentFilterError("Response was filtered by Anthropic's content policy")
                
                # Extract text from the chunk
                if hasattr(chunk, "delta") and chunk.delta and hasattr(chunk.delta, "text"):
                    # Modern Messages API (with delta)
                    if chunk.delta.text:
                        yield chunk.delta.text
                elif hasattr(chunk, "delta") and isinstance(chunk.delta, dict) and "text" in chunk.delta:
                    # Dictionary format delta
                    if chunk.delta["text"]:
                        yield chunk.delta["text"]
                elif hasattr(chunk, "completion"):
                    # Legacy Completion API
                    yield chunk.completion
                elif isinstance(chunk, dict):
                    # Dictionary response
                    if "delta" in chunk and "text" in chunk["delta"]:
                        yield chunk["delta"]["text"]
                    elif "completion" in chunk:
                        yield chunk["completion"]
        except APIContentFilterError:
            raise  # Re-raise content filter errors
        except (APITimeoutError, APIRateLimitError):
            raise  # Re-raise specific API errors
        except Exception as e:
            if isinstance(e, APIRequestError):
                raise
            else:
                raise APIRequestError(f"Anthropic API streaming request failed: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using Anthropic's tokenizer.
        
        Args:
            text: Text to count tokens in
            
        Returns:
            Token count
        """
        self._ensure_initialized()
        
        # Use either the real client's count_tokens or our helper function
        try:
            if hasattr(self.client, "count_tokens"):
                return self.client.count_tokens(text)
            else:
                return count_tokens_anthropic(text)
        except Exception as e:
            logger.warning(f"Token counting failed: {str(e)}")
            # Fall back to a simple character-based estimate
            return max(1, len(text) // 4)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        self._ensure_initialized()
        
        # In a real implementation with API support, we would query the API for model info
        # For now, we'll return hardcoded information
        model_capabilities = {
            "claude-3-opus-20240229": {
                "context_window": 200000,
                "description": "Anthropic's most powerful model",
                "capabilities": ["vision", "function_calling"],
                "max_output_tokens": 4096
            },
            "claude-3-sonnet-20240229": {
                "context_window": 200000,
                "description": "Balanced performance and speed",
                "capabilities": ["vision", "function_calling"],
                "max_output_tokens": 4096
            },
            "claude-3-haiku-20240307": {
                "context_window": 200000,
                "description": "Fast and efficient responses",
                "capabilities": ["vision", "function_calling"],
                "max_output_tokens": 4096
            },
            "claude-2.1": {
                "context_window": 100000,
                "description": "Previous generation model",
                "capabilities": ["function_calling"],
                "max_output_tokens": 4096
            },
            "claude-2.0": {
                "context_window": 100000,
                "description": "Previous generation model",
                "capabilities": [],
                "max_output_tokens": 4096
            },
            "claude-instant-1.2": {
                "context_window": 100000,
                "description": "Fast and efficient legacy model",
                "capabilities": [],
                "max_output_tokens": 4096
            }
        }
        
        # Get capabilities for the current model, or use defaults
        capabilities = model_capabilities.get(self.model_id, {
            "context_window": 100000,
            "description": "Claude model",
            "capabilities": [],
            "max_output_tokens": 4096
        })
        
        return {
            "provider": "anthropic",
            "model_id": self.model_id,
            "description": capabilities["description"],
            "capabilities": {
                "streaming": True,
                "vision": "vision" in capabilities["capabilities"],
                "function_calling": "function_calling" in capabilities["capabilities"]
            },
            "context_window": capabilities["context_window"],
            "max_output_tokens": capabilities["max_output_tokens"]
        }
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """List available Claude models.
        
        Returns:
            List of available models
        """
        self._ensure_initialized()
        
        # In a real implementation with API support, we would query the API for available models
        # For now, we'll return hardcoded information
        return [
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "context_window": 200000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "context_window": 200000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "context_window": 200000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "claude-2.1",
                "name": "Claude 2.1",
                "context_window": 100000,
                "capabilities": ["function_calling"]
            },
            {
                "id": "claude-2.0",
                "name": "Claude 2.0",
                "context_window": 100000,
                "capabilities": []
            },
            {
                "id": "claude-instant-1.2",
                "name": "Claude Instant 1.2",
                "context_window": 100000,
                "capabilities": []
            }
        ]
    
    def shutdown(self) -> None:
        """Release resources."""
        self.client = None
        self.initialized = False
        logger.debug("Shut down Anthropic client")