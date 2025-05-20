#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fallback implementations for platform abstraction layer.

This module provides minimal fallback implementations that can be used when
platform-specific implementations are not available.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

import numpy as np
import logging
import time
import threading
from typing import List, Dict, Any, Callable, Optional
from .interface import PlatformAudioCapture, PlatformAudioPlayback, PlatformHardwareAcceleration
from .capabilities import capability_registry, CapabilityStatus

logger = logging.getLogger(__name__)


class FallbackAudioCapture(PlatformAudioCapture):
    """Fallback implementation of platform audio capture (simulated)."""
    
    def __init__(self):
        """Initialize fallback audio capture."""
        logger.warning("Using fallback audio capture implementation (simulated)")
        self._sample_rate = 16000
        self._channels = 1
        self._chunk_size = 1024
        self._callbacks = []
        self._is_capturing = False
        self._capture_thread = None
        self._stop_event = threading.Event()
        capability_registry.register_capability(
            "audio.capture.fallback", 
            CapabilityStatus.SIMULATED,
            {"status": "fallback implementation", "simulated": True}
        )
    
    def initialize(self, sample_rate: int, channels: int, chunk_size: int) -> bool:
        """Initialize fallback audio capture resources.
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            chunk_size: Audio buffer chunk size
            
        Returns:
            True (simulated success)
        """
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size
        logger.warning(
            f"Initialized fallback audio capture (simulated): "
            f"sample_rate={sample_rate}, channels={channels}, chunk_size={chunk_size}"
        )
        return True
    
    def _simulate_audio_capture(self):
        """Thread function that simulates audio capture by generating silence."""
        logger.info("Starting simulated audio capture thread")
        
        while not self._stop_event.is_set():
            # Generate silent audio (zeros)
            silent_audio = np.zeros(self._chunk_size, dtype=np.int16)
            
            # Call registered callbacks with silent audio
            for callback in self._callbacks:
                try:
                    callback(silent_audio)
                except Exception as e:
                    logger.error(f"Error in audio callback: {str(e)}")
            
            # Sleep to simulate real-time audio capture
            # Calculate sleep time based on chunk size and sample rate
            sleep_time = self._chunk_size / self._sample_rate
            time.sleep(sleep_time)
        
        logger.info("Stopped simulated audio capture thread")
    
    def start_capture(self) -> bool:
        """Start fallback audio capture (simulated).
        
        Returns:
            True (simulated success)
        """
        if self._is_capturing:
            logger.warning("Fallback audio capture already started")
            return True
        
        self._stop_event.clear()
        self._capture_thread = threading.Thread(
            target=self._simulate_audio_capture,
            daemon=True
        )
        self._capture_thread.start()
        self._is_capturing = True
        
        logger.warning(
            f"Started fallback audio capture (simulated): "
            f"{self._sample_rate}Hz, {self._channels} channels"
        )
        return True
    
    def stop_capture(self) -> None:
        """Stop fallback audio capture and release resources (simulated)."""
        if not self._is_capturing:
            return
        
        self._stop_event.set()
        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None
        
        self._is_capturing = False
        logger.warning("Stopped fallback audio capture (simulated)")
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices (simulated).
        
        Returns:
            List with single simulated device
        """
        logger.warning("Using fallback audio device enumeration (simulated)")
        return [{
            "id": "fallback",
            "name": "Fallback Simulated Input",
            "channels": 1,
            "default_sample_rate": 16000,
            "is_default": True
        }]
    
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select input device (simulated).
        
        Args:
            device_id: Device identifier (ignored)
            
        Returns:
            True (simulated success)
        """
        logger.warning(f"Using fallback audio device selection (simulated, device_id={device_id})")
        return True
    
    def register_callback(self, callback_fn: Callable[[np.ndarray], None]) -> None:
        """Register callback function to receive audio data.
        
        Args:
            callback_fn: Function to call with new audio data
        """
        if callback_fn not in self._callbacks:
            self._callbacks.append(callback_fn)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities for fallback audio capture (simulated).
        
        Returns:
            Dict of simulated capabilities
        """
        return {
            "sample_rates": [8000, 16000, 22050, 44100, 48000],
            "bit_depths": [16],
            "channels": [1, 2],
            "api": "Fallback",
            "simulated": True
        }


class FallbackAudioPlayback(PlatformAudioPlayback):
    """Fallback implementation of platform audio playback (simulated)."""
    
    def __init__(self):
        """Initialize fallback audio playback."""
        logger.warning("Using fallback audio playback implementation (simulated)")
        self._sample_rate = 16000
        self._channels = 1
        self._buffer_size = 1024
        self._is_playing = False
        self._next_playback_id = 1
        capability_registry.register_capability(
            "audio.playback.fallback", 
            CapabilityStatus.SIMULATED,
            {"status": "fallback implementation", "simulated": True}
        )
    
    def initialize(self, sample_rate: int, channels: int, buffer_size: int) -> bool:
        """Initialize fallback audio playback resources.
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            buffer_size: Audio buffer size
            
        Returns:
            True (simulated success)
        """
        self._sample_rate = sample_rate
        self._channels = channels
        self._buffer_size = buffer_size
        logger.warning(
            f"Initialized fallback audio playback (simulated): "
            f"sample_rate={sample_rate}, channels={channels}, buffer_size={buffer_size}"
        )
        return True
    
    def start_playback(self) -> bool:
        """Start fallback audio playback system (simulated).
        
        Returns:
            True (simulated success)
        """
        if self._is_playing:
            logger.warning("Fallback audio playback already started")
            return True
        
        self._is_playing = True
        logger.warning("Started fallback audio playback system (simulated)")
        return True
    
    def stop_playback(self) -> None:
        """Stop fallback audio playback and release resources (simulated)."""
        if not self._is_playing:
            return
        
        self._is_playing = False
        logger.warning("Stopped fallback audio playback system (simulated)")
    
    def play_audio(self, audio_data: np.ndarray) -> int:
        """Play audio data (simulated).
        
        Args:
            audio_data: Audio samples as numpy array
            
        Returns:
            Simulated playback ID
        """
        if not self._is_playing:
            logger.warning("Fallback audio playback system not started")
            return -1
        
        playback_id = self._next_playback_id
        self._next_playback_id += 1
        
        # Calculate duration of audio
        duration = len(audio_data) / self._sample_rate
        logger.warning(
            f"Simulating audio playback (ID {playback_id}): "
            f"{len(audio_data)} samples, {duration:.2f} seconds"
        )
        
        # Simulate playback by sleeping
        def simulate_playback():
            time.sleep(duration)
            logger.debug(f"Completed simulated playback ID {playback_id}")
        
        thread = threading.Thread(target=simulate_playback, daemon=True)
        thread.start()
        
        return playback_id
    
    def stop_audio(self, playback_id: int) -> bool:
        """Stop a specific playback operation (simulated).
        
        Args:
            playback_id: Playback ID
            
        Returns:
            True (simulated success)
        """
        logger.warning(f"Simulating stop of audio playback ID {playback_id}")
        return True
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio output devices (simulated).
        
        Returns:
            List with single simulated device
        """
        logger.warning("Using fallback audio device enumeration (simulated)")
        return [{
            "id": "fallback",
            "name": "Fallback Simulated Output",
            "channels": 2,
            "default_sample_rate": 16000,
            "is_default": True
        }]
    
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select output device (simulated).
        
        Args:
            device_id: Device identifier (ignored)
            
        Returns:
            True (simulated success)
        """
        logger.warning(f"Using fallback audio device selection (simulated, device_id={device_id})")
        return True
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities for fallback audio playback (simulated).
        
        Returns:
            Dict of simulated capabilities
        """
        return {
            "sample_rates": [8000, 16000, 22050, 44100, 48000],
            "bit_depths": [16],
            "channels": [1, 2],
            "api": "Fallback",
            "simulated": True
        }


class FallbackHardwareAcceleration(PlatformHardwareAcceleration):
    """Fallback implementation of platform hardware acceleration (simulated)."""
    
    def __init__(self):
        """Initialize fallback hardware acceleration."""
        logger.warning("Using fallback hardware acceleration implementation (simulated)")
        capability_registry.register_capability(
            "acceleration.fallback", 
            CapabilityStatus.SIMULATED,
            {"status": "fallback implementation", "simulated": True}
        )
    
    def initialize(self) -> bool:
        """Initialize fallback hardware acceleration resources.
        
        Returns:
            True (simulated success)
        """
        logger.warning("Initialized fallback hardware acceleration (simulated)")
        return True
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available acceleration devices (simulated).
        
        Returns:
            List with single simulated device
        """
        logger.warning("Using fallback acceleration device enumeration (simulated)")
        return [{
            "id": "fallback",
            "name": "Fallback Simulated Acceleration",
            "type": "CPU",
            "memory": "System RAM",
            "is_default": True
        }]
    
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select acceleration device (simulated).
        
        Args:
            device_id: Device identifier (ignored)
            
        Returns:
            True (simulated success)
        """
        logger.warning(f"Using fallback acceleration device selection (simulated, device_id={device_id})")
        return True
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities for fallback hardware acceleration (simulated).
        
        Returns:
            Dict of simulated capabilities
        """
        return {
            "type": "CPU",
            "features": ["simulated"],
            "api": "Fallback",
            "simulated": True
        }