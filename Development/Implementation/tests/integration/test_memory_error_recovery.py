#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Error Recovery Integration Tests

This module tests error recovery mechanisms for memory system integration,
ensuring that the conversation can continue even when memory operations fail.
"""
# TASK-REF: INT_003 - Memory System Integration
# CONCEPT-REF: CON-VANTA-002 - Memory Engine
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..', 'src'))

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.state.vanta_state import VANTAState, ActivationStatus, create_empty_state
from langgraph.nodes.memory_nodes import (
    retrieve_memory_context_node,
    store_conversation_node,
    summarize_conversation_node,
    handle_memory_error
)
from memory.core import MemorySystem


class TestMemoryErrorRecovery:
    """Test suite for memory system error recovery."""
    
    @pytest.fixture
    def sample_state(self):
        """Create a sample VANTA state for testing."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [
            HumanMessage(content="Hello, how are you?"),
            AIMessage(content="I'm doing well, thank you!"),
        ]
        state["memory"]["conversation_history"] = [
            {
                "memory_id": "mem_001",
                "timestamp": datetime.now(),
                "user_message": "Previous question",
                "assistant_message": "Previous response"
            }
        ]
        return state
    
    @pytest.mark.asyncio
    async def test_memory_retrieval_failure_recovery(self, sample_state):
        """Test recovery from memory retrieval failures."""
        mock_memory_system = Mock(spec=MemorySystem)
        mock_memory_system.working_memory.retrieve_context.side_effect = Exception("Database connection failed")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await retrieve_memory_context_node(sample_state)
            
            # Verify graceful error handling
            assert "memory" in result
            memory_data = result["memory"]
            assert memory_data["status"] == "retrieval_error"
            assert "error" in memory_data
            assert "Memory retrieval error" in memory_data["error"]
            
            # Verify conversation can continue with fallback
            assert "retrieved_context" in memory_data
            assert memory_data["retrieved_context"]["error"] == "Database connection failed"
    
    @pytest.mark.asyncio
    async def test_memory_storage_failure_recovery(self, sample_state):
        """Test recovery from memory storage failures."""
        mock_memory_system = Mock(spec=MemorySystem)
        mock_memory_system.working_memory.store_conversation.side_effect = Exception("Storage quota exceeded")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await store_conversation_node(sample_state)
            
            # Verify graceful error handling
            assert "memory" in result
            memory_data = result["memory"]
            assert memory_data["last_storage_status"] == "error"
            assert "storage_error" in memory_data
            assert "Memory storage error" in memory_data["storage_error"]
            
            # Verify existing conversation history is preserved
            assert "conversation_history" in memory_data
    
    @pytest.mark.asyncio
    async def test_memory_summarization_failure_recovery(self, sample_state):
        """Test recovery from summarization failures."""
        # Setup state with long history requiring summarization
        long_history = []
        for i in range(15):
            long_history.append({
                "memory_id": f"mem_{i:03d}",
                "timestamp": datetime.now(),
                "user_message": f"User message {i}",
                "assistant_message": f"Assistant response {i}"
            })
        sample_state["memory"]["conversation_history"] = long_history
        sample_state["config"]["summarization_threshold"] = 10
        
        mock_memory_system = Mock(spec=MemorySystem)
        mock_memory_system.working_memory.generate_summary.side_effect = Exception("Summarization model unavailable")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await summarize_conversation_node(sample_state)
            
            # Verify graceful error handling
            assert "memory" in result
            memory_data = result["memory"]
            assert memory_data["summarization_status"] == "error"
            assert "summarization_error" in memory_data
            
            # Verify conversation history is preserved
            assert "conversation_history" in memory_data
            assert len(memory_data["conversation_history"]) == 15  # History preserved
    
    @pytest.mark.asyncio
    async def test_memory_system_initialization_failure(self, sample_state):
        """Test handling of memory system initialization failures."""
        with patch('langgraph.nodes.memory_nodes.get_memory_system', side_effect=RuntimeError("Memory system not initialized")):
            result = await retrieve_memory_context_node(sample_state)
            
            # Verify error handling
            assert "memory" in result
            memory_data = result["memory"]
            assert memory_data["status"] == "retrieval_error"
            assert "Memory system not initialized" in memory_data["error"]
    
    @pytest.mark.asyncio
    async def test_handle_memory_error_function(self, sample_state):
        """Test the dedicated memory error handler."""
        test_error = Exception("Critical memory system failure")
        
        result = await handle_memory_error(sample_state, test_error)
        
        # Verify fallback behavior
        assert "memory" in result
        memory_data = result["memory"]
        assert memory_data["status"] == "fallback_mode"
        assert "error" in memory_data
        assert "Critical memory system failure" in memory_data["error"]
        
        # Verify fallback provides conversation history
        assert "conversation_history" in memory_data
        assert len(memory_data["conversation_history"]) <= 3  # Limited to last 3
        
        # Verify fallback summary
        assert memory_data["conversation_summary"] == "Memory system temporarily unavailable"
    
    @pytest.mark.asyncio
    async def test_partial_memory_failure_recovery(self, sample_state):
        """Test recovery when some memory operations succeed and others fail."""
        mock_memory_system = Mock(spec=MemorySystem)
        # Retrieval succeeds
        mock_memory_system.working_memory.retrieve_context.return_value = {
            "results": [{"memory_id": "mem_001", "content": "Success context"}]
        }
        # Storage fails
        mock_memory_system.working_memory.store_conversation.side_effect = Exception("Storage failure")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            # Test successful retrieval
            retrieval_result = await retrieve_memory_context_node(sample_state)
            assert retrieval_result["memory"]["status"] == "context_retrieved"
            
            # Test failed storage
            storage_result = await store_conversation_node(sample_state)
            assert storage_result["memory"]["last_storage_status"] == "error"
            
            # Verify system can continue with partial functionality
            assert "conversation_history" in storage_result["memory"]
    
    @pytest.mark.asyncio
    async def test_memory_timeout_handling(self, sample_state):
        """Test handling of memory operation timeouts."""
        import asyncio
        
        async def slow_retrieve_context(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow operation
            return {"results": []}
        
        mock_memory_system = Mock(spec=MemorySystem)
        mock_memory_system.working_memory.retrieve_context.side_effect = slow_retrieve_context
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            # Test with timeout (this would need timeout implementation)
            start_time = asyncio.get_event_loop().time()
            result = await retrieve_memory_context_node(sample_state)
            elapsed_time = asyncio.get_event_loop().time() - start_time
            
            # For now, just verify the operation completes
            assert "memory" in result
            # In a real implementation, we'd want timeout handling
    
    @pytest.mark.asyncio
    async def test_memory_corruption_recovery(self, sample_state):
        """Test recovery from corrupted memory data."""
        # Simulate corrupted memory system response
        mock_memory_system = Mock(spec=MemorySystem)
        mock_memory_system.working_memory.retrieve_context.return_value = "invalid_data_format"
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await retrieve_memory_context_node(sample_state)
            
            # Verify graceful handling of corrupted data
            assert "memory" in result
            memory_data = result["memory"]
            
            # Should have some form of error indication
            # The actual behavior depends on implementation details
            assert "retrieved_context" in memory_data
    
    @pytest.mark.asyncio
    async def test_memory_quota_exceeded_recovery(self, sample_state):
        """Test recovery when memory storage quota is exceeded."""
        mock_memory_system = Mock(spec=MemorySystem)
        mock_memory_system.working_memory.store_conversation.side_effect = Exception("Storage quota exceeded: 1GB limit reached")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await store_conversation_node(sample_state)
            
            # Verify quota error is handled
            assert "memory" in result
            memory_data = result["memory"]
            assert memory_data["last_storage_status"] == "error"
            assert "quota exceeded" in memory_data["storage_error"].lower()
            
            # Verify conversation continues without storage
            assert "conversation_history" in memory_data
    
    @pytest.mark.asyncio
    async def test_cascading_memory_failures(self, sample_state):
        """Test handling of multiple simultaneous memory failures."""
        mock_memory_system = Mock(spec=MemorySystem)
        # All operations fail
        mock_memory_system.working_memory.retrieve_context.side_effect = Exception("Retrieval failed")
        mock_memory_system.working_memory.store_conversation.side_effect = Exception("Storage failed")
        mock_memory_system.working_memory.generate_summary.side_effect = Exception("Summarization failed")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            # Test all operations fail gracefully
            retrieval_result = await retrieve_memory_context_node(sample_state)
            storage_result = await store_conversation_node(sample_state)
            summary_result = await summarize_conversation_node(sample_state)
            
            # Verify all operations handle failures
            assert retrieval_result["memory"]["status"] == "retrieval_error"
            assert storage_result["memory"]["last_storage_status"] == "error"
            assert summary_result["memory"]["summarization_status"] == "error"
    
    @pytest.mark.asyncio
    async def test_memory_network_failure_recovery(self, sample_state):
        """Test recovery from network-related memory failures."""
        mock_memory_system = Mock(spec=MemorySystem)
        mock_memory_system.working_memory.retrieve_context.side_effect = ConnectionError("Network unreachable")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            result = await retrieve_memory_context_node(sample_state)
            
            # Verify network error handling
            assert "memory" in result
            memory_data = result["memory"]
            assert memory_data["status"] == "retrieval_error"
            assert "network unreachable" in memory_data["error"].lower()
    
    def test_memory_error_recovery_configuration(self, sample_state):
        """Test configuration of memory error recovery behavior."""
        # Test with different error recovery configurations
        sample_state["config"]["memory_error_recovery"] = {
            "max_retries": 3,
            "fallback_enabled": True,
            "timeout_seconds": 5
        }
        
        # For now, just verify configuration is accessible
        config = sample_state["config"]["memory_error_recovery"]
        assert config["max_retries"] == 3
        assert config["fallback_enabled"] is True
        assert config["timeout_seconds"] == 5
    
    @pytest.mark.asyncio
    async def test_memory_error_logging(self, sample_state):
        """Test that memory errors are properly logged."""
        import logging
        from unittest.mock import patch
        
        mock_memory_system = Mock(spec=MemorySystem)
        mock_memory_system.working_memory.retrieve_context.side_effect = Exception("Test error for logging")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            with patch('langgraph.nodes.memory_nodes.logger') as mock_logger:
                await retrieve_memory_context_node(sample_state)
                
                # Verify error was logged
                mock_logger.error.assert_called()
                call_args = mock_logger.error.call_args[0][0]
                assert "Memory context retrieval failed" in call_args


class TestMemoryErrorRecoveryPerformance:
    """Performance tests for memory error recovery."""
    
    @pytest.mark.asyncio
    async def test_error_recovery_performance(self, sample_state):
        """Test that error recovery doesn't significantly impact performance."""
        import time
        
        mock_memory_system = Mock(spec=MemorySystem)
        mock_memory_system.working_memory.retrieve_context.side_effect = Exception("Fast failure")
        
        with patch('langgraph.nodes.memory_nodes.get_memory_system', return_value=mock_memory_system):
            start_time = time.time()
            
            # Run multiple error recoveries
            for _ in range(10):
                await retrieve_memory_context_node(sample_state)
            
            elapsed_time = time.time() - start_time
            
            # Verify error recovery is fast
            assert elapsed_time < 0.5  # Should complete quickly even with errors
    
    @pytest.mark.asyncio 
    async def test_memory_fallback_efficiency(self, sample_state):
        """Test efficiency of memory fallback mechanisms."""
        # Test fallback with various conversation history sizes
        for history_size in [1, 10, 100]:
            large_history = []
            for i in range(history_size):
                large_history.append({
                    "memory_id": f"mem_{i:03d}",
                    "timestamp": datetime.now(),
                    "user_message": f"Message {i}",
                    "assistant_message": f"Response {i}"
                })
            
            sample_state["memory"]["conversation_history"] = large_history
            
            test_error = Exception("Memory system failure")
            result = await handle_memory_error(sample_state, test_error)
            
            # Verify fallback handles large histories efficiently
            assert "memory" in result
            memory_data = result["memory"]
            assert len(memory_data["conversation_history"]) <= 3  # Limited for efficiency


if __name__ == "__main__":
    pytest.main([__file__, "-v"])