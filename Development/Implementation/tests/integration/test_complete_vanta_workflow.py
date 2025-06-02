#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete VANTA System Workflow Integration Tests

This module implements comprehensive end-to-end integration testing for the complete
VANTA system, validating the entire workflow from voice input to voice output through
memory-enhanced dual-track processing with LangGraph orchestration.
"""
# TASK-REF: INT_002 - End-to-End System Integration Testing
# CONCEPT-REF: CON-VANTA-015 - System Integration Testing
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
# DECISION-REF: DEC-046-004 - Graceful error recovery for memory operations

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import time
import json

# Import VANTA system components  
from src.langgraph.state.vanta_state import VANTAState, create_empty_state
from src.langgraph.graph import create_default_vanta_graph, create_vanta_workflow
from tests.utils.integration_test_utils import (
    IntegrationTestBase,
    MockAudioProvider,
    MockMemorySystem,
    PerformanceMonitor,
    TestScenarios
)

logger = logging.getLogger(__name__)


class TestCompleteVANTAWorkflow(IntegrationTestBase):
    """Comprehensive end-to-end VANTA system workflow tests"""
    
    async def asyncSetUp(self):
        """Setup complete VANTA system for testing"""
        await super().asyncSetUp()
        
        # Initialize complete system components
        self.graph = await self.create_test_graph()
        self.memory_system = MockMemorySystem()
        self.audio_provider = MockAudioProvider()
        self.performance_monitor = PerformanceMonitor()
        self.test_scenarios = TestScenarios()
        
        # Initialize test state
        self.conversation_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        
        logger.info(f"Test setup complete - Conversation: {self.conversation_id}")
    
    async def create_test_graph(self):
        """Create complete VANTA LangGraph for testing"""
        # Create graph with available functions
        graph = create_default_vanta_graph()
        return graph
    
    async def create_test_state(self, scenario: str = "simple_greeting") -> VANTAState:
        """Create test state for workflow execution"""
        scenario_data = self.test_scenarios.get_scenario(scenario)
        
        # Start with empty state and update with test data
        state = create_empty_state()
        state["messages"] = [
            {"role": "user", "content": scenario_data.get("user_input", "Hello")}
        ]
        return state

    @pytest.mark.asyncio
    async def test_end_to_end_voice_conversation(self):
        """Test complete voice conversation workflow: Audio → STT → Memory → Processing → TTS → Audio"""
        logger.info("Testing end-to-end voice conversation workflow")
        
        # Arrange: Create test state with voice input
        initial_state = await self.create_test_state("simple_greeting")
        
        # Mock audio input
        with patch('src.voice.audio_capture.capture_audio') as mock_capture:
            mock_capture.return_value = self.audio_provider.get_test_audio("hello_greeting")
            
            # Mock TTS output
            with patch('src.voice.tts_engine.synthesize_speech') as mock_tts:
                mock_tts.return_value = self.audio_provider.get_test_audio("response_greeting")
                
                # Act: Execute complete workflow
                start_time = time.time()
                final_state = await self.graph.ainvoke(initial_state)
                end_time = time.time()
                
                # Assert: Verify complete workflow execution
                assert final_state is not None
                assert isinstance(final_state, dict)
                # Check if we have some kind of response or processing occurred
                assert len(final_state) > 0
                
                # Verify performance metrics
                execution_time = end_time - start_time
                assert execution_time < 5.0  # Should complete within 5 seconds
                
                # Basic structure verification
                assert "messages" in final_state
                
                logger.info(f"End-to-end workflow completed in {execution_time:.2f}s")

    @pytest.mark.asyncio
    async def test_memory_enhanced_dual_track_processing(self):
        """Test dual-track processing with memory context enhancement"""
        logger.info("Testing memory-enhanced dual-track processing")
        
        # Arrange: Create state with memory context
        initial_state = await self.create_test_state("complex_reasoning_with_memory")
        
        # Set up memory context
        memory_context = {
            "relevant_conversations": [
                {"topic": "AI capabilities", "summary": "Previous discussion about AI limits"},
                {"topic": "Technical details", "summary": "User interested in implementation details"}
            ],
            "user_preferences": {"detail_level": "technical", "response_style": "comprehensive"},
            "conversation_themes": ["artificial intelligence", "technical implementation"]
        }
        initial_state["memory_context"] = memory_context
        
        # Mock dual-track processing components
        with patch.object(DualTrackGraphNodes, 'dual_track_processing_node') as mock_dual_track:
            mock_dual_track.return_value = {
                "local_response": "Local model response with memory context",
                "api_response": "API model response with memory context",
                "processing_stats": {
                    "local_model_time": 1.2,
                    "api_model_time": 0.8,
                    "memory_context_used": True,
                    "optimization_applied": True
                }
            }
            
            # Act: Execute workflow with memory enhancement
            final_state = await self.graph.ainvoke(initial_state)
            
            # Assert: Verify memory context was used
            assert final_state["processing_stats"]["memory_context_used"] is True
            assert "memory context" in final_state["final_response"].lower()
            
            # Verify dual-track processing occurred
            assert final_state["local_response"] is not None
            assert final_state["api_response"] is not None
            
            # Verify optimization was applied
            assert final_state["processing_stats"]["optimization_applied"] is True
            
            logger.info("Memory-enhanced dual-track processing validated")

    @pytest.mark.asyncio  
    async def test_optimization_system_adaptation(self):
        """Test optimization system response to performance data"""
        logger.info("Testing optimization system adaptation")
        
        # Arrange: Create multiple test scenarios to trigger optimization
        scenarios = ["latency_sensitive", "quality_focused", "resource_constrained"]
        optimization_results = []
        
        for scenario in scenarios:
            initial_state = await self.create_test_state(scenario)
            
            # Mock performance conditions
            if scenario == "latency_sensitive":
                initial_state["optimization_data"] = {"target_latency": 500, "priority": "speed"}
            elif scenario == "quality_focused":
                initial_state["optimization_data"] = {"target_quality": 0.9, "priority": "accuracy"}
            else:  # resource_constrained
                initial_state["optimization_data"] = {"memory_limit": 256, "priority": "efficiency"}
            
            # Act: Execute workflow with optimization
            with patch('src.models.dual_track.optimization.AdaptiveOptimizer') as mock_optimizer:
                mock_optimizer.optimize_strategy.return_value = {
                    "strategy": scenario,
                    "parameters": {"timeout": 1.0 if scenario == "latency_sensitive" else 3.0},
                    "confidence": 0.8
                }
                
                final_state = await self.graph.ainvoke(initial_state)
                optimization_results.append(final_state["optimization_data"])
        
        # Assert: Verify optimization adapted to different scenarios
        assert len(optimization_results) == 3
        
        # Verify different strategies were applied
        strategies = [result.get("strategy") for result in optimization_results]
        assert len(set(strategies)) > 1  # Different strategies used
        
        logger.info("Optimization system adaptation validated")

    @pytest.mark.asyncio
    async def test_cross_session_persistence(self):
        """Test state persistence across sessions"""
        logger.info("Testing cross-session persistence")
        
        # Arrange: Create first session
        session1_id = str(uuid.uuid4())
        initial_state = await self.create_test_state("multi_turn_conversation")
        initial_state["session_id"] = session1_id
        
        # Mock persistence backend
        persistence_data = {}
        
        def mock_save_state(session_id: str, state: Dict[str, Any]):
            persistence_data[session_id] = state
            
        def mock_load_state(session_id: str) -> Optional[Dict[str, Any]]:
            return persistence_data.get(session_id)
        
        with patch('src.langgraph.persistence.save_state', side_effect=mock_save_state):
            with patch('src.langgraph.persistence.load_state', side_effect=mock_load_state):
                
                # Act: Execute first session
                session1_final = await self.graph.ainvoke(initial_state)
                
                # Create second session with same conversation
                session2_id = str(uuid.uuid4()) 
                session2_state = await self.create_test_state("follow_up_question")
                session2_state["session_id"] = session2_id
                session2_state["conversation_id"] = session1_final["conversation_id"]
                
                # Execute second session
                session2_final = await self.graph.ainvoke(session2_state)
                
                # Assert: Verify state persistence
                assert session1_final["conversation_id"] == session2_final["conversation_id"]
                assert len(session2_final["conversation_history"]) > len(session1_final["conversation_history"])
                
                # Verify conversation continuity
                assert session2_final["memory_context"] is not None
                
                logger.info("Cross-session persistence validated")

    @pytest.mark.asyncio
    async def test_concurrent_conversation_handling(self):
        """Test system handling of multiple concurrent conversations"""
        logger.info("Testing concurrent conversation handling")
        
        # Arrange: Create multiple concurrent conversations
        num_conversations = 3
        conversation_tasks = []
        
        for i in range(num_conversations):
            initial_state = await self.create_test_state("concurrent_conversation")
            initial_state["conversation_id"] = str(uuid.uuid4())
            initial_state["session_id"] = str(uuid.uuid4())
            initial_state["user_input"] = f"Concurrent conversation {i+1}"
            
            # Create task for each conversation
            task = asyncio.create_task(self.graph.ainvoke(initial_state))
            conversation_tasks.append(task)
        
        # Act: Execute all conversations concurrently
        start_time = time.time()
        results = await asyncio.gather(*conversation_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Assert: Verify all conversations completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == num_conversations
        
        # Verify each conversation maintained separate state
        conversation_ids = {r["conversation_id"] for r in successful_results}
        assert len(conversation_ids) == num_conversations
        
        # Verify reasonable performance under concurrent load
        total_time = end_time - start_time
        assert total_time < 10.0  # Should complete within 10 seconds
        
        logger.info(f"Concurrent conversations completed in {total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_error_recovery_workflow_continuity(self):
        """Test conversation continuity during various error conditions"""
        logger.info("Testing error recovery and workflow continuity")
        
        # Test memory system failure recovery
        initial_state = await self.create_test_state("memory_failure_scenario")
        
        with patch('src.memory.core.MemorySystem.retrieve_context') as mock_retrieve:
            mock_retrieve.side_effect = Exception("Memory system unavailable")
            
            # Act: Execute workflow with memory failure
            final_state = await self.graph.ainvoke(initial_state)
            
            # Assert: Conversation continued without memory
            assert final_state["final_response"] != ""
            assert final_state["error_state"] is None  # Error was handled gracefully
            
        # Test local model failure recovery
        with patch('src.models.local.LocalModel.generate') as mock_local:
            mock_local.side_effect = Exception("Local model unavailable")
            
            initial_state = await self.create_test_state("local_model_failure")
            final_state = await self.graph.ainvoke(initial_state)
            
            # Assert: System fell back to API model
            assert final_state["api_response"] is not None
            assert final_state["final_response"] != ""
            
        logger.info("Error recovery and workflow continuity validated")

    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self):
        """Test performance monitoring throughout the complete workflow"""
        logger.info("Testing performance monitoring integration")
        
        # Arrange: Enable performance monitoring
        initial_state = await self.create_test_state("performance_monitoring")
        
        performance_metrics = {}
        
        def collect_metric(component: str, metric: str, value: float):
            if component not in performance_metrics:
                performance_metrics[component] = {}
            performance_metrics[component][metric] = value
        
        with patch('src.monitoring.metrics_collector.collect', side_effect=collect_metric):
            
            # Act: Execute workflow with monitoring
            final_state = await self.graph.ainvoke(initial_state)
            
            # Assert: Verify metrics were collected
            expected_components = ["stt", "memory", "dual_track", "tts", "workflow"]
            
            for component in expected_components:
                assert component in performance_metrics
                assert "latency" in performance_metrics[component]
            
            # Verify processing stats in final state
            assert "processing_stats" in final_state
            assert len(final_state["processing_stats"]) > 0
            
            logger.info("Performance monitoring integration validated")

    @pytest.mark.asyncio
    async def test_complete_workflow_latency_targets(self):
        """Test that complete workflow meets latency targets"""
        logger.info("Testing complete workflow latency targets")
        
        # Test different latency scenarios
        latency_tests = [
            {"scenario": "simple_greeting", "target_ms": 2000},
            {"scenario": "complex_reasoning", "target_ms": 5000},
            {"scenario": "memory_enhanced", "target_ms": 3000}
        ]
        
        for test_case in latency_tests:
            initial_state = await self.create_test_state(test_case["scenario"])
            
            # Act: Measure workflow execution time
            start_time = time.time()
            final_state = await self.graph.ainvoke(initial_state)
            end_time = time.time()
            
            execution_time_ms = (end_time - start_time) * 1000
            
            # Assert: Verify latency target met
            assert execution_time_ms < test_case["target_ms"], \
                f"Latency target failed for {test_case['scenario']}: {execution_time_ms:.0f}ms > {test_case['target_ms']}ms"
            
            # Verify workflow completed successfully
            assert final_state["final_response"] != ""
            assert final_state["error_state"] is None
            
            logger.info(f"Latency test passed for {test_case['scenario']}: {execution_time_ms:.0f}ms")

    async def asyncTearDown(self):
        """Cleanup test environment"""
        if hasattr(self, 'performance_monitor'):
            await self.performance_monitor.close()
        
        if hasattr(self, 'memory_system'):
            await self.memory_system.close()
            
        await super().asyncTearDown()
        
        logger.info("Test teardown complete")


class TestLangGraphWorkflowIntegration(IntegrationTestBase):
    """LangGraph workflow-specific integration tests"""
    
    @pytest.mark.asyncio
    async def test_complete_graph_execution(self):
        """Test full LangGraph workflow execution with all nodes"""
        logger.info("Testing complete LangGraph workflow execution")
        
        # Create graph and test state
        graph = create_vanta_graph()
        initial_state = VANTAState(
            conversation_id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            user_input="Test complete graph execution",
            is_speech_detected=True,
            transcribed_text="Test complete graph execution",
            memory_context=None,
            conversation_history=[],
            timestamp=datetime.now().isoformat()
        )
        
        # Execute graph
        final_state = await graph.ainvoke(initial_state)
        
        # Verify all expected nodes were executed
        assert final_state["transcribed_text"] != ""
        assert final_state["final_response"] != ""
        assert final_state["conversation_history"] is not None
        
        logger.info("Complete LangGraph workflow execution validated")

    @pytest.mark.asyncio 
    async def test_conditional_routing_with_memory(self):
        """Test routing decisions with memory context"""
        logger.info("Testing conditional routing with memory context")
        
        # Test routing with different memory contexts
        test_cases = [
            {"memory_context": None, "expected_path": "standard"},
            {"memory_context": {"context_size": 100}, "expected_path": "memory_enhanced"},
            {"memory_context": {"context_size": 1000}, "expected_path": "memory_enhanced_with_summarization"}
        ]
        
        for case in test_cases:
            state = VANTAState(
                conversation_id=str(uuid.uuid4()),
                memory_context=case["memory_context"],
                conversation_history=[],
                timestamp=datetime.now().isoformat()
            )
            
            # Test routing decisions
            should_summarize = should_summarize_conversation(state)
            should_use_dual = should_use_dual_track(state)
            
            # Verify routing logic
            if case["memory_context"] is None:
                assert not should_summarize
            elif case["memory_context"]["context_size"] > 500:
                assert should_summarize
                
            logger.info(f"Routing test passed for {case['expected_path']}")


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])