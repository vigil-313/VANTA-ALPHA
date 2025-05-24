# VANTA Integration Tests

This directory contains comprehensive end-to-end integration tests for the complete VANTA system, validating all components working together in realistic scenarios.

## Overview

The integration tests validate:

- **Complete Workflow Integration**: End-to-end voice conversation workflows from audio input to audio output
- **Memory-Enhanced Processing**: Integration of memory system with dual-track processing and LangGraph orchestration
- **Performance Under Load**: System behavior under various load and resource conditions
- **Error Recovery**: Graceful degradation and recovery mechanisms across all system components
- **Cross-Session Persistence**: State management and conversation continuity across sessions

## Test Structure

### Core Integration Tests

#### `test_complete_vanta_workflow.py`
**Primary end-to-end workflow testing**

- `TestCompleteVANTAWorkflow`: Complete system workflow validation
  - `test_end_to_end_voice_conversation()`: Full audio → STT → Memory → Processing → TTS → Audio pipeline
  - `test_memory_enhanced_dual_track_processing()`: Dual-track processing with memory context enhancement
  - `test_optimization_system_adaptation()`: Optimization system response to performance data
  - `test_cross_session_persistence()`: State persistence across sessions
  - `test_concurrent_conversation_handling()`: Multiple concurrent conversations
  - `test_error_recovery_workflow_continuity()`: Conversation continuity during errors
  - `test_performance_monitoring_integration()`: Performance monitoring throughout workflow
  - `test_complete_workflow_latency_targets()`: Workflow latency target validation

- `TestLangGraphWorkflowIntegration`: LangGraph-specific workflow tests
  - `test_complete_graph_execution()`: Full LangGraph workflow execution
  - `test_conditional_routing_with_memory()`: Routing decisions with memory context

#### `test_performance_integration.py`
**Performance and resource management testing**

- `TestPerformanceIntegration`: System performance under various conditions
  - `test_system_under_load()`: Load testing with concurrent conversations
  - `test_resource_constraint_handling()`: Behavior under resource constraints
  - `test_latency_optimization()`: End-to-end latency optimization validation
  - `test_memory_usage_optimization()`: Memory usage optimization strategies
  - `test_concurrent_optimization_adaptation()`: Optimization under concurrent load
  - `test_performance_degradation_detection()`: Detection and recovery from performance issues

#### `test_error_recovery_integration.py`
**Error recovery and fault tolerance testing**

- `TestErrorRecoveryIntegration`: Comprehensive error recovery validation
  - `test_memory_system_failure_recovery()`: Memory system failure scenarios
  - `test_local_model_failure_recovery()`: Local model failure and API fallback
  - `test_api_model_failure_recovery()`: API model failure and local fallback
  - `test_audio_system_failure_recovery()`: Audio system failure and text mode fallback
  - `test_langgraph_workflow_failure_recovery()`: LangGraph workflow failure recovery
  - `test_cascading_failure_recovery()`: Multiple simultaneous system failures
  - `test_error_recovery_state_consistency()`: State consistency during error recovery
  - `test_error_recovery_performance_impact()`: Performance impact of error recovery

### Supporting Components

#### `test_utils/integration_test_utils.py`
**Comprehensive test utilities and mocks**

- `TestScenarios`: Predefined test scenarios for various use cases
- `MockAudioProvider`: Mock audio input/output for consistent testing
- `MockMemorySystem`: Mock memory system with configurable behavior
- `PerformanceMonitor`: Performance monitoring and metrics collection
- `IntegrationTestBase`: Base class with common setup/teardown
- `MockConfiguration`: Mock configuration management
- `TestDataGenerator`: Generate test data for various scenarios

#### `fixtures/integration_test_config.yaml`
**Test configuration and scenarios**

- Audio system configuration (mock mode, sample rates, formats)
- Memory system configuration (backends, thresholds, failure simulation)
- Model configuration (local/API models, dual-track settings)
- LangGraph configuration (nodes, routing, persistence)
- Performance targets and resource limits
- Error recovery behavior and fallback strategies
- Test scenarios for all major functionality areas

## Test Scenarios

### Basic Functionality
- **Simple Greeting**: Basic voice interaction workflow
- **Complex Reasoning**: Educational content generation
- **Memory Enhanced**: Conversations building on previous context

### Performance Testing
- **Latency Sensitive**: Quick factual responses
- **Quality Focused**: Detailed analytical content
- **Resource Constrained**: Efficient processing under limits

### Error Recovery
- **Memory Failure**: Memory system unavailable scenarios
- **Model Failures**: Local and API model failure scenarios
- **Audio Failures**: STT/TTS system failure scenarios
- **Cascading Failures**: Multiple simultaneous system failures

### Load Testing
- **Concurrent Conversations**: Multiple simultaneous users
- **High Frequency**: Rapid message exchanges
- **Resource Stress**: Testing under resource constraints

## Running Integration Tests

### Prerequisites

```bash
# Ensure you're in the implementation directory
cd /Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation

# Install test dependencies
pip install pytest pytest-asyncio pytest-mock psutil numpy

# Set up test environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Run All Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v --asyncio-mode=auto

# Run with detailed output
pytest tests/integration/ -v --asyncio-mode=auto -s

# Run specific test categories
pytest tests/integration/test_complete_vanta_workflow.py -v --asyncio-mode=auto
pytest tests/integration/test_performance_integration.py -v --asyncio-mode=auto
pytest tests/integration/test_error_recovery_integration.py -v --asyncio-mode=auto
```

### Run Tests in Docker

```bash
# Use the Docker test environment
cd /Users/vigil-313/workplace/VANTA-ALPHA/Development/Implementation
./scripts/docker_test.sh "python -m pytest tests/integration/ -v --asyncio-mode=auto"
```

### Performance Testing

```bash
# Run performance tests with timing
pytest tests/integration/test_performance_integration.py::TestPerformanceIntegration::test_system_under_load -v --asyncio-mode=auto

# Run latency optimization tests
pytest tests/integration/test_performance_integration.py::TestPerformanceIntegration::test_latency_optimization -v --asyncio-mode=auto
```

### Error Recovery Testing

```bash
# Run all error recovery scenarios
pytest tests/integration/test_error_recovery_integration.py -v --asyncio-mode=auto

# Run specific failure scenarios
pytest tests/integration/test_error_recovery_integration.py::TestErrorRecoveryIntegration::test_memory_system_failure_recovery -v --asyncio-mode=auto
pytest tests/integration/test_error_recovery_integration.py::TestErrorRecoveryIntegration::test_cascading_failure_recovery -v --asyncio-mode=auto
```

## Test Configuration

### Environment Variables

```bash
# Test configuration
export VANTA_TEST_MODE="integration"
export VANTA_MOCK_AUDIO="true"
export VANTA_MOCK_MODELS="true"
export VANTA_LOG_LEVEL="INFO"

# Performance testing
export VANTA_PERFORMANCE_MONITORING="true"
export VANTA_MAX_CONCURRENT_TESTS="5"

# Error simulation (for testing error recovery)
export VANTA_SIMULATE_ERRORS="false"  # Set to "true" to enable error simulation
export VANTA_ERROR_RATE="0.1"  # 10% error rate when simulation enabled
```

### Configuration File

The test configuration is managed through `tests/fixtures/integration_test_config.yaml`. Key sections:

- **Audio Configuration**: Sample rates, formats, mock audio generation
- **Memory Configuration**: Backend selection, thresholds, failure simulation
- **Model Configuration**: Local/API model settings, dual-track behavior
- **Performance Targets**: Latency thresholds, resource limits
- **Error Recovery**: Fallback strategies, retry behavior
- **Test Scenarios**: Predefined scenarios for all test categories

## Performance Targets

### Latency Targets (milliseconds)
- Simple Greeting: ≤ 1,500ms
- Complex Reasoning: ≤ 4,000ms
- Memory Enhanced: ≤ 3,000ms
- Latency Sensitive: ≤ 800ms
- Quality Focused: ≤ 6,000ms
- Resource Constrained: ≤ 500ms

### Resource Limits
- Memory Usage: ≤ 512MB per conversation
- CPU Usage: ≤ 80% during normal operation
- Concurrent Conversations: ≥ 10 simultaneous users
- Success Rate: ≥ 95% under normal conditions

### Scaling Requirements
- 10x load increase should not exceed 3x performance degradation
- Error recovery should complete within 15 seconds
- Memory failure should not interrupt conversation flow
- Cross-session persistence should maintain state correctly

## Error Recovery Validation

### Memory System Failures
- Context retrieval failure → Continue without memory context
- Storage failure → Continue with temporary local storage
- Complete memory failure → Full memory system fallback

### Model Failures
- Local model failure → Automatic API model fallback
- API model failure → Automatic local model fallback
- Both models unavailable → Graceful error message

### Audio System Failures
- Microphone unavailable → Text input mode
- Speaker unavailable → Text output mode
- STT failure → Retry with timeout or text input
- TTS failure → Text output only

### Workflow Failures
- Node execution failure → Skip node and continue workflow
- Routing failure → Use default routing path
- State persistence failure → Continue without persistence

## Debugging Integration Tests

### Verbose Logging

```bash
# Enable detailed logging
export VANTA_LOG_LEVEL="DEBUG"
pytest tests/integration/ -v --asyncio-mode=auto -s --log-cli-level=DEBUG
```

### Individual Test Debugging

```bash
# Run single test with detailed output
pytest tests/integration/test_complete_vanta_workflow.py::TestCompleteVANTAWorkflow::test_end_to_end_voice_conversation -v --asyncio-mode=auto -s

# Run with Python debugger
pytest tests/integration/test_complete_vanta_workflow.py::TestCompleteVANTAWorkflow::test_end_to_end_voice_conversation --pdb
```

### Performance Profiling

```bash
# Run with performance profiling
python -m cProfile -o integration_profile.prof -m pytest tests/integration/test_performance_integration.py

# Analyze profile
python -c "import pstats; pstats.Stats('integration_profile.prof').sort_stats('cumulative').print_stats(20)"
```

## Expected Results

### Successful Test Run
```
tests/integration/test_complete_vanta_workflow.py::TestCompleteVANTAWorkflow::test_end_to_end_voice_conversation PASSED
tests/integration/test_complete_vanta_workflow.py::TestCompleteVANTAWorkflow::test_memory_enhanced_dual_track_processing PASSED
tests/integration/test_complete_vanta_workflow.py::TestCompleteVANTAWorkflow::test_optimization_system_adaptation PASSED
tests/integration/test_complete_vanta_workflow.py::TestCompleteVANTAWorkflow::test_cross_session_persistence PASSED
tests/integration/test_performance_integration.py::TestPerformanceIntegration::test_system_under_load PASSED
tests/integration/test_performance_integration.py::TestPerformanceIntegration::test_latency_optimization PASSED
tests/integration/test_error_recovery_integration.py::TestErrorRecoveryIntegration::test_memory_system_failure_recovery PASSED
tests/integration/test_error_recovery_integration.py::TestErrorRecoveryIntegration::test_cascading_failure_recovery PASSED

================================ 8 passed in 45.67s ================================
```

### Performance Summary
```
Integration Test Performance Summary:
- Average end-to-end latency: 1,847ms
- Concurrent conversation success rate: 98.3%
- Error recovery success rate: 100%
- Memory usage efficiency: 234MB average
- All latency targets met
```

## Contributing

When adding new integration tests:

1. **Follow the established patterns** in existing test files
2. **Use the test utilities** from `integration_test_utils.py`
3. **Add new scenarios** to the configuration file
4. **Include performance assertions** for new functionality
5. **Test error recovery paths** for new components
6. **Update this documentation** with new test descriptions

### Test Naming Convention
- Test classes: `Test{Component}Integration`
- Test methods: `test_{functionality}_{scenario}`
- Example: `test_memory_system_failure_recovery`

### Test Documentation
Each test should include:
- Clear docstring describing what is being tested
- Performance expectations and assertions
- Error conditions and recovery expectations
- Integration points being validated

## Troubleshooting

### Common Issues

**Tests failing with timeout errors:**
- Increase timeout values in configuration
- Check for blocking operations in mocked components
- Verify async/await usage is correct

**Memory usage errors:**
- Reduce concurrent test count
- Check for memory leaks in test cleanup
- Verify mock objects are being properly released

**Performance target failures:**
- Review system load during test execution
- Check for inefficient mock implementations
- Verify performance targets are realistic for test environment

**State persistence issues:**
- Verify test isolation between test cases
- Check cleanup in test teardown methods
- Ensure mock state is reset between tests

### Getting Help

For issues with integration tests:

1. Check the test logs for specific error messages
2. Review the integration test configuration
3. Verify all dependencies are properly mocked
4. Run individual tests to isolate issues
5. Check resource usage during test execution