# TASK-REF: DP-001 - Processing Router Implementation
# CONCEPT-REF: CON-VANTA-010 - Dual-Track Processing Architecture

"""
Unit tests for the dual-track processing router.
"""

import pytest
from unittest.mock import Mock, patch
from src.models.dual_track.router import ProcessingRouter, determine_path, calculate_query_features
from src.models.dual_track.config import RouterConfig, ProcessingPath


class TestProcessingRouter:
    """Test cases for ProcessingRouter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = RouterConfig()
        self.router = ProcessingRouter(self.config)
    
    def test_router_initialization(self):
        """Test router initialization."""
        assert self.router.config == self.config
        assert self.router.total_decisions == 0
        assert len(self.router.routing_history) == 0
    
    def test_social_chat_routing(self):
        """Test routing for social chat queries."""
        query = "Hello, how are you?"
        decision = self.router.determine_path(query)
        
        assert decision.path == ProcessingPath.LOCAL
        assert decision.confidence >= 0.8
        assert "social interaction" in decision.reasoning.lower()
    
    def test_simple_factual_routing(self):
        """Test routing for simple factual queries."""
        query = "What is the capital of France?"
        decision = self.router.determine_path(query)
        
        assert decision.path == ProcessingPath.LOCAL
        assert decision.confidence >= 0.7
        assert "fact" in decision.reasoning.lower()
    
    def test_complex_reasoning_routing(self):
        """Test routing for complex reasoning queries."""
        query = "Analyze the economic implications of climate change on developing nations and propose three policy solutions."
        decision = self.router.determine_path(query)
        
        assert decision.path == ProcessingPath.API
        assert decision.confidence >= 0.8
        assert "reasoning" in decision.reasoning.lower() or "creativity" in decision.reasoning.lower()
    
    def test_creative_task_routing(self):
        """Test routing for creative tasks."""
        query = "Write a short story about a robot learning to paint."
        decision = self.router.determine_path(query)
        
        assert decision.path == ProcessingPath.API
        assert decision.confidence >= 0.8
        assert "creativity" in decision.reasoning.lower()
    
    def test_long_query_routing(self):
        """Test routing for very long queries."""
        query = " ".join(["word"] * 60)  # 60-word query
        decision = self.router.determine_path(query)
        
        assert decision.path == ProcessingPath.API
        assert "long" in decision.reasoning.lower() or "complex" in decision.reasoning.lower()
    
    def test_time_sensitive_routing(self):
        """Test routing for time-sensitive queries."""
        query = "I need an answer quickly about the meeting location"
        decision = self.router.determine_path(query)
        
        assert decision.path == ProcessingPath.LOCAL
        assert "time-sensitive" in decision.reasoning.lower() or "fast" in decision.reasoning.lower()
    
    def test_context_dependent_routing(self):
        """Test routing with high context dependency."""
        query = "What did they decide about that issue we discussed?"
        context = {"previous_conversation": "lots of context"}
        decision = self.router.determine_path(query, context)
        
        # Context-dependent queries should go to API
        assert decision.path == ProcessingPath.API
        assert decision.confidence > 0.0
    
    def test_moderate_complexity_parallel_routing(self):
        """Test routing for moderate complexity queries."""
        query = "Explain how photosynthesis works in plants"
        decision = self.router.determine_path(query)
        
        # Should use parallel processing for moderate complexity
        assert decision.path in [ProcessingPath.PARALLEL, ProcessingPath.LOCAL, ProcessingPath.API]
        assert decision.confidence > 0.0
    
    def test_routing_statistics(self):
        """Test routing statistics tracking."""
        queries = [
            "Hi there!",
            "What is 2+2?", 
            "Write a complex analysis of quantum mechanics"
        ]
        
        for query in queries:
            self.router.determine_path(query)
        
        stats = self.router.get_routing_stats()
        assert stats["total_decisions"] == 3
        assert stats["recent_decisions"] == 3
        assert "path_distribution" in stats
        assert "average_processing_time" in stats
        assert "average_confidence" in stats
    
    def test_reset_statistics(self):
        """Test resetting routing statistics."""
        self.router.determine_path("test query")
        assert self.router.total_decisions > 0
        
        self.router.reset_stats()
        assert self.router.total_decisions == 0
        assert len(self.router.routing_history) == 0


class TestQueryFeatures:
    """Test cases for query feature extraction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = ProcessingRouter()
    
    def test_token_count_extraction(self):
        """Test token count calculation."""
        query = "This is a test query with seven tokens"
        features = self.router.calculate_query_features(query)
        
        assert features.token_count == 8  # "This is a test query with seven tokens"
    
    def test_entity_extraction(self):
        """Test entity extraction."""
        query = "Barack Obama visited New York City and met with Apple executives"
        features = self.router.calculate_query_features(query)
        
        assert features.entity_count >= 2  # Should find proper nouns
    
    def test_question_word_detection(self):
        """Test question word detection."""
        query = "What is the weather like and how can I check it?"
        features = self.router.calculate_query_features(query)
        
        assert len(features.question_words) >= 2  # "what" and "how"
        assert "what" in features.question_words
        assert "how" in features.question_words
    
    def test_reasoning_step_detection(self):
        """Test reasoning step detection."""
        query = "Given that A is true, and if B follows from A, then what can we conclude?"
        features = self.router.calculate_query_features(query)
        
        assert features.reasoning_steps > 0
    
    def test_time_sensitivity_detection(self):
        """Test time sensitivity detection."""
        query = "I need this urgent information quickly!"
        features = self.router.calculate_query_features(query)
        
        assert features.time_sensitivity > 0
    
    def test_factual_retrieval_detection(self):
        """Test factual retrieval detection."""
        query = "What is the definition of machine learning?"
        features = self.router.calculate_query_features(query)
        
        assert features.factual_retrieval is True
    
    def test_creativity_detection(self):
        """Test creativity requirement detection."""
        query = "Create a story about space exploration"
        features = self.router.calculate_query_features(query)
        
        assert features.creativity_required is True
    
    def test_social_chat_detection(self):
        """Test social chat detection."""
        query = "Hello! Thank you for your help, goodbye!"
        features = self.router.calculate_query_features(query)
        
        assert features.social_chat is True
    
    def test_complexity_score_calculation(self):
        """Test overall complexity score calculation."""
        simple_query = "Hi"
        complex_query = "Analyze the multifaceted socioeconomic implications of artificial intelligence on global labor markets"
        
        simple_features = self.router.calculate_query_features(simple_query)
        complex_features = self.router.calculate_query_features(complex_query)
        
        assert simple_features.complexity_score < complex_features.complexity_score
        assert 0 <= simple_features.complexity_score <= 1
        assert 0 <= complex_features.complexity_score <= 1
    
    def test_context_dependency_calculation(self):
        """Test context dependency calculation."""
        context_heavy_query = "What did they say about that thing we mentioned before?"
        context_light_query = "What is the weather today?"
        
        context_heavy_features = self.router.calculate_query_features(context_heavy_query)
        context_light_features = self.router.calculate_query_features(context_light_query)
        
        assert context_heavy_features.context_dependency > context_light_features.context_dependency


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_determine_path_function(self):
        """Test the convenience determine_path function."""
        query = "What is machine learning?"
        result = determine_path(query)
        
        assert "path" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert result["path"] in ["local", "api", "parallel", "staged"]
    
    def test_calculate_query_features_function(self):
        """Test the convenience calculate_query_features function."""
        query = "How does photosynthesis work?"
        result = calculate_query_features(query)
        
        assert "token_count" in result
        assert "entity_count" in result
        assert "reasoning_steps" in result
        assert "complexity_score" in result
        assert isinstance(result["token_count"], int)
        assert isinstance(result["complexity_score"], float)


class TestRouterErrorHandling:
    """Test cases for router error handling."""
    
    def test_empty_query_handling(self):
        """Test handling of empty queries."""
        router = ProcessingRouter()
        decision = router.determine_path("")
        
        assert decision.path == router.config.default_path
        assert decision.confidence > 0
    
    def test_none_query_handling(self):
        """Test handling of None queries."""
        router = ProcessingRouter()
        decision = router.determine_path(None)
        
        assert decision.path == router.config.default_path
        assert decision.confidence > 0
    
    def test_invalid_context_handling(self):
        """Test handling of invalid context."""
        router = ProcessingRouter()
        decision = router.determine_path("test query", context="invalid")
        
        assert decision.path is not None
        assert decision.confidence > 0
    
    @patch('src.models.dual_track.router.re.findall')
    def test_regex_error_handling(self, mock_findall):
        """Test handling of regex errors."""
        mock_findall.side_effect = Exception("Regex error")
        
        router = ProcessingRouter()
        decision = router.determine_path("test query")
        
        assert decision.path == router.config.default_path
        assert "error" in decision.reasoning.lower()


class TestRouterConfiguration:
    """Test cases for router configuration."""
    
    def test_custom_config(self):
        """Test router with custom configuration."""
        config = RouterConfig(
            default_path=ProcessingPath.API,
            threshold_simple=10,
            threshold_complex=30
        )
        router = ProcessingRouter(config)
        
        assert router.config.default_path == ProcessingPath.API
        assert router.config.threshold_simple == 10
        assert router.config.threshold_complex == 30
    
    def test_config_weight_adjustment(self):
        """Test configuration weight adjustments."""
        config = RouterConfig(
            weights={
                "token_count": 0.5,
                "entity_count": 0.3,
                "reasoning_steps": 0.2,
                "context_dependency": 0.0,
                "creativity_required": 0.0
            }
        )
        router = ProcessingRouter(config)
        
        assert router.config.weights["token_count"] == 0.5
        assert router.config.weights["context_dependency"] == 0.0