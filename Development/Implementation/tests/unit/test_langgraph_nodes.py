#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for VANTA LangGraph Nodes

This module contains comprehensive unit tests for all LangGraph node functions
in the VANTA system, testing both normal operation and error handling.
"""
# TASK-REF: LG_002 - LangGraph Node Implementation
# CONCEPT-REF: CON-VANTA-008 - LangGraph Integration

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from langchain_core.messages import HumanMessage, AIMessage

from src.langgraph.state.vanta_state import (
    VANTAState, 
    ActivationMode, 
    ActivationStatus, 
    ProcessingPath,
    create_empty_state
)
from src.langgraph.nodes.voice_nodes import (
    check_activation,
    process_audio,
    synthesize_speech
)
from src.langgraph.nodes.memory_nodes import (
    retrieve_context,
    update_memory,
    prune_memory
)
from src.langgraph.nodes.processing_nodes import (
    router_node,
    local_model_node,
    api_model_node,
    integration_node
)


class TestVoiceNodes:
    """Test suite for voice processing nodes."""
    
    def test_check_activation_continuous_mode(self):
        """Test activation check in continuous mode."""
        state = create_empty_state()
        state["config"]["activation_mode"] = ActivationMode.CONTINUOUS
        state["activation"]["status"] = ActivationStatus.LISTENING
        state["audio"]["current_audio"] = "some audio data"
        
        result = check_activation(state)
        
        assert result["activation"]["status"] == ActivationStatus.PROCESSING
        assert "last_activation_time" in result["activation"]
    
    def test_check_activation_wake_word_mode(self):
        """Test activation check in wake word mode."""
        state = create_empty_state()
        state["config"]["activation_mode"] = ActivationMode.WAKE_WORD
        state["activation"]["status"] = ActivationStatus.LISTENING
        state["audio"]["current_audio"] = "hey vanta how are you"
        
        result = check_activation(state)
        
        assert result["activation"]["status"] == ActivationStatus.PROCESSING
        assert result["activation"]["wake_word_detected"] is True
    
    def test_check_activation_no_wake_word(self):
        """Test activation check without wake word."""
        state = create_empty_state()
        state["config"]["activation_mode"] = ActivationMode.WAKE_WORD
        state["activation"]["status"] = ActivationStatus.LISTENING
        state["audio"]["current_audio"] = "just regular speech"
        
        result = check_activation(state)
        
        assert result["activation"]["status"] == ActivationStatus.LISTENING
        assert result["activation"]["wake_word_detected"] is False
    
    def test_check_activation_already_processing(self):
        """Test activation check when already processing."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        
        result = check_activation(state)
        
        assert result["activation"]["status"] == ActivationStatus.PROCESSING
    
    def test_check_activation_no_audio(self):
        """Test activation check with no audio data."""
        state = create_empty_state()
        state["config"]["activation_mode"] = ActivationMode.CONTINUOUS
        state["activation"]["status"] = ActivationStatus.LISTENING
        state["audio"]["current_audio"] = None
        
        result = check_activation(state)
        
        # Should return empty dict to maintain current listening state
        assert result == {}
    
    def test_check_activation_scheduled_mode(self):
        """Test activation check in scheduled mode."""
        state = create_empty_state()
        state["config"]["activation_mode"] = ActivationMode.SCHEDULED
        state["config"]["scheduled_times"] = [datetime.now().strftime("%H:%M")]
        state["audio"]["current_audio"] = "some audio"
        
        result = check_activation(state)
        
        assert result["activation"]["status"] == ActivationStatus.PROCESSING
    
    @patch('src.langgraph.nodes.voice_nodes.SpeechToTextProcessor')
    def test_process_audio_success(self, mock_stt):
        """Test successful audio processing."""
        # Setup mock
        mock_transcriber = Mock()
        mock_transcriber.transcribe.return_value = "Hello, how are you?"
        mock_stt.return_value = mock_transcriber
        
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["audio"]["current_audio"] = "audio_data"
        state["audio"]["audio_path"] = "/path/to/audio.wav"
        
        result = process_audio(state)
        
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "Hello, how are you?"
        assert result["audio"]["last_transcription"] == "Hello, how are you?"
        assert result["audio"]["current_audio"] is None
        assert len(result["memory"]["audio_entries"]) == 1
    
    def test_process_audio_not_processing(self):
        """Test audio processing when not in processing mode."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.LISTENING
        state["audio"]["current_audio"] = "audio_data"
        
        result = process_audio(state)
        
        assert result == {}
    
    def test_process_audio_no_audio(self):
        """Test audio processing with no audio data."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["audio"]["current_audio"] = None
        
        result = process_audio(state)
        
        assert result == {}
    
    @patch('src.langgraph.nodes.voice_nodes.SpeechToTextProcessor')
    def test_process_audio_error_handling(self, mock_stt):
        """Test audio processing error handling."""
        # Setup mock to raise exception
        mock_transcriber = Mock()
        mock_transcriber.transcribe.side_effect = Exception("Transcription failed")
        mock_stt.return_value = mock_transcriber
        
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["audio"]["current_audio"] = "audio_data"
        
        result = process_audio(state)
        
        assert len(result["messages"]) == 1
        assert "couldn't understand" in result["messages"][0].content
        assert "error" in result["audio"]
    
    @patch('src.langgraph.nodes.voice_nodes.TextToSpeechProcessor')
    def test_synthesize_speech_success(self, mock_tts):
        """Test successful speech synthesis."""
        # Setup mock
        mock_processor = Mock()
        mock_processor.synthesize.return_value = "audio_output_data"
        mock_tts.return_value = mock_processor
        
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.SPEAKING
        state["messages"] = [AIMessage(content="Hello there!")]
        
        result = synthesize_speech(state)
        
        assert result["audio"]["current_output"] == "audio_output_data"
        assert result["activation"]["status"] == ActivationStatus.INACTIVE
        assert "last_synthesis" in result["audio"]
    
    def test_synthesize_speech_not_speaking(self):
        """Test speech synthesis when not in speaking mode."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [AIMessage(content="Hello there!")]
        
        result = synthesize_speech(state)
        
        assert result == {}
    
    def test_synthesize_speech_no_ai_messages(self):
        """Test speech synthesis with no AI messages."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.SPEAKING
        state["messages"] = [HumanMessage(content="Hello")]
        
        result = synthesize_speech(state)
        
        assert result["activation"]["status"] == ActivationStatus.INACTIVE


class TestMemoryNodes:
    """Test suite for memory processing nodes."""
    
    @patch('src.langgraph.nodes.memory_nodes.MemoryEngine')
    def test_retrieve_context_success(self, mock_memory_engine):
        """Test successful context retrieval."""
        # Setup mock
        mock_engine = Mock()
        mock_engine.retrieve_conversation_context.return_value = [
            {"user_message": "Previous question", "ai_message": "Previous answer"}
        ]
        mock_engine.retrieve_semantic_context.return_value = [
            {"content": "Related information"}
        ]
        mock_memory_engine.return_value = mock_engine
        
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [HumanMessage(content="What is the weather?")]
        
        result = retrieve_context(state)
        
        assert "retrieved_context" in result["memory"]
        assert result["memory"]["retrieved_context"]["query"] == "What is the weather?"
        assert result["memory"]["retrieved_context"]["total_results"] == 2
    
    def test_retrieve_context_not_processing(self):
        """Test context retrieval when not processing."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.LISTENING
        
        result = retrieve_context(state)
        
        assert result == {}
    
    def test_retrieve_context_no_messages(self):
        """Test context retrieval with no messages."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = []
        
        result = retrieve_context(state)
        
        assert result == {}
    
    @patch('src.langgraph.nodes.memory_nodes.MemoryEngine')
    def test_retrieve_context_error_handling(self, mock_memory_engine):
        """Test context retrieval error handling."""
        # Setup mock to raise exception
        mock_engine = Mock()
        mock_engine.retrieve_conversation_context.side_effect = Exception("Memory error")
        mock_memory_engine.return_value = mock_engine
        
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [HumanMessage(content="Test query")]
        
        result = retrieve_context(state)
        
        assert "retrieved_context" in result["memory"]
        assert result["memory"]["retrieved_context"]["total_results"] == 0
        assert "error" in result["memory"]["retrieved_context"]
    
    @patch('src.langgraph.nodes.memory_nodes.MemoryEngine')
    def test_update_memory_success(self, mock_memory_engine):
        """Test successful memory update."""
        # Setup mock
        mock_engine = Mock()
        mock_memory_engine.return_value = mock_engine
        
        state = create_empty_state()
        state["messages"] = [
            HumanMessage(content="What is AI?"),
            AIMessage(content="AI is artificial intelligence.")
        ]
        
        result = update_memory(state)
        
        assert "conversation_history" in result["memory"]
        assert len(result["memory"]["conversation_history"]) == 1
        assert result["memory"]["conversation_history"][0]["user_message"] == "What is AI?"
        assert result["memory"]["conversation_history"][0]["ai_message"] == "AI is artificial intelligence."
    
    def test_update_memory_insufficient_messages(self):
        """Test memory update with insufficient messages."""
        state = create_empty_state()
        state["messages"] = [HumanMessage(content="Hello")]
        
        result = update_memory(state)
        
        assert result == {}
    
    def test_update_memory_no_conversation_pair(self):
        """Test memory update with no complete conversation pair."""
        state = create_empty_state()
        state["messages"] = [
            HumanMessage(content="First question"),
            HumanMessage(content="Second question")
        ]
        
        result = update_memory(state)
        
        assert result == {}
    
    def test_prune_memory_no_pruning_needed(self):
        """Test memory pruning when no pruning is needed."""
        state = create_empty_state()
        state["memory"]["conversation_history"] = [
            {"id": "1", "user_message": "Test", "ai_message": "Response"}
        ]
        state["config"]["max_conversation_history"] = 100
        
        result = prune_memory(state)
        
        assert result == {}
    
    @patch('src.langgraph.nodes.memory_nodes.MemoryEngine')
    def test_prune_memory_pruning_needed(self, mock_memory_engine):
        """Test memory pruning when pruning is needed."""
        # Setup mock
        mock_engine = Mock()
        mock_memory_engine.return_value = mock_engine
        
        # Create state with too many conversations
        conversations = [
            {"id": f"{i}", "user_message": f"Question {i}", "ai_message": f"Answer {i}"}
            for i in range(150)
        ]
        
        state = create_empty_state()
        state["memory"]["conversation_history"] = conversations
        state["config"]["max_conversation_history"] = 100
        
        result = prune_memory(state)
        
        assert len(result["memory"]["conversation_history"]) == 100
        assert result["memory"]["archived_count"] == 50
        assert "pruning_time" in result["memory"]


class TestProcessingNodes:
    """Test suite for dual-track processing nodes."""
    
    @patch('src.langgraph.nodes.processing_nodes.ProcessingRouter')
    def test_router_node_success(self, mock_router_class):
        """Test successful routing decision."""
        # Setup mock
        mock_decision = Mock()
        mock_decision.path = ProcessingPath.LOCAL
        mock_decision.reasoning = "Simple query suitable for local processing"
        mock_decision.confidence = 0.8
        mock_decision.complexity_score = 3
        
        mock_router = Mock()
        mock_router.determine_processing_path.return_value = mock_decision
        mock_router_class.return_value = mock_router
        
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [HumanMessage(content="What time is it?")]
        
        result = router_node(state)
        
        assert result["processing"]["path"] == ProcessingPath.LOCAL
        assert result["processing"]["reasoning"] == "Simple query suitable for local processing"
        assert result["processing"]["confidence"] == 0.8
    
    def test_router_node_not_processing(self):
        """Test router node when not processing."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.LISTENING
        
        result = router_node(state)
        
        assert result == {}
    
    def test_router_node_no_messages(self):
        """Test router node with no messages."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = []
        
        result = router_node(state)
        
        assert result == {}
    
    @patch('src.langgraph.nodes.processing_nodes.LocalModelClient')
    def test_local_model_node_success(self, mock_local_client_class):
        """Test successful local model processing."""
        # Setup mock
        mock_client = Mock()
        mock_client.generate_response.return_value = "Local model response"
        mock_client.model_name = "llama-7b"
        mock_local_client_class.return_value = mock_client
        
        state = create_empty_state()
        state["processing"]["path"] = ProcessingPath.LOCAL
        state["processing"]["local_completed"] = False
        state["messages"] = [HumanMessage(content="Test query")]
        
        result = local_model_node(state)
        
        assert result["processing"]["local_response"] == "Local model response"
        assert result["processing"]["local_completed"] is True
        assert "local_time" in result["processing"]
    
    def test_local_model_node_wrong_path(self):
        """Test local model node with wrong processing path."""
        state = create_empty_state()
        state["processing"]["path"] = ProcessingPath.API
        
        result = local_model_node(state)
        
        assert result == {}
    
    def test_local_model_node_already_completed(self):
        """Test local model node when already completed."""
        state = create_empty_state()
        state["processing"]["path"] = ProcessingPath.LOCAL
        state["processing"]["local_completed"] = True
        
        result = local_model_node(state)
        
        assert result == {}
    
    @patch('src.langgraph.nodes.processing_nodes.APIModelClient')
    def test_api_model_node_success(self, mock_api_client_class):
        """Test successful API model processing."""
        # Setup mock
        mock_client = Mock()
        mock_client.generate_response.return_value = "API model response"
        mock_client.model_name = "claude-3-sonnet"
        mock_api_client_class.return_value = mock_client
        
        state = create_empty_state()
        state["processing"]["path"] = ProcessingPath.API
        state["processing"]["api_completed"] = False
        state["messages"] = [HumanMessage(content="Complex query")]
        
        result = api_model_node(state)
        
        assert result["processing"]["api_response"] == "API model response"
        assert result["processing"]["api_completed"] is True
        assert "api_time" in result["processing"]
    
    def test_api_model_node_staged_waiting(self):
        """Test API model node in staged mode waiting for local completion."""
        state = create_empty_state()
        state["processing"]["path"] = ProcessingPath.STAGED
        state["processing"]["local_completed"] = False
        state["processing"]["api_completed"] = False
        
        result = api_model_node(state)
        
        assert result == {}
    
    def test_integration_node_local_only(self):
        """Test integration node with local-only processing."""
        state = create_empty_state()
        state["processing"] = {
            "path": ProcessingPath.LOCAL,
            "local_completed": True,
            "local_response": "Local response",
            "api_completed": False,
            "api_response": None
        }
        
        result = integration_node(state)
        
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "Local response"
        assert result["activation"]["status"] == ActivationStatus.SPEAKING
    
    def test_integration_node_api_only(self):
        """Test integration node with API-only processing."""
        state = create_empty_state()
        state["processing"] = {
            "path": ProcessingPath.API,
            "local_completed": False,
            "local_response": None,
            "api_completed": True,
            "api_response": "API response"
        }
        
        result = integration_node(state)
        
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "API response"
        assert result["activation"]["status"] == ActivationStatus.SPEAKING
    
    def test_integration_node_parallel_incomplete(self):
        """Test integration node with incomplete parallel processing."""
        state = create_empty_state()
        state["processing"] = {
            "path": ProcessingPath.PARALLEL,
            "local_completed": True,
            "local_response": "Local response",
            "api_completed": False,
            "api_response": None
        }
        
        result = integration_node(state)
        
        assert result == {}  # Wait for both to complete
    
    def test_integration_node_parallel_complete(self):
        """Test integration node with complete parallel processing."""
        state = create_empty_state()
        state["processing"] = {
            "path": ProcessingPath.PARALLEL,
            "local_completed": True,
            "local_response": "Local response",
            "api_completed": True,
            "api_response": "API response"
        }
        state["config"]["integration_strategy"] = "prefer_api"
        
        result = integration_node(state)
        
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "API response"
        assert result["activation"]["status"] == ActivationStatus.SPEAKING
    
    def test_integration_node_no_responses(self):
        """Test integration node with no responses available."""
        state = create_empty_state()
        state["processing"] = {
            "path": ProcessingPath.LOCAL,
            "local_completed": True,
            "local_response": "",
            "api_completed": False,
            "api_response": None
        }
        
        result = integration_node(state)
        
        assert len(result["messages"]) == 1
        assert "wasn't able to generate" in result["messages"][0].content


class TestNodeIntegration:
    """Integration tests for node interactions."""
    
    def test_voice_pipeline_flow(self):
        """Test the complete voice processing flow."""
        state = create_empty_state()
        
        # Step 1: Check activation
        state["config"]["activation_mode"] = ActivationMode.CONTINUOUS
        state["audio"]["current_audio"] = "test audio"
        
        result1 = check_activation(state)
        state["activation"].update(result1["activation"])
        
        # Step 2: Process audio
        with patch('src.langgraph.nodes.voice_nodes.SpeechToTextProcessor') as mock_stt:
            mock_transcriber = Mock()
            mock_transcriber.transcribe.return_value = "Hello VANTA"
            mock_stt.return_value = mock_transcriber
            
            result2 = process_audio(state)
            state["messages"].extend(result2["messages"])
            state["audio"].update(result2["audio"])
            state["memory"].update(result2["memory"])
        
        # Step 3: Synthesize speech
        state["messages"].append(AIMessage(content="Hello! How can I help you?"))
        state["activation"]["status"] = ActivationStatus.SPEAKING
        
        with patch('src.langgraph.nodes.voice_nodes.TextToSpeechProcessor') as mock_tts:
            mock_processor = Mock()
            mock_processor.synthesize.return_value = "audio_output"
            mock_tts.return_value = mock_processor
            
            result3 = synthesize_speech(state)
        
        # Verify the flow
        assert len(state["messages"]) == 2
        assert state["messages"][0].content == "Hello VANTA"
        assert state["messages"][1].content == "Hello! How can I help you?"
        assert result3["activation"]["status"] == ActivationStatus.INACTIVE
    
    def test_memory_processing_flow(self):
        """Test the complete memory processing flow."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [HumanMessage(content="What is machine learning?")]
        
        # Step 1: Retrieve context
        with patch('src.langgraph.nodes.memory_nodes.MemoryEngine') as mock_memory:
            mock_engine = Mock()
            mock_engine.retrieve_conversation_context.return_value = []
            mock_engine.retrieve_semantic_context.return_value = []
            mock_memory.return_value = mock_engine
            
            result1 = retrieve_context(state)
            state["memory"].update(result1["memory"])
        
        # Step 2: Add AI response and update memory
        state["messages"].append(AIMessage(content="Machine learning is a subset of AI."))
        
        with patch('src.langgraph.nodes.memory_nodes.MemoryEngine') as mock_memory:
            mock_engine = Mock()
            mock_memory.return_value = mock_engine
            
            result2 = update_memory(state)
            state["memory"].update(result2["memory"])
        
        # Verify the flow
        assert "retrieved_context" in state["memory"]
        assert len(state["memory"]["conversation_history"]) == 1
        assert state["memory"]["conversation_history"][0]["user_message"] == "What is machine learning?"
    
    def test_dual_track_processing_flow(self):
        """Test the complete dual-track processing flow."""
        state = create_empty_state()
        state["activation"]["status"] = ActivationStatus.PROCESSING
        state["messages"] = [HumanMessage(content="Explain quantum computing")]
        
        # Step 1: Router decision
        with patch('src.langgraph.nodes.processing_nodes.ProcessingRouter') as mock_router_class:
            mock_decision = Mock()
            mock_decision.path = ProcessingPath.PARALLEL
            mock_decision.reasoning = "Complex topic needs both models"
            mock_decision.confidence = 0.9
            mock_decision.complexity_score = 8
            
            mock_router = Mock()
            mock_router.determine_processing_path.return_value = mock_decision
            mock_router_class.return_value = mock_router
            
            result1 = router_node(state)
            state["processing"].update(result1["processing"])
        
        # Step 2: Local model processing
        with patch('src.langgraph.nodes.processing_nodes.LocalModelClient') as mock_local:
            mock_client = Mock()
            mock_client.generate_response.return_value = "Basic quantum explanation"
            mock_client.model_name = "llama-7b"
            mock_local.return_value = mock_client
            
            result2 = local_model_node(state)
            state["processing"].update(result2["processing"])
        
        # Step 3: API model processing
        with patch('src.langgraph.nodes.processing_nodes.APIModelClient') as mock_api:
            mock_client = Mock()
            mock_client.generate_response.return_value = "Detailed quantum explanation"
            mock_client.model_name = "claude-3-sonnet"
            mock_api.return_value = mock_client
            
            result3 = api_model_node(state)
            state["processing"].update(result3["processing"])
        
        # Step 4: Integration
        state["config"]["integration_strategy"] = "prefer_api"
        result4 = integration_node(state)
        
        # Verify the flow
        assert state["processing"]["path"] == ProcessingPath.PARALLEL
        assert state["processing"]["local_completed"] is True
        assert state["processing"]["api_completed"] is True
        assert len(result4["messages"]) == 1
        assert result4["messages"][0].content == "Detailed quantum explanation"
        assert result4["activation"]["status"] == ActivationStatus.SPEAKING


if __name__ == "__main__":
    pytest.main([__file__])