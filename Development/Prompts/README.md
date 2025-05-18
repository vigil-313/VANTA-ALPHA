# Implementation Prompts

## Purpose
This directory contains individual prompt files for Claude Code implementation tasks. Each prompt follows the standard structure defined in PROMPT_SEQUENCES.md but is extracted into a separate file for clarity and easier session management.

## Directory Structure

```
/Prompts/
├── Phase0_Setup/              # Environment and setup tasks
├── Phase1_Core/               # Core component implementation
│   ├── VoicePipeline/         # Audio processing, STT, TTS
│   ├── LocalModel/            # Local LLM integration
│   ├── APIModel/              # API model integration
│   └── Memory/                # Memory and storage systems
├── Phase2_Workflow/           # Workflow and orchestration
│   ├── LangGraph/             # LangGraph implementation
│   ├── DualTrack/             # Dual-track processing
│   └── StateManagement/       # Configuration and state
├── Phase3_Integration/        # System integration
│   ├── Integration/           # Component integration
│   ├── Testing/               # Testing implementation
│   └── Optimization/          # Performance optimization
└── Phase4_Release/            # Release preparation
```

## File Naming Convention
- `{COMPONENT_ID}_{TASK_NAME}.md` - Individual task prompt files
- Example: `ENV_002_Docker_Environment.md`
- Each file corresponds to a specific implementation task from the Implementation Plan

## Content Requirements
Each prompt file should include:
- Clear context and objectives
- Specific requirements and steps
- References to technical documentation
- Validation criteria
- Expected output

## Example Structure
```
# IMPLEMENTATION TASK: ENV_002 Docker Environment Setup

## Context
[Background information...]

## Objective
[What this task aims to accomplish...]

## Requirements
[List of specific requirements...]

## Steps
1. [First step...]
2. [Second step...]
...

## References
- [DOC-TECH-API-1]: API Specification
...

## Validation
- [How to validate the implementation...]
```

## Development Workflow

1. Select a task from the implementation plan
2. Find or create the corresponding prompt file
3. Use `generate_dev_session.sh` to start an implementation session
4. Complete the implementation in Claude Code
5. Save implementation to the appropriate location in `/Development/Implementation/`
6. Run tests and validation as specified in the prompt
7. Update documentation using `update_documentation.sh`

## Post-Implementation Updates

After each implementation:
1. Update SESSION_STATE.md with implementation status
2. Update KNOWLEDGE_GRAPH.md with new concepts or relationships
3. Add implementation notes to the task prompt file
4. Mark task as completed in the implementation plan

## Current Focus
The current implementation focus is on Phase 0 (Setup) tasks:
- ENV_002: Docker development environment
- ENV_003: Model preparation 
- ENV_004: Testing framework setup

## Last Updated
2025-05-18 09:45:00 PDT | SES-V0-006 | Reorganized directory structure for better organization