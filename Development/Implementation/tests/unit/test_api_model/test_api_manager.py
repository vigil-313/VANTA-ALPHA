#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the API Model Manager.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import os
import unittest
from unittest import mock

import pytest

from src.models.api.api_manager import APIModelManager
from src.models.api.interface import APIModelInterface
from src.models.api.exceptions import APIConfigurationError, APIInitializationError


class MockClient(APIModelInterface):
    """Mock API client for testing."""
    
    def __init__(self):
        self.initialized = False
        self.config = None
    
    def initialize(self, config=None):
        self.initialized = True
        self.config = config or {}
    
    def generate(self, prompt, params=None):
        return "Mock response"
    
    def generate_stream(self, prompt, params=None):
        yield "Mock"
        yield " "
        yield "response"
    
    def count_tokens(self, text):
        return len(text.split())
    
    def get_model_info(self):
        return {
            "provider": "mock",
            "model_id": self.config.get("model_id", "mock-model"),
            "capabilities": {
                "streaming": True,
                "vision": False,
                "function_calling": True
            },
            "context_window": 10000,
            "max_output_tokens": 1000
        }
    
    def list_available_models(self):
        return [
            {
                "id": "mock-model-1",
                "name": "Mock Model 1",
                "context_window": 10000,
                "capabilities": []
            },
            {
                "id": "mock-model-2",
                "name": "Mock Model 2",
                "context_window": 20000,
                "capabilities": ["function_calling"]
            }
        ]
    
    def shutdown(self):
        self.initialized = False


class TestAPIModelManager:
    """Test the API Model Manager."""
    
    def setup_method(self):
        """Set up test environment."""
        # Patch the credential functions
        self.credentials_patch = mock.patch(
            "src.models.api.api_manager.get_credential",
            return_value="mock-api-key"
        )
        self.credentials_patch.start()
        
        # Create a test configuration
        self.test_config = {
            "default_provider": "mock",
            "default_models": {
                "mock": "mock-model-1"
            },
            "timeout": 10,
            "retry_attempts": 2,
            "backoff_factor": 1.0
        }
        
        # Create a manager with the test configuration
        self.manager = APIModelManager(self.test_config)
        
        # Register the mock provider
        self.manager.register_provider("mock", MockClient)
    
    def teardown_method(self):
        """Clean up after tests."""
        self.credentials_patch.stop()
        self.manager.shutdown()
    
    def test_register_provider(self):
        """Test registering a provider."""
        # Check that the mock provider was registered
        assert "mock" in self.manager.providers
        assert self.manager.providers["mock"] == MockClient
        
        # Try registering an invalid provider
        with pytest.raises(APIConfigurationError):
            self.manager.register_provider("invalid", str)
    
    def test_create_client(self):
        """Test creating a client."""
        # Create a client
        client = self.manager.create_client("mock", "mock-model-1")
        
        # Check that the client was created correctly
        assert client.initialized
        assert client.config["model_id"] == "mock-model-1"
        assert client.config["timeout"] == 10
        assert client.config["retry_attempts"] == 2
        assert client.config["backoff_factor"] == 1.0
        
        # Try creating a client with an unknown provider
        with pytest.raises(APIConfigurationError):
            self.manager.create_client("unknown")
    
    def test_get_model_info(self):
        """Test getting model information."""
        # Get model info
        info = self.manager.get_model_info("mock:mock-model-1")
        
        # Check the model info
        assert info["provider"] == "mock"
        assert info["model_id"] == "mock-model-1"
        assert "capabilities" in info
        assert "context_window" in info
        
        # Test with default provider
        info = self.manager.get_model_info("mock-model-2")
        assert info["model_id"] == "mock-model-2"
        
        # Try getting info for an unknown provider
        with pytest.raises(APIConfigurationError):
            self.manager.get_model_info("unknown:model")
    
    def test_generate(self):
        """Test generating a response."""
        # Generate a response
        response = self.manager.generate("Test prompt", "mock:mock-model-1")
        
        # Check the response
        assert response == "Mock response"
        
        # Test with default provider
        response = self.manager.generate("Test prompt")
        assert response == "Mock response"
    
    def test_generate_stream(self):
        """Test generating a streaming response."""
        # Generate a streaming response
        stream = self.manager.generate_stream("Test prompt", "mock:mock-model-1")
        
        # Check the response
        chunks = list(stream)
        assert chunks == ["Mock", " ", "response"]
        
        # Test with default provider
        stream = self.manager.generate_stream("Test prompt")
        chunks = list(stream)
        assert chunks == ["Mock", " ", "response"]
    
    def test_count_tokens(self):
        """Test counting tokens."""
        # Count tokens
        count = self.manager.count_tokens("This is a test", "mock:mock-model-1")
        
        # Check the count
        assert count == 4  # "This is a test" has 4 tokens in the mock implementation
    
    def test_client_caching(self):
        """Test that clients are cached."""
        # Create a client
        client1 = self.manager._get_or_create_client("mock", "mock-model-1")
        
        # Get the same client again
        client2 = self.manager._get_or_create_client("mock", "mock-model-1")
        
        # Check that the clients are the same object
        assert client1 is client2
        
        # Create a different client
        client3 = self.manager._get_or_create_client("mock", "mock-model-2")
        
        # Check that the clients are different objects
        assert client1 is not client3
    
    def test_shutdown(self):
        """Test shutting down the manager."""
        # Create a client
        client = self.manager._get_or_create_client("mock", "mock-model-1")
        
        # Shut down the manager
        self.manager.shutdown()
        
        # Check that the client was shut down
        assert not client.initialized
        assert len(self.manager.active_clients) == 0