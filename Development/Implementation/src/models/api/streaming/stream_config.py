#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration for streaming response handling.

This module provides configuration parameters for streaming response handling.
"""
# TASK-REF: AM_002 - Streaming Response Handling
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-002 - Streaming Response Handling Implementation

import os
from typing import Any, Dict, Optional


class StreamConfig:
    """Configuration for streaming response handling."""
    
    # Default configuration
    DEFAULT_CONFIG = {
        # Buffer settings
        "buffer_size": 1,  # Token buffer size (1 = no buffering)
        "max_buffer_size": 1024,  # Maximum buffer size in tokens
        
        # Threading settings
        "use_threads": True,  # Whether to use threads for processing
        "thread_timeout": 60.0,  # Timeout for thread operations in seconds
        
        # Control settings
        "pause_timeout": 30.0,  # Maximum time to wait for a paused stream
        "cancel_graceful": True,  # Whether to wait for current tokens on cancel
        
        # Error handling
        "retry_on_error": True,  # Whether to retry on error
        "max_retries": 3,  # Maximum number of retries
        "retry_delay": 1.0,  # Delay between retries in seconds
        
        # Performance settings
        "batch_events": False,  # Whether to batch events for handlers
        "max_batch_size": 10,  # Maximum number of events to batch
        "log_performance": False,  # Whether to log performance metrics
        
        # Provider-specific settings
        "anthropic": {
            "chunk_size": 1,  # Size of chunks to request
        },
        "openai": {
            "chunk_size": 1,  # Size of chunks to request
        }
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize stream configuration.
        
        Args:
            config: Optional configuration dictionary to override defaults
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Override with environment variables
        self._load_from_environment()
        
        # Override with provided config
        if config:
            self._update_config(config)
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Buffer settings
        if "VANTA_STREAM_BUFFER_SIZE" in os.environ:
            try:
                self.config["buffer_size"] = int(os.environ["VANTA_STREAM_BUFFER_SIZE"])
            except ValueError:
                pass
        
        # Threading settings
        if "VANTA_STREAM_USE_THREADS" in os.environ:
            self.config["use_threads"] = os.environ["VANTA_STREAM_USE_THREADS"].lower() in ("true", "1", "yes")
        
        # Timeout settings
        if "VANTA_STREAM_THREAD_TIMEOUT" in os.environ:
            try:
                self.config["thread_timeout"] = float(os.environ["VANTA_STREAM_THREAD_TIMEOUT"])
            except ValueError:
                pass
    
    def _update_config(self, config: Dict[str, Any]) -> None:
        """Update configuration with provided values.
        
        Args:
            config: Configuration dictionary with values to update
        """
        # Update top-level config
        for key, value in config.items():
            if key in self.config:
                if isinstance(value, dict) and isinstance(self.config[key], dict):
                    # Merge nested dictionaries
                    self.config[key].update(value)
                else:
                    # Replace value
                    self.config[key] = value
            else:
                # Add new key
                self.config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get provider-specific configuration.
        
        Args:
            provider: Provider name
            
        Returns:
            Provider-specific configuration dictionary
        """
        return self.config.get(provider, {})
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    def update(self, config: Dict[str, Any]) -> None:
        """Update configuration with provided values.
        
        Args:
            config: Configuration dictionary with values to update
        """
        self._update_config(config)
    
    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as a dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()