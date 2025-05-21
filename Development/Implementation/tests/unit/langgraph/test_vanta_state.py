#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the VANTA LangGraph state definition.

These tests verify the functionality of the VANTAState TypedDict, including
state creation, updating, serialization/deserialization, and utility functions.
"""
import pytest
import json
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.langgraph.state.vanta_state import (
    VANTAState,
    ActivationMode,
    ActivationStatus,
    ProcessingPath,
    create_empty_state,
    update_nested_dict,
    update_state,
    serialize_state,
    deserialize_state,
)


class TestVANTAState:
    """Tests for the VANTAState TypedDict and related functions."""

    def test_create_empty_state(self):
        """Test creation of an empty state with default values."""
        state = create_empty_state()
        
        # Verify the structure of the created state
        assert "messages" in state
        assert "audio" in state
        assert "memory" in state
        assert "config" in state
        assert "activation" in state
        assert "processing" in state
        
        # Check specific default values
        assert state["messages"] == []
        assert state["config"]["activation_mode"] == ActivationMode.WAKE_WORD
        assert state["activation"]["status"] == ActivationStatus.INACTIVE
        assert state["processing"]["path"] is None

    def test_update_nested_dict(self):
        """Test the nested dictionary update function."""
        original = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3
            }
        }
        
        updates = {
            "a": 10,
            "b": {
                "d": 30
            }
        }
        
        result = update_nested_dict(original, updates)
        
        # Check that the updates were applied correctly
        assert result["a"] == 10
        assert result["b"]["c"] == 2  # Value should be preserved from original
        assert result["b"]["d"] == 30  # Value should be updated

    def test_update_state(self):
        """Test the state update function."""
        state = create_empty_state()
        
        # Create some updates
        updates = {
            "messages": [HumanMessage(content="Hello")],
            "audio": {
                "current_audio": "audio_data",
                "metadata": {
                    "sample_rate": 16000
                }
            },
            "activation": {
                "status": ActivationStatus.LISTENING
            }
        }
        
        updated_state = update_state(state, updates)
        
        # Check that updates were applied
        assert len(updated_state["messages"]) == 1
        assert updated_state["messages"][0].content == "Hello"
        assert updated_state["audio"]["current_audio"] == "audio_data"
        assert updated_state["audio"]["metadata"]["sample_rate"] == 16000
        assert updated_state["activation"]["status"] == ActivationStatus.LISTENING
        
        # Check that unmodified fields are preserved
        assert updated_state["memory"] == state["memory"]
        assert updated_state["config"] == state["config"]
        assert updated_state["processing"] == state["processing"]

    def test_message_serialization_deserialization(self):
        """Test that messages are properly serialized and deserialized."""
        state = create_empty_state()
        
        # Add messages
        state["messages"] = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Hello, how are you?"),
            AIMessage(content="I'm doing well, thank you!")
        ]
        
        # Serialize the state
        serialized = serialize_state(state)
        
        # Check that messages were serialized properly
        assert isinstance(serialized["messages"], list)
        assert len(serialized["messages"]) == 3
        assert serialized["messages"][0]["type"] == "SystemMessage"
        assert serialized["messages"][1]["type"] == "HumanMessage"
        assert serialized["messages"][2]["type"] == "AIMessage"
        
        # Deserialize the state
        deserialized = deserialize_state(serialized)
        
        # Check that messages were deserialized properly
        assert len(deserialized["messages"]) == 3
        assert isinstance(deserialized["messages"][0], SystemMessage)
        assert isinstance(deserialized["messages"][1], HumanMessage)
        assert isinstance(deserialized["messages"][2], AIMessage)
        assert deserialized["messages"][0].content == "You are a helpful assistant."
        assert deserialized["messages"][1].content == "Hello, how are you?"
        assert deserialized["messages"][2].content == "I'm doing well, thank you!"

    def test_datetime_serialization_deserialization(self):
        """Test that datetime objects are properly serialized and deserialized."""
        state = create_empty_state()
        
        # Add timestamp
        now = datetime.now()
        state["activation"]["last_activation_time"] = now
        
        # Serialize the state
        serialized = serialize_state(state)
        
        # Check that datetime was serialized to string
        assert isinstance(serialized["activation"]["last_activation_time"], str)
        
        # Deserialize the state
        deserialized = deserialize_state(serialized)
        
        # Check that datetime was deserialized back to datetime
        assert isinstance(deserialized["activation"]["last_activation_time"], datetime)
        assert deserialized["activation"]["last_activation_time"] == now

    def test_json_serialization(self):
        """Test that the state can be serialized to JSON."""
        state = create_empty_state()
        
        # Add a message and timestamp
        state["messages"] = [HumanMessage(content="Hello!")]
        state["activation"]["last_activation_time"] = datetime.now()
        
        # Serialize to a dictionary
        serialized = serialize_state(state)
        
        # Verify that this can be converted to JSON
        json_str = json.dumps(serialized)
        
        # Verify that we can parse it back
        parsed = json.loads(json_str)
        
        # Check basic structure intact
        assert "messages" in parsed
        assert "audio" in parsed
        assert "memory" in parsed
        assert "config" in parsed
        assert "activation" in parsed
        assert "processing" in parsed
        
        # Check that message was serialized properly
        assert parsed["messages"][0]["type"] == "HumanMessage"
        assert parsed["messages"][0]["content"] == "Hello!"

    def test_enums(self):
        """Test that enums have the correct values."""
        # Test ActivationMode enum
        assert ActivationMode.CONTINUOUS == "continuous"
        assert ActivationMode.WAKE_WORD == "wake_word"
        assert ActivationMode.SCHEDULED == "scheduled"
        
        # Test ActivationStatus enum
        assert ActivationStatus.INACTIVE == "inactive"
        assert ActivationStatus.LISTENING == "listening"
        assert ActivationStatus.PROCESSING == "processing"
        assert ActivationStatus.SPEAKING == "speaking"
        
        # Test ProcessingPath enum
        assert ProcessingPath.LOCAL == "local"
        assert ProcessingPath.API == "api"
        assert ProcessingPath.PARALLEL == "parallel"
        assert ProcessingPath.STAGED == "staged"

    def test_complete_round_trip(self):
        """Test a complete serialization and deserialization round trip."""
        # Create a state with various types of data
        original_state = create_empty_state()
        original_state["messages"] = [
            SystemMessage(content="System message"),
            HumanMessage(content="User message"),
            AIMessage(content="Assistant message")
        ]
        original_state["audio"]["current_audio"] = "audio_data_bytes"
        original_state["audio"]["last_transcription"] = "Hello, world!"
        original_state["memory"]["retrieved_context"] = {"query": "test", "results": ["result1", "result2"]}
        original_state["config"]["model_settings"]["local"]["temperature"] = 0.5
        original_state["activation"]["status"] = ActivationStatus.PROCESSING
        original_state["activation"]["last_activation_time"] = datetime.now()
        original_state["processing"]["path"] = ProcessingPath.PARALLEL
        
        # Serialize
        serialized = serialize_state(original_state)
        
        # Convert to JSON and back (to simulate storage)
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)
        
        # Deserialize
        deserialized = deserialize_state(parsed)
        
        # Check that the structure is preserved
        assert len(deserialized["messages"]) == len(original_state["messages"])
        assert deserialized["audio"]["current_audio"] == original_state["audio"]["current_audio"]
        assert deserialized["audio"]["last_transcription"] == original_state["audio"]["last_transcription"]
        assert deserialized["memory"]["retrieved_context"] == original_state["memory"]["retrieved_context"]
        assert deserialized["config"]["model_settings"]["local"]["temperature"] == original_state["config"]["model_settings"]["local"]["temperature"]
        assert deserialized["activation"]["status"] == original_state["activation"]["status"]
        
        # DateTime will be serialized to string and back to datetime, so check format matches
        assert isinstance(deserialized["activation"]["last_activation_time"], datetime)
        assert deserialized["activation"]["last_activation_time"].isoformat() == original_state["activation"]["last_activation_time"].isoformat()
        
        assert deserialized["processing"]["path"] == original_state["processing"]["path"]