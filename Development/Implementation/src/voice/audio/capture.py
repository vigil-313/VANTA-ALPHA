#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio capture module for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-002 - Design for swappable TTS/STT components

import pyaudio
import numpy as np
import threading
import collections
import logging
import time
from typing import Callable, List, Optional, Dict, Any, Deque

logger = logging.getLogger(__name__)

class AudioCapture:
    """
    Handles real-time audio capture from the microphone.
    
    Features:
    - Real-time audio capture using PyAudio
    - Configurable sample rate, bit depth, and channels
    - Circular buffer for storing recent audio
    - Thread-safe access to audio data
    - Callback support for processing new audio chunks
    """
    
    def __init__(self, 
                 sample_rate: int = 16000, 
                 chunk_size: int = 4096, 
                 channels: int = 1, 
                 buffer_seconds: float = 5,
                 device_index: Optional[int] = None):
        """Initialize audio capture system.
        
        Args:
            sample_rate: Sampling rate in Hz
            chunk_size: Number of frames per buffer
            channels: Number of audio channels (1 for mono)
            buffer_seconds: Size of circular buffer in seconds
            device_index: PyAudio device index, None for default
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = pyaudio.paInt16  # 16-bit audio format
        self.device_index = device_index
        
        # Calculate buffer size based on seconds
        buffer_length = int(buffer_seconds * sample_rate * channels / chunk_size)
        self.audio_buffer: Deque[np.ndarray] = collections.deque(maxlen=buffer_length)
        
        # PyAudio objects (initialized in start())
        self.pa = None
        self.stream = None
        
        # Thread safety
        self.lock = threading.RLock()
        self.is_running = False
        
        # Callbacks for new audio data
        self.callbacks: List[Callable[[np.ndarray], None]] = []
        
        # Stats
        self.stats = {
            "chunks_captured": 0,
            "audio_level_peak": 0.0,
            "audio_level_avg": 0.0,
            "dropped_chunks": 0,
            "start_time": None
        }
    
    def start(self) -> bool:
        """
        Start audio capture.
        
        Returns:
            True if started successfully, False otherwise
        """
        with self.lock:
            if self.is_running:
                logger.warning("Audio capture already running")
                return False
            
            # Initialize PyAudio
            try:
                self.pa = pyaudio.PyAudio()
                
                # Open audio stream
                self.stream = self.pa.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    input_device_index=self.device_index,
                    stream_callback=self._audio_callback
                )
                
                self.is_running = True
                self.stats["start_time"] = time.time()
                logger.info(f"Audio capture started: {self.sample_rate}Hz, "
                           f"{self.channels} channel(s), {self.chunk_size} chunk size")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to start audio capture: {e}")
                self._cleanup()
                return False
    
    def stop(self) -> None:
        """Stop audio capture and release resources."""
        with self.lock:
            if not self.is_running:
                logger.debug("Audio capture already stopped")
                return
            
            self._cleanup()
            logger.info("Audio capture stopped")
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.warning(f"Error stopping audio stream: {e}")
            finally:
                self.stream = None
        
        if self.pa:
            try:
                self.pa.terminate()
            except Exception as e:
                logger.warning(f"Error terminating PyAudio: {e}")
            finally:
                self.pa = None
                
        self.is_running = False
    
    def _audio_callback(self, in_data, frame_count, time_info, status) -> tuple:
        """
        Callback function called by PyAudio when new audio data is available.
        
        Args:
            in_data: Audio data buffer
            frame_count: Number of frames
            time_info: Dictionary with timing information
            status: Status flag (0 for success)
            
        Returns:
            Tuple (None, pyaudio.paContinue)
        """
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        try:
            # Convert buffer to numpy array (int16 format)
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            
            # Add to circular buffer
            with self.lock:
                self.audio_buffer.append(audio_data.copy())
                
                # Update stats
                self.stats["chunks_captured"] += 1
                if len(audio_data) > 0:
                    peak = np.abs(audio_data).max() / 32768.0  # Normalize to 0-1
                    self.stats["audio_level_peak"] = max(self.stats["audio_level_peak"], peak)
                    
                    # Running average of audio level
                    avg = np.abs(audio_data).mean() / 32768.0
                    self.stats["audio_level_avg"] = (
                        0.95 * self.stats["audio_level_avg"] + 0.05 * avg
                        if self.stats["chunks_captured"] > 1 else avg
                    )
            
            # Notify callbacks
            self._notify_callbacks(audio_data)
            
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
            self.stats["dropped_chunks"] += 1
        
        return (None, pyaudio.paContinue)
    
    def _notify_callbacks(self, audio_data: np.ndarray) -> None:
        """
        Notify all registered callbacks with new audio data.
        
        Args:
            audio_data: Audio data as numpy array
        """
        for callback in self.callbacks:
            try:
                callback(audio_data)
            except Exception as e:
                logger.error(f"Error in audio callback handler: {e}")
    
    def get_latest_audio(self, seconds: Optional[float] = None) -> np.ndarray:
        """
        Get the latest N seconds of audio from the buffer.
        
        Args:
            seconds: Amount of audio to return in seconds, or None for all available
            
        Returns:
            Numpy array with audio data
        """
        with self.lock:
            if not self.audio_buffer:
                return np.array([], dtype=np.int16)
            
            if seconds is None:
                # Return all audio in buffer
                return np.concatenate(list(self.audio_buffer))
            
            # Calculate number of samples needed
            samples_needed = int(seconds * self.sample_rate)
            
            # Convert buffer to a flat array
            all_audio = np.concatenate(list(self.audio_buffer))
            
            # Return the most recent samples
            if samples_needed >= len(all_audio):
                return all_audio
            else:
                return all_audio[-samples_needed:]
    
    def add_callback(self, callback_fn: Callable[[np.ndarray], None]) -> None:
        """
        Add a callback function that's called with new audio chunks.
        
        Args:
            callback_fn: Function that takes a numpy array of audio data
        """
        if callback_fn not in self.callbacks:
            self.callbacks.append(callback_fn)
    
    def remove_callback(self, callback_fn: Callable[[np.ndarray], None]) -> None:
        """
        Remove a previously registered callback function.
        
        Args:
            callback_fn: Function to remove
        """
        if callback_fn in self.callbacks:
            self.callbacks.remove(callback_fn)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current audio capture statistics.
        
        Returns:
            Dictionary with capture statistics
        """
        with self.lock:
            stats = self.stats.copy()
            if stats["start_time"]:
                stats["uptime_seconds"] = time.time() - stats["start_time"]
            return stats
    
    def list_devices(self) -> List[Dict[str, Any]]:
        """
        List available audio input devices.
        
        Returns:
            List of dictionaries with device information
        """
        temp_pa = pyaudio.PyAudio()
        devices = []
        
        try:
            for i in range(temp_pa.get_device_count()):
                device_info = temp_pa.get_device_info_by_index(i)
                # Handle device info format - mock objects in tests might have different keys
                devices.append({
                    "index": i,
                    "name": device_info.get("name", f"Device {i}"),
                    "channels": device_info.get("maxInputChannels", 1),
                    "default_sample_rate": device_info.get("defaultSampleRate", 44100)
                })
        finally:
            temp_pa.terminate()
            
        return devices
    
    def __enter__(self):
        """Context manager enter - starts capture."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stops capture."""
        self.stop()