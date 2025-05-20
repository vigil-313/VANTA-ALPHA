#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform abstraction interfaces for platform-dependent functionality.

This module defines abstract base classes for platform-specific implementations,
ensuring consistent interfaces across different operating systems and hardware.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

from abc import ABC, abstractmethod
import numpy as np
from typing import Callable, List, Dict, Any, Optional


class PlatformAudioCapture(ABC):
    """Abstract base class for platform-specific audio capture implementations."""
    
    @abstractmethod
    def initialize(self, sample_rate: int, channels: int, chunk_size: int) -> bool:
        """Initialize platform-specific audio capture resources.
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            chunk_size: Audio buffer chunk size
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start_capture(self) -> bool:
        """Start audio capture on the platform.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop_capture(self) -> None:
        """Stop audio capture and release platform resources."""
        pass
    
    @abstractmethod
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices on this platform.
        
        Returns:
            List of device descriptors with platform-specific details
        """
        pass
    
    @abstractmethod
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select input device by platform-specific identifier.
        
        Args:
            device_id: Platform-specific device identifier
            
        Returns:
            True if device selection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def register_callback(self, callback_fn: Callable[[np.ndarray], None]) -> None:
        """Register callback function to receive audio data.
        
        Args:
            callback_fn: Function to call with new audio data
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get platform-specific capabilities for audio capture.
        
        Returns:
            Dict of capability names to values or feature flags
        """
        pass


class PlatformAudioPlayback(ABC):
    """Abstract base class for platform-specific audio playback implementations."""
    
    @abstractmethod
    def initialize(self, sample_rate: int, channels: int, buffer_size: int) -> bool:
        """Initialize platform-specific audio playback resources.
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            buffer_size: Audio buffer size
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start_playback(self) -> bool:
        """Start audio playback system.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop_playback(self) -> None:
        """Stop audio playback and release platform resources."""
        pass
    
    @abstractmethod
    def play_audio(self, audio_data: np.ndarray) -> int:
        """Play audio data through platform-specific output.
        
        Args:
            audio_data: Audio samples as numpy array
            
        Returns:
            Platform-specific ID for this playback operation
        """
        pass
    
    @abstractmethod
    def stop_audio(self, playback_id: int) -> bool:
        """Stop a specific playback operation.
        
        Args:
            playback_id: Platform-specific playback ID
            
        Returns:
            True if successfully stopped, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio output devices on this platform.
        
        Returns:
            List of device descriptors with platform-specific details
        """
        pass
    
    @abstractmethod
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select output device by platform-specific identifier.
        
        Args:
            device_id: Platform-specific device identifier
            
        Returns:
            True if device selection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get platform-specific capabilities for audio playback.
        
        Returns:
            Dict of capability names to values or feature flags
        """
        pass


class PlatformHardwareAcceleration(ABC):
    """Abstract base class for platform-specific hardware acceleration."""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize platform-specific acceleration resources.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available acceleration devices on this platform.
        
        Returns:
            List of device descriptors with platform-specific details
        """
        pass
    
    @abstractmethod
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select acceleration device by platform-specific identifier.
        
        Args:
            device_id: Platform-specific device identifier
            
        Returns:
            True if device selection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get platform-specific acceleration capabilities.
        
        Returns:
            Dict of capability names to values or feature flags
        """
        pass