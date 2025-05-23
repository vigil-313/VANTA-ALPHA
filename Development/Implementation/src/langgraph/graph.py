#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph Workflow Definition

This module implements the complete LangGraph workflow for VANTA, including
node connections, conditional routing, and persistence support.
"""
# TASK-REF: LG_003 - LangGraph Graph Definition and Conditional Routing
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration
# CONCEPT-REF: CON-VANTA-007 - Dual-Track Processing
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

import os
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Mock classes for development/testing without LangGraph
    class StateGraph:
        def __init__(self, state_type):
            self.state_type = state_type
            self.nodes = {}
            self.edges = []
            self.conditional_edges = []
            self.entry_point = None
            
        def add_node(self, name: str, func):
            self.nodes[name] = func
            
        def add_edge(self, from_node: str, to_node: str):
            self.edges.append((from_node, to_node))
            
        def add_conditional_edges(self, from_node: str, condition_func, mapping: Dict[str, str]):
            self.conditional_edges.append((from_node, condition_func, mapping))
            
        def set_entry_point(self, node: str):
            self.entry_point = node
            
        def compile(self, checkpointer=None):
            return CompiledGraph(self, checkpointer)
            
        def get_dot(self):
            return "digraph { /* Mock DOT representation */ }"
    
    class CompiledGraph:
        def __init__(self, graph, checkpointer):
            self.graph = graph
            self.checkpointer = checkpointer
            
        def invoke(self, state, config=None):
            return state  # Mock implementation
    
    class MemorySaver:
        def __init__(self):
            pass
    
    END = "__end__"
    LANGGRAPH_AVAILABLE = False

from .state import VANTAState
from .nodes import (
    check_activation,
    process_audio, 
    retrieve_context,
    router_node,
    local_model_node,
    api_model_node,
    integration_node,
    synthesize_speech,
    update_memory,
    prune_memory
)
from .routing import (
    should_process,
    determine_processing_path,
    check_processing_complete,
    should_synthesize_speech,
    should_update_memory
)

logger = logging.getLogger(__name__)


class VANTAWorkflowError(Exception):
    """Custom exception for VANTA workflow errors."""
    pass


def create_parallel_branch_node(state: VANTAState) -> Dict[str, Any]:
    """
    Empty node function for parallel processing branch.
    
    This node doesn't modify state, it just serves as a branching point
    for parallel execution of local and API model nodes.
    
    Args:
        state: Current VANTA state
        
    Returns:
        Empty dict (no state changes)
    """
    logger.debug("Entering parallel processing branch")
    return {}


def create_integration_check_node(state: VANTAState) -> Dict[str, Any]:
    """
    Empty node function for integration check.
    
    This node doesn't modify state, it just serves as a synchronization point
    where we check if processing is complete before integration.
    
    Args:
        state: Current VANTA state
        
    Returns:
        Empty dict (no state changes)
    """
    logger.debug("Checking if processing is complete for integration")
    return {}


def create_vanta_workflow() -> StateGraph:
    """
    Create the complete VANTA workflow graph.
    
    This function defines the complete workflow structure including all nodes,
    edges, and conditional routing logic for VANTA's dual-track processing.
    
    Returns:
        StateGraph: The compiled VANTA workflow graph
        
    Raises:
        VANTAWorkflowError: If workflow creation fails
    """
    if not LANGGRAPH_AVAILABLE:
        logger.warning("LangGraph not available, creating mock workflow")
    
    try:
        # Create the workflow graph
        workflow = StateGraph(VANTAState)
        
        # Add all node functions
        workflow.add_node("check_activation", check_activation)
        workflow.add_node("process_audio", process_audio)
        workflow.add_node("retrieve_context", retrieve_context)
        workflow.add_node("router_node", router_node)
        workflow.add_node("local_model_node", local_model_node)
        workflow.add_node("api_model_node", api_model_node)
        workflow.add_node("parallel_branch", create_parallel_branch_node)
        workflow.add_node("integration_check", create_integration_check_node)
        workflow.add_node("integration_node", integration_node)
        workflow.add_node("synthesize_speech", synthesize_speech)
        workflow.add_node("update_memory", update_memory)
        workflow.add_node("prune_memory", prune_memory)
        
        # Set entry point
        workflow.set_entry_point("check_activation")
        
        # Define the workflow structure
        
        # 1. Activation check - determine if we should process
        workflow.add_conditional_edges(
            "check_activation",
            should_process,
            {
                "continue": "process_audio",
                "end": END
            }
        )
        
        # 2. Sequential processing: audio -> context -> routing
        workflow.add_edge("process_audio", "retrieve_context")
        workflow.add_edge("retrieve_context", "router_node")
        
        # 3. Conditional routing based on processing path
        workflow.add_conditional_edges(
            "router_node",
            determine_processing_path,
            {
                "local": "local_model_node",
                "api": "api_model_node", 
                "parallel": "parallel_branch"
            }
        )
        
        # 4. Parallel processing branch
        workflow.add_edge("parallel_branch", "local_model_node")
        workflow.add_edge("parallel_branch", "api_model_node")
        
        # 5. Both model paths converge at integration check
        workflow.add_edge("local_model_node", "integration_check")
        workflow.add_edge("api_model_node", "integration_check")
        
        # 6. Wait for processing completion before integration
        workflow.add_conditional_edges(
            "integration_check",
            check_processing_complete,
            {
                "ready": "integration_node",
                "waiting": "integration_check"  # Loop back until ready
            }
        )
        
        # 7. Response integration and speech synthesis
        workflow.add_conditional_edges(
            "integration_node",
            should_synthesize_speech,
            {
                "synthesize": "synthesize_speech",
                "skip": "update_memory"
            }
        )
        
        # 8. From speech synthesis to memory update
        workflow.add_edge("synthesize_speech", "update_memory")
        
        # 9. Memory update and pruning
        workflow.add_conditional_edges(
            "update_memory",
            should_update_memory,
            {
                "update": "prune_memory",
                "skip": END
            }
        )
        
        # 10. Final step - end workflow
        workflow.add_edge("prune_memory", END)
        
        logger.info("VANTA workflow graph created successfully")
        return workflow
        
    except Exception as e:
        logger.error(f"Failed to create VANTA workflow: {e}")
        raise VANTAWorkflowError(f"Workflow creation failed: {e}")


def create_checkpointer(config: Dict[str, Any]) -> Union[MemorySaver, object]:
    """
    Create an appropriate checkpointer based on configuration.
    
    Args:
        config: Configuration dictionary containing persistence settings
        
    Returns:
        Checkpointer instance based on configuration
        
    Raises:
        VANTAWorkflowError: If checkpointer creation fails
    """
    try:
        persistence_type = config.get("persistence", {}).get("type", "memory")
        
        if persistence_type == "memory":
            logger.debug("Creating in-memory checkpointer")
            return MemorySaver()
            
        elif persistence_type == "file":
            # File-based persistence (if available)
            try:
                from langgraph.checkpoint.sqlite import SqliteSaver
                path = config.get("persistence", {}).get("path", "./checkpoints.db")
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Creating SQLite checkpointer at {path}")
                return SqliteSaver.from_conn_string(f"sqlite:///{path}")
            except ImportError:
                logger.warning("SQLite checkpointer not available, falling back to memory")
                return MemorySaver()
                
        elif persistence_type == "redis":
            # Redis-based persistence (if available)
            try:
                from langgraph.checkpoint.redis import RedisSaver
                redis_url = config.get("persistence", {}).get("url", "redis://localhost:6379")
                logger.debug(f"Creating Redis checkpointer with URL {redis_url}")
                return RedisSaver.from_conn_string(redis_url)
            except ImportError:
                logger.warning("Redis checkpointer not available, falling back to memory")
                return MemorySaver()
                
        else:
            logger.warning(f"Unknown persistence type: {persistence_type}, defaulting to memory")
            return MemorySaver()
            
    except Exception as e:
        logger.error(f"Failed to create checkpointer: {e}")
        raise VANTAWorkflowError(f"Checkpointer creation failed: {e}")


def compile_vanta_graph(config: Optional[Dict[str, Any]] = None) -> object:
    """
    Create and compile the complete VANTA workflow graph.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Compiled graph ready for execution
        
    Raises:
        VANTAWorkflowError: If graph compilation fails
    """
    try:
        if config is None:
            config = {"persistence": {"type": "memory"}}
            
        # Create the workflow
        workflow = create_vanta_workflow()
        
        # Create checkpointer for persistence
        checkpointer = create_checkpointer(config)
        
        # Compile the graph
        graph = workflow.compile(checkpointer=checkpointer)
        
        logger.info("VANTA workflow graph compiled successfully")
        return graph
        
    except Exception as e:
        logger.error(f"Failed to compile VANTA graph: {e}")
        raise VANTAWorkflowError(f"Graph compilation failed: {e}")


def process_with_vanta_graph(
    graph: object,
    input_state: VANTAState,
    thread_id: str = "default"
) -> VANTAState:
    """
    Process input using the VANTA workflow graph.
    
    Args:
        graph: Compiled VANTA workflow graph
        input_state: Initial state for processing
        thread_id: Thread ID for conversation continuity
        
    Returns:
        Final state after processing
        
    Raises:
        VANTAWorkflowError: If processing fails
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        
        logger.info(f"Processing input with thread ID: {thread_id}")
        result = graph.invoke(input_state, config)
        
        logger.info("Input processed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Failed to process input: {e}")
        raise VANTAWorkflowError(f"Processing failed: {e}")


def visualize_workflow(workflow: StateGraph, output_path: str = "vanta_workflow") -> str:
    """
    Generate a visualization of the VANTA workflow graph.
    
    Args:
        workflow: The workflow graph to visualize
        output_path: Base path for output files (without extension)
        
    Returns:
        Message describing the visualization result
    """
    try:
        # Get the DOT representation
        dot_string = workflow.get_dot()
        
        # Try to save as PNG using graphviz if available
        try:
            from graphviz import Source
            src = Source(dot_string)
            src.render(output_path, format="png", cleanup=True)
            return f"Graph visualization saved to {output_path}.png"
        except ImportError:
            # If graphviz not available, just save the DOT file
            dot_path = f"{output_path}.dot"
            with open(dot_path, "w") as f:
                f.write(dot_string)
            return f"Graph DOT representation saved to {dot_path}"
            
    except Exception as e:
        error_msg = f"Error generating graph visualization: {e}"
        logger.error(error_msg)
        return error_msg


# Convenience function for easy workflow creation
def create_default_vanta_graph() -> object:
    """
    Create a VANTA workflow graph with default configuration.
    
    Returns:
        Compiled graph with default settings
    """
    return compile_vanta_graph()


# Export the main interface functions
__all__ = [
    "create_vanta_workflow",
    "compile_vanta_graph", 
    "process_with_vanta_graph",
    "visualize_workflow",
    "create_default_vanta_graph",
    "VANTAWorkflowError"
]