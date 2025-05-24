#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory State Management Integration Tests

This module tests the state management aspects of memory integration,
including state serialization, cross-session persistence, and state consistency.
"""
# TASK-REF: INT_003 - Memory System Integration
# CONCEPT-REF: CON-VANTA-002 - Memory Engine
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration

import pytest
import json
from datetime import datetime
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..', 'src'))

from langgraph.state.vanta_state import (
    VANTAState, 
    create_empty_state, 
    serialize_state, 
    deserialize_state,
    update_state
)
from langchain_core.messages import HumanMessage, AIMessage


class TestMemoryStateManagement:
    """Test suite for memory state management."""
    
    @pytest.fixture
    def memory_enhanced_state(self):
        """Create a state with memory integration fields."""
        state = create_empty_state()
        state["memory"] = {
            **state["memory"],
            "retrieved_context": {
                "query": "test query",
                "results": [
                    {"memory_id": "mem_001", "content": "Test context", "relevance_score": 0.8}
                ],
                "retrieval_time": 0.05,
                "timestamp": datetime.now(),
                "memory_references": ["mem_001"],
                "context_tokens": 25,
                "available_tokens": 3975
            },
            "conversation_history": [
                {
                    "memory_id": "mem_001",
                    "timestamp": datetime.now(),
                    "user_message": "Hello",
                    "assistant_message": "Hi there!"
                }
            ],
            "memory_operations": [
                {
                    "operation": "store",
                    "memory_id": "mem_001",
                    "timestamp": datetime.now(),
                    "processing_time": 0.02
                }
            ],
            "conversation_summary": "Brief conversation about greetings",
            "memory_references": ["mem_001"],
            "context_window_size": 3975,
            "last_retrieval": datetime.now(),
            "last_storage_time": datetime.now(),
            "status": "context_retrieved"
        }
        return state
    
    def test_memory_state_serialization(self, memory_enhanced_state):
        """Test serialization of memory-enhanced state."""
        # Serialize the state
        serialized = serialize_state(memory_enhanced_state)
        
        # Verify serialization
        assert isinstance(serialized, dict)
        assert "memory" in serialized
        
        # Check memory fields are serialized
        memory_data = serialized["memory"]
        assert "retrieved_context" in memory_data
        assert "conversation_history" in memory_data
        assert "memory_operations" in memory_data
        
        # Check datetime serialization
        assert "last_retrieval" in memory_data
        assert isinstance(memory_data["last_retrieval"], str)  # Should be ISO format
        
        # Verify JSON serializable
        json_str = json.dumps(serialized)
        assert len(json_str) > 0
    
    def test_memory_state_deserialization(self, memory_enhanced_state):
        """Test deserialization of memory-enhanced state."""
        # Serialize then deserialize
        serialized = serialize_state(memory_enhanced_state)
        deserialized = deserialize_state(serialized)
        
        # Verify structure is preserved
        assert "memory" in deserialized
        memory_data = deserialized["memory"]
        
        assert "retrieved_context" in memory_data
        assert "conversation_history" in memory_data
        assert "memory_operations" in memory_data
        
        # Check datetime deserialization
        assert "last_retrieval" in memory_data
        assert isinstance(memory_data["last_retrieval"], datetime)
    
    def test_memory_state_updates(self, memory_enhanced_state):
        """Test updating memory state with new information."""
        # Create memory updates
        memory_updates = {
            "memory": {
                "retrieved_context": {
                    "query": "updated query",
                    "results": [
                        {"memory_id": "mem_002", "content": "New context", "relevance_score": 0.9}
                    ]
                },
                "status": "updated"
            }
        }
        
        # Update state
        updated_state = update_state(memory_enhanced_state, memory_updates)
        
        # Verify updates are applied
        assert updated_state["memory"]["status"] == "updated"
        assert updated_state["memory"]["retrieved_context"]["query"] == "updated query"
        
        # Verify other memory fields are preserved
        assert "conversation_history" in updated_state["memory"]
        assert "memory_operations" in updated_state["memory"]
    
    def test_memory_state_consistency(self, memory_enhanced_state):
        """Test state consistency across operations."""
        original_history_length = len(memory_enhanced_state["memory"]["conversation_history"])
        
        # Add new conversation
        new_conversation = {
            "memory_id": "mem_002",
            "timestamp": datetime.now(),
            "user_message": "How are you?",
            "assistant_message": "I'm doing well!"
        }
        
        updates = {
            "memory": {
                "conversation_history": memory_enhanced_state["memory"]["conversation_history"] + [new_conversation]
            }
        }
        
        updated_state = update_state(memory_enhanced_state, updates)
        
        # Verify consistency
        new_history_length = len(updated_state["memory"]["conversation_history"])
        assert new_history_length == original_history_length + 1
        
        # Verify the new conversation is properly added
        last_conversation = updated_state["memory"]["conversation_history"][-1]
        assert last_conversation["memory_id"] == "mem_002"
        assert last_conversation["user_message"] == "How are you?"
    
    def test_memory_references_tracking(self, memory_enhanced_state):
        """Test tracking of memory references in state."""
        # Verify initial memory references
        memory_refs = memory_enhanced_state["memory"]["memory_references"]
        assert isinstance(memory_refs, list)
        assert "mem_001" in memory_refs
        
        # Add new memory reference
        updates = {
            "memory": {
                "memory_references": memory_refs + ["mem_002", "mem_003"]
            }
        }
        
        updated_state = update_state(memory_enhanced_state, updates)
        
        # Verify references are updated
        new_refs = updated_state["memory"]["memory_references"]
        assert len(new_refs) == 3
        assert "mem_002" in new_refs
        assert "mem_003" in new_refs
    
    def test_memory_context_window_management(self, memory_enhanced_state):
        """Test context window size management."""
        # Verify initial context window
        initial_window = memory_enhanced_state["memory"]["context_window_size"]
        assert initial_window == 3975
        
        # Simulate context usage
        context_usage = 500
        new_window_size = initial_window - context_usage
        
        updates = {
            "memory": {
                "context_window_size": new_window_size,
                "retrieved_context": {
                    **memory_enhanced_state["memory"]["retrieved_context"],
                    "context_tokens": memory_enhanced_state["memory"]["retrieved_context"]["context_tokens"] + context_usage,
                    "available_tokens": new_window_size
                }
            }
        }
        
        updated_state = update_state(memory_enhanced_state, updates)
        
        # Verify context window management
        assert updated_state["memory"]["context_window_size"] == new_window_size
        assert updated_state["memory"]["retrieved_context"]["available_tokens"] == new_window_size
    
    def test_memory_operations_tracking(self, memory_enhanced_state):
        """Test tracking of memory operations."""
        initial_ops = memory_enhanced_state["memory"]["memory_operations"]
        assert len(initial_ops) == 1
        assert initial_ops[0]["operation"] == "store"
        
        # Add new operation
        new_operation = {
            "operation": "retrieve",
            "memory_id": "mem_002",
            "timestamp": datetime.now(),
            "processing_time": 0.03
        }
        
        updates = {
            "memory": {
                "memory_operations": initial_ops + [new_operation]
            }
        }
        
        updated_state = update_state(memory_enhanced_state, updates)
        
        # Verify operation tracking
        operations = updated_state["memory"]["memory_operations"]
        assert len(operations) == 2
        assert operations[-1]["operation"] == "retrieve"
        assert operations[-1]["memory_id"] == "mem_002"
    
    def test_conversation_summary_management(self, memory_enhanced_state):
        """Test conversation summary state management."""
        initial_summary = memory_enhanced_state["memory"]["conversation_summary"]
        assert initial_summary == "Brief conversation about greetings"
        
        # Update summary
        new_summary = "Extended conversation about greetings and AI capabilities"
        
        updates = {
            "memory": {
                "conversation_summary": new_summary,
                "last_summarization_time": datetime.now(),
                "summarization_status": "completed"
            }
        }
        
        updated_state = update_state(memory_enhanced_state, updates)
        
        # Verify summary management
        assert updated_state["memory"]["conversation_summary"] == new_summary
        assert "last_summarization_time" in updated_state["memory"]
        assert updated_state["memory"]["summarization_status"] == "completed"
    
    def test_memory_error_state_handling(self, memory_enhanced_state):
        """Test handling of memory error states."""
        # Simulate memory error
        error_updates = {
            "memory": {
                "status": "retrieval_error",
                "error": "Memory system temporarily unavailable",
                "retrieved_context": {"error": "System error"},
                "last_error_time": datetime.now()
            }
        }
        
        updated_state = update_state(memory_enhanced_state, error_updates)
        
        # Verify error state handling
        assert updated_state["memory"]["status"] == "retrieval_error"
        assert "error" in updated_state["memory"]
        assert "last_error_time" in updated_state["memory"]
        
        # Verify other memory data is preserved
        assert "conversation_history" in updated_state["memory"]
        assert len(updated_state["memory"]["conversation_history"]) > 0
    
    def test_cross_session_state_persistence(self, memory_enhanced_state):
        """Test state persistence across sessions."""
        # Simulate saving state at end of session
        serialized_state = serialize_state(memory_enhanced_state)
        
        # Simulate loading state in new session
        restored_state = deserialize_state(serialized_state)
        
        # Verify memory data is preserved
        assert restored_state["memory"]["conversation_summary"] == memory_enhanced_state["memory"]["conversation_summary"]
        assert len(restored_state["memory"]["conversation_history"]) == len(memory_enhanced_state["memory"]["conversation_history"])
        assert restored_state["memory"]["memory_references"] == memory_enhanced_state["memory"]["memory_references"]
        
        # Verify timestamps are properly restored
        assert isinstance(restored_state["memory"]["last_retrieval"], datetime)
        assert isinstance(restored_state["memory"]["last_storage_time"], datetime)
    
    def test_memory_state_validation(self, memory_enhanced_state):
        """Test validation of memory state structure."""
        # Verify required memory fields exist
        memory_data = memory_enhanced_state["memory"]
        
        required_fields = [
            "retrieved_context",
            "conversation_history", 
            "memory_operations",
            "memory_references",
            "status"
        ]
        
        for field in required_fields:
            assert field in memory_data, f"Required field '{field}' missing from memory state"
        
        # Verify field types
        assert isinstance(memory_data["retrieved_context"], dict)
        assert isinstance(memory_data["conversation_history"], list)
        assert isinstance(memory_data["memory_operations"], list)
        assert isinstance(memory_data["memory_references"], list)
        assert isinstance(memory_data["status"], str)
    
    def test_memory_state_size_limits(self, memory_enhanced_state):
        """Test memory state size management."""
        # Add many conversations to test size limits
        large_history = []
        for i in range(100):
            large_history.append({
                "memory_id": f"mem_{i:03d}",
                "timestamp": datetime.now(),
                "user_message": f"User message {i}",
                "assistant_message": f"Assistant response {i}"
            })
        
        updates = {
            "memory": {
                "conversation_history": large_history
            }
        }
        
        updated_state = update_state(memory_enhanced_state, updates)
        
        # Verify large history is stored
        assert len(updated_state["memory"]["conversation_history"]) == 100
        
        # Test serialization with large state
        serialized = serialize_state(updated_state)
        assert isinstance(serialized, dict)
        
        # Verify can be deserialized
        deserialized = deserialize_state(serialized)
        assert len(deserialized["memory"]["conversation_history"]) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])