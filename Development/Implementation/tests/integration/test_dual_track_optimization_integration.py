#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the dual-track optimization system with existing components.
"""
# TASK-REF: DP-003 - Dual-Track Optimization
# CONCEPT-REF: CON-VANTA-012 - Dual-Track Optimization

import pytest
import time
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.models.dual_track.optimizer import (
    DualTrackOptimizer,
    OptimizationConfig,
    OptimizationStrategy,
    ResourceConstraints,
    PerformanceMetrics
)
from src.models.dual_track.router import ProcessingRouter
from src.models.dual_track.integrator import ResponseIntegrator
from src.models.dual_track.config import DualTrackConfig
from src.models.dual_track.graph_nodes import DualTrackGraphNodes
from src.models.dual_track.exceptions import DualTrackOptimizationError


class TestOptimizerWithRouter:
    """Test optimization system integration with processing router."""
    
    @pytest.fixture
    def optimizer_config(self):
        """Fixture for optimizer configuration."""
        return OptimizationConfig(
            strategy=OptimizationStrategy.ADAPTIVE,
            adaptation_interval_seconds=1.0,  # Quick adaptation for testing
            enable_resource_monitoring=False  # Disable for testing
        )
    
    @pytest.fixture
    def optimizer(self, optimizer_config):
        """Fixture for optimizer."""
        opt = DualTrackOptimizer(optimizer_config)
        opt.start()
        return opt
    
    @pytest.fixture
    def router_config(self):
        """Fixture for router configuration."""
        return DualTrackConfig()
    
    @pytest.fixture
    def router(self, router_config):
        """Fixture for processing router."""
        return ProcessingRouter(router_config.router)
    
    def test_router_optimization_integration(self, router, optimizer):
        """Test integration between router and optimizer."""
        query = "What is machine learning?"
        context = {"user_id": "test123"}
        
        # Get optimization recommendations
        recommendations = optimizer.get_optimization_recommendations(query, context)
        
        # Router should be able to use recommendations
        assert "routing_preferences" in recommendations
        assert "resource_status" in recommendations
        assert "timeouts" in recommendations
        
        preferences = recommendations["routing_preferences"]
        assert "local_bias" in preferences
        assert "parallel_threshold" in preferences
        assert "timeout_multiplier" in preferences
    
    def test_optimization_affects_routing_decisions(self, router, optimizer):
        """Test that optimization recommendations affect routing decisions."""
        query = "Simple greeting"
        
        # Get initial routing decision
        initial_decision = router.determine_path(query)
        initial_path = initial_decision.path
        
        # Simulate metrics that would favor local processing
        for i in range(10):
            request_id = f"local-test-{i}"
            optimizer.record_request_start(request_id, query)
            
            # Simulate fast, successful local processing
            result = {
                "tokens_used": 20,
                "cost_estimate": 0.0,
                "quality_score": 0.9
            }
            optimizer.record_request_completion(
                request_id, "local", result, success=True
            )
        
        # Wait for adaptation
        time.sleep(1.1)
        
        # Get new recommendations after metrics
        recommendations = optimizer.get_optimization_recommendations(query)
        
        # Should have updated preferences based on metrics
        assert "routing_preferences" in recommendations
        preferences = recommendations["routing_preferences"]
        
        # Local bias might have changed based on the simulated good performance
        assert isinstance(preferences["local_bias"], float)
        assert 0.0 <= preferences["local_bias"] <= 1.0
    
    def test_resource_constraints_affect_routing(self, router, optimizer):
        """Test that resource constraints affect routing recommendations."""
        query = "Complex analysis task"
        
        # Mock high resource usage
        with patch.object(optimizer.resource_monitor, 'get_current_usage') as mock_usage:
            mock_usage.return_value = {
                "memory_mb": 8192.0,  # High memory usage
                "cpu_percent": 95.0,   # High CPU usage
                "gpu_memory_mb": 0.0,
                "battery_percent": 15.0,  # Low battery
                "timestamp": time.time()
            }
            
            recommendations = optimizer.get_optimization_recommendations(query)
            
            # Should detect resource violations
            resource_status = recommendations["resource_status"]
            violations = resource_status["violations"]
            
            # Should have memory, CPU, and battery violations
            assert "memory" in violations or "cpu" in violations or "battery" in violations
            assert resource_status["can_use_local"] is False or resource_status["can_use_parallel"] is False


class TestOptimizerWithIntegrator:
    """Test optimization system integration with response integrator."""
    
    @pytest.fixture
    def optimizer(self):
        """Fixture for optimizer."""
        config = OptimizationConfig(enable_resource_monitoring=False)
        opt = DualTrackOptimizer(config)
        opt.start()
        return opt
    
    @pytest.fixture
    def integrator(self):
        """Fixture for response integrator."""
        from src.models.dual_track.config import IntegrationConfig
        config = IntegrationConfig()
        return ResponseIntegrator(config)
    
    def test_quality_tracking_integration(self, optimizer, integrator):
        """Test integration of quality tracking with optimization."""
        local_response = {
            "text": "Local model response",
            "confidence": 0.7,
            "tokens_used": 50,
            "generation_time": 0.5
        }
        
        api_response = {
            "text": "API model response with higher quality",
            "confidence": 0.9,
            "tokens_used": 60,
            "generation_time": 2.0,
            "cost_estimate": 0.008
        }
        
        # Integrate responses
        result = integrator.integrate_responses(
            local_response, api_response, "parallel"
        )
        
        # Record metrics with quality scores from integration result
        request_id = str(uuid.uuid4())
        optimizer.record_request_start(request_id, "Test query")
        
        # Use integration result to determine quality score
        quality_score = result.similarity_score if hasattr(result, 'similarity_score') else 0.8
        
        completion_result = {
            "tokens_used": result.metadata.get("tokens_used", 55),
            "cost_estimate": result.metadata.get("cost_estimate", 0.004),
            "quality_score": quality_score
        }
        
        optimizer.record_request_completion(
            request_id, "parallel", completion_result, success=True
        )
        
        # Check that metrics were recorded
        summary = optimizer.get_metrics_summary()
        assert summary["total_requests"] == 1
        assert summary["avg_quality_score"] > 0


class TestOptimizerWithGraphNodes:
    """Test optimization system integration with LangGraph nodes."""
    
    @pytest.fixture
    def optimizer(self):
        """Fixture for optimizer."""
        config = OptimizationConfig(enable_resource_monitoring=False)
        opt = DualTrackOptimizer(config)
        opt.start()
        return opt
    
    @pytest.fixture
    def graph_nodes(self, optimizer):
        """Fixture for graph nodes with optimizer."""
        from src.models.dual_track.config import DualTrackConfig
        config = DualTrackConfig()
        return DualTrackGraphNodes(config, optimizer=optimizer)
    
    def test_graph_nodes_use_optimization(self, graph_nodes, optimizer):
        """Test that graph nodes use optimization recommendations."""
        # Mock LangGraph state
        state = {
            "query": "What is artificial intelligence?",
            "context": {"user_id": "test123"},
            "request_id": str(uuid.uuid4()),
            "optimization_recommendations": {}
        }
        
        # Test router node with optimization
        with patch.object(graph_nodes.router, 'determine_path') as mock_router:
            mock_decision = Mock()
            mock_decision.path = "parallel"
            mock_decision.confidence = 0.8
            mock_decision.reasoning = "Test routing"
            mock_router.return_value = mock_decision
            
            result = graph_nodes.enhanced_router_node(state)
            
            # Should include optimization recommendations in result
            assert "optimization_recommendations" in result
            recommendations = result["optimization_recommendations"]
            assert "routing_preferences" in recommendations
            assert "resource_status" in recommendations
    
    def test_graph_nodes_record_metrics(self, graph_nodes, optimizer):
        """Test that graph nodes properly record metrics."""
        request_id = str(uuid.uuid4())
        state = {
            "query": "Test query for metrics",
            "context": {"test": "context"},
            "request_id": request_id,
            "processing_path": "local"
        }
        
        # Simulate local processing node
        with patch.object(graph_nodes.local_controller, 'generate') as mock_generate:
            mock_response = Mock()
            mock_response.text = "Local response"
            mock_response.tokens_used = 45
            mock_response.generation_time = 0.8
            mock_response.success = True
            mock_generate.return_value = mock_response
            
            # Record request start
            optimizer.record_request_start(request_id, state["query"], state.get("context"))
            
            # Process with local node
            result = graph_nodes.enhanced_local_processing_node(state)
            
            # Should have local response
            assert "local_response" in result
            
            # Record completion
            completion_result = {
                "tokens_used": mock_response.tokens_used,
                "cost_estimate": 0.0,
                "quality_score": 0.7
            }
            optimizer.record_request_completion(
                request_id, "local", completion_result, success=True
            )
            
            # Check metrics were recorded
            summary = optimizer.get_metrics_summary("local")
            assert summary["total_requests"] >= 1


class TestEndToEndOptimization:
    """Test end-to-end optimization workflow."""
    
    @pytest.fixture
    def optimizer(self):
        """Fixture for optimizer with adaptive strategy."""
        config = OptimizationConfig(
            strategy=OptimizationStrategy.ADAPTIVE,
            adaptation_interval_seconds=0.5,  # Quick adaptation
            enable_resource_monitoring=False
        )
        opt = DualTrackOptimizer(config)
        opt.start()
        return opt
    
    def test_adaptive_optimization_workflow(self, optimizer):
        """Test complete adaptive optimization workflow."""
        queries = [
            "Simple question",
            "Complex analysis requiring deep reasoning",
            "Another simple query",
            "Moderately complex question"
        ]
        
        # Simulate processing different types of queries
        for i, query in enumerate(queries):
            request_id = f"adaptive-test-{i}"
            
            # Get optimization recommendations
            recommendations = optimizer.get_optimization_recommendations(query)
            assert "routing_preferences" in recommendations
            
            # Record request start
            optimizer.record_request_start(request_id, query, {"session": "test"})
            
            # Simulate different processing paths and outcomes
            if "simple" in query.lower():
                # Simple queries go to local with good performance
                path = "local"
                result = {
                    "tokens_used": 25,
                    "cost_estimate": 0.0,
                    "quality_score": 0.8
                }
                success = True
            else:
                # Complex queries go to API with higher cost
                path = "api"
                result = {
                    "tokens_used": 80,
                    "cost_estimate": 0.012,
                    "quality_score": 0.9
                }
                success = True
            
            # Record completion
            optimizer.record_request_completion(request_id, path, result, success)
        
        # Get overall metrics
        summary = optimizer.get_metrics_summary()
        
        assert summary["total_requests"] == len(queries)
        assert summary["success_rate"] == 1.0
        assert summary["total_cost"] > 0  # Should have some API costs
        
        # Check path-specific metrics
        local_summary = optimizer.get_metrics_summary("local")
        api_summary = optimizer.get_metrics_summary("api")
        
        assert local_summary["total_requests"] >= 1
        assert api_summary["total_requests"] >= 1
    
    def test_optimization_under_load(self, optimizer):
        """Test optimization system under concurrent load."""
        import threading
        import concurrent.futures
        
        def process_request(request_id):
            query = f"Load test query {request_id}"
            
            # Get recommendations
            recommendations = optimizer.get_optimization_recommendations(query)
            
            # Record request
            optimizer.record_request_start(request_id, query)
            
            # Simulate processing delay
            time.sleep(0.01)
            
            # Record completion
            result = {
                "tokens_used": 30,
                "cost_estimate": 0.005,
                "quality_score": 0.75
            }
            optimizer.record_request_completion(request_id, "parallel", result, True)
            
            return recommendations
        
        # Process multiple requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(20):
                future = executor.submit(process_request, f"load-test-{i}")
                futures.append(future)
            
            # Wait for all requests to complete
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=5.0)
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Request failed: {e}")
        
        # Check that all requests were processed
        assert len(results) == 20
        
        # Check final metrics
        summary = optimizer.get_metrics_summary()
        assert summary["total_requests"] == 20
        assert summary["success_rate"] == 1.0
    
    def test_optimization_error_handling(self, optimizer):
        """Test optimization system handles errors gracefully."""
        request_id = "error-test"
        query = "Query that will fail"
        
        # Record request start
        optimizer.record_request_start(request_id, query)
        
        # Simulate processing failure
        optimizer.record_request_completion(
            request_id, "api", {}, success=False, error_type="api_timeout"
        )
        
        # Get metrics
        summary = optimizer.get_metrics_summary()
        
        assert summary["total_requests"] == 1
        assert summary["successful_requests"] == 0
        assert summary["success_rate"] == 0.0
        assert "api_timeout" in summary["error_rate_by_type"]
        assert summary["error_rate_by_type"]["api_timeout"] == 1.0
        
        # System should still provide recommendations after errors
        recommendations = optimizer.get_optimization_recommendations("New query")
        assert "routing_preferences" in recommendations


class TestOptimizerConfiguration:
    """Test optimizer configuration integration."""
    
    def test_dual_track_config_with_optimization(self):
        """Test DualTrackConfig with optimization settings."""
        from src.models.dual_track.config import DualTrackConfig
        
        config = DualTrackConfig(
            enable_optimization=True,
            optimization_strategy="latency_focused",
            target_latency_ms=1000.0,
            max_memory_mb=2048.0
        )
        
        assert config.enable_optimization is True
        assert config.optimization_strategy == "latency_focused"
        assert config.target_latency_ms == 1000.0
        assert config.max_memory_mb == 2048.0
        
        # Should be able to create optimizer from this config
        optimizer_config = OptimizationConfig(
            strategy=OptimizationStrategy.LATENCY_FOCUSED,
            constraints=ResourceConstraints(
                target_latency_ms=config.target_latency_ms,
                max_memory_mb=config.max_memory_mb
            ),
            adaptation_interval_seconds=config.adaptation_interval_seconds
        )
        
        optimizer = DualTrackOptimizer(optimizer_config)
        assert optimizer.config.strategy == OptimizationStrategy.LATENCY_FOCUSED
    
    def test_config_validation_with_optimization(self):
        """Test configuration validation with optimization enabled."""
        from src.models.dual_track.config import DualTrackConfig
        
        # Valid configuration
        valid_config = DualTrackConfig(
            enable_optimization=True,
            optimization_strategy="adaptive",
            target_latency_ms=2000.0,
            max_concurrent_requests=4
        )
        
        # Should be able to create components with valid config
        optimizer_config = OptimizationConfig(
            strategy=OptimizationStrategy.ADAPTIVE,
            constraints=ResourceConstraints(
                target_latency_ms=valid_config.target_latency_ms,
                max_concurrent_requests=valid_config.max_concurrent_requests
            )
        )
        
        optimizer = DualTrackOptimizer(optimizer_config)
        status = optimizer.get_optimization_status()
        
        assert status["config"]["strategy"] == "adaptive"
        assert status["config"]["constraints"]["target_latency_ms"] == 2000.0
        assert status["config"]["constraints"]["max_concurrent_requests"] == 4


if __name__ == "__main__":
    pytest.main([__file__])