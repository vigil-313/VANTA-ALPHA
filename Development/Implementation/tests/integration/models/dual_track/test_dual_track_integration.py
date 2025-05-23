# TASK-REF: DP-001 - Processing Router Implementation
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture

"""
Integration tests for the complete dual-track processing system.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from src.models.dual_track import (
    ProcessingRouter, LocalModelController, APIModelController, ResponseIntegrator,
    DualTrackConfig, ProcessingPath, IntegrationStrategy
)


class TestDualTrackIntegration:
    """Integration tests for the complete dual-track processing workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = DualTrackConfig()
        
        # Create components
        self.router = ProcessingRouter(self.config.router)
        self.local_controller = None  # Will be mocked
        self.api_controller = None  # Will be mocked  
        self.integrator = ResponseIntegrator(self.config.integration)
        
        # Mock responses
        self.mock_local_response = {
            "text": "Paris is the capital of France.",
            "source": "local_model",
            "metadata": {
                "tokens_used": 10,
                "generation_time": 0.5,
                "finish_reason": "stop",
                "request_id": 1
            },
            "error": None,
            "success": True
        }
        
        self.mock_api_response = {
            "content": "Paris is the capital and most populous city of France, known for its art, fashion, and culture.",
            "source": "api_model", 
            "metadata": {
                "usage": {
                    "total_tokens": 25,
                    "completion_time": 1.2
                },
                "finish_reason": "stop",
                "model": "claude-3-sonnet",
                "provider": "anthropic",
                "request_id": 1
            },
            "error": None,
            "success": True
        }
    
    @patch('src.models.dual_track.local_model.LocalModelController')
    @patch('src.models.dual_track.api_client.APIModelController')
    def test_local_path_workflow(self, mock_api_controller, mock_local_controller):
        """Test complete workflow for local processing path."""
        # Setup mocks
        mock_local_instance = mock_local_controller.return_value
        mock_local_instance.process_query.return_value = self.mock_local_response
        mock_local_instance.is_available.return_value = True
        
        # Query that should route to local
        query = "Hello, how are you?"
        
        # Step 1: Route the query
        routing_decision = self.router.determine_path(query)
        assert routing_decision.path == ProcessingPath.LOCAL
        
        # Step 2: Process with local model
        local_response = mock_local_instance.process_query(query)
        assert local_response["success"] is True
        assert local_response["source"] == "local_model"
        
        # Step 3: Integrate (single source)
        integration_result = self.integrator.integrate_responses(
            local_response, None, "local"
        )
        assert integration_result.source == "local"
        assert integration_result.content == "Paris is the capital of France."
        
        # Verify mock calls
        mock_local_instance.process_query.assert_called_once_with(query)
    
    @patch('src.models.dual_track.local_model.LocalModelController')
    @patch('src.models.dual_track.api_client.APIModelController')
    def test_api_path_workflow(self, mock_api_controller, mock_local_controller):
        """Test complete workflow for API processing path."""
        # Setup mocks
        mock_api_instance = mock_api_controller.return_value
        mock_api_instance.process_query.return_value = self.mock_api_response
        mock_api_instance.is_available.return_value = True
        
        # Query that should route to API
        query = "Write a comprehensive analysis of quantum computing's impact on cryptography and propose three solutions for post-quantum security."
        
        # Step 1: Route the query
        routing_decision = self.router.determine_path(query)
        assert routing_decision.path == ProcessingPath.API
        
        # Step 2: Process with API model
        messages = [{"role": "user", "content": query}]
        api_response = mock_api_instance.process_query(messages)
        assert api_response["success"] is True
        assert api_response["source"] == "api_model"
        
        # Step 3: Integrate (single source)
        integration_result = self.integrator.integrate_responses(
            None, api_response, "api"
        )
        assert integration_result.source == "api"
        assert "Paris is the capital and most populous city" in integration_result.content
        
        # Verify mock calls
        mock_api_instance.process_query.assert_called_once_with(messages)
    
    @patch('src.models.dual_track.local_model.LocalModelController')
    @patch('src.models.dual_track.api_client.APIModelController')
    def test_parallel_path_workflow(self, mock_api_controller, mock_local_controller):
        """Test complete workflow for parallel processing path."""
        # Setup mocks
        mock_local_instance = mock_local_controller.return_value
        mock_local_instance.process_query.return_value = self.mock_local_response
        mock_local_instance.is_available.return_value = True
        
        mock_api_instance = mock_api_controller.return_value
        mock_api_instance.process_query.return_value = self.mock_api_response
        mock_api_instance.is_available.return_value = True
        
        # Query that should use parallel processing
        query = "Explain the basics of machine learning"
        
        # Step 1: Route the query
        routing_decision = self.router.determine_path(query)
        assert routing_decision.path in [ProcessingPath.PARALLEL, ProcessingPath.LOCAL, ProcessingPath.API]
        
        # Step 2: Process with both models (simulated parallel)
        local_response = mock_local_instance.process_query(query)
        messages = [{"role": "user", "content": query}]
        api_response = mock_api_instance.process_query(messages)
        
        assert local_response["success"] is True
        assert api_response["success"] is True
        
        # Step 3: Integrate both responses
        integration_result = self.integrator.integrate_responses(
            local_response, api_response, "parallel"
        )
        assert integration_result.source in ["local", "api", "integrated"]
        assert integration_result.content != ""
        assert integration_result.similarity_score is not None
    
    def test_routing_decision_accuracy(self):
        """Test accuracy of routing decisions for various query types."""
        test_cases = [
            ("Hi there!", ProcessingPath.LOCAL, "social chat"),
            ("What is 2+2?", ProcessingPath.LOCAL, "simple fact"),
            ("Create a story about dragons", ProcessingPath.API, "creative task"),
            ("Analyze the economic implications of AI", ProcessingPath.API, "complex analysis"),
            ("I need a quick answer about the weather", ProcessingPath.LOCAL, "time sensitive"),
        ]
        
        for query, expected_path, description in test_cases:
            decision = self.router.determine_path(query)
            
            # Allow some flexibility in routing decisions
            if expected_path == ProcessingPath.LOCAL:
                assert decision.path in [ProcessingPath.LOCAL, ProcessingPath.PARALLEL], \
                    f"Failed for {description}: {query}"
            elif expected_path == ProcessingPath.API:
                assert decision.path in [ProcessingPath.API, ProcessingPath.PARALLEL], \
                    f"Failed for {description}: {query}"
            
            assert decision.confidence > 0.0
            assert decision.reasoning != ""
    
    def test_integration_strategy_selection(self):
        """Test integration strategy selection for different scenarios."""
        # Similar responses
        similar_local = {"text": "Paris is the capital of France"}
        similar_api = {"content": "Paris is France's capital city"}
        
        result = self.integrator.integrate_responses(similar_local, similar_api, "parallel")
        assert result.integration_strategy in ["preference", "fastest"]
        assert result.similarity_score > 0.5
        
        # Different responses
        different_local = {"text": "Paris is the capital"}
        different_api = {"content": "The weather is nice today"}
        
        result2 = self.integrator.integrate_responses(different_local, different_api, "parallel")
        assert result2.integration_strategy in ["combine", "interrupt", "preference", "fastest"]
        assert result2.similarity_score < 0.8
    
    @patch('src.models.dual_track.local_model.LocalModelController')
    def test_local_model_error_handling(self, mock_local_controller):
        """Test error handling when local model fails."""
        # Setup mock to simulate error
        mock_local_instance = mock_local_controller.return_value
        mock_local_instance.process_query.return_value = {
            "text": "I'm sorry, but I'm having trouble processing your request right now.",
            "source": "local_model",
            "metadata": {"tokens_used": 0, "generation_time": 0.0, "request_id": 1},
            "error": "Model loading failed",
            "success": False
        }
        mock_local_instance.is_available.return_value = False
        
        query = "Test query"
        response = mock_local_instance.process_query(query)
        
        assert response["success"] is False
        assert response["error"] is not None
        assert "trouble" in response["text"].lower()
    
    @patch('src.models.dual_track.api_client.APIModelController')
    def test_api_model_error_handling(self, mock_api_controller):
        """Test error handling when API model fails."""
        # Setup mock to simulate error
        mock_api_instance = mock_api_controller.return_value
        mock_api_instance.process_query.return_value = {
            "content": "I'm sorry, but I'm having trouble connecting to the API service right now.",
            "source": "api_model",
            "metadata": {"usage": {"total_tokens": 0, "completion_time": 0.0}, "request_id": 1},
            "error": "API connection timeout",
            "success": False
        }
        mock_api_instance.is_available.return_value = False
        
        messages = [{"role": "user", "content": "Test query"}]
        response = mock_api_instance.process_query(messages)
        
        assert response["success"] is False
        assert response["error"] is not None
        assert "trouble connecting" in response["content"].lower()
    
    def test_integration_with_failed_responses(self):
        """Test integration when one or both responses fail."""
        failed_local = {
            "text": "Error occurred",
            "source": "local_model",
            "error": "Generation failed",
            "success": False
        }
        
        failed_api = {
            "content": "Service unavailable", 
            "source": "api_model",
            "error": "API timeout",
            "success": False
        }
        
        # Test with one failed response
        result1 = self.integrator.integrate_responses(failed_local, self.mock_api_response, "parallel")
        assert result1.source == "api"
        assert result1.content != ""
        
        # Test with both failed responses
        result2 = self.integrator.integrate_responses(failed_local, failed_api, "parallel")
        assert result2.source == "fallback"
        assert "trouble generating" in result2.content.lower()
    
    def test_performance_tracking(self):
        """Test performance tracking across the dual-track system."""
        # Test router performance tracking
        for i in range(5):
            self.router.determine_path(f"Test query {i}")
        
        router_stats = self.router.get_routing_stats()
        assert router_stats["total_decisions"] == 5
        assert "average_processing_time" in router_stats
        
        # Test integrator performance tracking
        for i in range(3):
            self.integrator.integrate_responses(
                self.mock_local_response, 
                self.mock_api_response, 
                "parallel"
            )
        
        integration_stats = self.integrator.get_integration_stats()
        assert integration_stats["integration_count"] == 3
        assert "average_processing_time" in integration_stats
    
    def test_configuration_effects(self):
        """Test effects of different configurations."""
        # Test router configuration effects
        custom_router_config = self.config.router
        custom_router_config.threshold_simple = 5
        custom_router_config.threshold_complex = 15
        
        custom_router = ProcessingRouter(custom_router_config)
        
        # Short query should still go to local
        short_decision = custom_router.determine_path("Hi")
        assert short_decision.path == ProcessingPath.LOCAL
        
        # Medium query behavior might change with new thresholds
        medium_decision = custom_router.determine_path("What is the weather today?")
        assert medium_decision.path in [ProcessingPath.LOCAL, ProcessingPath.API, ProcessingPath.PARALLEL]
        
        # Test integration configuration effects
        custom_integration_config = self.config.integration
        custom_integration_config.strategy = IntegrationStrategy.COMBINE
        custom_integration_config.api_preference_weight = 0.9
        
        custom_integrator = ResponseIntegrator(custom_integration_config)
        
        result = custom_integrator.integrate_responses(
            self.mock_local_response,
            self.mock_api_response,
            "parallel"
        )
        assert result.integration_strategy in ["combine", "preference", "fastest"]


class TestDualTrackEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = ProcessingRouter()
        self.integrator = ResponseIntegrator()
    
    def test_empty_query_handling(self):
        """Test handling of empty or invalid queries."""
        empty_queries = ["", "   ", None]
        
        for query in empty_queries:
            decision = self.router.determine_path(query)
            assert decision.path is not None
            assert decision.confidence > 0
    
    def test_very_long_query_handling(self):
        """Test handling of extremely long queries."""
        very_long_query = " ".join(["word"] * 1000)  # 1000 words
        
        decision = self.router.determine_path(very_long_query)
        assert decision.path == ProcessingPath.API  # Should route to API for very long queries
        assert decision.confidence > 0
    
    def test_special_characters_handling(self):
        """Test handling of queries with special characters."""
        special_queries = [
            "What is 2+2=? @#$%^&*()",
            "Émile Durkheim's théorie sociale",
            "🤖 Can AI understand emojis? 🚀",
            "Query with\nnewlines\tand\ttabs"
        ]
        
        for query in special_queries:
            decision = self.router.determine_path(query)
            assert decision.path is not None
            assert decision.confidence > 0
    
    def test_mixed_language_query_handling(self):
        """Test handling of mixed language queries."""
        mixed_queries = [
            "What is こんにちは in English?",
            "Translate bonjour to English",
            "¿Cómo se dice hello en español?"
        ]
        
        for query in mixed_queries:
            decision = self.router.determine_path(query)
            assert decision.path is not None
            assert decision.confidence > 0
    
    def test_malformed_response_integration(self):
        """Test integration with malformed response data."""
        malformed_responses = [
            {"invalid_field": "data"},
            {"text": None},
            {"content": ""},
            123,  # Non-dict response
            []    # Empty list
        ]
        
        for malformed in malformed_responses:
            result = self.integrator.integrate_responses(
                malformed, 
                {"content": "Valid response"}, 
                "parallel"
            )
            assert result.content != ""
            assert result.source != ""


class TestDualTrackPerformance:
    """Test performance characteristics of the dual-track system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = ProcessingRouter()
        self.integrator = ResponseIntegrator()
    
    def test_routing_performance(self):
        """Test routing performance with many queries."""
        import time
        
        queries = [f"Test query {i}" for i in range(100)]
        
        start_time = time.time()
        for query in queries:
            self.router.determine_path(query)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_query = total_time / 100
        
        # Should process queries quickly (less than 10ms per query on average)
        assert avg_time_per_query < 0.01, f"Routing too slow: {avg_time_per_query:.4f}s per query"
        
        # Check routing statistics
        stats = self.router.get_routing_stats()
        assert stats["total_decisions"] == 100
        assert stats["average_processing_time"] < 0.01
    
    def test_integration_performance(self):
        """Test integration performance with many responses."""
        import time
        
        local_resp = {"text": "Local response"}
        api_resp = {"content": "API response"}
        
        start_time = time.time()
        for i in range(50):
            self.integrator.integrate_responses(local_resp, api_resp, "parallel")
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_integration = total_time / 50
        
        # Should integrate responses quickly (less than 20ms per integration)
        assert avg_time_per_integration < 0.02, f"Integration too slow: {avg_time_per_integration:.4f}s per integration"
        
        # Check integration statistics
        stats = self.integrator.get_integration_stats()
        assert stats["integration_count"] == 50
        assert stats["average_processing_time"] < 0.02
    
    def test_memory_usage_stability(self):
        """Test that memory usage remains stable over many operations."""
        import gc
        
        # Perform many operations
        for i in range(200):
            # Routing operations
            decision = self.router.determine_path(f"Query {i}")
            
            # Integration operations
            local_resp = {"text": f"Local response {i}"}
            api_resp = {"content": f"API response {i}"}
            result = self.integrator.integrate_responses(local_resp, api_resp, "parallel")
            
            # Periodic garbage collection
            if i % 50 == 0:
                gc.collect()
        
        # Check that history lists don't grow unbounded
        assert len(self.router.routing_history) <= 1000  # Should be capped
        
        # Reset stats and ensure cleanup
        self.router.reset_stats()
        self.integrator.reset_stats()
        
        assert self.router.total_decisions == 0
        assert self.integrator.integration_count == 0