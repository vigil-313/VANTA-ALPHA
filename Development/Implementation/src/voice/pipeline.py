#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main voice pipeline coordinator for the VANTA system.
"""
# TASK-REF: VOICE_001 - Audio Processing Infrastructure
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-002 - Design for swappable TTS/STT components

import os
import logging
import threading
import time
import numpy as np
from typing import Dict, Any, Optional, List, Callable, Union

from voice.audio.capture import AudioCapture
from voice.audio.preprocessing import AudioPreprocessor
from voice.audio.playback import AudioPlayback
from voice.audio.config import AudioConfig
from voice.vad.detector import VoiceActivityDetector
from voice.vad.activation import WakeWordDetector, ActivationManager, ActivationState, ActivationMode
from voice.stt.whisper_adapter import WhisperAdapter
from voice.stt.transcriber import Transcriber, TranscriptionProcessor, TranscriptionQuality

logger = logging.getLogger(__name__)

class VoicePipeline:
    """
    Main coordinator for the voice pipeline components.
    
    Integrates audio capture, preprocessing, and playback into
    a unified pipeline, with hooks for VAD and STT components.
    """
    
    def __init__(self, config_file: Optional[str] = None, 
             mock_vad: Optional[VoiceActivityDetector] = None,
             mock_wake_word: Optional['WakeWordDetector'] = None,
             mock_activation: Optional['ActivationManager'] = None,
             mock_whisper: Optional[WhisperAdapter] = None,
             mock_transcriber: Optional[Transcriber] = None,
             mock_processor: Optional[TranscriptionProcessor] = None):
        """
        Initialize the voice pipeline with all components.
        
        Args:
            config_file: Optional path to configuration file
            mock_vad: Optional mock VAD for testing
            mock_wake_word: Optional mock wake word detector for testing
            mock_activation: Optional mock activation manager for testing
            mock_whisper: Optional mock WhisperAdapter for testing
            mock_transcriber: Optional mock Transcriber for testing
            mock_processor: Optional mock TranscriptionProcessor for testing
        """
        # Initialize configuration
        self.config = AudioConfig(config_file)
        
        # Initialize components
        self.capture = AudioCapture(**self.config.get_capture_config())
        self.preprocessor = AudioPreprocessor(**self.config.get_preprocessing_config())
        self.playback = AudioPlayback(**self.config.get_playback_config())
        
        # VAD components
        if mock_vad is not None:
            # Use provided mock VAD for testing
            self.vad = mock_vad
            logger.info("Using mock VAD detector for testing")
        else:
            # Initialize real VAD component
            vad_config = self.config.get_vad_config()
            self.vad = VoiceActivityDetector(**vad_config)
        
        # Use mock wake word detector or create a real one
        if mock_wake_word is not None:
            self.wake_word_detector = mock_wake_word
            logger.info("Using mock WakeWordDetector for testing")
        else:
            # Get wake word configuration and remove parameters not accepted by WakeWordDetector
            wake_word_config = self.config.get_wake_word_config()
            # Filter parameters to match WakeWordDetector constructor
            accepted_params = ["wake_word", "threshold", "sample_rate"]
            filtered_config = {k: v for k, v in wake_word_config.items() if k in accepted_params}
            
            # Rename 'phrase' to 'wake_word' if present
            if "phrase" in wake_word_config:
                filtered_config["wake_word"] = wake_word_config["phrase"]
                
            self.wake_word_detector = WakeWordDetector(vad=self.vad, **filtered_config)
        
        # Use mock activation manager or create a real one
        if mock_activation is not None:
            self.activation_manager = mock_activation
            logger.info("Using mock ActivationManager for testing")
        else:
            # Activation management
            activation_config = self.config.get_activation_config()
            self.activation_manager = ActivationManager(
                vad=self.vad,
                wake_word_detector=self.wake_word_detector,
                **activation_config
            )
        
        # Add activation state change listener
        self.activation_manager.add_state_change_listener(self._on_activation_state_change)
        
        # STT components
        stt_config = self.config.get_stt_config()
        
        # Use mock WhisperAdapter or create a real one
        if mock_whisper is not None:
            self.whisper_adapter = mock_whisper
            logger.info("Using mock WhisperAdapter for testing")
        else:
            self.whisper_adapter = WhisperAdapter(**stt_config.get("whisper", {}))
            
        # Use mock Transcriber or create a real one
        if mock_transcriber is not None:
            self.transcriber = mock_transcriber
            logger.info("Using mock Transcriber for testing")
        else:
            self.transcriber = Transcriber(
                whisper_adapter=self.whisper_adapter,
                **stt_config.get("transcriber", {})
            )
            
        # Use mock TranscriptionProcessor or create a real one
        if mock_processor is not None:
            self.transcription_processor = mock_processor
            logger.info("Using mock TranscriptionProcessor for testing")
        else:
            self.transcription_processor = TranscriptionProcessor(
                **stt_config.get("processor", {})
            )
        
        # Buffer for collecting speech audio during active periods
        self.speech_buffer = []
        
        # State management
        self.is_running = False
        self.lock = threading.RLock()
        
        # Pipeline state
        self.state = {
            "is_listening": True,  # Whether we're actively listening
            "is_speaking": False,  # Whether we're currently outputting audio
            "latest_energy": 0.0,  # Latest audio energy level
            "vad_active": False,   # Whether voice activity is detected
            "last_activity_time": 0.0,  # Timestamp of last voice activity
            "activation_state": ActivationState.INACTIVE.value,  # Current activation state
            "activation_mode": ActivationMode.WAKE_WORD.value,  # Current activation mode
            "wake_word_detected": False,  # Whether wake word was detected
            "should_process": False,  # Whether audio should be processed by STT
            "latest_transcription": "",  # Latest transcription text
            "transcription_confidence": 0.0  # Confidence level of latest transcription
        }
        
        # Event callbacks
        self.speech_detected_callbacks: List[Callable[[], None]] = []
        self.speech_ended_callbacks: List[Callable[[], None]] = []
        self.new_audio_callbacks: List[Callable[[np.ndarray], None]] = []
        self.transcription_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Stats
        self.stats = {
            "start_time": None,
            "audio_chunks_processed": 0,
            "speech_segments_detected": 0,
            "audio_played_count": 0,
            "audio_played_duration": 0.0,
            "transcriptions_processed": 0
        }
        
        # Set up audio processing callback
        self.capture.add_callback(self._process_audio)
        
        # Set up playback event listener
        self.playback.add_event_listener(
            AudioPlayback.EVENT_PLAYBACK_STARTED,
            self._handle_playback_started
        )
        self.playback.add_event_listener(
            AudioPlayback.EVENT_PLAYBACK_COMPLETED,
            self._handle_playback_completed
        )
        
    def start(self) -> bool:
        """
        Start the voice pipeline.
        
        Returns:
            True if started successfully, False otherwise
        """
        with self.lock:
            if self.is_running:
                logger.warning("Voice pipeline already running")
                return False
                
            # Start components
            if not self.playback.start():
                logger.error("Failed to start audio playback")
                return False
                
            if not self.capture.start():
                logger.error("Failed to start audio capture")
                self.playback.stop()
                return False
            
            self.is_running = True
            self.stats["start_time"] = time.time()
            
            logger.info("Voice pipeline started")
            return True
            
    def stop(self) -> None:
        """
        Stop the voice pipeline and clean up resources.
        """
        with self.lock:
            if not self.is_running:
                return
                
            # Stop components
            self.capture.stop()
            self.playback.stop()
            
            self.is_running = False
            logger.info("Voice pipeline stopped")
            
    def _process_audio(self, audio_data: np.ndarray) -> None:
        """
        Process incoming audio data from capture.
        
        Args:
            audio_data: Audio data from capture
        """
        try:
            # Process the audio
            processed_audio = self.preprocessor.process(audio_data)
            
            # Calculate energy for VAD heuristics
            energy = self.preprocessor.calculate_energy(processed_audio)
            self.state["latest_energy"] = energy
            
            # Update stats
            self.stats["audio_chunks_processed"] += 1
            
            # Process for activation management
            if self.state["is_listening"]:
                # Process audio through activation manager
                activation_result = self.activation_manager.process_audio(processed_audio)
                
                # Update state
                self.state["activation_state"] = activation_result["state"].value
                self.state["vad_active"] = activation_result["is_speech"]
                self.state["wake_word_detected"] = activation_result["wake_word_detected"]
                self.state["should_process"] = activation_result["should_process"]
                
                # If speech was detected, update last activity time
                if activation_result["is_speech"]:
                    self.state["last_activity_time"] = time.time()
                    
                # Track speech segments for stats
                if activation_result["is_speech"] and not self.state.get("_prev_is_speech", False):
                    self.stats["speech_segments_detected"] += 1
                    # Notify speech detected callbacks
                    for callback in self.speech_detected_callbacks:
                        try:
                            callback()
                        except Exception as e:
                            logger.error(f"Error in speech detected callback: {e}")
                            
                elif not activation_result["is_speech"] and self.state.get("_prev_is_speech", False):
                    # Notify speech ended callbacks
                    for callback in self.speech_ended_callbacks:
                        try:
                            callback()
                        except Exception as e:
                            logger.error(f"Error in speech ended callback: {e}")
                            
                # Track previous speech state
                self.state["_prev_is_speech"] = activation_result["is_speech"]
                
                # Process audio for speech recognition
                if activation_result["should_process"]:
                    # Add to speech buffer for processing
                    self.speech_buffer.append(processed_audio)
                    
                    # If we're in streaming mode, feed to streaming transcriber
                    if self.transcriber.is_streaming():
                        self._stream_audio_chunk(processed_audio)
                    
                    # If we've reached the end of speech or max buffer size
                    if (not activation_result["is_speech"] and len(self.speech_buffer) > 0) or \
                       len(self.speech_buffer) >= self.config.get_max_buffer_chunks():
                        self._process_speech_buffer()
            
            # Notify callbacks about new audio
            for callback in self.new_audio_callbacks:
                try:
                    callback(processed_audio)
                except Exception as e:
                    logger.error(f"Error in new audio callback: {e}")
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            
    def _handle_playback_started(self, event_data: Dict[str, Any]) -> None:
        """
        Handle playback started event.
        
        Args:
            event_data: Event data dictionary
        """
        with self.lock:
            self.state["is_speaking"] = True
            
    def _handle_playback_completed(self, event_data: Dict[str, Any]) -> None:
        """
        Handle playback completed event.
        
        Args:
            event_data: Event data dictionary
        """
        with self.lock:
            self.state["is_speaking"] = False
            self.stats["audio_played_count"] += 1
            self.stats["audio_played_duration"] += event_data.get("duration", 0)
            
    def add_speech_detected_callback(self, callback: Callable[[], None]) -> None:
        """
        Add callback for when speech is detected.
        
        Args:
            callback: Function to call when speech is detected
        """
        if callback not in self.speech_detected_callbacks:
            self.speech_detected_callbacks.append(callback)
            
    def add_speech_ended_callback(self, callback: Callable[[], None]) -> None:
        """
        Add callback for when speech ends.
        
        Args:
            callback: Function to call when speech ends
        """
        if callback not in self.speech_ended_callbacks:
            self.speech_ended_callbacks.append(callback)
            
    def add_new_audio_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        """
        Add callback for when new audio is processed.
        
        Args:
            callback: Function to call with new audio data
        """
        if callback not in self.new_audio_callbacks:
            self.new_audio_callbacks.append(callback)
            
    def say(self, text: str, priority: int = 0, interrupt: bool = False) -> bool:
        """
        Speak the provided text (placeholder for TTS integration).
        
        This will be replaced with actual TTS in a future task.
        For now, it just logs the text that would be spoken.
        
        Args:
            text: Text to speak
            priority: Priority level (higher = more important)
            interrupt: Whether to interrupt current speech
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"TTS (priority={priority}, interrupt={interrupt}): {text}")
        
        # For testing, generate a simple sine wave to play
        try:
            import numpy as np
            duration = 0.5  # seconds
            sample_rate = self.playback.sample_rate
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            frequency = 440  # A4 note
            audio_data = np.sin(2 * np.pi * frequency * t)
            audio_data = (audio_data * 32767).astype(np.int16)
            
            # Play the audio
            playback_id = self.play_audio(audio_data, priority, interrupt)
            return bool(playback_id)
        except Exception as e:
            logger.error(f"Error in say method: {e}")
            return False
        
    def play_audio(self, audio_data: np.ndarray, priority: int = 0, 
                  interrupt: bool = False) -> str:
        """
        Play audio data through the playback system.
        
        Args:
            audio_data: Audio data to play
            priority: Priority level (higher = more important)
            interrupt: Whether to interrupt current playback
            
        Returns:
            Playback ID
        """
        return self.playback.play(audio_data, priority, interrupt)
        
    def play_audio_file(self, file_path: str, priority: int = 0,
                       interrupt: bool = False) -> str:
        """
        Play audio from a file.
        
        Args:
            file_path: Path to audio file
            priority: Priority level
            interrupt: Whether to interrupt current playback
            
        Returns:
            Playback ID or empty on error
        """
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return ""
            
        return self.playback.play_file(file_path, priority, interrupt)
        
    def set_listening(self, enabled: bool) -> None:
        """
        Enable or disable active listening.
        
        Args:
            enabled: Whether listening should be enabled
        """
        with self.lock:
            self.state["is_listening"] = enabled
            
            # If listening is disabled, reset activation
            if not enabled:
                self.activation_manager.reset()
            
    def is_listening(self) -> bool:
        """
        Check if active listening is enabled.
        
        Returns:
            True if listening is enabled
        """
        return self.state["is_listening"]
        
    def set_activation_mode(self, mode: Union[str, ActivationMode]) -> None:
        """
        Set the activation mode.
        
        Args:
            mode: New activation mode
        """
        with self.lock:
            self.activation_manager.set_mode(mode)
            
            # Update state
            self.state["activation_mode"] = self.activation_manager.mode.value
            
    def get_activation_mode(self) -> str:
        """
        Get the current activation mode.
        
        Returns:
            Current activation mode as string
        """
        return self.state["activation_mode"]
        
    def get_activation_state(self) -> str:
        """
        Get the current activation state.
        
        Returns:
            Current activation state as string
        """
        return self.state["activation_state"]
        
    def manual_activate(self) -> bool:
        """
        Manually activate the voice pipeline.
        
        Returns:
            True if activation was successful
        """
        with self.lock:
            return self.activation_manager.activate()
            
    def manual_deactivate(self) -> None:
        """
        Manually deactivate the voice pipeline.
        """
        with self.lock:
            self.activation_manager.deactivate()
        
    def is_speaking(self) -> bool:
        """
        Check if currently speaking.
        
        Returns:
            True if currently speaking
        """
        return self.state["is_speaking"]
        
    def get_audio_level(self) -> float:
        """
        Get the current audio energy level.
        
        Returns:
            Audio energy level (0.0 to 1.0)
        """
        return self.state["latest_energy"]
        
    def get_latest_transcription(self) -> Dict[str, Any]:
        """
        Get the latest transcription result.
        
        Returns:
            Dictionary with latest transcription text and confidence
        """
        with self.lock:
            return {
                "text": self.state["latest_transcription"],
                "confidence": self.state["transcription_confidence"]
            }
        
    def _process_speech_buffer(self) -> None:
        """Process the collected speech buffer for transcription."""
        if not self.speech_buffer:
            return
            
        try:
            # Concatenate speech chunks
            speech_audio = np.concatenate(self.speech_buffer)
            
            # Reset buffer
            self.speech_buffer = []
            
            # Skip if audio is too short
            if len(speech_audio) < 2000:  # ~0.125 seconds at 16kHz
                logger.debug("Audio too short for transcription, skipping")
                return
                
            # Transcribe the full utterance
            transcription = self.transcriber.transcribe(speech_audio)
            
            # Process the transcription
            processed_result = self.transcription_processor.process(transcription)
            
            # Update state with latest transcription
            with self.lock:
                self.state["latest_transcription"] = processed_result["text"]
                self.state["transcription_confidence"] = processed_result.get("confidence", 0.0)
                self.stats["transcriptions_processed"] += 1
            
            # Notify any transcription callbacks
            self._notify_transcription_callbacks(processed_result)
            
            # Log the result
            confidence = processed_result.get("confidence", 0.0)
            confidence_str = f"({confidence:.2f})" if confidence > 0 else ""
            logger.info(f"Transcribed: {processed_result['text']} {confidence_str}")
            
        except Exception as e:
            logger.error(f"Error processing speech buffer: {e}")
    
    def _stream_audio_chunk(self, audio_chunk: np.ndarray) -> None:
        """
        Feed an audio chunk to the streaming transcriber.
        
        Args:
            audio_chunk: Audio chunk to feed to the transcriber
        """
        try:
            # Feed the chunk to the streaming transcriber
            interim_result = self.transcriber.feed_audio_chunk(audio_chunk)
            
            # If we got an interim result, process and notify
            if interim_result:
                # Process the interim result
                processed_interim = self.transcription_processor.process(interim_result)
                
                # Update state
                with self.lock:
                    self.state["latest_transcription"] = processed_interim["text"]
                    self.state["transcription_confidence"] = processed_interim.get("confidence", 0.0)
                
                # Add interim flag
                processed_interim["interim"] = True
                
                # Notify callbacks
                self._notify_transcription_callbacks(processed_interim)
                
                # Log interim result
                logger.debug(f"Interim: {processed_interim['text']}")
                
        except Exception as e:
            logger.error(f"Error in streaming transcription: {e}")
    
    def _notify_transcription_callbacks(self, result: Dict[str, Any]) -> None:
        """
        Notify transcription callbacks with a result.
        
        Args:
            result: Transcription result to notify about
        """
        for callback in self.transcription_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in transcription callback: {e}")
    
    def add_transcription_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add callback for transcription results.
        
        Args:
            callback: Function to call with transcription results
        """
        if callback not in self.transcription_callbacks:
            self.transcription_callbacks.append(callback)
    
    def _on_activation_state_change(self, old_state: ActivationState, new_state: ActivationState) -> None:
        """
        Handle activation state changes.
        
        Args:
            old_state: Previous activation state
            new_state: New activation state
        """
        logger.info(f"Activation state changed: {old_state.value} -> {new_state.value}")
        
        # Update state
        with self.lock:
            self.state["activation_state"] = new_state.value
            
            # Handle specific state transitions
            if new_state == ActivationState.ACTIVE:
                # Clear speech buffer when becoming active
                self.speech_buffer = []
                
                # Start streaming transcription
                self.transcriber.start_streaming(lambda result: self._on_streaming_result(result))
                
                # Play activation sound
                self.play_audio_file("data/sounds/activate.wav", priority=10)
                
            elif new_state == ActivationState.LISTENING and old_state == ActivationState.ACTIVE:
                # Stop streaming when becoming inactive
                if self.transcriber.is_streaming():
                    final_result = self.transcriber.stop_streaming()
                    if final_result:
                        processed_result = self.transcription_processor.process(final_result)
                        
                        # Update state
                        with self.lock:
                            self.state["latest_transcription"] = processed_result["text"]
                            self.state["transcription_confidence"] = processed_result.get("confidence", 0.0)
                            
                        # Notify callbacks
                        self._notify_transcription_callbacks(processed_result)
                        
                        # Log final result
                        logger.info(f"Final transcription: {processed_result['text']}")
                
                # Play deactivation sound
                self.play_audio_file("data/sounds/deactivate.wav", priority=10)
    
    def _on_streaming_result(self, interim_result: Dict[str, Any]) -> None:
        """
        Handle streaming transcription results.
        
        Args:
            interim_result: Interim transcription result
        """
        try:
            # Process the interim result
            processed_interim = self.transcription_processor.process(interim_result)
            
            # Add interim flag
            processed_interim["interim"] = True
            
            # Update state
            with self.lock:
                self.state["latest_transcription"] = processed_interim["text"]
                self.state["transcription_confidence"] = processed_interim.get("confidence", 0.0)
            
            # Notify callbacks
            self._notify_transcription_callbacks(processed_interim)
            
            # Log interim result
            logger.debug(f"Interim: {processed_interim['text']}")
            
        except Exception as e:
            logger.error(f"Error processing streaming result: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.
        
        Returns:
            Dictionary with pipeline statistics
        """
        stats = self.stats.copy()
        if stats["start_time"]:
            stats["uptime_seconds"] = time.time() - stats["start_time"]
            
        # Include component stats
        stats["capture"] = self.capture.get_stats()
        stats["preprocessing"] = self.preprocessor.get_stats()
        stats["playback"] = self.playback.get_stats()
        
        # Include STT stats
        stats["transcriber"] = self.transcriber.get_stats()
        stats["whisper"] = self.whisper_adapter.get_stats()
        
        # Include state
        stats["state"] = self.state.copy()
        
        return stats
    
    def get_devices(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get available audio devices.
        
        Returns:
            Dictionary with input and output devices
        """
        return {
            "input": self.capture.list_devices(),
            "output": self.playback.list_devices()
        }
        
    def update_config(self, config_updates: Dict[str, Any]) -> bool:
        """
        Update configuration.
        
        Args:
            config_updates: Configuration updates
            
        Returns:
            True if configuration was updated successfully
        """
        # Update main config
        self.config.update(config_updates)
        
        # Component-specific updates
        if "capture" in config_updates:
            # Capture requires restart to apply new config
            was_running = self.capture.is_running
            if was_running:
                self.capture.stop()
                
            # Apply updated config
            self.capture = AudioCapture(**self.config.get_capture_config())
            self.capture.add_callback(self._process_audio)
            
            if was_running:
                self.capture.start()
                
        if "preprocessing" in config_updates:
            # Preprocessor can be updated without restart
            self.preprocessor = AudioPreprocessor(**self.config.get_preprocessing_config())
            
        if "playback" in config_updates:
            # Playback requires restart to apply new config
            was_running = self.playback.is_running
            
            if was_running:
                self.playback.stop()
                
            # Apply updated config
            self.playback = AudioPlayback(**self.config.get_playback_config())
            
            # Re-add event listeners
            self.playback.add_event_listener(
                AudioPlayback.EVENT_PLAYBACK_STARTED,
                self._handle_playback_started
            )
            self.playback.add_event_listener(
                AudioPlayback.EVENT_PLAYBACK_COMPLETED,
                self._handle_playback_completed
            )
            
            if was_running:
                self.playback.start()
        
        # VAD component updates
        if "vad" in config_updates:
            # Update VAD configuration
            vad_config = self.config.get_vad_config()
            self.vad = VoiceActivityDetector(**vad_config)
            
            # Update wake word detector with new VAD
            wake_word_config = self.config.get_wake_word_config()
            # Filter parameters to match WakeWordDetector constructor
            accepted_params = ["wake_word", "threshold", "sample_rate"]
            filtered_config = {k: v for k, v in wake_word_config.items() if k in accepted_params}
            
            # Rename 'phrase' to 'wake_word' if present
            if "phrase" in wake_word_config:
                filtered_config["wake_word"] = wake_word_config["phrase"]
                
            self.wake_word_detector = WakeWordDetector(vad=self.vad, **filtered_config)
            
            # Update activation manager with new components
            activation_config = self.config.get_activation_config()
            self.activation_manager = ActivationManager(
                vad=self.vad,
                wake_word_detector=self.wake_word_detector,
                **activation_config
            )
            
            # Re-add activation state change listener
            self.activation_manager.add_state_change_listener(self._on_activation_state_change)
            
        elif "wake_word" in config_updates:
            # Update just wake word detector
            wake_word_config = self.config.get_wake_word_config()
            # Filter parameters to match WakeWordDetector constructor
            accepted_params = ["wake_word", "threshold", "sample_rate"]
            filtered_config = {k: v for k, v in wake_word_config.items() if k in accepted_params}
            
            # Rename 'phrase' to 'wake_word' if present
            if "phrase" in wake_word_config:
                filtered_config["wake_word"] = wake_word_config["phrase"]
                
            self.wake_word_detector = WakeWordDetector(vad=self.vad, **filtered_config)
            
            # Update activation manager with new wake word detector
            self.activation_manager = ActivationManager(
                vad=self.vad,
                wake_word_detector=self.wake_word_detector,
                **self.config.get_activation_config()
            )
            
            # Re-add activation state change listener
            self.activation_manager.add_state_change_listener(self._on_activation_state_change)
            
        elif "activation" in config_updates:
            # Update just activation manager
            activation_config = self.config.get_activation_config()
            self.activation_manager = ActivationManager(
                vad=self.vad,
                wake_word_detector=self.wake_word_detector,
                **activation_config
            )
            
            # Re-add activation state change listener
            self.activation_manager.add_state_change_listener(self._on_activation_state_change)
            
            # Update state
            self.state["activation_mode"] = self.activation_manager.mode.value
        
        # STT component updates
        elif "stt" in config_updates:
            stt_config = self.config.get_stt_config()
            
            # Update WhisperAdapter if whisper config changed
            if "whisper" in stt_config:
                # Unload current model
                self.whisper_adapter.unload_model()
                
                # Update configuration
                for key, value in stt_config["whisper"].items():
                    setattr(self.whisper_adapter, key, value)
            
            # Update Transcriber if transcriber config changed
            if "transcriber" in stt_config:
                self.transcriber.configure(**stt_config["transcriber"])
                
            # Update TranscriptionProcessor if processor config changed
            if "processor" in stt_config:
                self.transcription_processor.configure(**stt_config["processor"])
                
            logger.info("Updated STT configuration")
                
        return True
        
    def __enter__(self):
        """Context manager enter."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()