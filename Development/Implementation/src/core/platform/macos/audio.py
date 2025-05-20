#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS-specific audio implementation for the platform abstraction layer.

This module provides concrete implementations of the platform audio interfaces
for macOS, using PyAudio with CoreAudio backend.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

import numpy as np
import pyaudio
import logging
import time
import threading
from typing import List, Dict, Any, Callable, Optional, Set
from ..interface import PlatformAudioCapture, PlatformAudioPlayback
from ..capabilities import capability_registry, CapabilityStatus

logger = logging.getLogger(__name__)


class MacOSAudioCapture(PlatformAudioCapture):
    """macOS implementation of platform audio capture."""
    
    def __init__(self):
        """Initialize macOS audio capture."""
        self._pyaudio = None
        self._stream = None
        self._device_id = None
        self._sample_rate = 16000
        self._channels = 1
        self._chunk_size = 1024
        self._callbacks = []
        self._is_capturing = False
        self._check_capabilities()
    
    def _check_capabilities(self) -> None:
        """Check and register macOS-specific audio capabilities."""
        try:
            self._pyaudio = pyaudio.PyAudio()
            capability_registry.register_capability(
                "audio.capture.macos.pyaudio", 
                CapabilityStatus.AVAILABLE
            )
        except (ImportError, OSError) as e:
            logger.error(f"Failed to initialize PyAudio on macOS: {str(e)}")
            capability_registry.register_capability(
                "audio.capture.macos.pyaudio", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            raise RuntimeError(f"PyAudio initialization failed: {e}")
    
    def initialize(self, sample_rate: int, channels: int, chunk_size: int) -> bool:
        """Initialize macOS audio capture resources.
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            chunk_size: Audio buffer chunk size
            
        Returns:
            True if initialization successful, False otherwise
        """
        if not capability_registry.is_available("audio.capture.macos"):
            logger.error("macOS audio capture capability not available")
            return False
        
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size
        return True
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for incoming audio data."""
        if status:
            logger.warning(f"PyAudio status: {status}")
        
        # Convert to numpy array
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        
        # Call registered callbacks
        for callback in self._callbacks:
            try:
                callback(audio_data)
            except Exception as e:
                logger.error(f"Error in audio callback: {str(e)}")
        
        return (in_data, pyaudio.paContinue)
    
    def start_capture(self) -> bool:
        """Start audio capture on macOS.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self._is_capturing:
            logger.warning("Audio capture already started")
            return True
        
        try:
            # Configure PyAudio stream
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self._channels,
                rate=self._sample_rate,
                input=True,
                output=False,
                frames_per_buffer=self._chunk_size,
                input_device_index=self._device_id,
                stream_callback=self._audio_callback
            )
            
            self._stream.start_stream()
            self._is_capturing = True
            logger.info(f"Started macOS audio capture: {self._sample_rate}Hz, {self._channels} channels")
            return True
        except Exception as e:
            logger.error(f"Failed to start macOS audio capture: {str(e)}")
            return False
    
    def stop_capture(self) -> None:
        """Stop audio capture and release platform resources."""
        if not self._is_capturing:
            return
        
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            
            self._is_capturing = False
            logger.info("Stopped macOS audio capture")
        except Exception as e:
            logger.error(f"Error stopping macOS audio capture: {str(e)}")
        
        # Only terminate PyAudio when truly shutting down to avoid reinitialization issues
        # if self._pyaudio:
        #     self._pyaudio.terminate()
        #     self._pyaudio = None
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices on macOS.
        
        Returns:
            List of device descriptors with platform-specific details
        """
        devices = []
        
        if not self._pyaudio:
            logger.error("PyAudio not initialized")
            return devices
        
        try:
            for i in range(self._pyaudio.get_device_count()):
                device_info = self._pyaudio.get_device_info_by_index(i)
                # Only include input devices
                if device_info["maxInputChannels"] > 0:
                    devices.append({
                        "id": str(i),
                        "name": device_info["name"],
                        "channels": device_info["maxInputChannels"],
                        "default_sample_rate": device_info["defaultSampleRate"],
                        "is_default": device_info.get("isDefaultInputDevice", False)
                    })
        except Exception as e:
            logger.error(f"Error getting macOS audio devices: {str(e)}")
        
        return devices
    
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select input device by macOS-specific identifier.
        
        Args:
            device_id: PyAudio device index as string
            
        Returns:
            True if device selection successful, False otherwise
        """
        if device_id is None:
            # Use default device
            self._device_id = None
            logger.info("Selected default macOS audio input device")
            return True
        
        try:
            index = int(device_id)
            device_info = self._pyaudio.get_device_info_by_index(index)
            if device_info["maxInputChannels"] > 0:
                self._device_id = index
                logger.info(f"Selected macOS audio input device: {device_info['name']}")
                return True
            else:
                logger.error(f"Device {index} is not an input device")
                return False
        except (ValueError, OSError) as e:
            logger.error(f"Error selecting macOS audio device {device_id}: {str(e)}")
            return False
    
    def register_callback(self, callback_fn: Callable[[np.ndarray], None]) -> None:
        """Register callback function to receive audio data.
        
        Args:
            callback_fn: Function to call with new audio data
        """
        if callback_fn not in self._callbacks:
            self._callbacks.append(callback_fn)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get platform-specific capabilities for audio capture.
        
        Returns:
            Dict of capability names to values or feature flags
        """
        caps = {
            "sample_rates": [8000, 16000, 22050, 44100, 48000],
            "bit_depths": [16],
            "channels": [1, 2],
            "api": "CoreAudio"
        }
        
        # Add device-specific capabilities if we have a selected device
        if self._device_id is not None and self._pyaudio:
            try:
                device_info = self._pyaudio.get_device_info_by_index(self._device_id)
                caps["device_sample_rate"] = device_info["defaultSampleRate"]
                caps["device_channels"] = device_info["maxInputChannels"]
            except:
                pass
        
        return caps


class MacOSAudioPlayback(PlatformAudioPlayback):
    """macOS implementation of platform audio playback."""
    
    def __init__(self):
        """Initialize macOS audio playback."""
        self._pyaudio = None
        self._stream = None
        self._device_id = None
        self._sample_rate = 16000
        self._channels = 1
        self._buffer_size = 1024
        self._is_playing = False
        self._playback_queue = {}
        self._next_playback_id = 1
        self._playback_lock = threading.RLock()
        self._check_capabilities()
    
    def _check_capabilities(self) -> None:
        """Check and register macOS-specific audio capabilities."""
        try:
            self._pyaudio = pyaudio.PyAudio()
            capability_registry.register_capability(
                "audio.playback.macos.pyaudio", 
                CapabilityStatus.AVAILABLE
            )
        except (ImportError, OSError) as e:
            logger.error(f"Failed to initialize PyAudio on macOS: {str(e)}")
            capability_registry.register_capability(
                "audio.playback.macos.pyaudio", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            raise RuntimeError(f"PyAudio initialization failed: {e}")
    
    def initialize(self, sample_rate: int, channels: int, buffer_size: int) -> bool:
        """Initialize macOS audio playback resources.
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            buffer_size: Audio buffer size
            
        Returns:
            True if initialization successful, False otherwise
        """
        if not capability_registry.is_available("audio.playback.macos"):
            logger.error("macOS audio playback capability not available")
            return False
        
        self._sample_rate = sample_rate
        self._channels = channels
        self._buffer_size = buffer_size
        return True
    
    def start_playback(self) -> bool:
        """Start audio playback system.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self._is_playing:
            logger.warning("Audio playback already started")
            return True
        
        # We don't actually create a persistent stream here, but rather
        # create streams on-demand for each playback operation
        self._is_playing = True
        logger.info("Started macOS audio playback system")
        return True
    
    def stop_playback(self) -> None:
        """Stop audio playback and release platform resources."""
        if not self._is_playing:
            return
        
        # Cancel all ongoing playbacks
        playback_ids = list(self._playback_queue.keys())
        for playback_id in playback_ids:
            self.stop_audio(playback_id)
        
        # Clean up PyAudio resources
        # Only terminate PyAudio when truly shutting down to avoid reinitialization issues
        # if self._pyaudio:
        #     self._pyaudio.terminate()
        #     self._pyaudio = None
        
        self._is_playing = False
        logger.info("Stopped macOS audio playback system")
    
    def _playback_thread(self, playback_id: int, audio_data: np.ndarray) -> None:
        """Thread function for async audio playback."""
        try:
            stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self._channels,
                rate=self._sample_rate,
                output=True,
                output_device_index=self._device_id,
                frames_per_buffer=self._buffer_size
            )
            
            # Store the stream in the queue for possible cancellation
            with self._playback_lock:
                self._playback_queue[playback_id] = {
                    "stream": stream,
                    "thread": threading.current_thread(),
                    "status": "playing"
                }
            
            # Convert numpy array to bytes
            audio_bytes = audio_data.tobytes()
            
            # Write data to stream
            stream.write(audio_bytes)
            
            # Clean up
            stream.stop_stream()
            stream.close()
            
            # Mark as completed
            with self._playback_lock:
                if playback_id in self._playback_queue:
                    self._playback_queue[playback_id]["status"] = "completed"
                    del self._playback_queue[playback_id]
            
        except Exception as e:
            logger.error(f"Error in macOS audio playback thread: {e}")
            with self._playback_lock:
                if playback_id in self._playback_queue:
                    self._playback_queue[playback_id]["status"] = "error"
                    self._playback_queue[playback_id]["error"] = str(e)
                    del self._playback_queue[playback_id]
    
    def play_audio(self, audio_data: np.ndarray) -> int:
        """Play audio data through platform-specific output.
        
        Args:
            audio_data: Audio samples as numpy array
            
        Returns:
            Platform-specific ID for this playback operation
        """
        if not self._is_playing:
            logger.warning("Audio playback system not started")
            return -1
        
        with self._playback_lock:
            playback_id = self._next_playback_id
            self._next_playback_id += 1
        
        # Start a new thread for this playback
        playback_thread = threading.Thread(
            target=self._playback_thread,
            args=(playback_id, audio_data),
            daemon=True
        )
        playback_thread.start()
        
        logger.debug(f"Started audio playback ID {playback_id} with {len(audio_data)} samples")
        return playback_id
    
    def stop_audio(self, playback_id: int) -> bool:
        """Stop a specific playback operation.
        
        Args:
            playback_id: Platform-specific playback ID
            
        Returns:
            True if successfully stopped, False otherwise
        """
        with self._playback_lock:
            if playback_id in self._playback_queue:
                try:
                    # Stop the stream
                    stream = self._playback_queue[playback_id]["stream"]
                    stream.stop_stream()
                    stream.close()
                    
                    # Mark as cancelled
                    self._playback_queue[playback_id]["status"] = "cancelled"
                    del self._playback_queue[playback_id]
                    
                    logger.debug(f"Stopped audio playback ID {playback_id}")
                    return True
                except Exception as e:
                    logger.error(f"Error stopping audio playback ID {playback_id}: {e}")
                    return False
            else:
                logger.warning(f"Audio playback ID {playback_id} not found")
                return False
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio output devices on macOS.
        
        Returns:
            List of device descriptors with platform-specific details
        """
        devices = []
        
        if not self._pyaudio:
            logger.error("PyAudio not initialized")
            return devices
        
        try:
            for i in range(self._pyaudio.get_device_count()):
                device_info = self._pyaudio.get_device_info_by_index(i)
                # Only include output devices
                if device_info["maxOutputChannels"] > 0:
                    devices.append({
                        "id": str(i),
                        "name": device_info["name"],
                        "channels": device_info["maxOutputChannels"],
                        "default_sample_rate": device_info["defaultSampleRate"],
                        "is_default": device_info.get("isDefaultOutputDevice", False)
                    })
        except Exception as e:
            logger.error(f"Error getting macOS audio devices: {str(e)}")
        
        return devices
    
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select output device by macOS-specific identifier.
        
        Args:
            device_id: PyAudio device index as string
            
        Returns:
            True if device selection successful, False otherwise
        """
        if device_id is None:
            # Use default device
            self._device_id = None
            logger.info("Selected default macOS audio output device")
            return True
        
        try:
            index = int(device_id)
            device_info = self._pyaudio.get_device_info_by_index(index)
            if device_info["maxOutputChannels"] > 0:
                self._device_id = index
                logger.info(f"Selected macOS audio output device: {device_info['name']}")
                return True
            else:
                logger.error(f"Device {index} is not an output device")
                return False
        except (ValueError, OSError) as e:
            logger.error(f"Error selecting macOS audio device {device_id}: {str(e)}")
            return False
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get platform-specific capabilities for audio playback.
        
        Returns:
            Dict of capability names to values or feature flags
        """
        caps = {
            "sample_rates": [8000, 16000, 22050, 44100, 48000],
            "bit_depths": [16],
            "channels": [1, 2],
            "api": "CoreAudio"
        }
        
        # Add device-specific capabilities if we have a selected device
        if self._device_id is not None and self._pyaudio:
            try:
                device_info = self._pyaudio.get_device_info_by_index(self._device_id)
                caps["device_sample_rate"] = device_info["defaultSampleRate"]
                caps["device_channels"] = device_info["maxOutputChannels"]
            except:
                pass
        
        return caps