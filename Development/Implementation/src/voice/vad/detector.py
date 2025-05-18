#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voice Activity Detection module for VANTA Voice Pipeline.

This module provides the VoiceActivityDetector component which is responsible for
detecting speech in audio streams using various underlying VAD models.
"""
# TASK-REF: VOICE_002 - Voice Activity Detection
# CONCEPT-REF: CON-VOICE-009 - Voice Activity Detector
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-004 - Support multiple activation modes

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple

from voice.vad.models.silero import SileroVAD
from voice.vad.models.whisper_vad import WhisperVAD

logger = logging.getLogger(__name__)

class VoiceActivityDetector:
    """
    Voice Activity Detector for the VANTA Voice Pipeline.
    
    Provides speech detection capabilities using various underlying models (Silero, Whisper).
    Handles frame-level and utterance-level detection with configurable parameters.
    """
    
    def __init__(self, 
                 model_type: str = "silero",  # or "whisper_vad" 
                 model_path: Optional[str] = None,
                 sample_rate: int = 16000,
                 threshold: float = 0.5,
                 window_size_ms: int = 96,
                 min_speech_duration_ms: int = 250,
                 max_speech_duration_s: int = 30,
                 min_silence_duration_ms: int = 100,
                 use_onnx: bool = True):
        """
        Initialize voice activity detector.
        
        Args:
            model_type: Type of VAD model to use
            model_path: Optional path to model file
            sample_rate: Audio sample rate in Hz
            threshold: Detection threshold (0-1)
            window_size_ms: Analysis window size in milliseconds
            min_speech_duration_ms: Minimum speech segment length
            max_speech_duration_s: Maximum speech segment length
            min_silence_duration_ms: Minimum silence for segmentation
            use_onnx: Whether to use ONNX runtime for inference (faster)
        """
        self.model_type = model_type
        self.sample_rate = sample_rate
        self.threshold = threshold
        
        # Convert time parameters to sample counts
        self.window_size_samples = int((window_size_ms / 1000) * sample_rate)
        
        # Initialize the appropriate model
        if model_type == "silero":
            self.model = SileroVAD(
                model_path=model_path,
                use_onnx=use_onnx,
                sample_rate=sample_rate,
                threshold=threshold,
                window_size_samples=self.window_size_samples,
                min_speech_duration_ms=min_speech_duration_ms,
                max_speech_duration_s=max_speech_duration_s,
                min_silence_duration_ms=min_silence_duration_ms
            )
            logger.info("Initialized Silero VAD detector")
        elif model_type == "whisper_vad":
            # Currently a placeholder - this would be implemented in the future
            # Assuming WhisperVAD will be implemented with a similar interface
            self.model = None  # Replace with WhisperVAD when implemented
            logger.warning("WhisperVAD not yet fully implemented - check models/whisper_vad.py")
        else:
            raise ValueError(f"Unknown VAD model type: {model_type}")
        
        # Tracking variables for continuous detection
        self.is_speaking = False
        self.speech_start_time = 0
        self.current_speech_duration = 0
    
    def detect_speech(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Detect if audio contains speech.
        
        Args:
            audio_data: Numpy array of audio samples
            
        Returns:
            Dict with detection results:
            {
                "is_speech": bool,
                "confidence": float,
                "speech_segments": List of (start_ms, end_ms) tuples
            }
        """
        # Ensure audio_data is the right type
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data, dtype=np.float32)
        
        # Check for empty audio
        if len(audio_data) == 0:
            return {
                "is_speech": False,
                "confidence": 0.0,
                "speech_segments": []
            }
        
        # Normalize audio if not already normalized
        if np.max(np.abs(audio_data)) > 1.0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        
        if self.model_type == "silero":
            # Get simple speech detection
            is_speech, confidence = self.model.is_speech(audio_data)
            
            # Get detailed speech segments
            speech_timestamps = self.model.get_speech_timestamps(audio_data, return_seconds=True)
            
            # Convert to start_ms, end_ms format
            speech_segments = [(
                int(segment["start"] * 1000),  # start in ms
                int(segment["end"] * 1000)     # end in ms
            ) for segment in speech_timestamps]
            
            return {
                "is_speech": is_speech,
                "confidence": float(confidence),
                "speech_segments": speech_segments
            }
        
        elif self.model_type == "whisper_vad":
            # Placeholder for WhisperVAD
            # This will be implemented when WhisperVAD is available
            logger.warning("WhisperVAD detection - Not yet implemented")
            return {
                "is_speech": False,
                "confidence": 0.0,
                "speech_segments": []
            }
        
        else:
            raise ValueError(f"Unknown VAD model type: {self.model_type}")
    
    def reset(self) -> None:
        """Reset detector state (e.g., between processing sessions)."""
        if self.model_type == "silero" and self.model:
            self.model.reset_states()
        elif self.model_type == "whisper_vad" and self.model:
            # Will be implemented when WhisperVAD is available
            pass
        
        # Reset tracking variables
        self.is_speaking = False
        self.speech_start_time = 0
        self.current_speech_duration = 0
    
    def adapt_to_noise(self, background_audio: np.ndarray) -> None:
        """
        Adapt detection thresholds based on background noise.
        
        Args:
            background_audio: Numpy array of background noise samples
        """
        if self.model_type == "silero" and self.model:
            self.model.adapt_to_noise(background_audio)
            # Update threshold to match model
            self.threshold = self.model.threshold
        elif self.model_type == "whisper_vad" and self.model:
            # Will be implemented when WhisperVAD is available
            pass
        
        logger.info(f"Adapted VAD threshold to background noise. New threshold: {self.threshold}")
    
    def set_threshold(self, threshold: float) -> None:
        """
        Dynamically adjust detection threshold.
        
        Args:
            threshold: New detection threshold (0-1)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")
        
        self.threshold = threshold
        
        # Update threshold in the underlying model
        if self.model_type == "silero" and self.model:
            self.model.set_threshold(threshold)
        elif self.model_type == "whisper_vad" and self.model:
            # Will be implemented when WhisperVAD is available
            pass
        
        logger.info(f"Set VAD threshold to {threshold}")
    
    def is_silence(self, audio_data: np.ndarray, energy_threshold: float = 0.01) -> bool:
        """
        Fast check if audio is silent based on energy level.
        
        Useful for pre-filtering before more expensive VAD processing.
        
        Args:
            audio_data: Numpy array of audio samples
            energy_threshold: Energy threshold (0-1)
            
        Returns:
            True if audio is silent (below energy threshold)
        """
        # Ensure audio_data is the right type
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data, dtype=np.float32)
        
        # Normalize audio if not already normalized
        if np.max(np.abs(audio_data)) > 1.0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        
        # Calculate energy (RMS)
        energy = np.sqrt(np.mean(np.square(audio_data)))
        
        return energy < energy_threshold
    
    def get_speech_to_process(self, audio_stream: List[np.ndarray]) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Analyze an audio stream buffer to find complete speech segments.
        
        Useful for continuous processing of audio streams.
        
        Args:
            audio_stream: List of audio chunks in chronological order
            
        Returns:
            Tuple of (speech_ready, speech_audio) where:
                speech_ready: True if complete speech segment is ready
                speech_audio: Numpy array of the complete speech segment or None
        """
        if not audio_stream:
            return False, None
        
        # Concatenate audio chunks
        full_audio = np.concatenate(audio_stream)
        
        # Get speech segments
        result = self.detect_speech(full_audio)
        
        if not result["speech_segments"]:
            return False, None
        
        # Check if the last segment has ended (not cut off)
        last_segment_end_ms = result["speech_segments"][-1][1]
        last_segment_end_samples = int((last_segment_end_ms / 1000) * self.sample_rate)
        
        # If the last segment ends before the end of the audio, it's complete
        if last_segment_end_samples < len(full_audio) - self.window_size_samples:
            # Extract all speech segments combined
            combined_speech = np.array([], dtype=np.float32)
            
            for start_ms, end_ms in result["speech_segments"]:
                start_samples = int((start_ms / 1000) * self.sample_rate)
                end_samples = int((end_ms / 1000) * self.sample_rate)
                
                # Ensure we don't go out of bounds
                start_samples = max(0, min(start_samples, len(full_audio) - 1))
                end_samples = max(0, min(end_samples, len(full_audio)))
                
                # Add padding around speech
                padding_samples = int(0.1 * self.sample_rate)  # 100ms padding
                padded_start = max(0, start_samples - padding_samples)
                padded_end = min(len(full_audio), end_samples + padding_samples)
                
                # Extract and combine speech
                speech_segment = full_audio[padded_start:padded_end]
                combined_speech = np.concatenate([combined_speech, speech_segment])
            
            return True, combined_speech
        
        return False, None