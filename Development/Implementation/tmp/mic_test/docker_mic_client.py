#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker Microphone Client for macOS

This script provides a client interface for Docker containers to access
the host's microphone on macOS. It interacts with the file-based microphone
bridge that captures audio on the host and writes it to a shared directory.

Usage:
    As a standalone script:
        python docker_mic_client.py [--duration SECONDS] [--output OUTPUT_FILE]
        
    As a module:
        from docker_mic_client import MicrophoneClient
        mic = MicrophoneClient()
        mic.start_recording()
        audio_data = mic.read_audio(duration=5.0)
        mic.stop_recording()
"""
# TASK-REF: ENV_002 - Docker Environment Setup
# CONCEPT-REF: CON-VANTA-008 - Docker Environment
# DECISION-REF: DEC-026-001 - Use file-based communication for Docker TTS bridge

import os
import sys
import time
import json
import uuid
import wave
import argparse
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import numpy as np
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("docker_mic_client")

# Default configuration
DEFAULT_BRIDGE_DIR = "/host/vanta-mic-bridge"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_FORMAT = "wav"
DEFAULT_CHUNK_DURATION = 0.5  # seconds

class MicrophoneClient:
    """
    Client for the macOS microphone bridge in Docker containers.
    
    This class provides an interface to access the host's microphone
    from within a Docker container on macOS.
    """
    
    def __init__(self, bridge_dir=DEFAULT_BRIDGE_DIR, sample_rate=DEFAULT_SAMPLE_RATE, 
                 channels=DEFAULT_CHANNELS, format=DEFAULT_FORMAT, 
                 chunk_duration=DEFAULT_CHUNK_DURATION):
        """
        Initialize the microphone client.
        
        Args:
            bridge_dir: Path to the bridge directory (mounted from host)
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels (1 for mono, 2 for stereo)
            format: Audio format (e.g., "wav")
            chunk_duration: Duration of each audio chunk in seconds
        """
        self.bridge_dir = Path(bridge_dir)
        self.control_dir = self.bridge_dir / "control"
        self.audio_dir = self.bridge_dir / "audio"
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = format
        self.chunk_duration = chunk_duration
        
        self.uuid = str(uuid.uuid4())
        self.is_recording = False
        self.processed_files = set()
        self.audio_buffer = []
        self.process_thread = None
        self.stop_event = threading.Event()
        
    def _verify_bridge_dirs(self) -> bool:
        """
        Verify that the bridge directories exist and are accessible.
        
        Returns:
            bool: True if the directories are accessible, False otherwise
        """
        try:
            # Create directories if they don't exist (should be created by bridge)
            self.control_dir.mkdir(parents=True, exist_ok=True)
            self.audio_dir.mkdir(parents=True, exist_ok=True)
            
            # Verify write access by creating a test file
            test_file = self.control_dir / f"test_{self.uuid}.tmp"
            test_file.write_text("test")
            test_file.unlink()
            
            return True
        except Exception as e:
            logger.error(f"Bridge directory access error: {e}")
            return False
            
    def get_bridge_status(self) -> Dict[str, Any]:
        """
        Get the current status of the microphone bridge.
        
        Returns:
            Dict containing bridge status information
        """
        status_file = self.control_dir / "status.json"
        
        try:
            if status_file.exists():
                with open(status_file, 'r') as f:
                    return json.load(f)
            return {"status": "unknown", "is_recording": False, "error": "Status file not found"}
        except Exception as e:
            logger.error(f"Error reading bridge status: {e}")
            return {"status": "error", "is_recording": False, "error": str(e)}
    
    def start_recording(self) -> bool:
        """
        Start recording audio from the host microphone.
        
        Returns:
            bool: True if recording started successfully, False otherwise
        """
        if self.is_recording:
            logger.warning("Recording is already in progress")
            return True
            
        if not self._verify_bridge_dirs():
            logger.error("Bridge directories not accessible")
            return False
            
        # Create a control file to start recording
        control_file = self.control_dir / f"start_recording_{self.uuid}.ctrl"
        config = {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "format": self.format,
            "chunk_duration": self.chunk_duration
        }
        
        try:
            with open(control_file, 'w') as f:
                json.dump(config, f)
                
            logger.info(f"Recording started with UUID: {self.uuid}")
            self.is_recording = True
            self.processed_files.clear()
            self.audio_buffer.clear()
            
            # Start a thread to process audio files
            self.stop_event.clear()
            self.process_thread = threading.Thread(target=self._process_audio_files)
            self.process_thread.daemon = True
            self.process_thread.start()
            
            # Wait for the bridge to start recording
            start_time = time.time()
            while time.time() - start_time < 5.0:  # Wait up to 5 seconds
                status = self.get_bridge_status()
                if status.get("is_recording", False) and status.get("current_uuid") == self.uuid:
                    return True
                time.sleep(0.1)
                
                # Check if the control file was removed (indicating it was processed)
                if not control_file.exists():
                    # Give a little more time for recording to start
                    time.sleep(0.5)
                    status = self.get_bridge_status()
                    return status.get("is_recording", False)
                    
            logger.error("Timeout waiting for recording to start")
            return False
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return False
    
    def stop_recording(self) -> bool:
        """
        Stop recording audio from the host microphone.
        
        Returns:
            bool: True if recording stopped successfully, False otherwise
        """
        if not self.is_recording:
            logger.warning("No recording in progress")
            return True
            
        # Create a control file to stop recording
        control_file = self.control_dir / f"stop_recording_{self.uuid}.ctrl"
        
        try:
            # Touch the file (create empty file)
            control_file.touch()
            
            logger.info(f"Recording stopped with UUID: {self.uuid}")
            self.is_recording = False
            
            # Stop the processing thread
            self.stop_event.set()
            if self.process_thread and self.process_thread.is_alive():
                self.process_thread.join(timeout=5.0)
                
            # Wait for the bridge to stop recording
            start_time = time.time()
            while time.time() - start_time < 5.0:  # Wait up to 5 seconds
                status = self.get_bridge_status()
                if not status.get("is_recording", True) or status.get("current_uuid") != self.uuid:
                    return True
                time.sleep(0.1)
                
                # Check if the control file was removed (indicating it was processed)
                if not control_file.exists():
                    # Give a little more time for recording to stop
                    time.sleep(0.5)
                    status = self.get_bridge_status()
                    return not status.get("is_recording", True)
                    
            logger.error("Timeout waiting for recording to stop")
            return False
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return False
    
    def _process_audio_files(self):
        """
        Process audio files from the bridge directory.
        This method runs in a separate thread and continuously monitors
        the audio directory for new audio chunks.
        """
        logger.info("Starting audio file processing thread")
        
        while not self.stop_event.is_set():
            try:
                # Get all audio files for this UUID
                pattern = f"chunk_*_{self.uuid}.wav"
                files = sorted(self.audio_dir.glob(pattern))
                
                # Process new files
                for file_path in files:
                    if file_path not in self.processed_files:
                        logger.debug(f"Processing audio file: {file_path.name}")
                        
                        try:
                            # Read the audio file
                            with wave.open(str(file_path), 'rb') as wav_file:
                                n_channels = wav_file.getnchannels()
                                sampwidth = wav_file.getsampwidth()
                                framerate = wav_file.getframerate()
                                n_frames = wav_file.getnframes()
                                audio_data = wav_file.readframes(n_frames)
                                
                                # Convert to numpy array
                                dtype = {1: np.int8, 2: np.int16, 4: np.int32}.get(sampwidth, np.int16)
                                audio_array = np.frombuffer(audio_data, dtype=dtype)
                                
                                # Add to buffer
                                self.audio_buffer.append((audio_array, framerate, n_channels))
                                self.processed_files.add(file_path)
                                
                        except Exception as e:
                            logger.error(f"Error processing audio file {file_path.name}: {e}")
                
                # Sleep briefly before checking for new files
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in audio processing thread: {e}")
                time.sleep(1.0)  # Wait a bit longer on error
                
        logger.info("Audio file processing thread stopped")
    
    def read_audio(self, duration: Optional[float] = None, timeout: float = 10.0) -> Tuple[np.ndarray, int, int]:
        """
        Read audio data from the buffer.
        
        Args:
            duration: Duration of audio to read in seconds (None for all available)
            timeout: Maximum time to wait for audio in seconds
            
        Returns:
            Tuple of (audio_array, sample_rate, channels)
        """
        if not self.is_recording:
            logger.warning("Not recording, starting now")
            self.start_recording()
            # Allow some time for initial audio capture
            time.sleep(0.5)
            
        start_time = time.time()
        
        # If duration is specified, calculate how many chunks we need
        if duration is not None:
            target_chunks = int(duration / self.chunk_duration) + 1
        else:
            target_chunks = 1  # At least one chunk
            
        # Wait for enough audio data
        while len(self.audio_buffer) < target_chunks:
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout waiting for audio data (have {len(self.audio_buffer)} chunks, need {target_chunks})")
                break
            time.sleep(0.1)
            
        # Return empty array if no data
        if not self.audio_buffer:
            return np.array([], dtype=np.int16), self.sample_rate, self.channels
            
        # Combine audio chunks
        arrays = []
        for audio_array, framerate, n_channels in self.audio_buffer:
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
                
        return combined, self.sample_rate, self.channels
    
    def save_audio(self, output_file: str, duration: Optional[float] = None, timeout: float = 10.0) -> bool:
        """
        Save recorded audio to a WAV file.
        
        Args:
            output_file: Path to output WAV file
            duration: Duration of audio to save in seconds
            timeout: Maximum time to wait for audio
            
        Returns:
            bool: True if audio was saved successfully, False otherwise
        """
        try:
            # Read audio data
            audio_array, sample_rate, channels = self.read_audio(duration, timeout)
            
            if len(audio_array) == 0:
                logger.error("No audio data available to save")
                return False
                
            # Write to WAV file
            with wave.open(output_file, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_array.tobytes())
                
            logger.info(f"Audio saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            return False

def main():
    """Main entry point when used as a standalone script."""
    parser = argparse.ArgumentParser(description="Docker Microphone Client for macOS")
    parser.add_argument("--bridge-dir", default=DEFAULT_BRIDGE_DIR, help="Path to bridge directory")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE, help="Audio sample rate")
    parser.add_argument("--channels", type=int, default=DEFAULT_CHANNELS, help="Number of audio channels")
    parser.add_argument("--duration", type=float, default=5.0, help="Recording duration in seconds")
    parser.add_argument("--output", default="output.wav", help="Output WAV file")
    args = parser.parse_args()
    
    # Check if the bridge directory exists
    bridge_dir = Path(args.bridge_dir)
    if not bridge_dir.parent.exists():
        logger.error(f"Bridge directory parent path does not exist: {bridge_dir.parent}")
        logger.error("Make sure the host directory is mounted at /host or adjust the bridge directory path.")
        return 1
    
    # Create microphone client
    mic = MicrophoneClient(
        bridge_dir=args.bridge_dir,
        sample_rate=args.sample_rate,
        channels=args.channels
    )
    
    # Get bridge status
    status = mic.get_bridge_status()
    logger.info(f"Bridge status: {status}")
    
    # Start recording
    logger.info(f"Starting recording for {args.duration} seconds...")
    if not mic.start_recording():
        logger.error("Failed to start recording")
        return 1
    
    try:
        # Wait for the specified duration
        time.sleep(args.duration)
        
        # Save the recorded audio
        logger.info(f"Saving audio to {args.output}...")
        if not mic.save_audio(args.output):
            logger.error("Failed to save audio")
            return 1
            
        logger.info(f"Audio saved to {args.output}")
        
    finally:
        # Stop recording
        logger.info("Stopping recording...")
        mic.stop_recording()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())