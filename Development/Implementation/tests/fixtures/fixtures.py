# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

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