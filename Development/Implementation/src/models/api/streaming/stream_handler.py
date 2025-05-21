#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stream Handler interfaces and implementations.

This module defines the interface for handling streaming responses and provides
common implementations.
"""
# TASK-REF: AM_002 - Streaming Response Handling
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-002 - Streaming Response Handling Implementation

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

from .exceptions import StreamHandlerError

logger = logging.getLogger(__name__)


class StreamHandler(ABC):
    """Interface for handling streaming responses."""
    
    @abstractmethod
    def on_stream_start(self, metadata: Dict[str, Any]) -> None:
        """Called when a stream starts.
        
        Args:
            metadata: Stream metadata (provider, model, etc.)
        """
        pass
    
    @abstractmethod
    def on_token_received(self, token: str, index: int) -> None:
        """Called when a token is received from the stream.
        
        Args:
            token: The token received
            index: The token index in the response
        """
        pass
    
    @abstractmethod
    def on_stream_complete(self, full_response: str) -> None:
        """Called when a stream completes.
        
        Args:
            full_response: The complete response text
        """
        pass
    
    @abstractmethod
    def on_stream_error(self, error: Exception) -> None:
        """Called when a stream encounters an error.
        
        Args:
            error: The error that occurred
        """
        pass


class BufferedStreamHandler(StreamHandler):
    """Stream handler that buffers the complete response."""
    
    def __init__(self):
        """Initialize buffered stream handler."""
        self.tokens: List[str] = []
        self.is_complete: bool = False
        self.error: Optional[Exception] = None
        self.metadata: Dict[str, Any] = {}
    
    def on_stream_start(self, metadata: Dict[str, Any]) -> None:
        """Called when a stream starts.
        
        Args:
            metadata: Stream metadata (provider, model, etc.)
        """
        self.tokens = []
        self.is_complete = False
        self.error = None
        self.metadata = metadata
    
    def on_token_received(self, token: str, index: int) -> None:
        """Called when a token is received from the stream.
        
        Args:
            token: The token received
            index: The token index in the response
        """
        self.tokens.append(token)
    
    def on_stream_complete(self, full_response: str) -> None:
        """Called when a stream completes.
        
        Args:
            full_response: The complete response text
        """
        self.is_complete = True
    
    def on_stream_error(self, error: Exception) -> None:
        """Called when a stream encounters an error.
        
        Args:
            error: The error that occurred
        """
        self.error = error
    
    def get_response(self) -> str:
        """Get the buffered response.
        
        Returns:
            The complete response text
        """
        return "".join(self.tokens)
    
    def reset(self) -> None:
        """Reset the handler state."""
        self.tokens = []
        self.is_complete = False
        self.error = None
        self.metadata = {}


class ConsoleStreamHandler(StreamHandler):
    """Stream handler that prints tokens to the console."""
    
    def __init__(self, prefix: str = "", show_metadata: bool = False):
        """Initialize console stream handler.
        
        Args:
            prefix: Optional prefix to add to output
            show_metadata: Whether to print metadata
        """
        self.prefix = prefix
        self.show_metadata = show_metadata
    
    def on_stream_start(self, metadata: Dict[str, Any]) -> None:
        """Called when a stream starts.
        
        Args:
            metadata: Stream metadata (provider, model, etc.)
        """
        if self.show_metadata:
            print(f"{self.prefix}Stream started: {metadata}")
    
    def on_token_received(self, token: str, index: int) -> None:
        """Called when a token is received from the stream.
        
        Args:
            token: The token received
            index: The token index in the response
        """
        print(f"{self.prefix}{token}", end="", flush=True)
    
    def on_stream_complete(self, full_response: str) -> None:
        """Called when a stream completes.
        
        Args:
            full_response: The complete response text
        """
        print()  # New line at end
        if self.show_metadata:
            print(f"{self.prefix}Stream completed: {len(full_response)} characters")
    
    def on_stream_error(self, error: Exception) -> None:
        """Called when a stream encounters an error.
        
        Args:
            error: The error that occurred
        """
        print(f"\n{self.prefix}Stream error: {str(error)}")


class CallbackStreamHandler(StreamHandler):
    """Stream handler that calls user-provided callbacks."""
    
    def __init__(
        self,
        on_start: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_token: Optional[Callable[[str, int], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """Initialize callback stream handler.
        
        Args:
            on_start: Optional callback for stream start
            on_token: Optional callback for token received
            on_complete: Optional callback for stream completion
            on_error: Optional callback for stream error
        """
        self.on_start_callback = on_start
        self.on_token_callback = on_token
        self.on_complete_callback = on_complete
        self.on_error_callback = on_error
    
    def on_stream_start(self, metadata: Dict[str, Any]) -> None:
        """Called when a stream starts.
        
        Args:
            metadata: Stream metadata (provider, model, etc.)
        """
        if self.on_start_callback:
            try:
                self.on_start_callback(metadata)
            except Exception as e:
                logger.error(f"Error in stream start callback: {str(e)}")
                raise StreamHandlerError(f"Start callback error: {str(e)}") from e
    
    def on_token_received(self, token: str, index: int) -> None:
        """Called when a token is received from the stream.
        
        Args:
            token: The token received
            index: The token index in the response
        """
        if self.on_token_callback:
            try:
                self.on_token_callback(token, index)
            except Exception as e:
                logger.error(f"Error in token callback: {str(e)}")
                raise StreamHandlerError(f"Token callback error: {str(e)}") from e
    
    def on_stream_complete(self, full_response: str) -> None:
        """Called when a stream completes.
        
        Args:
            full_response: The complete response text
        """
        if self.on_complete_callback:
            try:
                self.on_complete_callback(full_response)
            except Exception as e:
                logger.error(f"Error in stream complete callback: {str(e)}")
                raise StreamHandlerError(f"Complete callback error: {str(e)}") from e
    
    def on_stream_error(self, error: Exception) -> None:
        """Called when a stream encounters an error.
        
        Args:
            error: The error that occurred
        """
        if self.on_error_callback:
            try:
                self.on_error_callback(error)
            except Exception as e:
                logger.error(f"Error in stream error callback: {str(e)}")
                # Don't raise here to avoid hiding the original error