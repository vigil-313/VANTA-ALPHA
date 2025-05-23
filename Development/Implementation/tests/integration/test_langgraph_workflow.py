#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for complete LangGraph workflow execution.

This module contains integration tests that verify the complete VANTA workflow
works correctly from start to finish with various scenarios.
"""
# TASK-REF: LG_003 - LangGraph Graph Definition and Conditional Routing
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration

import pytest
from unittest.mock import Mock, patch
import time

from src.langgraph.graph import (
    create_vanta_workflow,
    compile_vanta_graph,
    process_with_vanta_graph,
    create_default_vanta_graph,
)
from src.langgraph.state import (
    create_empty_state,
    create_message,
    ActivationStatus,
)
from src.langgraph.routing import (
    should_process,
    determine_processing_path,
    check_processing_complete,
)


class TestCompleteWorkflowIntegration:
    """Test complete workflow integration scenarios."""
    
    def test_workflow_creation_and_compilation(self):
        """Test that workflow can be created and compiled successfully."""
        # Create workflow
        workflow = create_vanta_workflow()
        assert workflow is not None
        
        # Compile with default config
        graph = compile_vanta_graph()
        assert graph is not None
        
        # Test default graph creation
        default_graph = create_default_vanta_graph()
        assert default_graph is not None
    
    def test_routing_functions_with_realistic_states(self):
        """Test routing functions with realistic state transitions."""
        # Test activation flow
        inactive_state = create_empty_state()
        inactive_state["activation"]["status"] = ActivationStatus.INACTIVE
        
        processing_state = create_empty_state()
        processing_state["activation"]["status"] = ActivationStatus.PROCESSING
        
        # Test activation routing
        assert should_process(inactive_state) == "end"
        assert should_process(processing_state) == "continue"
        
        # Test processing path routing
        local_state = create_empty_state()
        local_state["memory"]["processing"]["path"] = "local"
        
        parallel_state = create_empty_state()
        parallel_state["memory"]["processing"]["path"] = "parallel"
        
        assert determine_processing_path(local_state) == "local"
        assert determine_processing_path(parallel_state) == "parallel"
        
        # Test completion checking
        complete_local_state = create_empty_state()
        complete_local_state["memory"]["processing"]["path"] = "local"
        complete_local_state["memory"]["processing"]["local_completed"] = True
        
        incomplete_state = create_empty_state()
        incomplete_state["memory"]["processing"]["path"] = "local"
        incomplete_state["memory"]["processing"]["local_completed"] = False
        
        assert check_processing_complete(complete_local_state) == "ready"
        assert check_processing_complete(incomplete_state) == "waiting"


class TestWorkflowScenarios:
    """Test different workflow execution scenarios."""
    
    def test_local_model_workflow_scenario(self):
        """Test workflow scenario using only local model."""
        # Create initial state for local model processing
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["memory"]["processing"]["path"] = "local"
        state["messages"] = [create_message("user", "Hello, how are you?")]
        
        # Test routing decisions for this scenario
        assert should_process(state) == "continue"
        assert determine_processing_path(state) == "local"
        
        # Simulate local processing completion
        state["memory"]["processing"]["local_completed"] = True
        assert check_processing_complete(state) == "ready"
    
    def test_api_model_workflow_scenario(self):
        """Test workflow scenario using only API model."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["memory"]["processing"]["path"] = "api"
        state["messages"] = [create_message("user", "What's the weather like?")]
        
        # Test routing decisions
        assert should_process(state) == "continue"
        assert determine_processing_path(state) == "api"
        
        # Simulate API processing completion
        state["memory"]["processing"]["api_completed"] = True
        assert check_processing_complete(state) == "ready"
    
    def test_parallel_processing_workflow_scenario(self):
        """Test workflow scenario using parallel processing."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["memory"]["processing"]["path"] = "parallel"
        state["memory"]["processing"]["start_time"] = time.time()
        state["messages"] = [create_message("user", "Tell me about quantum computing")]
        
        # Test routing decisions
        assert should_process(state) == "continue"
        assert determine_processing_path(state) == "parallel"
        
        # Test with local completing first
        state["memory"]["processing"]["local_completed"] = True
        state["memory"]["processing"]["api_completed"] = False
        assert check_processing_complete(state) == "ready"
        
        # Reset and test with API completing first
        state["memory"]["processing"]["local_completed"] = False
        state["memory"]["processing"]["api_completed"] = True
        assert check_processing_complete(state) == "ready"
        
        # Test timeout scenario
        state["memory"]["processing"]["local_completed"] = False
        state["memory"]["processing"]["api_completed"] = False
        state["memory"]["processing"]["start_time"] = time.time() - 15  # 15 seconds ago
        state["memory"]["processing"]["timeout"] = 10  # 10 second timeout
        assert check_processing_complete(state) == "ready"  # Should proceed due to timeout


class TestWorkflowEdgeCases:
    """Test edge cases and error scenarios in workflow."""
    
    def test_workflow_with_malformed_state(self):
        """Test workflow behavior with malformed state."""
        # Test with missing activation
        malformed_state = {
            "messages": [],
            "audio": {},
            "memory": {},
            "config": {}
        }
        
        # Routing functions should handle gracefully
        assert should_process(malformed_state) == "end"
        assert determine_processing_path(malformed_state) == "parallel"
        assert check_processing_complete(malformed_state) == "waiting"
    
    def test_workflow_with_empty_state(self):
        """Test workflow with minimal/empty state."""
        empty_state = create_empty_state()
        
        # Should handle empty state gracefully
        assert should_process(empty_state) == "end"  # Default inactive
        assert determine_processing_path(empty_state) == "parallel"  # Default path
        assert check_processing_complete(empty_state) == "waiting"  # Default waiting
    
    def test_workflow_state_transitions(self):
        """Test realistic state transitions through workflow."""
        # Start with inactive state
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.INACTIVE
        
        # Should end workflow
        assert should_process(state) == "end"
        
        # Activate system
        state["activation"]["status"] = ActivationStatus.LISTENING
        assert should_process(state) == "continue"
        
        # Start processing
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["memory"]["processing"]["path"] = "parallel"
        assert determine_processing_path(state) == "parallel"
        
        # Processing in progress
        assert check_processing_complete(state) == "waiting"
        
        # Complete processing
        state["memory"]["processing"]["local_completed"] = True
        assert check_processing_complete(state) == "ready"


class TestWorkflowConfiguration:
    """Test workflow with different configurations."""
    
    def test_workflow_with_memory_persistence(self):
        """Test workflow compilation with memory persistence."""
        config = {
            "persistence": {"type": "memory"}
        }
        
        graph = compile_vanta_graph(config)
        assert graph is not None
    
    def test_workflow_with_file_persistence(self):
        """Test workflow compilation with file persistence."""
        config = {
            "persistence": {
                "type": "file",
                "path": "/tmp/test_workflow.db"
            }
        }
        
        # Should handle file persistence (even if not available)
        graph = compile_vanta_graph(config)
        assert graph is not None
    
    def test_workflow_with_custom_timeouts(self):
        """Test workflow with custom timeout configurations."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["memory"]["processing"]["path"] = "parallel"
        state["memory"]["processing"]["start_time"] = time.time() - 5
        state["memory"]["processing"]["timeout"] = 3  # 3 second timeout
        
        # Should be ready due to timeout
        assert check_processing_complete(state) == "ready"


class TestWorkflowPerformance:
    """Test workflow performance characteristics."""
    
    def test_routing_function_performance(self):
        """Test that routing functions perform efficiently."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["memory"]["processing"]["path"] = "parallel"
        
        # Test multiple calls to ensure no performance degradation
        start_time = time.time()
        for _ in range(1000):
            should_process(state)
            determine_processing_path(state)
            check_processing_complete(state)
        end_time = time.time()
        
        # Should complete 1000 iterations quickly (under 1 second)
        elapsed = end_time - start_time
        assert elapsed < 1.0, f"Routing functions too slow: {elapsed} seconds"
    
    def test_state_handling_efficiency(self):
        """Test efficient state handling in workflow."""
        # Create state with realistic message history
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        
        # Add multiple messages to simulate conversation
        for i in range(100):
            state["messages"].append(create_message("user", f"Message {i}"))
            state["messages"].append(create_message("assistant", f"Response {i}"))
        
        # Test that routing still works efficiently with large state
        start_time = time.time()
        result = should_process(state)
        end_time = time.time()
        
        assert result == "continue"
        assert (end_time - start_time) < 0.1  # Should be very fast


class TestWorkflowResilience:
    """Test workflow resilience and error recovery."""
    
    def test_workflow_with_node_errors(self):
        """Test workflow behavior when individual nodes encounter errors."""
        # This would require mocking individual node functions to raise errors
        # and verifying that the workflow handles them gracefully
        
        # For now, test that the workflow structure is resilient
        workflow = create_vanta_workflow()
        
        # Verify all critical nodes are present
        critical_nodes = [
            "check_activation",
            "router_node", 
            "integration_node"
        ]
        
        for node in critical_nodes:
            assert node in workflow.nodes
    
    def test_workflow_with_persistence_errors(self):
        """Test workflow behavior when persistence encounters errors."""
        # Test with invalid persistence configuration
        config = {
            "persistence": {
                "type": "invalid_type",
                "url": "invalid://url"
            }
        }
        
        # Should fallback gracefully
        graph = compile_vanta_graph(config)
        assert graph is not None


if __name__ == "__main__":
    pytest.main([__file__])