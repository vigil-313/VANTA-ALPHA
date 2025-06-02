#!/usr/bin/env python3
"""
VANTA Main Entry Point - Version 02 (Memory Integration)
======================================================

This version builds on v01 and adds full memory integration with persistent
conversations, semantic search, and context-aware responses.

Version 02 Features:
- All v01 features (dual-track processing, LangGraph workflow)
- Full memory system integration (working + long-term + vector storage)
- Persistent conversations across sessions
- Semantic memory search and retrieval
- Memory-enhanced AI responses

Usage:
    python main_vanta_memory.py
    
Architecture:
    - Uses the full LangGraph workflow from v01
    - Adds complete memory system integration
    - Real dual-track processing with memory context
    - Persistent conversation storage and retrieval
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any

# Add both implementation and src directories to Python path
IMPLEMENTATION_DIR = Path(__file__).parent.parent.parent
SRC_DIR = IMPLEMENTATION_DIR / "src"
sys.path.insert(0, str(IMPLEMENTATION_DIR))  # For src.* imports
sys.path.insert(0, str(SRC_DIR))  # For direct imports

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_vanta_header():
    """Print VANTA startup header."""
    print("=" * 70)
    print("🤖 VANTA - Voice Assistant Neural Thinking Architecture")
    print("📍 Version: 02 (Memory Integration)")
    print("🎯 Goal: Complete dual-track AI assistant with persistent memory")
    print("🧠 New: Full memory system (conversations + semantic search)")
    print("=" * 70)
    print()

def check_environment():
    """Check if all required components are available."""
    print("🔍 Checking VANTA environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print("✅ Python version:", sys.version.split()[0])
    
    # Check src directory
    if not SRC_DIR.exists():
        print(f"❌ Source directory not found: {SRC_DIR}")
        return False
    print(f"✅ Source directory: {SRC_DIR}")
    
    # Check for key modules
    try:
        import langchain_core
        print("✅ LangChain Core available")
    except ImportError:
        print("❌ LangChain Core not available")
        return False
    
    try:
        import langgraph
        print("✅ LangGraph available")
    except ImportError:
        print("❌ LangGraph not available - this is critical for VANTA")
        return False
    
    try:
        import chromadb
        print("✅ ChromaDB available (for vector memory)")
    except ImportError:
        print("⚠️  ChromaDB not available - memory will be limited")
    
    print("✅ Environment check passed!")
    print()
    return True

def initialize_memory_system():
    """Initialize the complete VANTA memory system."""
    try:
        from src.memory.core import MemorySystem
        
        print("🧠 Initializing VANTA memory system...")
        
        # Configure memory system
        memory_config = {
            "data_path": "./data/memory",
            "max_relevant_memories": 5,
            "max_relevant_conversations": 3,
            "working_memory": {
                "max_tokens": 8000,
                "default_user": "user",
                "prune_strategy": "importance"
            },
            "long_term_memory": {
                "storage_path": "./data/memory/conversations",
                "max_age_days": 30,
                "backup_enabled": True,
                "backup_interval_days": 7
            },
            "vector_store": {
                "db_path": "./data/memory/vectors",
                "collection_name": "vanta_memories",
                "embedding_model": "all-MiniLM-L6-v2",
                "distance_metric": "cosine"
            }
        }
        
        # Initialize memory system
        memory_system = MemorySystem(memory_config)
        memory_system.initialize()
        
        print("✅ Memory system initialized successfully")
        print(f"   📁 Data path: {memory_config['data_path']}")
        print(f"   🔍 Vector store: {memory_config['vector_store']['collection_name']}")
        print(f"   💾 Long-term storage: enabled")
        
        return memory_system
        
    except Exception as e:
        print(f"❌ Memory system initialization failed: {e}")
        print("🔄 Continuing without memory (will work like v01)...")
        return None

def initialize_vanta_components():
    """Initialize VANTA components and check their status."""
    print("🚀 Initializing VANTA components...")
    
    components_status = {}
    
    # 1. Try to import LangGraph workflow
    try:
        from src.vanta_workflow.graph import compile_vanta_graph, process_with_vanta_graph
        components_status["langgraph_workflow"] = "✅ Available"
        print("✅ LangGraph workflow system")
    except ImportError as e:
        components_status["langgraph_workflow"] = f"❌ Import error: {e}"
        print(f"❌ LangGraph workflow: {e}")
    
    # 2. Initialize memory system (v02 addition)
    memory_system = initialize_memory_system()
    if memory_system:
        components_status["memory_system"] = "✅ Available"
        print("✅ Memory system")
    else:
        components_status["memory_system"] = "❌ Not available"
        print("❌ Memory system")
    
    # 3. Try to import dual-track processing
    try:
        from src.models.dual_track.graph_nodes import DualTrackGraphNodes
        components_status["dual_track"] = "✅ Available"
        print("✅ Dual-track processing")
    except ImportError as e:
        components_status["dual_track"] = f"❌ Import error: {e}"
        print(f"❌ Dual-track processing: {e}")
    
    # 4. Try to import voice pipeline
    try:
        from src.voice.pipeline import VoicePipeline
        components_status["voice_pipeline"] = "✅ Available"
        print("✅ Voice pipeline")
    except ImportError as e:
        components_status["voice_pipeline"] = f"❌ Import error: {e}"
        print(f"❌ Voice pipeline: {e}")
    
    # 5. Check local models
    models_dir = IMPLEMENTATION_DIR / "models"
    if models_dir.exists() and any(models_dir.glob("*.gguf")):
        components_status["local_models"] = "✅ Available"
        print("✅ Local models")
    else:
        components_status["local_models"] = "❌ No .gguf models found"
        print("❌ Local models not found")
    
    print()
    return components_status, memory_system

def enhance_state_with_memory(state, memory_system, user_input: str):
    """Enhance VANTA state with memory context (v02 addition)."""
    if not memory_system:
        return state
    
    try:
        # Get memory context for user input
        memory_context = memory_system.get_context(query=user_input)
        
        # Enhance state memory with real context
        enhanced_memory = {
            'conversation_history': state.get('memory', {}).get('conversation_history', []),
            'retrieved_context': {
                'results': memory_context.get('relevant_memories', []),
                'conversations': memory_context.get('relevant_conversations', []),
                'query': user_input,
                'count': len(memory_context.get('relevant_memories', []))
            },
            'user_preferences': memory_context.get('user_preferences', {}),
            'recent_topics': memory_context.get('recent_topics', []),
            'memory_summary': memory_context.get('conversation_summary', ''),
            'memory_enhanced': True
        }
        
        # Update state
        state['memory'] = enhanced_memory
        
        # Log memory usage
        memory_count = len(memory_context.get('relevant_memories', []))
        if memory_count > 0:
            print(f"🧠 Enhanced with {memory_count} relevant memories")
        
        return state
        
    except Exception as e:
        logger.error(f"Error enhancing state with memory: {e}")
        return state

def store_conversation(memory_system, result):
    """Store conversation result in memory system (v02 addition)."""
    if not memory_system:
        return
    
    try:
        messages = result.get('messages', [])
        if len(messages) >= 2:
            # Extract user and assistant messages
            user_msg = None
            assistant_msg = None
            
            for message in messages[-2:]:  # Get last 2 messages
                if hasattr(message, 'content'):
                    if hasattr(message, '__class__') and 'Human' in message.__class__.__name__:
                        user_msg = message.content
                    elif hasattr(message, '__class__') and 'AI' in message.__class__.__name__:
                        assistant_msg = message.content
            
            if user_msg and assistant_msg:
                interaction = {
                    "user_message": user_msg,
                    "assistant_message": assistant_msg,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "metadata": {
                        "session": "vanta_v02",
                        "processing": result.get('processing', {}),
                        "version": "v02_memory"
                    }
                }
                
                memory_system.store_interaction(interaction)
                print("💾 Conversation stored in memory")
                
    except Exception as e:
        logger.error(f"Error storing conversation: {e}")

def run_full_vanta_workflow():
    """Attempt to run the full VANTA LangGraph workflow with memory."""
    print("🎯 Attempting to run full VANTA v02 workflow...")
    
    try:
        # Import the real LangGraph workflow
        from src.vanta_workflow.graph import compile_vanta_graph, process_with_vanta_graph
        from src.vanta_workflow.state.vanta_state import VANTAState, ActivationStatus
        from langchain_core.messages import HumanMessage
        
        print("✅ LangGraph workflow components imported successfully")
        
        # Initialize components including memory
        components_status, memory_system = initialize_vanta_components()
        
        # Compile the real VANTA graph
        print("🔧 Compiling VANTA LangGraph workflow...")
        graph = compile_vanta_graph()
        print("✅ VANTA LangGraph workflow compiled successfully")
        
        print("\n" + "="*50)
        print("🤖 VANTA v02 - Memory-Enhanced Workflow")
        print("="*50)
        print("This is VANTA with FULL MEMORY INTEGRATION!")
        print("Features: Persistent conversations, semantic search, memory-enhanced responses")
        if memory_system:
            print("🧠 Memory: FULLY ACTIVE - conversations will be remembered!")
        else:
            print("🧠 Memory: Basic mode (like v01)")
        print()
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Create state for real LangGraph workflow
                state = VANTAState(
                    messages=[HumanMessage(content=user_input)],
                    activation={'status': ActivationStatus.PROCESSING, 'trigger': 'user_input', 'timestamp': time.time()},
                    memory={'conversation_history': [], 'retrieved_context': {}, 'user_preferences': {}, 'recent_topics': []},
                    config={'activation_mode': 'continuous', 'voice_settings': {}},
                    audio={'current_audio': user_input}
                )
                
                # Enhance state with memory (v02 addition)
                if memory_system:
                    state = enhance_state_with_memory(state, memory_system, user_input)
                
                print("🎯 Processing through VANTA v02 memory-enhanced workflow...")
                
                # Process with the REAL VANTA workflow
                result = process_with_vanta_graph(graph, state, thread_id="vanta_session_v02")
                
                # Show response with cleaner formatting
                messages = result.get('messages', [])
                if messages and len(messages) > 1:
                    response = messages[-1].content
                    print(f"\n🤖 VANTA: {response}")
                    
                    # Store conversation in memory (v02 addition)
                    if memory_system:
                        store_conversation(memory_system, result)
                    
                    # Show simplified processing stats
                    processing = result.get('processing', {})
                    if processing:
                        path = processing.get('path', 'unknown')
                        conf = processing.get('confidence', 0)
                        local_time = processing.get('local_processing_time', 0)
                        total_time = processing.get('total_processing_time', 0)
                        print(f"📊 [{path.upper()}] confidence:{conf:.2f} | processing:{local_time:.2f}s | total:{total_time:.2f}s")
                        
                        # Show memory usage
                        memory_info = result.get('memory', {})
                        if memory_info.get('memory_enhanced'):
                            count = memory_info.get('retrieved_context', {}).get('count', 0)
                            if count > 0:
                                print(f"🧠 Memory-enhanced response (used {count} past memories)")
                else:
                    print("❌ No response generated")
                
                print("" + "-" * 60)  # Separator for readability
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error in workflow: {e}")
                print("Continuing...")
        
        # Cleanup memory system
        if memory_system:
            memory_system.shutdown()
            print("💾 Memory system saved and closed")
        
        return True
        
    except ImportError as e:
        print(f"❌ LangGraph workflow import failed: {e}")
        print("🔧 Still need to fix LangGraph node imports")
        return False
    except Exception as e:
        print(f"❌ Full workflow failed: {e}")
        return False

def run_fallback_demo():
    """Run the working demo as fallback (same as v01)."""
    print("🔄 Running fallback demo workflow (like v01)...")
    
    try:
        # Use the same import pattern as the working demo
        from src.models.dual_track.graph_nodes import DualTrackGraphNodes
        from src.vanta_workflow.state.vanta_state import VANTAState, ActivationStatus
        from langchain_core.messages import HumanMessage
        
        print("✅ Demo components loaded successfully")
        
        # Initialize dual-track system
        nodes = DualTrackGraphNodes()
        
        print("\n" + "="*50)
        print("🤖 VANTA v02 Demo (Fallback Mode)")
        print("="*50)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Create state
                state = VANTAState(
                    messages=[HumanMessage(content=user_input)],
                    activation={'status': ActivationStatus.PROCESSING, 'trigger': 'user_input', 'timestamp': time.time()},
                    memory={'conversation_history': [], 'retrieved_context': {}, 'user_preferences': {}, 'recent_topics': []}
                )
                
                # Process through workflow
                print("🎯 Processing...")
                
                # Router
                router_update = nodes.enhanced_router_node(state)
                if router_update:
                    current_processing = state.get('processing', {})
                    current_processing.update(router_update['processing'])
                    state['processing'] = current_processing
                
                # Local processing
                local_update = nodes.enhanced_local_processing_node(state)
                if local_update and 'processing' in local_update:
                    current_processing = state.get('processing', {})
                    current_processing.update(local_update['processing'])
                    state['processing'] = current_processing
                
                # Integration
                integration_update = nodes.enhanced_integration_node(state)
                if integration_update:
                    state.update(integration_update)
                
                # Show response
                messages = state.get('messages', [])
                if messages and len(messages) > 1:
                    response = messages[-1].content
                    print(f"🤖 VANTA: {response}")
                else:
                    print("❌ No response generated")
                
                # Show stats
                processing = state.get('processing', {})
                if processing:
                    local_time = processing.get('local_processing_time', 0)
                    path = processing.get('path', 'unknown')
                    print(f"📊 Stats: {path.upper()} path, {local_time:.2f}s")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except ImportError as e:
        print(f"❌ Even demo failed to load: {e}")
        return False
    
    return True

def main():
    """Main VANTA entry point."""
    print_vanta_header()
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed. Cannot start VANTA.")
        return 1
    
    # Initialize components
    components_status, memory_system = initialize_vanta_components()
    
    # Determine what we can run
    working_components = sum(1 for status in components_status.values() if status.startswith("✅"))
    total_components = len(components_status)
    
    print(f"📊 Component Status: {working_components}/{total_components} working")
    print()
    
    # Try to run full workflow, fallback to demo
    if working_components >= 3:  # Need at least 3 core components
        print("🎯 Attempting full VANTA v02 workflow...")
        if not run_full_vanta_workflow():
            print("🔄 Full workflow not ready, falling back to demo...")
            run_fallback_demo()
    else:
        print("⚠️  Too many components missing for full VANTA")
        print("📋 Component status:")
        for component, status in components_status.items():
            print(f"   {component}: {status}")
        
        if components_status.get("dual_track", "").startswith("✅"):
            print("\n🔄 Running demo mode...")
            run_fallback_demo()
        else:
            print("\n❌ Cannot run even demo mode")
            return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
