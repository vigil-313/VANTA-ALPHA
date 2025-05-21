#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Anthropic Client.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import os
import unittest
from unittest import mock

import pytest

from src.models.api.anthropic_client import AnthropicClient, MockAnthropicClient
from src.models.api.exceptions import (
    APIInitializationError,
    APIRequestError,
    APIContentFilterError
)


class TestAnthropicClient:
    """Test the Anthropic Claude client."""
    
    def setup_method(self):
        """Set up test environment."""
        # Patch the credential functions
        self.credentials_patch = mock.patch(
            "src.models.api.anthropic_client.get_credential",
            return_value="mock-api-key"
        )
        self.credentials_patch.start()
        
        # Create a client
        self.client = AnthropicClient()
        
        # Force using the mock client
        self.client._anthropic_available = False
        
        # Initialize the client
        self.client.initialize({
            "model_id": "claude-3-opus-20240229",
            "timeout": 10,
            "retry_attempts": 2,
            "backoff_factor": 1.0
        })
    
    def teardown_method(self):
        """Clean up after tests."""
        self.credentials_patch.stop()
        self.client.shutdown()
    
    def test_initialization(self):
        """Test client initialization."""
        # Check that the client was initialized correctly
        assert self.client.initialized
        assert self.client.api_key == "mock-api-key"
        assert self.client.model_id == "claude-3-opus-20240229"
        assert isinstance(self.client.client, MockAnthropicClient)
        
        # Test with missing API key
        with mock.patch(
            "src.models.api.anthropic_client.get_credential",
            side_effect=Exception("No API key")
        ):
            client = AnthropicClient()
            with pytest.raises(APIInitializationError):
                client.initialize()
    
    def test_generate(self):
        """Test generating a response."""
        # Test with string prompt
        response = self.client.generate("Test prompt")
        assert "mock response" in response.lower()
        
        # Test with message list prompt
        messages = [
            {"role": "system", "content": "You are Claude."},
            {"role": "user", "content": "Hello"}
        ]
        response = self.client.generate(messages)
        assert "mock response" in response.lower()
    
    def test_generate_stream(self):
        """Test generating a streaming response."""
        # Set up mock streaming response
        mock_response = [
            {"delta": {"text": "This"}},
            {"delta": {"text": " is"}},
            {"delta": {"text": " a"}},
            {"delta": {"text": " mock"}},
            {"delta": {"text": " response"}}
        ]
        
        # Mock the client.messages.create method to return a generator
        self.client.client.messages.create = mock.MagicMock(return_value=mock_response)
        
        # Test with string prompt
        stream = self.client.generate_stream("Test prompt")
        chunks = list(stream)
        assert chunks == ["This", " is", " a", " mock", " response"]
        
        # Test with content filtering
        filtered_response = [
            {"delta": {"text": "This"}},
            {"stop_reason": "content_filtered"}
        ]
        self.client.client.messages.create = mock.MagicMock(return_value=filtered_response)
        
        with pytest.raises(APIContentFilterError):
            # This should raise an exception when content filtering is detected
            list(self.client.generate_stream("Test prompt"))
    
    def test_count_tokens(self):
        """Test token counting."""
        # Mock the client's count_tokens method
        self.client.client.count_tokens = mock.MagicMock(return_value=10)
        
        # Count tokens
        count = self.client.count_tokens("This is a test")
        
        # Check that the count matches the mock
        assert count == 10
        self.client.client.count_tokens.assert_called_once_with("This is a test")
        
        # Test fallback when count_tokens raises an exception
        self.client.client.count_tokens.side_effect = Exception("Error")
        count = self.client.count_tokens("This is a test")
        
        # Should use a character-based estimate
        assert count > 0
    
    def test_get_model_info(self):
        """Test getting model information."""
        # Get model info
        info = self.client.get_model_info()
        
        # Check the model info
        assert info["provider"] == "anthropic"
        assert info["model_id"] == "claude-3-opus-20240229"
        assert "capabilities" in info
        assert "context_window" in info
        assert "max_output_tokens" in info
        
        # Check capabilities specific to Claude 3 Opus
        assert info["capabilities"]["vision"] is True
        assert info["capabilities"]["function_calling"] is True
        
        # Test with a different model
        self.client.model_id = "claude-2.0"
        info = self.client.get_model_info()
        
        # Check the different capabilities
        assert info["capabilities"]["vision"] is False
    
    def test_list_available_models(self):
        """Test listing available models."""
        # List models
        models = self.client.list_available_models()
        
        # Check the list
        assert len(models) > 0
        assert all("id" in model for model in models)
        assert all("name" in model for model in models)
        assert all("context_window" in model for model in models)
        assert all("capabilities" in model for model in models)
        
        # Check that Claude 3 models are included
        model_ids = [model["id"] for model in models]
        assert "claude-3-opus-20240229" in model_ids
        assert "claude-3-sonnet-20240229" in model_ids
        assert "claude-3-haiku-20240307" in model_ids