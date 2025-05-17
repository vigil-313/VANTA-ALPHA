# Hybrid Architecture Diagrams [DOC-RESEARCH-HVA-6]

This document contains visual representations of VANTA's hybrid voice architecture, illustrating the relationships between components and the flow of data through the system.

## System Overview

```mermaid
graph TD
    %% User Interaction Layer
    User((User)) <-->|Voice| A[Audio Interface]
    
    %% Input Processing
    A -->|Audio Input| B[Speech Recognition<br/>Whisper]
    B -->|Transcribed Text| C[Input Processor]
    
    %% Dual-Process Core
    C --> D{Processing<br/>Router}
    D -->|Simple/Fast Path| E[Local LLM<br/>7B Model]
    D -->|Complex/Deep Path| F[Cloud API<br/>GPT/Claude]
    
    %% Response Integration
    E --> G[Response<br/>Integrator]
    F --> G
    G -->|Response Text| H[Speech Synthesizer]
    H -->|Audio Output| A
    
    %% Shared Resources
    I[Context Manager] <--> C
    I <--> D
    I <--> E
    I <--> F
    I <--> G
    
    J[Short-Term<br/>Memory] <--> I
    K[Long-Term<br/>Memory] <--> I
    
    L[Prosody<br/>Controller] <--> G
    L <--> H
    
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#fbb,stroke:#333,stroke-width:2px
    style G fill:#bfb,stroke:#333,stroke-width:2px
```

## Dual-Process Cognitive Model

```mermaid
graph TD
    %% Input Processing
    A[User Input] --> B[Perception<br/>Layer]
    
    %% Cognitive Processing
    B --> C{Processing<br/>Router}
    
    %% System 1 - Fast Thinking
    C -->|System 1| D[Local Processing]
    D -->|Fast Response| G[Response<br/>Generation]
    
    subgraph "System 1 Components"
        D --> D1[Pattern<br/>Recognition]
        D --> D2[Emotional<br/>Processing]
        D --> D3[Social<br/>Signals]
        D --> D4[Memory<br/>Associations]
    end
    
    %% System 2 - Slow Thinking
    C -->|System 2| E[API Processing]
    E -->|Deep Response| G
    
    subgraph "System 2 Components"
        E --> E1[Reasoning<br/>Engine]
        E --> E2[Complex<br/>Synthesis]
        E --> E3[Novel<br/>Insights]
        E --> E4[Structured<br/>Planning]
    end
    
    %% Response Generation
    G --> H[Prosody<br/>Application]
    H --> I[Output<br/>Delivery]
    
    %% Memory Systems
    J[Working<br/>Memory] <--> C
    J <--> D
    J <--> E
    K[Long-term<br/>Memory] <--> J
    
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#fbb,stroke:#333,stroke-width:2px
    style G fill:#bfb,stroke:#333,stroke-width:2px
```

## Information Flow During Processing

```mermaid
sequenceDiagram
    participant User
    participant STT as Speech Recognition
    participant Router as Processing Router
    participant Local as Local LLM
    participant API as Cloud API
    participant TTS as Speech Synthesis
    
    User->>STT: Speaks
    STT->>Router: Transcribed Text
    
    alt Simple Query or Social Response
        Router->>Local: Route to local processing
        Local->>TTS: Fast response
        TTS->>User: Immediate verbal response
    else Complex Query
        Router->>Local: Generate acknowledgment
        Local->>TTS: Backchanneling response
        TTS->>User: "Let me think about that..."
        Router->>API: Route to API processing
        API-->>Router: Processing (1-3s)
        Router->>Local: Prepare for API response
        API->>Router: API response received
        Router->>TTS: Thoughtful response
        TTS->>User: Detailed verbal response
    end
```

## Hardware Resource Allocation

```mermaid
graph TD
    subgraph "M4 MacBook Pro (24GB RAM)"
        A[Neural Engine] --- B[CPU Cores]
        B --- C[Unified Memory<br/>24GB]
        C --- D[SSD Storage]
        
        %% Allocation Visualization
        subgraph "Memory Allocation"
            E[System OS<br/>~4GB]
            F[Local LLM<br/>~8-10GB]
            G[STT/TTS<br/>~4-5GB]
            H[App Framework<br/>~2GB]
            I[Available<br/>~4GB]
        end
        
        %% Processing Allocation
        subgraph "Neural Engine Priority"
            J[Local LLM<br/>Inference]
            K[Speech<br/>Processing]
            L[Memory<br/>Embeddings]
        end
        
        %% CPU Priority
        subgraph "CPU Priority"
            M[App Logic]
            N[I/O Handling]
            O[Background<br/>Processing]
        end
    end
    
    style F fill:#bbf,stroke:#333,stroke-width:2px
    style G fill:#fbb,stroke:#333,stroke-width:2px
    style J fill:#bbf,stroke:#333,stroke-width:2px
    style K fill:#fbb,stroke:#333,stroke-width:2px
```

## LangGraph Implementation

```mermaid
graph LR
    %% Graph Nodes
    A[Input Node] --> B{Router Node}
    B -->|System 1 Path| C[Local Model Node]
    B -->|System 2 Path| D[API Model Node]
    
    %% Response Handling
    C --> E[Integration Node]
    D --> E
    E --> F[Prosody Node]
    F --> G[Output Node]
    
    %% State Management
    H[Memory Node] <--> B
    H <--> C
    H <--> D
    H <--> E
    
    %% User Interaction
    I[User Input] --> A
    G --> J[User Output]
    
    %% Shared Resources
    K[Context Manager] <--> H
    K <--> B
    K <--> E
    
    style B fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#fbb,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
```

## Version History

- v0.1.0 - 2025-05-17 - Initial creation [SES-V0-004]