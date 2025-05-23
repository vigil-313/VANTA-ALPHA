# TASK-REF: DP-002 - Dual-Track Response Integration System
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
Integration tests for the dual-track processing graph nodes.

Tests the complete integration of dual-track processing components with the
LangGraph workflow system, ensuring proper coordination and response integration.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage

from src.models.dual_track.graph_nodes import DualTrackGraphNodes
from src.models.dual_track.config import DEFAULT_CONFIG, IntegrationStrategy
from src.models.dual_track.exceptions import DualTrackError, LocalModelError, APIModelError
from src.langgraph.state.vanta_state import VANTAState, ActivationStatus


class TestDualTrackGraphIntegration:
    """Test suite for dual-track graph node integration."""
    
    @pytest.fixture
    def graph_nodes(self):
        """Create DualTrackGraphNodes instance for testing."""
        return DualTrackGraphNodes(DEFAULT_CONFIG)
    
    @pytest.fixture
    def sample_state(self):
        """Create sample VANTA state for testing."""
        return {
            "messages": [
                HumanMessage(content="What is artificial intelligence?")
            ],
            "memory": {
                "retrieved_context": {
                    "conversation_context": [],
                    "semantic_context": []
                },
                "conversation_history": [],
                "user_preferences": {}
            },
            "activation": {
                "status": ActivationStatus.PROCESSING
            },
            "config": {
                "integration_strategy": "preference",
                "model_settings": {
                    "local": {"max_tokens": 512, "temperature": 0.7},
                    "api": {"max_tokens": 1024, "temperature": 0.7}
                }
            },
            "processing": {}
        }
    
    def test_enhanced_router_node_simple_query(self, graph_nodes, sample_state):
        """Test router node with simple query routing to local model."""
        sample_state["messages"] = [HumanMessage(content="Hello")]
        
        with patch.object(graph_nodes.router, 'determine_path') as mock_router:
            mock_router.return_value = Mock(
                path="local",
                confidence=0.9,
                reasoning="Simple greeting",
                features={"complexity": 0.2, "creativity": 0.1},
                estimated_local_time=0.5,
                estimated_api_time=2.0
            )
            
            result = graph_nodes.enhanced_router_node(sample_state)
            
            assert "processing" in result
            processing = result["processing"]
            assert processing["path"] == "local"
            assert processing["confidence"] == 0.9
            assert processing["reasoning"] == "Simple greeting"
            assert processing["local_completed"] == False
            assert processing["api_completed"] == False
            assert "timestamp" in processing
            
    def test_enhanced_router_node_complex_query(self, graph_nodes, sample_state):
        """Test router node with complex query routing to API model."""
        sample_state["messages"] = [
            HumanMessage(content="Explain the philosophical implications of quantum consciousness theory")
        ]
        
        with patch.object(graph_nodes.router, 'determine_path') as mock_router:
            mock_router.return_value = Mock(
                path="api",
                confidence=0.85,
                reasoning="Complex philosophical question requiring deep reasoning",
                features={"complexity": 0.9, "creativity": 0.8},
                estimated_local_time=2.0,
                estimated_api_time=3.0
            )
            
            result = graph_nodes.enhanced_router_node(sample_state)
            
            processing = result["processing"]
            assert processing["path"] == "api"
            assert processing["confidence"] == 0.85
            assert "philosophical" in processing["reasoning"]
            
    def test_enhanced_router_node_parallel_processing(self, graph_nodes, sample_state):
        """Test router node deciding on parallel processing."""
        sample_state["messages"] = [
            HumanMessage(content="What are the benefits and drawbacks of renewable energy?")
        ]
        
        with patch.object(graph_nodes.router, 'determine_path') as mock_router:
            mock_router.return_value = Mock(
                path="parallel",
                confidence=0.75,
                reasoning="Balanced analysis requiring both speed and depth",
                features={"complexity": 0.6, "time_sensitivity": 0.7},
                estimated_local_time=1.5,
                estimated_api_time=2.5
            )
            
            result = graph_nodes.enhanced_router_node(sample_state)
            
            processing = result["processing"]
            assert processing["path"] == "parallel"
            assert processing["confidence"] == 0.75
            
    def test_enhanced_local_processing_node_success(self, graph_nodes, sample_state):
        """Test successful local model processing."""
        sample_state["processing"] = {
            "path": "local",
            "local_completed": False
        }
        
        mock_response = {
            "content": "Hello! How can I help you today?",
            "generation_time": 0.8,
            "tokens_generated": 15,
            "finish_reason": "completed"
        }
        
        with patch.object(graph_nodes.local_controller, 'generate') as mock_generate:
            mock_generate.return_value = mock_response
            
            result = graph_nodes.enhanced_local_processing_node(sample_state)
            
            processing = result["processing"]
            assert processing["local_completed"] == True
            assert processing["local_response"] == mock_response
            assert processing["local_processing_time"] > 0
            assert processing["local_error"] is None
            assert "local_metadata" in processing
            
    def test_enhanced_local_processing_node_error(self, graph_nodes, sample_state):
        """Test local model processing with error handling."""
        sample_state["processing"] = {
            "path": "local",
            "local_completed": False
        }
        
        with patch.object(graph_nodes.local_controller, 'generate') as mock_generate:
            mock_generate.side_effect = LocalModelError("Model timeout")
            
            result = graph_nodes.enhanced_local_processing_node(sample_state)
            
            processing = result["processing"]
            assert processing["local_completed"] == True  # Marked completed to not block
            assert processing["local_response"] is None
            assert processing["local_error"] == "Model timeout"
            assert "local_metadata" in processing
            
    def test_enhanced_api_processing_node_success(self, graph_nodes, sample_state):
        """Test successful API model processing."""
        sample_state["processing"] = {
            "path": "api",
            "api_completed": False
        }
        
        mock_response = {
            "content": "Artificial intelligence is a field of computer science...",
            "usage": {"total_tokens": 150, "completion_time": 2.1},
            "finish_reason": "completed"
        }
        
        with patch.object(graph_nodes.api_controller, 'generate') as mock_generate:
            mock_generate.return_value = mock_response
            
            result = graph_nodes.enhanced_api_processing_node(sample_state)
            
            processing = result["processing"]
            assert processing["api_completed"] == True
            assert processing["api_response"] == mock_response
            assert processing["api_processing_time"] > 0
            assert processing["api_error"] is None
            assert "api_metadata" in processing
            
    def test_enhanced_api_processing_node_staged_skip(self, graph_nodes, sample_state):
        """Test API processing skipping in staged mode when local is sufficient."""
        sample_state["processing"] = {
            "path": "staged",
            "local_completed": True,
            "local_response": {
                "content": "This is a comprehensive and complete answer that addresses all aspects of the question."
            },
            "api_completed": False
        }
        
        result = graph_nodes.enhanced_api_processing_node(sample_state)
        
        # Should return empty dict (no processing needed)
        assert result == {}
        
    def test_enhanced_integration_node_local_only(self, graph_nodes, sample_state):
        """Test integration node with local-only processing."""
        sample_state["processing"] = {
            "path": "local",
            "local_completed": True,
            "local_response": {
                "content": "Hello! How can I help you?",
                "generation_time": 0.5
            },
            "api_completed": False,
            "api_response": None,
            "local_processing_time": 0.5,
            "api_processing_time": 0.0
        }
        
        with patch.object(graph_nodes.integrator, 'integrate_responses') as mock_integrate:
            mock_integrate.return_value = Mock(
                content="Hello! How can I help you?",
                source="local",
                integration_strategy="single_source",
                similarity_score=None,
                processing_time=0.1,
                metadata={"reason": "Only local response available"}
            )
            
            result = graph_nodes.enhanced_integration_node(sample_state)
            
            assert "messages" in result
            assert len(result["messages"]) == 1
            assert isinstance(result["messages"][0], AIMessage)
            assert result["messages"][0].content == "Hello! How can I help you?"
            assert result["activation"]["status"] == ActivationStatus.SPEAKING
            
            processing = result["processing"]
            assert processing["final_response"] == "Hello! How can I help you?"
            assert processing["integration_result"]["source"] == "local"
            assert processing["integration_error"] is None
            
    def test_enhanced_integration_node_parallel_processing(self, graph_nodes, sample_state):
        """Test integration node with parallel processing results."""
        sample_state["processing"] = {
            "path": "parallel",
            "local_completed": True,
            "local_response": {
                "content": "AI is machine intelligence.",
                "generation_time": 0.8
            },
            "api_completed": True,
            "api_response": {
                "content": "Artificial intelligence is a comprehensive field of computer science focused on creating intelligent machines.",
                "completion_time": 2.1
            },
            "local_processing_time": 0.8,
            "api_processing_time": 2.1
        }
        
        integrated_content = "AI is machine intelligence. To give you a more complete answer, artificial intelligence is a comprehensive field of computer science focused on creating intelligent machines."
        
        with patch.object(graph_nodes.integrator, 'integrate_responses') as mock_integrate:
            mock_integrate.return_value = Mock(
                content=integrated_content,
                source="integrated",
                integration_strategy="combine",
                similarity_score=0.6,
                processing_time=0.2,
                metadata={"reason": "Combined different responses"}
            )
            
            result = graph_nodes.enhanced_integration_node(sample_state)
            
            assert result["messages"][0].content == integrated_content
            
            processing = result["processing"]
            assert processing["integration_result"]["source"] == "integrated"
            assert processing["integration_result"]["strategy"] == "combine"
            assert processing["integration_result"]["similarity_score"] == 0.6
            assert processing["total_processing_time"] > 2.5  # Sum of all processing times
            
    def test_enhanced_integration_node_incomplete_processing(self, graph_nodes, sample_state):
        """Test integration node when processing is not yet complete."""
        sample_state["processing"] = {
            "path": "parallel",
            "local_completed": True,
            "local_response": {"content": "Partial response"},
            "api_completed": False,  # API still processing
            "api_response": None
        }
        
        result = graph_nodes.enhanced_integration_node(sample_state)
        
        # Should return empty dict (wait for completion)
        assert result == {}
        
    def test_enhanced_integration_node_fallback_on_error(self, graph_nodes, sample_state):
        """Test integration node fallback when integration fails."""
        sample_state["processing"] = {
            "path": "local",
            "local_completed": True,
            "local_response": {"content": "Valid response"},
            "api_completed": False,
            "local_processing_time": 0.5
        }
        
        with patch.object(graph_nodes.integrator, 'integrate_responses') as mock_integrate:
            mock_integrate.side_effect = Exception("Integration failed")
            
            result = graph_nodes.enhanced_integration_node(sample_state)
            
            assert "messages" in result
            assert "apologize" in result["messages"][0].content.lower()
            assert result["activation"]["status"] == ActivationStatus.SPEAKING
            
            processing = result["processing"]
            assert "fallback_used" in processing
            assert processing["fallback_used"] == True
            
    def test_statistics_tracking(self, graph_nodes, sample_state):
        """Test that processing statistics are properly tracked."""
        initial_stats = graph_nodes.get_processing_stats()
        initial_requests = initial_stats["total_requests"]
        
        # Mock router response
        with patch.object(graph_nodes.router, 'determine_path') as mock_router:
            mock_router.return_value = Mock(
                path="local",
                confidence=0.9,
                reasoning="Test query",
                features={},
                estimated_local_time=0.5,
                estimated_api_time=2.0
            )
            
            # Process a routing decision
            graph_nodes.enhanced_router_node(sample_state)
            
            updated_stats = graph_nodes.get_processing_stats()
            assert updated_stats["total_requests"] == initial_requests + 1
            assert updated_stats["path_usage"]["local"] > initial_stats["path_usage"]["local"]
            
    def test_error_handling_no_messages(self, graph_nodes, sample_state):
        """Test error handling when no messages are available."""
        sample_state["messages"] = []
        
        result = graph_nodes.enhanced_router_node(sample_state)
        assert result == {}
        
    def test_error_handling_inactive_state(self, graph_nodes, sample_state):
        """Test error handling when activation status is not PROCESSING."""
        sample_state["activation"]["status"] = ActivationStatus.IDLE
        
        result = graph_nodes.enhanced_router_node(sample_state)
        assert result == {}
        
    def test_performance_optimization_staged_processing(self, graph_nodes, sample_state):
        """Test performance optimization in staged processing."""
        # Set up staged processing with good local response
        sample_state["processing"] = {
            "path": "staged",
            "local_completed": True,
            "local_response": {
                "content": "This is a complete and satisfactory response that fully addresses the user's question."
            },
            "api_completed": False
        }
        
        result = graph_nodes.enhanced_api_processing_node(sample_state)
        
        # API processing should be skipped
        assert result == {}
        
    def test_memory_context_integration(self, graph_nodes, sample_state):
        """Test integration with memory system context."""
        sample_state["memory"] = {
            "retrieved_context": {
                "conversation_context": [
                    {"user_message": "Previous question", "ai_message": "Previous answer"}
                ],
                "semantic_context": ["Related information"]
            },
            "conversation_history": [
                {"user_message": "Old query", "ai_message": "Old response"}
            ],
            "user_preferences": {"response_style": "detailed"}
        }
        
        with patch.object(graph_nodes.router, 'determine_path') as mock_router:
            mock_router.return_value = Mock(
                path="api",
                confidence=0.8,
                reasoning="Context-aware routing",
                features={},
                estimated_local_time=1.0,
                estimated_api_time=2.0
            )
            
            result = graph_nodes.enhanced_router_node(sample_state)
            
            # Verify context was passed to router
            call_args = mock_router.call_args
            context_arg = call_args[0][1]  # Second argument (context)
            assert "retrieved_context" in context_arg
            assert "conversation_history" in context_arg
            assert "user_preferences" in context_arg