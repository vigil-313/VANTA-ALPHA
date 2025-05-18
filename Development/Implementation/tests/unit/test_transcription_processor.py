#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for TranscriptionProcessor.
"""
# TASK-REF: VOICE_003 - Speech-to-Text Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy
# DECISION-REF: DEC-002-001 - Use Whisper for speech-to-text conversion

import pytest
import re
from unittest.mock import patch, Mock, MagicMock

from voice.stt.transcriber import TranscriptionProcessor
from tests.utils.audio_test_utils import add_hesitations_to_text, create_test_transcription_data

class TestTranscriptionProcessor:
    """Tests for TranscriptionProcessor class."""
    
    def test_init_default(self):
        """Test initialization with default parameters."""
        # Act
        processor = TranscriptionProcessor()
        
        # Assert
        assert processor.capitalize_sentences is True
        assert processor.filter_hesitations is True
        assert processor.confidence_threshold == 0.4
        assert isinstance(processor.hesitation_regex, re.Pattern)
        
    def test_init_custom(self):
        """Test initialization with custom parameters."""
        # Act
        processor = TranscriptionProcessor(
            capitalize_sentences=False,
            filter_hesitations=False,
            confidence_threshold=0.7
        )
        
        # Assert
        assert processor.capitalize_sentences is False
        assert processor.filter_hesitations is False
        assert processor.confidence_threshold == 0.7
        
    def test_normalize_text_empty(self):
        """Test normalize_text with empty text."""
        # Arrange
        processor = TranscriptionProcessor()
        
        # Act
        result = processor.normalize_text("")
        
        # Assert
        assert result == ""
        
    def test_normalize_text_whitespace(self):
        """Test normalize_text with extra whitespace."""
        # Arrange
        processor = TranscriptionProcessor()
        
        # Act
        result = processor.normalize_text("  hello   world  ")
        
        # Assert
        assert result == "Hello world"
        
    def test_normalize_text_capitalization(self):
        """Test normalize_text with capitalization."""
        # Arrange
        processor = TranscriptionProcessor(capitalize_sentences=True)
        
        # Act
        result = processor.normalize_text("hello. world. this is a test.")
        
        # Assert - Each sentence should start with capital letter
        assert result == "Hello. World. This is a test."
        
    def test_normalize_text_no_capitalization(self):
        """Test normalize_text without capitalization."""
        # Arrange
        processor = TranscriptionProcessor(capitalize_sentences=False)
        
        # Act
        result = processor.normalize_text("hello. world. this is a test.")
        
        # Assert - Should not capitalize
        assert result == "hello. world. this is a test."
        
    def test_filter_hesitation_words_empty(self):
        """Test filter_hesitation_words with empty text."""
        # Arrange
        processor = TranscriptionProcessor()
        
        # Act
        result = processor.filter_hesitation_words("")
        
        # Assert
        assert result == ""
        
    def test_filter_hesitation_words(self):
        """Test filter_hesitation_words with hesitations."""
        # Arrange
        processor = TranscriptionProcessor()
        text_with_hesitations = "um hello uh world er this ah is hmm a test"
        
        # Act
        result = processor.filter_hesitation_words(text_with_hesitations)
        
        # Assert - All hesitations should be removed
        assert result == "hello world this is a test"
        
    def test_filter_hesitation_words_case_insensitive(self):
        """Test filter_hesitation_words case insensitivity."""
        # Arrange
        processor = TranscriptionProcessor()
        text_with_hesitations = "UM hello UH world ER this AH is HMM a test"
        
        # Act
        result = processor.filter_hesitation_words(text_with_hesitations)
        
        # Assert - All hesitations should be removed regardless of case
        assert result == "hello world this is a test"
        
    def test_filter_low_confidence_empty(self):
        """Test filter_low_confidence with empty list."""
        # Arrange
        processor = TranscriptionProcessor(confidence_threshold=0.5)
        
        # Act
        result = processor.filter_low_confidence([])
        
        # Assert
        assert result == []
        
    def test_filter_low_confidence(self):
        """Test filter_low_confidence with mixed confidences."""
        # Arrange
        processor = TranscriptionProcessor(confidence_threshold=0.5)
        segments = [
            {"id": 0, "text": "High confidence", "confidence": 0.8},
            {"id": 1, "text": "Low confidence", "confidence": 0.3},
            {"id": 2, "text": "Medium confidence", "confidence": 0.6},
            {"id": 3, "text": "No confidence specified"}
        ]
        
        # Act
        result = processor.filter_low_confidence(segments)
        
        # Assert - Should filter out segment with confidence < 0.5
        assert len(result) == 3
        assert result[0]["text"] == "High confidence"
        assert result[1]["text"] == "Medium confidence"
        assert result[2]["text"] == "No confidence specified"  # Default confidence is 1.0
        
    def test_filter_low_confidence_custom_threshold(self):
        """Test filter_low_confidence with custom threshold."""
        # Arrange
        processor = TranscriptionProcessor(confidence_threshold=0.5)
        segments = [
            {"id": 0, "text": "High confidence", "confidence": 0.8},
            {"id": 1, "text": "Low confidence", "confidence": 0.3},
            {"id": 2, "text": "Medium confidence", "confidence": 0.6}
        ]
        
        # Act - Use override threshold
        result = processor.filter_low_confidence(segments, threshold=0.7)
        
        # Assert - Should filter out segments with confidence < 0.7
        assert len(result) == 1
        assert result[0]["text"] == "High confidence"
        
    def test_extract_metadata_empty(self):
        """Test extract_metadata with empty result."""
        # Arrange
        processor = TranscriptionProcessor()
        empty_result = {"text": "", "segments": []}
        
        # Act
        metadata = processor.extract_metadata(empty_result)
        
        # Assert
        assert metadata["word_count"] == 0
        assert metadata["duration"] == 0.0
        assert metadata["language"] == "en"  # Default
        assert metadata["confidence"] == 0.0  # Default
        assert metadata["is_interim"] is False  # Default
        
    def test_extract_metadata_with_segments(self):
        """Test extract_metadata with segments."""
        # Arrange
        processor = TranscriptionProcessor()
        result = {
            "text": "Hello world this is a test",
            "segments": [
                {"id": 0, "text": "Hello world", "start": 0.0, "end": 1.0},
                {"id": 1, "text": "this is a test", "start": 1.2, "end": 2.5}
            ],
            "language": "fr",
            "confidence": 0.85,
            "interim": True
        }
        
        # Act
        metadata = processor.extract_metadata(result)
        
        # Assert
        assert metadata["word_count"] == 6  # 6 words in the text
        assert metadata["duration"] == 2.5  # End time of last segment
        assert metadata["language"] == "fr"
        assert metadata["confidence"] == 0.85
        assert metadata["is_interim"] is True
        
    def test_format_for_language_model(self):
        """Test format_for_language_model."""
        # Arrange
        processor = TranscriptionProcessor()
        processed_result = {
            "text": "Formatted for LLM",
            "confidence": 0.9,
            "metadata": {
                "word_count": 3,
                "duration": 1.5,
                "language": "en"
            },
            "other_field": "should not be included"
        }
        
        # Act
        llm_input = processor.format_for_language_model(processed_result)
        
        # Assert
        assert llm_input["transcript"] == "Formatted for LLM"
        assert llm_input["confidence"] == 0.9
        assert llm_input["metadata"] == processed_result["metadata"]
        assert "other_field" not in llm_input
        
    def test_process_empty_text(self):
        """Test process with empty text."""
        # Arrange
        processor = TranscriptionProcessor()
        empty_result = {"text": "", "segments": []}
        
        # Act
        processed = processor.process(empty_result)
        
        # Assert - Just check that the text is still empty
        assert processed["text"] == ""
        
    def test_process_with_hesitations(self):
        """Test process with hesitations to filter."""
        # Arrange
        processor = TranscriptionProcessor(
            capitalize_sentences=True,
            filter_hesitations=True
        )
        
        text_with_hesitations = "um hello uh world"
        result = {"text": text_with_hesitations, "segments": [], "confidence": 0.8}
        
        # Act
        processed = processor.process(result)
        
        # Assert
        assert processed["text"] == "Hello world"
        assert processed["processed"] is True
        assert processed["processing"]["hesitations_filtered"] is True
        assert processed["processing"]["capitalization_applied"] is True
        
    def test_process_no_filtering(self):
        """Test process with filtering disabled."""
        # Arrange
        processor = TranscriptionProcessor(
            capitalize_sentences=False,
            filter_hesitations=False
        )
        
        text_with_hesitations = "um hello uh world"
        result = {"text": text_with_hesitations, "segments": [], "confidence": 0.8}
        
        # Act
        processed = processor.process(result)
        
        # Assert
        assert processed["text"] == "um hello uh world"
        assert processed["processed"] is True
        assert processed["processing"]["hesitations_filtered"] is False
        assert processed["processing"]["capitalization_applied"] is False
        
    def test_process_with_segments(self):
        """Test process with segments."""
        # Arrange
        processor = TranscriptionProcessor(
            capitalize_sentences=True,
            filter_hesitations=True,
            confidence_threshold=0.5
        )
        
        # Create result with segments
        result = {
            "text": "Um hello uh world. This is er a test.",
            "segments": [
                {
                    "id": 0,
                    "text": "Um hello uh world",
                    "start": 0.0,
                    "end": 1.0,
                    "confidence": 0.7
                },
                {
                    "id": 1,
                    "text": "This is er a test",
                    "start": 1.2,
                    "end": 2.5,
                    "confidence": 0.4  # Below threshold
                }
            ],
            "language": "en",
            "confidence": 0.6
        }
        
        # Act
        processed = processor.process(result)
        
        # Assert
        assert len(processed["segments"]) == 1  # Low confidence segment should be filtered out
        assert processed["segments"][0]["text"] == "Hello world"  # Normalized and filtered
        assert processed["text"] == "Hello world"  # Text regenerated from segments
        assert processed["processed"] is True
        
    def test_configure(self):
        """Test configure method."""
        # Arrange
        processor = TranscriptionProcessor(
            capitalize_sentences=True,
            filter_hesitations=True,
            confidence_threshold=0.4
        )
        
        # Act
        processor.configure(
            capitalize_sentences=False,
            filter_hesitations=False,
            confidence_threshold=0.7
        )
        
        # Assert
        assert processor.capitalize_sentences is False
        assert processor.filter_hesitations is False
        assert processor.confidence_threshold == 0.7
        
    def test_configure_invalid_values(self):
        """Test configure with invalid parameter values."""
        # Arrange
        processor = TranscriptionProcessor()
        initial_threshold = processor.confidence_threshold
        
        # Act - Try to update with invalid parameters
        processor.configure(
            capitalize_sentences="not a boolean",  # Not a boolean
            filter_hesitations=123,               # Not a boolean
            confidence_threshold="not a number",  # Not a number
            unknown_parameter="ignored"           # Unknown parameter
        )
        
        # Assert - Should not change any settings
        assert processor.capitalize_sentences is True
        assert processor.filter_hesitations is True
        assert processor.confidence_threshold == initial_threshold
        
    def test_configure_threshold_clamping(self):
        """Test configure with threshold clamping."""
        # Arrange
        processor = TranscriptionProcessor()
        
        # Act - Try values outside [0, 1] range
        processor.configure(confidence_threshold=1.5)  # Above 1.0
        assert processor.confidence_threshold == 1.0  # Should clamp to 1.0
        
        processor.configure(confidence_threshold=-0.5)  # Below 0.0
        assert processor.confidence_threshold == 0.0  # Should clamp to 0.0
        
    def test_update_hesitation_patterns(self):
        """Test updating hesitation patterns."""
        # Arrange
        processor = TranscriptionProcessor()
        
        # Act - Update hesitation patterns
        new_patterns = ["hum", "erm", "like"]
        processor.configure(hesitation_patterns=new_patterns)
        
        # Create text with only new hesitations
        text = "hum this is erm a like test"
        
        # Filter using updated patterns
        result = processor.filter_hesitation_words(text)
        
        # Assert
        assert result == "this is a test"
        
    def test_integration_with_test_utils(self):
        """Test integration with audio_test_utils."""
        # Arrange
        processor = TranscriptionProcessor()
        
        # Create test text with hesitations
        original_text = "This is a test sentence for processor"
        text_with_hesitations = add_hesitations_to_text(original_text, hesitation_probability=0.5)
        
        # Create mock transcription data
        transcription = create_test_transcription_data(
            text=text_with_hesitations,
            num_segments=2,
            confidence=0.8,
            duration=2.0
        )
        
        # Act
        processed = processor.process(transcription)
        
        # Assert
        # Should be similar to original, but may not be exact due to capitalization
        assert processed["text"].lower() != text_with_hesitations.lower()
        assert "hesitations_filtered" in processed["processing"]
        assert "metadata" in processed
        assert processed["metadata"]["duration"] == 2.0
        assert processed["metadata"]["confidence"] == 0.8