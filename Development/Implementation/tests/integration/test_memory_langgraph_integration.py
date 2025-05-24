#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Tests for Memory System LangGraph Integration

This module tests the complete integration of the memory system with the LangGraph workflow,
ensuring that memory operations work correctly within the conversation flow.
"""
# TASK-REF: INT_003 - Memory System Integration
# CONCEPT-REF: CON-VANTA-002 - Memory Engine
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch

from langchain_core.messages import HumanMessage, AIMessage

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..', 'src'))

from langgraph.state.vanta_state import VANTAState, ActivationStatus, create_empty_state
from langgraph.nodes.memory_nodes import (
    retrieve_memory_context_node,
    store_conversation_node,
    summarize_conversation_node,
    initialize_memory_system,
    get_memory_system
)
from langgraph.routing import should_summarize_conversation
from memory.core import MemorySystem


class TestMemoryLangGraphIntegration:
    """Test suite for memory system LangGraph integration."""
    
    @pytest.fixture
    def mock_memory_system(self):
        """Create a mock memory system for testing."""
        mock_system = Mock(spec=MemorySystem)
        mock_working_memory = Mock()
        mock_system.working_memory = mock_working_memory
        return mock_system
    
    @pytest.fixture
    def sample_state(self):
        """Create a sample VANTA state for testing."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [
            HumanMessage(content="Hello, how are you?"),
        ]
        return state
    
    @pytest.fixture
    def conversation_state(self):
        """Create a state with conversation history."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [
            HumanMessage(content="Hello, how are you?"),
            AIMessage(content="I'm doing well, thank you! How can I help you today?"),
            HumanMessage(content="Can you help me understand memory systems?"),
        ]
        state["memory"]["conversation_history"] = [
            {
                "memory_id": "mem_001",
                "timestamp": datetime.now(),
                "user_message": "Previous question about AI",
                "assistant_message": "Previous response about AI capabilities"
            }
        ]
        return state
    
    @pytest.mark.asyncio
    async def test_retrieve_memory_context_integration(self, mock_memory_system, sample_state):
        """Test memory context retrieval in LangGraph workflow."""
        # Setup mock
        mock_context_results = {
            "results": [
                {
                    "memory_id": "mem_001",
                    "content": "Previous conversation about greetings",
                    "relevance_score": 0.8
                }
            ]
        }
        mock_memory_system.working_memory.retrieve_context.return_value = mock_context_results
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            # Test memory context retrieval
            result = await retrieve_memory_context_node(sample_state)
            
            # Verify the results
            assert "memory" in result
            memory_data = result["memory"]
            assert "retrieved_context" in memory_data
            assert "status" in memory_data
            assert memory_data["status"] == "context_retrieved"
            
            # Verify memory system was called
            mock_memory_system.working_memory.retrieve_context.assert_called_once()
            call_args = mock_memory_system.working_memory.retrieve_context.call_args[1]
            assert call_args["query"] == "Hello, how are you?"
            assert call_args["max_results"] == 5
    
    @pytest.mark.asyncio
    async def test_retrieve_memory_context_no_input(self, mock_memory_system):
        """Test memory context retrieval with no user input."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.INACTIVE
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await retrieve_memory_context_node(state)
            
            assert "memory" in result
            assert result["memory"]["status"] == "no_input_to_process"
            mock_memory_system.working_memory.retrieve_context.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_store_conversation_integration(self, mock_memory_system, conversation_state):
        """Test conversation storage in LangGraph workflow."""
        # Setup mock
        mock_memory_system.working_memory.store_conversation.return_value = "mem_002"
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            # Test conversation storage
            result = await store_conversation_node(conversation_state)
            
            # Verify the results
            assert "memory" in result
            memory_data = result["memory"]
            assert "last_storage_status" in memory_data
            assert memory_data["last_storage_status"] == "success"
            assert "conversation_history" in memory_data
            assert "memory_operations" in memory_data
            
            # Verify conversation was stored
            mock_memory_system.working_memory.store_conversation.assert_called_once()
            stored_message = mock_memory_system.working_memory.store_conversation.call_args[0][0]
            assert stored_message["user_message"] == "Can you help me understand memory systems?"
            assert stored_message["assistant_message"] == "I'm doing well, thank you! How can I help you today?"
    
    @pytest.mark.asyncio
    async def test_store_conversation_insufficient_messages(self, mock_memory_system):
        """Test conversation storage with insufficient messages."""
        state = create_empty_state()
        state["messages"] = [HumanMessage(content="Hello")]  # Only one message
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await store_conversation_node(state)
            
            assert "memory" in result
            assert result["memory"]["last_storage_status"] == "insufficient_messages"
            mock_memory_system.working_memory.store_conversation.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_summarize_conversation_integration(self, mock_memory_system, conversation_state):
        """Test conversation summarization in LangGraph workflow."""
        # Setup state with many conversations
        long_history = []
        for i in range(12):  # Exceed threshold of 10
            long_history.append({
                "memory_id": f"mem_{i:03d}",
                "timestamp": datetime.now(),
                "user_message": f"User message {i}",
                "assistant_message": f"Assistant response {i}"
            })
        conversation_state["memory"]["conversation_history"] = long_history
        conversation_state["config"]["summarization_threshold"] = 10
        
        # Setup mock
        mock_memory_system.working_memory.generate_summary.return_value = "Conversation about various topics including greetings and AI systems."
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            # Test summarization
            result = await summarize_conversation_node(conversation_state)
            
            # Verify the results
            assert "memory" in result
            memory_data = result["memory"]
            assert "summarization_status" in memory_data
            assert memory_data["summarization_status"] == "completed"
            assert "conversation_summary" in memory_data
            assert "conversation_history" in memory_data
            assert len(memory_data["conversation_history"]) == 5  # Keep last 5 messages
            
            # Verify summarization was called
            mock_memory_system.working_memory.generate_summary.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summarize_conversation_not_needed(self, mock_memory_system, conversation_state):
        """Test that summarization is skipped when not needed."""
        # State with few conversations
        conversation_state["config"]["summarization_threshold"] = 10
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await summarize_conversation_node(conversation_state)
            
            assert "memory" in result
            assert result["memory"]["summarization_status"] == "not_needed"
            mock_memory_system.working_memory.generate_summary.assert_not_called()
    
    def test_should_summarize_conversation_routing(self):
        """Test the routing function for conversation summarization."""
        # Test with history exceeding threshold
        state_long = create_empty_state()
        state_long["memory"]["conversation_history"] = [{"id": i} for i in range(12)]
        state_long["config"]["summarization_threshold"] = 10
        
        result = should_summarize_conversation(state_long)
        assert result == "summarize"
        
        # Test with history below threshold
        state_short = create_empty_state()
        state_short["memory"]["conversation_history"] = [{"id": i} for i in range(5)]
        state_short["config"]["summarization_threshold"] = 10
        
        result = should_summarize_conversation(state_short)
        assert result == "continue"
    
    @pytest.mark.asyncio
    async def test_memory_error_handling(self, mock_memory_system, sample_state):
        """Test memory system error handling."""
        # Setup mock to raise exception
        mock_memory_system.working_memory.retrieve_context.side_effect = Exception("Memory system error")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await retrieve_memory_context_node(sample_state)
            
            # Verify error handling
            assert "memory" in result
            assert "error" in result["memory"]
            assert "status" in result["memory"]
            assert result["memory"]["status"] == "retrieval_error"
    
    @pytest.mark.asyncio
    async def test_memory_context_token_estimation(self, mock_memory_system, sample_state):
        """Test token count estimation for memory context."""
        # Setup mock with detailed context
        mock_context_results = {
            "results": [
                {
                    "memory_id": "mem_001",
                    "content": "This is a long conversation about artificial intelligence and machine learning systems that should consume several tokens when processed.",
                    "relevance_score": 0.9
                }
            ]
        }
        mock_memory_system.working_memory.retrieve_context.return_value = mock_context_results
        sample_state["config"]["context_window_size"] = 4000
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await retrieve_memory_context_node(sample_state)
            
            # Verify token estimation
            assert "memory" in result
            memory_data = result["memory"]
            assert "context_window_size" in memory_data
            assert "retrieved_context" in memory_data
            
            context = memory_data["retrieved_context"]
            assert "context_tokens" in context
            assert "available_tokens" in context
            assert context["context_tokens"] > 0
            assert context["available_tokens"] < 4000  # Should be reduced by context size
    
    @pytest.mark.asyncio
    async def test_complete_memory_integration_workflow(self, mock_memory_system):
        """Test complete memory integration workflow."""
        # Setup mocks
        mock_memory_system.working_memory.retrieve_context.return_value = {
            "results": [{"memory_id": "mem_001", "content": "Previous context"}]
        }
        mock_memory_system.working_memory.store_conversation.return_value = "mem_002"
        mock_memory_system.working_memory.generate_summary.return_value = "Summary of conversation"
        
        # Create state for complete workflow
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="How are you?"),
        ]
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            # Step 1: Retrieve memory context
            state = {**state, **await retrieve_memory_context_node(state)}
            assert state["memory"]["status"] == "context_retrieved"
            
            # Step 2: Store conversation
            state = {**state, **await store_conversation_node(state)}
            assert state["memory"]["last_storage_status"] == "success"
            
            # Step 3: Check if summarization is needed (it shouldn't be for short history)
            routing_result = should_summarize_conversation(state)
            assert routing_result == "continue"  # Short conversation, no summarization needed
    
    @pytest.mark.asyncio
    async def test_memory_performance_tracking(self, mock_memory_system, sample_state):
        """Test that memory operations track performance metrics."""
        mock_memory_system.working_memory.retrieve_context.return_value = {"results": []}
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await retrieve_memory_context_node(sample_state)
            
            # Verify performance tracking
            assert "memory" in result
            memory_data = result["memory"]
            assert "retrieved_context" in memory_data
            
            context = memory_data["retrieved_context"]
            assert "retrieval_time" in context
            assert "timestamp" in context
            assert context["retrieval_time"] >= 0
    
    def test_memory_integration_configuration(self):
        """Test memory integration configuration parameters."""
        state = create_empty_state()
        
        # Test default configuration values
        assert "config" in state
        assert state["config"]["activation_mode"] is not None
        
        # Test memory-specific configuration
        state["config"]["summarization_threshold"] = 15
        state["config"]["context_window_size"] = 8000
        
        routing_result = should_summarize_conversation(state)
        assert routing_result == "continue"  # Empty history, no summarization


# Performance and load testing
class TestMemoryIntegrationPerformance:
    """Performance tests for memory integration."""
    
    @pytest.mark.asyncio
    async def test_memory_retrieval_performance(self, mock_memory_system):
        """Test memory retrieval performance under load."""
        import time
        
        # Setup mock
        mock_memory_system.working_memory.retrieve_context.return_value = {
            "results": [{"memory_id": f"mem_{i}", "content": f"Content {i}"} for i in range(100)]
        }
        
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [HumanMessage(content="Test query")]
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            # Run multiple retrievals
            start_time = time.time()
            for _ in range(10):
                await retrieve_memory_context_node(state)
            elapsed_time = time.time() - start_time
            
            # Verify reasonable performance (should be fast with mocks)
            assert elapsed_time < 1.0  # Should complete in under 1 second
    
    @pytest.mark.asyncio
    async def test_memory_storage_batch_performance(self, mock_memory_system):
        """Test memory storage performance with multiple conversations."""
        mock_memory_system.working_memory.store_conversation.return_value = "mem_batch"
        
        # Create state with multiple message pairs
        state = create_empty_state()
        messages = []
        for i in range(20):  # 10 conversation pairs
            messages.extend([
                HumanMessage(content=f"User message {i}"),
                AIMessage(content=f"Assistant response {i}")
            ])
        state["messages"] = messages
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await store_conversation_node(state)
            
            # Verify storage completed successfully
            assert result["memory"]["last_storage_status"] == "success"
            mock_memory_system.working_memory.store_conversation.assert_called_once()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])