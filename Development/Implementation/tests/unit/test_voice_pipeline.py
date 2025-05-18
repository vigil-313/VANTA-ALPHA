# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification

"""Unit tests for voice pipeline integration."""

import os
import pytest
import numpy as np
import tempfile
import time
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from voice.pipeline import VoicePipeline
from voice.vad.detector import VoiceActivityDetector
from voice.vad.models.silero import SileroVAD
from voice.vad.activation import WakeWordDetector, ActivationManager, ActivationState, ActivationMode
from tests.utils.test_utils import create_test_audio, save_test_audio

class TestVoicePipeline:
    """Tests for VoicePipeline class."""
    
    @pytest.fixture
    def test_config_path(self):
        """Return path to test config file."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures", "test_config.yaml")
    
    @pytest.fixture
    def mock_streams(self):
        """Set up mock PyAudio streams."""
        mock_stream_playback = MagicMock()
        mock_stream_capture = MagicMock()
        return mock_stream_playback, mock_stream_capture
        
    @pytest.fixture
    def mock_vad(self):
        """Create a mock VAD detector."""
        mock_vad = MagicMock(spec=VoiceActivityDetector)
        mock_silero = MagicMock(spec=SileroVAD)
        
        # Configure the mock VAD to return appropriate values
        mock_vad.model = mock_silero
        mock_vad.model_type = "silero"
        mock_vad.sample_rate = 16000
        mock_vad.threshold = 0.5
        
        # Set up detect_speech method
        mock_vad.detect_speech.return_value = {
            "is_speech": False,
            "confidence": 0.1,
            "speech_segments": []
        }
        
        # Set up is_silence method
        mock_vad.is_silence.return_value = True
        
        return mock_vad
        
    @pytest.fixture
    def mock_wake_word_detector(self, mock_vad):
        """Create a mock wake word detector."""
        mock_wake_word = MagicMock(spec=WakeWordDetector)
        
        # Configure the mock wake word detector
        mock_wake_word.wake_word = "hey vanta"
        mock_wake_word.threshold = 0.7
        mock_wake_word.sample_rate = 16000
        mock_wake_word.vad = mock_vad
        
        # Set up detect method
        mock_wake_word.detect.return_value = {
            "detected": False,
            "confidence": 0.1,
            "timestamp_ms": 0
        }
        
        return mock_wake_word
        
    @pytest.fixture
    def mock_activation_manager(self, mock_vad, mock_wake_word_detector):
        """Create a mock activation manager."""
        mock_activation = MagicMock(spec=ActivationManager)
        
        # Configure the mock activation manager
        mock_activation.vad = mock_vad
        mock_activation.wake_word_detector = mock_wake_word_detector
        mock_activation.mode = ActivationMode.WAKE_WORD
        mock_activation.state = ActivationState.INACTIVE
        
        # Set up process_audio method
        mock_activation.process_audio.return_value = {
            "state": ActivationState.INACTIVE,
            "is_speech": False,
            "wake_word_detected": False,
            "should_process": False
        }
        
        return mock_activation
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_init(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, 
                 mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test initialization."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        # Act
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        
        # Assert
        assert pipeline.is_running is False
        assert pipeline.capture is not None
        assert pipeline.preprocessor is not None
        assert pipeline.playback is not None
        assert pipeline.state["is_listening"] is True
        assert pipeline.state["is_speaking"] is False
        assert len(pipeline.speech_detected_callbacks) == 0
        assert len(pipeline.speech_ended_callbacks) == 0
        assert len(pipeline.new_audio_callbacks) == 0
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_start_and_stop(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test starting and stopping the pipeline."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        
        # Act - Start
        pipeline.start()
        
        # Assert
        assert pipeline.is_running is True
        
        # Act - Stop
        pipeline.stop()
        
        # Assert
        assert pipeline.is_running is False
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_process_audio_callback(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test audio processing callback."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        
        # Add mock callback
        mock_callback = MagicMock()
        pipeline.add_new_audio_callback(mock_callback)
        
        # Create test audio
        audio_data = np.ones(1000, dtype=np.int16)
        
        # Act
        pipeline._process_audio(audio_data)
        
        # Assert
        mock_callback.assert_called_once()
        assert pipeline.state["latest_energy"] > 0
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_playback_event_handling(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test handling of playback events."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        
        # Act - Handle start event
        pipeline._handle_playback_started({})
        
        # Assert
        assert pipeline.state["is_speaking"] is True
        
        # Act - Handle stop event
        pipeline._handle_playback_completed({})
        
        # Assert
        assert pipeline.state["is_speaking"] is False
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_play_audio(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test audio playback."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        test_audio = np.ones(1000, dtype=np.int16)
        
        # Mock playback.play to return True
        pipeline.playback.play = MagicMock(return_value=True)
        
        # Act
        result = pipeline.play_audio(test_audio)
        
        # Assert
        assert result is True
        pipeline.playback.play.assert_called_once()
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_play_audio_file(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, temp_dir, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test playing audio from a file."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        
        # Mock the os.path.exists to return True for our test file
        with patch('os.path.exists', return_value=True):
            # Mock the playback.play_file method to return a playback ID
            pipeline.playback.play_file = MagicMock(return_value="test-playback-id")
            
            # Act
            result = pipeline.play_audio_file("/path/to/mock_file.wav")
            
            # Assert
            assert result == "test-playback-id"
            pipeline.playback.play_file.assert_called_once()
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_state_getters_setters(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test state getters and setters."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        
        # Act & Assert - Listening state
        assert pipeline.is_listening() is True
        pipeline.set_listening(False)
        assert pipeline.is_listening() is False
        
        # Act & Assert - Speaking state
        assert pipeline.is_speaking() is False
        pipeline.state["is_speaking"] = True
        assert pipeline.is_speaking() is True
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_get_stats(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test getting pipeline statistics."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        
        # Mock component stats
        pipeline.capture.get_stats = MagicMock(return_value={"capture_stat": 1})
        pipeline.preprocessor.get_stats = MagicMock(return_value={"preproc_stat": 2})
        pipeline.playback.get_stats = MagicMock(return_value={"playback_stat": 3})
        
        # Act
        stats = pipeline.get_stats()
        
        # Assert
        assert "state" in stats
        assert "capture" in stats
        assert "preprocessing" in stats
        assert "playback" in stats
        assert stats["capture"]["capture_stat"] == 1
        assert stats["preprocessing"]["preproc_stat"] == 2
        assert stats["playback"]["playback_stat"] == 3
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_get_devices(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test getting device lists."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        # Mock the list_devices methods
        mock_input_devices = [{"name": "Test Input Device", "index": 0}]
        mock_output_devices = [{"name": "Test Output Device", "index": 0}]
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        pipeline.capture.list_devices = MagicMock(return_value=mock_input_devices)
        pipeline.playback.list_devices = MagicMock(return_value=mock_output_devices)
        
        # Act
        devices = pipeline.get_devices()
        
        # Assert
        assert "input" in devices
        assert "output" in devices
        assert devices["input"] == mock_input_devices
        assert devices["output"] == mock_output_devices
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_update_config(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test updating configuration."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        
        # Initial config values
        initial_sample_rate = pipeline.config.config["capture"]["sample_rate"]
        
        # Act - Update configuration
        pipeline.update_config({
            "capture": {"sample_rate": 48000}
        })
        
        # Assert
        assert pipeline.config.config["capture"]["sample_rate"] == 48000
        assert pipeline.config.config["capture"]["sample_rate"] != initial_sample_rate
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_say(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test placeholder TTS function."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        pipeline = VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        )
        pipeline.play_audio = MagicMock(return_value=True)
        
        # Act
        result = pipeline.say("Hello world")
        
        # Assert
        assert result is True
        pipeline.play_audio.assert_called_once()
    
    @patch('voice.audio.capture.pyaudio.PyAudio')
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_context_manager(self, mock_pyaudio_playback, mock_pyaudio_capture, mock_streams, mock_vad, mock_wake_word_detector, mock_activation_manager, test_config_path):
        """Test using pipeline as a context manager."""
        # Arrange
        mock_stream_playback, mock_stream_capture = mock_streams
        mock_pyaudio_playback.return_value.open.return_value = mock_stream_playback
        mock_pyaudio_capture.return_value.open.return_value = mock_stream_capture
        
        # Act & Assert
        with VoicePipeline(
            config_file=test_config_path, 
            mock_vad=mock_vad,
            mock_wake_word=mock_wake_word_detector,
            mock_activation=mock_activation_manager
        ) as pipeline:
            assert pipeline.is_running is True
        
        # After exiting context
        assert pipeline.is_running is False