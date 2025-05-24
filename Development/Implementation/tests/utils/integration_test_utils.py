#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Test Utilities

This module provides comprehensive utilities for end-to-end VANTA system integration testing,
including mock providers, performance monitoring, test scenarios, and base test classes.
"""
# TASK-REF: INT_002 - End-to-End System Integration Testing
# CONCEPT-REF: CON-VANTA-015 - System Integration Testing
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import json
from unittest.mock import Mock, AsyncMock, MagicMock
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TestScenario:
    """Test scenario data structure"""
    name: str
    user_input: str
    audio_data: Optional[bytes] = None
    transcribed_text: str = ""
    is_speech_detected: bool = True
    memory_context: Optional[Dict[str, Any]] = None
    conversation_summary: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = None
    expected_response_type: str = "standard"
    performance_expectations: Dict[str, float] = None

    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.performance_expectations is None:
            self.performance_expectations = {"latency_ms": 2000}


class TestScenarios:
    """Collection of predefined test scenarios for integration testing"""
    
    def __init__(self):
        self.scenarios = self._initialize_scenarios()
    
    def _initialize_scenarios(self) -> Dict[str, TestScenario]:
        """Initialize predefined test scenarios"""
        return {
            "simple_greeting": TestScenario(
                name="simple_greeting",
                user_input="Hello, how are you today?",
                transcribed_text="Hello, how are you today?",
                audio_data=self._generate_mock_audio("hello"),
                expected_response_type="greeting",
                performance_expectations={"latency_ms": 1500}
            ),
            
            "complex_reasoning": TestScenario(
                name="complex_reasoning",
                user_input="Can you explain the differences between machine learning and artificial intelligence?",
                transcribed_text="Can you explain the differences between machine learning and artificial intelligence?",
                audio_data=self._generate_mock_audio("complex_question"),
                expected_response_type="educational",
                performance_expectations={"latency_ms": 4000}
            ),
            
            "complex_reasoning_with_memory": TestScenario(
                name="complex_reasoning_with_memory",
                user_input="Building on our previous discussion about AI, how does deep learning fit in?",
                transcribed_text="Building on our previous discussion about AI, how does deep learning fit in?",
                memory_context={
                    "relevant_conversations": [
                        {"topic": "AI vs ML", "summary": "Discussed differences between AI and machine learning"}
                    ],
                    "user_preferences": {"detail_level": "technical"},
                    "conversation_themes": ["artificial intelligence", "machine learning"]
                },
                conversation_history=[
                    {"role": "user", "content": "What is artificial intelligence?"},
                    {"role": "assistant", "content": "AI is the simulation of human intelligence in machines..."}
                ],
                expected_response_type="contextual_educational",
                performance_expectations={"latency_ms": 3500}
            ),
            
            "multi_turn_conversation": TestScenario(
                name="multi_turn_conversation",
                user_input="That's interesting, can you tell me more?",
                transcribed_text="That's interesting, can you tell me more?",
                conversation_history=[
                    {"role": "user", "content": "What is quantum computing?"},
                    {"role": "assistant", "content": "Quantum computing uses quantum mechanics principles..."},
                    {"role": "user", "content": "How is it different from classical computing?"},
                    {"role": "assistant", "content": "Classical computers use bits while quantum computers use qubits..."}
                ],
                memory_context={
                    "current_topic": "quantum computing",
                    "context_depth": "technical_explanation"
                },
                expected_response_type="continuation",
                performance_expectations={"latency_ms": 2500}
            ),
            
            "latency_sensitive": TestScenario(
                name="latency_sensitive",
                user_input="Quick question - what time is it?",
                transcribed_text="Quick question - what time is it?",
                expected_response_type="factual",
                performance_expectations={"latency_ms": 800}
            ),
            
            "quality_focused": TestScenario(
                name="quality_focused",
                user_input="Write a detailed analysis of renewable energy trends in 2024",
                transcribed_text="Write a detailed analysis of renewable energy trends in 2024",
                expected_response_type="analytical",
                performance_expectations={"latency_ms": 6000, "quality_score": 0.9}
            ),
            
            "resource_constrained": TestScenario(
                name="resource_constrained",
                user_input="Simple math: what is 2 + 2?",
                transcribed_text="Simple math: what is 2 + 2?",
                expected_response_type="calculation",
                performance_expectations={"latency_ms": 500, "memory_mb": 50}
            ),
            
            "memory_failure_scenario": TestScenario(
                name="memory_failure_scenario",
                user_input="Continue our conversation from earlier",
                transcribed_text="Continue our conversation from earlier",
                memory_context=None,  # Will trigger memory failure in tests
                expected_response_type="fallback_response",
                performance_expectations={"latency_ms": 2000}
            ),
            
            "local_model_failure": TestScenario(
                name="local_model_failure",
                user_input="Help me with a technical problem",
                transcribed_text="Help me with a technical problem",
                expected_response_type="api_fallback",
                performance_expectations={"latency_ms": 3000}
            ),
            
            "concurrent_conversation": TestScenario(
                name="concurrent_conversation",
                user_input="Test concurrent processing",
                transcribed_text="Test concurrent processing",
                expected_response_type="standard",
                performance_expectations={"latency_ms": 2500}
            ),
            
            "follow_up_question": TestScenario(
                name="follow_up_question",
                user_input="Can you elaborate on that last point?",
                transcribed_text="Can you elaborate on that last point?",
                conversation_history=[
                    {"role": "assistant", "content": "Here are three key points about the topic..."}
                ],
                expected_response_type="elaboration",
                performance_expectations={"latency_ms": 2000}
            ),
            
            "performance_monitoring": TestScenario(
                name="performance_monitoring",
                user_input="Test performance monitoring capabilities",
                transcribed_text="Test performance monitoring capabilities",
                expected_response_type="standard",
                performance_expectations={"latency_ms": 2000}
            )
        }
    
    def get_scenario(self, name: str) -> TestScenario:
        """Get test scenario by name"""
        if name not in self.scenarios:
            logger.warning(f"Unknown scenario '{name}', using simple_greeting")
            return self.scenarios["simple_greeting"]
        return self.scenarios[name]
    
    def list_scenarios(self) -> List[str]:
        """List all available scenario names"""
        return list(self.scenarios.keys())
    
    def _generate_mock_audio(self, content_type: str) -> bytes:
        """Generate mock audio data for testing"""
        # Generate mock audio based on content type
        duration_map = {
            "hello": 1.0,
            "complex_question": 5.0,
            "default": 2.0
        }
        
        duration = duration_map.get(content_type, 2.0)
        sample_rate = 16000
        samples = int(duration * sample_rate)
        
        # Generate simple sine wave as mock audio
        frequency = 440  # A4 note
        t = np.linspace(0, duration, samples, False)
        audio_data = np.sin(frequency * 2 * np.pi * t)
        
        # Convert to bytes (16-bit PCM)
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        return audio_bytes


class MockAudioProvider:
    """Mock audio provider for integration testing"""
    
    def __init__(self):
        self.test_scenarios = TestScenarios()
    
    def get_test_audio(self, audio_type: str) -> bytes:
        """Get mock audio data for testing"""
        return self.test_scenarios._generate_mock_audio(audio_type)
    
    async def capture_audio(self, duration: float = 5.0) -> bytes:
        """Mock audio capture"""
        await asyncio.sleep(0.1)  # Simulate capture delay
        return self.get_test_audio("default")
    
    async def play_audio(self, audio_data: bytes) -> None:
        """Mock audio playback"""
        await asyncio.sleep(0.1)  # Simulate playback delay


class MockMemorySystem:
    """Mock memory system for integration testing"""
    
    def __init__(self):
        self.conversations = {}
        self.summaries = {}
        self.context_data = {}
        
    async def retrieve_context(self, conversation_id: str, query: str) -> Dict[str, Any]:
        """Mock context retrieval"""
        await asyncio.sleep(0.05)  # Simulate retrieval delay
        
        return self.context_data.get(conversation_id, {
            "relevant_conversations": [],
            "user_preferences": {},
            "conversation_themes": []
        })
    
    async def store_conversation(self, conversation_id: str, message: Dict[str, Any]) -> None:
        """Mock conversation storage"""
        await asyncio.sleep(0.02)  # Simulate storage delay
        
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        self.conversations[conversation_id].append(message)
    
    async def summarize_conversation(self, conversation_id: str) -> Optional[str]:
        """Mock conversation summarization"""
        await asyncio.sleep(0.1)  # Simulate summarization delay
        
        messages = self.conversations.get(conversation_id, [])
        if len(messages) > 5:
            return f"Summary of {len(messages)} messages in conversation {conversation_id}"
        return None
    
    async def close(self):
        """Mock cleanup"""
        pass


class PerformanceMonitor:
    """Performance monitoring for integration tests"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        
    def start_timing(self, operation: str) -> str:
        """Start timing an operation"""
        operation_id = f"{operation}_{uuid.uuid4()}"
        self.start_times[operation_id] = time.time()
        return operation_id
    
    def end_timing(self, operation_id: str) -> float:
        """End timing an operation and return duration"""
        if operation_id not in self.start_times:
            return 0.0
            
        duration = time.time() - self.start_times[operation_id]
        del self.start_times[operation_id]
        return duration
    
    def record_metric(self, component: str, metric: str, value: float):
        """Record a performance metric"""
        if component not in self.metrics:
            self.metrics[component] = {}
        self.metrics[component][metric] = value
    
    def get_metrics(self, component: Optional[str] = None) -> Dict[str, Any]:
        """Get recorded metrics"""
        if component:
            return self.metrics.get(component, {})
        return self.metrics
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.start_times.clear()
    
    async def close(self):
        """Cleanup resources"""
        self.reset_metrics()


class IntegrationTestBase:
    """Base class for integration tests with common setup/teardown"""
    
    async def asyncSetUp(self):
        """Common setup for integration tests"""
        self.start_time = time.time()
        self.test_id = str(uuid.uuid4())
        
        # Configure logging for test
        self.logger = logging.getLogger(f"test_{self.__class__.__name__}")
        self.logger.setLevel(logging.INFO)
        
        # Initialize common test components
        self.performance_monitor = PerformanceMonitor()
        
        self.logger.info(f"Integration test setup complete - Test ID: {self.test_id}")
    
    async def asyncTearDown(self):
        """Common teardown for integration tests"""
        test_duration = time.time() - self.start_time
        
        # Log test completion
        self.logger.info(f"Integration test completed in {test_duration:.2f}s - Test ID: {self.test_id}")
        
        # Cleanup resources
        if hasattr(self, 'performance_monitor'):
            await self.performance_monitor.close()
    
    def assert_performance_target(self, actual_ms: float, target_ms: float, operation: str):
        """Assert that performance target was met"""
        assert actual_ms <= target_ms, \
            f"Performance target failed for {operation}: {actual_ms:.0f}ms > {target_ms}ms"
        
        self.logger.info(f"Performance target met for {operation}: {actual_ms:.0f}ms <= {target_ms}ms")
    
    def assert_workflow_completion(self, state: Dict[str, Any]):
        """Assert that workflow completed successfully"""
        assert state is not None, "Workflow state should not be None"
        assert "final_response" in state, "Workflow should produce final_response"
        assert state["final_response"] != "", "Final response should not be empty"
        assert state.get("error_state") is None, f"Workflow should not have errors: {state.get('error_state')}"
        
        self.logger.info("Workflow completion assertions passed")


class MockConfiguration:
    """Mock configuration for integration testing"""
    
    def __init__(self):
        self.config = {
            "memory": {
                "backend": "mock",
                "summarization_threshold": 10,
                "context_window_size": 4000
            },
            "models": {
                "local_model": "mock_local",
                "api_provider": "mock_api",
                "dual_track_enabled": True
            },
            "audio": {
                "sample_rate": 16000,
                "format": "wav",
                "mock_mode": True
            },
            "performance": {
                "latency_target_ms": 2000,
                "memory_limit_mb": 512,
                "optimization_enabled": True
            },
            "testing": {
                "mock_audio": True,
                "mock_models": True,
                "performance_monitoring": True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        keys = key.split(".")
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value


class TestDataGenerator:
    """Generate test data for various integration scenarios"""
    
    @staticmethod
    def generate_conversation_history(length: int) -> List[Dict[str, Any]]:
        """Generate mock conversation history"""
        history = []
        
        for i in range(length):
            if i % 2 == 0:
                history.append({
                    "role": "user",
                    "content": f"User message {i//2 + 1}",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                history.append({
                    "role": "assistant", 
                    "content": f"Assistant response {i//2 + 1}",
                    "timestamp": datetime.now().isoformat()
                })
        
        return history
    
    @staticmethod
    def generate_memory_context(complexity: str = "simple") -> Dict[str, Any]:
        """Generate mock memory context"""
        contexts = {
            "simple": {
                "relevant_conversations": [
                    {"topic": "general", "summary": "Basic conversation"}
                ],
                "user_preferences": {"response_style": "casual"},
                "conversation_themes": ["general"]
            },
            "complex": {
                "relevant_conversations": [
                    {"topic": "technical", "summary": "Detailed technical discussion"},
                    {"topic": "preferences", "summary": "User prefers detailed explanations"},
                    {"topic": "history", "summary": "Long conversation history"}
                ],
                "user_preferences": {
                    "response_style": "detailed",
                    "expertise_level": "advanced",
                    "preferred_topics": ["technology", "science"]
                },
                "conversation_themes": ["artificial intelligence", "machine learning", "technology"]
            }
        }
        
        return contexts.get(complexity, contexts["simple"])
    
    @staticmethod
    def generate_performance_metrics() -> Dict[str, Dict[str, float]]:
        """Generate mock performance metrics"""
        return {
            "stt": {"latency": 150.0, "accuracy": 0.95},
            "memory": {"retrieval_time": 50.0, "storage_time": 20.0},
            "local_model": {"generation_time": 800.0, "tokens_per_second": 15.0},
            "api_model": {"generation_time": 400.0, "tokens_per_second": 25.0},
            "tts": {"synthesis_time": 200.0, "audio_quality": 0.9},
            "workflow": {"total_time": 1200.0, "success_rate": 0.98}
        }


# Export public interface
__all__ = [
    "TestScenario",
    "TestScenarios", 
    "MockAudioProvider",
    "MockMemorySystem",
    "PerformanceMonitor",
    "IntegrationTestBase",
    "MockConfiguration",
    "TestDataGenerator"
]