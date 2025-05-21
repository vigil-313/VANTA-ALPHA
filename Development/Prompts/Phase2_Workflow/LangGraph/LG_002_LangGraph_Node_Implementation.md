# LangGraph Node Implementation Prompt

## Task Identification
- **Task ID**: TASK-LG-002
- **Component**: Core Architecture
- **Phase**: Foundation
- **Priority**: High
- **Related Concepts**: [CON-VANTA-002 Memory Engine, CON-VANTA-008 LangGraph Integration]

## Task Description
Implement the core LangGraph node functions for VANTA that will process user inputs, manage memory operations, and coordinate the dual-track model responses. These nodes will form the primary workflow of the VANTA system, handling voice pipeline outputs, memory retrieval, local and API model processing, and response integration.

### Objective
Create a comprehensive set of LangGraph nodes that implement VANTA's core processing workflow.

### Success Criteria
- A complete set of node functions for all core VANTA components
- Proper state management in each node function
- Support for both local and API model processing
- Clean separation of concerns between different nodes
- Comprehensive docstrings and comments

## Implementation Context
The LangGraph node functions depend on the LangGraph state definition (TASK-LG-001) and provide the actual implementation of VANTA's processing workflow. These nodes will be composed into a graph structure in TASK-LG-003 to create the complete VANTA workflow.

### Task Dependencies
- **TASK-LG-001**: LangGraph State Definition (Required)
- **VOICE_001**: Audio Processing Infrastructure (Completed)
- **VOICE_002**: Voice Activity Detection (Completed)
- **VOICE_003**: Speech-to-Text Integration (Completed)
- **VOICE_004**: Text-to-Speech Integration (Completed)
- **LM_001**: Local Model Integration (Completed)
- **AM_001**: API Model Client (Completed)
- **AM_002**: Streaming Response Handling (Completed)
- **MEM_001**: Memory System (Completed)

### Architectural Context
The node functions provide the implementation logic for VANTA's workflow in the LangGraph framework. They will interact with the voice pipeline, memory system, and dual-track processing components. Each node function should be focused on a specific aspect of processing, following the single responsibility principle. Together, they implement the hybrid architecture by coordinating inputs and outputs across both local and cloud model paths.

### Technical Requirements
1. Pure functions that take state as input and return partial state updates
2. Clear docstrings explaining the purpose of each node
3. Comprehensive input validation and error handling
4. Support for LangGraph's state management approach
5. Integration with completed VANTA components

## Implementation Details

### Interfaces
Each node function should follow this signature pattern:

```python
def node_name(state: VANTAState) -> Dict:
    """
    Brief description of what this node does.
    
    Args:
        state: The current VANTA state
        
    Returns:
        Dict: Partial state updates
    """
    # Implementation
    return state_updates
```

### Primary Node Functions

The primary nodes to implement are:

1. **check_activation**: Determines if VANTA should activate based on the current mode
2. **process_audio**: Processes audio input using Whisper for transcription
3. **retrieve_context**: Retrieves relevant context from the memory system
4. **router_node**: Analyzes input and determines processing path (local, API, or both)
5. **local_model_node**: Processes the query with the local model
6. **api_model_node**: Processes the query with the API model
7. **integration_node**: Integrates responses from both processing tracks
8. **synthesize_speech**: Converts text to speech using CSM
9. **update_memory**: Updates memory system with the current conversation

### Inputs
Each node function receives the full VANTA state and extracts relevant components:

| Node Function | Key Inputs | Description |
|---------------|------------|-------------|
| check_activation | activation.status, config.activation_mode, audio.current_audio | Determines activation based on mode and audio |
| process_audio | audio.current_audio, activation.status | Processes audio when in active state |
| retrieve_context | messages, activation.status | Retrieves context based on last message |
| router_node | messages, memory.retrieved_context | Determines processing path for query |
| local_model_node | messages, memory.retrieved_context, memory.processing.path | Processes with local model if appropriate |
| api_model_node | messages, memory.retrieved_context, memory.processing.path | Processes with API model if appropriate |
| integration_node | memory.processing | Integrates responses from both paths |
| synthesize_speech | messages, activation.status | Synthesizes speech from last AI message |
| update_memory | messages, audio.audio_path | Updates memory with conversation history |

### Outputs
Each node function returns partial state updates:

| Node Function | Key Outputs | Description |
|---------------|-------------|-------------|
| check_activation | activation.status | Updated activation status |
| process_audio | messages, audio, memory.audio_entries | Adds user message and updates audio state |
| retrieve_context | memory.retrieved_context | Adds retrieved context information |
| router_node | memory.processing | Sets processing path and reasoning |
| local_model_node | memory.processing.local_* | Adds local model response and metadata |
| api_model_node | memory.processing.api_* | Adds API model response and metadata |
| integration_node | messages, activation.status | Adds AI message with integrated response |
| synthesize_speech | audio.last_synthesis, activation.status | Updates with synthesis information |
| update_memory | memory.conversation_history | Updates conversation history |

### State Management
Each node must follow these state management principles:

1. Read from state but never modify the input state directly
2. Return only the fields that need to be updated
3. Handle special fields like `messages` according to their reducer annotations
4. Update nested dictionaries by including the full path (e.g., `memory.processing.local_response`)

### Algorithm / Processing Steps

#### check_activation
1. Get current activation mode from config
2. Check current activation status
3. If already processing or speaking, continue
4. If in continuous mode, activate when audio is present
5. If in wake word mode, activate when wake word is detected
6. If in scheduled mode, activate at scheduled times
7. Return updated activation status

#### process_audio
1. Get current audio data
2. Skip if inactive or no audio
3. Transcribe audio using Whisper integration
4. Create audio metadata entry
5. Return updates with new human message and audio metadata

#### retrieve_context
1. Skip if inactive or no messages
2. Get last message content
3. Use memory system to retrieve relevant context
4. Return memory updates with retrieved context

#### router_node
1. Skip if inactive or no messages
2. Get last message and context
3. Analyze query complexity and requirements
4. Determine processing path (local, API, or parallel)
5. Return processing metadata updates

#### local_model_node
1. Skip if not using local processing path
2. Get query and context
3. Construct prompt for local model
4. Generate response with local model
5. Return processing updates with local model response

#### api_model_node
1. Skip if not using API processing path
2. Get conversation history and context
3. Prepare messages for API request
4. Generate response with API client
5. Return processing updates with API model response

#### integration_node
1. Get processing results for both paths
2. Check if processing is complete for the selected path
3. Choose between local and API responses based on configured strategy
4. Combine responses if using parallel processing
5. Return message update with final response

#### synthesize_speech
1. Skip if not in speaking mode
2. Get last AI message content
3. Generate speech using TTS integration
4. Update audio state with synthesis information
5. Reset activation to inactive

#### update_memory
1. Skip if no complete conversation pair
2. Get last user-assistant exchange
3. Create memory entry with messages and metadata
4. Update memory state with new conversation history

### Error Handling
1. Invalid state: Check for required fields before processing
2. Transcription errors: Log and provide generic transcription
3. Context retrieval failures: Continue with empty context
4. Model generation failures: Fall back to alternate path or generic response
5. Speech synthesis errors: Log and skip audio generation

### Performance Considerations
1. Lazy loading: Only load models when needed
2. Asynchronous processing: When appropriate for API calls
3. Resource monitoring: Track memory and processing time
4. Incremental updates: Only return changed fields

## Validation Criteria
1. All node functions handle empty or partial states gracefully
2. State updates follow LangGraph conventions
3. Error handling covers common failure cases
4. Functions include comprehensive docstrings
5. Integration with VANTA components works correctly

## Testing Approach

### Unit Tests
1. Test each node function with various input states
2. Test handling of empty or partial states
3. Test error handling in each node
4. Test state update patterns for correctness

### Integration Tests
1. Test full workflow with simulated inputs
2. Test interaction between nodes in sequence
3. Test integration with voice pipeline components
4. Test integration with memory system
5. Test integration with local and API models

### Performance Tests
1. Test processing time for each node function
2. Test memory usage patterns
3. Test full workflow latency

## Effort Estimation
- **Estimated Level of Effort**: Large (1-2 weeks)
- **Estimated Story Points**: 8
- **Skills Required**: Python, LangGraph, Audio Processing, LLM Integration

## Code References
1. Example node functions: `/research/langgraph/examples/vanta_simplified_example.py:58-253`
2. Dual-Track Processing specification: `/Development/Architecture/COMPONENT_SPECIFICATIONS/DUAL_TRACK_PROCESSING.md:134-246`
3. VANTA state definition: (To be implemented in TASK-LG-001)

## Additional Resources
1. [LangGraph Documentation on Node Functions](https://langchain-ai.github.io/langgraph/)
2. [LangGraph Integration Notes](/research/langgraph/integration_notes/LANGGRAPH_VANTA_INTEGRATION.md)

---

## Implementation Guidance

### Node Implementation Strategy

1. **Start with Voice Pipeline Nodes**:
   - `check_activation`
   - `process_audio`
   - `synthesize_speech`

   These nodes integrate directly with existing voice pipeline components.

2. **Implement Memory Nodes**:
   - `retrieve_context`
   - `update_memory`
   
   These nodes integrate with the Memory System.

3. **Implement Dual-Track Processing Nodes**:
   - `router_node`
   - `local_model_node`
   - `api_model_node`
   - `integration_node`
   
   These nodes implement the core dual-track processing flow.

### Implementation Example: check_activation

Here's an example implementation of the `check_activation` node:

```python
def check_activation(state: VANTAState) -> Dict:
    """
    Determines if VANTA should activate based on the current mode.
    
    This node checks the current activation mode (continuous, wake_word, scheduled)
    and determines whether the system should be activated based on audio input.
    
    Args:
        state: Current VANTA state
        
    Returns:
        Dict: Updated activation status
    """
    # Extract required fields
    try:
        activation_mode = state["config"]["activation_mode"]
        current_status = state["activation"]["status"]
        
        # If already processing or speaking, continue the pipeline
        if current_status in [ActivationStatus.PROCESSING, ActivationStatus.SPEAKING]:
            return {"activation": {"status": ActivationStatus.PROCESSING}}
        
        # Otherwise, check if we should activate based on the mode
        audio_data = state["audio"].get("current_audio")
        
        # No audio data, remain inactive
        if not audio_data:
            return {"activation": {"status": ActivationStatus.INACTIVE}}
        
        # Wake word detection (simplified)
        wake_word_detected = False
        if isinstance(audio_data, str):
            wake_word_detected = "hey vanta" in audio_data.lower()
        else:
            # Assume audio_data is processed by the Voice Pipeline's VAD component
            wake_word_detector = VoiceActivityDetector()
            wake_word_detected = wake_word_detector.detect_wake_word(audio_data)
        
        # Continuous mode: always activate with audio
        if activation_mode == ActivationMode.CONTINUOUS:
            return {"activation": {"status": ActivationStatus.PROCESSING}}
        
        # Wake word mode: activate only if wake word detected
        elif activation_mode == ActivationMode.WAKE_WORD and wake_word_detected:
            return {"activation": {"status": ActivationStatus.PROCESSING}}
        
        # Scheduled mode: activate based on schedule
        elif activation_mode == ActivationMode.SCHEDULED:
            current_time = datetime.now().strftime("%H:%M")
            scheduled_times = state["config"].get("scheduled_times", [])
            
            if current_time in scheduled_times:
                return {"activation": {"status": ActivationStatus.PROCESSING}}
        
        # Default: remain inactive
        return {"activation": {"status": ActivationStatus.INACTIVE}}
        
    except KeyError as e:
        # Handle missing required fields
        logger.error(f"Missing required field: {e}")
        return {"activation": {"status": ActivationStatus.INACTIVE}}
```

### Implementation Example: process_audio

Here's an example implementation of the `process_audio` node:

```python
def process_audio(state: VANTAState) -> Dict:
    """
    Processes audio input using Whisper for transcription.
    
    This node takes the current audio data, uses the Voice Pipeline's
    transcription component to convert it to text, and adds a new
    user message to the conversation.
    
    Args:
        state: Current VANTA state
        
    Returns:
        Dict: Updates with new user message and audio metadata
    """
    try:
        # Skip if no audio or not in processing mode
        audio_data = state["audio"].get("current_audio")
        if not audio_data or state["activation"]["status"] != ActivationStatus.PROCESSING:
            return {}
        
        # Transcribe audio using Whisper via the Voice Pipeline
        transcriber = SpeechToTextProcessor()
        transcription = transcriber.transcribe(audio_data)
        
        # Store the transcription result and metadata
        timestamp = datetime.now().isoformat()
        audio_metadata = {
            "timestamp": timestamp,
            "transcription": transcription,
            "audio_reference": state["audio"].get("audio_path", ""),
        }
        
        # Calculate a unique ID for this audio entry
        entry_id = f"audio_{int(time.time())}_{hash(transcription) % 10000}"
        
        # Return state updates with new message and metadata
        return {
            "messages": [HumanMessage(content=transcription)],
            "audio": {
                "last_transcription": transcription, 
                "metadata": audio_metadata
            },
            "memory": {
                "audio_entries": state["memory"].get("audio_entries", []) + [{
                    "id": entry_id,
                    "timestamp": timestamp,
                    "transcription": transcription,
                    "audio_path": state["audio"].get("audio_path", "")
                }]
            }
        }
    
    except Exception as e:
        # Handle errors in transcription
        logger.error(f"Error transcribing audio: {e}")
        transcription = "I couldn't understand what you said. Could you please repeat that?"
        
        return {
            "messages": [HumanMessage(content=transcription)],
            "audio": {"last_transcription": transcription, "error": str(e)},
        }
```

### Testing Strategy

For each node function, create:

1. **Basic Tests**: Test with minimal valid state
2. **Edge Case Tests**: Test with empty fields, missing data
3. **Error Case Tests**: Test with invalid data that should trigger error handling
4. **Integration Tests**: Test interaction with actual components

Example test for `check_activation`:

```python
def test_check_activation_continuous_mode():
    # Create test state with continuous mode
    state = {
        "config": {"activation_mode": ActivationMode.CONTINUOUS},
        "activation": {"status": ActivationStatus.LISTENING},
        "audio": {"current_audio": "some audio data"},
        "messages": [],
        "memory": {}
    }
    
    # Call the node function
    result = check_activation(state)
    
    # Verify that it activates with continuous mode
    assert result["activation"]["status"] == ActivationStatus.PROCESSING
```

### Documentation Guidelines

For each node function, document:

1. **Purpose**: What the node does in the workflow
2. **Inputs**: What parts of the state it reads
3. **Outputs**: What parts of the state it updates
4. **Exceptions**: What errors it might encounter
5. **Integration**: How it integrates with other VANTA components