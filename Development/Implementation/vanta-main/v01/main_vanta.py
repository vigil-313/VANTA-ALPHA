#!/usr/bin/env python3
"""
VANTA Main Entry Point - Version 01
===================================

This is the main entry point for running VANTA with the real LangGraph workflow.
This version focuses on getting the complete architecture working with proper
memory integration and dual-track processing.

Usage:
    python main_vanta.py
    
Architecture:
    - Uses the full LangGraph workflow (not the demo hack)
    - Includes proper memory retrieval and storage
    - Real dual-track processing with local + API models
    - Complete voice pipeline integration
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
    print("📍 Version: 01 (Full LangGraph Workflow)")
    print("🎯 Goal: Complete dual-track AI assistant with memory")
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
        print("❌ LangGraph not available - this is critical for real VANTA")
        return False
    
    print("✅ Environment check passed!")
    print()
    return True

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
    
    # 2. Try to import memory system
    try:
        from src.memory.core import MemorySystem
        from src.vanta_workflow.nodes.memory_nodes import initialize_memory_system
        components_status["memory_system"] = "✅ Available"
        print("✅ Memory system")
    except ImportError as e:
        components_status["memory_system"] = f"❌ Import error: {e}"
        print(f"❌ Memory system: {e}")
    
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
    return components_status

def run_full_vanta_workflow():
    """Attempt to run the full VANTA LangGraph workflow."""
    print("🎯 Attempting to run full VANTA workflow...")
    
    try:
        # Import the real LangGraph workflow
        from src.vanta_workflow.graph import compile_vanta_graph, process_with_vanta_graph
        from src.vanta_workflow.state.vanta_state import VANTAState, ActivationStatus
        from src.vanta_workflow.nodes.memory_nodes import initialize_memory_system
        from langchain_core.messages import HumanMessage
        
        print("✅ LangGraph workflow components imported successfully")
        
        # Initialize memory system
        print("🔧 Initializing memory system...")
        initialize_memory_system()
        print("✅ Memory system initialized")
        
        # Compile the real VANTA graph
        print("🔧 Compiling VANTA LangGraph workflow...")
        graph = compile_vanta_graph()
        print("✅ VANTA LangGraph workflow compiled successfully")
        
        print("\n" + "="*50)
        print("🤖 VANTA - Real LangGraph Workflow")
        print("="*50)
        print("This is the COMPLETE VANTA architecture running!")
        print("Features: Memory integration, dual-track processing, full workflow")
        print()
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Create state for real LangGraph workflow with just the new message
                # LangGraph's checkpointer will handle state persistence automatically
                state = VANTAState(
                    messages=[HumanMessage(content=user_input)],
                    activation={'status': ActivationStatus.PROCESSING, 'trigger': 'user_input', 'timestamp': time.time()},
                    memory={'conversation_history': [], 'retrieved_context': {}, 'user_preferences': {}, 'recent_topics': []},
                    config={'activation_mode': 'continuous', 'voice_settings': {}},
                    audio={'current_audio': user_input}
                )
                
                print("🎯 Processing through REAL LangGraph workflow...")
                
                # Process with the REAL VANTA workflow
                result = process_with_vanta_graph(graph, state, thread_id="vanta_session_01")
                
                # Show response with cleaner formatting
                messages = result.get('messages', [])
                if messages and len(messages) > 1:
                    response = messages[-1].content
                    print(f"\n🤖 VANTA: {response}")
                    
                    # Show simplified processing stats
                    processing = result.get('processing', {})
                    if processing:
                        path = processing.get('path', 'unknown')
                        conf = processing.get('confidence', 0)
                        local_time = processing.get('local_processing_time', 0)
                        total_time = processing.get('total_processing_time', 0)
                        print(f"📊 [{path.upper()}] confidence:{conf:.2f} | processing:{local_time:.2f}s | total:{total_time:.2f}s")
                else:
                    print("❌ No response generated")
                
                print("" + "-" * 60)  # Separator for readability
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error in workflow: {e}")
                print("Continuing...")
        
        return True
        
    except ImportError as e:
        print(f"❌ LangGraph workflow import failed: {e}")
        print("🔧 Still need to fix LangGraph node imports")
        return False
    except Exception as e:
        print(f"❌ Full workflow failed: {e}")
        return False

def run_fallback_demo():
    """Run the working demo as fallback."""
    print("🔄 Running fallback demo workflow...")
    
    try:
        # Use the same import pattern as the working demo
        from src.models.dual_track.graph_nodes import DualTrackGraphNodes
        from src.vanta_workflow.state.vanta_state import VANTAState, ActivationStatus
        from langchain_core.messages import HumanMessage
        
        print("✅ Demo components loaded successfully")
        
        # Initialize dual-track system
        nodes = DualTrackGraphNodes()
        
        print("\n" + "="*50)
        print("🤖 VANTA Demo (Fallback Mode)")
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
    components_status = initialize_vanta_components()
    
    # Determine what we can run
    working_components = sum(1 for status in components_status.values() if status.startswith("✅"))
    total_components = len(components_status)
    
    print(f"📊 Component Status: {working_components}/{total_components} working")
    print()
    
    # Try to run full workflow, fallback to demo
    if working_components >= 3:  # Need at least 3 core components
        print("🎯 Attempting full VANTA workflow...")
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
