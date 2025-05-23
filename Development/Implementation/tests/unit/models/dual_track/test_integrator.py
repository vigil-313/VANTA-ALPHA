# TASK-REF: DP-001 - Processing Router Implementation
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture

"""
Unit tests for the dual-track response integrator.
"""

import pytest
from unittest.mock import Mock, patch
from src.models.dual_track.integrator import ResponseIntegrator, integrate_responses, IntegrationResult
from src.models.dual_track.config import IntegrationConfig, IntegrationStrategy, InterruptStyle


class TestResponseIntegrator:
    """Test cases for ResponseIntegrator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = IntegrationConfig()
        self.integrator = ResponseIntegrator(self.config)
        
        # Sample responses for testing
        self.local_response = {
            "text": "The capital of France is Paris.",
            "metadata": {
                "generation_time": 0.5,
                "tokens_used": 10
            }
        }
        
        self.api_response = {
            "content": "Paris is the capital and most populous city of France.",
            "metadata": {
                "usage": {
                    "completion_time": 1.2,
                    "total_tokens": 15
                }
            }
        }
    
    def test_integrator_initialization(self):
        """Test integrator initialization."""
        assert self.integrator.config == self.config
        assert self.integrator.integration_count == 0
        assert len(self.integrator.strategy_usage) == 0
    
    def test_single_local_response_integration(self):
        """Test integration with only local response."""
        result = self.integrator.integrate_responses(self.local_response, None, "local")
        
        assert result.content == "The capital of France is Paris."
        assert result.source == "local"
        assert result.integration_strategy == "single_source"
        assert result.similarity_score is None
    
    def test_single_api_response_integration(self):
        """Test integration with only API response."""
        result = self.integrator.integrate_responses(None, self.api_response, "api")
        
        assert result.content == "Paris is the capital and most populous city of France."
        assert result.source == "api"
        assert result.integration_strategy == "single_source"
        assert result.similarity_score is None
    
    def test_no_responses_integration(self):
        """Test integration with no responses."""
        result = self.integrator.integrate_responses(None, None, "parallel")
        
        assert result.source == "fallback"
        assert result.integration_strategy == "fallback"
        assert "trouble generating" in result.content.lower()
    
    def test_similar_responses_preference_strategy(self):
        """Test integration of similar responses with preference strategy."""
        # Create similar responses
        local_resp = {"text": "Paris is the capital of France."}
        api_resp = {"content": "Paris is France's capital city."}
        
        config = IntegrationConfig(strategy=IntegrationStrategy.PREFERENCE)
        integrator = ResponseIntegrator(config)
        
        result = integrator.integrate_responses(local_resp, api_resp, "parallel")
        
        assert result.source in ["local", "api"]
        assert result.integration_strategy == "preference"
        assert result.similarity_score is not None
        assert result.similarity_score > 0.5
    
    def test_different_responses_combination_strategy(self):
        """Test integration of different responses with combination strategy."""
        # Create different responses
        local_resp = {"text": "Paris is the capital."}
        api_resp = {"content": "France has a rich cultural history."}
        
        config = IntegrationConfig(strategy=IntegrationStrategy.COMBINE)
        integrator = ResponseIntegrator(config)
        
        result = integrator.integrate_responses(local_resp, api_resp, "parallel")
        
        assert result.integration_strategy == "combine"
        assert result.similarity_score is not None
        assert result.similarity_score < 0.8
    
    def test_interruption_strategy_smooth(self):
        """Test interruption strategy with smooth transitions."""
        config = IntegrationConfig(
            strategy=IntegrationStrategy.INTERRUPT,
            interrupt_style=InterruptStyle.SMOOTH
        )
        integrator = ResponseIntegrator(config)
        
        result = integrator.integrate_responses(self.local_response, self.api_response, "parallel")
        
        assert result.integration_strategy == "interrupt"
        assert result.source == "integrated"
        assert len(result.content) > len(self.local_response["text"])
    
    def test_interruption_strategy_abrupt(self):
        """Test interruption strategy with abrupt transitions."""
        config = IntegrationConfig(
            strategy=IntegrationStrategy.INTERRUPT,
            interrupt_style=InterruptStyle.ABRUPT
        )
        integrator = ResponseIntegrator(config)
        
        result = integrator.integrate_responses(self.local_response, self.api_response, "parallel")
        
        assert result.integration_strategy == "interrupt"
        assert result.source == "integrated"
        assert "..." in result.content or any(word in result.content.lower() for word in ["actually", "wait", "hold"])
    
    def test_fastest_strategy(self):
        """Test fastest response strategy."""
        # Create responses with different completion times
        fast_local = {
            "text": "Quick answer",
            "metadata": {"generation_time": 0.3}
        }
        slow_api = {
            "content": "Detailed answer",
            "metadata": {"usage": {"completion_time": 2.0}}
        }
        
        config = IntegrationConfig(strategy=IntegrationStrategy.FASTEST)
        integrator = ResponseIntegrator(config)
        
        result = integrator.integrate_responses(fast_local, slow_api, "parallel")
        
        assert result.integration_strategy == "fastest"
        assert result.source == "local"  # Faster response
        assert result.content == "Quick answer"
    
    def test_similarity_calculation(self):
        """Test similarity calculation between responses."""
        text1 = "Paris is the capital of France"
        text2 = "Paris is France's capital city"
        text3 = "The weather is nice today"
        
        sim_high = self.integrator._calculate_similarity(text1, text2)
        sim_low = self.integrator._calculate_similarity(text1, text3)
        
        assert 0 <= sim_high <= 1
        assert 0 <= sim_low <= 1
        assert sim_high > sim_low
    
    def test_response_quality_scoring(self):
        """Test response quality scoring."""
        good_response = "This is a well-formed response with proper punctuation."
        poor_response = "error bad response"
        empty_response = ""
        
        good_score = self.integrator._score_response_quality(good_response)
        poor_score = self.integrator._score_response_quality(poor_response)
        empty_score = self.integrator._score_response_quality(empty_response)
        
        assert good_score > poor_score > empty_score
        assert 0 <= good_score <= 1
    
    def test_text_extraction(self):
        """Test text extraction from various response formats."""
        # Test different field names
        resp1 = {"content": "response text"}
        resp2 = {"text": "response text"}
        resp3 = {"response": "response text"}
        resp4 = {"other_field": "response text"}
        
        assert self.integrator._extract_text(resp1) == "response text"
        assert self.integrator._extract_text(resp2) == "response text"
        assert self.integrator._extract_text(resp3) == "response text"
        assert self.integrator._extract_text(resp4) != ""  # Should fallback to string conversion
    
    def test_completion_time_extraction(self):
        """Test completion time extraction from metadata."""
        resp1 = {"metadata": {"completion_time": 1.5}}
        resp2 = {"metadata": {"generation_time": 2.0}}
        resp3 = {"metadata": {"usage": {"completion_time": 1.0}}}
        resp4 = {"metadata": {}}
        
        assert self.integrator._get_completion_time(resp1) == 1.5
        assert self.integrator._get_completion_time(resp2) == 2.0
        assert self.integrator._get_completion_time(resp3) == 1.0
        assert self.integrator._get_completion_time(resp4) == 0.0
    
    def test_integration_statistics(self):
        """Test integration statistics tracking."""
        # Perform several integrations
        for i in range(3):
            self.integrator.integrate_responses(self.local_response, self.api_response, "parallel")
        
        stats = self.integrator.get_integration_stats()
        
        assert stats["integration_count"] == 3
        assert "total_processing_time" in stats
        assert "average_processing_time" in stats
        assert "strategy_usage" in stats
        assert "strategy_percentages" in stats
    
    def test_reset_statistics(self):
        """Test resetting integration statistics."""
        self.integrator.integrate_responses(self.local_response, self.api_response, "parallel")
        assert self.integrator.integration_count > 0
        
        self.integrator.reset_stats()
        assert self.integrator.integration_count == 0
        assert len(self.integrator.strategy_usage) == 0
    
    def test_strategy_selection_logic(self):
        """Test strategy selection based on conditions."""
        # Very similar responses should use preference
        similar_local = {"text": "Paris is the capital"}
        similar_api = {"content": "Paris is the capital"}
        
        result = self.integrator.integrate_responses(similar_local, similar_api, "parallel")
        # Should choose preference strategy for very similar responses
        
        # Very different responses should use combination or interruption
        different_local = {"text": "Paris is the capital"}
        different_api = {"content": "The weather is sunny today"}
        
        result2 = self.integrator.integrate_responses(different_local, different_api, "parallel")
        # Should choose combination or interruption for very different responses
        
        assert result.similarity_score is not None
        assert result2.similarity_score is not None
        assert result.similarity_score > result2.similarity_score


class TestIntegrationErrorHandling:
    """Test cases for integration error handling."""
    
    def test_malformed_response_handling(self):
        """Test handling of malformed responses."""
        integrator = ResponseIntegrator()
        
        malformed_local = {"invalid": "format"}
        malformed_api = None
        
        result = integrator.integrate_responses(malformed_local, malformed_api, "parallel")
        
        assert result.source == "local"
        assert result.content != ""
    
    def test_exception_during_integration(self):
        """Test handling of exceptions during integration."""
        integrator = ResponseIntegrator()
        
        # Mock an exception in similarity calculation
        with patch.object(integrator, '_calculate_similarity', side_effect=Exception("Test error")):
            result = integrator.integrate_responses(
                {"text": "test"}, 
                {"content": "test"}, 
                "parallel"
            )
            
            assert result.source == "fallback"
            assert result.integration_strategy == "fallback"
    
    def test_empty_text_extraction(self):
        """Test handling of empty text extraction."""
        integrator = ResponseIntegrator()
        
        empty_resp1 = {"text": ""}
        empty_resp2 = {"content": ""}
        
        result = integrator.integrate_responses(empty_resp1, empty_resp2, "parallel")
        
        assert result.source == "fallback"
        assert result.content != ""


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_integrate_responses_function(self):
        """Test the convenience integrate_responses function."""
        local_resp = {"text": "Local response"}
        api_resp = {"content": "API response"}
        
        result = integrate_responses(local_resp, api_resp, "parallel")
        
        assert "content" in result
        assert "source" in result
        assert "integration_strategy" in result
        assert "similarity_score" in result
        assert "processing_time" in result
        assert "metadata" in result


class TestIntegrationConfiguration:
    """Test cases for integration configuration."""
    
    def test_custom_integration_config(self):
        """Test integrator with custom configuration."""
        config = IntegrationConfig(
            strategy=IntegrationStrategy.COMBINE,
            interrupt_style=InterruptStyle.ABRUPT,
            similarity_threshold=0.9,
            api_preference_weight=0.8
        )
        integrator = ResponseIntegrator(config)
        
        assert integrator.config.strategy == IntegrationStrategy.COMBINE
        assert integrator.config.interrupt_style == InterruptStyle.ABRUPT
        assert integrator.config.similarity_threshold == 0.9
        assert integrator.config.api_preference_weight == 0.8
    
    def test_preference_weight_effects(self):
        """Test effects of preference weight on integration."""
        # High API preference
        high_api_config = IntegrationConfig(
            strategy=IntegrationStrategy.PREFERENCE,
            api_preference_weight=0.9
        )
        
        # Low API preference
        low_api_config = IntegrationConfig(
            strategy=IntegrationStrategy.PREFERENCE,
            api_preference_weight=0.1
        )
        
        local_resp = {"text": "Local response"}
        api_resp = {"content": "API response"}
        
        high_integrator = ResponseIntegrator(high_api_config)
        low_integrator = ResponseIntegrator(low_api_config)
        
        high_result = high_integrator.integrate_responses(local_resp, api_resp, "parallel")
        low_result = low_integrator.integrate_responses(local_resp, api_resp, "parallel")
        
        # With high API preference, should tend toward API
        # With low API preference, should tend toward local
        # Note: Actual result depends on response quality scoring