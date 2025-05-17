# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

V0_VANTA is a new version of the VANTA (Voice-based Ambient Neural Thought Assistant) project, focused on creating a real-time, voice-based AI assistant that behaves like an ambient presence. The original VANTA implementation encountered significant challenges, and this repository represents a redesign effort using the VISTA methodology for improved architecture and implementation.

### Core Components

1. **Voice Pipeline**: Audio input/output processing with continuous listening and voice responses
2. **Memory Engine**: Sophisticated conversation storage with semantic retrieval  
3. **Reasoning Engine**: LLM-based intelligence for contextual understanding and response
4. **Personality System**: Adaptive traits, mood, and behavior
5. **Scheduler**: Goal tracking and time-based actions

## VISTA Protocol

This project follows the VISTA (Versatile Intelligent System for Technical Acceleration) methodology, which requires:

1. **Documentation Hierarchy**: Creating structured documentation for different audiences (Executive, Management, Technical, Development)
2. **Knowledge Persistence**: Maintaining SESSION_STATE.md and KNOWLEDGE_GRAPH.md across planning sessions
3. **Implementation Planning**: Breaking down development into discrete, manageable tasks
4. **Documentation-Code Synchronization**: Updating documentation to reflect implementation changes

### VISTA Session Protocol

When developing this project:

1. Begin each session with: `# DOCPROTOCOL: Claude will (1)Load system context from SESSION_STATE.md (2)Process new information (3)Update all affected documents (4)Maintain cross-references via unique IDs (5)Version all changes (6)Generate comprehensive session summary (7)Update knowledge graph (8)Prepare handoff state for next session`

2. Use consistent document formatting with unique identifiers (DOC-XX-YY, CON-XX-YY, DEC-XX-YY)

3. Maintain visual progress indicators with emoji status markers (🟢 Complete, 🟡 In Progress, 🔴 Not Started, ⚪ Not Applicable)

4. Keep cross-references updated between documents 

5. Update SESSION_STATE.md and KNOWLEDGE_GRAPH.md at the end of every session

## Implementation Guidelines

- **Modular Architecture**: Maintain clear separation of concerns between components
- **Event-Driven Communication**: Use an event bus pattern for loose coupling
- **Async-First**: Design for real-time responsiveness
- **Error Resilience**: Implement proper error handling, especially for audio processing
- **Resource Management**: Monitor and constrain resource usage for stable operation

## Important Notes
- When making commits, please DO NOT include references to Claude, Claude Code, or Anthropic in the commit messages.
- THROUGHOUT ALL STEPS, SESSION_STATE.md AND KNOWLEDGE_GRAPH.md MUST BE UPDATED USING VISTA PROTOCOL!