#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stream processor for handling streaming responses.

This module provides a processor for handling streaming responses from API models.
"""
# TASK-REF: AM_002 - Streaming Response Handling
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-002 - Streaming Response Handling Implementation

import logging
import time
from typing import Any, Dict, Iterator, List, Optional

from .stream_handler import StreamHandler
from .stream_config import StreamConfig
from .exceptions import StreamProcessingError, StreamBufferOverflowError

logger = logging.getLogger(__name__)


class StreamProcessor:
    """Processes streaming responses from API models."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize stream processor.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = StreamConfig(config)
        self.buffer_size = self.config.get("buffer_size", 1)
        self.max_buffer_size = self.config.get("max_buffer_size", 1024)
        self.token_buffer: List[str] = []
        
        # Performance tracking
        self.stats = {
            "tokens_processed": 0,
            "tokens_per_second": 0,
            "processing_time": 0,
            "buffer_overflows": 0,
            "errors": 0,
            "start_time": None,
            "last_token_time": None
        }
    
    def process_stream(
        self, stream: Iterator[str], handlers: List[StreamHandler], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process a stream, dispatching to handlers.
        
        Args:
            stream: Token iterator
            handlers: List of stream handlers
            metadata: Optional metadata about the stream
            
        Returns:
            Full response text
            
        Raises:
            StreamProcessingError: If stream processing fails
        """
        response_parts: List[str] = []
        metadata = metadata or {}
        
        # Initialize stats
        self.stats["tokens_processed"] = 0
        self.stats["tokens_per_second"] = 0
        self.stats["processing_time"] = 0
        self.stats["buffer_overflows"] = 0
        self.stats["errors"] = 0
        self.stats["start_time"] = time.time()
        self.stats["last_token_time"] = self.stats["start_time"]
        
        try:
            # Notify handlers of stream start
            for handler in handlers:
                try:
                    handler.on_stream_start(metadata)
                except Exception as e:
                    logger.error(f"Error in stream start handler: {str(e)}")
                    self.stats["errors"] += 1
            
            # Process tokens
            for i, token in enumerate(stream):
                response_parts.append(token)
                self.stats["tokens_processed"] += 1
                
                # Update timing stats
                current_time = time.time()
                self.stats["processing_time"] = current_time - self.stats["start_time"]
                self.stats["last_token_time"] = current_time
                
                if self.stats["processing_time"] > 0:
                    self.stats["tokens_per_second"] = self.stats["tokens_processed"] / self.stats["processing_time"]
                
                # Add to buffer
                self.token_buffer.append(token)
                
                if len(self.token_buffer) > self.max_buffer_size:
                    # Buffer overflow
                    logger.warning(f"Stream buffer overflow ({len(self.token_buffer)} tokens)")
                    self.stats["buffer_overflows"] += 1
                    
                    # Force processing the buffer
                    buffered_content = "".join(self.token_buffer)
                    
                    # Notify handlers
                    for handler in handlers:
                        try:
                            handler.on_token_received(buffered_content, i)
                        except Exception as e:
                            logger.error(f"Error in token handler: {str(e)}")
                            self.stats["errors"] += 1
                    
                    # Clear buffer
                    self.token_buffer = []
                    
                    # Check if we should raise an error
                    if self.config.get("error_on_buffer_overflow", False):
                        raise StreamBufferOverflowError(
                            f"Stream buffer overflow exceeded maximum size ({self.max_buffer_size} tokens)"
                        )
                
                # Process buffer if it reaches the desired size
                if len(self.token_buffer) >= self.buffer_size:
                    buffered_content = "".join(self.token_buffer)
                    
                    # Notify handlers
                    for handler in handlers:
                        try:
                            handler.on_token_received(buffered_content, i)
                        except Exception as e:
                            logger.error(f"Error in token handler: {str(e)}")
                            self.stats["errors"] += 1
                    
                    # Clear buffer
                    self.token_buffer = []
            
            # Process any remaining tokens in buffer
            if self.token_buffer:
                buffered_content = "".join(self.token_buffer)
                
                # Notify handlers
                for handler in handlers:
                    try:
                        handler.on_token_received(buffered_content, len(response_parts) - 1)
                    except Exception as e:
                        logger.error(f"Error in token handler: {str(e)}")
                        self.stats["errors"] += 1
                
                # Clear buffer
                self.token_buffer = []
            
            # Compile full response
            full_response = "".join(response_parts)
            
            # Notify handlers of completion
            for handler in handlers:
                try:
                    handler.on_stream_complete(full_response)
                except Exception as e:
                    logger.error(f"Error in stream complete handler: {str(e)}")
                    self.stats["errors"] += 1
            
            return full_response
            
        except Exception as e:
            # Update error stats
            self.stats["errors"] += 1
            
            # Clean up buffer
            self.token_buffer = []
            
            # Notify handlers of error
            for handler in handlers:
                try:
                    handler.on_stream_error(e)
                except Exception as handler_e:
                    logger.error(f"Error in stream error handler: {str(handler_e)}")
                    self.stats["errors"] += 1
            
            # Re-raise as stream processing error
            if isinstance(e, StreamProcessingError):
                raise
            else:
                raise StreamProcessingError(f"Stream processing failed: {str(e)}") from e
    
    def buffer_tokens(self, tokens: Iterator[str], buffer_size: Optional[int] = None) -> Iterator[str]:
        """Buffer tokens into larger chunks.
        
        Args:
            tokens: Iterator of tokens
            buffer_size: Optional size to override default
            
        Returns:
            Iterator of buffered token chunks
        """
        buffer_size = buffer_size or self.buffer_size
        current_buffer: List[str] = []
        
        for token in tokens:
            current_buffer.append(token)
            
            if len(current_buffer) >= buffer_size:
                yield "".join(current_buffer)
                current_buffer = []
        
        # Yield any remaining tokens
        if current_buffer:
            yield "".join(current_buffer)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get stream processor statistics.
        
        Returns:
            Dictionary with processor statistics
        """
        # Calculate elapsed time
        if self.stats["start_time"] is not None:
            if self.stats["last_token_time"] is not None:
                last_token_elapsed = time.time() - self.stats["last_token_time"]
            else:
                last_token_elapsed = 0
            
            elapsed = time.time() - self.stats["start_time"]
        else:
            elapsed = 0
            last_token_elapsed = 0
        
        return {
            "buffer_size": self.buffer_size,
            "max_buffer_size": self.max_buffer_size,
            "buffered_tokens": len(self.token_buffer),
            "tokens_processed": self.stats["tokens_processed"],
            "tokens_per_second": self.stats["tokens_per_second"],
            "processing_time": self.stats["processing_time"],
            "elapsed_time": elapsed,
            "last_token_elapsed": last_token_elapsed,
            "buffer_overflows": self.stats["buffer_overflows"],
            "errors": self.stats["errors"]
        }