#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcription manager and processor for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_003 - Speech-to-Text Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-001 - Use Whisper for speech-to-text conversion

import logging
import time
import re
import threading
import numpy as np
from collections import deque
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Tuple, Callable

from voice.stt.whisper_adapter import WhisperAdapter

logger = logging.getLogger(__name__)

class TranscriptionQuality(Enum):
    """Quality level for transcription."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Transcriber:
    """
    High-level interface for speech recognition with streaming capability.
    
    Provides streaming transcription, confidence filtering, and caching
    for improved performance and user experience.
    """
    
    # Quality to model size mapping
    QUALITY_MAPPING = {
        TranscriptionQuality.LOW: "tiny",
        TranscriptionQuality.MEDIUM: "base",
        TranscriptionQuality.HIGH: "small"
    }
    
    def __init__(self,
                whisper_adapter: Optional[WhisperAdapter] = None,
                min_confidence: float = 0.4,
                default_quality: Union[str, TranscriptionQuality] = TranscriptionQuality.MEDIUM,
                enable_streaming: bool = True,
                cache_size: int = 10):
        """
        Initialize transcription manager.
        
        Args:
            whisper_adapter: WhisperAdapter instance
            min_confidence: Minimum confidence threshold
            default_quality: Default transcription quality
            enable_streaming: Whether to enable streaming transcription
            cache_size: Size of result cache
        """
        # Convert string quality to enum if needed
        if isinstance(default_quality, str):
            try:
                default_quality = TranscriptionQuality(default_quality)
            except ValueError:
                default_quality = TranscriptionQuality.MEDIUM
                logger.warning(f"Invalid quality value: {default_quality}, using MEDIUM")
                
        self.default_quality = default_quality
        self.min_confidence = min_confidence
        self.enable_streaming = enable_streaming
        self.cache_size = cache_size
        
        # Use provided adapter or create default
        self.whisper_adapter = whisper_adapter or WhisperAdapter(
            model_size=self.QUALITY_MAPPING[self.default_quality]
        )
        
        # Result cache for quick lookups
        self.result_cache = {}
        self.cache_queue = deque(maxlen=cache_size)
        
        # Streaming state
        self._streaming = False
        self._stream_buffer = []
        self._stream_callback = None
        self._last_interim_result = None
        self._streaming_lock = threading.RLock()
        
        # Stats
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "streaming_chunks": 0,
            "avg_latency": 0.0
        }
        
        logger.info(f"Initialized Transcriber with quality={default_quality.value}, "
                  f"min_confidence={min_confidence}, streaming={enable_streaming}")
        
    def transcribe(self, 
                  audio_data: np.ndarray, 
                  quality: Optional[TranscriptionQuality] = None,
                  context: Optional[str] = None,
                  callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Numpy array of audio samples
            quality: TranscriptionQuality or None for default
            context: Optional previous context to improve transcription
            callback: Optional callback for streaming results
            
        Returns:
            Dict with transcription results
        """
        start_time = time.time()
        
        # Check if we have cached result
        cache_key = self._get_cache_key(audio_data)
        if cache_key in self.result_cache:
            logger.debug("Using cached transcription result")
            self.stats["cache_hits"] += 1
            result = self.result_cache[cache_key]
            
            # Update stats
            self.stats["total_requests"] += 1
            latency = time.time() - start_time
            self._update_latency_stats(latency)
            
            return result
        
        # Determine which model size to use
        quality = quality or self.default_quality
        model_size = self.QUALITY_MAPPING.get(quality, self.QUALITY_MAPPING[TranscriptionQuality.MEDIUM])
        
        # Check if we need to switch model size
        current_size = self.whisper_adapter.model_size
        if current_size != model_size:
            logger.debug(f"Switching model size from {current_size} to {model_size}")
            # Unload current model
            self.whisper_adapter.unload_model()
            # Update model size
            self.whisper_adapter.model_size = model_size
        
        # Prepare transcription parameters
        params = {}
        if context is not None:
            # Context not directly used by Whisper, but could be used in future implementations
            logger.debug("Context provided but not used directly by current Whisper implementation")
        
        # Perform transcription
        result = self.whisper_adapter.transcribe(audio_data, **params)
        
        # Filter low confidence results
        if result["confidence"] < self.min_confidence and len(result["text"].strip()) > 0:
            logger.debug(f"Low confidence result: {result['confidence']:.2f} < {self.min_confidence}")
            # Don't discard completely, but mark as low confidence
            result["low_confidence"] = True
        else:
            result["low_confidence"] = False
        
        # Cache the result
        if len(self.cache_queue) >= self.cache_size:
            # Remove oldest item from cache if full
            oldest = self.cache_queue.popleft()
            if oldest in self.result_cache:
                del self.result_cache[oldest]
                
        self.result_cache[cache_key] = result
        self.cache_queue.append(cache_key)
        
        # Update stats
        self.stats["total_requests"] += 1
        latency = time.time() - start_time
        self._update_latency_stats(latency)
        
        # Notify callback if provided
        if callback:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in transcription callback: {e}")
                
        return result
    
    def start_streaming(self, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Start streaming transcription mode.
        
        Args:
            callback: Function to call with interim results
            
        Returns:
            True if streaming started successfully
        """
        if not self.enable_streaming:
            logger.warning("Streaming transcription is disabled")
            return False
            
        with self._streaming_lock:
            if self._streaming:
                logger.warning("Streaming already active")
                return False
                
            self._streaming = True
            self._stream_buffer = []
            self._stream_callback = callback
            self._last_interim_result = None
            
            logger.debug("Started streaming transcription")
            return True
    
    def feed_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Feed audio chunk to streaming transcription.
        
        Args:
            audio_chunk: New chunk of audio data
            
        Returns:
            Dict with interim transcription (if available)
        """
        if not self._streaming:
            logger.warning("Cannot feed audio chunk - streaming not active")
            return None
            
        with self._streaming_lock:
            # Add chunk to buffer
            self._stream_buffer.append(audio_chunk)
            self.stats["streaming_chunks"] += 1
            
            # Only generate interim results every few chunks to avoid excessive processing
            # For a typical 16kHz audio with 4096 chunk size, this is roughly every 0.5 seconds
            if len(self._stream_buffer) % 2 == 0:
                # Generate interim result
                try:
                    # Concatenate all chunks
                    audio_data = np.concatenate(self._stream_buffer)
                    
                    # Process the audio
                    interim_result = self.whisper_adapter.transcribe(audio_data, beam_size=3)
                    interim_result["interim"] = True
                    
                    # Save as last interim result
                    self._last_interim_result = interim_result
                    
                    # Notify callback
                    if self._stream_callback:
                        try:
                            self._stream_callback(interim_result)
                        except Exception as e:
                            logger.error(f"Error in stream callback: {e}")
                            
                    return interim_result
                except Exception as e:
                    logger.error(f"Error generating interim result: {e}")
                    
            return None
    
    def stop_streaming(self) -> Optional[Dict[str, Any]]:
        """
        Stop streaming and return final transcription.
        
        Returns:
            Dict with final transcription or None if no audio was captured
        """
        if not self._streaming:
            logger.warning("Cannot stop streaming - streaming not active")
            return None
            
        with self._streaming_lock:
            logger.debug("Stopping streaming transcription")
            
            # Process final result if we have audio
            final_result = None
            if self._stream_buffer:
                try:
                    # Concatenate all chunks
                    audio_data = np.concatenate(self._stream_buffer)
                    
                    # If very short audio, likely not speech
                    if len(audio_data) < 4000:  # ~0.25 seconds at 16kHz
                        logger.debug("Audio too short for transcription")
                        final_result = {
                            "text": "",
                            "segments": [],
                            "language": "en",
                            "confidence": 0,
                            "interim": False
                        }
                    else:
                        # Process with higher quality settings for final result
                        final_result = self.whisper_adapter.transcribe(
                            audio_data, 
                            beam_size=self.whisper_adapter.beam_size
                        )
                        final_result["interim"] = False
                except Exception as e:
                    logger.error(f"Error generating final result: {e}")
                    final_result = self._last_interim_result
            
            # Reset streaming state
            self._streaming = False
            self._stream_buffer = []
            self._stream_callback = None
            
            return final_result
    
    def is_streaming(self) -> bool:
        """
        Check if streaming is currently active.
        
        Returns:
            True if streaming is active
        """
        return self._streaming
    
    def set_quality(self, quality: TranscriptionQuality) -> None:
        """
        Set transcription quality (affects model size and parameters).
        
        Args:
            quality: New transcription quality
        """
        if quality == self.default_quality:
            return
            
        logger.info(f"Setting transcription quality to {quality.value}")
        self.default_quality = quality
        
        # Unload current model
        self.whisper_adapter.unload_model()
        
        # Update model size based on quality
        model_size = self.QUALITY_MAPPING.get(quality, self.QUALITY_MAPPING[TranscriptionQuality.MEDIUM])
        self.whisper_adapter.model_size = model_size
    
    def configure(self, **kwargs) -> None:
        """
        Update configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for param, value in kwargs.items():
            if param == "min_confidence" and isinstance(value, (int, float)):
                self.min_confidence = min(1.0, max(0.0, value))
                logger.debug(f"Updated min_confidence to {self.min_confidence}")
            elif param == "default_quality":
                if isinstance(value, TranscriptionQuality):
                    self.default_quality = value
                elif isinstance(value, str):
                    try:
                        self.default_quality = TranscriptionQuality(value)
                    except ValueError:
                        logger.warning(f"Invalid quality value: {value}")
                logger.debug(f"Updated default_quality to {self.default_quality.value}")
            elif param == "enable_streaming" and isinstance(value, bool):
                self.enable_streaming = value
                logger.debug(f"Updated enable_streaming to {self.enable_streaming}")
            elif param == "cache_size" and isinstance(value, int):
                self.cache_size = max(1, value)
                # Resize cache queue
                new_queue = deque(self.cache_queue, maxlen=self.cache_size)
                self.cache_queue = new_queue
                logger.debug(f"Updated cache_size to {self.cache_size}")
    
    def clear_cache(self) -> None:
        """Clear the result cache."""
        self.result_cache = {}
        self.cache_queue.clear()
        logger.debug("Cleared transcription cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about transcription performance.
        
        Returns:
            Dictionary with statistics
        """
        # Add model stats
        stats = self.stats.copy()
        stats["adapter"] = self.whisper_adapter.get_stats()
        stats["cache_size"] = len(self.result_cache)
        stats["is_streaming"] = self._streaming
        
        return stats
    
    def _get_cache_key(self, audio_data: np.ndarray) -> str:
        """
        Generate a cache key for audio data.
        
        Args:
            audio_data: Audio data to generate key for
            
        Returns:
            Cache key string
        """
        # Simple hash-based key
        data_hash = hash(audio_data.tobytes())
        return f"audio_{data_hash}"
    
    def _update_latency_stats(self, latency: float) -> None:
        """
        Update latency statistics.
        
        Args:
            latency: New latency measurement
        """
        # Exponential moving average
        if self.stats["total_requests"] == 1:
            self.stats["avg_latency"] = latency
        else:
            alpha = 0.1  # Weight for new sample
            self.stats["avg_latency"] = alpha * latency + (1 - alpha) * self.stats["avg_latency"]


class TranscriptionProcessor:
    """
    Process and normalize transcription results.
    
    Handles text normalization, confidence filtering, and formatting
    for language model input.
    """
    
    # Common hesitation words to filter
    HESITATION_PATTERNS = [
        r'\bum\b', r'\buh\b', r'\beh\b', r'\ber\b', r'\bah\b', r'\bmm\b',
        r'\bhmm\b', r'\bumm\b', r'\bahm\b', r'\behm\b'
    ]
    
    def __init__(self,
                capitalize_sentences: bool = True,
                filter_hesitations: bool = True,
                confidence_threshold: float = 0.4):
        """
        Initialize transcription processor.
        
        Args:
            capitalize_sentences: Whether to auto-capitalize sentences
            filter_hesitations: Whether to filter out hesitation sounds
            confidence_threshold: Threshold for accepting words
        """
        self.capitalize_sentences = capitalize_sentences
        self.filter_hesitations = filter_hesitations
        self.confidence_threshold = confidence_threshold
        
        # Compile hesitation patterns
        self.hesitation_regex = re.compile('|'.join(self.HESITATION_PATTERNS), re.IGNORECASE)
        
        logger.debug(f"Initialized TranscriptionProcessor with capitalize={capitalize_sentences}, "
                    f"filter_hesitations={filter_hesitations}, threshold={confidence_threshold}")
    
    def process(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a transcription result.
        
        Args:
            transcription_result: Dict from Whisper transcription
            
        Returns:
            Processed transcription with normalized text
        """
        # Create a copy to avoid modifying the original
        result = transcription_result.copy()
        
        # Skip processing if no text
        if not result.get("text"):
            return result
            
        # Process text
        processed_text = result["text"]
        
        # Filter hesitations if enabled
        if self.filter_hesitations:
            processed_text = self.filter_hesitation_words(processed_text)
            
        # Normalize and capitalize
        processed_text = self.normalize_text(processed_text)
        
        # Process segments if present
        if "segments" in result:
            # Create a copy of segments
            processed_segments = []
            for segment in result["segments"]:
                # Copy segment
                processed_segment = segment.copy()
                
                # Process segment text
                if self.filter_hesitations:
                    processed_segment["text"] = self.filter_hesitation_words(segment["text"])
                    
                processed_segment["text"] = self.normalize_text(processed_segment["text"])
                
                # Only include if above confidence threshold
                if segment.get("confidence", 1.0) >= self.confidence_threshold:
                    processed_segments.append(processed_segment)
                    
            result["segments"] = processed_segments
            
            # Regenerate text from processed segments
            if processed_segments:
                processed_text = " ".join(seg["text"] for seg in processed_segments)
        
        # Update text
        result["text"] = processed_text
        
        # Add processing metadata
        result["processed"] = True
        result["processing"] = {
            "hesitations_filtered": self.filter_hesitations,
            "capitalization_applied": self.capitalize_sentences,
            "confidence_threshold": self.confidence_threshold
        }
        
        # Extract metadata
        result["metadata"] = self.extract_metadata(result)
        
        return result
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text with proper capitalization and punctuation.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
            
        # Remove extra whitespace
        normalized = " ".join(text.split())
        
        # Capitalize first letter of sentences if enabled
        if self.capitalize_sentences:
            # Split by sentence-ending punctuation
            sentences = re.split(r'([.!?]+\s+)', normalized)
            
            # Capitalize first letter of each sentence
            for i in range(0, len(sentences), 2):
                if sentences[i]:
                    sentences[i] = sentences[i][0].upper() + sentences[i][1:]
                    
            normalized = "".join(sentences)
            
            # Capitalize first letter of text if not already
            if normalized and normalized[0].islower():
                normalized = normalized[0].upper() + normalized[1:]
        
        return normalized
    
    def filter_hesitation_words(self, text: str) -> str:
        """
        Filter out hesitation words from text.
        
        Args:
            text: Text to filter
            
        Returns:
            Filtered text
        """
        if not text:
            return ""
            
        # Replace hesitation words with empty string
        filtered = self.hesitation_regex.sub('', text)
        
        # Clean up any resulting double spaces
        filtered = re.sub(r'\s+', ' ', filtered).strip()
        
        return filtered
    
    def filter_low_confidence(self, segments: List[Dict[str, Any]], threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Filter out low confidence words or segments.
        
        Args:
            segments: List of segments from transcription
            threshold: Optional override for confidence threshold
            
        Returns:
            Filtered list of segments
        """
        if not segments:
            return []
            
        threshold = threshold if threshold is not None else self.confidence_threshold
        
        return [seg for seg in segments if seg.get("confidence", 1.0) >= threshold]
    
    def extract_metadata(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract useful metadata from transcription result.
        
        Args:
            transcription_result: Transcription result dictionary
            
        Returns:
            Dictionary with metadata
        """
        metadata = {
            "word_count": 0,
            "duration": 0.0,
            "language": transcription_result.get("language", "en"),
            "confidence": transcription_result.get("confidence", 0.0),
            "is_interim": transcription_result.get("interim", False)
        }
        
        # Extract word count
        if transcription_result.get("text"):
            metadata["word_count"] = len(transcription_result["text"].split())
            
        # Extract duration from segments
        segments = transcription_result.get("segments", [])
        if segments:
            # Duration is the end time of the last segment
            metadata["duration"] = segments[-1].get("end", 0.0)
            
        return metadata
    
    def format_for_language_model(self, processed_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the processed transcription for LLM input.
        
        Args:
            processed_result: Processed transcription result
            
        Returns:
            Dictionary with formatted input for language model
        """
        # Create LLM input context
        llm_input = {
            "transcript": processed_result["text"],
            "confidence": processed_result.get("confidence", 0.0),
            "metadata": processed_result.get("metadata", {})
        }
        
        return llm_input
    
    def configure(self, **kwargs) -> None:
        """
        Update configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for param, value in kwargs.items():
            if param == "capitalize_sentences" and isinstance(value, bool):
                self.capitalize_sentences = value
                logger.debug(f"Updated capitalize_sentences to {self.capitalize_sentences}")
                
            elif param == "filter_hesitations" and isinstance(value, bool):
                self.filter_hesitations = value
                logger.debug(f"Updated filter_hesitations to {self.filter_hesitations}")
                
            elif param == "confidence_threshold" and isinstance(value, (int, float)):
                self.confidence_threshold = min(1.0, max(0.0, value))
                logger.debug(f"Updated confidence_threshold to {self.confidence_threshold}")
                
            elif param == "hesitation_patterns" and isinstance(value, list):
                # Update hesitation patterns
                try:
                    self.HESITATION_PATTERNS = value
                    self.hesitation_regex = re.compile('|'.join(self.HESITATION_PATTERNS), re.IGNORECASE)
                    logger.debug(f"Updated hesitation patterns with {len(value)} patterns")
                except Exception as e:
                    logger.error(f"Failed to update hesitation patterns: {e}")