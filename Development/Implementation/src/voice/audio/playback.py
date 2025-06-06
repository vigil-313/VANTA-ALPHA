#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio playback module for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-002 - Design for swappable TTS/STT components
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

import numpy as np
import threading
import queue
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple

# Import the platform abstraction layer components
from core.platform.factory import audio_playback_factory

logger = logging.getLogger(__name__)

class AudioPlayback:
    """
    Handles audio playback with priority queue management.
    
    Features:
    - Audio output to default speaker using platform abstraction layer
    - Audio queue with priority levels
    - Support for interrupting current playback
    - Volume control
    - Smooth transitions between segments
    - Event callbacks for playback state changes
    """
    
    # Event types for callbacks
    EVENT_PLAYBACK_STARTED = "playback_started"
    EVENT_PLAYBACK_STOPPED = "playback_stopped"
    EVENT_PLAYBACK_COMPLETED = "playback_completed"
    EVENT_PLAYBACK_INTERRUPTED = "playback_interrupted"
    EVENT_QUEUE_EMPTY = "queue_empty"
    
    def __init__(self, 
                 sample_rate: int = 24000, 
                 channels: int = 1, 
                 buffer_size: int = 1024,
                 device_id: Optional[str] = None,
                 platform_impl: Optional[str] = None):
        """Initialize audio playback system.
        
        Args:
            sample_rate: Playback sample rate in Hz
            channels: Number of audio channels (1 for mono)
            buffer_size: Audio buffer size
            device_id: Platform-specific device identifier, None for default
            platform_impl: Optional specific platform implementation name
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_size = buffer_size
        
        # Volume control (0.0 to 1.0)
        self._volume = 0.8
        
        # Playback queue with (priority, playback_id, audio_data) items
        self.queue = queue.PriorityQueue()
        
        # Currently playing audio
        self.current_playback_id = None
        self.is_playing = False
        
        # Thread management
        self.lock = threading.RLock()
        self.playback_thread = None
        self.should_stop = False
        
        # Event listeners: {event_type: [callbacks]}
        self.event_listeners: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {
            self.EVENT_PLAYBACK_STARTED: [],
            self.EVENT_PLAYBACK_STOPPED: [],
            self.EVENT_PLAYBACK_COMPLETED: [],
            self.EVENT_PLAYBACK_INTERRUPTED: [],
            self.EVENT_QUEUE_EMPTY: []
        }
        
        # Stats
        self.stats = {
            "playbacks_completed": 0,
            "playbacks_interrupted": 0,
            "total_playback_duration": 0.0,  # In seconds
            "start_time": None
        }
        
        # Platform abstraction
        try:
            self.platform_playback = audio_playback_factory.create(
                name=platform_impl
            )
            
            if self.platform_playback is None:
                logger.error("Failed to create platform audio playback implementation")
                raise RuntimeError("No suitable audio playback implementation available")
            
            # Initialize platform implementation
            if not self.platform_playback.initialize(
                sample_rate=sample_rate,
                channels=channels,
                buffer_size=buffer_size
            ):
                logger.error("Failed to initialize platform audio playback")
                raise RuntimeError("Audio playback initialization failed")
            
            # Select device if specified
            if device_id is not None:
                if not self.platform_playback.select_device(device_id):
                    logger.warning(f"Failed to select device {device_id}, using default")
        
        except Exception as e:
            logger.error(f"Error initializing audio playback: {e}")
            raise RuntimeError(f"Failed to initialize audio playback: {e}")
    
    def start(self) -> bool:
        """
        Start the playback system.
        
        Returns:
            True if started successfully, False otherwise
        """
        with self.lock:
            if self.playback_thread and self.playback_thread.is_alive():
                logger.warning("Audio playback already running")
                return False
            
            try:
                # Start platform playback
                if not self.platform_playback.start_playback():
                    logger.error("Failed to start platform audio playback")
                    return False
                
                # Reset control flags
                self.should_stop = False
                
                # Start playback thread
                self.playback_thread = threading.Thread(
                    target=self._playback_worker,
                    name="AudioPlaybackThread",
                    daemon=True
                )
                self.playback_thread.start()
                
                self.stats["start_time"] = time.time()
                logger.info(f"Audio playback started: {self.sample_rate}Hz, "
                           f"{self.channels} channel(s), {self.buffer_size} buffer size")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to start audio playback: {e}")
                self._cleanup()
                return False
    
    def stop(self) -> None:
        """Stop the playback system and release resources."""
        with self.lock:
            # Signal the playback thread to stop
            self.should_stop = True
            
            # Clear the queue
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except queue.Empty:
                    break
            
            # Wait for playback thread to finish
            if self.playback_thread and self.playback_thread.is_alive():
                if threading.current_thread() != self.playback_thread:
                    self.playback_thread.join(timeout=1.0)
            
            self._cleanup()
            logger.info("Audio playback stopped")
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.platform_playback.stop_playback()
        except Exception as e:
            logger.warning(f"Error stopping platform audio playback: {e}")
        
        self.is_playing = False
        self.current_playback_id = None
    
    def _playback_worker(self) -> None:
        """Worker thread for audio playback."""
        while not self.should_stop:
            try:
                # Get the next audio segment to play
                priority, playback_id, audio_data = self.queue.get(timeout=0.1)
                
                # Update state
                with self.lock:
                    if self.should_stop:
                        break
                    
                    self.is_playing = True
                    self.current_playback_id = playback_id
                
                # Emit started event
                self._emit_event(self.EVENT_PLAYBACK_STARTED, {
                    "playback_id": playback_id,
                    "priority": priority,
                    "duration": len(audio_data) / self.sample_rate
                })
                
                # Apply volume
                if self._volume < 1.0:
                    audio_data = self._apply_volume(audio_data, self._volume)
                
                # Play the audio using platform implementation
                platform_playback_id = self.platform_playback.play_audio(audio_data)
                
                # Wait until playback completes or is interrupted
                interrupted = False
                while self.is_playing and self.current_playback_id == playback_id:
                    # Check if we should stop
                    if self.should_stop:
                        interrupted = True
                        break
                    
                    # Check if playback was interrupted by another higher priority item
                    if self.current_playback_id != playback_id:
                        interrupted = True
                        break
                    
                    # Small sleep to reduce CPU usage
                    time.sleep(0.01)
                
                # Handle interruption
                if interrupted:
                    # Stop the platform playback
                    self.platform_playback.stop_audio(platform_playback_id)
                    
                    # Emit interrupted event
                    self._emit_event(self.EVENT_PLAYBACK_INTERRUPTED, {
                        "playback_id": playback_id,
                        "interrupted_by": self.current_playback_id
                    })
                    self.stats["playbacks_interrupted"] += 1
                else:
                    # Update stats for completed playback
                    self.stats["playbacks_completed"] += 1
                    self.stats["total_playback_duration"] += len(audio_data) / self.sample_rate
                    
                    # Emit completed event
                    self._emit_event(self.EVENT_PLAYBACK_COMPLETED, {
                        "playback_id": playback_id,
                        "duration": len(audio_data) / self.sample_rate
                    })
                
                # Mark task as done
                self.queue.task_done()
                
                # Check if the queue is now empty
                if self.queue.empty():
                    with self.lock:
                        self.is_playing = False
                        self.current_playback_id = None
                    
                    # Emit queue empty event
                    self._emit_event(self.EVENT_QUEUE_EMPTY, {})
                
            except queue.Empty:
                # No audio to play, continue checking
                pass
            except Exception as e:
                logger.error(f"Error in playback worker: {e}")
                time.sleep(0.1)  # Prevent tight loop on error
    
    def play(self, audio_data: np.ndarray, priority: int = 0, 
             interrupt: bool = False) -> str:
        """Queue audio data for playback.
        
        Args:
            audio_data: Audio samples as numpy array
            priority: Priority level (higher = more important)
            interrupt: Whether to interrupt current playback
            
        Returns:
            Playback ID that can be used to track this audio
        """
        if audio_data.size == 0:
            logger.warning("Attempted to play empty audio data")
            return ""
        
        # Ensure audio data is int16
        if audio_data.dtype != np.int16:
            audio_data = np.clip(audio_data, -32767, 32767).astype(np.int16)
        
        # Generate unique ID for this playback
        playback_id = str(uuid.uuid4())
        
        # Handle interruption
        if interrupt and self.is_playing:
            with self.lock:
                # Clear the queue
                while not self.queue.empty():
                    try:
                        self.queue.get_nowait()
                        self.queue.task_done()
                    except queue.Empty:
                        break
                
                # Set new playback ID to interrupt current
                self.current_playback_id = playback_id
        
        # Use negative priority so higher values are processed first
        self.queue.put((-priority, playback_id, audio_data))
        
        return playback_id
    
    def play_file(self, file_path: str, priority: int = 0, 
                 interrupt: bool = False) -> str:
        """Play audio from a WAV file.
        
        Args:
            file_path: Path to WAV file
            priority: Priority level (higher = more important)
            interrupt: Whether to interrupt current playback
            
        Returns:
            Playback ID or empty string if error
        """
        try:
            import soundfile as sf
            audio_data, file_sr = sf.read(file_path, dtype='int16')
            
            # Convert to mono if needed
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                audio_data = np.mean(audio_data, axis=1).astype(np.int16)
            
            # Resample if needed
            if file_sr != self.sample_rate:
                # Simple resampling for now
                import scipy.signal as signal
                samples_out = int(audio_data.shape[0] * self.sample_rate / file_sr)
                audio_data = signal.resample(audio_data, samples_out).astype(np.int16)
            
            return self.play(audio_data, priority, interrupt)
            
        except Exception as e:
            logger.error(f"Error playing audio file {file_path}: {e}")
            return ""
    
    def stop_playback(self, playback_id: Optional[str] = None) -> None:
        """
        Stop specific playback or all playback if id is None.
        
        Args:
            playback_id: ID of playback to stop, or None for all
        """
        with self.lock:
            if playback_id is None or playback_id == self.current_playback_id:
                # Clear queue and stop current playback
                while not self.queue.empty():
                    try:
                        self.queue.get_nowait()
                        self.queue.task_done()
                    except queue.Empty:
                        break
                
                old_id = self.current_playback_id
                self.current_playback_id = None
                
                if old_id:
                    # Emit stopped event
                    self._emit_event(self.EVENT_PLAYBACK_STOPPED, {
                        "playback_id": old_id
                    })
            else:
                # Only stop a specific playback in the queue
                # This is more complex as we need to remove a specific item
                # For simplicity, we'll just skip it when it comes up
                pass
    
    def set_volume(self, volume_level: float) -> None:
        """
        Set playback volume (0.0 to 1.0).
        
        Args:
            volume_level: Volume level from 0.0 (mute) to 1.0 (max)
        """
        self._volume = max(0.0, min(1.0, volume_level))
    
    def _apply_volume(self, audio_data: np.ndarray, volume: float) -> np.ndarray:
        """
        Apply volume to audio data.
        
        Args:
            audio_data: Audio data as numpy array
            volume: Volume level from 0.0 to 1.0
            
        Returns:
            Audio data with volume applied
        """
        if volume >= 1.0:
            return audio_data
            
        # Convert to float, apply volume, convert back to int16
        float_data = audio_data.astype(np.float32) * volume
        return np.clip(float_data, -32767, 32767).astype(np.int16)
    
    def add_event_listener(self, event_type: str, 
                         callback_fn: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Add callback for playback events (start, stop, complete).
        
        Args:
            event_type: Event type (see EVENT_* constants)
            callback_fn: Function to call when event occurs
            
        Returns:
            True if added successfully, False otherwise
        """
        if event_type not in self.event_listeners:
            logger.error(f"Unknown event type: {event_type}")
            return False
            
        if callback_fn not in self.event_listeners[event_type]:
            self.event_listeners[event_type].append(callback_fn)
            return True
            
        return False
    
    def remove_event_listener(self, event_type: str,
                            callback_fn: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Remove a previously added event listener.
        
        Args:
            event_type: Event type
            callback_fn: Function to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        if event_type not in self.event_listeners:
            return False
            
        if callback_fn in self.event_listeners[event_type]:
            self.event_listeners[event_type].remove(callback_fn)
            return True
            
        return False
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit an event to all registered listeners.
        
        Args:
            event_type: Event type
            data: Event data dictionary
        """
        if event_type not in self.event_listeners:
            return
            
        # Add timestamp and event type to data
        event_data = data.copy()
        event_data["timestamp"] = time.time()
        event_data["event_type"] = event_type
        
        # Notify listeners
        for callback in self.event_listeners[event_type]:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current playback statistics.
        
        Returns:
            Dictionary with playback statistics
        """
        with self.lock:
            stats = self.stats.copy()
            if stats["start_time"]:
                stats["uptime_seconds"] = time.time() - stats["start_time"]
            stats["is_playing"] = self.is_playing
            stats["queue_size"] = self.queue.qsize()
            return stats
    
    def list_devices(self) -> List[Dict[str, Any]]:
        """
        List available audio output devices.
        
        Returns:
            List of dictionaries with device information
        """
        try:
            return self.platform_playback.get_available_devices()
        except Exception as e:
            logger.error(f"Error listing audio devices: {e}")
            return []
    
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """
        Select output device by platform-specific identifier.
        
        Args:
            device_id: Platform-specific device identifier
            
        Returns:
            True if device selection successful, False otherwise
        """
        try:
            return self.platform_playback.select_device(device_id)
        except Exception as e:
            logger.error(f"Error selecting audio device: {e}")
            return False
    
    def is_queue_empty(self) -> bool:
        """
        Check if the playback queue is empty.
        
        Returns:
            True if queue is empty, False otherwise
        """
        return self.queue.empty()
    
    def __enter__(self):
        """Context manager enter - starts playback."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stops playback."""
        self.stop()