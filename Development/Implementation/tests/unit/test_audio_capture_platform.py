# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer

"""Unit tests for audio capture module with platform abstraction."""

import pytest
import numpy as np
import time
from unittest.mock import patch, MagicMock, call

from voice.audio.capture import AudioCapture
from core.platform.interface import PlatformAudioCapture


class MockPlatformAudioCapture(MagicMock):
    """Mock implementation of PlatformAudioCapture for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(spec=PlatformAudioCapture, *args, **kwargs)
        self.initialize.return_value = True
        self.start_capture.return_value = True
        self.stop_capture.return_value = None
        self.get_available_devices.return_value = [
            {
                "id": "mock_device_1", 
                "name": "Mock Device 1", 
                "channels": 1,
                "default_sample_rate": 16000,
                "is_default": True
            },
            {
                "id": "mock_device_2", 
                "name": "Mock Device 2", 
                "channels": 2,
                "default_sample_rate": 44100,
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
        
        # Store the registered callback for simulation
        self._callback_fn = None
        
    def register_callback(self, callback_fn):
        """Register callback function to receive audio data."""
        self._callback_fn = callback_fn
        
    def simulate_audio_data(self, audio_data):
        """Simulate receiving audio data from the platform."""
        if self._callback_fn is not None:
            self._callback_fn(audio_data)


class TestAudioCapturePlatform:
    """Tests for AudioCapture class with platform abstraction."""
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_init(self, mock_factory_create):
        """Test initialization of AudioCapture with platform abstraction."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        # Act
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
        
        # Verify platform specific calls
        mock_factory_create.assert_called_once()
        mock_platform.initialize.assert_called_once_with(
            sample_rate=16000, channels=1, chunk_size=1024
        )
        
        # Verify callback registration
        assert mock_platform._callback_fn == capture._on_audio_data
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_init_with_device_id(self, mock_factory_create):
        """Test initialization with device ID."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        # Act
        capture = AudioCapture(device_id="test_device")
        
        # Assert
        mock_platform.select_device.assert_called_once_with("test_device")
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_init_failure(self, mock_factory_create):
        """Test handling of initialization failures."""
        # Arrange - Factory returns None
        mock_factory_create.return_value = None
        
        # Act & Assert - Should raise RuntimeError
        with pytest.raises(RuntimeError, match="No suitable audio capture implementation available"):
            AudioCapture()
        
        # Arrange - Platform initialization fails
        mock_platform = MockPlatformAudioCapture()
        mock_platform.initialize.return_value = False
        mock_factory_create.return_value = mock_platform
        
        # Act & Assert - Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Audio capture initialization failed"):
            AudioCapture()
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_start_and_stop(self, mock_factory_create):
        """Test starting and stopping audio capture."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        capture = AudioCapture()
        
        # Act - Start
        result = capture.start()
        
        # Assert - Start
        assert result is True
        assert capture.is_running is True
        mock_platform.start_capture.assert_called_once()
        
        # Act - Start again (should return False)
        mock_platform.reset_mock()
        result = capture.start()
        
        # Assert - Already running
        assert result is False
        mock_platform.start_capture.assert_not_called()
        
        # Act - Stop
        mock_platform.reset_mock()
        capture.stop()
        
        # Assert - Stop
        assert capture.is_running is False
        mock_platform.stop_capture.assert_called_once()
        
        # Act - Stop again (should not call platform_capture.stop_capture again)
        mock_platform.reset_mock()
        capture.stop()
        
        # Assert - Already stopped
        mock_platform.stop_capture.assert_not_called()
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_get_latest_audio_empty(self, mock_factory_create):
        """Test getting audio data when buffer is empty."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        capture = AudioCapture()
        
        # Act
        audio = capture.get_latest_audio()
        
        # Assert
        assert isinstance(audio, np.ndarray)
        assert audio.size == 0
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_get_latest_audio_with_data(self, mock_factory_create):
        """Test getting audio data when buffer has data."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
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
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_callbacks(self, mock_factory_create):
        """Test callback registration and invocation."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        capture = AudioCapture()
        callback_data = []
        
        def test_callback(audio_data):
            callback_data.append(audio_data)
        
        # Act - Add callback
        capture.add_callback(test_callback)
        
        # Assert
        assert test_callback in capture.callbacks
        
        # Act - Simulate audio data from platform
        test_audio = np.ones(1000, dtype=np.int16)
        mock_platform.simulate_audio_data(test_audio)
        
        # Assert - Callback should be called with the audio data
        assert len(callback_data) == 1
        assert np.array_equal(callback_data[0], test_audio)
        
        # Act - Remove callback
        capture.remove_callback(test_callback)
        
        # Assert
        assert test_callback not in capture.callbacks
        
        # Act - Simulate more audio data
        callback_data.clear()
        mock_platform.simulate_audio_data(test_audio)
        
        # Assert - Callback should not be called
        assert len(callback_data) == 0
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_on_audio_data_updates_stats(self, mock_factory_create):
        """Test that _on_audio_data updates stats correctly."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        capture = AudioCapture()
        
        # Act - Simulate audio data with non-zero values
        test_audio = np.ones(1000, dtype=np.int16) * 16384  # Half of max int16
        mock_platform.simulate_audio_data(test_audio)
        
        # Assert
        assert capture.stats["chunks_captured"] == 1
        assert capture.stats["audio_level_peak"] > 0
        assert capture.stats["audio_level_avg"] > 0
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_on_audio_data_exception_handling(self, mock_factory_create):
        """Test that _on_audio_data handles exceptions gracefully."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        capture = AudioCapture()
        
        # Add a callback that raises an exception
        def bad_callback(audio_data):
            raise ValueError("Test exception")
        
        capture.add_callback(bad_callback)
        
        # Act - Simulate audio data
        test_audio = np.ones(1000, dtype=np.int16)
        mock_platform.simulate_audio_data(test_audio)
        
        # Assert - Should increment dropped chunks
        assert capture.stats["dropped_chunks"] == 0  # The main processing succeeded
        # The callback error is caught separately in _notify_callbacks
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_get_stats(self, mock_factory_create):
        """Test getting capture statistics."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        capture = AudioCapture()
        capture.stats["chunks_captured"] = 10
        capture.stats["audio_level_peak"] = 0.5
        capture.stats["start_time"] = time.time() - 30  # 30 seconds ago
        
        # Act
        stats = capture.get_stats()
        
        # Assert
        assert stats["chunks_captured"] == 10
        assert stats["audio_level_peak"] == 0.5
        assert "uptime_seconds" in stats
        assert stats["uptime_seconds"] >= 29  # Allow for small timing differences
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_list_devices(self, mock_factory_create):
        """Test listing available devices."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        capture = AudioCapture()
        
        # Act
        devices = capture.list_devices()
        
        # Assert
        assert len(devices) == 2
        assert devices[0]["id"] == "mock_device_1"
        assert devices[1]["id"] == "mock_device_2"
        mock_platform.get_available_devices.assert_called_once()
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_select_device(self, mock_factory_create):
        """Test selecting a device."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        capture = AudioCapture()
        
        # Act
        result = capture.select_device("test_device")
        
        # Assert
        assert result is True
        mock_platform.select_device.assert_called_once_with("test_device")
    
    @patch('core.platform.factory.audio_capture_factory.create')
    def test_context_manager(self, mock_factory_create):
        """Test using AudioCapture as a context manager."""
        # Arrange
        mock_platform = MockPlatformAudioCapture()
        mock_factory_create.return_value = mock_platform
        
        # Act - Use as context manager
        with AudioCapture() as capture:
            # Assert - Should be started
            assert capture.is_running is True
            mock_platform.start_capture.assert_called_once()
            
        # Assert - Should be stopped after context
        assert capture.is_running is False
        mock_platform.stop_capture.assert_called_once()