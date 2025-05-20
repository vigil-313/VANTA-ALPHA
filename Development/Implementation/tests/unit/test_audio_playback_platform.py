# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer

"""Unit tests for audio playback module with platform abstraction."""

import pytest
import numpy as np
import time
import threading
from unittest.mock import patch, MagicMock, call, ANY

from voice.audio.playback import AudioPlayback
from core.platform.interface import PlatformAudioPlayback


class MockPlatformAudioPlayback(MagicMock):
    """Mock implementation of PlatformAudioPlayback for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(spec=PlatformAudioPlayback, *args, **kwargs)
        self.initialize.return_value = True
        self.start_playback.return_value = True
        self.stop_playback.return_value = None
        self.get_available_devices.return_value = [
            {
                "id": "mock_device_1", 
                "name": "Mock Device 1", 
                "channels": 2,
                "default_sample_rate": 44100,
                "is_default": True
            },
            {
                "id": "mock_device_2", 
                "name": "Mock Device 2", 
                "channels": 1,
                "default_sample_rate": 16000,
                "is_default": False
            }
        ]
        self.select_device.return_value = True
        self.get_capabilities.return_value = {
            "sample_rates": [8000, 16000, 44100, 48000],
            "bit_depths": [16],
            "channels": [1, 2],
            "api": "MockAPI"
        }
        self._next_playback_id = 1
        
    def play_audio(self, audio_data):
        """Simulate playing audio data."""
        playback_id = self._next_playback_id
        self._next_playback_id += 1
        
        # In a real implementation, we'd start a thread to play the audio,
        # but for testing we just return immediately
        return playback_id
    
    def stop_audio(self, playback_id):
        """Simulate stopping audio playback."""
        return True


class TestAudioPlaybackPlatform:
    """Tests for AudioPlayback class with platform abstraction."""
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_init(self, mock_factory_create):
        """Test initialization of AudioPlayback with platform abstraction."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        # Act
        playback = AudioPlayback(sample_rate=24000, channels=1, buffer_size=1024)
        
        # Assert
        assert playback.sample_rate == 24000
        assert playback.channels == 1
        assert playback.buffer_size == 1024
        assert playback.is_running is False
        assert playback._volume == 0.8  # Default volume
        
        # Verify platform specific calls
        mock_factory_create.assert_called_once()
        mock_platform.initialize.assert_called_once_with(
            sample_rate=24000, channels=1, buffer_size=1024
        )
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_init_with_device_id(self, mock_factory_create):
        """Test initialization with device ID."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        # Act
        playback = AudioPlayback(device_id="test_device")
        
        # Assert
        mock_platform.select_device.assert_called_once_with("test_device")
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_init_failure(self, mock_factory_create):
        """Test handling of initialization failures."""
        # Arrange - Factory returns None
        mock_factory_create.return_value = None
        
        # Act & Assert - Should raise RuntimeError
        with pytest.raises(RuntimeError, match="No suitable audio playback implementation available"):
            AudioPlayback()
        
        # Arrange - Platform initialization fails
        mock_platform = MockPlatformAudioPlayback()
        mock_platform.initialize.return_value = False
        mock_factory_create.return_value = mock_platform
        
        # Act & Assert - Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Audio playback initialization failed"):
            AudioPlayback()
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_start_and_stop(self, mock_factory_create):
        """Test starting and stopping audio playback."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        
        # Act - Start
        result = playback.start()
        
        # Assert - Start
        assert result is True
        assert playback.is_running is True
        mock_platform.start_playback.assert_called_once()
        
        # Act - Start again (should return False)
        mock_platform.reset_mock()
        result = playback.start()
        
        # Assert - Already running
        assert result is False
        mock_platform.start_playback.assert_not_called()
        
        # Act - Stop
        mock_platform.reset_mock()
        playback.stop()
        
        # Assert - Stop
        assert playback.is_running is False
        mock_platform.stop_playback.assert_called_once()
        
        # Act - Stop again (should not call platform_playback.stop_playback again)
        mock_platform.reset_mock()
        playback.stop()
        
        # Assert - Already stopped
        mock_platform.stop_playback.assert_not_called()
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_play_audio(self, mock_factory_create):
        """Test playing audio data."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        playback.start()
        
        test_audio = np.ones(16000, dtype=np.int16)  # 1 second of test audio at 16kHz
        
        # Act
        playback_id = playback.play(test_audio)
        
        # Assert
        assert playback_id is not None
        assert playback.current_playback_id == playback_id
        mock_platform.play_audio.assert_called_once()
        
        # Let the playback complete
        playback.playback_thread.join(timeout=0.5)
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_play_audio_with_priority(self, mock_factory_create):
        """Test playing audio with different priorities."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        playback.start()
        
        test_audio1 = np.ones(8000, dtype=np.int16)  # 0.5 second at 16kHz
        test_audio2 = np.ones(8000, dtype=np.int16) * 2  # 0.5 second at 16kHz
        
        # Act - Play with normal priority
        playback_id1 = playback.play(test_audio1)
        
        # Wait for audio to start playing
        time.sleep(0.1)
        
        # Act - Play with higher priority (should interrupt)
        playback_id2 = playback.play(test_audio2, priority=5)
        
        # Let the playback complete
        playback.playback_thread.join(timeout=0.5)
        
        # Assert
        assert playback_id1 is not None
        assert playback_id2 is not None
        assert playback.current_playback_id == playback_id2  # Should be playing the higher priority audio
        assert playback.stats["playbacks_interrupted"] >= 1  # Should have interrupted at least once
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_stop_current_playback(self, mock_factory_create):
        """Test stopping the current playback."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        playback.start()
        
        test_audio = np.ones(48000, dtype=np.int16)  # 2 seconds at 24kHz
        
        # Act - Play and then stop immediately
        playback_id = playback.play(test_audio)
        time.sleep(0.1)  # Let the playback start
        result = playback.stop_current()
        
        # Assert
        assert result is True
        assert playback.is_playing is False
        assert playback.current_playback_id is None
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_clear_queue(self, mock_factory_create):
        """Test clearing the playback queue."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        playback.start()
        
        test_audio1 = np.ones(8000, dtype=np.int16)
        test_audio2 = np.ones(8000, dtype=np.int16) * 2
        test_audio3 = np.ones(8000, dtype=np.int16) * 3
        
        # Act - Queue multiple audio segments
        playback.play(test_audio1, block=False)
        playback.play(test_audio2, block=False)
        playback.play(test_audio3, block=False)
        
        # Let the first one start playing
        time.sleep(0.1)
        
        # Act - Clear the queue
        playback.clear_queue()
        
        # Assert
        assert playback.queue.empty()
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_get_stats(self, mock_factory_create):
        """Test getting playback statistics."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        playback.start()
        
        # Set some stats
        playback.stats["playbacks_completed"] = 5
        playback.stats["playbacks_interrupted"] = 2
        playback.stats["start_time"] = time.time() - 30  # 30 seconds ago
        
        # Act
        stats = playback.get_stats()
        
        # Assert
        assert stats["playbacks_completed"] == 5
        assert stats["playbacks_interrupted"] == 2
        assert "uptime_seconds" in stats
        assert stats["uptime_seconds"] >= 29  # Allow for small timing differences
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_register_event_handler(self, mock_factory_create):
        """Test registering event handlers."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        
        events_received = []
        
        def event_handler(event_type, event_data):
            events_received.append((event_type, event_data))
        
        # Act - Register handler
        playback.register_event_handler(AudioPlayback.EVENT_PLAYBACK_STARTED, event_handler)
        playback.register_event_handler(AudioPlayback.EVENT_PLAYBACK_COMPLETE, event_handler)
        
        # Act - Trigger events
        playback.start()
        test_audio = np.ones(8000, dtype=np.int16)
        playback_id = playback.play(test_audio)
        
        # Let the playback complete
        playback.playback_thread.join(timeout=0.5)
        
        # Assert
        assert len(events_received) >= 2  # Should have received at least start and complete events
        
        # Check for start event
        start_events = [e for e in events_received if e[0] == AudioPlayback.EVENT_PLAYBACK_STARTED]
        assert len(start_events) >= 1
        assert start_events[0][1]["playback_id"] == playback_id
        
        # Check for complete event
        complete_events = [e for e in events_received if e[0] == AudioPlayback.EVENT_PLAYBACK_COMPLETE]
        assert len(complete_events) >= 1
        assert complete_events[0][1]["playback_id"] == playback_id
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_list_devices(self, mock_factory_create):
        """Test listing available devices."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        
        # Act
        devices = playback.list_devices()
        
        # Assert
        assert len(devices) == 2
        assert devices[0]["id"] == "mock_device_1"
        assert devices[1]["id"] == "mock_device_2"
        mock_platform.get_available_devices.assert_called_once()
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_select_device(self, mock_factory_create):
        """Test selecting a device."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        
        # Act
        result = playback.select_device("test_device")
        
        # Assert
        assert result is True
        mock_platform.select_device.assert_called_once_with("test_device")
    
    @patch('core.platform.factory.audio_playback_factory.create')
    def test_set_volume(self, mock_factory_create):
        """Test setting the volume."""
        # Arrange
        mock_platform = MockPlatformAudioPlayback()
        mock_factory_create.return_value = mock_platform
        
        playback = AudioPlayback()
        
        # Act - Set valid volume
        playback.set_volume(0.5)
        
        # Assert
        assert playback._volume == 0.5
        
        # Act - Set volume too high (should clamp to 1.0)
        playback.set_volume(1.5)
        
        # Assert
        assert playback._volume == 1.0
        
        # Act - Set volume too low (should clamp to 0.0)
        playback.set_volume(-0.5)
        
        # Assert
        assert playback._volume == 0.0