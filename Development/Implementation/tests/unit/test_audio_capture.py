# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification

"""Unit tests for audio capture module."""

import pytest
import numpy as np
import time
from unittest.mock import patch, MagicMock

from voice.audio.capture import AudioCapture

class TestAudioCapture:
    """Tests for AudioCapture class."""
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    def test_init(self, mock_pyaudio):
        """Test initialization of AudioCapture."""
        # Arrange & Act
        capture = AudioCapture(sample_rate=16000, chunk_size=1024, channels=1, buffer_seconds=3)
        
        # Assert
        assert capture.sample_rate == 16000
        assert capture.chunk_size == 1024
        assert capture.channels == 1
        assert capture.is_running is False
        assert len(capture.callbacks) == 0
        # Buffer size should be calculated based on buffer_seconds
        expected_buffer_length = int(3 * 16000 * 1 / 1024)
        assert capture.audio_buffer.maxlen == expected_buffer_length
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    def test_start_and_stop(self, mock_pyaudio):
        """Test starting and stopping audio capture."""
        # Arrange
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        capture = AudioCapture()
        
        # Act - Start
        result = capture.start()
        
        # Assert - Start
        assert result is True
        assert capture.is_running is True
        assert capture.pa is not None
        assert capture.stream is not None
        mock_pyaudio.return_value.open.assert_called_once()
        
        # Act - Stop
        capture.stop()
        
        # Assert - Stop
        assert capture.is_running is False
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_pyaudio.return_value.terminate.assert_called_once()
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    def test_get_latest_audio_empty(self, mock_pyaudio):
        """Test getting audio data when buffer is empty."""
        # Arrange
        capture = AudioCapture()
        
        # Act
        audio = capture.get_latest_audio()
        
        # Assert
        assert isinstance(audio, np.ndarray)
        assert audio.size == 0
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    def test_get_latest_audio_with_data(self, mock_pyaudio):
        """Test getting audio data when buffer has data."""
        # Arrange
        capture = AudioCapture()
        # Add some test data to the buffer
        test_data1 = np.ones(1000, dtype=np.int16)
        test_data2 = np.ones(1000, dtype=np.int16) * 2
        with capture.lock:
            capture.audio_buffer.append(test_data1)
            capture.audio_buffer.append(test_data2)
        
        # Act - Get all audio
        audio_all = capture.get_latest_audio()
        
        # Assert
        assert audio_all.size == 2000
        assert np.array_equal(audio_all[:1000], test_data1)
        assert np.array_equal(audio_all[1000:], test_data2)
        
        # Act - Get limited audio (1 second worth of samples assuming 1000Hz)
        # This test is simplified - in reality we'd calculate based on sample rate
        capture.sample_rate = 1000  # For easy calculation
        audio_limited = capture.get_latest_audio(seconds=1.0)
        
        # Assert - Should get the most recent chunk
        assert audio_limited.size == 1000
        assert np.array_equal(audio_limited, test_data2)
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    def test_callbacks(self, mock_pyaudio):
        """Test callback registration and invocation."""
        # Arrange
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        capture = AudioCapture()
        callback_data = []
        
        def test_callback(audio_data):
            callback_data.append(audio_data)
        
        # Act - Add callback
        capture.add_callback(test_callback)
        
        # Assert
        assert test_callback in capture.callbacks
        
        # Act - Simulate audio callback
        test_audio = np.ones(1000, dtype=np.int16)
        capture._audio_callback(test_audio.tobytes(), 1000, {}, 0)
        
        # Assert - Callback should be called with the audio data
        assert len(callback_data) == 1
        assert callback_data[0].size == 1000
        
        # Act - Remove callback
        capture.remove_callback(test_callback)
        
        # Assert
        assert test_callback not in capture.callbacks
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    def test_audio_callback_updates_stats(self, mock_pyaudio):
        """Test that audio callback updates stats correctly."""
        # Arrange
        capture = AudioCapture()
        
        # Act - Simulate audio callback with non-zero audio
        test_audio = np.ones(1000, dtype=np.int16) * 16384  # Half of max int16
        capture._audio_callback(test_audio.tobytes(), 1000, {}, 0)
        
        # Assert
        assert capture.stats["chunks_captured"] == 1
        assert capture.stats["audio_level_peak"] > 0
        assert capture.stats["audio_level_avg"] > 0
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    def test_get_stats(self, mock_pyaudio):
        """Test getting capture statistics."""
        # Arrange
        capture = AudioCapture()
        capture.stats["chunks_captured"] = 10
        capture.stats["audio_level_peak"] = 0.5
        
        # Act
        stats = capture.get_stats()
        
        # Assert
        assert stats["chunks_captured"] == 10
        assert stats["audio_level_peak"] == 0.5
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    def test_context_manager(self, mock_pyaudio):
        """Test using AudioCapture as a context manager."""
        # Arrange
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        # Act - Use as context manager
        with AudioCapture() as capture:
            # Assert - Should be started
            assert capture.is_running is True
            
        # Assert - Should be stopped after context
        assert capture.is_running is False
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_pyaudio.return_value.terminate.assert_called_once()