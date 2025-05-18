#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock Voice Activity Detection for testing.
"""
# TASK-REF: VOICE_002 - Voice Activity Detection
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

import numpy as np
from typing import Dict, Any, Optional, List, Tuple

class MockVAD:
    """Mock Voice Activity Detector for testing."""
    
    def __init__(self, 
                model_type: str = "silero",
                threshold: float = 0.5,
                window_size_ms: int = 96,
                sample_rate: int = 16000,
                min_silence_duration_ms: int = 500,
                speech_pad_ms: int = 30):
        """
        Initialize mock VAD.
        
        Args:
            model_type: Type of VAD model to simulate
            threshold: Voice detection threshold
            window_size_ms: Window size in milliseconds
            sample_rate: Audio sample rate
            min_silence_duration_ms: Minimum silence duration in ms
            speech_pad_ms: Speech padding in ms
        """
        self.model_type = model_type
        self.threshold = threshold
        self.window_size_ms = window_size_ms
        self.sample_rate = sample_rate
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        
        # Track method calls
        self.method_calls = {
            "is_speech": 0,
            "detect_speech_segments": 0,
            "reset": 0,
            "configure": 0
        }
        
        # Stateful detection
        self._audio_buffer = []
        self._is_speech_state = False
        self._speech_start_time = 0
        self._silence_start_time = 0
        self._is_active = False
        
    def is_speech(self, audio_data: np.ndarray) -> bool:
        """
        Detect if audio segment contains speech.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            True if speech detected, False otherwise
        """
        self.method_calls["is_speech"] += 1
        
        # Simple heuristic: check if average energy exceeds threshold
        energy = np.mean(np.abs(audio_data))
        is_speech = energy > self.threshold
        
        return is_speech
    
    def detect_speech_segments(self, 
                              audio_data: np.ndarray,
                              return_seconds: bool = True) -> List[Tuple[float, float]]:
        """
        Detect speech segments in audio.
        
        Args:
            audio_data: Audio data as numpy array
            return_seconds: Whether to return times in seconds
            
        Returns:
            List of (start_time, end_time) tuples
        """
        self.method_calls["detect_speech_segments"] += 1
        
        # Calculate energy
        energy = np.abs(audio_data)
        mean_energy = np.mean(energy)
        
        # Simple threshold-based segmentation
        is_speech = energy > (mean_energy * 0.5)
        
        # Find segment boundaries
        changes = np.diff(np.concatenate(([0], is_speech.astype(int), [0])))
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]
        
        # Create segments
        segments = []
        
        for start, end in zip(starts, ends - 1):
            # Window size in samples
            window_samples = int(self.window_size_ms * self.sample_rate / 1000)
            
            # Minimum segment duration
            min_samples = int(self.min_silence_duration_ms * self.sample_rate / 1000)
            
            if end - start >= min_samples:
                if return_seconds:
                    # Convert to seconds
                    start_time = start / self.sample_rate
                    end_time = end / self.sample_rate
                    segments.append((start_time, end_time))
                else:
                    # Use sample indices
                    segments.append((start, end))
        
        return segments
    
    def reset(self) -> None:
        """Reset stateful detection."""
        self.method_calls["reset"] += 1
        self._audio_buffer = []
        self._is_speech_state = False
        
    def configure(self, **kwargs) -> None:
        """Update configuration."""
        self.method_calls["configure"] += 1
        
        for param, value in kwargs.items():
            if hasattr(self, param) and param not in ["method_calls", "_audio_buffer", "_is_speech_state"]:
                setattr(self, param, value)
    
    def _simulate_speech(self, text: str) -> np.ndarray:
        """
        Simulate speech audio based on text (for testing)
        
        Args:
            text: Text to simulate
            
        Returns:
            Speech audio as numpy array
        """
        # Create dummy audio proportional to text length
        duration = 0.1 * len(text)  # Roughly 0.1s per character
        samples = int(duration * self.sample_rate)
        
        # Create sine wave with frequency based on text hash
        text_hash = hash(text) % 200
        frequency = 300 + text_hash  # Range 300-500 Hz
        
        t = np.linspace(0, duration, samples, False)
        audio = np.sin(2 * np.pi * frequency * t)
        
        # Add noise
        noise = np.random.normal(0, 0.01, samples)
        audio = audio + noise
        
        # Normalize
        audio = audio / np.max(np.abs(audio))
        
        return audio