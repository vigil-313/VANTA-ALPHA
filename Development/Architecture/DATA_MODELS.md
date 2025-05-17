# Data Models [DOC-DEV-ARCH-2]

## Overview

This document defines the core data structures and schemas used in the VANTA system. These data models ensure consistency across components and provide a common understanding of the system's state.

## State Model

The central state model for VANTA is implemented using LangGraph's typed state system. This provides type safety and explicit state management throughout the application.

```python
from typing import Annotated, Dict, List, Optional, Sequence, TypedDict, Union
from enum import Enum
from datetime import datetime
from langchain_core.messages import BaseMessage
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
```

### State Components

#### Messages

The messages field contains the conversation history using LangChain message types:

```python
messages: Annotated[Sequence[BaseMessage], add_messages]
```

- Contains `HumanMessage`, `AIMessage`, and occasionally `SystemMessage` objects
- Managed by the `add_messages` reducer to handle appending efficiently
- Retains full conversation history within the session

#### Audio

The audio dictionary contains metadata about the audio processing:

```python
audio: Dict[str, Any] = {
    "current_audio": Optional[bytes],  # Current audio buffer being processed
    "audio_path": Optional[str],       # Path to the current audio file
    "last_transcription": Optional[str],  # Most recent transcription result
    "last_synthesis": Optional[Dict],  # Metadata about last speech synthesis
    "metadata": Dict,                  # Additional audio processing metadata
}
```

#### Memory

The memory dictionary contains references to both working and long-term memory:

```python
memory: Dict[str, Any] = {
    "conversation_history": List[Dict],  # Historical conversations
    "retrieved_context": Dict,         # Context retrieved for current turn
    "audio_entries": List[Dict],       # References to audio recordings
    "last_interaction": str,           # ISO timestamp of last interaction
    "semantic_entries": List[Dict],    # Vector-indexed semantic memories
}
```

#### Config

The config dictionary contains system configuration settings:

```python
config: Dict[str, Any] = {
    "activation_mode": ActivationMode,  # Current activation mode
    "scheduled_times": Optional[List[str]],  # Times for scheduled mode
    "voice_id": str,                   # TTS voice identifier
    "local_model_config": Dict,        # Configuration for local model
    "api_model_config": Dict,          # Configuration for API model
    "privacy_settings": Dict,          # User privacy preferences
    "performance_mode": str,           # Balance mode (speed vs quality)
}
```

#### Activation

The activation dictionary tracks the current system activation state:

```python
activation: Dict[str, Any] = {
    "status": ActivationStatus,        # Current activation status
    "wake_word_detected": bool,        # Whether wake word was detected
    "activation_timestamp": Optional[str],  # When activation occurred
    "confidence": float,               # Confidence in current activation
}
```

## Memory Models

### Working Memory

Working memory is primarily stored in the LangGraph state and represents the active session context:

```python
class WorkingMemory:
    """In-session memory for VANTA."""
    messages: List[BaseMessage]       # Active conversation
    current_context: Dict             # Currently relevant context
    user_profile: Dict                # Active user information
    session_metadata: Dict            # Session-specific information
    audio_references: Dict            # References to session audio
```

### Long-Term Memory

Long-term memory is stored persistently and structured for efficient retrieval:

```python
class ConversationEntry:
    """A single conversation turn in long-term memory."""
    id: str                          # Unique identifier
    user_message: str                # User's message content
    assistant_message: str           # VANTA's response
    timestamp: str                   # ISO format timestamp
    audio_reference: Optional[str]   # Path to audio recording
    metadata: Dict                   # Additional metadata
    embedding: Optional[List[float]] # Vector embedding for retrieval

class SemanticMemory:
    """Semantic memory entry for vector storage."""
    id: str                          # Unique identifier
    content: str                     # Memory content
    source: str                      # Source of the memory
    timestamp: str                   # When the memory was created
    importance: float                # Importance score (0-1)
    embedding: List[float]           # Vector embedding for retrieval
    metadata: Dict                   # Additional context and tags

class UserPreference:
    """Stored user preference."""
    id: str                          # Preference identifier
    category: str                    # Preference category
    value: Any                       # Preference value
    confidence: float                # Confidence in this preference
    last_updated: str                # ISO timestamp of last update
    source_references: List[str]     # References to source interactions
```

## Voice Processing Models

### Audio Processing

```python
class AudioSegment:
    """A segment of audio for processing."""
    id: str                          # Segment identifier
    audio_data: bytes                # Raw audio bytes
    sample_rate: int                 # Sample rate in Hz
    channels: int                    # Number of audio channels
    timestamp: str                   # ISO timestamp when recorded
    duration: float                  # Duration in seconds
    metadata: Dict                   # Additional audio metadata

class TranscriptionResult:
    """Result from speech-to-text processing."""
    text: str                        # Transcribed text
    confidence: float                # Overall confidence score
    word_timestamps: Optional[List[Dict]]  # Timing for each word
    speaker_id: Optional[str]        # Identified speaker if available
    language: str                    # Detected language
    alternatives: Optional[List[Dict]]  # Alternative transcriptions
    metadata: Dict                   # Additional metadata
```

### Speech Synthesis

```python
class SynthesisRequest:
    """Request for text-to-speech synthesis."""
    text: str                        # Text to synthesize
    voice_id: str                    # Voice identifier
    speed: float                     # Speech rate modifier
    pitch: float                     # Pitch modifier
    emphasis_markers: Optional[Dict] # Word emphasis information
    ssml: Optional[str]              # SSML markup if available
    emotion: Optional[str]           # Emotional tone

class SynthesisResult:
    """Result from text-to-speech processing."""
    audio_data: bytes                # Raw audio bytes
    sample_rate: int                 # Sample rate in Hz
    format: str                      # Audio format (e.g., "wav")
    duration: float                  # Duration in seconds
    word_timings: Optional[List[Dict]]  # Timing for each word
    metadata: Dict                   # Additional metadata
```

## Model Processing Models

### Router Decision

```python
class RouterDecision:
    """Decision about which model path to use."""
    path: str                        # "local" or "api"
    confidence: float                # Confidence in this decision
    reasoning: str                   # Reason for this decision
    query_complexity: float          # Estimated query complexity
    time_sensitivity: float          # Time sensitivity score
    privacy_sensitivity: float       # Privacy sensitivity score
```

### Local Model Processing

```python
class LocalModelRequest:
    """Request to the local language model."""
    prompt: str                      # Input prompt
    context: List[Dict]              # Conversation context
    parameters: Dict                 # Generation parameters
    max_tokens: int                  # Maximum tokens to generate
    stop_sequences: List[str]        # Sequences that stop generation

class LocalModelResponse:
    """Response from the local language model."""
    text: str                        # Generated text
    finish_reason: str               # Reason generation stopped
    tokens_used: int                 # Total tokens used
    generation_time: float           # Time taken to generate
    metadata: Dict                   # Additional metadata
```

### API Model Processing

```python
class APIModelRequest:
    """Request to the API language model."""
    messages: List[Dict]             # Messages in the conversation
    model: str                       # Model identifier
    temperature: float               # Temperature parameter
    max_tokens: int                  # Maximum tokens to generate
    stream: bool                     # Whether to stream the response
    additional_params: Dict          # Additional API parameters

class APIModelResponse:
    """Response from the API language model."""
    content: str                     # Generated content
    finish_reason: str               # Reason generation stopped
    model: str                       # Model used for generation
    usage: Dict                      # Token usage statistics
    metadata: Dict                   # Additional metadata
```

## Persistent Storage Models

### Vector Store Schema

```python
class VectorEntry:
    """Entry in the vector database."""
    id: str                          # Unique identifier
    vector: List[float]              # Embedding vector
    text: str                        # Original text
    metadata: Dict                   # Searchable metadata
    timestamp: str                   # When the entry was created
```

### Log Storage Schema

```python
class LogEntry:
    """Entry in the raw log storage."""
    id: str                          # Log entry identifier
    timestamp: str                   # ISO timestamp
    level: str                       # Log level (info, warning, etc.)
    category: str                    # Log category
    message: str                     # Log message
    data: Dict                       # Additional structured data
```

### Configuration Storage Schema

```python
class ConfigurationEntry:
    """Stored configuration entry."""
    key: str                         # Configuration key
    value: Any                       # Configuration value
    scope: str                       # Scope (system, user, session)
    last_updated: str                # When last updated
    description: Optional[str]       # Description of this config
```

## File Storage Structure

The persistent data will be organized in a structured filesystem:

```
/data
  /audio                          # Audio recordings
    /sessions                     # Organized by session
      /{session_id}/              # Session recordings
        input_{timestamp}.wav     # User input
        output_{timestamp}.wav    # System output
  
  /memory                         # Memory storage
    /conversations                # Raw conversation logs
      /{date}/                    # Organized by date
        {timestamp}_{id}.jsonl    # Conversation entries
    /vectors                      # Vector database files
      chroma.db                   # Vector DB files
      embeddings/                 # Embedding storage
  
  /logs                           # System logs
    /system                       # System-level logs
    /components                   # Component-specific logs
      /voice                      # Voice processing logs
      /memory                     # Memory system logs
      /models                     # Model processing logs
  
  /config                         # Configuration storage
    system_config.json            # System-wide configuration
    user_config.json              # User-specific settings
```

## Serialization Formats

### Message Serialization

Messages will be serialized as JSON with a standardized schema:

```json
{
  "id": "msg_123456",
  "role": "user",
  "content": "What's the weather like today?",
  "timestamp": "2025-05-17T12:34:56Z",
  "metadata": {
    "audio_reference": "/data/audio/sessions/sess_123/input_20250517123456.wav",
    "confidence": 0.98,
    "device_info": {
      "type": "microphone",
      "name": "Built-in Microphone"
    }
  }
}
```

### State Serialization

State will be serialized for checkpointing using a structured JSON format:

```json
{
  "version": "0.1.0",
  "timestamp": "2025-05-17T12:35:12Z",
  "session_id": "sess_123",
  "state": {
    "messages": [
      {
        "id": "msg_123456",
        "role": "user",
        "content": "What's the weather like today?",
        "timestamp": "2025-05-17T12:34:56Z"
      },
      {
        "id": "msg_123457",
        "role": "assistant",
        "content": "It's currently sunny and 68 degrees.",
        "timestamp": "2025-05-17T12:35:10Z"
      }
    ],
    "audio": {
      "last_transcription": "What's the weather like today?",
      "last_synthesis": {
        "text": "It's currently sunny and 68 degrees.",
        "audio_path": "/data/audio/sessions/sess_123/output_20250517123510.wav"
      }
    },
    "memory": {
      "last_interaction": "2025-05-17T12:35:10Z",
      "retrieved_context": {
        "weather_preference": "User prefers Celsius"
      }
    },
    "config": {
      "activation_mode": "wake_word",
      "voice_id": "warm_female"
    },
    "activation": {
      "status": "inactive",
      "activation_timestamp": "2025-05-17T12:34:56Z"
    }
  }
}
```

## Type Safety and Validation

The system will employ several approaches to ensure data integrity:

1. **TypedDict Definitions**: Core state uses TypedDict for static typing
2. **Pydantic Models**: Data validation for complex structures
3. **JSON Schema Validation**: Runtime validation for serialized data
4. **Conversion Utilities**: Safe conversion between formats
5. **Error Handlers**: Graceful handling of validation failures

## Migration Strategy

As the system evolves, data models will need to change. The migration strategy includes:

1. **Version Tagging**: All serialized data includes version information
2. **Migration Scripts**: Explicit scripts for version-to-version migration
3. **Forward Compatibility**: New code can read old data formats
4. **Deprecation Path**: Gradual phase-out of old formats
5. **Backup Mechanisms**: Automatic backups before migrations

## Version History

- v0.1.0 - 2025-05-17 - Initial creation [SES-V0-005]