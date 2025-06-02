"""
VANTA LangGraph Integration Package

This package provides LangGraph integration for the VANTA system, enabling
graph-based workflow management with typed state definitions.

The LangGraph integration provides:
1. A typed state definition for all VANTA components
2. Node implementations for various processing steps
3. Persistence utilities for conversation history
4. Graph definition and conditional routing logic
"""
# TASK-REF: LG_001 - LangGraph State Definition
# TASK-REF: LG_002 - LangGraph Node Implementation
# TASK-REF: LG_003 - LangGraph Graph Definition and Conditional Routing
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration

# Version
__version__ = "0.2.0"

# Core exports
from .state import (
    VANTAState,
    ActivationMode,
    ActivationStatus,
    ProcessingPath,
    serialize_state,
    deserialize_state,
    create_empty_state,
    update_state,
)

# Temporarily commenting out node imports to resolve dependency issues
# from .nodes import (
#     # Voice processing nodes
#     check_activation,
#     process_audio,
#     synthesize_speech,
#     
#     # Memory processing nodes
#     retrieve_context,
#     update_memory,
#     prune_memory,
#     
#     # Dual-track processing nodes
#     router_node,
#     local_model_node,
#     api_model_node,
#     integration_node,
# )

# Temporarily commenting out routing imports to resolve dependency issues
# from .routing import (
#     should_process,
#     determine_processing_path,
#     check_processing_complete,
#     should_synthesize_speech,
#     should_update_memory,
#     get_routing_function,
#     list_routing_functions,
# )

from .graph import (
    create_vanta_workflow,
    compile_vanta_graph,
    process_with_vanta_graph,
    visualize_workflow,
    create_default_vanta_graph,
    VANTAWorkflowError,
)

# Temporarily commenting out persistence imports to resolve dependency issues
# from .persistence import (
#     create_memory_saver,
#     load_conversation_state,
#     save_conversation_state,
#     ConversationPersistence,
# )

__all__ = [
    # State management
    "VANTAState",
    "ActivationMode",
    "ActivationStatus", 
    "ProcessingPath",
    "serialize_state",
    "deserialize_state",
    "create_empty_state",
    "update_state",
    
    # Node functions (temporarily commented out due to import issues)
    # "check_activation",
    # "process_audio",
    # "synthesize_speech",
    # "retrieve_context", 
    # "update_memory",
    # "prune_memory",
    # "router_node",
    # "local_model_node",
    # "api_model_node",
    # "integration_node",
    
    # Routing functions (temporarily commented out due to import issues)
    # "should_process",
    # "determine_processing_path",
    # "check_processing_complete",
    # "should_synthesize_speech",
    # "should_update_memory",
    # "get_routing_function",
    # "list_routing_functions",
    
    # Graph management
    "create_vanta_workflow",
    "compile_vanta_graph",
    "process_with_vanta_graph", 
    "visualize_workflow",
    "create_default_vanta_graph",
    "VANTAWorkflowError",
    
    # Persistence (temporarily commented out due to import issues)
    # "create_memory_saver",
    # "load_conversation_state",
    # "save_conversation_state",
    # "ConversationPersistence",
]