#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VANTA LangGraph Voice Processing Nodes

This module implements the LangGraph nodes for voice-related processing in the VANTA system,
including activation checking, audio processing, and speech synthesis.
"""
# TASK-REF: LG_002 - LangGraph Node Implementation
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-ARCH-001 - V0 Architecture Overview

import logging
import time
from datetime import datetime
from typing import Dict, Any

from langchain_core.messages import HumanMessage

from ..state.vanta_state import VANTAState, ActivationMode, ActivationStatus
from ...voice.pipeline import SpeechToTextProcessor, TextToSpeechProcessor
from ...voice.vad import VoiceActivityDetector

logger = logging.getLogger(__name__)


def check_activation(state: VANTAState) -> Dict[str, Any]:
    """
    Determines if VANTA should activate based on the current mode.
    
    This node checks the current activation mode (continuous, wake_word, scheduled)
    and determines whether the system should be activated based on audio input.
    It handles the initial activation logic for the VANTA system.
    
    Args:
        state: Current VANTA state containing config, activation, and audio data
        
    Returns:
        Dict: Updated activation status and metadata
    """
    try:
        # Extract required fields
        activation_mode = state["config"]["activation_mode"]
        current_status = state["activation"]["status"]
        
        # If already processing or speaking, continue the pipeline
        if current_status in [ActivationStatus.PROCESSING, ActivationStatus.SPEAKING]:
            return {"activation": {"status": ActivationStatus.PROCESSING}}
        
        # Get audio data
        audio_data = state["audio"].get("current_audio")
        
        # No audio data, remain inactive unless already listening
        if not audio_data:
            if current_status == ActivationStatus.LISTENING:
                return {}  # Stay in listening mode
            return {"activation": {"status": ActivationStatus.INACTIVE}}
        
        # Wake word detection
        wake_word_detected = False
        if isinstance(audio_data, str):
            # Text-based detection for testing
            wake_word_detected = "hey vanta" in audio_data.lower()
        else:
            # Audio-based detection using VAD component
            try:
                vad = VoiceActivityDetector()
                wake_word_detected = vad.detect_wake_word(audio_data)
            except Exception as e:
                logger.warning(f"Wake word detection failed: {e}")
                wake_word_detected = False
        
        current_time = datetime.now()
        
        # Determine activation based on mode
        should_activate = False
        
        if activation_mode == ActivationMode.CONTINUOUS:
            # Continuous mode: always activate with audio
            should_activate = True
            
        elif activation_mode == ActivationMode.WAKE_WORD:
            # Wake word mode: activate only if wake word detected
            should_activate = wake_word_detected
            
        elif activation_mode == ActivationMode.SCHEDULED:
            # Scheduled mode: activate based on schedule
            current_time_str = current_time.strftime("%H:%M")
            scheduled_times = state["config"].get("scheduled_times", [])
            should_activate = current_time_str in scheduled_times
        
        # Update activation state
        if should_activate:
            return {
                "activation": {
                    "status": ActivationStatus.PROCESSING,
                    "last_activation_time": current_time.isoformat(),
                    "wake_word_detected": wake_word_detected,
                }
            }
        else:
            # Set to listening if not already active
            new_status = (ActivationStatus.LISTENING 
                         if activation_mode in [ActivationMode.WAKE_WORD, ActivationMode.CONTINUOUS]
                         else ActivationStatus.INACTIVE)
            
            return {
                "activation": {
                    "status": new_status,
                    "wake_word_detected": wake_word_detected,
                }
            }
        
    except KeyError as e:
        logger.error(f"Missing required field in activation check: {e}")
        return {"activation": {"status": ActivationStatus.INACTIVE}}
    except Exception as e:
        logger.error(f"Error in activation check: {e}")
        return {"activation": {"status": ActivationStatus.INACTIVE}}


def process_audio(state: VANTAState) -> Dict[str, Any]:
    """
    Processes audio input using Whisper for transcription.
    
    This node takes the current audio data, uses the Voice Pipeline's
    transcription component to convert it to text, and adds a new
    user message to the conversation.
    
    Args:
        state: Current VANTA state containing audio data and activation status
        
    Returns:
        Dict: Updates with new user message and audio metadata
    """
    try:
        # Skip if no audio or not in processing mode
        audio_data = state["audio"].get("current_audio")
        if not audio_data or state["activation"]["status"] != ActivationStatus.PROCESSING:
            return {}
        
        # Initialize transcriber
        transcriber = SpeechToTextProcessor()
        
        # Transcribe audio
        start_time = time.time()
        transcription = transcriber.transcribe(audio_data)
        transcription_time = time.time() - start_time
        
        # Create audio metadata
        timestamp = datetime.now().isoformat()
        audio_metadata = {
            "timestamp": timestamp,
            "transcription": transcription,
            "audio_reference": state["audio"].get("audio_path", ""),
            "transcription_time": transcription_time,
        }
        
        # Calculate unique ID for this audio entry
        entry_id = f"audio_{int(time.time())}_{hash(transcription) % 10000}"
        
        # Create new audio entry for memory
        audio_entry = {
            "id": entry_id,
            "timestamp": timestamp,
            "transcription": transcription,
            "audio_path": state["audio"].get("audio_path", ""),
            "processing_time": transcription_time,
        }
        
        # Return state updates
        return {
            "messages": [HumanMessage(content=transcription)],
            "audio": {
                "last_transcription": transcription,
                "metadata": audio_metadata,
                "current_audio": None,  # Clear processed audio
            },
            "memory": {
                "audio_entries": state["memory"].get("audio_entries", []) + [audio_entry]
            }
        }
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        
        # Fallback transcription for errors
        error_transcription = "I couldn't understand what you said. Could you please repeat that?"
        timestamp = datetime.now().isoformat()
        
        return {
            "messages": [HumanMessage(content=error_transcription)],
            "audio": {
                "last_transcription": error_transcription,
                "error": str(e),
                "current_audio": None,
                "metadata": {
                    "timestamp": timestamp,
                    "transcription": error_transcription,
                    "error": str(e),
                }
            }
        }


def synthesize_speech(state: VANTAState) -> Dict[str, Any]:
    """
    Converts text to speech using CSM (or platform TTS).
    
    This node takes the last AI message content and generates speech
    using the Text-to-Speech integration. It updates the audio state
    with synthesis information and resets activation to inactive.
    
    Args:
        state: Current VANTA state containing messages and voice settings
        
    Returns:
        Dict: Updates with synthesis information and new activation status
    """
    try:
        # Skip if not in speaking mode or no AI messages
        if state["activation"]["status"] != ActivationStatus.SPEAKING:
            return {}
        
        # Get the last AI message
        messages = state.get("messages", [])
        if not messages:
            return {}
        
        # Find the last AI message
        last_ai_message = None
        for message in reversed(messages):
            if hasattr(message, 'type') and message.type == 'ai':
                last_ai_message = message
                break
            elif message.__class__.__name__ == 'AIMessage':
                last_ai_message = message
                break
        
        if not last_ai_message or not last_ai_message.content:
            return {"activation": {"status": ActivationStatus.INACTIVE}}
        
        # Initialize TTS processor
        tts_processor = TextToSpeechProcessor()
        
        # Get voice settings from config
        voice_settings = state["config"].get("voice_settings", {})
        voice_id = voice_settings.get("voice_id", "default")
        speed = voice_settings.get("speed", 1.0)
        pitch = voice_settings.get("pitch", 1.0)
        
        # Synthesize speech
        start_time = time.time()
        audio_output = tts_processor.synthesize(
            text=last_ai_message.content,
            voice_id=voice_id,
            speed=speed,
            pitch=pitch
        )
        synthesis_time = time.time() - start_time
        
        # Create synthesis metadata
        timestamp = datetime.now().isoformat()
        synthesis_metadata = {
            "timestamp": timestamp,
            "text": last_ai_message.content,
            "voice_id": voice_id,
            "speed": speed,
            "pitch": pitch,
            "synthesis_time": synthesis_time,
            "audio_output": audio_output,
        }
        
        # Return state updates
        return {
            "audio": {
                "last_synthesis": synthesis_metadata,
                "current_output": audio_output,
            },
            "activation": {
                "status": ActivationStatus.INACTIVE,  # Reset to inactive after speaking
            }
        }
    
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        
        # Log error and reset activation without audio output
        return {
            "audio": {
                "synthesis_error": str(e),
                "last_synthesis": {
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                }
            },
            "activation": {
                "status": ActivationStatus.INACTIVE,
            }
        }