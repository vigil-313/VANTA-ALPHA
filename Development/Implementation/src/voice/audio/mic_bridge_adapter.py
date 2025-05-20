#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Microphone Bridge Adapter

This module provides a bridge adapter for microphone input that allows
Docker containers on macOS to use the host's microphone.
"""
# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

import os
import time
import json
import uuid
import logging
import threading
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path

# Import the Docker microphone client
# In a production environment, you would package this as a proper module
# For this implementation, we'll use a relative import
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../scripts/demo"))
from docker_mic_client import MicrophoneClient

class MicBridgeAdapter:
    """
    Microphone Bridge Adapter for Docker on macOS
    
    This adapter uses a file-based bridge to enable microphone input
    functionality from Docker containers on macOS by reading audio files
    from a shared directory that is populated by a bridge script running
    on the host.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Microphone Bridge Adapter.
        
        Args:
            config: Configuration dictionary for the adapter
        """
        self.logger = logging.getLogger("mic_bridge_adapter")
        
        # Extract configuration
        self.bridge_dir = config.get("bridge_dir", "/host/vanta-mic-bridge")
        self.sample_rate = config.get("sample_rate", 16000)
        self.channels = config.get("channels", 1)
        self.chunk_duration = config.get("chunk_duration", 0.5)
        self.buffer_size = config.get("buffer_size", 10)  # Number of chunks to buffer
        
        # Runtime state
        self.is_initialized = False
        self.is_capturing = False
        self.mic_client = None
        self.audio_buffer = []
        self.buffer_lock = threading.Lock()
        self.processing_thread = None
        self.stop_event = threading.Event()
        self.capture_uuid = None
        
        # Statistics
        self.stats = {
            "adapter_type": "bridge",
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "total_chunks": 0,
            "total_time": 0,
            "last_latency": 0
        }
        
    def initialize(self) -> bool:
        """
        Initialize the Microphone Bridge Adapter.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Initialize the microphone client
            self.mic_client = MicrophoneClient(
                bridge_dir=self.bridge_dir,
                sample_rate=self.sample_rate,
                channels=self.channels,
                chunk_duration=self.chunk_duration
            )
            
            # Check if bridge is accessible
            status = self.mic_client.get_bridge_status()
            if status.get("status") == "error":
                self.logger.error(f"Bridge error: {status.get('error', 'Unknown error')}")
                return False
                
            self.logger.info(f"Microphone Bridge Adapter initialized with bridge directory: {self.bridge_dir}")
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Microphone Bridge Adapter: {e}")
            return False
    
    def start_capture(self) -> bool:
        """
        Start capturing audio from the microphone.
        
        Returns:
            bool: True if capture started successfully, False otherwise
        """
        if not self.is_initialized:
            self.logger.error("Cannot start capture: adapter not initialized")
            return False
            
        if self.is_capturing:
            self.logger.warning("Audio capture already in progress")
            return True
            
        try:
            # Generate a new UUID for this capture session
            self.capture_uuid = str(uuid.uuid4())
            
            # Start recording via the microphone client
            if not self.mic_client.start_recording():
                self.logger.error("Failed to start microphone recording")
                return False
                
            # Clear the audio buffer
            with self.buffer_lock:
                self.audio_buffer.clear()
                
            # Start the audio processing thread
            self.stop_event.clear()
            self.processing_thread = threading.Thread(target=self._process_audio)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            self.is_capturing = True
            self.logger.info(f"Started audio capture with UUID: {self.capture_uuid}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start audio capture: {e}")
            return False
    
    def stop_capture(self) -> bool:
        """
        Stop capturing audio from the microphone.
        
        Returns:
            bool: True if capture stopped successfully, False otherwise
        """
        if not self.is_capturing:
            self.logger.warning("No audio capture in progress")
            return True
            
        try:
            # Stop the microphone client recording
            if not self.mic_client.stop_recording():
                self.logger.error("Failed to stop microphone recording")
                
            # Stop the processing thread
            self.stop_event.set()
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=5.0)
                
            self.is_capturing = False
            self.logger.info(f"Stopped audio capture with UUID: {self.capture_uuid}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop audio capture: {e}")
            return False
            
    def _process_audio(self):
        """
        Process audio data from the microphone client.
        This method runs in a separate thread and continuously reads
        audio data from the microphone client.
        """
        self.logger.info("Starting audio processing thread")
        
        while not self.stop_event.is_set():
            try:
                # Read audio data from the microphone client
                # Use a short duration to get chunks frequently
                start_time = time.time()
                audio_array, sample_rate, channels = self.mic_client.read_audio(
                    duration=self.chunk_duration, 
                    timeout=2.0
                )
                
                # Calculate latency
                latency = time.time() - start_time
                
                # Skip if no audio data
                if len(audio_array) == 0:
                    time.sleep(0.1)
                    continue
                    
                # Update stats
                self.stats["total_chunks"] += 1
                self.stats["last_latency"] = latency
                self.stats["total_time"] += latency
                
                # Add to buffer
                with self.buffer_lock:
                    self.audio_buffer.append((audio_array, sample_rate, channels))
                    # Limit buffer size
                    if len(self.audio_buffer) > self.buffer_size:
                        self.audio_buffer.pop(0)
                        
                self.logger.debug(f"Processed audio chunk: {len(audio_array)} samples, latency: {latency:.3f}s")
                
            except Exception as e:
                self.logger.error(f"Error processing audio: {e}")
                time.sleep(0.5)
    
    def read_audio(self, duration: Optional[float] = None) -> Tuple[np.ndarray, int]:
        """
        Read audio data from the buffer.
        
        Args:
            duration: Duration of audio to read in seconds (None for all available)
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        if not self.is_capturing:
            self.logger.warning("Not capturing audio, starting now")
            self.start_capture()
            # Allow some time for initial audio capture
            time.sleep(1.0)
        
        # Return empty array if no data
        with self.buffer_lock:
            if not self.audio_buffer:
                return np.array([], dtype=np.int16), self.sample_rate
                
            # Combine audio chunks
            arrays = []
            for audio_array, sample_rate, channels in self.audio_buffer:
                arrays.append(audio_array)
                
            # Clear the buffer after reading
            self.audio_buffer.clear()
            
        # Concatenate arrays
        combined = np.concatenate(arrays)
        
        # If duration is specified, trim to requested duration
        if duration is not None:
            samples_per_second = self.sample_rate * self.channels
            target_samples = int(duration * samples_per_second)
            if len(combined) > target_samples:
                combined = combined[:target_samples]
                
        return combined, self.sample_rate
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the microphone adapter.
        
        Returns:
            Dict containing usage statistics
        """
        return self.stats
        
    def cleanup(self) -> bool:
        """
        Clean up resources used by the microphone adapter.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.is_capturing:
                self.stop_capture()
                
            self.is_initialized = False
            return True
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return False