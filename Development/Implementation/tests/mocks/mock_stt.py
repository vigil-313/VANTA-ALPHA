#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock Speech-to-Text components for testing.
"""
# TASK-REF: VOICE_003 - Speech-to-Text Integration
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

import numpy as np
import time
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

class MockWhisperAdapter:
    """Mock implementation of WhisperAdapter for testing."""
    
    def __init__(self, 
                model_size: str = "small",
                device: str = "cpu",
                compute_type: str = "int8",
                language: str = "en",
                beam_size: int = 5):
        """Initialize mock WhisperAdapter."""
        self.model_size = model_size
        self.device_name = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        
        self.model = None
        self.device = None
        self.model_path = None
        
        # Track method calls for testing
        self.method_calls = {
            "load_model": 0,
            "unload_model": 0,
            "transcribe": 0,
            "transcribe_with_timestamps": 0
        }
        
        # Predetermined responses for transcription
        self.responses = {}
        
        # Stats
        self.stats = {
            "transcription_count": 0,
            "total_audio_seconds": 0.0,
            "total_transcription_time": 0.0,
            "model_info": None
        }
        
    def load_model(self) -> bool:
        """Mock loading the model."""
        self.method_calls["load_model"] += 1
        self.model = f"mock-whisper-{self.model_size}"
        self.device = self.device_name
        self.model_path = f"/mock/path/to/whisper-{self.model_size}"
        
        # Set model info
        self.stats["model_info"] = {
            "implementation": "mock-whisper",
            "model_size": self.model_size,
            "device": self.device_name,
            "compute_type": self.compute_type,
            "path": self.model_path
        }
        
        return True
        
    def unload_model(self) -> None:
        """Mock unloading the model."""
        self.method_calls["unload_model"] += 1
        self.model = None
        
    def is_loaded(self) -> bool:
        """Check if mock model is loaded."""
        return self.model is not None
    
    def add_response(self, audio_key: Any, response: Dict[str, Any]) -> None:
        """
        Add a predetermined response for a given audio input.
        
        Args:
            audio_key: Any key that can identify the audio (e.g., hash, length)
            response: The response to return for that audio
        """
        self.responses[audio_key] = response
    
    def transcribe(self, audio_data: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Mock transcribe method that returns predefined or generated responses.
        
        Args:
            audio_data: Audio data as numpy array
            **kwargs: Additional parameters
            
        Returns:
            Mock transcription result
        """
        self.method_calls["transcribe"] += 1
        
        # Check if we need to load the model
        if not self.is_loaded():
            self.load_model()
            
        # Calculate audio duration (assuming 16kHz sample rate)
        sample_rate = kwargs.get("sample_rate", 16000)
        audio_duration = len(audio_data) / sample_rate
        
        # Skip if audio is too short
        if audio_duration < 0.1:
            return {
                "text": "",
                "segments": [],
                "language": self.language,
                "confidence": 0
            }
            
        # Measure transcription time
        start_time = time.time()
        
        # Check if we have a predetermined response for this audio
        audio_hash = hash(audio_data.tobytes())
        if audio_hash in self.responses:
            result = self.responses[audio_hash]
        else:
            # Generate a mock response based on the audio characteristics
            energy = np.mean(np.abs(audio_data))
            duration = len(audio_data) / sample_rate
            
            # More energetic audio gets higher confidence
            confidence = min(0.95, max(0.1, energy * 10))
            
            # Longer audio gets more segments
            num_segments = max(1, int(duration / 0.5))
            
            # Generate segments
            segments = []
            segment_duration = duration / num_segments
            for i in range(num_segments):
                start_time_seg = i * segment_duration
                end_time_seg = (i + 1) * segment_duration
                segments.append({
                    "id": i,
                    "text": f"Mock segment {i+1}",
                    "start": start_time_seg,
                    "end": end_time_seg,
                    "confidence": confidence
                })
                
            # Create result
            result = {
                "text": f"Mock transcription of {duration:.1f}s audio with energy {energy:.2f}",
                "segments": segments,
                "language": self.language,
                "confidence": confidence
            }
        
        # Add processing delay proportional to audio length
        # (longer audio takes more time to process)
        time.sleep(min(0.05, audio_duration / 30))
        
        # Update stats
        end_time = time.time()
        transcription_time = end_time - start_time
        
        self.stats["transcription_count"] += 1
        self.stats["total_audio_seconds"] += audio_duration
        self.stats["total_transcription_time"] += transcription_time
        
        return result
        
    def transcribe_with_timestamps(self, audio_data: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Mock transcribe with timestamps."""
        self.method_calls["transcribe_with_timestamps"] += 1
        
        # Get basic transcription
        result = self.transcribe(audio_data, **kwargs)
        
        # Add empty word timestamps for now
        for segment in result["segments"]:
            segment["words"] = []
            
        return result
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get mock model info."""
        if not self.is_loaded():
            return {
                "loaded": False,
                "model_size": self.model_size,
                "device": self.device_name,
                "compute_type": self.compute_type
            }
            
        return {
            "loaded": True,
            **self.stats["model_info"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get mock stats."""
        stats = self.stats.copy()
        
        # Calculate real-time factor
        if stats["total_transcription_time"] > 0 and stats["total_audio_seconds"] > 0:
            stats["real_time_factor"] = stats["total_audio_seconds"] / stats["total_transcription_time"]
        else:
            stats["real_time_factor"] = 0
            
        return stats
        
        
class MockTranscriptionQuality(Enum):
    """Mock quality level for transcription."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MockTranscriber:
    """Mock implementation of Transcriber for testing."""
    
    QUALITY_MAPPING = {
        MockTranscriptionQuality.LOW: "tiny",
        MockTranscriptionQuality.MEDIUM: "base",
        MockTranscriptionQuality.HIGH: "small"
    }
    
    def __init__(self,
                whisper_adapter: Optional["MockWhisperAdapter"] = None,
                min_confidence: float = 0.4,
                default_quality: Any = MockTranscriptionQuality.MEDIUM,
                enable_streaming: bool = True,
                cache_size: int = 10):
        """Initialize mock transcriber."""
        
        # Convert string quality to enum if needed
        if isinstance(default_quality, str):
            try:
                default_quality = MockTranscriptionQuality(default_quality)
            except ValueError:
                default_quality = MockTranscriptionQuality.MEDIUM
        
        self.default_quality = default_quality
        self.min_confidence = min_confidence
        self.enable_streaming = enable_streaming
        self.cache_size = cache_size
        
        # Use provided adapter or create a mock one
        self.whisper_adapter = whisper_adapter or MockWhisperAdapter(
            model_size=self.QUALITY_MAPPING[self.default_quality]
        )
        
        # Result cache
        self.result_cache = {}
        
        # Streaming state
        self._streaming = False
        self._stream_buffer = []
        self._stream_callback = None
        self._last_interim_result = None
        
        # Track method calls
        self.method_calls = {
            "transcribe": 0,
            "start_streaming": 0,
            "feed_audio_chunk": 0,
            "stop_streaming": 0,
            "set_quality": 0,
            "configure": 0,
            "clear_cache": 0
        }
        
        # Stats
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "streaming_chunks": 0,
            "avg_latency": 0.0
        }
    
    def transcribe(self, 
                  audio_data: np.ndarray, 
                  quality: Optional[MockTranscriptionQuality] = None,
                  context: Optional[str] = None,
                  callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """Mock transcribe audio to text."""
        self.method_calls["transcribe"] += 1
        
        # Check cache
        cache_key = hash(audio_data.tobytes())
        if cache_key in self.result_cache:
            self.stats["cache_hits"] += 1
            return self.result_cache[cache_key]
        
        # Determine model size
        quality = quality or self.default_quality
        model_size = self.QUALITY_MAPPING.get(quality, self.QUALITY_MAPPING[MockTranscriptionQuality.MEDIUM])
        
        # Check if we need to switch model size
        current_size = self.whisper_adapter.model_size
        if current_size != model_size:
            # Unload current model
            self.whisper_adapter.unload_model()
            # Update model size
            self.whisper_adapter.model_size = model_size
        
        # Perform transcription
        result = self.whisper_adapter.transcribe(audio_data)
        
        # Filter low confidence
        if result["confidence"] < self.min_confidence and len(result["text"].strip()) > 0:
            result["low_confidence"] = True
        else:
            result["low_confidence"] = False
        
        # Cache the result
        self.result_cache[cache_key] = result
        
        # Update stats
        self.stats["total_requests"] += 1
        
        # Notify callback if provided
        if callback:
            try:
                callback(result)
            except Exception:
                pass
                
        return result
    
    def start_streaming(self, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """Mock start streaming transcription."""
        self.method_calls["start_streaming"] += 1
        
        if not self.enable_streaming:
            return False
            
        self._streaming = True
        self._stream_buffer = []
        self._stream_callback = callback
        self._last_interim_result = None
        
        return True
    
    def feed_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[Dict[str, Any]]:
        """Mock feed audio chunk to streaming transcription."""
        self.method_calls["feed_audio_chunk"] += 1
        
        if not self._streaming:
            return None
            
        # Add chunk to buffer
        self._stream_buffer.append(audio_chunk)
        self.stats["streaming_chunks"] += 1
        
        # Only generate interim results every few chunks
        if len(self._stream_buffer) % 2 == 0:
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
                    except Exception:
                        pass
                        
                return interim_result
            except Exception:
                pass
                
        return None
    
    def stop_streaming(self) -> Optional[Dict[str, Any]]:
        """Mock stop streaming and return final transcription."""
        self.method_calls["stop_streaming"] += 1
        
        if not self._streaming:
            return None
            
        # Process final result if we have audio
        final_result = None
        if self._stream_buffer:
            try:
                # Concatenate all chunks
                audio_data = np.concatenate(self._stream_buffer)
                
                # If very short audio, likely not speech
                if len(audio_data) < 4000:
                    final_result = {
                        "text": "",
                        "segments": [],
                        "language": "en",
                        "confidence": 0,
                        "interim": False
                    }
                else:
                    # Process with higher quality for final result
                    final_result = self.whisper_adapter.transcribe(audio_data)
                    final_result["interim"] = False
            except Exception:
                final_result = self._last_interim_result
        
        # Reset streaming state
        self._streaming = False
        self._stream_buffer = []
        self._stream_callback = None
        
        return final_result
    
    def is_streaming(self) -> bool:
        """Check if streaming is active."""
        return self._streaming
    
    def set_quality(self, quality: MockTranscriptionQuality) -> None:
        """Set transcription quality."""
        self.method_calls["set_quality"] += 1
        
        if quality == self.default_quality:
            return
            
        self.default_quality = quality
        
        # Unload current model
        self.whisper_adapter.unload_model()
        
        # Update model size based on quality
        model_size = self.QUALITY_MAPPING.get(quality, self.QUALITY_MAPPING[MockTranscriptionQuality.MEDIUM])
        self.whisper_adapter.model_size = model_size
    
    def configure(self, **kwargs) -> None:
        """Update configuration parameters."""
        self.method_calls["configure"] += 1
        
        for param, value in kwargs.items():
            if param == "min_confidence" and isinstance(value, (int, float)):
                self.min_confidence = min(1.0, max(0.0, value))
            elif param == "default_quality":
                if isinstance(value, MockTranscriptionQuality):
                    self.default_quality = value
                elif isinstance(value, str):
                    try:
                        self.default_quality = MockTranscriptionQuality(value)
                    except ValueError:
                        pass
            elif param == "enable_streaming" and isinstance(value, bool):
                self.enable_streaming = value
            elif param == "cache_size" and isinstance(value, int):
                self.cache_size = max(1, value)
    
    def clear_cache(self) -> None:
        """Clear the result cache."""
        self.method_calls["clear_cache"] += 1
        self.result_cache = {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about transcription performance."""
        stats = self.stats.copy()
        stats["adapter"] = self.whisper_adapter.get_stats()
        stats["cache_size"] = len(self.result_cache)
        stats["is_streaming"] = self._streaming
        
        return stats


class MockTranscriptionProcessor:
    """Mock implementation of TranscriptionProcessor for testing."""
    
    def __init__(self,
                capitalize_sentences: bool = True,
                filter_hesitations: bool = True,
                confidence_threshold: float = 0.4):
        """Initialize mock processor."""
        self.capitalize_sentences = capitalize_sentences
        self.filter_hesitations = filter_hesitations
        self.confidence_threshold = confidence_threshold
        
        # Track method calls
        self.method_calls = {
            "process": 0,
            "normalize_text": 0,
            "filter_hesitation_words": 0,
            "filter_low_confidence": 0,
            "extract_metadata": 0,
            "format_for_language_model": 0,
            "configure": 0
        }
    
    def process(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process a transcription result."""
        self.method_calls["process"] += 1
        
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
            processed_segments = []
            for segment in result["segments"]:
                processed_segment = segment.copy()
                
                if self.filter_hesitations:
                    processed_segment["text"] = self.filter_hesitation_words(segment["text"])
                    
                processed_segment["text"] = self.normalize_text(processed_segment["text"])
                
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
        """Mock normalize text with proper capitalization."""
        self.method_calls["normalize_text"] += 1
        
        if not text:
            return ""
            
        # Remove extra whitespace
        normalized = " ".join(text.split())
        
        # Capitalize first letter if enabled
        if self.capitalize_sentences and normalized:
            normalized = normalized[0].upper() + normalized[1:]
        
        return normalized
    
    def filter_hesitation_words(self, text: str) -> str:
        """Mock filter hesitation words from text."""
        self.method_calls["filter_hesitation_words"] += 1
        
        if not text:
            return ""
        
        # Simple mock implementation
        hesitations = ["um", "uh", "eh", "er", "ah", "mm", "hmm", "umm", "ahm", "ehm"]
        words = text.split()
        filtered_words = [word for word in words if word.lower() not in hesitations]
        
        return " ".join(filtered_words)
    
    def filter_low_confidence(self, 
                             segments: List[Dict[str, Any]], 
                             threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Filter out low confidence segments."""
        self.method_calls["filter_low_confidence"] += 1
        
        if not segments:
            return []
            
        threshold = threshold if threshold is not None else self.confidence_threshold
        
        return [seg for seg in segments if seg.get("confidence", 1.0) >= threshold]
    
    def extract_metadata(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from transcription result."""
        self.method_calls["extract_metadata"] += 1
        
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
        """Format the processed transcription for LLM input."""
        self.method_calls["format_for_language_model"] += 1
        
        # Create LLM input context
        llm_input = {
            "transcript": processed_result["text"],
            "confidence": processed_result.get("confidence", 0.0),
            "metadata": processed_result.get("metadata", {})
        }
        
        return llm_input
    
    def configure(self, **kwargs) -> None:
        """Update configuration parameters."""
        self.method_calls["configure"] += 1
        
        for param, value in kwargs.items():
            if param == "capitalize_sentences" and isinstance(value, bool):
                self.capitalize_sentences = value
            elif param == "filter_hesitations" and isinstance(value, bool):
                self.filter_hesitations = value
            elif param == "confidence_threshold" and isinstance(value, (int, float)):
                self.confidence_threshold = min(1.0, max(0.0, value))