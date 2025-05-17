# Dual Processing Architecture [DOC-RESEARCH-HVA-3]

## Overview

This document details the technical implementation of VANTA's dual-processing approach, which combines local and cloud-based language models to achieve natural conversational interactions. This architecture provides both fast responses and high-quality reasoning while operating within the constraints of consumer hardware.

## Architecture Components

```mermaid
graph TD
    subgraph "User Interaction Layer"
        A[Audio Input] --> B[STT Processing]
        Z[TTS Processing] --> AA[Audio Output]
    end
    
    subgraph "Processing Orchestration Layer"
        B --> C[Input Analysis]
        C --> D{Processing<br/>Router}
        D -->|Simple/Fast Path| E[Local Model<br/>Processing]
        D -->|Complex/Deep Path| F[API Model<br/>Processing]
        
        E --> G[Response<br/>Integration]
        F --> G
        G --> Z
        
        H[Context Manager] <--> D
        H <--> E
        H <--> F
        H <--> G
    end
    
    subgraph "Memory Layer"
        I[Working Memory] <--> H
        J[Long-term Memory] <--> H
        I <--> J
    end
    
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#fbb,stroke:#333,stroke-width:2px
    style G fill:#bfb,stroke:#333,stroke-width:2px
```

## Component Descriptions

### Processing Router [CON-HVA-009]

The Processing Router determines which model (local or API) should handle each aspect of the conversation:

- **Routing Criteria**:
  - Response urgency (immediate vs. thoughtful)
  - Query complexity (simple facts vs. synthesis)
  - Contextual cues (casual chat vs. detailed explanation)
  - Current system load and API quota status

- **Implementation Approach**:
  - Classifier model trained on conversation patterns
  - Heuristic rules for common scenarios
  - Dynamic adjustment based on user interaction patterns

### Local Model Processing [CON-HVA-010]

Fast, lightweight language model running on device:

- **Target Capabilities**:
  - Social acknowledgments and backchanneling
  - Simple factual responses from common knowledge
  - Conversational continuity during API processing
  - Personality consistency and emotional responses

- **Implementation Options**:
  - 7B parameter models optimized for M4 architecture
  - Quantized models (4-bit) for memory efficiency
  - Domain-specific fine-tuning for conversation

### API Model Processing [CON-HVA-011]

Cloud-based language model for complex reasoning:

- **Target Capabilities**:
  - Deep reasoning and novel insights
  - Complex information synthesis
  - Detailed explanations and step-by-step thinking
  - Access to broader knowledge and capabilities

- **Implementation Options**:
  - GPT-4 or Claude APIs with streaming responses
  - Careful prompt engineering for context efficiency
  - Asynchronous processing with callback handling

### Response Integration [CON-HVA-012]

Combines outputs from both processing streams into coherent conversation:

- **Integration Strategies**:
  - Immediate local responses while waiting for API results
  - Graceful interruption when API results arrive
  - Context-aware transitions between response types
  - Seamless handoffs between models during extended conversations

- **Implementation Approach**:
  - Priority queue for managing response timing
  - Natural language transitions between response types
  - Coherence checking to prevent contradictions

## Hardware Considerations [CON-HVA-003]

The architecture is designed to run efficiently on a MacBook Pro M4 with 24GB RAM:

| Component | Resource Requirements | Optimization Strategy |
|-----------|----------------------|------------------------|
| STT (Whisper) | ~2GB RAM, moderate CPU | Batch processing, activity detection |
| Local LLM | 8-10GB RAM, high Neural Engine | 4-bit quantization, model pruning |
| TTS | 2-3GB RAM, moderate CPU | Caching common phrases, voice profiles |
| Memory Systems | 2-4GB RAM, SSD storage | Tiered storage, compression |
| API Processing | Minimal local resources | Request batching, streaming responses |

## Latency Management [CON-HVA-004]

Techniques to minimize perceived latency:

1. **Predictive Processing**: Begin formulating responses before user completes speaking
2. **Progressive Response Generation**: Start speaking before full response is generated
3. **Background Processing**: Perform heavy computation during natural conversation pauses
4. **Response Caching**: Store common responses for immediate retrieval
5. **Attention Management**: Use verbal and prosodic cues to maintain engagement during processing

## Integration with LangGraph

The dual processing architecture can be implemented as a LangGraph workflow:

```mermaid
graph LR
    A[Input Node] --> B{Router Node}
    B -->|Fast Path| C[Local Model Node]
    B -->|Deep Path| D[API Model Node]
    C --> E[Integration Node]
    D --> E
    E --> F[Output Node]
    
    G[Memory Node] <--> B
    G <--> C
    G <--> D
    G <--> E
    
    style B fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#fbb,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
```

## Version History

- v0.1.0 - 2025-05-17 - Initial creation [SES-V0-004]