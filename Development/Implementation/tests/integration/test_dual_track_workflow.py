# TASK-REF: DP-002 - Dual-Track Response Integration System
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture
# DOC-REF: DOC-DEV-ARCH-COMP-2 - Dual-Track Processing Component Specification

"""
End-to-end integration tests for the complete dual-track processing workflow.

Tests the full workflow from query analysis through response integration,
ensuring all components work together seamlessly.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from langchain_core.messages import HumanMessage, AIMessage

from src.models.dual_track.graph_nodes import DualTrackGraphNodes
from src.models.dual_track.config import DEFAULT_CONFIG, IntegrationStrategy
from src.langgraph.nodes.processing_nodes import (
    router_node, 
    local_model_node, 
    api_model_node, 
    integration_node
)


class TestDualTrackWorkflow:
    """Test suite for end-to-end dual-track processing workflow."""
    
    @pytest.fixture
    def sample_state(self):
        """Create sample VANTA state for workflow testing."""
        return {
            "messages": [
                HumanMessage(content="What are the benefits of renewable energy?")
            ],
            "memory": {
                "retrieved_context": {
                    "conversation_context": [],
                    "semantic_context": ["Environmental sustainability", "Energy efficiency"]
                },
                "conversation_history": [
                    {"user_message": "Tell me about energy", "ai_message": "Energy is essential for modern life"}
                ],
                "user_preferences": {"response_style": "balanced"}
            },
            "activation": {
                "status": "processing"
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
    
    def test_local_only_workflow(self, sample_state):
        """Test complete workflow for local-only processing."""
        # Mock routing to local only
        with patch('src.models.dual_track.graph_nodes.ProcessingRouter') as mock_router_class:
            mock_router = Mock()
            mock_router_class.return_value = mock_router
            mock_router.determine_path.return_value = Mock(
                path="local",
                confidence=0.9,
                reasoning="Simple question suitable for local processing",
                features={"complexity": 0.3, "time_sensitivity": 0.8},
                estimated_local_time=0.8,
                estimated_api_time=2.0
            )
            
            # Mock local model response
            with patch('src.models.dual_track.graph_nodes.LocalModelController') as mock_local_class:
                mock_local = Mock()
                mock_local_class.return_value = mock_local
                mock_local.generate.return_value = {
                    "content": "Renewable energy offers environmental benefits and cost savings.",
                    "generation_time": 0.7,
                    "tokens_generated": 45,
                    "finish_reason": "completed"
                }
                
                # Mock integrator
                with patch('src.models.dual_track.graph_nodes.ResponseIntegrator') as mock_integrator_class:
                    mock_integrator = Mock()
                    mock_integrator_class.return_value = mock_integrator
                    mock_integrator.integrate_responses.return_value = Mock(
                        content="Renewable energy offers environmental benefits and cost savings.",
                        source="local",
                        integration_strategy="single_source",
                        similarity_score=None,
                        processing_time=0.1,
                        metadata={"reason": "Only local response available"}
                    )
                    
                    # Execute workflow
                    # Step 1: Routing
                    routing_result = router_node(sample_state)
                    assert routing_result["processing"]["path"] == "local"
                    sample_state.update(routing_result)
                    
                    # Step 2: Local processing
                    local_result = local_model_node(sample_state)
                    assert local_result["processing"]["local_completed"] == True
                    sample_state["processing"].update(local_result["processing"])
                    
                    # Step 3: API processing (should be skipped)
                    api_result = api_model_node(sample_state)
                    assert api_result == {}  # Should skip
                    
                    # Step 4: Integration
                    integration_result = integration_node(sample_state)
                    assert len(integration_result["messages"]) == 1
                    assert isinstance(integration_result["messages"][0], AIMessage)
                    assert "environmental benefits" in integration_result["messages"][0].content
                    assert integration_result["activation"]["status"] == "speaking"
                    
    def test_api_only_workflow(self, sample_state):
        """Test complete workflow for API-only processing."""
        # Set complex query that requires API processing
        sample_state["messages"] = [
            HumanMessage(content="Analyze the geopolitical implications of the transition to renewable energy in developing nations.")
        ]
        
        with patch('src.models.dual_track.graph_nodes.ProcessingRouter') as mock_router_class:
            mock_router = Mock()
            mock_router_class.return_value = mock_router
            mock_router.determine_path.return_value = Mock(
                path="api",
                confidence=0.85,
                reasoning="Complex analytical question requiring deep knowledge",
                features={"complexity": 0.9, "creativity": 0.8},
                estimated_local_time=2.0,
                estimated_api_time=3.0
            )
            
            # Mock API model response
            with patch('src.models.dual_track.graph_nodes.APIModelController') as mock_api_class:
                mock_api = Mock()
                mock_api_class.return_value = mock_api
                mock_api.generate.return_value = {
                    "content": "The transition to renewable energy in developing nations involves complex geopolitical considerations including energy security, international partnerships, and economic development strategies...",
                    "usage": {"total_tokens": 250, "completion_time": 2.8},
                    "finish_reason": "completed"
                }
                
                with patch('src.models.dual_track.graph_nodes.ResponseIntegrator') as mock_integrator_class:
                    mock_integrator = Mock()
                    mock_integrator_class.return_value = mock_integrator
                    mock_integrator.integrate_responses.return_value = Mock(
                        content="The transition to renewable energy in developing nations involves complex geopolitical considerations...",
                        source="api",
                        integration_strategy="single_source",
                        similarity_score=None,
                        processing_time=0.1,
                        metadata={"reason": "Only API response available"}
                    )
                    
                    # Execute workflow
                    routing_result = router_node(sample_state)
                    assert routing_result["processing"]["path"] == "api"
                    sample_state.update(routing_result)
                    
                    # Local processing should be skipped
                    local_result = local_model_node(sample_state)
                    assert local_result == {}
                    
                    # API processing
                    api_result = api_model_node(sample_state)
                    assert api_result["processing"]["api_completed"] == True
                    sample_state["processing"].update(api_result["processing"])
                    
                    # Integration
                    integration_result = integration_node(sample_state)
                    assert "geopolitical considerations" in integration_result["messages"][0].content
                    
    def test_parallel_processing_workflow(self, sample_state):
        """Test complete workflow for parallel processing with both models."""
        with patch('src.models.dual_track.graph_nodes.ProcessingRouter') as mock_router_class:
            mock_router = Mock()
            mock_router_class.return_value = mock_router
            mock_router.determine_path.return_value = Mock(
                path="parallel",
                confidence=0.75,
                reasoning="Balanced question benefiting from both speed and depth",
                features={"complexity": 0.6, "time_sensitivity": 0.7},
                estimated_local_time=1.0,
                estimated_api_time=2.5
            )
            
            # Mock both model responses
            with patch('src.models.dual_track.graph_nodes.LocalModelController') as mock_local_class:
                with patch('src.models.dual_track.graph_nodes.APIModelController') as mock_api_class:
                    mock_local = Mock()
                    mock_local_class.return_value = mock_local
                    mock_local.generate.return_value = {
                        "content": "Renewable energy reduces carbon emissions.",
                        "generation_time": 0.9,
                        "tokens_generated": 25,
                        "finish_reason": "completed"
                    }
                    
                    mock_api = Mock()
                    mock_api_class.return_value = mock_api
                    mock_api.generate.return_value = {
                        "content": "Renewable energy provides comprehensive environmental and economic advantages including reduced greenhouse gas emissions, energy independence, job creation, and long-term cost savings.",
                        "usage": {"total_tokens": 180, "completion_time": 2.3},
                        "finish_reason": "completed"
                    }
                    
                    with patch('src.models.dual_track.graph_nodes.ResponseIntegrator') as mock_integrator_class:
                        mock_integrator = Mock()
                        mock_integrator_class.return_value = mock_integrator
                        mock_integrator.integrate_responses.return_value = Mock(
                            content="Renewable energy reduces carbon emissions. To give you a more complete answer, renewable energy provides comprehensive environmental and economic advantages including reduced greenhouse gas emissions, energy independence, job creation, and long-term cost savings.",
                            source="integrated",
                            integration_strategy="combine",
                            similarity_score=0.6,
                            processing_time=0.2,
                            metadata={"reason": "Combined different responses"}
                        )
                        
                        # Execute parallel workflow
                        routing_result = router_node(sample_state)
                        assert routing_result["processing"]["path"] == "parallel"
                        sample_state.update(routing_result)
                        
                        # Both processing paths should execute
                        local_result = local_model_node(sample_state)
                        assert local_result["processing"]["local_completed"] == True
                        sample_state["processing"].update(local_result["processing"])
                        
                        api_result = api_model_node(sample_state)
                        assert api_result["processing"]["api_completed"] == True
                        sample_state["processing"].update(api_result["processing"])
                        
                        # Integration should combine responses
                        integration_result = integration_node(sample_state)
                        content = integration_result["messages"][0].content
                        assert "carbon emissions" in content
                        assert "comprehensive environmental" in content
                        assert integration_result["processing"]["integration_result"]["source"] == "integrated"
                        
    def test_staged_processing_workflow_sufficient_local(self, sample_state):
        """Test staged processing workflow where local response is sufficient."""
        with patch('src.models.dual_track.graph_nodes.ProcessingRouter') as mock_router_class:
            mock_router = Mock()
            mock_router_class.return_value = mock_router
            mock_router.determine_path.return_value = Mock(
                path="staged",
                confidence=0.7,
                reasoning="Try local first, API if needed",
                features={"complexity": 0.5, "time_sensitivity": 0.8},
                estimated_local_time=1.0,
                estimated_api_time=2.0
            )
            
            with patch('src.models.dual_track.graph_nodes.LocalModelController') as mock_local_class:
                mock_local = Mock()
                mock_local_class.return_value = mock_local
                mock_local.generate.return_value = {
                    "content": "Renewable energy offers significant environmental benefits including reduced carbon footprint, cleaner air, and sustainable resource utilization. It also provides economic advantages through job creation and energy independence.",
                    "generation_time": 0.8,
                    "tokens_generated": 120,
                    "finish_reason": "completed"
                }
                
                with patch('src.models.dual_track.graph_nodes.ResponseIntegrator') as mock_integrator_class:
                    mock_integrator = Mock()
                    mock_integrator_class.return_value = mock_integrator
                    mock_integrator.integrate_responses.return_value = Mock(
                        content="Renewable energy offers significant environmental benefits including reduced carbon footprint, cleaner air, and sustainable resource utilization. It also provides economic advantages through job creation and energy independence.",
                        source="local",
                        integration_strategy="single_source",
                        similarity_score=None,
                        processing_time=0.1,
                        metadata={"reason": "Only local response available"}
                    )
                    
                    # Execute staged workflow
                    routing_result = router_node(sample_state)
                    sample_state.update(routing_result)
                    
                    # Local processing
                    local_result = local_model_node(sample_state)
                    sample_state["processing"].update(local_result["processing"])
                    
                    # API processing should be skipped (local is sufficient)
                    api_result = api_model_node(sample_state)
                    assert api_result == {}  # Should skip due to sufficient local response
                    
                    # Integration with only local response
                    integration_result = integration_node(sample_state)
                    assert "environmental benefits" in integration_result["messages"][0].content
                    assert "economic advantages" in integration_result["messages"][0].content
                    
    def test_workflow_error_recovery(self, sample_state):
        """Test workflow error recovery and fallback mechanisms."""
        with patch('src.models.dual_track.graph_nodes.ProcessingRouter') as mock_router_class:
            mock_router = Mock()
            mock_router_class.return_value = mock_router
            mock_router.determine_path.return_value = Mock(
                path="parallel",
                confidence=0.8,
                reasoning="Both models for comprehensive response",
                features={"complexity": 0.7},
                estimated_local_time=1.0,
                estimated_api_time=2.0
            )
            
            # Mock local model failure
            with patch('src.models.dual_track.graph_nodes.LocalModelController') as mock_local_class:
                mock_local = Mock()
                mock_local_class.return_value = mock_local
                mock_local.generate.side_effect = Exception("Local model timeout")
                
                # Mock successful API response
                with patch('src.models.dual_track.graph_nodes.APIModelController') as mock_api_class:
                    mock_api = Mock()
                    mock_api_class.return_value = mock_api
                    mock_api.generate.return_value = {
                        "content": "Renewable energy is essential for environmental sustainability and economic growth.",
                        "usage": {"total_tokens": 120, "completion_time": 2.1},
                        "finish_reason": "completed"
                    }
                    
                    with patch('src.models.dual_track.graph_nodes.ResponseIntegrator') as mock_integrator_class:
                        mock_integrator = Mock()
                        mock_integrator_class.return_value = mock_integrator
                        mock_integrator.integrate_responses.return_value = Mock(
                            content="Renewable energy is essential for environmental sustainability and economic growth.",
                            source="api",
                            integration_strategy="single_source",
                            similarity_score=None,
                            processing_time=0.1,
                            metadata={"reason": "Local model failed, using API response"}
                        )
                        
                        # Execute workflow with error recovery
                        routing_result = router_node(sample_state)
                        sample_state.update(routing_result)
                        
                        # Local processing fails but continues
                        local_result = local_model_node(sample_state)
                        assert local_result["processing"]["local_completed"] == True  # Marked as completed
                        assert local_result["processing"]["local_error"] is not None
                        sample_state["processing"].update(local_result["processing"])
                        
                        # API processing succeeds
                        api_result = api_model_node(sample_state)
                        assert api_result["processing"]["api_completed"] == True
                        sample_state["processing"].update(api_result["processing"])
                        
                        # Integration handles partial failure gracefully
                        integration_result = integration_node(sample_state)
                        assert "environmental sustainability" in integration_result["messages"][0].content
                        
    def test_workflow_performance_tracking(self, sample_state):
        """Test that workflow properly tracks performance metrics."""
        with patch('src.models.dual_track.graph_nodes.DualTrackGraphNodes') as mock_nodes_class:
            mock_nodes = Mock()
            mock_nodes_class.return_value = mock_nodes
            
            # Mock successful routing
            mock_nodes.enhanced_router_node.return_value = {
                "processing": {
                    "path": "local",
                    "confidence": 0.8,
                    "reasoning": "Simple query",
                    "routing_time": 0.1
                }
            }
            
            # Mock successful local processing
            mock_nodes.enhanced_local_processing_node.return_value = {
                "processing": {
                    "local_completed": True,
                    "local_response": {"content": "Test response"},
                    "local_processing_time": 0.7
                }
            }
            
            # Mock successful integration
            mock_nodes.enhanced_integration_node.return_value = {
                "messages": [AIMessage(content="Test response")],
                "activation": {"status": "speaking"},
                "processing": {
                    "integration_time": 0.1,
                    "total_processing_time": 0.9
                }
            }
            
            # Verify stats tracking is called
            with patch('src.models.dual_track.graph_nodes.get_dual_track_stats') as mock_stats:
                mock_stats.return_value = {
                    "total_requests": 1,
                    "successful_integrations": 1,
                    "average_processing_time": 0.9,
                    "path_usage": {"local": 1, "api": 0, "parallel": 0, "staged": 0}
                }
                
                # Execute workflow
                router_node(sample_state)
                local_model_node(sample_state)
                integration_node(sample_state)
                
                # Verify tracking was called through the module functions
                assert mock_nodes.enhanced_router_node.called
                assert mock_nodes.enhanced_local_processing_node.called
                assert mock_nodes.enhanced_integration_node.called
    
    def test_workflow_state_consistency(self, sample_state):
        """Test that state remains consistent throughout the workflow."""
        initial_messages = sample_state["messages"].copy()
        initial_memory = sample_state["memory"].copy()
        
        with patch('src.models.dual_track.graph_nodes.ProcessingRouter') as mock_router_class:
            mock_router = Mock()
            mock_router_class.return_value = mock_router
            mock_router.determine_path.return_value = Mock(
                path="local",
                confidence=0.8,
                reasoning="Test routing",
                features={},
                estimated_local_time=1.0,
                estimated_api_time=2.0
            )
            
            with patch('src.models.dual_track.graph_nodes.LocalModelController') as mock_local_class:
                mock_local = Mock()
                mock_local_class.return_value = mock_local
                mock_local.generate.return_value = {
                    "content": "Test response",
                    "generation_time": 0.5
                }
                
                with patch('src.models.dual_track.graph_nodes.ResponseIntegrator') as mock_integrator_class:
                    mock_integrator = Mock()
                    mock_integrator_class.return_value = mock_integrator
                    mock_integrator.integrate_responses.return_value = Mock(
                        content="Test response",
                        source="local",
                        integration_strategy="single_source",
                        similarity_score=None,
                        processing_time=0.1,
                        metadata={}
                    )
                    
                    # Execute complete workflow
                    routing_result = router_node(sample_state)
                    sample_state.update(routing_result)
                    
                    local_result = local_model_node(sample_state)
                    sample_state["processing"].update(local_result["processing"])
                    
                    api_result = api_model_node(sample_state)
                    # API should be skipped, so state shouldn't change
                    
                    integration_result = integration_node(sample_state)
                    
                    # Verify state consistency
                    # Original messages should be preserved
                    assert sample_state["messages"][0] == initial_messages[0]
                    
                    # Memory should be preserved
                    assert sample_state["memory"] == initial_memory
                    
                    # New AI message should be added
                    assert len(integration_result["messages"]) == 1
                    assert isinstance(integration_result["messages"][0], AIMessage)
                    
                    # Processing metadata should be complete
                    assert "processing" in sample_state
                    assert sample_state["processing"]["path"] == "local"
                    assert sample_state["processing"]["local_completed"] == True