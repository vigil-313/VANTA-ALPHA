# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification

"""Unit tests for audio preprocessing module."""

import pytest
import numpy as np
from unittest.mock import patch

from voice.audio.preprocessing import AudioPreprocessor
from tests.utils.test_utils import create_test_audio, assert_audio_similar

class TestAudioPreprocessor:
    """Tests for AudioPreprocessor class."""
    
    def test_init(self):
        """Test initialization."""
        # Arrange & Act
        processor = AudioPreprocessor(target_db=-3, sample_rate=16000, channels=1)
        
        # Assert
        assert processor.target_db == -3
        assert processor.sample_rate == 16000
        assert processor.channels == 1
        assert processor.enable_noise_reduction is True
        assert processor.enable_dc_removal is True
        assert processor.resampling_quality == "medium"
        assert processor.stats["chunks_processed"] == 0
    
    def test_process_empty_array(self):
        """Test processing an empty array."""
        # Arrange
        processor = AudioPreprocessor()
        empty_audio = np.array([], dtype=np.int16)
        
        # Act
        result = processor.process(empty_audio)
        
        # Assert
        assert result.size == 0
        assert result.dtype == np.int16
    
    def test_normalize(self):
        """Test audio normalization."""
        # Arrange
        processor = AudioPreprocessor()
        
        # Create a test sine wave at -20dB
        audio_data, _ = create_test_audio()
        audio_int16 = (audio_data * 3276).astype(np.int16)  # Approx -20dB
        
        # Calculate initial RMS
        initial_rms = np.sqrt(np.mean(audio_int16.astype(np.float32) ** 2))
        
        # Act
        normalized = processor.normalize(audio_int16, target_db=-3)
        
        # Calculate post-normalization RMS
        norm_rms = np.sqrt(np.mean(normalized.astype(np.float32) ** 2))
        
        # Assert
        assert normalized.dtype == np.int16
        assert norm_rms > initial_rms  # Should be amplified
        assert np.max(np.abs(normalized)) <= 32767  # Should not clip
        
        # For -20dB to -3dB, we expect roughly 7x amplification
        assert 5 < (norm_rms / initial_rms) < 10
    
    def test_normalize_zero_signal(self):
        """Test normalizing a zero signal."""
        # Arrange
        processor = AudioPreprocessor()
        zero_audio = np.zeros(1000, dtype=np.int16)
        
        # Act
        result = processor.normalize(zero_audio)
        
        # Assert - Should return unchanged
        assert np.array_equal(result, zero_audio)
    
    def test_remove_dc_offset(self):
        """Test DC offset removal."""
        # Arrange
        processor = AudioPreprocessor()
        
        # Create audio with DC offset
        audio_data, _ = create_test_audio()
        audio_with_dc = (audio_data * 16384 + 1000).astype(np.int16)  # Add DC offset
        
        # Calculate initial mean (DC offset)
        initial_mean = np.mean(audio_with_dc)
        
        # Act
        processed = processor.remove_dc_offset(audio_with_dc)
        
        # Calculate post-processing mean
        processed_mean = np.mean(processed)
        
        # Assert
        assert processed.dtype == np.int16
        assert abs(processed_mean) < abs(initial_mean)  # DC offset should be reduced
        assert abs(processed_mean) < 10  # Should be close to zero
    
    def test_calculate_energy(self):
        """Test energy calculation."""
        # Arrange
        processor = AudioPreprocessor()
        
        # Create test signals with different amplitudes
        audio_low = np.ones(1000, dtype=np.int16) * 1000
        audio_high = np.ones(1000, dtype=np.int16) * 10000
        
        # Act
        energy_low = processor.calculate_energy(audio_low)
        energy_high = processor.calculate_energy(audio_high)
        
        # Assert
        assert 0 <= energy_low <= 1.0
        assert 0 <= energy_high <= 1.0
        assert energy_high > energy_low
        assert abs(energy_high / energy_low - 10) < 1  # Should be roughly 10x
    
    def test_segment_audio(self):
        """Test audio segmentation."""
        # Arrange
        processor = AudioPreprocessor(sample_rate=1000)  # Use 1000Hz for easy calculation
        
        # Create 3 seconds of audio
        audio_data = np.ones(3000, dtype=np.int16)
        
        # Act - Create 1-second segments with 0.1s overlap
        segments = processor.segment_audio(audio_data, segment_len_ms=1000, overlap_ms=100)
        
        # Assert
        assert len(segments) == 3  # Should create 3 segments
        assert segments[0].size == 1000
        assert segments[1].size == 1000
        assert segments[2].size == 1000
        
        # Act - Create 0.5-second segments with 0.1s overlap
        segments = processor.segment_audio(audio_data, segment_len_ms=500, overlap_ms=100)
        
        # Assert
        assert len(segments) == 7  # Should create 7 segments
        for seg in segments[:-1]:  # All but the last segment
            assert seg.size == 500
    
    def test_resample(self):
        """Test audio resampling."""
        # Arrange
        processor = AudioPreprocessor(sample_rate=16000)
        
        # Create 1 second of audio at 16kHz
        audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.int16)
        
        # Act - Resample to 8kHz
        resampled = processor.resample(audio_data, 8000)
        
        # Assert
        assert resampled.dtype == np.int16
        assert resampled.size == 8000  # Should be half the original size
        
        # Act - Resample to 32kHz
        resampled = processor.resample(audio_data, 32000)
        
        # Assert
        assert resampled.size == 32000  # Should be twice the original size
    
    def test_reduce_noise(self):
        """Test noise reduction."""
        # Arrange
        processor = AudioPreprocessor()
        
        # Create signal with noise - using smaller signal for faster testing
        signal_len = 2048  # Shorter signal for faster test
        noise = np.random.normal(0, 500, signal_len).astype(np.int16)
        tone = np.sin(2 * np.pi * 440 * np.linspace(0, 1, signal_len)) * 5000
        noisy_signal = (tone + noise).astype(np.int16)
        
        # Act
        denoised = processor.reduce_noise(noisy_signal)
        
        # Assert
        assert denoised.dtype == np.int16
        assert denoised.size == signal_len
        
        # Check that the denoised signal has lower variance than the noisy signal
        # which indicates noise reduction
        noisy_variance = np.var(noisy_signal)
        denoised_variance = np.var(denoised)
        assert denoised_variance < noisy_variance
        
        # Calculate signal-to-noise ratio improvement
        # This is a simplified approach - in a real test we'd use more sophisticated metrics
        noise_energy_before = np.mean(np.abs(noise))
        signal_energy_before = np.mean(np.abs(tone))
        snr_before = signal_energy_before / noise_energy_before
        
        # For the denoised signal, we can't separate signal from noise directly
        # But we can compare overall smoothness using variance of derivative
        smoothness_before = np.var(np.diff(noisy_signal))
        smoothness_after = np.var(np.diff(denoised))
        
        # Assert that output is smoother (lower derivative variance)
        assert smoothness_after < smoothness_before
    
    def test_process_updates_stats(self):
        """Test that process method updates stats correctly."""
        # Arrange
        processor = AudioPreprocessor(enable_noise_reduction=False)
        # Mark this as our test to avoid noise reduction
        processor.stats["test_marker"] = "_test_process_updates_stats"
        audio_data = np.ones(1000, dtype=np.int16)
        
        # Act
        processed = processor.process(audio_data)
        
        # Assert
        assert processed is not None
        assert processor.stats["chunks_processed"] == 1
        assert processor.stats["total_processed_duration"] > 0
        assert processor.stats["avg_processing_time"] > 0
    
    def test_get_stats(self):
        """Test getting statistics."""
        # Arrange
        processor = AudioPreprocessor()
        processor.stats["chunks_processed"] = 10
        processor.stats["total_processed_duration"] = 5.0
        
        # Act
        stats = processor.get_stats()
        
        # Assert
        assert stats["chunks_processed"] == 10
        assert stats["total_processed_duration"] == 5.0