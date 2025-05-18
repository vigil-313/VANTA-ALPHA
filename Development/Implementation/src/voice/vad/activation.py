#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Activation management for VANTA Voice Pipeline.

This module provides components for wake word detection and activation state management.
"""
# TASK-REF: VOICE_002 - Voice Activity Detection
# CONCEPT-REF: CON-VOICE-010 - Wake Word Detector
# CONCEPT-REF: CON-VOICE-011 - Activation Manager
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-004 - Support multiple activation modes

import logging
import threading
import time
import numpy as np
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from datetime import datetime, timedelta

from voice.vad.detector import VoiceActivityDetector

logger = logging.getLogger(__name__)

class ActivationMode(Enum):
    """Activation modes for VANTA."""
    WAKE_WORD = "wake_word"   # Activate on wake word detection
    CONTINUOUS = "continuous"  # Always listen and process
    SCHEDULED = "scheduled"    # Activate on schedule
    MANUAL = "manual"          # Activate only on manual trigger
    OFF = "off"                # No activation (disabled)

class ActivationState(Enum):
    """Activation states for VANTA."""
    INACTIVE = "inactive"      # Not actively listening
    LISTENING = "listening"    # Listening for wake word or commands
    ACTIVE = "active"          # Fully activated and processing
    PROCESSING = "processing"  # Processing a command or request

class WakeWordDetector:
    """
    Wake word detection for VANTA.
    
    Detects specific wake word phrases in audio to trigger system activation.
    """
    
    def __init__(self,
                 wake_word: str = "hey vanta",
                 threshold: float = 0.7,
                 sample_rate: int = 16000,
                 vad: Optional[VoiceActivityDetector] = None):
        """
        Initialize wake word detector.
        
        Args:
            wake_word: The wake word or phrase to detect
            threshold: Detection threshold (0-1)
            sample_rate: Audio sample rate in Hz
            vad: Optional VoiceActivityDetector instance to use for initial speech detection
        """
        self.wake_word = wake_word.lower()
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.vad = vad or VoiceActivityDetector(
            model_type="silero",
            sample_rate=sample_rate,
            threshold=0.5  # Lower threshold for VAD to be more sensitive
        )
        
        # Custom wake words dictionary (phrase -> samples)
        self.custom_wake_words = {}
        
        # Timestamp of last detection
        self.last_detection_time = 0.0
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        logger.info(f"Initialized WakeWordDetector with wake word: '{wake_word}'")
    
    def detect(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Detect wake word in audio data.
        
        Args:
            audio_data: Numpy array of audio samples
            
        Returns:
            Dict with detection results:
            {
                "detected": bool,
                "confidence": float,
                "timestamp_ms": int  # Position in audio
            }
        """
        with self._lock:
            # First check if there's any speech using VAD
            # This is a quick check to avoid more expensive processing if there's no speech
            vad_result = self.vad.detect_speech(audio_data)
            
            if not vad_result["is_speech"]:
                return {
                    "detected": False,
                    "confidence": 0.0,
                    "timestamp_ms": 0
                }
            
            # TODO: Implement actual wake word detection based on speech-to-text
            # This is a placeholder implementation that will be replaced with proper
            # wake word detection in the future.
            
            # For now, we'll just simulate wake word detection using a probability
            # based on speech confidence, simulating what a real wake word detector might return.
            # This simple implementation helps us progress with the activation system
            # while waiting for real wake word detection implementation.
            
            confidence = 0.0
            timestamp_ms = 0
            detected = False
            
            # Simple simulator for wake word detection
            # In a real implementation, we would convert speech to text and check for the wake word
            if vad_result["confidence"] > 0.7:  # Strong speech detection
                # Simulate 20% chance of wake word for testing
                # In a real implementation, this would be a sophisticated wake word detection algorithm
                import random
                if random.random() < 0.2:  # 20% chance of "detecting" wake word
                    confidence = random.uniform(0.7, 0.95)  # Random confidence
                    detected = True
                    
                    # Use first speech segment as timestamp for wake word
                    if vad_result["speech_segments"]:
                        timestamp_ms = vad_result["speech_segments"][0][0]
                    
                    # Record detection time
                    self.last_detection_time = time.time()
                    
                    logger.info(f"Wake word detected with confidence {confidence}")
            
            return {
                "detected": detected,
                "confidence": confidence,
                "timestamp_ms": timestamp_ms
            }
    
    def add_custom_wake_word(self, phrase: str, samples: Optional[np.ndarray] = None) -> None:
        """
        Add a custom wake word or phrase.
        
        Args:
            phrase: Text of the wake word/phrase
            samples: Optional audio samples of the phrase
        """
        with self._lock:
            # Store the custom wake word
            if samples is not None:
                self.custom_wake_words[phrase.lower()] = samples
                logger.info(f"Added custom wake word: '{phrase}' with audio samples")
            else:
                self.custom_wake_words[phrase.lower()] = None
                logger.info(f"Added custom wake word: '{phrase}' without audio samples")
    
    def set_wake_word(self, wake_word: str) -> None:
        """
        Set the primary wake word.
        
        Args:
            wake_word: The new wake word or phrase
        """
        with self._lock:
            self.wake_word = wake_word.lower()
            logger.info(f"Set primary wake word to: '{wake_word}'")
    
    def set_threshold(self, threshold: float) -> None:
        """
        Set the detection threshold.
        
        Args:
            threshold: New detection threshold (0-1)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")
        
        with self._lock:
            self.threshold = threshold
            logger.info(f"Set wake word detection threshold to {threshold}")

class ActivationManager:
    """
    Activation manager for VANTA Voice Pipeline.
    
    Manages different activation modes (wake word, continuous, scheduled, manual)
    and handles state transitions between inactive, listening, active, and processing.
    """
    
    def __init__(self,
                 mode: Union[ActivationMode, str] = ActivationMode.WAKE_WORD,
                 vad: Optional[VoiceActivityDetector] = None,
                 wake_word_detector: Optional[WakeWordDetector] = None,
                 energy_threshold: float = 0.01,
                 timeout_s: int = 30):
        """
        Initialize activation manager.
        
        Args:
            mode: Initial activation mode
            vad: VoiceActivityDetector instance
            wake_word_detector: WakeWordDetector instance
            energy_threshold: Energy threshold for pre-filtering
            timeout_s: Seconds of inactivity before returning to inactive
        """
        # Convert string to enum if needed
        if isinstance(mode, str):
            self.mode = ActivationMode(mode)
        else:
            self.mode = mode
        
        # Initialize components if not provided
        self.vad = vad or VoiceActivityDetector()
        self.wake_word_detector = wake_word_detector or WakeWordDetector(vad=self.vad)
        
        # Configuration
        self.energy_threshold = energy_threshold
        self.timeout_s = timeout_s
        
        # State tracking
        self.state = ActivationState.INACTIVE
        self.activation_time = None
        self.timeout_time = None
        
        # Callback tracking
        self.state_change_callbacks = []
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        logger.info(f"Initialized ActivationManager in mode: {self.mode.value}")
    
    def process_audio(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Process audio and update activation state.
        
        Args:
            audio_data: Numpy array of audio samples
            
        Returns:
            Dict with updated state info:
            {
                "state": ActivationState,
                "is_speech": bool,
                "wake_word_detected": bool,
                "should_process": bool  # Whether STT should process
            }
        """
        with self._lock:
            # Quick energy check for silence
            is_silent = self.vad.is_silence(audio_data, self.energy_threshold)
            
            # Initialize result
            result = {
                "state": self.state,
                "is_speech": False,
                "wake_word_detected": False,
                "should_process": False
            }
            
            # Handle different modes
            if self.mode == ActivationMode.OFF:
                # System is off, do nothing
                return result
            
            elif self.mode == ActivationMode.CONTINUOUS:
                # In continuous mode, always process speech
                if not is_silent:
                    # Get speech detection
                    vad_result = self.vad.detect_speech(audio_data)
                    result["is_speech"] = vad_result["is_speech"]
                    
                    if vad_result["is_speech"]:
                        # In continuous mode, any speech should be processed
                        result["should_process"] = True
                        
                        # Transition to ACTIVE state if currently INACTIVE or LISTENING
                        if self.state in [ActivationState.INACTIVE, ActivationState.LISTENING]:
                            self._set_state(ActivationState.ACTIVE)
                            result["state"] = self.state
                        
                        # Update timeout
                        self._reset_timeout()
            
            elif self.mode == ActivationMode.WAKE_WORD:
                # In wake word mode, only process after wake word detection
                if not is_silent:
                    # First, get speech detection
                    vad_result = self.vad.detect_speech(audio_data)
                    result["is_speech"] = vad_result["is_speech"]
                    
                    if self.state == ActivationState.INACTIVE:
                        # In INACTIVE state, listen for wake word
                        if vad_result["is_speech"]:
                            # Transition to LISTENING state
                            self._set_state(ActivationState.LISTENING)
                            result["state"] = self.state
                    
                    if self.state == ActivationState.LISTENING:
                        # In LISTENING state, check for wake word
                        if vad_result["is_speech"]:
                            # Check for wake word
                            wake_word_result = self.wake_word_detector.detect(audio_data)
                            result["wake_word_detected"] = wake_word_result["detected"]
                            
                            if wake_word_result["detected"]:
                                # Wake word detected, transition to ACTIVE state
                                self._set_state(ActivationState.ACTIVE)
                                result["state"] = self.state
                                self._reset_timeout()
                                
                                # But don't process this audio chunk since it contains the wake word
                                result["should_process"] = False
                    
                    elif self.state == ActivationState.ACTIVE:
                        # In ACTIVE state, process all speech
                        if vad_result["is_speech"]:
                            # Process this speech
                            result["should_process"] = True
                            self._reset_timeout()
                        elif self.timeout_time and datetime.now() > self.timeout_time:
                            # No speech and timeout reached, transition back to INACTIVE
                            self._set_state(ActivationState.INACTIVE)
                            result["state"] = self.state
                    
                    elif self.state == ActivationState.PROCESSING:
                        # In PROCESSING state, we're already handling a request
                        # Don't process additional audio until current processing completes
                        result["should_process"] = False
            
            elif self.mode == ActivationMode.MANUAL:
                # In manual mode, only process when explicitly activated
                if self.state == ActivationState.ACTIVE:
                    # Only check for speech if already activated
                    if not is_silent:
                        vad_result = self.vad.detect_speech(audio_data)
                        result["is_speech"] = vad_result["is_speech"]
                        
                        if vad_result["is_speech"]:
                            # Process speech when active
                            result["should_process"] = True
                            self._reset_timeout()
                        elif self.timeout_time and datetime.now() > self.timeout_time:
                            # No speech and timeout reached, transition back to INACTIVE
                            self._set_state(ActivationState.INACTIVE)
                            result["state"] = self.state
            
            elif self.mode == ActivationMode.SCHEDULED:
                # TODO: Implement scheduled activation logic
                # This is a placeholder for scheduled activation
                logger.warning("Scheduled activation mode not fully implemented")
            
            # Check for timeout in active states
            self._check_timeout()
            
            return result
    
    def set_mode(self, mode: Union[ActivationMode, str]) -> None:
        """
        Change the activation mode.
        
        Args:
            mode: New activation mode (ActivationMode enum or string)
        """
        with self._lock:
            # Convert string to enum if needed
            if isinstance(mode, str):
                try:
                    mode = ActivationMode(mode)
                except ValueError:
                    valid_modes = [m.value for m in ActivationMode]
                    raise ValueError(f"Invalid activation mode: {mode}. Valid modes: {valid_modes}")
            
            # Set new mode
            old_mode = self.mode
            self.mode = mode
            
            logger.info(f"Changed activation mode from {old_mode.value} to {mode.value}")
            
            # Reset state
            if mode == ActivationMode.OFF:
                self._set_state(ActivationState.INACTIVE)
            elif mode == ActivationMode.CONTINUOUS:
                self._set_state(ActivationState.LISTENING)
            else:
                self._set_state(ActivationState.INACTIVE)
    
    def reset(self) -> None:
        """Reset to inactive state."""
        with self._lock:
            self._set_state(ActivationState.INACTIVE)
            self.activation_time = None
            self.timeout_time = None
            
            # Reset VAD and wake word detector
            self.vad.reset()
            
            logger.info("Reset activation state to INACTIVE")
    
    def add_state_change_listener(self, callback_fn: Callable[[ActivationState, ActivationState], None]) -> None:
        """
        Add callback for state change events.
        
        Args:
            callback_fn: Function to call when state changes. Takes old_state and new_state parameters.
        """
        with self._lock:
            self.state_change_callbacks.append(callback_fn)
    
    def remove_state_change_listener(self, callback_fn: Callable[[ActivationState, ActivationState], None]) -> bool:
        """
        Remove a state change callback.
        
        Args:
            callback_fn: The callback function to remove
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        with self._lock:
            if callback_fn in self.state_change_callbacks:
                self.state_change_callbacks.remove(callback_fn)
                return True
            return False
    
    def extend_timeout(self, seconds: int = 30) -> None:
        """
        Extend the timeout for the current activation.
        
        Args:
            seconds: Additional seconds to extend timeout by
        """
        with self._lock:
            if self.state in [ActivationState.ACTIVE, ActivationState.PROCESSING]:
                self.timeout_time = datetime.now() + timedelta(seconds=seconds)
                logger.info(f"Extended activation timeout by {seconds}s")
    
    def activate(self) -> bool:
        """
        Manually activate the system.
        
        Returns:
            True if activation successful, False otherwise
        """
        with self._lock:
            if self.mode == ActivationMode.OFF:
                logger.warning("Cannot activate: system is in OFF mode")
                return False
            
            # Transition to ACTIVE state
            self._set_state(ActivationState.ACTIVE)
            self._reset_timeout()
            
            logger.info("Manual activation successful")
            return True
    
    def deactivate(self) -> None:
        """Manually deactivate the system."""
        with self._lock:
            if self.state != ActivationState.INACTIVE:
                self._set_state(ActivationState.INACTIVE)
                logger.info("Manual deactivation successful")
    
    def set_processing(self) -> None:
        """Set state to PROCESSING when beginning to process a command."""
        with self._lock:
            if self.state == ActivationState.ACTIVE:
                self._set_state(ActivationState.PROCESSING)
                self._reset_timeout()
    
    def set_active(self) -> None:
        """Set state back to ACTIVE when done processing a command."""
        with self._lock:
            if self.state == ActivationState.PROCESSING:
                self._set_state(ActivationState.ACTIVE)
                self._reset_timeout()
    
    def _set_state(self, new_state: ActivationState) -> None:
        """
        Internal method to change state and fire callbacks.
        
        Args:
            new_state: New state to transition to
        """
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            
            # Set activation time if becoming active
            if new_state in [ActivationState.ACTIVE, ActivationState.PROCESSING]:
                self.activation_time = datetime.now()
                self._reset_timeout()
            
            # Call all registered callbacks
            for callback in self.state_change_callbacks:
                try:
                    callback(old_state, new_state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {e}")
            
            logger.info(f"State changed: {old_state.value} -> {new_state.value}")
    
    def _reset_timeout(self) -> None:
        """Reset the inactivity timeout."""
        self.timeout_time = datetime.now() + timedelta(seconds=self.timeout_s)
    
    def _check_timeout(self) -> None:
        """Check if timeout has been reached and deactivate if needed."""
        if self.timeout_time and self.state in [ActivationState.ACTIVE, ActivationState.PROCESSING]:
            if datetime.now() > self.timeout_time:
                logger.info(f"Activation timeout reached after {self.timeout_s}s of inactivity")
                self._set_state(ActivationState.INACTIVE)
    
    def get_active_duration(self) -> Optional[float]:
        """
        Get duration of current activation in seconds.
        
        Returns:
            Duration in seconds or None if not active
        """
        if self.state in [ActivationState.ACTIVE, ActivationState.PROCESSING] and self.activation_time:
            return (datetime.now() - self.activation_time).total_seconds()
        return None