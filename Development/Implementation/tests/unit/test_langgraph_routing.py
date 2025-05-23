#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for LangGraph routing functions.

This module contains comprehensive tests for the conditional routing logic
that controls workflow flow in the VANTA LangGraph implementation.
"""
# TASK-REF: LG_003 - LangGraph Graph Definition and Conditional Routing
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration

import time
import pytest
from unittest.mock import patch

from src.langgraph.routing import (
    should_process,
    determine_processing_path,
    check_processing_complete,
    should_synthesize_speech,
    should_update_memory,
    get_routing_function,
    list_routing_functions,
)
from src.langgraph.state import (
    VANTAState,
    ActivationStatus,
    create_empty_state,
    create_message,
)


class TestShouldProcess:
    """Test the should_process routing function."""
    
    def test_should_process_inactive(self):
        """Test that inactive status returns 'end'."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.INACTIVE
        
        result = should_process(state)
        assert result == "end"
    
    def test_should_process_listening(self):
        """Test that listening status returns 'continue'."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.LISTENING
        
        result = should_process(state)
        assert result == "continue"
    
    def test_should_process_processing(self):
        """Test that processing status returns 'continue'."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        
        result = should_process(state)
        assert result == "continue"
    
    def test_should_process_speaking(self):
        """Test that speaking status returns 'continue'."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.SPEAKING
        
        result = should_process(state)
        assert result == "continue"
    
    def test_should_process_missing_activation(self):
        """Test that missing activation status returns 'end'."""
        state = {
            "messages": [],
            "audio": {},
            "memory": {},
            "config": {}
        }
        
        result = should_process(state)
        assert result == "end"
    
    def test_should_process_missing_status(self):
        """Test that missing status in activation returns 'end'."""
        state = create_empty_state()
        del state["activation"]["status"]
        
        result = should_process(state)
        assert result == "end"


class TestDetermineProcessingPath:
    """Test the determine_processing_path routing function."""
    
    def test_determine_path_local(self):
        """Test routing to local processing path."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "local"
        
        result = determine_processing_path(state)
        assert result == "local"
    
    def test_determine_path_api(self):
        """Test routing to API processing path."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "api"
        
        result = determine_processing_path(state)
        assert result == "api"
    
    def test_determine_path_parallel(self):
        """Test routing to parallel processing path."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "parallel"
        
        result = determine_processing_path(state)
        assert result == "parallel"
    
    def test_determine_path_unknown(self):
        """Test that unknown path defaults to parallel."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "unknown_path"
        
        result = determine_processing_path(state)
        assert result == "parallel"
    
    def test_determine_path_missing_processing(self):
        """Test that missing processing info defaults to parallel."""
        state = create_empty_state()
        del state["memory"]["processing"]
        
        result = determine_processing_path(state)
        assert result == "parallel"
    
    def test_determine_path_missing_path(self):
        """Test that missing path defaults to parallel."""
        state = create_empty_state()
        # processing dict exists but path key is missing
        
        result = determine_processing_path(state)
        assert result == "parallel"


class TestCheckProcessingComplete:
    """Test the check_processing_complete routing function."""
    
    def test_check_local_complete(self):
        """Test local processing completion check."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "local"
        state["memory"]["processing"]["local_completed"] = True
        
        result = check_processing_complete(state)
        assert result == "ready"
    
    def test_check_local_not_complete(self):
        """Test local processing not complete."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "local"
        state["memory"]["processing"]["local_completed"] = False
        
        result = check_processing_complete(state)
        assert result == "waiting"
    
    def test_check_api_complete(self):
        """Test API processing completion check."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "api"
        state["memory"]["processing"]["api_completed"] = True
        
        result = check_processing_complete(state)
        assert result == "ready"
    
    def test_check_api_not_complete(self):
        """Test API processing not complete."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "api"
        state["memory"]["processing"]["api_completed"] = False
        
        result = check_processing_complete(state)
        assert result == "waiting"
    
    def test_check_parallel_local_complete(self):
        """Test parallel processing with local complete."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "parallel"
        state["memory"]["processing"]["local_completed"] = True
        state["memory"]["processing"]["api_completed"] = False
        
        result = check_processing_complete(state)
        assert result == "ready"
    
    def test_check_parallel_api_complete(self):
        """Test parallel processing with API complete."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "parallel"
        state["memory"]["processing"]["local_completed"] = False
        state["memory"]["processing"]["api_completed"] = True
        
        result = check_processing_complete(state)
        assert result == "ready"
    
    def test_check_parallel_both_complete(self):
        """Test parallel processing with both complete."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "parallel"
        state["memory"]["processing"]["local_completed"] = True
        state["memory"]["processing"]["api_completed"] = True
        
        result = check_processing_complete(state)
        assert result == "ready"
    
    def test_check_parallel_none_complete(self):
        """Test parallel processing with neither complete."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "parallel"
        state["memory"]["processing"]["local_completed"] = False
        state["memory"]["processing"]["api_completed"] = False
        
        result = check_processing_complete(state)
        assert result == "waiting"
    
    def test_check_parallel_timeout(self):
        """Test parallel processing timeout handling."""
        state = create_empty_state()
        state["memory"]["processing"]["path"] = "parallel"
        state["memory"]["processing"]["local_completed"] = False
        state["memory"]["processing"]["api_completed"] = False
        state["memory"]["processing"]["start_time"] = time.time() - 15  # 15 seconds ago
        state["memory"]["processing"]["timeout"] = 10  # 10 second timeout
        
        result = check_processing_complete(state)
        assert result == "ready"  # Should proceed due to timeout
    
    def test_check_processing_missing_data(self):
        """Test processing check with missing data."""
        state = create_empty_state()
        del state["memory"]["processing"]
        
        result = check_processing_complete(state)
        assert result == "waiting"


class TestShouldSynthesizeSpeech:
    """Test the should_synthesize_speech routing function."""
    
    def test_should_synthesize_with_assistant_message(self):
        """Test synthesis with valid assistant message."""
        state = create_empty_state()
        state["messages"] = [
            create_message("user", "Hello"),
            create_message("assistant", "Hi there!")
        ]
        state["config"]["tts_enabled"] = True
        
        result = should_synthesize_speech(state)
        assert result == "synthesize"
    
    def test_should_synthesize_no_messages(self):
        """Test synthesis with no messages."""
        state = create_empty_state()
        state["messages"] = []
        
        result = should_synthesize_speech(state)
        assert result == "skip"
    
    def test_should_synthesize_no_assistant_message(self):
        """Test synthesis with no assistant message."""
        state = create_empty_state()
        state["messages"] = [create_message("user", "Hello")]
        
        result = should_synthesize_speech(state)
        assert result == "skip"
    
    def test_should_synthesize_empty_content(self):
        """Test synthesis with empty assistant message."""
        state = create_empty_state()
        state["messages"] = [
            create_message("user", "Hello"),
            create_message("assistant", "")
        ]
        
        result = should_synthesize_speech(state)
        assert result == "skip"
    
    def test_should_synthesize_tts_disabled(self):
        """Test synthesis with TTS disabled."""
        state = create_empty_state()
        state["messages"] = [
            create_message("user", "Hello"),
            create_message("assistant", "Hi there!")
        ]
        state["config"]["tts_enabled"] = False
        
        result = should_synthesize_speech(state)
        assert result == "skip"
    
    def test_should_synthesize_tts_default_enabled(self):
        """Test synthesis with TTS enabled by default."""
        state = create_empty_state()
        state["messages"] = [
            create_message("user", "Hello"),
            create_message("assistant", "Hi there!")
        ]
        # tts_enabled not specified, should default to True
        
        result = should_synthesize_speech(state)
        assert result == "synthesize"


class TestShouldUpdateMemory:
    """Test the should_update_memory routing function."""
    
    def test_should_update_with_new_messages(self):
        """Test memory update with new messages."""
        state = create_empty_state()
        state["messages"] = [
            create_message("user", "Hello"),
            create_message("assistant", "Hi there!")
        ]
        state["memory"]["last_stored_message_count"] = 0
        state["config"]["memory_enabled"] = True
        
        result = should_update_memory(state)
        assert result == "update"
    
    def test_should_update_insufficient_messages(self):
        """Test memory update with insufficient messages."""
        state = create_empty_state()
        state["messages"] = [create_message("user", "Hello")]  # Only one message
        
        result = should_update_memory(state)
        assert result == "skip"
    
    def test_should_update_memory_disabled(self):
        """Test memory update with memory disabled."""
        state = create_empty_state()
        state["messages"] = [
            create_message("user", "Hello"),
            create_message("assistant", "Hi there!")
        ]
        state["config"]["memory_enabled"] = False
        
        result = should_update_memory(state)
        assert result == "skip"
    
    def test_should_update_no_new_messages(self):
        """Test memory update with no new messages."""
        state = create_empty_state()
        state["messages"] = [
            create_message("user", "Hello"),
            create_message("assistant", "Hi there!")
        ]
        state["memory"]["last_stored_message_count"] = 2  # Already stored
        
        result = should_update_memory(state)
        assert result == "skip"
    
    def test_should_update_memory_default_enabled(self):
        """Test memory update with memory enabled by default."""
        state = create_empty_state()
        state["messages"] = [
            create_message("user", "Hello"),
            create_message("assistant", "Hi there!")
        ]
        state["memory"]["last_stored_message_count"] = 0
        # memory_enabled not specified, should default to True
        
        result = should_update_memory(state)
        assert result == "update"


class TestRoutingUtilities:
    """Test routing utility functions."""
    
    def test_get_routing_function_valid(self):
        """Test getting a valid routing function."""
        func = get_routing_function("should_process")
        assert func is should_process
    
    def test_get_routing_function_invalid(self):
        """Test getting an invalid routing function."""
        func = get_routing_function("nonexistent_function")
        assert func is None
    
    def test_list_routing_functions(self):
        """Test listing all routing functions."""
        functions = list_routing_functions()
        expected_functions = [
            "should_process",
            "determine_processing_path",
            "check_processing_complete",
            "should_synthesize_speech",
            "should_update_memory"
        ]
        
        for func_name in expected_functions:
            assert func_name in functions


class TestRoutingErrorHandling:
    """Test error handling in routing functions."""
    
    def test_should_process_with_exception(self):
        """Test should_process error handling."""
        # Create malformed state that will cause exception
        state = {"activation": None}  # This will cause TypeError
        
        result = should_process(state)
        assert result == "end"  # Should default to safe option
    
    def test_determine_path_with_exception(self):
        """Test determine_processing_path error handling."""
        state = {"memory": None}  # This will cause TypeError
        
        result = determine_processing_path(state)
        assert result == "parallel"  # Should default to parallel
    
    def test_check_processing_complete_with_exception(self):
        """Test check_processing_complete error handling."""
        state = {"memory": {"processing": None}}  # This will cause TypeError
        
        result = check_processing_complete(state)
        assert result == "waiting"  # Should default to waiting
    
    def test_should_synthesize_speech_with_exception(self):
        """Test should_synthesize_speech error handling."""
        state = {"messages": None}  # This will cause TypeError
        
        result = should_synthesize_speech(state)
        assert result == "skip"  # Should default to skip
    
    def test_should_update_memory_with_exception(self):
        """Test should_update_memory error handling."""
        state = {"messages": None}  # This will cause TypeError
        
        result = should_update_memory(state)
        assert result == "update"  # Should default to update when error occurs


if __name__ == "__main__":
    pytest.main([__file__])