# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

from typing import Dict, Any, List, Optional, Callable
from unittest.mock import MagicMock

class MockNode:
    """Mock node for testing LangGraph components."""
    
    def __init__(self, name: str, func: Optional[Callable] = None):
        self.name = name
        self.func = func or (lambda state: {**state, "touched_by": state.get("touched_by", []) + [name]})
        self.called = 0
        self.last_inputs = None
    
    def __call__(self, state):
        self.called += 1
        self.last_inputs = state
        return self.func(state)

def create_mock_graph():
    """Create a mock LangGraph for testing."""
    nodes = {
        "start": MockNode("start"),
        "process": MockNode("process"),
        "end": MockNode("end")
    }
    
    edges = {
        "start": "process",
        "process": "end"
    }
    
    # Simple mock of a LangGraph
    mock_graph = MagicMock()
    mock_graph.nodes = nodes
    mock_graph._edges = edges
    
    def mock_invoke(state, **kwargs):
        """Mock invoke method that simulates graph execution."""
        current = "start"
        result = state
        
        while current is not None:
            # Call current node
            node = nodes[current]
            result = node(result)
            
            # Get next node
            current = edges.get(current)
        
        return result
    
    mock_graph.invoke = mock_invoke
    
    return mock_graph

def assert_graph_flow(graph, initial_state, expected_touched_order):
    """
    Assert that a graph processes nodes in the expected order.
    
    Args:
        graph: The graph to test
        initial_state: Initial state to pass to the graph
        expected_touched_order: Expected order of nodes to be processed
        
    Returns:
        True if the flow matches expectations, False otherwise
    """
    result = graph.invoke(initial_state)
    
    # Check that all expected nodes were touched
    touched = result.get("touched_by", [])
    
    return touched == expected_touched_order