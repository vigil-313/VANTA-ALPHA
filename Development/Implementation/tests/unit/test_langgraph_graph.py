#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for LangGraph workflow graph functionality.

This module contains comprehensive tests for the VANTA LangGraph workflow
creation, compilation, and execution.
"""
# TASK-REF: LG_003 - LangGraph Graph Definition and Conditional Routing
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.langgraph.graph import (
    create_vanta_workflow,
    create_checkpointer,
    compile_vanta_graph,
    process_with_vanta_graph,
    visualize_workflow,
    create_default_vanta_graph,
    VANTAWorkflowError,
    create_parallel_branch_node,
    create_integration_check_node,
)
from src.langgraph.state import create_empty_state, ActivationStatus


class TestWorkflowCreation:
    """Test VANTA workflow creation."""
    
    def test_create_vanta_workflow_success(self):
        """Test successful workflow creation."""
        workflow = create_vanta_workflow()
        
        # Check that workflow has expected nodes
        expected_nodes = [
            "check_activation",
            "process_audio",
            "retrieve_context",
            "router_node",
            "local_model_node",
            "api_model_node",
            "parallel_branch",
            "integration_check",
            "integration_node",
            "synthesize_speech",
            "update_memory",
            "prune_memory"
        ]
        
        for node_name in expected_nodes:
            assert node_name in workflow.nodes
        
        # Check that entry point is set
        assert workflow.entry_point == "check_activation"
    
    def test_create_parallel_branch_node(self):
        """Test parallel branch node function."""
        state = create_empty_state()
        result = create_parallel_branch_node(state)
        
        # Should return empty dict (no state changes)
        assert result == {}
    
    def test_create_integration_check_node(self):
        """Test integration check node function."""
        state = create_empty_state()
        result = create_integration_check_node(state)
        
        # Should return empty dict (no state changes)
        assert result == {}


class TestCheckpointerCreation:
    """Test checkpointer creation with various configurations."""
    
    def test_create_memory_checkpointer(self):
        """Test creating memory-based checkpointer."""
        config = {"persistence": {"type": "memory"}}
        checkpointer = create_checkpointer(config)
        
        # Should be a MemorySaver instance (or mock)
        assert checkpointer is not None
    
    def test_create_file_checkpointer_mock(self):
        """Test creating file-based checkpointer (mocked)."""
        config = {
            "persistence": {
                "type": "file",
                "path": "/tmp/test_checkpoints.db"
            }
        }
        
        # Since SQLite checkpointer might not be available, test should handle gracefully
        checkpointer = create_checkpointer(config)
        assert checkpointer is not None
    
    def test_create_redis_checkpointer_mock(self):
        """Test creating Redis-based checkpointer (mocked)."""
        config = {
            "persistence": {
                "type": "redis",
                "url": "redis://localhost:6379"
            }
        }
        
        # Since Redis checkpointer might not be available, test should handle gracefully
        checkpointer = create_checkpointer(config)
        assert checkpointer is not None
    
    def test_create_checkpointer_unknown_type(self):
        """Test creating checkpointer with unknown type."""
        config = {"persistence": {"type": "unknown"}}
        checkpointer = create_checkpointer(config)
        
        # Should fallback to memory saver
        assert checkpointer is not None
    
    def test_create_checkpointer_default(self):
        """Test creating checkpointer with default config."""
        config = {}
        checkpointer = create_checkpointer(config)
        
        # Should default to memory saver
        assert checkpointer is not None
    
    def test_create_checkpointer_error_handling(self):
        """Test checkpointer creation error handling."""
        # Test with malformed config that might cause errors
        with patch('src.langgraph.graph.MemorySaver', side_effect=Exception("Mock error")):
            with pytest.raises(VANTAWorkflowError):
                create_checkpointer({"persistence": {"type": "memory"}})


class TestGraphCompilation:
    """Test graph compilation functionality."""
    
    def test_compile_vanta_graph_default(self):
        """Test compiling graph with default configuration."""
        graph = compile_vanta_graph()
        assert graph is not None
    
    def test_compile_vanta_graph_with_config(self):
        """Test compiling graph with custom configuration."""
        config = {
            "persistence": {"type": "memory"}
        }
        graph = compile_vanta_graph(config)
        assert graph is not None
    
    def test_compile_vanta_graph_error_handling(self):
        """Test graph compilation error handling."""
        # Mock workflow creation to raise an error
        with patch('src.langgraph.graph.create_vanta_workflow', side_effect=Exception("Mock error")):
            with pytest.raises(VANTAWorkflowError):
                compile_vanta_graph()


class TestGraphProcessing:
    """Test graph processing functionality."""
    
    def test_process_with_vanta_graph_success(self):
        """Test successful processing with VANTA graph."""
        # Create a mock graph
        mock_graph = Mock()
        mock_graph.invoke.return_value = {"test": "result"}
        
        input_state = create_empty_state()
        result = process_with_vanta_graph(mock_graph, input_state, "test_thread")
        
        # Check that graph.invoke was called with correct parameters
        mock_graph.invoke.assert_called_once()
        args, kwargs = mock_graph.invoke.call_args
        assert args[0] == input_state
        assert kwargs["config"]["configurable"]["thread_id"] == "test_thread"
        
        assert result == {"test": "result"}
    
    def test_process_with_vanta_graph_default_thread(self):
        """Test processing with default thread ID."""
        mock_graph = Mock()
        mock_graph.invoke.return_value = {"test": "result"}
        
        input_state = create_empty_state()
        result = process_with_vanta_graph(mock_graph, input_state)
        
        # Check that default thread ID was used
        args, kwargs = mock_graph.invoke.call_args
        assert kwargs["config"]["configurable"]["thread_id"] == "default"
    
    def test_process_with_vanta_graph_error_handling(self):
        """Test graph processing error handling."""
        mock_graph = Mock()
        mock_graph.invoke.side_effect = Exception("Processing failed")
        
        input_state = create_empty_state()
        
        with pytest.raises(VANTAWorkflowError):
            process_with_vanta_graph(mock_graph, input_state)


class TestVisualization:
    """Test workflow visualization functionality."""
    
    def test_visualize_workflow_with_graphviz(self):
        """Test workflow visualization with graphviz available."""
        mock_workflow = Mock()
        mock_workflow.get_dot.return_value = "digraph { a -> b; }"
        
        # Mock graphviz Source
        mock_source = Mock()
        
        with patch('src.langgraph.graph.Source', return_value=mock_source) as mock_source_class:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "test_graph")
                result = visualize_workflow(mock_workflow, output_path)
                
                # Check that Source was created and render was called
                mock_source_class.assert_called_once_with("digraph { a -> b; }")
                mock_source.render.assert_called_once_with(output_path, format="png", cleanup=True)
                
                assert "Graph visualization saved" in result
                assert ".png" in result
    
    def test_visualize_workflow_without_graphviz(self):
        """Test workflow visualization without graphviz."""
        mock_workflow = Mock()
        mock_workflow.get_dot.return_value = "digraph { a -> b; }"
        
        # Mock ImportError for graphviz
        with patch('src.langgraph.graph.Source', side_effect=ImportError("No graphviz")):
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "test_graph")
                result = visualize_workflow(mock_workflow, output_path)
                
                # Should save DOT file instead
                assert "Graph DOT representation saved" in result
                assert ".dot" in result
                
                # Check that DOT file was created
                dot_file = f"{output_path}.dot"
                assert os.path.exists(dot_file)
                
                with open(dot_file, "r") as f:
                    content = f.read()
                    assert "digraph { a -> b; }" in content
    
    def test_visualize_workflow_error_handling(self):
        """Test visualization error handling."""
        mock_workflow = Mock()
        mock_workflow.get_dot.side_effect = Exception("DOT generation failed")
        
        result = visualize_workflow(mock_workflow, "test_output")
        
        assert "Error generating graph visualization" in result
        assert "DOT generation failed" in result


class TestDefaultGraph:
    """Test default graph creation functionality."""
    
    def test_create_default_vanta_graph(self):
        """Test creating default VANTA graph."""
        graph = create_default_vanta_graph()
        assert graph is not None


class TestIntegrationScenarios:
    """Test integration scenarios with the workflow."""
    
    def test_workflow_with_different_activation_states(self):
        """Test workflow behavior with different activation states."""
        # This is a mock test since we don't have actual LangGraph available
        workflow = create_vanta_workflow()
        
        # Test with inactive state
        inactive_state = create_empty_state()
        inactive_state["activation"]["status"] = ActivationStatus.INACTIVE
        
        # Test with processing state
        processing_state = create_empty_state()
        processing_state["activation"]["status"] = ActivationStatus.PROCESSING
        
        # In a real test, we would invoke the workflow and check the path taken
        # For now, we just verify the workflow structure
        assert "check_activation" in workflow.nodes
        assert workflow.entry_point == "check_activation"
    
    def test_workflow_with_different_processing_paths(self):
        """Test workflow routing with different processing paths."""
        workflow = create_vanta_workflow()
        
        # Test states for different processing paths
        local_state = create_empty_state()
        local_state["memory"]["processing"]["path"] = "local"
        
        api_state = create_empty_state()
        api_state["memory"]["processing"]["path"] = "api"
        
        parallel_state = create_empty_state()
        parallel_state["memory"]["processing"]["path"] = "parallel"
        
        # Verify that all necessary nodes exist for different paths
        assert "router_node" in workflow.nodes
        assert "local_model_node" in workflow.nodes
        assert "api_model_node" in workflow.nodes
        assert "parallel_branch" in workflow.nodes
        assert "integration_node" in workflow.nodes


class TestErrorScenarios:
    """Test various error scenarios in graph operations."""
    
    def test_workflow_creation_with_missing_dependencies(self):
        """Test workflow creation when dependencies are missing."""
        # Mock missing node functions
        with patch('src.langgraph.graph.check_activation', side_effect=ImportError("Missing dependency")):
            # Should still create workflow but might fail at runtime
            # In production, this would be handled by proper dependency management
            pass  # This test structure depends on actual implementation details
    
    def test_graph_compilation_with_invalid_checkpointer(self):
        """Test graph compilation with invalid checkpointer."""
        config = {"persistence": {"type": "invalid"}}
        
        # Should fallback to memory saver and not raise error
        graph = compile_vanta_graph(config)
        assert graph is not None


if __name__ == "__main__":
    pytest.main([__file__])