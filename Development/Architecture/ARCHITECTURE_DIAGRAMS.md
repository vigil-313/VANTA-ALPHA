# Architecture Diagrams [DOC-DEV-ARCH-4]

## Overview

This document contains visual representations of the VANTA system architecture. These diagrams illustrate different aspects of the system from various perspectives to aid in understanding the overall design.

## System Overview

The following diagram shows the high-level components of the VANTA system and their relationships:

```mermaid
graph TD
    User(("User")) <--> A["Voice Interface"]
    
    subgraph "Core System"
        A <--> B["Voice Pipeline"]
        B <--> C["LangGraph Workflow Engine"]
        C <--> D["Dual-Track Processing"]
        C <--> E["Memory System"]
        D --> F["Response Generation"]
        F --> A
    end
    
    subgraph "Model Integration"
        D <--> G["Local Model (7B)"]
        D <--> H["API Model (Claude/GPT-4)"]
    end
    
    subgraph "Persistent Storage"
        E <--> I["Vector Database"]
        E <--> J["Conversation Logs"]
        E <--> K["Configuration Store"]
    end
    
    style A fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#fbb,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
```

## Voice Pipeline Architecture

The voice processing pipeline includes components for audio input/output and speech processing:

```mermaid
graph TD
    A["Audio Input Device"] --> B["Audio Preprocessing"]
    B --> C["Voice Activity Detection"]
    C --> D["Speech-to-Text (Whisper)"]
    D --> E["Text Normalization"]
    E --> F["LangGraph Workflow"]
    
    F --> G["Text Formatting"]
    G --> H["Prosody Control"]
    H --> I["Text-to-Speech (CSM)"]
    I --> J["Audio Postprocessing"]
    J --> K["Audio Output Device"]
    
    subgraph "Voice Pipeline Configuration"
        L["Microphone Settings"]
        M["Voice Profiles"]
        N["Speech Recognition Models"]
        O["TTS Voice Options"]
        P["Audio Processing Parameters"]
    end
    
    L -.-> B
    M -.-> I
    N -.-> D
    O -.-> I
    P -.-> B
    P -.-> J
    
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style I fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#f9f,stroke:#333,stroke-width:2px
```

## LangGraph Workflow Architecture

The core processing workflow implemented using LangGraph:

```mermaid
graph TD
    Start(("Start")) --> A["Check Activation Node"]
    
    A --> B{"Activation Check"}
    B -->|"Inactive"| Stop(("End"))
    B -->|"Active"| C["Process Audio Node"]
    
    C --> D["Memory Retrieval Node"]
    D --> E["Router Node"]
    
    E -->|"Local Path"| F["Local Model Node"]
    E -->|"API Path"| G["API Model Node"]
    
    F --> H["Response Integration Node"]
    G --> H
    
    H --> I["Response Generation Node"]
    I --> J["Speech Synthesis Node"]
    J --> K["Memory Update Node"]
    K --> Stop
    
    style A fill:#ddf,stroke:#333,stroke-width:1px
    style C fill:#ddf,stroke:#333,stroke-width:1px
    style D fill:#ddf,stroke:#333,stroke-width:1px
    style E fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
    style G fill:#fbb,stroke:#333,stroke-width:2px
    style H fill:#bfb,stroke:#333,stroke-width:2px
    style I fill:#ddf,stroke:#333,stroke-width:1px
    style J fill:#ddf,stroke:#333,stroke-width:1px
    style K fill:#ddf,stroke:#333,stroke-width:1px
```

## Dual-Track Processing Architecture

The dual-track processing system that combines local and API models:

```mermaid
graph LR
    A["User Query"] --> B["Input Analysis"]
    B --> C{"Processing Router"}
    
    C -->|"Fast Path:<br/>Simple queries<br/>Time-sensitive<br/>Backchanneling"| D["Local Model (7B)"]
    C -->|"Deep Path:<br/>Complex queries<br/>Reasoning<br/>Synthesis"| E["API Model (Claude/GPT-4)"]
    
    D -->|"Fast Response"| F["Response Integration"]
    E -->|"Deep Response"| F
    
    F --> G["Unified Response"]
    
    H["Routing Criteria"] -.-> C
    I["Context Memory"] -.-> D
    I -.-> E
    
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#fbb,stroke:#333,stroke-width:2px
    style F fill:#bfb,stroke:#333,stroke-width:2px
```

## Memory System Architecture

The layered memory architecture for short and long-term storage:

```mermaid
graph TD
    subgraph "Working Memory (Session State)"
        A["Active Messages"]
        B["Current Context"]
        C["Session Metadata"]
    end
    
    subgraph "Long-Term Memory"
        D["Vector-Based Semantic Memory"]
        E["Conversation History"]
        F["User Preferences"]
        G["Raw Log Storage"]
    end
    
    A <--> D
    A <--> E
    B <--> D
    B <--> F
    
    H["Memory Manager"] --> A
    H --> B
    H --> C
    H --> D
    H --> E
    H --> F
    H --> G
    
    I["Memory Query Interface"] <--> H
    J["Memory Update Interface"] <--> H
    
    K["LangGraph State"] <--> I
    K <--> J
    
    style K fill:#f9f,stroke:#333,stroke-width:2px
    style H fill:#bfb,stroke:#333,stroke-width:2px
```

## State Flow Diagram

The flow of state through the LangGraph components:

```mermaid
stateDiagram-v2
    [*] --> Listening
    
    Listening --> Processing: Audio detected
    Processing --> Responding: Transcript generated
    Responding --> Speaking: Response generated
    Speaking --> Listening: Speech completed
    
    Listening --> [*]: Session end
    
    state Processing {
        [*] --> InputAnalysis
        InputAnalysis --> ModelRouting
        ModelRouting --> LocalProcessing: Simple query
        ModelRouting --> APIProcessing: Complex query
        LocalProcessing --> ResponseIntegration
        APIProcessing --> ResponseIntegration
        ResponseIntegration --> [*]
    }
    
    state Responding {
        [*] --> ContextRetrieval
        ContextRetrieval --> ResponseGeneration
        ResponseGeneration --> OutputFormatting
        OutputFormatting --> [*]
    }
    
    state Speaking {
        [*] --> TTS
        TTS --> AudioOutput
        AudioOutput --> MemoryUpdate
        MemoryUpdate --> [*]
    }
```

## Component Dependency Diagram

The dependencies between major system components:

```mermaid
graph TD
    A["Voice Pipeline"] --> B["LangGraph Workflow"]
    C["Memory System"] --> B
    D["Local Model"] --> B
    E["API Client"] --> B
    
    B --> F["Event Bus"]
    F --> A
    F --> C
    
    G["Vector Database"] --> C
    H["Raw Storage"] --> C
    
    I["Model Loading System"] --> D
    J["API Authentication"] --> E
    
    K["Configuration System"] --> A
    K --> B
    K --> C
    K --> D
    K --> E
    
    style B fill:#f9f,stroke:#333,stroke-width:2px
```

## Deployment Diagram

The deployment architecture for the VANTA system:

```mermaid
graph TD
    subgraph "Local Machine (MacBook Pro M4)"
        A["VANTA Application"]
        
        subgraph "Core Components"
            B["Voice Pipeline"]
            C["LangGraph Engine"]
            D["Local Model (llama.cpp)"]
            E["Memory System"]
        end
        
        subgraph "Local Storage"
            F["Vector DB (Chroma)"]
            G["Log Files"]
            H["Audio Cache"]
        end
        
        A --> B
        A --> C
        A --> D
        A --> E
        
        E --> F
        E --> G
        B --> H
    end
    
    subgraph "Cloud Services"
        I["Claude API"]
        J["GPT-4 API"]
        K["Optional: Cloud Backup"]
    end
    
    A --> I
    A --> J
    E -.-> K
    
    L["Audio Input Devices"] --> B
    B --> M["Audio Output Devices"]
    
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
```

## Data Flow Diagram

The flow of data through the system:

```mermaid
graph TD
    A["Audio Input"] -->|"Raw Audio"| B["Voice Activity Detection"]
    B -->|"Audio Segment"| C["Speech-to-Text"]
    C -->|"Transcript"| D["Input Processing"]
    
    D -->|"Processed Input"| E["Context Building"]
    F["Memory System"] -->|"Retrieved Context"| E
    
    E -->|"Enhanced Input + Context"| G["Model Router"]
    
    G -->|"Simple Query"| H["Local Model"]
    G -->|"Complex Query"| I["API Model"]
    
    H -->|"Fast Response"| J["Response Integration"]
    I -->|"Deep Response"| J
    
    J -->|"Integrated Response"| K["Response Formatting"]
    K -->|"Formatted Text"| L["Text-to-Speech"]
    L -->|"Audio Response"| M["Audio Output"]
    
    D -->|"Store Input"| F
    J -->|"Store Response"| F
    
    style G fill:#f9f,stroke:#333,stroke-width:2px
    style H fill:#bbf,stroke:#333,stroke-width:2px
    style I fill:#fbb,stroke:#333,stroke-width:2px
    style J fill:#bfb,stroke:#333,stroke-width:2px
```

## Class Diagram (Core Components)

The relationships between core classes in the system:

```mermaid
classDiagram
    class VANTAState {
        +messages: List[BaseMessage]
        +audio: Dict
        +memory: Dict
        +config: Dict
        +activation: Dict
    }
    
    class StateGraph {
        +nodes: Dict
        +edges: Dict
        +entry_point: str
        +add_node(name, function)
        +add_edge(start, end)
        +add_conditional_edges(start, condition, targets)
        +compile(checkpointer)
    }
    
    class VoicePipeline {
        +preprocess_audio(audio_data)
        +detect_voice_activity(audio_data)
        +transcribe(audio_data)
        +synthesize(text)
        +postprocess_audio(audio_data)
    }
    
    class ModelRouter {
        +route(input, context)
        +get_routing_criteria()
        +update_routing_model(data)
    }
    
    class LocalModel {
        +generate(prompt, params)
        +get_embeddings(text)
        +tokenize(text)
        +load_model(path)
    }
    
    class APIClient {
        +generate(messages, params)
        +stream_generate(messages, params)
        +get_embeddings(text)
        +handle_error(error)
    }
    
    class MemorySystem {
        +store(data)
        +retrieve(query, filters)
        +update(id, data)
        +summarize(entries)
    }
    
    StateGraph --> VANTAState: operates on
    VoicePipeline --> StateGraph: provides nodes
    ModelRouter --> StateGraph: provides nodes
    LocalModel --> ModelRouter: used by
    APIClient --> ModelRouter: used by
    MemorySystem --> StateGraph: provides nodes
```

## Sequence Diagram (Processing Flow)

The sequence of operations for processing a user query:

```mermaid
sequenceDiagram
    participant User
    participant VP as Voice Pipeline
    participant Router as Model Router
    participant Local as Local Model
    participant API as API Model
    participant Memory as Memory System
    participant TTS as Text-to-Speech
    
    User->>VP: Speak query
    VP->>VP: Detect voice activity
    VP->>VP: Transcribe audio
    VP->>Router: Send transcript
    Router->>Memory: Retrieve context
    
    alt Simple query
        Router->>Local: Process with local model
        Local->>Router: Return fast response
    else Complex query
        Router->>API: Process with API model
        API->>Router: Stream response
        
        par Backchanneling
            Router->>Local: Generate acknowledgment
            Local->>TTS: Synthesize acknowledgment
            TTS->>User: Play acknowledgment
        end
        
        Router->>Memory: Update with final response
    end
    
    Router->>TTS: Send response for synthesis
    TTS->>User: Play synthesized response
    Router->>Memory: Store conversation turn
```

## State Transition Diagram

The transitions between system states:

```mermaid
stateDiagram-v2
    [*] --> Idle
    
    Idle --> Listening: Activate
    Listening --> Processing: Voice Detected
    Processing --> Thinking: Transcription Complete
    
    state Thinking {
        [*] --> Routing
        Routing --> LocalThinking: Use Local Model
        Routing --> APIThinking: Use API Model
        LocalThinking --> [*]: Response Ready
        APIThinking --> [*]: Response Ready
    }
    
    Thinking --> Responding: Response Integrated
    Responding --> Speaking: Response Formatted
    Speaking --> Idle: Speech Complete
    
    Idle --> [*]: Shutdown
```

## Resource Utilization Diagram

The allocation of system resources:

```mermaid
pie title "Memory Allocation (24GB Total)"
    "Local Model" : 10
    "Voice Pipeline" : 4
    "LangGraph State" : 2
    "Vector Database" : 3
    "System & OS" : 3
    "Available Headroom" : 2
```

```mermaid
pie title "CPU Utilization by Component"
    "Voice Processing" : 30
    "Local Model Inference" : 40
    "Memory Operations" : 10
    "State Management" : 10
    "Other Processing" : 10
```

## Error Handling Flow

The flow of error handling in the system:

```mermaid
graph TD
    A["Error Detected"] --> B{"Error Type"}
    
    B -->|"Voice Pipeline Error"| C["Fallback to Text Input"]
    B -->|"Local Model Error"| D["Route to API Model"]
    B -->|"API Model Error"| E["Use Cached Responses"]
    B -->|"Memory Error"| F["Use Working Memory Only"]
    B -->|"System Error"| G["Graceful Degradation"]
    
    C --> H["Log Error"]
    D --> H
    E --> H
    F --> H
    G --> H
    
    H --> I["Notify User If Necessary"]
    I --> J["Attempt Recovery"]
    J --> K["Resume Operation"]
```

## Version Evolution Diagram

The planned evolution of the system through versions:

```mermaid
graph LR
    A["V0: Foundation"] --> B["V0.5: Dual-track Integration"]
    B --> C["V1: Natural Conversation"]
    C --> D["V1.5: Advanced Memory"]
    D --> E["V2: Cognitive Capabilities"]
    E --> F["V2.5: Tooling Integration"]
    F --> G["V3: Ambient Presence"]
    
    style A fill:#bbf,stroke:#333,stroke-width:2px
```

## Version History

- v0.1.0 - 2025-05-17 - Initial creation [SES-V0-005]