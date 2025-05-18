# IMPLEMENTATION TASK: ENV_004 Test Framework Setup

## Context
Effective testing is critical for ensuring the reliability and stability of the VANTA system. A comprehensive testing framework needs to be established early in the development process to support test-driven development and continuous validation of components. This task involves setting up the testing infrastructure, including unit testing, integration testing, and performance testing capabilities.

This task (TASK-ENV-004) depends on the Docker environment setup (TASK-ENV-002) and is a prerequisite for component development and integration tasks.

## Objective
Create a comprehensive testing framework for VANTA that enables effective validation of all system components and their interactions, with support for various testing types and automated test execution.

## Requirements
1. Set up pytest-based test infrastructure
2. Configure test discovery and execution
3. Create test utilities and helper functions
4. Implement mocking and stubbing capabilities for dependencies
5. Set up audio testing environment
6. Configure CI/CD integration
7. Establish test coverage reporting
8. Create test fixture management
9. Set up performance testing tools
10. Create documentation and guidelines for writing tests

## References
- [DOC-DEV-TEST-1]: Development/TEST_STRATEGY.md - For testing approach and strategy
- [DOC-DEV-IMPL-1]: Development/IMPLEMENTATION_PLAN.md - For task dependencies
- [DOC-ARCH-001]: Development/Architecture/V0_ARCHITECTURE_OVERVIEW.md - For overall architecture understanding
- [DOC-COMP-001]: Development/Architecture/COMPONENT_SPECIFICATIONS/VOICE_PIPELINE.md - For voice component test requirements
- [DOC-COMP-002]: Development/Architecture/COMPONENT_SPECIFICATIONS/DUAL_TRACK_PROCESSING.md - For dual-track test requirements

## Steps

### 1. Create Test Directory Structure

Set up a structured test directory to organize different types of tests:

```bash
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/performance
mkdir -p tests/fixtures
mkdir -p tests/utils
mkdir -p tests/mocks
```

### 2. Create Basic pytest Configuration

Create a pytest configuration file:

```python
# tests/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    slow: Tests that take a long time to run
    audio: Tests that require audio capability
    model: Tests that require ML models
filterwarnings =
    ignore::DeprecationWarning
    ignore::UserWarning
log_cli = True
log_cli_level = INFO
```

### 3. Create Test Utilities

Create helper utilities for testing:

```python
# tests/utils/test_utils.py
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Tuple, Optional

def create_test_audio(duration: float = 1.0, 
                      sample_rate: int = 16000, 
                      frequency: float = 440.0) -> Tuple[np.ndarray, int]:
    """
    Create a test audio signal with a sine wave.
    
    Args:
        duration: Duration of the audio in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of the sine wave in Hz
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    # Generate time array
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate sine wave
    audio_data = np.sin(2 * np.pi * frequency * t)
    
    # Normalize to [-1, 1]
    audio_data = audio_data / np.max(np.abs(audio_data))
    
    return audio_data, sample_rate

def save_test_audio(audio_data: np.ndarray, 
                   sample_rate: int, 
                   path: Optional[str] = None) -> str:
    """
    Save test audio to a temporary file or specified path.
    
    Args:
        audio_data: Audio data as numpy array
        sample_rate: Sample rate in Hz
        path: Optional path to save the file
        
    Returns:
        Path to the saved audio file
    """
    if path is None:
        # Create a temporary file with .wav extension
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name
    
    # Save the audio file
    sf.write(path, audio_data, sample_rate)
    
    return path

def audio_rms(audio_data: np.ndarray) -> float:
    """
    Calculate the root mean square (RMS) of an audio signal.
    
    Args:
        audio_data: Audio data as numpy array
        
    Returns:
        RMS value
    """
    return np.sqrt(np.mean(np.square(audio_data)))

def assert_audio_similar(audio1: np.ndarray, 
                         audio2: np.ndarray, 
                         threshold: float = 0.1) -> bool:
    """
    Assert that two audio signals are similar based on RMS difference.
    
    Args:
        audio1: First audio signal
        audio2: Second audio signal
        threshold: Similarity threshold (lower means more similar)
        
    Returns:
        True if similar, False otherwise
    """
    # Ensure same length by truncating to shorter
    min_length = min(len(audio1), len(audio2))
    audio1 = audio1[:min_length]
    audio2 = audio2[:min_length]
    
    # Calculate RMS difference
    diff = np.abs(audio1 - audio2)
    diff_rms = audio_rms(diff)
    
    # Calculate reference RMS
    rms1 = audio_rms(audio1)
    
    # Calculate relative difference
    relative_diff = diff_rms / (rms1 + 1e-10)  # Avoid division by zero
    
    return relative_diff < threshold
```

### 4. Create Model Testing Utilities

Create utilities for testing ML models:

```python
# tests/utils/model_utils.py
import os
import json
from typing import Dict, Any, Optional, List

def get_test_models(model_type: str) -> List[Dict[str, Any]]:
    """
    Get available test models from the model registry.
    
    Args:
        model_type: Type of model to retrieve ('whisper', 'llm', 'embedding', 'tts')
        
    Returns:
        List of model information dictionaries
    """
    registry_path = os.path.abspath("models/registry/registry.json")
    
    if not os.path.exists(registry_path):
        return []
    
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    return [m for m in registry["models"] if m["type"] == model_type]

def get_smallest_model(model_type: str) -> Optional[Dict[str, Any]]:
    """
    Get the smallest available model of a given type for testing.
    
    Args:
        model_type: Type of model to retrieve ('whisper', 'llm', 'embedding', 'tts')
        
    Returns:
        Model information dictionary or None if no models available
    """
    models = get_test_models(model_type)
    
    if not models:
        return None
    
    # Find model with "tiny" or "small" in the name, or the first one
    for keyword in ["tiny", "small", "base", "mini"]:
        for model in models:
            if keyword in model["name"].lower():
                return model
    
    # If no preferred small model found, return the first one
    return models[0]

def skip_if_no_model(model_type: str) -> bool:
    """
    Check if a required model is available and skip test if not.
    
    Args:
        model_type: Type of model required ('whisper', 'llm', 'embedding', 'tts')
        
    Returns:
        True if a model is available, False if not
    """
    model = get_smallest_model(model_type)
    return model is not None
```

### 5. Create Mock Objects

Create mock objects for testing:

```python
# tests/mocks/mock_audio.py
import numpy as np
from typing import Tuple, List, Dict, Any, Optional

class MockAudioCapture:
    """Mock audio capture device for testing."""
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.is_active = False
        self.test_audio: Optional[np.ndarray] = None
        self.position = 0
    
    def set_test_audio(self, audio: np.ndarray):
        """Set the test audio data to be returned by read."""
        self.test_audio = audio
        self.position = 0
    
    def start(self):
        """Start audio capture."""
        self.is_active = True
        self.position = 0
        return self
    
    def stop(self):
        """Stop audio capture."""
        self.is_active = False
        return self
    
    def read(self) -> Tuple[bool, np.ndarray]:
        """Read a chunk of audio data."""
        if not self.is_active or self.test_audio is None:
            return False, np.zeros(self.chunk_size, dtype=np.float32)
        
        # Calculate end position for current chunk
        end_pos = min(self.position + self.chunk_size, len(self.test_audio))
        
        # Get chunk from test audio
        chunk = self.test_audio[self.position:end_pos]
        
        # Pad if needed
        if len(chunk) < self.chunk_size:
            chunk = np.pad(chunk, (0, self.chunk_size - len(chunk)))
        
        # Update position
        self.position = end_pos
        
        # Return chunk
        return True, chunk

# tests/mocks/mock_tts.py
import numpy as np
from typing import Dict, Any, Optional

class MockTTS:
    """Mock text-to-speech system for testing."""
    
    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self.last_text = ""
    
    def synthesize(self, text: str, voice: str = "default") -> np.ndarray:
        """
        Mock synthesize text to speech.
        
        Args:
            text: Text to synthesize
            voice: Voice to use
            
        Returns:
            Audio data as numpy array
        """
        self.last_text = text
        
        # Create simple signal proportional to text length
        duration = len(text) * 0.1  # 100ms per character
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # Generate sine wave with frequency related to voice
        if voice == "high":
            freq = 880.0
        elif voice == "low":
            freq = 220.0
        else:
            freq = 440.0
            
        audio_data = np.sin(2 * np.pi * freq * t)
        
        # Add some noise to make it more realistic
        noise = np.random.normal(0, 0.01, len(audio_data))
        audio_data = audio_data + noise
        
        # Normalize
        audio_data = audio_data / np.max(np.abs(audio_data))
        
        return audio_data

# tests/mocks/mock_llm.py
from typing import Dict, Any, List, Optional

class MockLLM:
    """Mock language model for testing."""
    
    def __init__(self):
        self.last_prompt = ""
        self.responses = {}
        
    def add_response(self, prompt_contains: str, response: str):
        """
        Add a canned response for prompts containing a specific string.
        
        Args:
            prompt_contains: String that should be contained in the prompt
            response: Response to return
        """
        self.responses[prompt_contains] = response
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Mock generate text from a prompt.
        
        Args:
            prompt: Text prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated text
        """
        self.last_prompt = prompt
        
        # Look for matching canned response
        for key, response in self.responses.items():
            if key in prompt:
                return response
        
        # Default response based on prompt length
        return f"Response to: {prompt[:10]}..." if len(prompt) > 10 else f"Response to: {prompt}"

class MockStreamingLLM:
    """Mock streaming language model for testing."""
    
    def __init__(self):
        self.llm = MockLLM()
        
    def add_response(self, prompt_contains: str, response: str):
        """Add a canned response."""
        self.llm.add_response(prompt_contains, response)
    
    def generate_stream(self, prompt: str, **kwargs):
        """
        Mock streaming text generation.
        
        Args:
            prompt: Text prompt
            **kwargs: Additional parameters
            
        Yields:
            Chunks of generated text
        """
        response = self.llm.generate(prompt, **kwargs)
        
        # Yield response in chunks of ~5 characters
        chunk_size = min(5, len(response))
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]
```

### 6. Create Test Fixtures

Create test fixtures for reusable test setup:

```python
# tests/fixtures/fixtures.py
import os
import pytest
import numpy as np
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator

from tests.utils.test_utils import create_test_audio, save_test_audio
from tests.mocks.mock_audio import MockAudioCapture
from tests.mocks.mock_tts import MockTTS
from tests.mocks.mock_llm import MockLLM, MockStreamingLLM

@pytest.fixture
def test_audio_data():
    """Fixture providing standard test audio data."""
    return create_test_audio(duration=2.0, sample_rate=16000, frequency=440.0)

@pytest.fixture
def test_audio_file(test_audio_data):
    """Fixture providing a temporary test audio file."""
    audio_data, sample_rate = test_audio_data
    
    # Create a temporary file
    audio_path = save_test_audio(audio_data, sample_rate)
    
    yield audio_path
    
    # Clean up
    if os.path.exists(audio_path):
        os.remove(audio_path)

@pytest.fixture
def mock_audio_capture():
    """Fixture providing a mock audio capture device."""
    return MockAudioCapture()

@pytest.fixture
def mock_tts():
    """Fixture providing a mock TTS system."""
    return MockTTS()

@pytest.fixture
def mock_llm():
    """Fixture providing a mock language model."""
    model = MockLLM()
    
    # Add some standard responses
    model.add_response("hello", "Hello there! How can I help you today?")
    model.add_response("weather", "The weather today is sunny with a high of 75°F.")
    model.add_response("help", "I'm here to assist you with any questions you may have.")
    
    return model

@pytest.fixture
def mock_streaming_llm():
    """Fixture providing a mock streaming language model."""
    model = MockStreamingLLM()
    
    # Add some standard responses
    model.add_response("hello", "Hello there! How can I help you today?")
    model.add_response("weather", "The weather today is sunny with a high of 75°F.")
    model.add_response("help", "I'm here to assist you with any questions you may have.")
    
    return model

@pytest.fixture
def temp_dir():
    """Fixture providing a temporary directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)
```

### 7. Create Performance Testing Utilities

Create utilities for performance testing:

```python
# tests/utils/performance_utils.py
import time
import psutil
import numpy as np
from typing import Dict, Any, List, Optional, Callable, Tuple
from functools import wraps

def measure_execution_time(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """
    Measure the execution time of a function.
    
    Args:
        func: Function to measure
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Tuple of (function result, execution time in seconds)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    
    return result, end_time - start_time

def measure_memory_usage(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """
    Measure the peak memory usage of a function.
    
    Args:
        func: Function to measure
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Tuple of (function result, peak memory usage in MB)
    """
    process = psutil.Process()
    start_memory = process.memory_info().rss / (1024 * 1024)  # Convert to MB
    
    result = func(*args, **kwargs)
    
    end_memory = process.memory_info().rss / (1024 * 1024)  # Convert to MB
    
    return result, end_memory - start_memory

def performance_benchmark(repeat: int = 5) -> Callable:
    """
    Decorator to benchmark the performance of a function.
    
    Args:
        repeat: Number of times to repeat the measurement
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            times = []
            memory_usages = []
            
            for _ in range(repeat):
                # Time measurement
                result, execution_time = measure_execution_time(func, *args, **kwargs)
                times.append(execution_time)
                
                # Memory measurement
                _, memory_usage = measure_memory_usage(func, *args, **kwargs)
                memory_usages.append(memory_usage)
            
            # Calculate statistics
            avg_time = np.mean(times)
            min_time = np.min(times)
            max_time = np.max(times)
            std_time = np.std(times)
            
            avg_memory = np.mean(memory_usages)
            max_memory = np.max(memory_usages)
            
            return {
                "result": result,
                "time": {
                    "avg": avg_time,
                    "min": min_time,
                    "max": max_time,
                    "std": std_time
                },
                "memory": {
                    "avg": avg_memory,
                    "max": max_memory
                }
            }
        
        return wrapper
    
    return decorator
```

### 8. Create Audio Testing Utilities

Create specialized utilities for testing audio components:

```python
# tests/utils/audio_test_utils.py
import numpy as np
import soundfile as sf
import librosa
from typing import Tuple, List, Optional

def load_audio_file(file_path: str) -> Tuple[np.ndarray, int]:
    """
    Load an audio file.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    audio_data, sample_rate = sf.read(file_path)
    return audio_data, sample_rate

def detect_speech_segments(audio_data: np.ndarray, 
                          sample_rate: int, 
                          threshold: float = 0.01,
                          min_duration: float = 0.1) -> List[Tuple[float, float]]:
    """
    Detect speech segments in audio based on energy threshold.
    
    Args:
        audio_data: Audio data as numpy array
        sample_rate: Sample rate in Hz
        threshold: Energy threshold (0-1 range)
        min_duration: Minimum duration of a segment in seconds
        
    Returns:
        List of (start_time, end_time) tuples in seconds
    """
    # Convert to mono if needed
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Calculate energy
    energy = np.abs(audio_data)
    
    # Find segments above threshold
    is_speech = energy > threshold
    
    # Find segment boundaries
    changes = np.diff(is_speech.astype(int))
    segment_starts = np.where(changes == 1)[0]
    segment_ends = np.where(changes == -1)[0]
    
    # Handle edge cases
    if len(segment_starts) == 0:
        return []
    
    if is_speech[0]:
        segment_starts = np.insert(segment_starts, 0, 0)
    
    if is_speech[-1]:
        segment_ends = np.append(segment_ends, len(audio_data) - 1)
    
    # Convert to seconds and filter by minimum duration
    min_samples = int(min_duration * sample_rate)
    segments = []
    
    for start, end in zip(segment_starts, segment_ends):
        if end - start >= min_samples:
            start_time = start / sample_rate
            end_time = end / sample_rate
            segments.append((start_time, end_time))
    
    return segments

def extract_audio_features(audio_data: np.ndarray, sample_rate: int) -> Dict[str, np.ndarray]:
    """
    Extract common audio features for testing.
    
    Args:
        audio_data: Audio data as numpy array
        sample_rate: Sample rate in Hz
        
    Returns:
        Dictionary of audio features
    """
    # Convert to mono if needed
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Calculate spectral features
    try:
        mfccs = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=13)
        spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)
        zero_crossing_rate = librosa.feature.zero_crossing_rate(audio_data)
        
        return {
            "mfccs": mfccs,
            "spectral_centroid": spectral_centroid,
            "zero_crossing_rate": zero_crossing_rate
        }
    except Exception as e:
        print(f"Error extracting audio features: {e}")
        return {}

def compare_audio_features(features1: Dict[str, np.ndarray], 
                          features2: Dict[str, np.ndarray],
                          tolerance: float = 0.1) -> bool:
    """
    Compare two sets of audio features for similarity testing.
    
    Args:
        features1: First set of audio features
        features2: Second set of audio features
        tolerance: Similarity tolerance
        
    Returns:
        True if features are similar, False otherwise
    """
    if not features1 or not features2:
        return False
    
    # Check that both have the same features
    if set(features1.keys()) != set(features2.keys()):
        return False
    
    # Compare each feature
    for feature_name in features1:
        feat1 = features1[feature_name]
        feat2 = features2[feature_name]
        
        # Ensure same shape by truncating to smaller size
        min_shape = (min(feat1.shape[0], feat2.shape[0]), min(feat1.shape[1], feat2.shape[1]))
        feat1 = feat1[:min_shape[0], :min_shape[1]]
        feat2 = feat2[:min_shape[0], :min_shape[1]]
        
        # Calculate mean squared error
        mse = np.mean((feat1 - feat2) ** 2)
        
        # Compare with tolerance
        if mse > tolerance:
            return False
    
    return True
```

### 9. Create LangGraph Testing Utilities

Create utilities for testing LangGraph components:

```python
# tests/utils/langgraph_test_utils.py
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import MagicMock

class MockNode:
    """Mock node for testing LangGraph components."""
    
    def __init__(self, name: str, func: Optional[Callable] = None):
        self.name = name
        self.func = func or (lambda state: {**state, "touched_by": state.get("touched_by", []) + [name]})
        self.called = 0
        self.last_inputs = None
    
    def __call__(self, state):
        self.called += 1
        self.last_inputs = state
        return self.func(state)

def create_mock_graph():
    """Create a mock LangGraph for testing."""
    nodes = {
        "start": MockNode("start"),
        "process": MockNode("process"),
        "end": MockNode("end")
    }
    
    edges = {
        "start": "process",
        "process": "end"
    }
    
    # Simple mock of a LangGraph
    mock_graph = MagicMock()
    mock_graph.nodes = nodes
    mock_graph._edges = edges
    
    def mock_invoke(state, **kwargs):
        """Mock invoke method that simulates graph execution."""
        current = "start"
        result = state
        
        while current is not None:
            # Call current node
            node = nodes[current]
            result = node(result)
            
            # Get next node
            current = edges.get(current)
        
        return result
    
    mock_graph.invoke = mock_invoke
    
    return mock_graph

def assert_graph_flow(graph, initial_state, expected_touched_order):
    """
    Assert that a graph processes nodes in the expected order.
    
    Args:
        graph: The graph to test
        initial_state: Initial state to pass to the graph
        expected_touched_order: Expected order of nodes to be processed
        
    Returns:
        True if the flow matches expectations, False otherwise
    """
    result = graph.invoke(initial_state)
    
    # Check that all expected nodes were touched
    touched = result.get("touched_by", [])
    
    return touched == expected_touched_order
```

### 10. Create Basic Example Tests

Create example tests for each test type:

```python
# tests/unit/test_example_unit.py
"""Example unit tests to demonstrate testing approach."""

import pytest
from tests.mocks.mock_llm import MockLLM

def add_numbers(a, b):
    """Simple function to add two numbers."""
    return a + b

class TestExampleUnit:
    """Example unit tests."""
    
    def test_add_numbers(self):
        """Test the add_numbers function."""
        # Arrange
        a, b = 2, 3
        expected_sum = 5
        
        # Act
        result = add_numbers(a, b)
        
        # Assert
        assert result == expected_sum
    
    def test_with_mock_llm(self, mock_llm):
        """Test using the mock LLM fixture."""
        # Arrange
        prompt = "What's the weather like today?"
        
        # Act
        response = mock_llm.generate(prompt)
        
        # Assert
        assert "weather" in mock_llm.last_prompt
        assert "sunny" in response
        assert "75" in response

# tests/integration/test_example_integration.py
"""Example integration tests to demonstrate testing approach."""

import pytest
import numpy as np
from tests.utils.test_utils import create_test_audio, assert_audio_similar
from tests.mocks.mock_audio import MockAudioCapture
from tests.mocks.mock_tts import MockTTS

class TestExampleIntegration:
    """Example integration tests."""
    
    def test_audio_pipeline(self, test_audio_data, mock_audio_capture, mock_tts):
        """Test a simple audio pipeline."""
        # Arrange
        audio_data, sample_rate = test_audio_data
        mock_audio_capture.set_test_audio(audio_data)
        
        # Act
        # Simulate simple pipeline: capture -> process -> synthesize
        
        # Step 1: Start capture and read audio
        mock_audio_capture.start()
        success, captured_audio = mock_audio_capture.read()
        mock_audio_capture.stop()
        
        # Step 2: Simple "processing" - convert to text (mock)
        text = f"Audio signal with {len(captured_audio)} samples"
        
        # Step 3: TTS synthesis
        output_audio = mock_tts.synthesize(text)
        
        # Assert
        assert success
        assert len(captured_audio) > 0
        assert mock_tts.last_text == text
        assert len(output_audio) > 0

# tests/performance/test_example_performance.py
"""Example performance tests to demonstrate testing approach."""

import pytest
import time
import numpy as np
from tests.utils.performance_utils import performance_benchmark

@performance_benchmark(repeat=3)
def process_large_array(size):
    """Example function for performance testing."""
    arr = np.random.random((size, size))
    result = np.dot(arr, arr.T)
    return result.sum()

class TestExamplePerformance:
    """Example performance tests."""
    
    def test_array_processing_performance(self):
        """Test the performance of array processing."""
        # Run benchmark
        result = process_large_array(1000)
        
        # Assert performance criteria
        assert result["time"]["avg"] < 1.0, "Processing took too long"
        assert result["memory"]["avg"] < 500, "Processing used too much memory"
```

### 11. Create CI Configuration

Create a GitHub Actions workflow for CI:

```yaml
# .github/workflows/tests.yml
name: VANTA Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; else pip install -r requirements.txt; fi
        pip install pytest pytest-cov
        
    - name: Test with pytest
      run: |
        pytest --cov=./ --cov-report=xml
        
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
```

### 12. Create Documentation for Test Framework

Create a test documentation file:

```markdown
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
```

## Validation

This implementation should be validated by:

1. Verifying that the test directory structure is set up correctly:
   ```
   find tests -type d
   ```

2. Checking that the pytest configuration is valid:
   ```
   pytest --collect-only
   ```

3. Running the example tests to ensure they pass:
   ```
   pytest -xvs tests/unit/test_example_unit.py
   pytest -xvs tests/integration/test_example_integration.py
   pytest -xvs tests/performance/test_example_performance.py
   ```

4. Verifying that the test utilities can be imported without errors:
   ```
   python -c "from tests.utils import test_utils, audio_test_utils, model_utils, performance_utils, langgraph_test_utils"
   ```

5. Checking that the test documentation is comprehensive and clear.

## Notes and Considerations

- The implementation focuses on establishing a flexible and comprehensive testing framework that can support the various components of the VANTA system.

- The framework includes specialized utilities for audio testing, which is critical for the voice pipeline components.

- Mock objects are provided for all major external dependencies, enabling isolated unit testing.

- Performance testing tools are included to ensure the system meets latency and resource usage requirements.

- The framework is designed to be extensible, allowing additional test types and utilities to be added as needed.

- LangGraph-specific testing utilities are provided to simplify testing of workflow components.

- CI integration ensures tests are run automatically for all changes, promoting code quality and reliability.

- Test documentation provides clear guidelines for writing and running tests, promoting consistency across the codebase.