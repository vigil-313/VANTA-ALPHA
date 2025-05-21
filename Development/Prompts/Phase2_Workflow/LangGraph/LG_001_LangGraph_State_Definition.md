# LangGraph State Definition Implementation Prompt

## Task Identification
- **Task ID**: TASK-LG-001
- **Component**: Core Architecture
- **Phase**: Foundation
- **Priority**: High
- **Related Concepts**: [CON-VANTA-002 Memory Engine, CON-VANTA-008 LangGraph Integration]

## Task Description
Implement the core LangGraph state definition for VANTA that will serve as the foundation for all workflow components. This state definition will provide a structured TypedDict class that represents the complete state of the VANTA system, including conversation messages, audio processing metadata, memory references, configuration, and activation status.

### Objective
Create a well-defined, type-safe state object that can be used by all LangGraph nodes in the VANTA system.

### Success Criteria
- A comprehensive state definition that supports all VANTA components
- Type annotations for all state components with appropriate reducers
- Documentation explaining each state field's purpose and usage
- Integration with LangGraph's state management system
- Support for serialization/deserialization of complex objects

## Implementation Context
The LangGraph state definition is the foundation upon which all VANTA components will interact. It provides a shared data model that enables different components (Voice Pipeline, Memory Engine, Local Model, API Model, etc.) to exchange information in a structured way. This task is a prerequisite for all further LangGraph implementation tasks.

### Task Dependencies
- **ENV_002**: Docker Environment (Completed)
- **ENV_003**: Model Preparation (Completed)
- **ENV_004**: Test Framework (Completed)

### Architectural Context
The state definition will be aligned with the hybrid architecture, supporting both local and API model integration. It will accommodate the dual-track processing architecture by including fields for both local and API model state and responses. The state structure will follow LangGraph best practices while accommodating VANTA's specific requirements.

### Technical Requirements
1. Use Python 3.10+ TypedDict for type safety
2. Include annotations for LangGraph reducers (add_messages, etc.)
3. Support for complex nested objects with proper serialization
4. Support for all VANTA components (Voice, Memory, Local Model, API Model, etc.)
5. Encapsulate LangGraph-specific details to maintain clean interfaces

## Implementation Details

### Interfaces
The primary interface is the VANTAState TypedDict class:

```python
from typing import Annotated, Dict, List, Optional, Sequence, TypedDict, Union
from enum import Enum
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages

# Enums for VANTA states
class ActivationMode(str, Enum):
    CONTINUOUS = "continuous"
    WAKE_WORD = "wake_word"
    SCHEDULED = "scheduled"
    
class ActivationStatus(str, Enum):
    INACTIVE = "inactive"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

# State definition with typed annotations
class VANTAState(TypedDict):
    """Full state for VANTA agent."""
    # Conversation messages using add_messages reducer
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Audio processing metadata
    audio: Dict
    # Memory references and context
    memory: Dict
    # System configuration
    config: Dict
    # Current activation state
    activation: Dict
    # Other components as needed...
```

### Inputs
The VANTAState will receive inputs from all VANTA components, including:

| Input | Type | Description |
|-------|------|-------------|
| User messages | HumanMessage | Transcribed user inputs from the Voice Pipeline |
| Audio metadata | Dict | Information about audio processing, including transcriptions and synthesis data |
| Memory entries | Dict | References to content in short-term and long-term memory |
| Configuration updates | Dict | System-wide configuration changes |
| Activation updates | Dict | Changes to activation status and mode |
| Model responses | Dict | Responses from local and API models |

### Outputs
The VANTAState is accessed by all VANTA components, providing:

| Output | Type | Description |
|--------|------|-------------|
| Complete conversation history | Sequence[BaseMessage] | Full history of interactions for context |
| Current audio state | Dict | Latest audio processing information |
| Retrieved memory context | Dict | Relevant information retrieved from memory |
| System configuration | Dict | Current system settings |
| Activation status | Dict | Current activation mode and status |
| Processing results | Dict | Results from local and API models |

### State Management
The state definition will include the following primary sections:

| State Field | Type | Read/Write | Description |
|-------------|------|------------|-------------|
| messages | Sequence[BaseMessage] | Read/Write | Conversation history using add_messages reducer |
| audio | Dict | Read/Write | Audio processing metadata, including transcription and synthesis data |
| memory | Dict | Read/Write | Memory references and retrieved context |
| config | Dict | Read/Write | System configuration, including model settings and activation modes |
| activation | Dict | Read/Write | Current system activation state and mode |
| processing | Dict | Read/Write | Dual-track processing state and responses |

### Algorithm / Processing Steps
1. Define the core VANTAState TypedDict with all required fields
2. Add appropriate type annotations for each field, including LangGraph reducers
3. Create Enum classes for various status options (activation modes, etc.)
4. Document each field with comprehensive docstrings
5. Implement serialization/deserialization helpers for complex objects
6. Create utility functions for common state manipulation operations

### Error Handling
1. Type mismatches: Implement runtime type checking for critical components
2. Missing fields: Ensure defaults are provided for optional fields
3. Serialization errors: Handle complex objects with custom serialization

### Performance Considerations
1. Minimize state size to ensure efficient serialization/deserialization
2. Consider memory usage when storing large objects in state
3. Structure state to allow efficient partial updates

## Validation Criteria
1. All required fields are included in the state definition
2. Type annotations are correctly applied, including appropriate reducers
3. State can be serialized and deserialized without data loss
4. Documentation clearly explains each state field and its purpose
5. State structure supports all VANTA components

## Testing Approach

### Unit Tests
1. Test creation of empty state with defaults
2. Test adding messages to state
3. Test updating various state components
4. Test serialization/deserialization of state

### Integration Tests
1. Test state updates from Voice Pipeline
2. Test memory system interaction with state
3. Test local and API model integration with state
4. Test complete workflow using the defined state

### Performance Tests
1. Test serialization/deserialization performance with various state sizes
2. Test memory usage with large conversation histories
3. Benchmark state update operations

## Effort Estimation
- **Estimated Level of Effort**: Medium (3-5 days)
- **Estimated Story Points**: 5
- **Skills Required**: Python, LangGraph, Type Hints, State Management

## Code References
1. Example LangGraph state definition: `/research/langgraph/examples/vanta_simplified_example.py:40-52`
2. Dual-Track Processing specification: `/Development/Architecture/COMPONENT_SPECIFICATIONS/DUAL_TRACK_PROCESSING.md:165-173`
3. LangGraph integration notes: `/research/langgraph/integration_notes/LANGGRAPH_VANTA_INTEGRATION.md:93-103`

## Additional Resources
1. [LangGraph Documentation on State Management](https://langchain-ai.github.io/langgraph/)
2. [TypedDict Reference](https://www.python.org/dev/peps/pep-0589/)
3. [LangGraph State Serialization](https://langchain-ai.github.io/langgraph/concepts/persistence/)

---

## Implementation Guidance

### State Definition Structure

The VANTAState should be structured as follows:

1. **messages**: Conversation history
   ```python
   messages: Annotated[Sequence[BaseMessage], add_messages]
   ```

2. **audio**: Audio processing metadata
   ```python
   audio: Dict[str, Any]  # Should include:
   # current_audio: Current audio data or reference
   # last_transcription: Last transcribed text
   # metadata: Audio processing metadata (timestamps, etc.)
   # last_synthesis: Information about last synthesized audio
   ```

3. **memory**: Memory references and context
   ```python
   memory: Dict[str, Any]  # Should include:
   # audio_entries: List of audio references stored in memory
   # conversation_history: List of stored conversation entries
   # retrieved_context: Context retrieved from memory for current query
   # embeddings: References to embedding vectors
   ```

4. **config**: System configuration
   ```python
   config: Dict[str, Any]  # Should include:
   # activation_mode: Current activation mode (wake word, continuous, scheduled)
   # model_settings: Settings for local and API models
   # voice_settings: Voice characteristics for TTS
   # scheduled_times: Times for scheduled activations
   ```

5. **activation**: Current system state
   ```python
   activation: Dict[str, Any]  # Should include:
   # status: Current status (inactive, listening, processing, speaking)
   # last_activation_time: Timestamp of last activation
   # wake_word_detected: Whether wake word was detected
   ```

6. **processing**: Dual-track processing state
   ```python
   processing: Dict[str, Any]  # Should include:
   # path: Current processing path (local, api, parallel)
   # local_response: Response from local model
   # api_response: Response from API model
   # local_completed: Whether local processing is complete
   # api_completed: Whether API processing is complete
   # local_time: Processing time for local model
   # api_time: Processing time for API model
   ```

### Utility Functions

Consider implementing utility functions for common state operations:

```python
def create_empty_state() -> VANTAState:
    """Create an empty state with default values."""
    return {
        "messages": [],
        "audio": {},
        "memory": {},
        "config": {"activation_mode": ActivationMode.WAKE_WORD},
        "activation": {"status": ActivationStatus.INACTIVE},
        "processing": {}
    }

def update_state(state: VANTAState, updates: Dict) -> VANTAState:
    """Update state with changes, handling special cases like messages."""
    # Implementation details...
    pass
```

### Serialization Considerations

Ensure that complex objects can be properly serialized/deserialized:

```python
def serialize_state(state: VANTAState) -> Dict:
    """Convert state to serializable dictionary."""
    # Implementation details...
    pass

def deserialize_state(serialized: Dict) -> VANTAState:
    """Convert serialized dictionary back to state."""
    # Implementation details...
    pass
```

These functions will be useful for persistence and checkpointing in LangGraph.

### Documentation Guidelines

For each state field, include comprehensive docstrings explaining:
- Purpose and meaning of the field
- Expected structure and values
- How and when it should be updated
- Which components typically read from or write to it
- Example values or usage patterns

Include class-level docstrings that explain the overall state structure and how it relates to the VANTA architecture.