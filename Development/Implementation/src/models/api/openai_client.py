#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI GPT API Client for VANTA.

This module provides integration with the OpenAI GPT-4 and other models.
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
from .token_counter import count_tokens_openai
from .request_builder import format_openai_request
from .response_parser import parse_openai_response, check_for_content_filter
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


class MockOpenAIClient:
    """Mock implementation for the OpenAI client when SDK is not available."""
    
    def __init__(self, api_key: str):
        """Initialize the mock client.
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.chat = MockOpenAIChatCompletions()


class MockOpenAIChatCompletions:
    """Mock implementation for OpenAI chat completions API."""
    
    def create(self, **kwargs) -> Dict[str, Any]:
        """Mock chat completion creation.
        
        Args:
            **kwargs: API parameters
            
        Returns:
            Mock response
        """
        # Check if streaming
        if kwargs.get("stream", False):
            # Return a generator for streaming
            return self._stream_mock_response(kwargs)
        
        # Create a minimal mock response
        return {
            "id": "chatcmpl_mock12345",
            "object": "chat.completion",
            "created": 1683130000,
            "model": kwargs.get("model", "gpt-4"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a mock response from OpenAI GPT."
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120
            }
        }
    
    def _stream_mock_response(self, kwargs: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Generate a streaming mock response.
        
        Args:
            kwargs: API parameters
            
        Returns:
            Iterator of response chunks
        """
        # Split the mock response into chunks
        response_parts = ["This ", "is ", "a ", "mock ", "response ", "from ", "OpenAI ", "GPT."]
        
        for i, part in enumerate(response_parts):
            yield {
                "id": f"chatcmpl_mock12345_{i}",
                "object": "chat.completion.chunk",
                "created": 1683130000 + i,
                "model": kwargs.get("model", "gpt-4"),
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": part
                    },
                    "finish_reason": None if i < len(response_parts) - 1 else "stop"
                }]
            }


class OpenAIClient(APIModelInterface):
    """Client for OpenAI GPT API."""
    
    def __init__(self):
        """Initialize OpenAI GPT client."""
        self.config = None
        self.api_key = None
        self.model_id = None
        self.client = None
        self.initialized = False
        self._openai_available = self._check_openai_available()
        self._tiktoken_available = self._check_tiktoken_available()
    
    def _check_openai_available(self) -> bool:
        """Check if the OpenAI Python SDK is available.
        
        Returns:
            True if available, False otherwise
        """
        return importlib.util.find_spec("openai") is not None
    
    def _check_tiktoken_available(self) -> bool:
        """Check if the tiktoken package is available.
        
        Returns:
            True if available, False otherwise
        """
        return importlib.util.find_spec("tiktoken") is not None
    
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
            self.api_key = get_credential("openai", self.config)
            
            # Set model ID
            self.model_id = self.config.get("model_id", "gpt-4o")
            
            # Set up client
            self.client = self._setup_client()
            
            self.initialized = True
            logger.info(f"Initialized OpenAI client with model: {self.model_id}")
        except APICredentialError as e:
            raise APIInitializationError(f"OpenAI API key not found: {str(e)}")
        except Exception as e:
            raise APIInitializationError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def _setup_client(self) -> Any:
        """Set up the OpenAI API client.
        
        Returns:
            OpenAI API client
            
        Raises:
            APIInitializationError: If client setup fails
        """
        # Import the OpenAI SDK if available
        if self._openai_available:
            try:
                import openai
                return openai.OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to create OpenAI client with SDK: {str(e)}")
                logger.warning("Falling back to mock implementation")
        else:
            logger.warning("OpenAI SDK not available, using mock implementation")
        
        # Fall back to mock implementation
        return MockOpenAIClient(self.api_key)
    
    def _ensure_initialized(self) -> None:
        """Ensure client is initialized before use.
        
        Raises:
            APIInitializationError: If client is not initialized
        """
        if not self.initialized:
            raise APIInitializationError("OpenAI client not initialized. Call initialize() first.")
    
    def generate(self, prompt: PromptType, params: ParamsType = None) -> str:
        """Generate a response from GPT.
        
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
        openai_params = format_openai_request(prompt, self.model_id, params)
        
        # Call API with retry
        try:
            response = with_retry(
                lambda: self.client.chat.completions.create(**openai_params),
                max_attempts=self.config.get("retry_attempts", 3),
                backoff_factor=self.config.get("backoff_factor", 1.5)
            )
            
            # Check for content filtering
            if check_for_content_filter(response):
                raise APIContentFilterError("Response was filtered by OpenAI's content policy")
            
            # Parse response
            return parse_openai_response(response)
        except APIContentFilterError:
            raise  # Re-raise content filter errors
        except (APITimeoutError, APIRateLimitError):
            raise  # Re-raise specific API errors
        except Exception as e:
            if isinstance(e, APIRequestError):
                raise
            else:
                raise APIRequestError(f"OpenAI API request failed: {str(e)}")
    
    def generate_stream(self, prompt: PromptType, params: ParamsType = None) -> Iterator[str]:
        """Generate a streaming response from GPT.
        
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
        openai_params = format_openai_request(prompt, self.model_id, stream_params)
        
        try:
            # Call streaming API
            stream = self.client.chat.completions.create(**openai_params)
            
            # Process stream
            for chunk in stream:
                # Check for content filtering
                if check_for_content_filter(chunk):
                    raise APIContentFilterError("Response was filtered by OpenAI's content policy")
                
                # Extract text from the chunk
                if hasattr(chunk, "choices") and chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    
                    if hasattr(choice, "delta") and hasattr(choice.delta, "content") and choice.delta.content:
                        yield choice.delta.content
                    elif hasattr(choice, "delta") and isinstance(choice.delta, dict) and "content" in choice.delta and choice.delta["content"]:
                        yield choice.delta["content"]
                elif isinstance(chunk, dict) and "choices" in chunk and chunk["choices"]:
                    if "delta" in chunk["choices"][0] and "content" in chunk["choices"][0]["delta"] and chunk["choices"][0]["delta"]["content"]:
                        yield chunk["choices"][0]["delta"]["content"]
        except APIContentFilterError:
            raise  # Re-raise content filter errors
        except (APITimeoutError, APIRateLimitError):
            raise  # Re-raise specific API errors
        except Exception as e:
            if isinstance(e, APIRequestError):
                raise
            else:
                raise APIRequestError(f"OpenAI API streaming request failed: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken if available.
        
        Args:
            text: Text to count tokens in
            
        Returns:
            Token count
        """
        self._ensure_initialized()
        
        return count_tokens_openai(text, self.model_id)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        self._ensure_initialized()
        
        # In a real implementation with API support, we would query the API for model info
        # For now, we'll return hardcoded information
        model_capabilities = {
            "gpt-4o": {
                "context_window": 128000,
                "description": "GPT-4o (Omni) - OpenAI's most capable multimodal model",
                "capabilities": ["vision", "function_calling"],
                "max_output_tokens": 4096
            },
            "gpt-4-turbo": {
                "context_window": 128000,
                "description": "GPT-4 Turbo with extended context window",
                "capabilities": ["vision", "function_calling"],
                "max_output_tokens": 4096
            },
            "gpt-4": {
                "context_window": 8192,
                "description": "Original GPT-4 model",
                "capabilities": ["function_calling"],
                "max_output_tokens": 4096
            },
            "gpt-4-vision-preview": {
                "context_window": 128000,
                "description": "GPT-4 with vision capabilities",
                "capabilities": ["vision", "function_calling"],
                "max_output_tokens": 4096
            },
            "gpt-3.5-turbo": {
                "context_window": 16385,
                "description": "GPT-3.5 Turbo model",
                "capabilities": ["function_calling"],
                "max_output_tokens": 4096
            }
        }
        
        # Get capabilities for the current model, or use defaults
        capabilities = model_capabilities.get(self.model_id, {
            "context_window": 8192,
            "description": "OpenAI GPT model",
            "capabilities": ["function_calling"],
            "max_output_tokens": 4096
        })
        
        # For models with specific context sizes in their names
        if "16k" in self.model_id:
            capabilities["context_window"] = 16385
        elif "32k" in self.model_id:
            capabilities["context_window"] = 32768
        elif "128k" in self.model_id:
            capabilities["context_window"] = 128000
        
        return {
            "provider": "openai",
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
        """List available GPT models.
        
        Returns:
            List of available models
        """
        self._ensure_initialized()
        
        # In a real implementation with API support, we would query the API for available models
        # For now, we'll return hardcoded information
        return [
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "context_window": 128000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "context_window": 128000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "context_window": 8192,
                "capabilities": ["function_calling"]
            },
            {
                "id": "gpt-4-vision-preview",
                "name": "GPT-4 Vision",
                "context_window": 128000,
                "capabilities": ["vision", "function_calling"]
            },
            {
                "id": "gpt-3.5-turbo-0125",
                "name": "GPT-3.5 Turbo",
                "context_window": 16385,
                "capabilities": ["function_calling"]
            }
        ]
    
    def shutdown(self) -> None:
        """Release resources."""
        self.client = None
        self.initialized = False
        logger.debug("Shut down OpenAI client")