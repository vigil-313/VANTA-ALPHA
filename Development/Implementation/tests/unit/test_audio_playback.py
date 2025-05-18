# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification

"""Unit tests for audio playback module."""

import os
import pytest
import numpy as np
import threading
import time
from unittest.mock import patch, MagicMock

from voice.audio.playback import AudioPlayback
from tests.utils.test_utils import create_test_audio

class TestAudioPlayback:
    """Tests for AudioPlayback class."""
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_init(self, mock_pyaudio):
        """Test initialization."""
        # Arrange & Act
        playback = AudioPlayback(sample_rate=24000, channels=1, buffer_size=1024)
        
        # Assert
        assert playback.sample_rate == 24000
        assert playback.channels == 1
        assert playback.buffer_size == 1024
        assert playback._volume == 0.8
        assert playback.is_playing is False
        assert playback.current_playback_id is None
        assert playback.queue.empty()
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_start_and_stop(self, mock_pyaudio):
        """Test starting and stopping playback."""
        # Arrange
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        playback = AudioPlayback()
        
        # Act - Start
        result = playback.start()
        
        # Assert - Start
        assert result is True
        assert playback.stream is not None
        assert playback.pa is not None
        assert playback.playback_thread is not None
        assert playback.playback_thread.is_alive()
        
        # Wait a moment for thread to fully start
        time.sleep(0.1)
        
        # Act - Stop
        playback.stop()
        
        # Assert - Stop
        assert playback.should_stop is True
        # Wait for thread to terminate
        playback.playback_thread.join(timeout=1.0)
        assert not playback.playback_thread.is_alive()
        mock_stream.stop_stream.assert_called()
        mock_stream.close.assert_called()
        mock_pyaudio.return_value.terminate.assert_called()
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_play(self, mock_pyaudio):
        """Test queueing audio for playback."""
        # Arrange
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        playback = AudioPlayback()
        playback.start()
        
        # Create test audio
        test_audio = np.ones(1000, dtype=np.int16)
        
        # Act
        playback_id = playback.play(test_audio)
        
        # Assert
        assert isinstance(playback_id, str)
        assert len(playback_id) > 0
        assert not playback.queue.empty()
        
        # Clean up
        playback.stop()
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_play_with_priority(self, mock_pyaudio):
        """Test playing audio with different priorities."""
        # Arrange
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        playback = AudioPlayback()
        playback.start()
        
        # Create test audio
        audio_low = np.ones(1000, dtype=np.int16)
        audio_high = np.ones(1000, dtype=np.int16) * 2
        
        # Act - Queue low priority first, then high priority
        low_id = playback.play(audio_low, priority=0)
        high_id = playback.play(audio_high, priority=10)
        
        # Get first item from queue (should be high priority)
        priority, playback_id, audio = playback.queue.get()
        
        # Assert
        assert playback_id == high_id  # High priority should be first
        assert priority == -10  # Priority is inverted internally
        assert np.array_equal(audio, audio_high)
        
        # Clean up
        playback.stop()
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_stop_playback(self, mock_pyaudio):
        """Test stopping playback."""
        # Arrange
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        playback = AudioPlayback()
        playback.start()
        
        # Create test audio and queue it
        test_audio = np.ones(1000, dtype=np.int16)
        playback_id = playback.play(test_audio)
        
        # Set current playback ID
        playback.current_playback_id = playback_id
        
        # Register a mock event listener
        event_listener = MagicMock()
        playback.add_event_listener(
            AudioPlayback.EVENT_PLAYBACK_STOPPED, 
            event_listener
        )
        
        # Act
        playback.stop_playback()
        
        # Assert
        assert playback.current_playback_id is None
        assert playback.queue.empty()
        event_listener.assert_called()
        
        # Clean up
        playback.stop()
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_set_volume(self, mock_pyaudio):
        """Test volume control."""
        # Arrange
        playback = AudioPlayback()
        
        # Act
        playback.set_volume(0.5)
        
        # Assert
        assert playback._volume == 0.5
        
        # Act - Test clipping
        playback.set_volume(1.5)
        
        # Assert
        assert playback._volume == 1.0
        
        # Act - Test negative volume
        playback.set_volume(-0.5)
        
        # Assert
        assert playback._volume == 0.0
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_apply_volume(self, mock_pyaudio):
        """Test applying volume to audio data."""
        # Arrange
        playback = AudioPlayback()
        test_audio = np.ones(1000, dtype=np.int16) * 10000
        
        # Act
        processed = playback._apply_volume(test_audio, 0.5)
        
        # Assert
        assert processed.dtype == np.int16
        assert np.all(processed == 5000)  # Should be half volume
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_event_listeners(self, mock_pyaudio):
        """Test event listener management."""
        # Arrange
        playback = AudioPlayback()
        callback = MagicMock()
        
        # Act - Add listener
        result = playback.add_event_listener(
            AudioPlayback.EVENT_PLAYBACK_STARTED, 
            callback
        )
        
        # Assert
        assert result is True
        assert callback in playback.event_listeners[AudioPlayback.EVENT_PLAYBACK_STARTED]
        
        # Act - Emit event
        playback._emit_event(AudioPlayback.EVENT_PLAYBACK_STARTED, 
                           {"playback_id": "test", "duration": 1.0})
        
        # Assert
        callback.assert_called_once()
        assert "timestamp" in callback.call_args[0][0]
        assert "playback_id" in callback.call_args[0][0]
        
        # Act - Remove listener
        result = playback.remove_event_listener(
            AudioPlayback.EVENT_PLAYBACK_STARTED, 
            callback
        )
        
        # Assert
        assert result is True
        assert callback not in playback.event_listeners[AudioPlayback.EVENT_PLAYBACK_STARTED]
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_get_stats(self, mock_pyaudio):
        """Test getting statistics."""
        # Arrange
        playback = AudioPlayback()
        playback.stats["playbacks_completed"] = 5
        playback.stats["total_playback_duration"] = 10.0
        
        # Act
        stats = playback.get_stats()
        
        # Assert
        assert stats["playbacks_completed"] == 5
        assert stats["total_playback_duration"] == 10.0
        assert "is_playing" in stats
        assert "queue_size" in stats
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_is_queue_empty(self, mock_pyaudio):
        """Test queue empty check."""
        # Arrange
        playback = AudioPlayback()
        
        # Assert - Should be empty initially
        assert playback.is_queue_empty() is True
        
        # Act - Add an item
        test_audio = np.ones(1000, dtype=np.int16)
        playback.play(test_audio)
        
        # Assert - Should not be empty now
        assert playback.is_queue_empty() is False
    
    @patch('voice.audio.playback.pyaudio.PyAudio')
    def test_context_manager(self, mock_pyaudio):
        """Test using as context manager."""
        # Arrange
        mock_stream = MagicMock()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        # Act & Assert - Context manager should start and stop
        with AudioPlayback() as playback:
            assert playback.playback_thread is not None
            assert playback.playback_thread.is_alive()
        
        # Assert - Should be stopped after context
        assert playback.stream is None
        assert playback.pa is None