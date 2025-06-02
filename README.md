# VANTA

**V**oice-based **A**mbient **N**eural **T**hought **A**ssistant

## Overview

VANTA is a real-time, voice-based AI assistant designed to behave like an ambient presence in your environment. It's a persistent, conversational agent that can listen, respond verbally, maintain memory, and make intelligent decisions about when to speak.

The project explores dual-track AI processing, where simple queries are handled by local language models for speed, while complex queries are routed to cloud APIs for higher quality responses.

## Features

- **Dual-Track Processing**: Routes between local LLM (fast) and cloud API (quality) based on query complexity
- **Memory System**: Stores conversations with semantic understanding and retrieval
- **Voice Pipeline**: Text-to-speech and speech-to-text capabilities
- **Intelligent Routing**: Automatic decision-making about which AI model to use
- **LangGraph Workflow**: Manages conversation flow and state
- **Cross-Session Memory**: Remembers conversations across different sessions

## Current Implementation

VANTA consists of several components in various stages of development:

### Working Components:
- **Text-based conversation** with local models (Llama-3.1-8B/70B)
- **API integration** with Anthropic Claude for complex queries
- **Conversation memory storage** using JSON files and ChromaDB
- **Dual-track routing** that chooses appropriate AI model
- **Basic voice synthesis** (with some parameter issues to fix)

### In Development:
- **Memory integration** with LangGraph workflow (partial conflicts)
- **Always-listening** voice activation
- **Personality system** and adaptive behavior
- **Goal tracking** and reflective advice

## Architecture

VANTA uses a modular architecture with clear separation of concerns:

1. **Voice Pipeline**: Audio input/output processing
2. **Memory Engine**: Conversation storage and semantic retrieval  
3. **Dual-Track Reasoning**: Local LLM + Cloud API with intelligent routing
4. **LangGraph Workflow**: State management and conversation flow
5. **Storage System**: ChromaDB for vectors, JSON for conversations

```
User Input → Router → ┌─ Local Model (Llama, fast)
                      └─ API Model (Claude, quality)
                            ↓
Memory System ← Response Integration ← Processing
```

## Quick Start

### Prerequisites
```bash
pip install langchain-core langgraph anthropic chromadb sentence-transformers llama-cpp-python
```

### Optional: Set up API access
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### Run VANTA
```bash
cd Development/Implementation/vanta-main/v02
python main_vanta_memory.py
```

## Project Structure

```
VANTA-ALPHA/
├── Development/Implementation/
│   ├── vanta-main/v01/          # Basic dual-track version
│   ├── vanta-main/v02/          # Version with memory integration
│   ├── src/
│   │   ├── vanta_workflow/      # LangGraph workflow nodes
│   │   ├── models/dual_track/   # AI model routing and management
│   │   ├── memory/              # Memory and conversation storage
│   │   └── voice/               # Speech processing pipeline
│   └── models/                  # Downloaded language models (8GB-70GB)
```

## Examples

Simple queries use the local model:
```
User: "Hi"
VANTA: "Hello! How can I help you today?"
[LOCAL model, 1.95s]
```

Complex queries route to the API:
```
User: "Write a creative story about AI learning to paint"
VANTA: [Detailed creative story from Claude API]
[API model, 5.21s]
```

Memory works across sessions:
```
User: "My name is Sarah"
VANTA: "Nice to meet you, Sarah!"
[Later session]
User: "What's my name?"
VANTA: "Your name is Sarah."
[Retrieved from memory]
```

## Current Status

This is an experimental side project for learning about AI assistant architectures. Some parts work well, others need refinement:

**Performance:**
- Local queries: 1-3 seconds
- API queries: 5-20 seconds  
- Memory retrieval: <0.1 seconds
- Routing accuracy: Generally good

**Known Issues:**
- TTS synthesis parameter conflicts
- Memory system integration conflicts with LangGraph
- Voice activation not yet implemented
- Some conversation context loss between dual tracks

See [MEMORY_INTEGRATION_FIX_PLAN.md](Development/Implementation/vanta-main/v02/MEMORY_INTEGRATION_FIX_PLAN.md) for technical details on current development challenges.

## Technical Notes

- Local models run via llama-cpp-python (supports 8B to 70B models)
- Vector storage uses ChromaDB with sentence-transformers embeddings
- Memory system stores conversations as timestamped JSON files
- LangGraph manages conversation state and routing decisions
- Dual-track processing prevents API costs for simple queries

This project explores practical challenges in building conversational AI systems, including model selection, memory management, and maintaining context across different AI providers.

## Appendix: Rudimentary Architecture for V0

The following diagrams illustrate the current system architecture:

### System Overview

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
        D <--> G["Local Model (8B/70B)"]
        D <--> H["API Model (Claude)"]
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

### LangGraph Workflow Architecture

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

### Dual-Track Processing Architecture

```mermaid
graph LR
    A["User Query"] --> B["Input Analysis"]
    B --> C{"Processing Router"}
    
    C -->|"Fast Path:<br/>Simple queries<br/>Time-sensitive<br/>Backchanneling"| D["Local Model (Llama)"]
    C -->|"Deep Path:<br/>Complex queries<br/>Reasoning<br/>Synthesis"| E["API Model (Claude)"]
    
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

### Memory System Architecture

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
