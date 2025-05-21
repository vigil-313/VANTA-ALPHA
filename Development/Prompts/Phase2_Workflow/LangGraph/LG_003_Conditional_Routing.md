# LangGraph Conditional Routing Implementation Prompt

## Task Identification
- **Task ID**: TASK-LG-003
- **Component**: Core Architecture
- **Phase**: Foundation
- **Priority**: High
- **Related Concepts**: [CON-VANTA-008 LangGraph Integration, CON-VANTA-007 Dual-Track Processing]

## Task Description
Implement the LangGraph conditional routing logic and graph structure for VANTA. This task involves defining conditional edge functions that determine the flow between nodes, composing the complete workflow graph, and implementing the runtime execution system for the graph. The conditional routing will enable dynamic processing paths based on query characteristics, system state, and resource availability.

### Objective
Create a flexible, dynamic LangGraph workflow that connects all VANTA components through appropriate conditional routing.

### Success Criteria
- Complete graph definition connecting all VANTA nodes
- Conditional routing functions for all decision points
- Support for parallel execution of local and API model paths
- Support for persistence and state checkpointing
- Comprehensive documentation of the graph structure

## Implementation Context
This task depends on the LangGraph State Definition (TASK-LG-001) and Node Implementation (TASK-LG-002), and will use their outputs to create the complete workflow graph. The conditional routing is essential for implementing the dual-track processing architecture, allowing VANTA to dynamically choose between local and API models based on the query characteristics and system state.

### Task Dependencies
- **TASK-LG-001**: LangGraph State Definition (Required)
- **TASK-LG-002**: LangGraph Node Implementation (Required)

### Architectural Context
The conditional routing implements the workflow logic of VANTA's hybrid architecture, especially the dynamic routing between local and API models in the dual-track processing component. The graph structure defines how components interact and how data flows through the system. This component is central to VANTA's ability to balance performance, response quality, and resource usage.

### Technical Requirements
1. LangGraph's conditional edges for dynamic routing
2. Support for both sequential and parallel processing paths
3. Integration with LangGraph's persistence system
4. Clean error handling and recovery mechanisms
5. Support for runtime graph visualization
6. Efficient graph execution with minimal overhead

## Implementation Details

### Interfaces
The primary interfaces are the conditional edge functions and the graph definition:

```python
# Conditional edge function
def should_process(state: VANTAState) -> str:
    """
    Determines whether to process audio or end workflow.
    
    Args:
        state: The current VANTA state
        
    Returns:
        str: The edge to follow ("continue" or "end")
    """
    if state["activation"]["status"] == ActivationStatus.INACTIVE:
        return "end"
    return "continue"

# Graph definition
workflow = StateGraph(VANTAState)
workflow.add_node("check_activation", check_activation)
workflow.add_conditional_edges(
    "check_activation",
    should_process,
    {
        "continue": "process_audio",
        "end": END
    }
)
# ... additional nodes and edges
```

### Key Conditional Functions

The implementation should include the following key conditional functions:

1. **should_process**: Determines whether to process audio based on activation
2. **determine_processing_path**: Routes to local, API, or parallel processing
3. **check_local_completion**: Checks if local processing is complete
4. **check_api_completion**: Checks if API processing is complete
5. **can_integrate_responses**: Determines if response integration is possible

### Inputs
The conditional functions receive the full VANTA state and extract relevant components:

| Conditional Function | Key Inputs | Description |
|----------------------|------------|-------------|
| should_process | activation.status | Checks activation status to determine if processing should continue |
| determine_processing_path | memory.processing.path | Determines which processing path(s) to follow |
| check_local_completion | memory.processing.local_completed | Checks if local processing is complete |
| check_api_completion | memory.processing.api_completed | Checks if API processing is complete |
| can_integrate_responses | memory.processing | Checks if responses can be integrated |

### Outputs
The conditional functions return string identifiers for the edges to follow:

| Conditional Function | Possible Outputs | Description |
|----------------------|------------------|-------------|
| should_process | "continue", "end" | Whether to continue processing or end the workflow |
| determine_processing_path | "local", "api", "parallel" | Which processing path(s) to follow |
| check_local_completion | "complete", "waiting" | Whether local processing is complete |
| check_api_completion | "complete", "waiting" | Whether API processing is complete |
| can_integrate_responses | "ready", "waiting" | Whether responses can be integrated |

### Graph Structure
The complete graph structure should include:

1. **Entry Point**: Starting with check_activation
2. **Voice Pipeline Path**: For audio processing and transcription
3. **Memory System Path**: For context retrieval and memory updates
4. **Processing Paths**: 
   - Local Model Path
   - API Model Path
   - Parallel Processing Path
5. **Response Integration**: For combining results
6. **Speech Synthesis**: For converting responses to audio
7. **End Node**: Marking the completion of the workflow

### Algorithm / Processing Steps

#### Graph Construction
1. Create a new StateGraph with VANTAState
2. Add all node functions from TASK-LG-002
3. Define conditional routing functions
4. Set the entry point to check_activation
5. Add conditional edges between nodes
6. Compile the graph with a checkpointer for persistence

#### Workflow Execution
1. Create or load initial state
2. Configure thread ID for persistence
3. Invoke the graph with the initial state
4. Process state updates through the nodes
5. Follow conditional edges based on state
6. Complete execution and return final state

#### Checkpointing Strategy
1. Define a checkpointer based on the desired persistence backend
2. Configure the graph to use the checkpointer
3. Use thread IDs to maintain conversation continuity
4. Implement periodic checkpointing during long-running operations

### Error Handling
1. Node function errors: Wrap in try/except blocks, continue with defaults
2. Conditional function errors: Default to safest path on error
3. Graph execution errors: Catch, log, and restart from latest checkpoint
4. Resource exhaustion: Implement circuit breakers for API calls

### Performance Considerations
1. Lazy node execution: Only execute nodes when needed
2. Partial state updates: Minimize serialization/deserialization
3. Stream processing: Use streaming for long-running operations
4. Asynchronous execution: Where possible for I/O bound operations

## Validation Criteria
1. Graph connects all VANTA nodes correctly
2. Conditional routing handles all decision points
3. Parallel execution works for dual-track processing
4. State persistence maintains conversation continuity
5. Error recovery mechanisms work correctly

## Testing Approach

### Unit Tests
1. Test each conditional function with various input states
2. Test graph construction and compilation
3. Test persistence and checkpointing
4. Test error handling in routing functions

### Integration Tests
1. Test complete workflow execution with simulated inputs
2. Test interaction between sequential nodes
3. Test parallel execution paths
4. Test persistence across multiple invocations

### Performance Tests
1. Test workflow execution latency
2. Test memory usage during execution
3. Test checkpoint serialization performance
4. Test multi-user concurrency with separate thread IDs

## Effort Estimation
- **Estimated Level of Effort**: Medium (3-5 days)
- **Estimated Story Points**: 5
- **Skills Required**: Python, LangGraph, Graph Theory, State Management

## Code References
1. Example graph definition: `/research/langgraph/examples/vanta_simplified_example.py:255-287`
2. Dual-Track Processing routing: `/Development/Architecture/COMPONENT_SPECIFICATIONS/DUAL_TRACK_PROCESSING.md:249-307`

## Additional Resources
1. [LangGraph Documentation on Conditional Edges](https://langchain-ai.github.io/langgraph/)
2. [LangGraph Documentation on Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)

---

## Implementation Guidance

### Graph Structure Implementation

The complete graph structure should be implemented as follows:

```python
# Create our graph
workflow = StateGraph(VANTAState)

# Add our nodes
workflow.add_node("check_activation", check_activation)
workflow.add_node("process_audio", process_audio)
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("router_node", router_node)
workflow.add_node("local_model_node", local_model_node)
workflow.add_node("api_model_node", api_model_node)
workflow.add_node("integration_node", integration_node)
workflow.add_node("synthesize_speech", synthesize_speech)
workflow.add_node("update_memory", update_memory)

# Add conditional routing functions
def should_process(state: VANTAState) -> str:
    """Determines if we should process audio based on activation status."""
    if state["activation"]["status"] == ActivationStatus.INACTIVE:
        return "end"
    return "continue"

def determine_path(state: VANTAState) -> str:
    """Determines which processing path to take."""
    try:
        path = state["memory"]["processing"]["path"]
        if path == "local":
            return "local"
        elif path == "api":
            return "api"
        else:  # "parallel" or any other value
            return "parallel"
    except (KeyError, TypeError):
        # Default to parallel if path not specified
        return "parallel"

def check_processing_complete(state: VANTAState) -> str:
    """Checks if processing is complete and we can integrate responses."""
    try:
        processing = state["memory"]["processing"]
        path = processing.get("path", "parallel")
        
        # Check appropriate completion flags based on path
        if path == "local" and processing.get("local_completed", False):
            return "ready"
        elif path == "api" and processing.get("api_completed", False):
            return "ready"
        elif path == "parallel":
            # For parallel, check if either is complete
            if processing.get("local_completed", False) or processing.get("api_completed", False):
                return "ready"
        
        # Not ready for integration yet
        return "waiting"
    except (KeyError, TypeError):
        return "waiting"

# Define our edges
workflow.set_entry_point("check_activation")

# Conditional edge after check_activation
workflow.add_conditional_edges(
    "check_activation",
    should_process,
    {
        "continue": "process_audio",
        "end": END
    }
)

# Sequential edges for audio processing and context retrieval
workflow.add_edge("process_audio", "retrieve_context")
workflow.add_edge("retrieve_context", "router_node")

# Conditional edges for routing to appropriate processing path
workflow.add_conditional_edges(
    "router_node",
    determine_path,
    {
        "local": "local_model_node",
        "api": "api_model_node",
        "parallel": "parallel_branch"
    }
)

# For parallel processing, create a branch
workflow.add_node("parallel_branch", lambda state: {})
workflow.add_edge("parallel_branch", "local_model_node")
workflow.add_edge("parallel_branch", "api_model_node")

# Both model nodes lead to integration check
workflow.add_edge("local_model_node", "integration_check")
workflow.add_edge("api_model_node", "integration_check")

# Add integration check node (empty node for routing)
workflow.add_node("integration_check", lambda state: {})

# Conditional edge to wait for processing or proceed to integration
workflow.add_conditional_edges(
    "integration_check",
    check_processing_complete,
    {
        "ready": "integration_node",
        "waiting": "integration_check"  # Loop back until ready
    }
)

# Final edges for response synthesis and memory update
workflow.add_edge("integration_node", "synthesize_speech")
workflow.add_edge("synthesize_speech", "update_memory")
workflow.add_edge("update_memory", END)

# Set up persistence
checkpointer = InMemorySaver()  # Or other saver implementation

# Compile the graph
graph = workflow.compile(checkpointer=checkpointer)
```

### Conditional Routing Functions

#### should_process

```python
def should_process(state: VANTAState) -> str:
    """
    Determines if we should process audio based on activation status.
    
    This function checks if the system is currently activated and should
    proceed with processing the audio input, or if it should end the workflow.
    
    Args:
        state: Current VANTA state
        
    Returns:
        str: "continue" if processing should continue, "end" otherwise
    """
    try:
        if state["activation"]["status"] == ActivationStatus.INACTIVE:
            return "end"
        return "continue"
    except KeyError:
        # If activation status is missing, assume inactive
        return "end"
```

#### determine_path

```python
def determine_path(state: VANTAState) -> str:
    """
    Determines which processing path to take based on routing decision.
    
    This function examines the routing decision made by the router_node
    and directs the workflow to the appropriate processing path (local,
    API, or parallel).
    
    Args:
        state: Current VANTA state
        
    Returns:
        str: "local", "api", or "parallel" based on processing path
    """
    try:
        path = state["memory"]["processing"]["path"]
        if path == "local":
            return "local"
        elif path == "api":
            return "api"
        else:  # "parallel" or any other value
            return "parallel"
    except (KeyError, TypeError):
        # Default to parallel if path not specified
        logger.warning("Processing path not specified, defaulting to parallel")
        return "parallel"
```

#### check_processing_complete

```python
def check_processing_complete(state: VANTAState) -> str:
    """
    Checks if processing is complete and we can integrate responses.
    
    This function examines the processing state to determine if the
    required models have completed their processing and we can proceed
    to response integration.
    
    Args:
        state: Current VANTA state
        
    Returns:
        str: "ready" if processing is complete, "waiting" otherwise
    """
    try:
        processing = state["memory"]["processing"]
        path = processing.get("path", "parallel")
        
        # Check appropriate completion flags based on path
        if path == "local" and processing.get("local_completed", False):
            return "ready"
        elif path == "api" and processing.get("api_completed", False):
            return "ready"
        elif path == "parallel":
            # For parallel, we can proceed if either is complete
            if processing.get("local_completed", False) or processing.get("api_completed", False):
                return "ready"
            
            # Check timeout for parallel processing
            start_time = processing.get("start_time")
            if start_time:
                current_time = time.time()
                if current_time - start_time > processing.get("timeout", 10):
                    # If we've waited too long, use whatever we have
                    logger.warning("Processing timeout reached, proceeding with available results")
                    return "ready"
        
        # Not ready for integration yet
        return "waiting"
    except (KeyError, TypeError) as e:
        logger.error(f"Error checking processing completion: {e}")
        return "waiting"
```

### Persistence Implementation

For persistence across conversations:

```python
# Create a persistent saver (choose based on deployment needs)
def create_checkpointer(config):
    """Create an appropriate checkpointer based on configuration."""
    persistence_type = config.get("persistence", "memory")
    
    if persistence_type == "memory":
        return InMemorySaver()
    elif persistence_type == "file":
        path = config.get("persistence_path", "./checkpoints")
        return FileSaver(path)
    elif persistence_type == "redis":
        redis_url = config.get("redis_url", "redis://localhost:6379")
        return RedisSaver(redis_url)
    else:
        logger.warning(f"Unknown persistence type: {persistence_type}, defaulting to memory")
        return InMemorySaver()

# Usage in graph compilation
checkpointer = create_checkpointer(config)
graph = workflow.compile(checkpointer=checkpointer)

# Using the graph with thread ID for conversation continuity
def process_input(input_state, thread_id):
    """Process input with persistent conversation state."""
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(input_state, config)
```

### Visualization Support

To support visualization of the workflow:

```python
def visualize_graph(workflow, output_path="workflow_graph.png"):
    """Generate a visualization of the workflow graph."""
    try:
        # Get the DOT representation
        dot_string = workflow.get_dot()
        
        # Save to file using graphviz if available
        try:
            from graphviz import Source
            src = Source(dot_string)
            src.render(output_path, format="png", cleanup=True)
            return f"Graph visualization saved to {output_path}.png"
        except ImportError:
            # If graphviz not available, just save the DOT file
            with open(f"{output_path}.dot", "w") as f:
                f.write(dot_string)
            return f"Graph DOT representation saved to {output_path}.dot"
    except Exception as e:
        return f"Error generating graph visualization: {e}"
```

### Testing Examples

For testing the conditional routing:

```python
def test_should_process():
    # Test with inactive state
    inactive_state = {
        "activation": {"status": ActivationStatus.INACTIVE},
        "messages": [],
        "audio": {},
        "memory": {},
        "config": {}
    }
    assert should_process(inactive_state) == "end"
    
    # Test with processing state
    processing_state = {
        "activation": {"status": ActivationStatus.PROCESSING},
        "messages": [],
        "audio": {},
        "memory": {},
        "config": {}
    }
    assert should_process(processing_state) == "continue"
    
    # Test with missing activation (should default to end)
    missing_state = {
        "messages": [],
        "audio": {},
        "memory": {},
        "config": {}
    }
    assert should_process(missing_state) == "end"

def test_determine_path():
    # Test local path
    local_state = {
        "memory": {"processing": {"path": "local"}},
        "messages": [],
        "audio": {},
        "activation": {},
        "config": {}
    }
    assert determine_path(local_state) == "local"
    
    # Test API path
    api_state = {
        "memory": {"processing": {"path": "api"}},
        "messages": [],
        "audio": {},
        "activation": {},
        "config": {}
    }
    assert determine_path(api_state) == "api"
    
    # Test parallel path
    parallel_state = {
        "memory": {"processing": {"path": "parallel"}},
        "messages": [],
        "audio": {},
        "activation": {},
        "config": {}
    }
    assert determine_path(parallel_state) == "parallel"
    
    # Test missing path (should default to parallel)
    missing_state = {
        "memory": {},
        "messages": [],
        "audio": {},
        "activation": {},
        "config": {}
    }
    assert determine_path(missing_state) == "parallel"
```

These testing examples will help verify that the conditional routing functions work correctly under various conditions.