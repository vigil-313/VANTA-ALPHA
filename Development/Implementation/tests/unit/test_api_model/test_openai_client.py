#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the OpenAI Client.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import os
import unittest
from unittest import mock

import pytest

from src.models.api.openai_client import OpenAIClient, MockOpenAIClient
from src.models.api.exceptions import (
    APIInitializationError,
    APIRequestError,
    APIContentFilterError
)


class TestOpenAIClient:
    """Test the OpenAI GPT client."""
    
    def setup_method(self):
        """Set up test environment."""
        # Patch the credential functions
        self.credentials_patch = mock.patch(
            "src.models.api.openai_client.get_credential",
            return_value="mock-api-key"
        )
        self.credentials_patch.start()
        
        # Create a client
        self.client = OpenAIClient()
        
        # Force using the mock client
        self.client._openai_available = False
        self.client._tiktoken_available = False
        
        # Initialize the client
        self.client.initialize({
            "model_id": "gpt-4o",
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
        assert self.client.model_id == "gpt-4o"
        assert isinstance(self.client.client, MockOpenAIClient)
        
        # Test with missing API key
        with mock.patch(
            "src.models.api.openai_client.get_credential",
            side_effect=Exception("No API key")
        ):
            client = OpenAIClient()
            with pytest.raises(APIInitializationError):
                client.initialize()
    
    def test_generate(self):
        """Test generating a response."""
        # Set up a mock response
        mock_response = mock.MagicMock()
        mock_response.choices = [mock.MagicMock()]
        mock_response.choices[0].message.content = "This is a mock response from GPT-4."
        
        # Override the mock client
        self.client.client.chat.completions.create = mock.MagicMock(return_value=mock_response)
        
        # Test with string prompt
        response = self.client.generate("Test prompt")
        assert response == "This is a mock response from GPT-4."
        
        # Test with message list prompt
        messages = [
            {"role": "system", "content": "You are GPT-4."},
            {"role": "user", "content": "Hello"}
        ]
        response = self.client.generate(messages)
        assert response == "This is a mock response from GPT-4."
        
        # Test with content filtering
        mock_response.choices[0].finish_reason = "content_filter"
        with pytest.raises(APIContentFilterError):
            self.client.generate("Test prompt")
    
    def test_generate_stream(self):
        """Test generating a streaming response."""
        # Set up mock streaming response
        mock_chunks = [
            mock.MagicMock(
                choices=[mock.MagicMock(delta=mock.MagicMock(content="This"))],
                model="gpt-4"
            ),
            mock.MagicMock(
                choices=[mock.MagicMock(delta=mock.MagicMock(content=" is"))],
                model="gpt-4"
            ),
            mock.MagicMock(
                choices=[mock.MagicMock(delta=mock.MagicMock(content=" a"))],
                model="gpt-4"
            ),
            mock.MagicMock(
                choices=[mock.MagicMock(delta=mock.MagicMock(content=" mock"))],
                model="gpt-4"
            ),
            mock.MagicMock(
                choices=[mock.MagicMock(delta=mock.MagicMock(content=" response"))],
                model="gpt-4"
            )
        ]
        
        # Mock the client.chat.completions.create method to return a generator
        self.client.client.chat.completions.create = mock.MagicMock(return_value=mock_chunks)
        
        # Test with string prompt
        stream = self.client.generate_stream("Test prompt")
        chunks = list(stream)
        assert chunks == ["This", " is", " a", " mock", " response"]
        
        # Test with content filtering
        mock_chunks[-1].choices[0].finish_reason = "content_filter"
        self.client.client.chat.completions.create = mock.MagicMock(return_value=mock_chunks)
        
        with pytest.raises(APIContentFilterError):
            # This should raise an exception when content filtering is detected
            list(self.client.generate_stream("Test prompt"))
    
    def test_count_tokens(self):
        """Test token counting."""
        # Count tokens without tiktoken (estimated)
        count = self.client.count_tokens("This is a test")
        
        # Should use a simple estimate
        assert count > 0
        
        # Test with tiktoken available
        with mock.patch("src.models.api.token_counter._has_tiktoken", return_value=True):
            with mock.patch("src.models.api.token_counter.count_tokens_openai", return_value=4):
                count = self.client.count_tokens("This is a test")
                assert count == 4
    
    def test_get_model_info(self):
        """Test getting model information."""
        # Get model info
        info = self.client.get_model_info()
        
        # Check the model info
        assert info["provider"] == "openai"
        assert info["model_id"] == "gpt-4o"
        assert "capabilities" in info
        assert "context_window" in info
        assert "max_output_tokens" in info
        
        # Check capabilities specific to GPT-4o
        assert info["capabilities"]["vision"] is True
        assert info["capabilities"]["function_calling"] is True
        
        # Test with a different model
        self.client.model_id = "gpt-3.5-turbo"
        info = self.client.get_model_info()
        
        # Check the different capabilities
        assert info["context_window"] == 16385
    
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
        
        # Check that new models are included
        model_ids = [model["id"] for model in models]
        assert "gpt-4o" in model_ids
        assert "gpt-4-turbo" in model_ids