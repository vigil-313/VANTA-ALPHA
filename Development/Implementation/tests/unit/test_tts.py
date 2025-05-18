#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for TTS components.
"""
# TASK-REF: VOICE_004 - Text-to-Speech Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-009-003 - Support both API and local models for TTS

import os
import tempfile
import pytest
import numpy as np
from unittest import mock

from voice.tts.tts_adapter import TTSAdapter, TTSEngineType, create_tts_adapter
from voice.tts.tts_engine_system import SystemTTSAdapter
from voice.tts.prosody_formatter import ProsodyFormatter
from voice.tts.speech_synthesizer import SpeechSynthesizer

class TestTTSAdapter:
    """Tests for the TTSAdapter base class."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = TTSAdapter()
        assert adapter.engine_type == TTSEngineType.LOCAL
        assert adapter.voice_id == "default"
        assert adapter.is_loaded() is False
        
        # Test with enum and string engine type
        adapter1 = TTSAdapter(engine_type=TTSEngineType.API)
        assert adapter1.engine_type == TTSEngineType.API
        
        adapter2 = TTSAdapter(engine_type="system")
        assert adapter2.engine_type == TTSEngineType.SYSTEM
        
    def test_load_unload(self):
        """Test load/unload methods."""
        adapter = TTSAdapter()
        assert adapter.is_loaded() is False
        
        result = adapter.load_engine()
        assert result is True
        assert adapter.is_loaded() is True
        
        result = adapter.unload_engine()
        assert result is True
        assert adapter.is_loaded() is False
        
    def test_base_synthesize(self):
        """Test base synthesize method."""
        adapter = TTSAdapter()
        result = adapter.synthesize("Hello world")
        
        assert "audio" in result
        assert "sample_rate" in result
        assert "duration" in result
        assert "format" in result
        assert "latency" in result
        
        # Verify audio is empty (as this is just the base implementation)
        assert len(result["audio"]) > 0
        assert np.all(result["audio"] == 0)
        
    def test_get_stats(self):
        """Test stats tracking."""
        adapter = TTSAdapter()
        
        # Verify initial stats
        stats = adapter.get_stats()
        assert stats["synthesis_count"] == 0
        assert stats["total_duration"] == 0.0
        
        # Synthesize and check updated stats
        adapter.synthesize("Hello")
        stats = adapter.get_stats()
        assert stats["synthesis_count"] == 1
        assert stats["total_duration"] > 0.0
        
    def test_factory_function(self):
        """Test create_tts_adapter factory function."""
        # Use a monkeypatch to avoid importing the actual adapter classes
        with mock.patch("voice.tts.tts_adapter.OpenAITTSAdapter"), \
             mock.patch("voice.tts.tts_adapter.PiperTTSAdapter"), \
             mock.patch("voice.tts.tts_adapter.SystemTTSAdapter"):
            
            # Test API engine creation
            config = {"engine_type": "api"}
            adapter = create_tts_adapter(config)
            assert adapter is not None
            
            # Test local engine creation
            config = {"engine_type": "local"}
            adapter = create_tts_adapter(config)
            assert adapter is not None
            
            # Test system engine creation
            config = {"engine_type": "system"}
            adapter = create_tts_adapter(config)
            assert adapter is not None


class TestSystemTTSAdapter:
    """Tests for the SystemTTSAdapter."""
    
    def test_init(self):
        """Test system adapter initialization."""
        adapter = SystemTTSAdapter()
        assert adapter.engine_type == TTSEngineType.SYSTEM
        assert "voice_id" in adapter.__dict__
        
    @pytest.mark.skipif(os.name != "posix", reason="Requires macOS for say command")
    def test_load_voices(self):
        """Test loading system voices."""
        adapter = SystemTTSAdapter()
        adapter.load_engine()
        
        voices = adapter.get_available_voices()
        # Even if we can't test exact voices, we can check the structure
        assert len(voices) > 0
        assert "id" in voices[0]
        assert "name" in voices[0]
        
    @pytest.mark.skipif(os.name != "posix", reason="Requires macOS for say command")
    def test_synthesize_basic(self):
        """Test basic synthesis."""
        # This is a simplified test that only checks the function runs without errors
        # A more complete test would verify the audio output, but that's harder to do in a unit test
        adapter = SystemTTSAdapter()
        result = adapter.synthesize("Test message")
        
        # Check structure of result
        assert "audio" in result
        assert "sample_rate" in result
        assert "duration" in result
        assert "latency" in result
        
        # Verify we got some audio back
        assert len(result["audio"]) > 0
        
        # If synthesis failed, there would be an error key
        assert "error" not in result


class TestProsodyFormatter:
    """Tests for the ProsodyFormatter."""
    
    def test_init(self):
        """Test formatter initialization."""
        formatter = ProsodyFormatter()
        assert formatter.add_punctuation is True
        assert formatter.enhance_questions is True
        
        # Test with different settings
        formatter = ProsodyFormatter(add_punctuation=False, enhance_emphasis=False)
        assert formatter.add_punctuation is False
        assert formatter.enhance_emphasis is False
        
    def test_format_text(self):
        """Test text formatting."""
        formatter = ProsodyFormatter()
        
        # Test punctuation addition
        text = "hello world"
        result = formatter.format_text(text)
        assert result.endswith(".")
        
        # Test with existing punctuation
        text = "hello world!"
        result = formatter.format_text(text)
        assert result == text
        
    def test_expand_abbreviations(self):
        """Test abbreviation expansion."""
        formatter = ProsodyFormatter()
        
        # Test common abbreviations
        text = "Mr. Smith and Dr. Jones"
        result = formatter.expand_abbreviations_in_text(text)
        assert "Mister" in result
        assert "Doctor" in result
        
    def test_ssml_generation(self):
        """Test SSML generation."""
        formatter = ProsodyFormatter()
        
        text = "Is this a question?"
        ssml = formatter.to_ssml(text)
        
        # Verify basic SSML structure
        assert "<?xml" in ssml
        assert "<speak" in ssml
        assert "<prosody" in ssml
        assert "Is this a question?" in ssml


class TestSpeechSynthesizer:
    """Tests for the SpeechSynthesizer."""
    
    def test_init(self):
        """Test synthesizer initialization."""
        synthesizer = SpeechSynthesizer()
        assert synthesizer.enable_caching is True
        assert synthesizer.cache_size == 50
        
        # Test with custom settings
        synthesizer = SpeechSynthesizer(enable_caching=False, cache_size=10)
        assert synthesizer.enable_caching is False
        assert synthesizer.cache_size == 10
        
    def test_cache_operation(self):
        """Test caching functionality."""
        # Create a mock adapter for testing
        mock_adapter = mock.MagicMock()
        mock_adapter.engine_type = TTSEngineType.SYSTEM
        mock_adapter.voice_id = "test"
        mock_adapter.speaking_rate = 1.0
        mock_adapter.pitch = 0.0
        mock_adapter.synthesize.return_value = {
            "audio": np.zeros(1000),
            "sample_rate": 24000,
            "duration": 0.5,
            "format": "wav"
        }
        
        # Create synthesizer with mocked adapter
        synthesizer = SpeechSynthesizer(tts_adapter=mock_adapter, cache_size=3)
        
        # First synthesis call should use adapter
        synthesizer.synthesize("Hello")
        mock_adapter.synthesize.assert_called_once()
        mock_adapter.synthesize.reset_mock()
        
        # Second call with same text should use cache
        synthesizer.synthesize("Hello")
        mock_adapter.synthesize.assert_not_called()
        
        # Different text should use adapter again
        synthesizer.synthesize("World")
        mock_adapter.synthesize.assert_called_once()
        
        # Test cache limit
        mock_adapter.synthesize.reset_mock()
        synthesizer.synthesize("One")
        synthesizer.synthesize("Two")
        synthesizer.synthesize("Three")
        
        # This should evict the oldest cache entry (Hello)
        synthesizer.synthesize("Four") 
        
        # Now Hello should use adapter again
        mock_adapter.synthesize.reset_mock()
        synthesizer.synthesize("Hello")
        mock_adapter.synthesize.assert_called_once()
        
    def test_cache_clearing(self):
        """Test cache clearing."""
        synthesizer = SpeechSynthesizer()
        
        # Set up mock adapter
        mock_adapter = mock.MagicMock()
        mock_adapter.engine_type = TTSEngineType.SYSTEM
        mock_adapter.voice_id = "test"
        mock_adapter.speaking_rate = 1.0
        mock_adapter.pitch = 0.0
        mock_adapter.synthesize.return_value = {
            "audio": np.zeros(1000),
            "sample_rate": 24000,
            "duration": 0.5,
            "format": "wav"
        }
        synthesizer.tts_adapter = mock_adapter
        
        # Fill cache
        synthesizer.synthesize("Hello")
        synthesizer.synthesize("World")
        mock_adapter.synthesize.reset_mock()
        
        # Verify cache is working
        synthesizer.synthesize("Hello")
        mock_adapter.synthesize.assert_not_called()
        
        # Clear cache
        synthesizer.clear_cache()
        
        # Now should use adapter again
        synthesizer.synthesize("Hello")
        mock_adapter.synthesize.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])