#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Integration Tests

This module implements comprehensive performance testing for the complete VANTA system,
validating performance characteristics under various load and resource conditions.
"""
# TASK-REF: INT_002 - End-to-End System Integration Testing
# CONCEPT-REF: CON-VANTA-015 - System Integration Testing
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview
# DECISION-REF: DEC-045-001 - Performance monitoring and metrics collection

import pytest
import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, Any, List
from unittest.mock import patch, Mock
import statistics
import uuid
from datetime import datetime

from src.langgraph.graph import create_vanta_graph, VANTAState
from src.models.dual_track.optimization import (
    MetricsCollector,
    AdaptiveOptimizer,
    ResourceMonitor
)
from tests.utils.integration_test_utils import (
    IntegrationTestBase,
    PerformanceMonitor,
    TestScenarios,
    MockConfiguration
)

logger = logging.getLogger(__name__)


class TestPerformanceIntegration(IntegrationTestBase):
    """Performance integration tests for the complete VANTA system"""
    
    async def asyncSetUp(self):
        """Setup performance testing environment"""
        await super().asyncSetUp()
        
        self.graph = create_vanta_graph()
        self.test_scenarios = TestScenarios()
        self.config = MockConfiguration()
        self.performance_data = []
        
        # Initialize performance monitoring components
        self.metrics_collector = MetricsCollector()
        self.resource_monitor = ResourceMonitor()
        self.adaptive_optimizer = AdaptiveOptimizer(
            metrics_collector=self.metrics_collector,
            resource_monitor=self.resource_monitor
        )
        
        logger.info("Performance testing environment setup complete")

    @pytest.mark.asyncio
    async def test_system_under_load(self):
        """Test system behavior under various load conditions"""
        logger.info("Testing system under load")
        
        # Test different load levels
        load_levels = [1, 3, 5, 10]  # Number of concurrent conversations
        results = {}
        
        for num_conversations in load_levels:
            logger.info(f"Testing with {num_conversations} concurrent conversations")
            
            # Create conversation tasks
            tasks = []
            start_time = time.time()
            
            for i in range(num_conversations):
                initial_state = VANTAState(
                    conversation_id=str(uuid.uuid4()),
                    session_id=str(uuid.uuid4()),
                    user_input=f"Load test conversation {i+1}",
                    transcribed_text=f"Load test conversation {i+1}",
                    is_speech_detected=True,
                    conversation_history=[],
                    timestamp=datetime.now().isoformat()
                )
                
                task = asyncio.create_task(self.graph.ainvoke(initial_state))
                tasks.append(task)
            
            # Execute all conversations concurrently
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Analyze results
            successful_results = [r for r in completed_results if not isinstance(r, Exception)]
            failed_results = [r for r in completed_results if isinstance(r, Exception)]
            
            total_time = end_time - start_time
            success_rate = len(successful_results) / num_conversations
            avg_time_per_conversation = total_time / num_conversations if num_conversations > 0 else 0
            
            results[num_conversations] = {
                "total_time": total_time,
                "success_rate": success_rate,
                "avg_time_per_conversation": avg_time_per_conversation,
                "failed_count": len(failed_results)
            }
            
            # Assert performance expectations
            assert success_rate >= 0.9, f"Success rate too low: {success_rate:.2f}"
            assert avg_time_per_conversation < 5.0, f"Average time too high: {avg_time_per_conversation:.2f}s"
            
            logger.info(f"Load test results for {num_conversations} conversations: "
                       f"success_rate={success_rate:.2f}, avg_time={avg_time_per_conversation:.2f}s")
        
        # Verify system scales reasonably
        single_time = results[1]["avg_time_per_conversation"]
        ten_time = results[10]["avg_time_per_conversation"]
        scaling_factor = ten_time / single_time
        
        assert scaling_factor < 3.0, f"Poor scaling: {scaling_factor:.2f}x slowdown with 10x load"
        
        logger.info(f"Load testing completed. Scaling factor: {scaling_factor:.2f}")

    @pytest.mark.asyncio
    async def test_resource_constraint_handling(self):
        """Test system behavior under resource constraints"""
        logger.info("Testing resource constraint handling")
        
        # Simulate different resource constraint scenarios
        constraint_scenarios = [
            {"memory_limit_mb": 256, "cpu_limit_percent": 50},
            {"memory_limit_mb": 128, "cpu_limit_percent": 30},
            {"memory_limit_mb": 512, "cpu_limit_percent": 80}
        ]
        
        for scenario in constraint_scenarios:
            logger.info(f"Testing with constraints: {scenario}")
            
            # Configure resource constraints
            self.resource_monitor.set_memory_limit(scenario["memory_limit_mb"])
            self.resource_monitor.set_cpu_limit(scenario["cpu_limit_percent"])
            
            # Create test state
            initial_state = VANTAState(
                conversation_id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                user_input="Test under resource constraints",
                transcribed_text="Test under resource constraints", 
                is_speech_detected=True,
                conversation_history=[],
                timestamp=datetime.now().isoformat()
            )
            
            # Monitor resource usage during execution
            initial_memory = psutil.virtual_memory().used / 1024 / 1024  # MB
            initial_cpu = psutil.cpu_percent()
            
            start_time = time.time()
            final_state = await self.graph.ainvoke(initial_state)
            end_time = time.time()
            
            final_memory = psutil.virtual_memory().used / 1024 / 1024  # MB
            memory_used = final_memory - initial_memory
            execution_time = end_time - start_time
            
            # Assert system completed successfully within constraints
            assert final_state["final_response"] != "", "System should complete under constraints"
            assert final_state["error_state"] is None, "Should not error under normal constraints"
            assert memory_used < scenario["memory_limit_mb"] * 2, f"Memory usage too high: {memory_used:.1f}MB"
            assert execution_time < 10.0, f"Execution time too high under constraints: {execution_time:.2f}s"
            
            logger.info(f"Resource constraint test passed: memory_used={memory_used:.1f}MB, "
                       f"time={execution_time:.2f}s")

    @pytest.mark.asyncio
    async def test_latency_optimization(self):
        """Test end-to-end latency optimization"""
        logger.info("Testing latency optimization")
        
        # Test scenarios with different latency requirements
        latency_scenarios = [
            {"scenario": "latency_sensitive", "target_ms": 800, "strategy": "speed"},
            {"scenario": "simple_greeting", "target_ms": 1500, "strategy": "balanced"},
            {"scenario": "complex_reasoning", "target_ms": 4000, "strategy": "quality"}
        ]
        
        optimization_results = []
        
        for scenario_config in latency_scenarios:
            scenario = self.test_scenarios.get_scenario(scenario_config["scenario"])
            
            # Configure optimization strategy
            self.adaptive_optimizer.set_strategy(scenario_config["strategy"])
            
            # Execute multiple iterations to test optimization improvement
            iteration_times = []
            
            for iteration in range(5):
                initial_state = VANTAState(
                    conversation_id=str(uuid.uuid4()),
                    session_id=str(uuid.uuid4()),
                    user_input=scenario.user_input,
                    transcribed_text=scenario.transcribed_text,
                    is_speech_detected=True,
                    conversation_history=[],
                    optimization_data={"strategy": scenario_config["strategy"]},
                    timestamp=datetime.now().isoformat()
                )
                
                start_time = time.time()
                final_state = await self.graph.ainvoke(initial_state)
                end_time = time.time()
                
                execution_time_ms = (end_time - start_time) * 1000
                iteration_times.append(execution_time_ms)
                
                # Record metrics for optimization
                self.metrics_collector.record_latency("workflow", execution_time_ms)
                
                # Assert basic functionality
                assert final_state["final_response"] != "", "Response should be generated"
                
                logger.info(f"Iteration {iteration+1}: {execution_time_ms:.0f}ms")
            
            # Analyze optimization effectiveness
            avg_latency = statistics.mean(iteration_times)
            min_latency = min(iteration_times)
            improvement = (iteration_times[0] - iteration_times[-1]) / iteration_times[0] * 100
            
            optimization_results.append({
                "scenario": scenario_config["scenario"],
                "strategy": scenario_config["strategy"],
                "target_ms": scenario_config["target_ms"],
                "avg_latency": avg_latency,
                "min_latency": min_latency,
                "improvement_percent": improvement
            })
            
            # Assert latency targets met
            assert avg_latency <= scenario_config["target_ms"], \
                f"Average latency target not met: {avg_latency:.0f}ms > {scenario_config['target_ms']}ms"
            
            logger.info(f"Latency optimization test passed for {scenario_config['scenario']}: "
                       f"avg={avg_latency:.0f}ms, improvement={improvement:.1f}%")
        
        # Verify optimization strategies show different performance characteristics
        speed_result = next(r for r in optimization_results if r["strategy"] == "speed")
        quality_result = next(r for r in optimization_results if r["strategy"] == "quality")
        
        assert speed_result["avg_latency"] < quality_result["avg_latency"], \
            "Speed strategy should be faster than quality strategy"

    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self):
        """Test memory usage optimization strategies"""
        logger.info("Testing memory usage optimization")
        
        # Test different memory scenarios
        memory_scenarios = [
            {"history_length": 5, "expected_memory_mb": 50},
            {"history_length": 20, "expected_memory_mb": 100},
            {"history_length": 50, "expected_memory_mb": 200}
        ]
        
        for scenario in memory_scenarios:
            # Create conversation with specified history length
            conversation_history = []
            for i in range(scenario["history_length"]):
                conversation_history.extend([
                    {"role": "user", "content": f"Message {i+1} from user with some content"},
                    {"role": "assistant", "content": f"Response {i+1} from assistant with detailed information"}
                ])
            
            initial_state = VANTAState(
                conversation_id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                user_input="Continue our conversation",
                transcribed_text="Continue our conversation",
                is_speech_detected=True,
                conversation_history=conversation_history,
                memory_context={"context_size": len(conversation_history) * 100},  # Approximate size
                timestamp=datetime.now().isoformat()
            )
            
            # Monitor memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Execute workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Assert memory usage is reasonable
            assert final_state["final_response"] != "", "Response should be generated"
            assert memory_increase < scenario["expected_memory_mb"], \
                f"Memory usage too high: {memory_increase:.1f}MB > {scenario['expected_memory_mb']}MB"
            
            # Check if summarization was triggered for long conversations
            if scenario["history_length"] > 20:
                assert final_state.get("conversation_summary") is not None, \
                    "Long conversations should trigger summarization"
            
            logger.info(f"Memory test passed for {scenario['history_length']} messages: "
                       f"memory_increase={memory_increase:.1f}MB")

    @pytest.mark.asyncio
    async def test_concurrent_optimization_adaptation(self):
        """Test optimization system adaptation under concurrent load"""
        logger.info("Testing concurrent optimization adaptation")
        
        # Create multiple concurrent conversations with different characteristics
        conversation_configs = [
            {"type": "speed_focused", "count": 3},
            {"type": "quality_focused", "count": 2}, 
            {"type": "resource_constrained", "count": 2}
        ]
        
        all_tasks = []
        start_time = time.time()
        
        for config in conversation_configs:
            for i in range(config["count"]):
                scenario = self.test_scenarios.get_scenario(config["type"])
                
                initial_state = VANTAState(
                    conversation_id=str(uuid.uuid4()),
                    session_id=str(uuid.uuid4()),
                    user_input=scenario.user_input,
                    transcribed_text=scenario.transcribed_text,
                    is_speech_detected=True,
                    conversation_history=[],
                    optimization_data={"priority": config["type"]},
                    timestamp=datetime.now().isoformat()
                )
                
                task = asyncio.create_task(
                    self._execute_with_metrics(initial_state, config["type"])
                )
                all_tasks.append(task)
        
        # Execute all conversations concurrently
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze concurrent execution results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        success_rate = len(successful_results) / len(all_tasks)
        
        # Assert system handled concurrent optimization well
        assert success_rate >= 0.9, f"Concurrent success rate too low: {success_rate:.2f}"
        assert total_time < 15.0, f"Total concurrent execution time too high: {total_time:.2f}s"
        
        # Verify different optimization strategies were applied
        optimization_strategies = set()
        for result in successful_results:
            if "optimization_data" in result and "applied_strategy" in result["optimization_data"]:
                optimization_strategies.add(result["optimization_data"]["applied_strategy"])
        
        assert len(optimization_strategies) > 1, "Multiple optimization strategies should be used"
        
        logger.info(f"Concurrent optimization test passed: success_rate={success_rate:.2f}, "
                   f"strategies_used={len(optimization_strategies)}, total_time={total_time:.2f}s")

    async def _execute_with_metrics(self, initial_state: VANTAState, optimization_type: str) -> Dict[str, Any]:
        """Execute workflow with metrics collection"""
        start_time = time.time()
        
        # Apply optimization strategy based on type
        if optimization_type == "speed_focused":
            self.adaptive_optimizer.set_strategy("speed")
        elif optimization_type == "quality_focused":
            self.adaptive_optimizer.set_strategy("quality")
        else:  # resource_constrained
            self.adaptive_optimizer.set_strategy("efficiency")
        
        # Execute workflow
        final_state = await self.graph.ainvoke(initial_state)
        
        execution_time = time.time() - start_time
        
        # Add metrics to final state
        final_state["optimization_data"] = {
            **final_state.get("optimization_data", {}),
            "execution_time": execution_time,
            "applied_strategy": self.adaptive_optimizer.current_strategy
        }
        
        return final_state

    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self):
        """Test detection of performance degradation and recovery"""
        logger.info("Testing performance degradation detection")
        
        # Baseline performance measurement
        baseline_times = []
        for i in range(3):
            initial_state = VANTAState(
                conversation_id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                user_input="Baseline performance test",
                transcribed_text="Baseline performance test",
                is_speech_detected=True,
                conversation_history=[],
                timestamp=datetime.now().isoformat()
            )
            
            start_time = time.time()
            await self.graph.ainvoke(initial_state)
            baseline_times.append(time.time() - start_time)
        
        baseline_avg = statistics.mean(baseline_times)
        
        # Simulate performance degradation
        with patch('src.models.dual_track.local_model.LocalModel.generate') as mock_local:
            # Add artificial delay to simulate degradation
            async def slow_generate(*args, **kwargs):
                await asyncio.sleep(2.0)  # 2 second delay
                return "Slow response due to degradation"
            
            mock_local.side_effect = slow_generate
            
            # Measure degraded performance
            degraded_times = []
            for i in range(3):
                initial_state = VANTAState(
                    conversation_id=str(uuid.uuid4()),
                    session_id=str(uuid.uuid4()),
                    user_input="Degraded performance test",
                    transcribed_text="Degraded performance test",
                    is_speech_detected=True,
                    conversation_history=[],
                    timestamp=datetime.now().isoformat()
                )
                
                start_time = time.time()
                final_state = await self.graph.ainvoke(initial_state)
                degraded_times.append(time.time() - start_time)
                
                # Record degraded performance
                self.metrics_collector.record_latency("local_model", (time.time() - start_time) * 1000)
        
        degraded_avg = statistics.mean(degraded_times)
        degradation_factor = degraded_avg / baseline_avg
        
        # Assert degradation was detected
        assert degradation_factor > 2.0, f"Expected significant degradation, got {degradation_factor:.2f}x"
        
        # Test recovery - system should adapt
        recovery_times = []
        for i in range(3):
            initial_state = VANTAState(
                conversation_id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                user_input="Recovery performance test",
                transcribed_text="Recovery performance test",
                is_speech_detected=True,
                conversation_history=[],
                timestamp=datetime.now().isoformat()
            )
            
            start_time = time.time()
            await self.graph.ainvoke(initial_state)
            recovery_times.append(time.time() - start_time)
        
        recovery_avg = statistics.mean(recovery_times)
        recovery_improvement = degraded_avg / recovery_avg
        
        # Assert system recovered
        assert recovery_improvement > 1.2, f"Expected performance recovery, got {recovery_improvement:.2f}x improvement"
        
        logger.info(f"Performance degradation test passed: baseline={baseline_avg:.2f}s, "
                   f"degraded={degraded_avg:.2f}s, recovered={recovery_avg:.2f}s")

    async def asyncTearDown(self):
        """Cleanup performance testing environment"""
        # Log performance summary
        if self.performance_data:
            avg_performance = statistics.mean(self.performance_data)
            logger.info(f"Average performance across all tests: {avg_performance:.2f}s")
        
        # Cleanup optimization components
        if hasattr(self, 'metrics_collector'):
            self.metrics_collector.reset()
        
        if hasattr(self, 'resource_monitor'):
            await self.resource_monitor.close()
        
        if hasattr(self, 'adaptive_optimizer'):
            await self.adaptive_optimizer.close()
        
        await super().asyncTearDown()
        
        logger.info("Performance testing cleanup complete")


if __name__ == "__main__":
    # Configure logging for performance tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run performance tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-x"])