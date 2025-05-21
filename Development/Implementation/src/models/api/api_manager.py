#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Model Manager for VANTA.

This module provides a central manager for API model clients.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Processing
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import logging
from typing import Any, Dict, Iterator, List, Optional, Type, Union

from .interface import APIModelInterface, PromptType, ParamsType
from .config import load_config
from .exceptions import APIModelError, APIInitializationError, APIConfigurationError
from .streaming.stream_handler import StreamHandler
from .streaming.stream_manager import StreamManager

logger = logging.getLogger(__name__)


class APIModelManager:
    """Manages API model selection and configuration.
    
    This class serves as a central point for managing different API model
    clients and their configurations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the API model manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or load_config()
        self.providers = {}  # Maps provider names to provider classes
        self.active_clients = {}  # Maps client keys to active client instances
        self._register_default_providers()
    
    def _register_default_providers(self) -> None:
        """Register default API providers."""
        try:
            # Import here to avoid circular imports
            from .anthropic_client import AnthropicClient
            self.providers["anthropic"] = AnthropicClient
        except ImportError:
            logger.warning("Anthropic client not available")
        
        try:
            # Import here to avoid circular imports
            from .openai_client import OpenAIClient
            self.providers["openai"] = OpenAIClient
        except ImportError:
            logger.warning("OpenAI client not available")
    
    def register_provider(self, name: str, provider_class: Type[APIModelInterface]) -> None:
        """Register a new API provider.
        
        Args:
            name: Provider name
            provider_class: Provider implementation class
        """
        if not issubclass(provider_class, APIModelInterface):
            raise APIConfigurationError(
                f"Provider class must implement APIModelInterface: {provider_class}"
            )
        
        self.providers[name] = provider_class
        logger.info(f"Registered provider: {name}")
    
    def list_available_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all available API models.
        
        Returns:
            Dictionary of available models by provider
        """
        available_models = {}
        
        for provider_name, provider_class in self.providers.items():
            try:
                # Create a temporary client
                client = provider_class()
                client.initialize()
                
                # Get models
                models = client.list_available_models() if hasattr(client, "list_available_models") else []
                available_models[provider_name] = models
                
                # Clean up
                client.shutdown()
            except Exception as e:
                logger.warning(f"Failed to list models for provider {provider_name}: {str(e)}")
                available_models[provider_name] = []
        
        return available_models
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific model.
        
        Args:
            model_id: Model identifier, can include provider prefix
                    (e.g., "anthropic:claude-3-opus-20240229")
                    
        Returns:
            Dictionary with model information
            
        Raises:
            APIConfigurationError: If the provider is unknown
        """
        # Parse provider and model ID
        if ":" in model_id:
            provider_name, model_name = model_id.split(":", 1)
        else:
            # Assume default provider
            provider_name = self.config["default_provider"]
            model_name = model_id
        
        # Check if provider exists
        if provider_name not in self.providers:
            raise APIConfigurationError(f"Unknown provider: {provider_name}")
        
        # Create client if necessary
        client = self._get_or_create_client(provider_name, model_name)
        
        # Get model info
        return client.get_model_info()
    
    def get_provider(self, provider_name: str) -> Type[APIModelInterface]:
        """Get a provider class by name.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider class
            
        Raises:
            APIConfigurationError: If the provider is unknown
        """
        if provider_name not in self.providers:
            raise APIConfigurationError(f"Unknown provider: {provider_name}")
        
        return self.providers[provider_name]
    
    def create_client(self, provider_name: str, model_id: Optional[str] = None) -> APIModelInterface:
        """Create a new API client.
        
        Args:
            provider_name: Name of the provider
            model_id: Optional model ID
            
        Returns:
            API client instance
            
        Raises:
            APIConfigurationError: If the provider is unknown
            APIInitializationError: If the client fails to initialize
        """
        if provider_name not in self.providers:
            raise APIConfigurationError(f"Unknown provider: {provider_name}")
        
        provider_class = self.providers[provider_name]
        
        # Use default model if not specified
        if model_id is None:
            model_id = self.config["default_models"].get(provider_name)
        
        # Create and initialize client
        try:
            client = provider_class()
            client_config = {
                "model_id": model_id,
                "timeout": self.config.get("timeout", 30),
                "retry_attempts": self.config.get("retry_attempts", 3),
                "backoff_factor": self.config.get("backoff_factor", 1.5)
            }
            client.initialize(client_config)
            return client
        except Exception as e:
            raise APIInitializationError(f"Failed to initialize {provider_name} client: {str(e)}")
    
    def _get_or_create_client(
        self, provider_name: str, model_id: Optional[str] = None
    ) -> APIModelInterface:
        """Get existing client or create a new one.
        
        Args:
            provider_name: Name of the provider
            model_id: Optional model ID
            
        Returns:
            API client instance
        """
        # Generate a unique key for this provider+model combination
        client_key = f"{provider_name}:{model_id or 'default'}"
        
        # Return existing client if available
        if client_key in self.active_clients:
            return self.active_clients[client_key]
        
        # Create new client
        client = self.create_client(provider_name, model_id)
        self.active_clients[client_key] = client
        
        return client
    
    def generate(
        self, prompt: PromptType, model_id: Optional[str] = None, params: ParamsType = None
    ) -> str:
        """Generate a response from the specified API model.
        
        Args:
            prompt: Prompt data (string or message list)
            model_id: Optional model ID with provider prefix
                    (e.g., "anthropic:claude-3-opus-20240229")
            params: Optional generation parameters
            
        Returns:
            Generated response
            
        Raises:
            APIModelError: If generation fails
        """
        # Parse provider and model
        provider_name = self.config["default_provider"]
        model_name = None
        
        if model_id:
            if ":" in model_id:
                provider_name, model_name = model_id.split(":", 1)
            else:
                model_name = model_id
        
        # Get or create client
        client = self._get_or_create_client(provider_name, model_name)
        
        try:
            # Generate response
            return client.generate(prompt, params)
        except Exception as e:
            if isinstance(e, APIModelError):
                raise
            else:
                raise APIModelError(f"API generation failed: {str(e)}")
    
    def generate_stream(
        self, prompt: PromptType, model_id: Optional[str] = None, params: ParamsType = None
    ) -> Iterator[str]:
        """Generate a streaming response from the specified API model.
        
        Args:
            prompt: Prompt data (string or message list)
            model_id: Optional model ID with provider prefix
            params: Optional generation parameters
            
        Returns:
            Iterator yielding response chunks as they arrive
            
        Raises:
            APIModelError: If generation fails
        """
        # Parse provider and model
        provider_name = self.config["default_provider"]
        model_name = None
        
        if model_id:
            if ":" in model_id:
                provider_name, model_name = model_id.split(":", 1)
            else:
                model_name = model_id
        
        # Get or create client
        client = self._get_or_create_client(provider_name, model_name)
        
        try:
            # Generate streaming response
            for chunk in client.generate_stream(prompt, params):
                yield chunk
        except Exception as e:
            if isinstance(e, APIModelError):
                raise
            else:
                raise APIModelError(f"API streaming generation failed: {str(e)}")
    
    def count_tokens(self, text: str, model_id: Optional[str] = None) -> int:
        """Count tokens in the input text.
        
        Args:
            text: Input text to count tokens for
            model_id: Optional model ID with provider prefix
            
        Returns:
            Number of tokens in the text
        """
        # Parse provider and model
        provider_name = self.config["default_provider"]
        model_name = None
        
        if model_id:
            if ":" in model_id:
                provider_name, model_name = model_id.split(":", 1)
            else:
                model_name = model_id
        
        # Get or create client
        client = self._get_or_create_client(provider_name, model_name)
        
        # Count tokens
        return client.count_tokens(text)
    
    def generate_stream_with_handlers(
        self, prompt: PromptType, model_id: Optional[str] = None, 
        params: ParamsType = None, handlers: Optional[List[StreamHandler]] = None,
        stream_config: Optional[Dict[str, Any]] = None
    ) -> StreamManager:
        """Generate a streaming response with handlers.
        
        Args:
            prompt: Prompt data (string or message list)
            model_id: Optional model ID with provider prefix
            params: Optional generation parameters
            handlers: Optional list of stream handlers
            stream_config: Optional streaming configuration
            
        Returns:
            StreamManager instance managing the stream
            
        Raises:
            APIModelError: If generation fails
        """
        # Create stream manager with configuration
        stream_manager = StreamManager(stream_config)
        
        # Register handlers
        if handlers:
            for handler in handlers:
                stream_manager.register_handler(handler)
        
        # Parse provider and model
        provider_name = self.config["default_provider"]
        model_name = None
        
        if model_id:
            if ":" in model_id:
                provider_name, model_name = model_id.split(":", 1)
            else:
                model_name = model_id
        
        # Get or create client
        client = self._get_or_create_client(provider_name, model_name)
        
        try:
            # Ensure stream parameter is set
            if params is None:
                params = {}
            
            if "stream" not in params:
                params["stream"] = True
            
            # Get stream
            stream = client.generate_stream(prompt, params)
            
            # Start stream processing
            metadata = {
                "provider": provider_name,
                "model": model_name or client.model_id,
                "prompt": prompt,
                "request_id": model_id or f"{provider_name}:{model_name or client.model_id}"
            }
            stream_manager.start_stream(stream, metadata)
            
            return stream_manager
        except Exception as e:
            if isinstance(e, APIModelError):
                raise
            else:
                raise APIModelError(f"API streaming generation failed: {str(e)}")
    
    def shutdown(self) -> None:
        """Shutdown all active clients and release resources."""
        for client_key, client in list(self.active_clients.items()):
            try:
                client.shutdown()
                del self.active_clients[client_key]
                logger.debug(f"Shut down client: {client_key}")
            except Exception as e:
                logger.error(f"Error shutting down client {client_key}: {str(e)}")
        
        # Clear active clients
        self.active_clients = {}