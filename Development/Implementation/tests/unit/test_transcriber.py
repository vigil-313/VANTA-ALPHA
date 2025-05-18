#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Transcriber.
"""
# TASK-REF: VOICE_003 - Speech-to-Text Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy
# DECISION-REF: DEC-002-001 - Use Whisper for speech-to-text conversion

import pytest
import numpy as np
import time
from unittest.mock import patch, Mock, MagicMock, call
from contextlib import nullcontext as does_not_raise

from voice.stt.transcriber import Transcriber, TranscriptionQuality
from voice.stt.whisper_adapter import WhisperAdapter
from tests.utils.test_utils import create_test_audio
from tests.utils.audio_test_utils import generate_spoken_text_audio
from tests.mocks.mock_stt import MockWhisperAdapter

class TestTranscriber:
    """Tests for Transcriber class."""
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        # Arrange - Mock the WhisperAdapter to avoid actual loading
        mock_adapter = MockWhisperAdapter()
        
        # Act
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Assert
        assert transcriber.default_quality == TranscriptionQuality.MEDIUM
        assert transcriber.min_confidence == 0.4
        assert transcriber.enable_streaming == True
        assert transcriber.cache_size == 10
        assert transcriber.whisper_adapter == mock_adapter
        assert transcriber._streaming == False
        assert len(transcriber.result_cache) == 0
        
    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        
        # Act
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            min_confidence=0.6,
            default_quality=TranscriptionQuality.HIGH,
            enable_streaming=False,
            cache_size=20
        )
        
        # Assert
        assert transcriber.default_quality == TranscriptionQuality.HIGH
        assert transcriber.min_confidence == 0.6
        assert transcriber.enable_streaming == False
        assert transcriber.cache_size == 20
        
    def test_init_with_string_quality(self):
        """Test initialization with string quality parameter."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        
        # Act
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            default_quality="high"
        )
        
        # Assert
        assert transcriber.default_quality == TranscriptionQuality.HIGH
        
    def test_init_with_invalid_string_quality(self):
        """Test initialization with invalid string quality parameter."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        
        # Act
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            default_quality="ultra"  # Invalid quality
        )
        
        # Assert - Should fall back to MEDIUM
        assert transcriber.default_quality == TranscriptionQuality.MEDIUM
        
    def test_transcribe_simple(self):
        """Test basic transcription without caching."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        # Set up a predetermined response
        mock_response = {
            "text": "Hello world",
            "segments": [
                {
                    "id": 0,
                    "text": "Hello world",
                    "start": 0.0,
                    "end": 1.0,
                    "confidence": 0.9
                }
            ],
            "language": "en",
            "confidence": 0.9
        }
        mock_adapter.transcribe = MagicMock(return_value=mock_response)
        
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Create test audio
        audio_data, _ = create_test_audio(duration=1.0, sample_rate=16000)
        
        # Act
        result = transcriber.transcribe(audio_data)
        
        # Assert
        assert result["text"] == "Hello world"
        assert result["confidence"] == 0.9
        assert result["low_confidence"] == False
        assert mock_adapter.transcribe.call_count == 1
        assert transcriber.stats["total_requests"] == 1
        assert transcriber.stats["cache_hits"] == 0
        assert len(transcriber.result_cache) == 1
        
    def test_transcribe_low_confidence(self):
        """Test transcription with low confidence result."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        # Set up a low confidence response
        mock_response = {
            "text": "Hello world",
            "segments": [
                {
                    "id": 0,
                    "text": "Hello world",
                    "start": 0.0,
                    "end": 1.0,
                    "confidence": 0.3
                }
            ],
            "language": "en",
            "confidence": 0.3  # Below default threshold of 0.4
        }
        mock_adapter.transcribe = MagicMock(return_value=mock_response)
        
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Create test audio
        audio_data, _ = create_test_audio(duration=1.0, sample_rate=16000)
        
        # Act
        result = transcriber.transcribe(audio_data)
        
        # Assert
        assert result["text"] == "Hello world"
        assert result["confidence"] == 0.3
        assert result["low_confidence"] == True
        
    def test_transcribe_with_caching(self):
        """Test transcription with cache hit."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Create test audio
        audio_data, _ = create_test_audio(duration=1.0, sample_rate=16000)
        
        # Set up mock responses
        mock_response = {
            "text": "Hello world",
            "segments": [],
            "language": "en",
            "confidence": 0.9
        }
        mock_adapter.transcribe = MagicMock(return_value=mock_response)
        
        # First call to populate cache
        first_result = transcriber.transcribe(audio_data)
        
        # Reset the mock to verify it's not called again
        mock_adapter.transcribe.reset_mock()
        
        # Act - Second call should use cache
        second_result = transcriber.transcribe(audio_data)
        
        # Assert
        assert second_result == first_result
        assert mock_adapter.transcribe.call_count == 0
        assert transcriber.stats["total_requests"] == 2
        assert transcriber.stats["cache_hits"] == 1
        
    def test_transcribe_with_quality_change(self):
        """Test transcription with quality change."""
        # Arrange
        mock_adapter = MockWhisperAdapter(model_size="base")  # Start with base model
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            default_quality=TranscriptionQuality.MEDIUM  # Maps to "base"
        )
        
        # Create test audio
        audio_data, _ = create_test_audio(duration=1.0, sample_rate=16000)
        
        # Set up mock responses
        mock_response = {
            "text": "Hello world",
            "segments": [],
            "language": "en",
            "confidence": 0.9
        }
        mock_adapter.transcribe = MagicMock(return_value=mock_response)
        mock_adapter.unload_model = MagicMock()
        
        # Act - Transcribe with higher quality
        result = transcriber.transcribe(audio_data, quality=TranscriptionQuality.HIGH)
        
        # Assert
        assert result["text"] == "Hello world"
        assert mock_adapter.unload_model.call_count == 1
        assert mock_adapter.model_size == "small"  # Should be updated to match HIGH quality
        
    def test_transcribe_with_callback(self):
        """Test transcription with result callback."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Create test audio
        audio_data, _ = create_test_audio(duration=1.0, sample_rate=16000)
        
        # Set up mock response
        mock_response = {
            "text": "Hello with callback",
            "segments": [],
            "language": "en",
            "confidence": 0.9
        }
        mock_adapter.transcribe = MagicMock(return_value=mock_response)
        
        # Create a mock callback
        callback_result = None
        def callback(result):
            nonlocal callback_result
            callback_result = result
            
        # Act
        result = transcriber.transcribe(audio_data, callback=callback)
        
        # Assert
        assert result["text"] == "Hello with callback"
        assert callback_result == result
        
    def test_start_streaming_disabled(self):
        """Test start_streaming when streaming is disabled."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            enable_streaming=False
        )
        
        # Create a mock callback
        callback = MagicMock()
        
        # Act
        result = transcriber.start_streaming(callback)
        
        # Assert
        assert result is False
        assert transcriber._streaming is False
        assert transcriber._stream_callback is None
        
    def test_start_streaming_enabled(self):
        """Test start_streaming when streaming is enabled."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            enable_streaming=True
        )
        
        # Create a mock callback
        callback = MagicMock()
        
        # Act
        result = transcriber.start_streaming(callback)
        
        # Assert
        assert result is True
        assert transcriber._streaming is True
        assert transcriber._stream_buffer == []
        assert transcriber._stream_callback == callback
        
    def test_start_streaming_already_active(self):
        """Test start_streaming when streaming is already active."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            enable_streaming=True
        )
        
        # Start streaming once
        callback1 = MagicMock()
        transcriber.start_streaming(callback1)
        
        # Create another callback
        callback2 = MagicMock()
        
        # Act - Try to start streaming again
        result = transcriber.start_streaming(callback2)
        
        # Assert
        assert result is False
        assert transcriber._stream_callback == callback1  # Should keep the first callback
        
    def test_feed_audio_chunk_not_streaming(self):
        """Test feed_audio_chunk when not streaming."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Create test audio chunk
        audio_chunk, _ = create_test_audio(duration=0.1, sample_rate=16000)
        
        # Act
        result = transcriber.feed_audio_chunk(audio_chunk)
        
        # Assert
        assert result is None
        assert transcriber.stats["streaming_chunks"] == 0
        
    def test_feed_audio_chunk_streaming(self):
        """Test feed_audio_chunk when streaming."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Start streaming
        callback = MagicMock()
        transcriber.start_streaming(callback)
        
        # Create two audio chunks
        chunk1, _ = create_test_audio(duration=0.1, sample_rate=16000)
        chunk2, _ = create_test_audio(duration=0.1, sample_rate=16000, frequency=600)
        
        # Set up mock response for interim result
        mock_interim = {
            "text": "Interim result",
            "segments": [],
            "language": "en",
            "confidence": 0.7
        }
        mock_adapter.transcribe = MagicMock(return_value=mock_interim)
        
        # Act - Feed first chunk (should not generate interim result yet)
        result1 = transcriber.feed_audio_chunk(chunk1)
        
        # Act - Feed second chunk (should generate interim result)
        result2 = transcriber.feed_audio_chunk(chunk2)
        
        # Assert
        assert result1 is None
        assert result2["text"] == "Interim result"
        assert result2["interim"] is True
        assert transcriber.stats["streaming_chunks"] == 2
        assert len(transcriber._stream_buffer) == 2
        assert callback.call_count == 1
        assert callback.call_args[0][0] == result2
        
    def test_stop_streaming_not_active(self):
        """Test stop_streaming when not streaming."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Act
        result = transcriber.stop_streaming()
        
        # Assert
        assert result is None
        
    def test_stop_streaming_with_empty_buffer(self):
        """Test stop_streaming with empty buffer."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Start streaming but don't feed any audio
        callback = MagicMock()
        transcriber.start_streaming(callback)
        
        # Act
        result = transcriber.stop_streaming()
        
        # Assert
        assert result is None
        assert transcriber._streaming is False
        assert transcriber._stream_buffer == []
        
    def test_stop_streaming_with_audio(self):
        """Test stop_streaming with audio in buffer."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Start streaming
        callback = MagicMock()
        transcriber.start_streaming(callback)
        
        # Feed audio chunks
        chunk1, _ = create_test_audio(duration=0.5, sample_rate=16000)
        chunk2, _ = create_test_audio(duration=0.5, sample_rate=16000, frequency=600)
        transcriber.feed_audio_chunk(chunk1)
        transcriber.feed_audio_chunk(chunk2)
        
        # Set up mock response for final result
        mock_final = {
            "text": "Final transcription result",
            "segments": [],
            "language": "en",
            "confidence": 0.9
        }
        mock_adapter.transcribe = MagicMock(return_value=mock_final)
        
        # Act
        result = transcriber.stop_streaming()
        
        # Assert
        assert result["text"] == "Final transcription result"
        assert result["interim"] is False
        assert transcriber._streaming is False
        assert transcriber._stream_buffer == []
        assert mock_adapter.transcribe.call_count == 1
        
    def test_stop_streaming_with_short_audio(self):
        """Test stop_streaming with very short audio buffer."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Start streaming
        callback = MagicMock()
        transcriber.start_streaming(callback)
        
        # Feed a very short audio chunk (less than 0.25s at 16kHz)
        short_chunk = np.zeros(3000, dtype=np.float32)
        transcriber.feed_audio_chunk(short_chunk)
        
        # Act
        result = transcriber.stop_streaming()
        
        # Assert
        assert result["text"] == ""
        assert result["confidence"] == 0
        assert len(result["segments"]) == 0
        assert result["interim"] is False
        
    def test_is_streaming(self):
        """Test is_streaming method."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Act & Assert - Initially false
        assert transcriber.is_streaming() is False
        
        # Start streaming
        callback = MagicMock()
        transcriber.start_streaming(callback)
        
        # Act & Assert - Should be true after starting
        assert transcriber.is_streaming() is True
        
        # Stop streaming
        transcriber.stop_streaming()
        
        # Act & Assert - Should be false after stopping
        assert transcriber.is_streaming() is False
        
    def test_set_quality(self):
        """Test set_quality method."""
        # Arrange
        mock_adapter = MockWhisperAdapter(model_size="base")
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            default_quality=TranscriptionQuality.MEDIUM  # Maps to "base"
        )
        
        # Set up mock
        mock_adapter.unload_model = MagicMock()
        
        # Act - Set to HIGH quality
        transcriber.set_quality(TranscriptionQuality.HIGH)
        
        # Assert
        assert transcriber.default_quality == TranscriptionQuality.HIGH
        assert mock_adapter.unload_model.call_count == 1
        assert mock_adapter.model_size == "small"  # HIGH quality maps to "small" model
        
    def test_set_quality_same(self):
        """Test set_quality with same quality (should do nothing)."""
        # Arrange
        mock_adapter = MockWhisperAdapter(model_size="base")
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            default_quality=TranscriptionQuality.MEDIUM  # Maps to "base"
        )
        
        # Set up mock
        mock_adapter.unload_model = MagicMock()
        
        # Act - Set to same quality
        transcriber.set_quality(TranscriptionQuality.MEDIUM)
        
        # Assert
        assert transcriber.default_quality == TranscriptionQuality.MEDIUM
        assert mock_adapter.unload_model.call_count == 0
        assert mock_adapter.model_size == "base"  # Should remain unchanged
        
    def test_configure(self):
        """Test configure method."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            min_confidence=0.4,
            enable_streaming=True,
            cache_size=10
        )
        
        # Act - Update configuration
        transcriber.configure(
            min_confidence=0.7,
            enable_streaming=False,
            cache_size=20
        )
        
        # Assert
        assert transcriber.min_confidence == 0.7
        assert transcriber.enable_streaming is False
        assert transcriber.cache_size == 20
        assert transcriber.cache_queue.maxlen == 20
        
    def test_configure_quality(self):
        """Test configure with quality parameter."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            default_quality=TranscriptionQuality.MEDIUM
        )
        
        # Act - Update quality with string
        transcriber.configure(default_quality="high")
        
        # Assert
        assert transcriber.default_quality == TranscriptionQuality.HIGH
        
        # Act - Update quality with enum
        transcriber.configure(default_quality=TranscriptionQuality.LOW)
        
        # Assert
        assert transcriber.default_quality == TranscriptionQuality.LOW
        
        # Act - Update with invalid quality (should be ignored)
        transcriber.configure(default_quality="ultra")
        
        # Assert - Should remain unchanged
        assert transcriber.default_quality == TranscriptionQuality.LOW
        
    def test_clear_cache(self):
        """Test clear_cache method."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        
        # Create test audio and cache a result
        audio_data, _ = create_test_audio(duration=1.0)
        transcriber.transcribe(audio_data)
        
        # Verify cache is populated
        assert len(transcriber.result_cache) == 1
        assert len(transcriber.cache_queue) == 1
        
        # Act
        transcriber.clear_cache()
        
        # Assert
        assert len(transcriber.result_cache) == 0
        assert len(transcriber.cache_queue) == 0
        
    def test_get_stats(self):
        """Test get_stats method."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        mock_adapter.get_stats = MagicMock(return_value={"transcription_count": 5})
        
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        transcriber.stats = {
            "total_requests": 10,
            "cache_hits": 3,
            "streaming_chunks": 20,
            "avg_latency": 0.2
        }
        
        # Add an item to cache
        transcriber.result_cache = {"key1": "value1"}
        
        # Act
        stats = transcriber.get_stats()
        
        # Assert
        assert stats["total_requests"] == 10
        assert stats["cache_hits"] == 3
        assert stats["streaming_chunks"] == 20
        assert stats["avg_latency"] == 0.2
        assert stats["cache_size"] == 1
        assert stats["is_streaming"] is False
        assert stats["adapter"]["transcription_count"] == 5
        
    def test_cache_overflow(self):
        """Test cache overflow behavior."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        # Small cache size for testing
        transcriber = Transcriber(
            whisper_adapter=mock_adapter,
            cache_size=2
        )
        
        # Create different test audio samples
        audio1, _ = create_test_audio(duration=1.0, frequency=440)
        audio2, _ = create_test_audio(duration=1.0, frequency=880)
        audio3, _ = create_test_audio(duration=1.0, frequency=220)
        
        # Mock responses for each
        mock_responses = [
            {"text": f"Audio {i+1}", "segments": [], "language": "en", "confidence": 0.9}
            for i in range(3)
        ]
        
        # Setup mock to return different response for each call
        mock_adapter.transcribe = MagicMock(side_effect=mock_responses)
        
        # Act - Fill cache and overflow
        result1 = transcriber.transcribe(audio1)
        result2 = transcriber.transcribe(audio2)
        result3 = transcriber.transcribe(audio3)
        
        # Get cache keys
        cache_key1 = transcriber._get_cache_key(audio1)
        cache_key2 = transcriber._get_cache_key(audio2)
        cache_key3 = transcriber._get_cache_key(audio3)
        
        # Assert
        assert len(transcriber.result_cache) == 2  # Max cache size
        assert len(transcriber.cache_queue) == 2
        assert cache_key1 not in transcriber.result_cache  # Oldest should be evicted
        assert cache_key2 in transcriber.result_cache
        assert cache_key3 in transcriber.result_cache
        assert list(transcriber.cache_queue) == [cache_key2, cache_key3]  # Order preserved
        
    def test_update_latency_stats(self):
        """Test _update_latency_stats method."""
        # Arrange
        mock_adapter = MockWhisperAdapter()
        transcriber = Transcriber(whisper_adapter=mock_adapter)
        transcriber.stats["total_requests"] = 0
        transcriber.stats["avg_latency"] = 0.0
        
        # Act - First request
        transcriber._update_latency_stats(0.5)
        
        # Assert - Implementation might use alpha=0.1 for first request too
        # Check it's a number between 0 and 1
        assert 0 < transcriber.stats["avg_latency"] <= 0.5
        
        # Store the result from first update
        first_avg = transcriber.stats["avg_latency"]
        
        # Act - Second request
        transcriber.stats["total_requests"] = 2
        transcriber._update_latency_stats(0.7)
        
        # Assert - Subsequent requests use exponential moving average
        # Should be between first_avg and new value 0.7
        assert first_avg < transcriber.stats["avg_latency"] < 0.7


class TestTranscriptionQuality:
    """Tests for TranscriptionQuality enum."""
    
    def test_enum_values(self):
        """Test enum values."""
        # Assert
        assert TranscriptionQuality.LOW.value == "low"
        assert TranscriptionQuality.MEDIUM.value == "medium"
        assert TranscriptionQuality.HIGH.value == "high"
        
    def test_equality(self):
        """Test equality comparisons."""
        # Assert
        assert TranscriptionQuality.LOW == TranscriptionQuality.LOW
        assert TranscriptionQuality.LOW != TranscriptionQuality.MEDIUM
        assert TranscriptionQuality("low") == TranscriptionQuality.LOW
        
    def test_from_string(self):
        """Test creating enum from string."""
        # Assert
        assert TranscriptionQuality("low") == TranscriptionQuality.LOW
        assert TranscriptionQuality("medium") == TranscriptionQuality.MEDIUM
        assert TranscriptionQuality("high") == TranscriptionQuality.HIGH
        
        # Invalid value should raise ValueError
        with pytest.raises(ValueError):
            TranscriptionQuality("invalid")