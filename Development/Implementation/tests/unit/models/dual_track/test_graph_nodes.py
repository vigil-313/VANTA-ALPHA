# TASK-REF: DP-002 - Dual-Track Response Integration System
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
Unit tests for the dual-track processing graph nodes.

Tests the individual functionality of each graph node component including
routing logic, processing coordination, and response integration.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage

from src.models.dual_track.graph_nodes import DualTrackGraphNodes
from src.models.dual_track.config import DEFAULT_CONFIG, IntegrationStrategy, InterruptStyle
from src.models.dual_track.exceptions import DualTrackError, LocalModelError, APIModelError, IntegrationError


class TestDualTrackGraphNodes:
    """Test suite for DualTrackGraphNodes class."""
    
    @pytest.fixture
    def graph_nodes(self):
        """Create DualTrackGraphNodes instance for testing."""
        return DualTrackGraphNodes(DEFAULT_CONFIG)
    
    @pytest.fixture
    def sample_state(self):
        """Create sample state for testing."""
        return {
            "messages": [HumanMessage(content="Test query")],
            "memory": {
                "retrieved_context": {},
                "conversation_history": [],
                "user_preferences": {}
            },
            "activation": {"status": "processing"},
            "config": {"integration_strategy": "preference"},
            "processing": {}
        }
    
    def test_initialization(self, graph_nodes):
        """Test proper initialization of DualTrackGraphNodes."""
        assert graph_nodes.config == DEFAULT_CONFIG
        assert graph_nodes.router is not None
        assert graph_nodes.local_controller is not None
        assert graph_nodes.api_controller is not None
        assert graph_nodes.integrator is not None
        assert graph_nodes.executor is not None
        
        # Check initial statistics
        stats = graph_nodes.processing_stats
        assert stats["total_requests"] == 0
        assert stats["successful_integrations"] == 0
        assert stats["failed_integrations"] == 0
        assert stats["average_processing_time"] == 0.0
        assert all(count == 0 for count in stats["path_usage"].values())
    
    def test_is_local_response_sufficient_good_response(self, graph_nodes):
        """Test sufficient local response detection."""
        good_response = {
            "content": "This is a comprehensive response that fully addresses the question with detailed information and ends properly."
        }
        
        assert graph_nodes._is_local_response_sufficient(good_response) == True
    
    def test_is_local_response_sufficient_short_response(self, graph_nodes):
        """Test insufficient short local response."""
        short_response = {
            "content": "Yes."
        }
        
        assert graph_nodes._is_local_response_sufficient(short_response) == False
    
    def test_is_local_response_sufficient_error_response(self, graph_nodes):
        """Test insufficient error response."""
        error_response = {
            "content": "I'm sorry, but I encountered an error while processing your request."
        }
        
        assert graph_nodes._is_local_response_sufficient(error_response) == False
    
    def test_is_local_response_sufficient_incomplete_response(self, graph_nodes):
        """Test insufficient incomplete response."""
        incomplete_response = {
            "content": "This is a response that doesn't end properly and seems to be cut off"
        }
        
        # Should be False for incomplete response (no proper ending punctuation)
        assert graph_nodes._is_local_response_sufficient(incomplete_response) == False
    
    def test_is_local_response_sufficient_none_response(self, graph_nodes):
        """Test handling of None response."""
        assert graph_nodes._is_local_response_sufficient(None) == False
        assert graph_nodes._is_local_response_sufficient({}) == False
    
    def test_build_api_conversation_basic(self, graph_nodes):
        """Test building API conversation from messages and memory."""
        messages = [
            HumanMessage(content="What is AI?"),
            AIMessage(content="AI is artificial intelligence."),
            HumanMessage(content="Tell me more.")
        ]
        
        memory = {
            "retrieved_context": {
                "conversation_context": [
                    {"user_message": "Previous question", "ai_message": "Previous answer"}
                ]
            },
            "conversation_history": [
                {"user_message": "Old query", "ai_message": "Old response"}
            ]
        }
        
        api_messages = graph_nodes._build_api_conversation(messages, memory)
        
        # Should include system context, conversation history, and current messages
        assert len(api_messages) > 0
        assert any(msg["role"] == "system" for msg in api_messages)
        assert any(msg["role"] == "user" for msg in api_messages)
        assert any(msg["role"] == "assistant" for msg in api_messages)
    
    def test_build_api_conversation_no_context(self, graph_nodes):
        """Test building API conversation without context."""
        messages = [HumanMessage(content="Simple question")]
        memory = {}
        
        api_messages = graph_nodes._build_api_conversation(messages, memory)
        
        # Should still have the current message
        assert len(api_messages) >= 1
        assert api_messages[-1]["role"] == "user"
        assert api_messages[-1]["content"] == "Simple question"
    
    def test_format_context_summary(self, graph_nodes):
        """Test context summary formatting."""
        context = {
            "conversation_context": ["some conversation data"],
            "semantic_context": ["some semantic data"],
            "user_preferences": {"style": "detailed"}
        }
        
        summary = graph_nodes._format_context_summary(context)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "conversation" in summary.lower() or "preferences" in summary.lower()
    
    def test_format_context_summary_empty(self, graph_nodes):
        """Test context summary formatting with empty context."""
        context = {}
        
        summary = graph_nodes._format_context_summary(context)
        
        assert summary == "General conversation"
    
    def test_create_fallback_response(self, graph_nodes):
        """Test creation of fallback response."""
        processing = {
            "path": "local",
            "local_response": {"content": "Valid local response"},
            "api_response": None
        }
        
        result = graph_nodes._create_fallback_response(processing, error="Test error")
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert "activation" in result
        assert result["processing"]["integration_error"] == "Test error"
        assert result["processing"]["fallback_used"] == True
        
        # Should prefer valid response over generic fallback
        content = result["messages"][0].content
        assert "Valid local response" in content or "trouble generating" in content
    
    def test_update_average_processing_time(self, graph_nodes):
        """Test processing time averaging."""
        # Start with one request
        graph_nodes.processing_stats["total_requests"] = 1
        graph_nodes.processing_stats["average_processing_time"] = 1.0
        
        # Add second request
        graph_nodes.processing_stats["total_requests"] = 2
        graph_nodes._update_average_processing_time(3.0)
        
        # Average should be (1.0 + 3.0) / 2 = 2.0
        assert graph_nodes.processing_stats["average_processing_time"] == 2.0
    
    def test_get_processing_stats(self, graph_nodes):
        """Test processing statistics retrieval."""
        stats = graph_nodes.get_processing_stats()
        
        assert "total_requests" in stats
        assert "successful_integrations" in stats
        assert "failed_integrations" in stats
        assert "average_processing_time" in stats
        assert "path_usage" in stats
        assert "integrator_stats" in stats
        
        # Check path usage structure
        path_usage = stats["path_usage"]
        assert "local" in path_usage
        assert "api" in path_usage
        assert "parallel" in path_usage
        assert "staged" in path_usage
    
    def test_reset_stats(self, graph_nodes):
        """Test statistics reset functionality."""
        # Set some stats
        graph_nodes.processing_stats["total_requests"] = 10
        graph_nodes.processing_stats["successful_integrations"] = 8
        graph_nodes.processing_stats["path_usage"]["local"] = 5
        
        # Reset
        graph_nodes.reset_stats()
        
        stats = graph_nodes.processing_stats
        assert stats["total_requests"] == 0
        assert stats["successful_integrations"] == 0
        assert stats["failed_integrations"] == 0
        assert stats["average_processing_time"] == 0.0
        assert all(count == 0 for count in stats["path_usage"].values())
    
    def test_enhanced_router_node_error_handling(self, graph_nodes):
        """Test router node error handling."""
        state = {
            "activation": {"status": "processing"},
            "messages": [HumanMessage(content="Test")]
            # Missing memory and config to trigger error
        }
        
        with patch.object(graph_nodes.router, 'determine_path') as mock_router:
            mock_router.side_effect = Exception("Router error")
            
            result = graph_nodes.enhanced_router_node(state)
            
            assert "processing" in result
            processing = result["processing"]
            assert "error" in processing
            assert processing["path"] == "local"  # Fallback
            assert processing["confidence"] == 0.5
    
    def test_enhanced_local_processing_node_skip_conditions(self, graph_nodes):
        """Test local processing node skip conditions."""
        # Test skip when path doesn't include local
        state = {
            "processing": {"path": "api", "local_completed": False},
            "messages": [HumanMessage(content="Test")]
        }
        
        result = graph_nodes.enhanced_local_processing_node(state)
        assert result == {}
        
        # Test skip when already completed
        state["processing"]["path"] = "local"
        state["processing"]["local_completed"] = True
        
        result = graph_nodes.enhanced_local_processing_node(state)
        assert result == {}
    
    def test_enhanced_api_processing_node_skip_conditions(self, graph_nodes):
        """Test API processing node skip conditions."""
        # Test skip when path doesn't include API
        state = {
            "processing": {"path": "local", "api_completed": False},
            "messages": [HumanMessage(content="Test")]
        }
        
        result = graph_nodes.enhanced_api_processing_node(state)
        assert result == {}
        
        # Test skip when already completed
        state["processing"]["path"] = "api"
        state["processing"]["api_completed"] = True
        
        result = graph_nodes.enhanced_api_processing_node(state)
        assert result == {}
    
    def test_enhanced_integration_node_path_completion_requirements(self, graph_nodes):
        """Test integration node completion requirements for different paths."""
        base_state = {
            "processing": {"path": "local"},
            "messages": [HumanMessage(content="Test")]
        }
        
        # Test local path - needs local completion
        state = base_state.copy()
        state["processing"]["local_completed"] = False
        result = graph_nodes.enhanced_integration_node(state)
        assert result == {}
        
        # Test parallel path - needs both completions
        state = base_state.copy()
        state["processing"]["path"] = "parallel"
        state["processing"]["local_completed"] = True
        state["processing"]["api_completed"] = False
        result = graph_nodes.enhanced_integration_node(state)
        assert result == {}
        
        # Test staged path - needs at least one completion
        state = base_state.copy()
        state["processing"]["path"] = "staged"
        state["processing"]["local_completed"] = False
        state["processing"]["api_completed"] = False
        result = graph_nodes.enhanced_integration_node(state)
        assert result == {}
    
    def test_enhanced_integration_node_no_responses(self, graph_nodes):
        """Test integration node handling when no responses are available."""
        state = {
            "processing": {
                "path": "local",
                "local_completed": True,
                "local_response": None,
                "api_completed": False,
                "api_response": None
            },
            "messages": [HumanMessage(content="Test")]
        }
        
        result = graph_nodes.enhanced_integration_node(state)
        
        assert "messages" in result
        assert "apologize" in result["messages"][0].content.lower()
        assert result["processing"]["fallback_used"] == True
    
    def test_configuration_injection(self):
        """Test that custom configuration is properly injected."""
        custom_config = DEFAULT_CONFIG
        custom_config.integration.strategy = IntegrationStrategy.COMBINE
        custom_config.integration.interrupt_style = InterruptStyle.ABRUPT
        
        graph_nodes = DualTrackGraphNodes(custom_config)
        
        assert graph_nodes.config.integration.strategy == IntegrationStrategy.COMBINE
        assert graph_nodes.config.integration.interrupt_style == InterruptStyle.ABRUPT
    
    def test_thread_pool_initialization(self, graph_nodes):
        """Test that thread pool is properly initialized."""
        assert graph_nodes.executor is not None
        assert graph_nodes.executor._max_workers == 2
        assert "dual_track" in graph_nodes.executor._thread_name_prefix


class TestModuleFunctions:
    """Test module-level convenience functions."""
    
    def test_convenience_function_exports(self):
        """Test that convenience functions are properly exported."""
        from src.models.dual_track.graph_nodes import (
            enhanced_router_node,
            enhanced_local_processing_node,
            enhanced_api_processing_node,
            enhanced_integration_node,
            get_dual_track_stats,
            reset_dual_track_stats
        )
        
        # All functions should be callable
        assert callable(enhanced_router_node)
        assert callable(enhanced_local_processing_node)
        assert callable(enhanced_api_processing_node)
        assert callable(enhanced_integration_node)
        assert callable(get_dual_track_stats)
        assert callable(reset_dual_track_stats)
    
    def test_stats_functions(self):
        """Test statistics functions work correctly."""
        from src.models.dual_track.graph_nodes import get_dual_track_stats, reset_dual_track_stats
        
        # Get initial stats
        stats = get_dual_track_stats()
        assert isinstance(stats, dict)
        assert "total_requests" in stats
        
        # Reset should work without error
        reset_dual_track_stats()
        
        # Stats should be reset
        reset_stats = get_dual_track_stats()
        assert reset_stats["total_requests"] == 0