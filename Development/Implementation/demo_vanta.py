#!/usr/bin/env python3
"""
VANTA Dual-Track AI Demo
========================

Interactive demo of the VANTA dual-track processing system.
Shows intelligent routing between local Llama 2 and Anthropic Claude API.
"""

import os
import sys
import time
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from langchain_core.messages import HumanMessage, AIMessage
from src.models.dual_track.graph_nodes import DualTrackGraphNodes
from src.langgraph.state.vanta_state import VANTAState, ActivationStatus

def print_header():
    """Print the demo header."""
    print("🤖 " + "=" * 60)
    print("🤖  VANTA DUAL-TRACK AI ASSISTANT DEMO")
    print("🤖 " + "=" * 60)
    print("🧠  Local Model:  Llama 2-7B-Chat (Real AI)")
    print("☁️   API Model:    Anthropic Claude")
    print("🎯  Smart Routing: Based on complexity & context")
    print("🤖 " + "=" * 60)
    print()
    print("Type your questions and see the intelligent routing in action!")
    print("Commands: 'quit' to exit, 'stats' for statistics")
    print()

def print_routing_info(processing: Dict[str, Any]):
    """Print routing decision information."""
    if not processing:
        return
    
    path = processing.get('path', 'unknown')
    confidence = processing.get('confidence', 0)
    reasoning = processing.get('reasoning', 'No reasoning available')
    
    # Choose emoji based on path
    path_emoji = {
        'local': '🧠',
        'api': '☁️',
        'parallel': '🔀',
        'staged': '📈'
    }.get(path, '❓')
    
    print(f"{path_emoji} ROUTING: {path.upper()} (confidence: {confidence:.2f})")
    print(f"💭 Reasoning: {reasoning}")

def print_response_info(processing: Dict[str, Any]):
    """Print response information."""
    if not processing:
        return
    
    local_completed = processing.get('local_completed', False)
    api_completed = processing.get('api_completed', False)
    local_time = processing.get('local_processing_time', 0)
    api_time = processing.get('api_processing_time', 0)
    integration_time = processing.get('integration_time', 0)
    total_time = processing.get('total_processing_time', 0)
    
    print("\n📊 PROCESSING STATS:")
    if local_completed:
        print(f"   🧠 Local:  {local_time:.2f}s")
    if api_completed:
        print(f"   ☁️  API:    {api_time:.2f}s")
    if integration_time:
        print(f"   🔧 Integration: {integration_time:.2f}s")
    print(f"   ⏱️  Total:  {total_time:.2f}s")

def create_demo_state(user_input: str, conversation_history: list) -> VANTAState:
    """Create a VANTA state for processing."""
    # Add user message
    messages = conversation_history + [HumanMessage(content=user_input)]
    
    return VANTAState(
        messages=messages,
        activation={
            "status": ActivationStatus.PROCESSING,
            "trigger": "user_input",
            "timestamp": time.time()
        },
        memory={
            "conversation_history": [],
            "retrieved_context": {},
            "user_preferences": {},
            "recent_topics": []
        }
    )

def demo_interaction():
    """Run the interactive demo."""
    print_header()
    
    # Initialize the dual-track system
    try:
        print("🔄 Initializing VANTA dual-track system...")
        nodes = DualTrackGraphNodes()
        print("✅ System ready!\n")
    except Exception as e:
        print(f"❌ Failed to initialize system: {e}")
        return
    
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("👤 You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
                
            if user_input.lower() == 'stats':
                stats = nodes.get_processing_stats()
                print("\n📈 VANTA STATISTICS:")
                print(f"   Total requests: {stats['total_requests']}")
                print(f"   Successful integrations: {stats['successful_integrations']}")
                print(f"   Failed integrations: {stats['failed_integrations']}")
                print(f"   Average processing time: {stats['average_processing_time']:.2f}s")
                print("   Path usage:")
                for path, count in stats['path_usage'].items():
                    print(f"     {path}: {count}")
                print()
                continue
            
            print()
            
            # Create state and process through dual-track system
            state = create_demo_state(user_input, conversation_history)
            
            # 1. Router decision
            print("🎯 ANALYZING QUERY...")
            state = nodes.enhanced_router_node(state)
            processing = state.get('processing', {})
            print_routing_info(processing)
            print()
            
            # 2. Processing
            path = processing.get('path', 'local')
            
            if path in ['local', 'parallel', 'staged']:
                print("🧠 Processing with local model...")
                state = nodes.enhanced_local_processing_node(state)
            
            if path in ['api', 'parallel', 'staged']:
                print("☁️  Processing with API model...")
                state = nodes.enhanced_api_processing_node(state)
            
            # 3. Integration
            print("🔧 Integrating responses...")
            state = nodes.enhanced_integration_node(state)
            
            # 4. Display results
            messages = state.get('messages', [])
            if messages and isinstance(messages[-1], AIMessage):
                print(f"\n🤖 VANTA: {messages[-1].content}")
                conversation_history.extend([
                    HumanMessage(content=user_input),
                    messages[-1]
                ])
            else:
                print("\n❌ No response generated")
            
            # 5. Show processing stats
            processing = state.get('processing', {})
            print_response_info(processing)
            print("\n" + "-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again.\n")

if __name__ == "__main__":
    demo_interaction()
