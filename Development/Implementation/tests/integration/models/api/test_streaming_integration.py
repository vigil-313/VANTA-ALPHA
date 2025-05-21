#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for API Model streaming functionality.
"""
# TASK-REF: AM_002 - Streaming Response Handling
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-002 - Streaming Response Handling Implementation

import unittest
import os
import time
from typing import Dict, Any, List, Optional

from src.models.api.api_manager import APIModelManager
from src.models.api.streaming.stream_handler import BufferedStreamHandler, StreamHandler
from src.models.api.exceptions import APIModelError

# Skip tests if API keys are not available
SKIP_TESTS = not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
SKIP_REASON = "API keys not available in environment"


class TokenTimingHandler(StreamHandler):
    """Stream handler that tracks token timing."""
    
    def __init__(self):
        """Initialize token timing handler."""
        self.start_time: Optional[float] = None
        self.tokens: List[Dict[str, Any]] = []
        self.is_complete: bool = False
        self.error: Optional[Exception] = None
        self.metadata: Dict[str, Any] = {}
    
    def on_stream_start(self, metadata: Dict[str, Any]) -> None:
        """Called when a stream starts.
        
        Args:
            metadata: Stream metadata (provider, model, etc.)
        """
        self.start_time = time.time()
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
        self.tokens.append({
            "token": token,
            "index": index,
            "time": time.time() - (self.start_time or time.time()),
            "length": len(token)
        })
    
    def on_stream_complete(self, full_response: str) -> None:
        """Called when a stream completes.
        
        Args:
            full_response: The complete response text
        """
        self.is_complete = True
        self.total_time = time.time() - (self.start_time or time.time())
    
    def on_stream_error(self, error: Exception) -> None:
        """Called when a stream encounters an error.
        
        Args:
            error: The error that occurred
        """
        self.error = error
    
    def get_stats(self) -> Dict[str, Any]:
        """Get token statistics.
        
        Returns:
            Dictionary with token statistics
        """
        if not self.tokens:
            return {
                "tokens": 0,
                "total_time": 0,
                "tokens_per_second": 0,
                "first_token_time": 0,
                "average_token_length": 0
            }
        
        total_tokens = len(self.tokens)
        total_characters = sum(t["length"] for t in self.tokens)
        total_time = self.tokens[-1]["time"]
        first_token_time = self.tokens[0]["time"] if self.tokens else 0
        
        return {
            "tokens": total_tokens,
            "characters": total_characters,
            "total_time": total_time,
            "tokens_per_second": total_tokens / total_time if total_time > 0 else 0,
            "characters_per_second": total_characters / total_time if total_time > 0 else 0,
            "first_token_time": first_token_time,
            "average_token_length": total_characters / total_tokens if total_tokens > 0 else 0
        }


@unittest.skipIf(SKIP_TESTS, SKIP_REASON)
class TestAPIStreaming(unittest.TestCase):
    """Test API streaming functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.api_manager = APIModelManager()
    
    def test_anthropic_streaming(self):
        """Test streaming from Anthropic API."""
        # Skip if no API key
        if not os.environ.get("ANTHROPIC_API_KEY"):
            self.skipTest("Anthropic API key not available")
        
        # Create handlers
        buffer_handler = BufferedStreamHandler()
        timing_handler = TokenTimingHandler()
        
        # Set up prompt
        prompt = "Write 3 facts about dogs."
        
        try:
            # Start streaming
            stream_manager = self.api_manager.generate_stream_with_handlers(
                prompt=prompt,
                model_id="anthropic:claude-3-haiku-20240307",  # Use smallest/fastest model for testing
                params={"max_tokens": 100},
                handlers=[buffer_handler, timing_handler],
                stream_config={"buffer_size": 1}  # No buffering to measure individual tokens
            )
            
            # Wait for completion
            result = stream_manager.get_result(timeout=30.0)
            
            # Verify completion
            self.assertTrue(buffer_handler.is_complete)
            self.assertTrue(timing_handler.is_complete)
            
            # Check response
            response = buffer_handler.get_response()
            self.assertGreater(len(response), 20)  # Should be more than 20 characters
            
            # Check timing stats
            stats = timing_handler.get_stats()
            print(f"Anthropic streaming stats: {stats}")
            
            # Verify performance
            self.assertGreater(stats["tokens"], 10)  # Should have at least 10 tokens
            self.assertLess(stats["first_token_time"], 5.0)  # First token should arrive within 5 seconds
            
        except APIModelError as e:
            self.fail(f"API error: {str(e)}")
    
    def test_openai_streaming(self):
        """Test streaming from OpenAI API."""
        # Skip if no API key
        if not os.environ.get("OPENAI_API_KEY"):
            self.skipTest("OpenAI API key not available")
        
        # Create handlers
        buffer_handler = BufferedStreamHandler()
        timing_handler = TokenTimingHandler()
        
        # Set up prompt
        prompt = "Write 3 facts about cats."
        
        try:
            # Start streaming
            stream_manager = self.api_manager.generate_stream_with_handlers(
                prompt=prompt,
                model_id="openai:gpt-3.5-turbo",  # Use fastest model for testing
                params={"max_tokens": 100},
                handlers=[buffer_handler, timing_handler],
                stream_config={"buffer_size": 1}  # No buffering to measure individual tokens
            )
            
            # Wait for completion
            result = stream_manager.get_result(timeout=30.0)
            
            # Verify completion
            self.assertTrue(buffer_handler.is_complete)
            self.assertTrue(timing_handler.is_complete)
            
            # Check response
            response = buffer_handler.get_response()
            self.assertGreater(len(response), 20)  # Should be more than 20 characters
            
            # Check timing stats
            stats = timing_handler.get_stats()
            print(f"OpenAI streaming stats: {stats}")
            
            # Verify performance
            self.assertGreater(stats["tokens"], 10)  # Should have at least 10 tokens
            self.assertLess(stats["first_token_time"], 5.0)  # First token should arrive within 5 seconds
            
        except APIModelError as e:
            self.fail(f"API error: {str(e)}")
    
    def test_stream_control(self):
        """Test streaming control operations."""
        # Skip if no API keys
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")):
            self.skipTest("No API keys available")
        
        # Use available model
        if os.environ.get("ANTHROPIC_API_KEY"):
            model_id = "anthropic:claude-3-haiku-20240307"
        else:
            model_id = "openai:gpt-3.5-turbo"
        
        # Create handler
        buffer_handler = BufferedStreamHandler()
        
        # Set up prompt for long response
        prompt = "Write a detailed explanation of how the solar system formed."
        
        try:
            # Start streaming
            stream_manager = self.api_manager.generate_stream_with_handlers(
                prompt=prompt,
                model_id=model_id,
                params={"max_tokens": 300},  # Make sure it generates enough tokens
                handlers=[buffer_handler]
            )
            
            # Let it process for a moment
            time.sleep(2.0)
            
            # Get status
            status_before = stream_manager.get_stream_status()
            tokens_before = len(buffer_handler.tokens)
            
            # Pause the stream
            result = stream_manager.pause_stream()
            self.assertTrue(result)
            
            # Wait a moment to ensure it's paused
            time.sleep(1.0)
            
            # Verify no new tokens arrived
            self.assertEqual(len(buffer_handler.tokens), tokens_before)
            
            # Resume the stream
            result = stream_manager.resume_stream()
            self.assertTrue(result)
            
            # Let it process a bit more
            time.sleep(2.0)
            
            # Should have more tokens now
            self.assertGreater(len(buffer_handler.tokens), tokens_before)
            
            # Cancel the stream
            result = stream_manager.cancel_stream()
            self.assertTrue(result)
            
            # Verify stream was cancelled
            status = stream_manager.get_stream_status()
            self.assertEqual(status["state"], "cancelled")
            
        except APIModelError as e:
            self.fail(f"API error: {str(e)}")


if __name__ == "__main__":
    unittest.main()