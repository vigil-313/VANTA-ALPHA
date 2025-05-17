# VANTA LangGraph Example with Memory and Voice Processing
from typing import Annotated, Dict, List, Optional, Sequence, TypedDict, Union
import json
from datetime import datetime
import os
from enum import Enum

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

# Simulated voice processing imports
# In a real implementation, these would be actual voice processing libraries
class SimulatedWhisper:
    def transcribe(self, audio_data):
        # Simulate Whisper transcription
        # For demo purposes, we'll just return a hardcoded response
        return "What's the weather in San Francisco today?"
    
class SimulatedCSM:
    def synthesize(self, text, voice_id="default"):
        # Simulate CSM text-to-speech
        return f"AUDIO_DATA_{hash(text)}"

# Enums for VANTA states
class ActivationMode(str, Enum):
    CONTINUOUS = "continuous"
    WAKE_WORD = "wake_word"
    SCHEDULED = "scheduled"
    
class ActivationStatus(str, Enum):
    INACTIVE = "inactive"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

# State definition with typed annotations
class VANTAState(TypedDict):
    """Full state for VANTA agent."""
    # Conversation messages using add_messages reducer
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Audio processing metadata
    audio: Dict
    # Memory references and context
    memory: Dict
    # System configuration
    config: Dict
    # Current activation state
    activation: Dict

# Initialize our simulated voice components
whisper = SimulatedWhisper()
csm = SimulatedCSM()

# Define our nodes (components)
def check_activation(state: VANTAState):
    """Determines if VANTA should activate based on the current mode."""
    activation_mode = state["config"]["activation_mode"]
    current_status = state["activation"]["status"]
    
    # If already processing or speaking, continue the pipeline
    if current_status in [ActivationStatus.PROCESSING, ActivationStatus.SPEAKING]:
        return {"activation": {"status": ActivationStatus.PROCESSING}}
    
    # Otherwise, check if we should activate based on the mode
    audio_data = state["audio"].get("current_audio")
    wake_word_detected = "hey vanta" in str(audio_data).lower()  # Simplified detection
    
    # Continuous mode: always activate
    if activation_mode == ActivationMode.CONTINUOUS and audio_data:
        return {"activation": {"status": ActivationStatus.PROCESSING}}
    
    # Wake word mode: activate only if wake word detected
    elif activation_mode == ActivationMode.WAKE_WORD and wake_word_detected:
        return {"activation": {"status": ActivationStatus.PROCESSING}}
    
    # Scheduled mode: activate based on schedule
    elif activation_mode == ActivationMode.SCHEDULED:
        # Check if current time matches a scheduled time
        current_time = datetime.now().strftime("%H:%M")
        scheduled_times = state["config"].get("scheduled_times", [])
        
        if current_time in scheduled_times:
            return {"activation": {"status": ActivationStatus.PROCESSING}}
    
    # Default: remain inactive
    return {"activation": {"status": ActivationStatus.INACTIVE}}

def process_audio(state: VANTAState):
    """Processes audio input using Whisper for transcription."""
    audio_data = state["audio"].get("current_audio", "")
    
    # Skip if no audio or not in processing mode
    if not audio_data or state["activation"]["status"] != ActivationStatus.PROCESSING:
        return {}
    
    # Transcribe audio using Whisper (simulated)
    transcription = whisper.transcribe(audio_data)
    
    # Store the transcription result and original audio path in long-term memory
    audio_metadata = {
        "timestamp": datetime.now().isoformat(),
        "transcription": transcription,
        "audio_reference": state["audio"].get("audio_path", ""),
    }
    
    return {
        "messages": [HumanMessage(content=transcription)],
        "audio": {"last_transcription": transcription, "metadata": audio_metadata},
        "memory": {
            "audio_entries": state["memory"].get("audio_entries", []) + [audio_metadata]
        }
    }

def retrieve_context(state: VANTAState):
    """Retrieves relevant context from the memory system."""
    # Skip if we're not processing
    if state["activation"]["status"] != ActivationStatus.PROCESSING:
        return {}
    
    # Get the last message
    if not state["messages"]:
        return {}
        
    last_message = state["messages"][-1]
    
    # In a real implementation, this would query a vector store
    # For our example, we'll simulate some basic keyword-based retrieval
    query = last_message.content.lower()
    
    relevant_memories = []
    context_summary = ""
    
    # Super simple "retrieval" based on keywords
    if "weather" in query and "san francisco" in query:
        relevant_memories = ["User frequently asks about SF weather"]
        context_summary = "User is interested in San Francisco weather forecasts."
    elif "name" in query:
        relevant_memories = ["User introduced themselves as Alex"]
        context_summary = "User's name is Alex based on previous conversations."
    
    # Update memory state with retrieved context
    return {
        "memory": {
            "retrieved_context": {
                "relevant_memories": relevant_memories,
                "summary": context_summary,
                "query_timestamp": datetime.now().isoformat(),
            }
        }
    }

def generate_response(state: VANTAState):
    """Generates a response using an LLM with memory context."""
    # Skip if we're not processing
    if state["activation"]["status"] != ActivationStatus.PROCESSING:
        return {}
    
    # Get the last message and retrieved context
    if not state["messages"]:
        return {}
        
    last_message = state["messages"][-1].content
    retrieved_context = state["memory"].get("retrieved_context", {})
    
    # In a real implementation, this would call the LLM
    # For our example, we'll simulate responses based on the input
    response = ""
    
    # Simplified response generation based on keywords
    if "weather" in last_message.lower() and "san francisco" in last_message.lower():
        response = "It's currently sunny and 68 degrees in San Francisco. The forecast shows clear skies throughout the day."
    elif "name" in last_message.lower():
        if "Alex" in str(retrieved_context):
            response = "Your name is Alex, as you mentioned earlier."
        else:
            response = "I don't believe you've told me your name yet."
    else:
        response = "I'm not sure how to respond to that. Is there something specific you'd like to know?"
    
    # Update state with the generated response
    return {
        "messages": [AIMessage(content=response)],
        "activation": {"status": ActivationStatus.SPEAKING}
    }

def synthesize_speech(state: VANTAState):
    """Converts text to speech using CSM."""
    # Skip if we're not in speaking mode
    if state["activation"]["status"] != ActivationStatus.SPEAKING:
        return {}
    
    # Get the last AI message
    if not state["messages"] or not isinstance(state["messages"][-1], AIMessage):
        return {}
        
    response_text = state["messages"][-1].content
    
    # Generate speech using CSM (simulated)
    audio_data = csm.synthesize(response_text)
    
    # In a real implementation, this would save the audio file
    # and play it through the speakers
    audio_path = f"/tmp/vanta_response_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
    
    # Update audio state with synthesized speech info
    return {
        "audio": {
            "last_synthesis": {
                "text": response_text,
                "audio_data": audio_data,
                "audio_path": audio_path,
                "timestamp": datetime.now().isoformat(),
            }
        },
        "activation": {"status": ActivationStatus.INACTIVE}  # Reset to inactive after speaking
    }

def update_memory(state: VANTAState):
    """Updates the memory system with the current conversation."""
    # Only update memory if we have processed something
    if not state["messages"] or len(state["messages"]) < 2:
        return {}
    
    # Get the last user-assistant exchange
    last_messages = state["messages"][-2:]
    
    if isinstance(last_messages[0], HumanMessage) and isinstance(last_messages[1], AIMessage):
        # Create a conversation memory entry
        memory_entry = {
            "user_message": last_messages[0].content,
            "assistant_message": last_messages[1].content,
            "timestamp": datetime.now().isoformat(),
            "audio_reference": state["audio"].get("audio_path", ""),
        }
        
        # In a real implementation, this would be stored in a database
        # and indexed for retrieval
        
        # Update memory state
        conversation_history = state["memory"].get("conversation_history", [])
        conversation_history.append(memory_entry)
        
        return {
            "memory": {
                "conversation_history": conversation_history,
                "last_interaction": datetime.now().isoformat(),
            }
        }
    
    return {}

# Create our graph
workflow = StateGraph(VANTAState)

# Add our nodes
workflow.add_node("check_activation", check_activation)
workflow.add_node("process_audio", process_audio)
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("generate_response", generate_response)
workflow.add_node("synthesize_speech", synthesize_speech)
workflow.add_node("update_memory", update_memory)

# Define the conditional edge for activation
def should_process(state: VANTAState):
    """Determines if we should process audio based on activation status."""
    if state["activation"]["status"] == ActivationStatus.INACTIVE:
        return "end"
    return "continue"

# Define our edges
workflow.set_entry_point("check_activation")
workflow.add_conditional_edges(
    "check_activation",
    should_process,
    {
        "continue": "process_audio",
        "end": END
    }
)
workflow.add_edge("process_audio", "retrieve_context")
workflow.add_edge("retrieve_context", "generate_response")
workflow.add_edge("generate_response", "synthesize_speech")
workflow.add_edge("synthesize_speech", "update_memory")
workflow.add_edge("update_memory", END)

# Set up persistence
checkpointer = InMemorySaver()

# Compile the graph
graph = workflow.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    # Initialize the state
    initial_state = {
        "messages": [],
        "audio": {"current_audio": "hey vanta, what's the weather in San Francisco?"},
        "memory": {},
        "config": {"activation_mode": ActivationMode.WAKE_WORD},
        "activation": {"status": ActivationStatus.LISTENING}
    }
    
    # Execute the graph with thread ID for persistence
    thread_id = "user_session_123"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Run the graph and get the result
    result = graph.invoke(initial_state, config)
    
    # Print the result
    print("First interaction result:")
    print(f"Messages: {[m.content for m in result['messages']]}")
    print(f"Activation status: {result['activation']['status']}")
    print(f"Memory entries: {len(result['memory'].get('conversation_history', []))}")
    
    # Now let's run a follow-up query using the persisted state
    follow_up_input = {
        "audio": {"current_audio": "hey vanta, what's my name?"},
        "activation": {"status": ActivationStatus.LISTENING}
    }
    
    # The graph will automatically load the previous state because we're using the same thread_id
    follow_up_result = graph.invoke(follow_up_input, config)
    
    print("\nSecond interaction result:")
    print(f"Messages: {[m.content for m in follow_up_result['messages']]}")
    print(f"Activation status: {follow_up_result['activation']['status']}")
    print(f"Memory entries: {len(follow_up_result['memory'].get('conversation_history', []))}")