# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

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