# VANTA-ALPHA Essential Context Files

This guide identifies all critical documentation files needed to maintain full context for the VANTA-ALPHA project. Reference these files in the recommended order when starting a new session.

## VISTA Framework Documentation

| Document | Purpose | When to Access |
|----------|---------|----------------|
| `/CLAUDE.md` | Core VISTA methodology and VANTA project overview | **Always read first** for every session |
| `/INSTRUCTIONS.md` | VISTA workflow and session continuity protocols | For understanding session protocols |
| `/SESSION_STATE.md` | Current project state, decisions, and action items | **Always read** to understand current progress |
| `/KNOWLEDGE_GRAPH.md` | Concepts and relationships | For understanding technical concepts |
| `/METADATA.json` | Document versions, cross-references, and session history | For tracking document relationships |

**How to dive deeper:** If you need more information about the VISTA methodology, consult the reference VISTA documentation at `/Users/vigil-313/workplace/VISTA/`, particularly `README.md` and `VISTA_TEMPLATE.md`. These files contain comprehensive information about the document structure, implementation phases, and workflow patterns.

## LangGraph Research

| Document | Purpose | When to Access |
|----------|---------|----------------|
| `/research/langgraph/integration_notes/LANGGRAPH_VANTA_INTEGRATION.md` | Integration strategy for LangGraph and VANTA | For LangGraph architecture questions |
| `/research/langgraph/examples/vanta_simplified_example.py` | Code example of VANTA implementation with LangGraph | For implementation reference |
| `/research/INTEGRATION_FINDINGS_SUMMARY.md` | Summary of framework evaluation research | For high-level integration strategy |

**How to dive deeper:** For more detailed LangGraph understanding, analyze the graph structure in the example code. The integration notes document should contain links to external LangGraph resources. Pay particular attention to the graph nodes and state management approach as these will be critical for implementation.

## MCP Research

| Document | Purpose | When to Access |
|----------|---------|----------------|
| `/Technical/MCP_REFERENCE.md` | Core MCP concepts and capabilities | For MCP fundamentals |
| `/research/mcp/integration_patterns/MCP_LANGGRAPH_INTEGRATION.md` | How to integrate MCP with LangGraph | For combined architecture questions |
| `/research/mcp/server_designs/VANTA_MCP_SERVERS.md` | Custom MCP server specifications for VANTA | For MCP server implementation details |

**How to dive deeper:** The MCP reference document should contain links to external MCP documentation. The server designs document will include details about each server type, their APIs, and data models. If you need to understand how MCP servers exchange information, focus on the integration patterns document.

## Hybrid Voice Architecture

| Document | Purpose | When to Access |
|----------|---------|----------------|
| `/research/hybrid_voice_architecture/README.md` | Overview of the hybrid voice architecture | For introduction to the architecture |
| `/research/hybrid_voice_architecture/design/HYBRID_COGNITIVE_MODEL.md` | Theoretical basis for the dual-process architecture | For understanding the cognitive model |
| `/research/hybrid_voice_architecture/design/DUAL_PROCESSING_ARCHITECTURE.md` | System design for local+API model integration | For technical architecture details |
| `/research/hybrid_voice_architecture/design/SPEECH_NATURALIZATION.md` | Techniques for natural speech patterns | For speech output system questions |
| `/research/hybrid_voice_architecture/implementation_notes/IMPLEMENTATION_CONSIDERATIONS.md` | Hardware and implementation guidance | For implementation planning |
| `/research/hybrid_voice_architecture/diagrams/HYBRID_ARCHITECTURE_DIAGRAM.md` | Visual architecture diagrams | For visual understanding of system |

**How to dive deeper:** Each document contains detailed sections that can be explored based on the specific area of interest. For voice processing, focus on the speech naturalization document. For understanding state management, examine the dual processing architecture document. The diagrams file contains visualizations that show the relationships between components.

## Implementation Planning 
(Note: This section will be expanded as implementation planning progresses)

| Document | Purpose | When to Access |
|----------|---------|----------------|
| `/Development/IMPLEMENTATION_PLAN.md` | High-level implementation plan | For understanding implementation phases |
| `/Development/TEST_STRATEGY.md` | Testing approaches and validation criteria | For testing considerations |
| `/Development/PROMPT_SEQUENCES.md` | Templates for implementation tasks | For implementation task structure |

## Session Management

For effective session management:

1. **Begin each session by reviewing:**
   - Current session state in SESSION_STATE.md, focusing on the Handoff section
   - Recent decisions and questions that need addressing
   - The progress snapshot to understand overall project status

2. **When creating new documentation:**
   - Follow VISTA document formatting with unique identifiers (DOC-XX-YY, CON-XX-YY, DEC-XX-YY)
   - Use appropriate audience-level directories (Executive/, Management/, Technical/, Development/)
   - Maintain visual progress indicators with emoji status markers (🟢 Complete, 🟡 In Progress, 🔴 Not Started, ⚪ Not Applicable)
   - Use Mermaid for diagrams where appropriate

3. **When ending a session:**
   - Update SESSION_STATE.md with new decisions, questions, and action items
   - Update KNOWLEDGE_GRAPH.md with new concepts and relationships
   - Update METADATA.json with document versions and cross-references
   - Ensure all new documents are properly referenced in their parent directories

## Continuous Updates

To ensure this context guide remains current:

1. After creating significant new documentation, add the file paths to this guide under the appropriate section
2. When discovering new resources that provide valuable context, document them here
3. At the end of each major project phase, review and update this guide with relevant new information
4. Whenever new implementation details are finalized, add them to the Implementation Planning section

## Version History

- v0.1.0 - 2025-05-17 - Initial creation based on project structure and VISTA framework