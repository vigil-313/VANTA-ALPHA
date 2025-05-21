#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stream Manager for handling streaming responses.

This module provides a manager for handling streaming responses from API models.
"""
# TASK-REF: AM_002 - Streaming Response Handling
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-002 - Streaming Response Handling Implementation

import logging
import threading
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

from .stream_handler import StreamHandler
from .stream_processor import StreamProcessor
from .stream_config import StreamConfig
from .exceptions import (
    StreamingError,
    StreamProcessingError,
    StreamTimeoutError,
    StreamCancelledError,
)

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages streaming response processing."""
    
    # Stream states
    STATE_INACTIVE = "inactive"
    STATE_ACTIVE = "active"
    STATE_PAUSED = "paused"
    STATE_COMPLETED = "completed"
    STATE_ERROR = "error"
    STATE_CANCELLED = "cancelled"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize stream manager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = StreamConfig(config)
        self.handlers: List[StreamHandler] = []
        self.processor = StreamProcessor(config)
        
        # Streaming state
        self.stream_id = uuid.uuid4().hex  # Unique ID for this stream
        self.stream_thread: Optional[threading.Thread] = None
        self.stream_state = self.STATE_INACTIVE
        self.stream_lock = threading.RLock()  # Re-entrant lock for thread safety
        self.stream_result: Optional[str] = None
        self.stream_error: Optional[Exception] = None
        
        # Stream source
        self.current_stream: Optional[Iterator[str]] = None
        
        # Statistics
        self.stats = {
            "tokens_received": 0,
            "tokens_per_second": 0,
            "start_time": None,
            "elapsed_time": 0,
            "errors": 0
        }
    
    def register_handler(self, handler: StreamHandler) -> int:
        """Register a stream handler.
        
        Args:
            handler: StreamHandler instance
            
        Returns:
            Handler ID for later reference
            
        Raises:
            TypeError: If handler does not implement StreamHandler
        """
        if not isinstance(handler, StreamHandler):
            raise TypeError("Handler must implement StreamHandler interface")
        
        with self.stream_lock:
            self.handlers.append(handler)
            return len(self.handlers) - 1
    
    def unregister_handler(self, handler_id: int) -> bool:
        """Unregister a stream handler.
        
        Args:
            handler_id: Handler ID returned from register_handler
            
        Returns:
            True if successful, False otherwise
        """
        with self.stream_lock:
            if 0 <= handler_id < len(self.handlers):
                self.handlers.pop(handler_id)
                return True
            return False
    
    def start_stream(
        self, stream_source: Iterator[str], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start processing a stream.
        
        Args:
            stream_source: Iterator producing tokens
            metadata: Optional metadata about the stream
            
        Returns:
            Stream ID for tracking
            
        Raises:
            StreamingError: If there is an existing active stream
        """
        with self.stream_lock:
            # Check if there's already an active stream
            if self.stream_state in (self.STATE_ACTIVE, self.STATE_PAUSED):
                raise StreamingError("Cannot start new stream while another is active")
            
            # Reset state
            self.stream_id = uuid.uuid4().hex
            self.stream_state = self.STATE_ACTIVE
            self.stream_result = None
            self.stream_error = None
            self.current_stream = stream_source
            
            # Reset statistics
            self.stats = {
                "tokens_received": 0,
                "tokens_per_second": 0,
                "start_time": time.time(),
                "elapsed_time": 0,
                "errors": 0
            }
            
            # Notify handlers of stream start
            stream_metadata = metadata or {}
            for handler in self.handlers:
                try:
                    handler.on_stream_start(stream_metadata)
                except Exception as e:
                    logger.error(f"Error in stream start handler: {str(e)}")
                    self.stats["errors"] += 1
            
            # Start processing
            use_threads = self.config.get("use_threads", True)
            if use_threads:
                self.stream_thread = threading.Thread(
                    target=self._process_stream_thread,
                    name=f"stream-{self.stream_id[:8]}",
                    daemon=True,
                )
                self.stream_thread.start()
            else:
                # Process synchronously
                self._process_stream()
            
            return self.stream_id
    
    def _process_stream_thread(self) -> None:
        """Process the stream in a separate thread."""
        try:
            self._process_stream()
        except Exception as e:
            logger.error(f"Unhandled exception in stream thread: {str(e)}")
            with self.stream_lock:
                if self.stream_state not in (self.STATE_COMPLETED, self.STATE_CANCELLED):
                    self.stream_state = self.STATE_ERROR
                    self.stream_error = e
                    
                    # Notify handlers of error
                    for handler in self.handlers:
                        try:
                            handler.on_stream_error(e)
                        except Exception as handler_e:
                            logger.error(f"Error in stream error handler: {str(handler_e)}")
                            self.stats["errors"] += 1
    
    def _process_stream(self) -> None:
        """Process the current stream, dispatching tokens to handlers."""
        if self.current_stream is None:
            logger.error("No stream source to process")
            return
        
        try:
            full_response: List[str] = []
            
            for i, token in enumerate(self.current_stream):
                with self.stream_lock:
                    # Check if we should continue processing
                    if self.stream_state == self.STATE_CANCELLED:
                        raise StreamCancelledError("Stream was cancelled")
                    
                    # Process token if active
                    if self.stream_state == self.STATE_ACTIVE:
                        # Store token
                        full_response.append(token)
                        self.stats["tokens_received"] += 1
                        self.stats["elapsed_time"] = time.time() - self.stats["start_time"]
                        
                        if self.stats["elapsed_time"] > 0:
                            self.stats["tokens_per_second"] = self.stats["tokens_received"] / self.stats["elapsed_time"]
                        
                        # Notify handlers
                        for handler in self.handlers:
                            try:
                                handler.on_token_received(token, i)
                            except Exception as e:
                                logger.error(f"Error in token handler: {str(e)}")
                                self.stats["errors"] += 1
                
                # Handle pause state outside the lock
                while True:
                    with self.stream_lock:
                        if self.stream_state != self.STATE_PAUSED:
                            break
                    
                    # Sleep briefly to avoid tight loop
                    time.sleep(0.01)
                    
                    # Check if we timed out waiting for pause to end
                    pause_timeout = self.config.get("pause_timeout", 30.0)
                    if time.time() - self.stats["start_time"] > pause_timeout:
                        with self.stream_lock:
                            self.stream_state = self.STATE_ERROR
                            self.stream_error = StreamTimeoutError(f"Stream paused for more than {pause_timeout} seconds")
                            
                            # Notify handlers of error
                            for handler in self.handlers:
                                try:
                                    handler.on_stream_error(self.stream_error)
                                except Exception as e:
                                    logger.error(f"Error in stream error handler: {str(e)}")
                                    self.stats["errors"] += 1
                            
                            return
            
            # Stream completed normally
            with self.stream_lock:
                if self.stream_state != self.STATE_CANCELLED:
                    self.stream_state = self.STATE_COMPLETED
                    complete_response = "".join(full_response)
                    self.stream_result = complete_response
                    
                    # Notify handlers of completion
                    for handler in self.handlers:
                        try:
                            handler.on_stream_complete(complete_response)
                        except Exception as e:
                            logger.error(f"Error in stream complete handler: {str(e)}")
                            self.stats["errors"] += 1
        
        except StreamCancelledError:
            # Stream was cancelled, no need to notify again
            pass
        
        except Exception as e:
            # Stream encountered an error
            with self.stream_lock:
                if self.stream_state not in (self.STATE_COMPLETED, self.STATE_CANCELLED):
                    self.stream_state = self.STATE_ERROR
                    self.stream_error = e
                    
                    # Notify handlers of error
                    for handler in self.handlers:
                        try:
                            handler.on_stream_error(e)
                        except Exception as handler_e:
                            logger.error(f"Error in stream error handler: {str(handler_e)}")
            
                    self.stats["errors"] += 1
                    logger.error(f"Stream processing error: {str(e)}")
    
    def pause_stream(self) -> bool:
        """Pause the current stream.
        
        Returns:
            True if successful, False otherwise
        """
        with self.stream_lock:
            if self.stream_state == self.STATE_ACTIVE:
                self.stream_state = self.STATE_PAUSED
                logger.debug(f"Stream {self.stream_id[:8]} paused")
                return True
            return False
    
    def resume_stream(self) -> bool:
        """Resume the current stream.
        
        Returns:
            True if successful, False otherwise
        """
        with self.stream_lock:
            if self.stream_state == self.STATE_PAUSED:
                self.stream_state = self.STATE_ACTIVE
                logger.debug(f"Stream {self.stream_id[:8]} resumed")
                return True
            return False
    
    def cancel_stream(self) -> bool:
        """Cancel the current stream.
        
        Returns:
            True if successful, False otherwise
        """
        with self.stream_lock:
            if self.stream_state in (self.STATE_ACTIVE, self.STATE_PAUSED):
                self.stream_state = self.STATE_CANCELLED
                logger.debug(f"Stream {self.stream_id[:8]} cancelled")
                return True
            return False
    
    def get_stream_status(self) -> Dict[str, Any]:
        """Get current stream status.
        
        Returns:
            Dictionary with stream status and statistics
        """
        with self.stream_lock:
            return {
                "id": self.stream_id,
                "state": self.stream_state,
                "stats": self.stats.copy(),
                "has_result": self.stream_result is not None,
                "has_error": self.stream_error is not None,
                "processor_stats": self.processor.get_statistics()
            }
    
    def get_result(self, timeout: Optional[float] = None) -> str:
        """Get the stream result, waiting if necessary.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Stream result string
            
        Raises:
            StreamingError: If stream is inactive
            StreamTimeoutError: If timeout is reached
            StreamProcessingError: If stream ended with an error
        """
        if self.stream_state == self.STATE_INACTIVE:
            raise StreamingError("No active stream")
        
        # If we have a thread, wait for it to complete
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=timeout)
            
            if self.stream_thread.is_alive():
                raise StreamTimeoutError(f"Timeout waiting for stream completion (timeout={timeout}s)")
        
        with self.stream_lock:
            # Check for error
            if self.stream_error:
                raise StreamProcessingError(f"Stream ended with error: {str(self.stream_error)}")
            
            # Check for result
            if self.stream_result is not None:
                return self.stream_result
            
            # No result yet
            if self.stream_state == self.STATE_COMPLETED:
                return ""  # Empty result
            
            raise StreamingError(f"Stream is in state {self.stream_state} with no result")