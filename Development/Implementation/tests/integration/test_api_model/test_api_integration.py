#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the API Model Client.

These tests use mock API responses to simulate API interactions.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import os
import json
import pytest
from unittest import mock

from src.models.api.api_manager import APIModelManager
from src.models.api.anthropic_client import AnthropicClient
from src.models.api.openai_client import OpenAIClient


@pytest.fixture
def api_manager():
    """Create an API model manager with mock providers."""
    # Patch credential functions
    with mock.patch(
        "src.models.api.anthropic_client.get_credential",
        return_value="mock-api-key"
    ), mock.patch(
        "src.models.api.openai_client.get_credential",
        return_value="mock-api-key"
    ):
        # Create a manager
        manager = APIModelManager({
            "default_provider": "anthropic",
            "default_models": {
                "anthropic": "claude-3-opus-20240229",
                "openai": "gpt-4o"
            }
        })
        
        # Force clients to use mocks
        manager.shutdown()  # Clear any existing clients
        
        # Register providers with forced mock settings
        class MockedAnthropicClient(AnthropicClient):
            def __init__(self):
                super().__init__()
                self._anthropic_available = False
        
        class MockedOpenAIClient(OpenAIClient):
            def __init__(self):
                super().__init__()
                self._openai_available = False
                self._tiktoken_available = False
        
        manager.register_provider("anthropic", MockedAnthropicClient)
        manager.register_provider("openai", MockedOpenAIClient)
        
        yield manager
        
        # Clean up
        manager.shutdown()


class TestAPIIntegration:
    """Integration tests for the API client components."""
    
    def test_dual_provider_setup(self, api_manager):
        """Test using multiple providers in the same session."""
        # Get info about both providers
        anthropic_info = api_manager.get_model_info("anthropic:claude-3-opus-20240229")
        openai_info = api_manager.get_model_info("openai:gpt-4o")
        
        # Check that info was retrieved correctly
        assert anthropic_info["provider"] == "anthropic"
        assert openai_info["provider"] == "openai"
    
    def test_manager_client_isolation(self, api_manager):
        """Test that clients remain isolated in the manager."""
        # Generate responses with both providers
        anthropic_response = api_manager.generate("Test prompt", "anthropic:claude-3-opus-20240229")
        openai_response = api_manager.generate("Test prompt", "openai:gpt-4o")
        
        # Should get responses from both
        assert anthropic_response is not None
        assert openai_response is not None
        
        # Check active clients
        assert len(api_manager.active_clients) == 2
        assert "anthropic:claude-3-opus-20240229" in api_manager.active_clients
        assert "openai:gpt-4o" in api_manager.active_clients
    
    def test_streaming_with_different_providers(self, api_manager):
        """Test streaming from different providers."""
        # Generate streaming responses from both providers
        anthropic_chunks = list(api_manager.generate_stream("Test prompt", "anthropic:claude-3-opus-20240229"))
        openai_chunks = list(api_manager.generate_stream("Test prompt", "openai:gpt-4o"))
        
        # Should get responses from both
        assert len(anthropic_chunks) > 0
        assert len(openai_chunks) > 0
    
    def test_default_provider_selection(self, api_manager):
        """Test the default provider selection."""
        # Generate with default provider
        default_response = api_manager.generate("Test prompt")
        
        # Generate with explicit provider
        anthropic_response = api_manager.generate("Test prompt", "anthropic:claude-3-opus-20240229")
        
        # Both should generate responses
        assert default_response is not None
        assert anthropic_response is not None
        
        # Check that only one client was created for both calls
        anthropic_client_key = "anthropic:claude-3-opus-20240229"
        assert anthropic_client_key in api_manager.active_clients
        
        # Check active clients
        anthropic_client_count = sum(
            1 for key in api_manager.active_clients.keys() if key.startswith("anthropic:")
        )
        assert anthropic_client_count == 1, "Should reuse the same client for default provider"
    
    def test_complex_messages(self, api_manager):
        """Test handling complex message formats."""
        # Create a complex messages format
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "Hello, who are you?"},
            {"role": "assistant", "content": "I'm an AI assistant."},
            {"role": "user", "content": "Can you help me?"}
        ]
        
        # Generate with both providers
        anthropic_response = api_manager.generate(messages, "anthropic:claude-3-opus-20240229")
        openai_response = api_manager.generate(messages, "openai:gpt-4o")
        
        # Both should generate responses
        assert anthropic_response is not None
        assert openai_response is not None