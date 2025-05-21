#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for API Model streaming functionality.
"""
# TASK-REF: AM_002 - Streaming Response Handling
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-002 - Streaming Response Handling Implementation

import unittest
import time
from typing import Dict, Any, List, Iterator
from unittest.mock import MagicMock, patch

from src.models.api.streaming.stream_handler import (
    StreamHandler,
    BufferedStreamHandler,
    ConsoleStreamHandler,
    CallbackStreamHandler,
)
from src.models.api.streaming.stream_manager import StreamManager
from src.models.api.streaming.stream_processor import StreamProcessor
from src.models.api.streaming.stream_config import StreamConfig
from src.models.api.streaming.exceptions import (
    StreamingError,
    StreamHandlerError,
    StreamProcessingError,
    StreamTimeoutError,
    StreamCancelledError,
)


class MockStreamSource:
    """Mock stream source for testing."""
    
    def __init__(self, tokens: List[str], delay: float = 0.01):
        """Initialize mock stream source.
        
        Args:
            tokens: List of tokens to yield
            delay: Delay between tokens in seconds
        """
        self.tokens = tokens
        self.delay = delay
        self.index = 0
    
    def __iter__(self) -> Iterator[str]:
        """Get iterator."""
        self.index = 0
        return self
    
    def __next__(self) -> str:
        """Get next token."""
        if self.index >= len(self.tokens):
            raise StopIteration
        
        token = self.tokens[self.index]
        self.index += 1
        
        # Add delay
        if self.delay > 0:
            time.sleep(self.delay)
        
        return token


class TestStreamHandler(unittest.TestCase):
    """Test the StreamHandler implementations."""
    
    def test_buffered_stream_handler(self):
        """Test the BufferedStreamHandler."""
        handler = BufferedStreamHandler()
        
        # Test stream start
        metadata = {"model": "test-model", "provider": "test-provider"}
        handler.on_stream_start(metadata)
        self.assertEqual(handler.metadata, metadata)
        self.assertEqual(handler.tokens, [])
        self.assertFalse(handler.is_complete)
        self.assertIsNone(handler.error)
        
        # Test token handling
        handler.on_token_received("Hello", 0)
        handler.on_token_received(" ", 1)
        handler.on_token_received("world", 2)
        self.assertEqual(handler.tokens, ["Hello", " ", "world"])
        self.assertEqual(handler.get_response(), "Hello world")
        
        # Test completion
        handler.on_stream_complete("Hello world")
        self.assertTrue(handler.is_complete)
        
        # Test reset
        handler.reset()
        self.assertEqual(handler.tokens, [])
        self.assertFalse(handler.is_complete)
        self.assertIsNone(handler.error)
        self.assertEqual(handler.metadata, {})
    
    def test_callback_stream_handler(self):
        """Test the CallbackStreamHandler."""
        # Create mock callbacks
        on_start = MagicMock()
        on_token = MagicMock()
        on_complete = MagicMock()
        on_error = MagicMock()
        
        handler = CallbackStreamHandler(
            on_start=on_start,
            on_token=on_token,
            on_complete=on_complete,
            on_error=on_error
        )
        
        # Test stream start
        metadata = {"model": "test-model", "provider": "test-provider"}
        handler.on_stream_start(metadata)
        on_start.assert_called_once_with(metadata)
        
        # Test token handling
        handler.on_token_received("Hello", 0)
        on_token.assert_called_once_with("Hello", 0)
        
        handler.on_token_received("world", 1)
        self.assertEqual(on_token.call_count, 2)
        on_token.assert_called_with("world", 1)
        
        # Test completion
        handler.on_stream_complete("Hello world")
        on_complete.assert_called_once_with("Hello world")
        
        # Test error
        error = Exception("Test error")
        handler.on_stream_error(error)
        on_error.assert_called_once_with(error)


class TestStreamProcessor(unittest.TestCase):
    """Test the StreamProcessor."""
    
    def test_process_stream(self):
        """Test processing a stream."""
        # Create mock stream source
        tokens = ["Hello", " ", "world", "!"]
        stream = iter(tokens)
        
        # Create mock handler
        handler = MagicMock(spec=StreamHandler)
        
        # Process stream
        processor = StreamProcessor()
        result = processor.process_stream(stream, [handler], {"test": "metadata"})
        
        # Verify result
        self.assertEqual(result, "Hello world!")
        
        # Verify handler calls
        handler.on_stream_start.assert_called_once_with({"test": "metadata"})
        self.assertEqual(handler.on_token_received.call_count, 4)
        handler.on_stream_complete.assert_called_once_with("Hello world!")
    
    def test_buffer_tokens(self):
        """Test buffering tokens."""
        # Create processor with buffer size 2
        processor = StreamProcessor({"buffer_size": 2})
        
        # Test buffering
        tokens = ["a", "b", "c", "d", "e"]
        buffered = list(processor.buffer_tokens(iter(tokens)))
        
        # Verify result
        self.assertEqual(buffered, ["ab", "cd", "e"])
    
    def test_error_handling(self):
        """Test error handling during processing."""
        # Create mock stream source that raises an error
        def error_stream():
            yield "Hello"
            yield " "
            raise ValueError("Test error")
        
        # Create mock handler
        handler = MagicMock(spec=StreamHandler)
        
        # Process stream
        processor = StreamProcessor()
        
        # Verify error handling
        with self.assertRaises(StreamProcessingError):
            processor.process_stream(error_stream(), [handler])
        
        # Verify handler calls
        handler.on_stream_start.assert_called_once()
        self.assertEqual(handler.on_token_received.call_count, 2)
        handler.on_stream_error.assert_called_once()


class TestStreamManager(unittest.TestCase):
    """Test the StreamManager."""
    
    def test_register_handler(self):
        """Test registering a handler."""
        manager = StreamManager()
        
        # Register a handler
        handler = BufferedStreamHandler()
        handler_id = manager.register_handler(handler)
        
        # Verify registration
        self.assertEqual(handler_id, 0)
        self.assertEqual(len(manager.handlers), 1)
        self.assertIs(manager.handlers[0], handler)
        
        # Register another handler
        handler2 = BufferedStreamHandler()
        handler_id2 = manager.register_handler(handler2)
        
        # Verify registration
        self.assertEqual(handler_id2, 1)
        self.assertEqual(len(manager.handlers), 2)
        self.assertIs(manager.handlers[1], handler2)
    
    def test_unregister_handler(self):
        """Test unregistering a handler."""
        manager = StreamManager()
        
        # Register handlers
        handler1 = BufferedStreamHandler()
        handler2 = BufferedStreamHandler()
        handler_id1 = manager.register_handler(handler1)
        handler_id2 = manager.register_handler(handler2)
        
        # Unregister first handler
        result = manager.unregister_handler(handler_id1)
        
        # Verify unregistration
        self.assertTrue(result)
        self.assertEqual(len(manager.handlers), 1)
        self.assertIs(manager.handlers[0], handler2)
        
        # Unregister invalid handler
        result = manager.unregister_handler(99)
        
        # Verify failure
        self.assertFalse(result)
    
    def test_start_stream(self):
        """Test starting a stream."""
        manager = StreamManager({"use_threads": False})  # Don't use threads for testing
        
        # Create mock stream source
        tokens = ["Hello", " ", "world", "!"]
        stream = MockStreamSource(tokens, delay=0)
        
        # Create handler
        handler = BufferedStreamHandler()
        manager.register_handler(handler)
        
        # Start stream
        stream_id = manager.start_stream(stream, {"test": "metadata"})
        
        # Verify stream ID
        self.assertIsNotNone(stream_id)
        
        # Verify stream state
        status = manager.get_stream_status()
        self.assertEqual(status["state"], StreamManager.STATE_COMPLETED)
        
        # Verify handler received all tokens
        self.assertEqual(handler.get_response(), "Hello world!")
        self.assertTrue(handler.is_complete)
    
    def test_cancel_stream(self):
        """Test cancelling a stream."""
        manager = StreamManager({"use_threads": True})
        
        # Create a slow stream source
        tokens = ["This", " ", "is", " ", "a", " ", "test", " ", "message", "."]
        stream = MockStreamSource(tokens, delay=0.1)
        
        # Create handler
        handler = BufferedStreamHandler()
        manager.register_handler(handler)
        
        # Start stream
        stream_id = manager.start_stream(stream)
        
        # Let it process a few tokens
        time.sleep(0.25)
        
        # Cancel the stream
        result = manager.cancel_stream()
        
        # Verify cancellation
        self.assertTrue(result)
        
        # Wait for thread to finish
        if manager.stream_thread:
            manager.stream_thread.join(timeout=1.0)
        
        # Verify stream state
        status = manager.get_stream_status()
        self.assertEqual(status["state"], StreamManager.STATE_CANCELLED)
        
        # Verify handler received some but not all tokens
        self.assertLess(len(handler.tokens), len(tokens))
    
    def test_pause_resume_stream(self):
        """Test pausing and resuming a stream."""
        manager = StreamManager({"use_threads": True})
        
        # Create a slow stream source
        tokens = ["This", " ", "is", " ", "a", " ", "test", " ", "message", "."]
        stream = MockStreamSource(tokens, delay=0.1)
        
        # Create handler
        handler = BufferedStreamHandler()
        manager.register_handler(handler)
        
        # Start stream
        stream_id = manager.start_stream(stream)
        
        # Let it process a few tokens
        time.sleep(0.25)
        
        # Pause the stream
        result = manager.pause_stream()
        
        # Verify pause
        self.assertTrue(result)
        
        # Check state
        self.assertEqual(manager.stream_state, StreamManager.STATE_PAUSED)
        
        # Record token count
        tokens_before_pause = len(handler.tokens)
        
        # Wait a bit and verify no new tokens
        time.sleep(0.3)
        self.assertEqual(len(handler.tokens), tokens_before_pause)
        
        # Resume the stream
        result = manager.resume_stream()
        
        # Verify resume
        self.assertTrue(result)
        
        # Check state
        self.assertEqual(manager.stream_state, StreamManager.STATE_ACTIVE)
        
        # Wait for completion
        if manager.stream_thread:
            manager.stream_thread.join(timeout=2.0)
        
        # Verify completion
        self.assertEqual(manager.stream_state, StreamManager.STATE_COMPLETED)
        self.assertEqual(handler.get_response(), "This is a test message.")
        self.assertTrue(handler.is_complete)


if __name__ == "__main__":
    unittest.main()