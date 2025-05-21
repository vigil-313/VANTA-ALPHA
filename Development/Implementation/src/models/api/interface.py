#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Model Interface for VANTA.

This module defines the interface for API-based language models.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Processing
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, Union

PromptType = Union[str, List[Dict[str, str]]]
ParamsType = Optional[Dict[str, Any]]


class APIModelInterface(ABC):
    """Base interface for API model operations.
    
    This interface defines the common operations that all API model
    implementations must support.
    """
    
    @abstractmethod
    def initialize(self, config: ParamsType = None) -> None:
        """Initialize the API model with configuration.
        
        Args:
            config: Optional configuration dictionary with settings
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: PromptType, params: ParamsType = None) -> str:
        """Generate a response from the API model.
        
        Args:
            prompt: Input prompt (string or message list)
            params: Optional generation parameters
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def generate_stream(self, prompt: PromptType, params: ParamsType = None) -> Iterator[str]:
        """Generate a streaming response from the API model.
        
        Args:
            prompt: Input prompt (string or message list)
            params: Optional generation parameters
            
        Returns:
            Iterator yielding response chunks as they arrive
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in the input text.
        
        Args:
            text: Input text to count tokens for
            
        Returns:
            Number of tokens in the text
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the client and release any resources."""
        pass