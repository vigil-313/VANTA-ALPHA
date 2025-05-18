# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

# VANTA Test Framework Documentation

This document provides guidelines and information for using the VANTA test framework.

## Test Types

The VANTA test framework supports several types of tests:

### Unit Tests

Unit tests focus on testing individual components in isolation. These tests should:
- Be fast to run
- Not have external dependencies
- Test a single unit of functionality
- Use mocks for external dependencies

### Integration Tests

Integration tests verify that different components work together correctly. These tests:
- Test the interaction between multiple components
- May have some external dependencies (though limited)
- Validate end-to-end workflows

### Performance Tests

Performance tests evaluate the system's efficiency and resource usage. These tests:
- Measure execution time
- Monitor memory usage
- Set benchmarks for acceptable performance
- Ensure the system meets performance requirements

## Writing Tests

### Test File Organization

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Place performance tests in `tests/performance/`
- Use the naming convention `test_*.py` for test files
- Group tests by component or feature

### Test Class and Function Naming

- Name test classes as `Test{Component}` (e.g., `TestAudioProcessor`)
- Name test functions as `test_{scenario}` (e.g., `test_process_audio_with_noise`)

### Test Structure

Follow the Arrange-Act-Assert pattern:

```python
def test_some_function():
    # Arrange - Set up test conditions
    test_input = [1, 2, 3]
    expected_output = 6
    
    # Act - Execute the code being tested
    actual_output = sum(test_input)
    
    # Assert - Verify the results
    assert actual_output == expected_output
```

### Using Fixtures

The test framework provides several fixtures to simplify test setup:

- `test_audio_data`: Provides standard test audio data
- `test_audio_file`: Provides a temporary audio file for testing
- `mock_audio_capture`: Provides a mock audio capture device
- `mock_tts`: Provides a mock TTS system
- `mock_llm`: Provides a mock language model
- `mock_streaming_llm`: Provides a mock streaming language model
- `temp_dir`: Provides a temporary directory

Example usage:

```python
def test_audio_processing(test_audio_data, mock_audio_capture):
    audio_data, sample_rate = test_audio_data
    mock_audio_capture.set_test_audio(audio_data)
    
    # Test code here...
```

### Using Test Utilities

The test framework provides various utilities to simplify testing:

- `test_utils.py`: General testing utilities
- `audio_test_utils.py`: Audio-specific testing utilities
- `model_utils.py`: Model testing utilities
- `performance_utils.py`: Performance testing utilities
- `langgraph_test_utils.py`: LangGraph testing utilities

## Running Tests

### Running All Tests

```bash
pytest
```

### Running Specific Test Types

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run performance tests
pytest tests/performance/
```

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/unit/test_audio_processor.py

# Run a specific test function
pytest tests/unit/test_audio_processor.py::TestAudioProcessor::test_process_audio_with_noise
```

### Running with Code Coverage

```bash
pytest --cov=./ --cov-report=html
```

## Test Markers

The test framework includes several markers to categorize tests:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Tests that take a long time to run
- `@pytest.mark.audio`: Tests that require audio capability
- `@pytest.mark.model`: Tests that require ML models

Example usage:

```python
@pytest.mark.slow
@pytest.mark.model
def test_large_model_inference():
    # Slow test that requires a model
    pass
```

Running tests with specific markers:

```bash
pytest -m "unit and not slow"
```

## Mocking

The test framework provides several mock objects for testing:

- `MockAudioCapture`: Mocks audio capture devices
- `MockTTS`: Mocks TTS systems
- `MockLLM`: Mocks language models
- `MockStreamingLLM`: Mocks streaming language models

Example usage:

```python
def test_with_mock_llm():
    mock_llm = MockLLM()
    mock_llm.add_response("weather", "It's sunny today")
    
    response = mock_llm.generate("What's the weather like?")
    assert "sunny" in response
```