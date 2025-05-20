#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text-to-Speech adapter for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_004 - Text-to-Speech Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-002 - Design for swappable TTS/STT components

import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Union
import numpy as np
import time

logger = logging.getLogger(__name__)

class TTSEngineType(Enum):
    """Enumeration of supported TTS engine types."""
    API = "api"  # Cloud-based API engines
    LOCAL = "local"  # Local model-based engines
    SYSTEM = "system"  # Operating system TTS
    BRIDGE = "bridge"  # File-based bridge for Docker on macOS

class TTSAdapter:
    """
    Base class for text-to-speech adapters.
    
    Provides a common interface for all TTS engines, whether they're
    API-based, local models, or system TTS services.
    """
    
    def __init__(self, 
                 engine_type: Union[TTSEngineType, str] = TTSEngineType.LOCAL,
                 voice_id: str = "default",
                 model_path: Optional[str] = None,
                 api_key: Optional[str] = None,
                 speaking_rate: float = 1.0,
                 pitch: float = 0.0,
                 sample_rate: int = 24000):
        """
        Initialize TTS adapter.
        
        Args:
            engine_type: Type of TTS engine to use
            voice_id: Voice identifier to use
            model_path: Path to local model (if using LOCAL engine)
            api_key: API key (if using API engine)
            speaking_rate: Speech rate multiplier (0.5-2.0)
            pitch: Voice pitch adjustment (-10.0 to 10.0)
            sample_rate: Output audio sample rate
        """
        # Convert string to enum if needed
        if isinstance(engine_type, str):
            try:
                self.engine_type = TTSEngineType(engine_type)
            except ValueError:
                logger.warning(f"Invalid engine type: {engine_type}, using LOCAL")
                self.engine_type = TTSEngineType.LOCAL
        else:
            self.engine_type = engine_type
        
        # Common parameters
        self.voice_id = voice_id
        self.model_path = model_path
        self.api_key = api_key
        self.speaking_rate = speaking_rate
        self.pitch = pitch
        self.sample_rate = sample_rate
        
        # Engine state
        self.is_loaded_flag = False
        
        # Stats
        self.stats = {
            "synthesis_count": 0,
            "total_duration": 0.0,
            "total_audio_length": 0,
            "total_synthesis_time": 0.0,
            "last_synthesis_time": 0.0,
            "average_latency": 0.0
        }
    
    def load_engine(self) -> bool:
        """
        Load the TTS engine.
        
        Returns:
            True if successfully loaded, False otherwise
        """
        # To be implemented by subclasses
        self.is_loaded_flag = True
        return True
    
    def unload_engine(self) -> bool:
        """
        Unload the engine to free resources.
        
        Returns:
            True if successfully unloaded, False otherwise
        """
        # To be implemented by subclasses
        self.is_loaded_flag = False
        return True
    
    def is_loaded(self) -> bool:
        """
        Check if engine is currently loaded.
        
        Returns:
            True if loaded, False otherwise
        """
        return self.is_loaded_flag
    
    def synthesize(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            **kwargs: Additional parameters for synthesis
            
        Returns:
            Dict with synthesis results:
            {
                "audio": numpy array of audio samples,
                "sample_rate": int,
                "duration": float (seconds),
                "format": str (audio format)
            }
        """
        # To be implemented by subclasses
        # Start timing
        start_time = time.time()
        
        # Default implementation (silent audio)
        duration = 0.5  # seconds
        sample_rate = self.sample_rate
        audio = np.zeros(int(duration * sample_rate), dtype=np.float32)
        
        # Update stats
        synthesis_time = time.time() - start_time
        self.stats["synthesis_count"] += 1
        self.stats["total_duration"] += duration
        self.stats["total_audio_length"] += len(audio)
        self.stats["total_synthesis_time"] += synthesis_time
        self.stats["last_synthesis_time"] = synthesis_time
        self.stats["average_latency"] = self.stats["total_synthesis_time"] / self.stats["synthesis_count"]
        
        return {
            "audio": audio,
            "sample_rate": sample_rate,
            "duration": duration,
            "format": "raw",
            "latency": synthesis_time
        }
    
    def synthesize_ssml(self, ssml: str, **kwargs) -> Dict[str, Any]:
        """
        Synthesize speech from SSML markup.
        
        Args:
            ssml: SSML text to synthesize
            **kwargs: Additional parameters for synthesis
            
        Returns:
            Dict with synthesis results
        """
        # Default implementation (call regular synthesize)
        # Many engines don't support SSML directly
        logger.warning("SSML synthesis not supported by this engine, falling back to plain text")
        
        # Strip SSML tags to get plain text
        import re
        plain_text = re.sub(r'<[^>]+>', '', ssml)
        plain_text = plain_text.replace('<?xml version="1.0"?>', '')
        plain_text = plain_text.replace('<speak>', '').replace('</speak>', '')
        plain_text = plain_text.strip()
        
        return self.synthesize(plain_text, **kwargs)
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available voices for the current engine.
        
        Returns:
            List of voice information dictionaries
        """
        # To be implemented by subclasses
        return [{
            "id": "default",
            "name": "Default",
            "gender": "neutral",
            "language": "en"
        }]
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Change the voice to use for synthesis.
        
        Args:
            voice_id: Voice identifier to use
            
        Returns:
            True if voice was changed successfully, False otherwise
        """
        # Check if voice exists
        available_voices = self.get_available_voices()
        voice_ids = [voice["id"] for voice in available_voices]
        
        if voice_id in voice_ids:
            self.voice_id = voice_id
            return True
        else:
            logger.warning(f"Voice '{voice_id}' not found")
            return False
    
    def set_parameters(self, **params) -> bool:
        """
        Update synthesis parameters.
        
        Args:
            **params: Parameters to update
            
        Returns:
            True if parameters were updated successfully
        """
        # Update supported parameters
        for param, value in params.items():
            if param == "speaking_rate" and 0.5 <= value <= 2.0:
                self.speaking_rate = value
            elif param == "pitch" and -10.0 <= value <= 10.0:
                self.pitch = value
            elif param == "sample_rate" and 8000 <= value <= 48000:
                self.sample_rate = value
            elif param == "voice_id":
                self.set_voice(value)
            elif param == "model_path":
                self.model_path = value
            elif param == "api_key":
                self.api_key = value
                
        return True
    
    def get_engine_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded engine.
        
        Returns:
            Dict with engine information
        """
        return {
            "engine_type": self.engine_type.value,
            "is_loaded": self.is_loaded(),
            "voice_id": self.voice_id,
            "sample_rate": self.sample_rate,
            "speaking_rate": self.speaking_rate,
            "pitch": self.pitch,
            "stats": self.get_stats()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get synthesis statistics.
        
        Returns:
            Dict with synthesis statistics
        """
        return self.stats.copy()


def create_tts_adapter(config: Dict[str, Any]) -> TTSAdapter:
    """
    Factory function to create the appropriate TTS adapter.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        TTSAdapter instance
    """
    from voice.tts.tts_engine_api import OpenAITTSAdapter
    from voice.tts.tts_engine_local import PiperTTSAdapter
    from voice.tts.tts_engine_system import SystemTTSAdapter
    from voice.tts.bridge_adapter import TTSBridgeAdapter
    
    engine_type = config.get("engine_type", "local")
    
    if isinstance(engine_type, str):
        try:
            engine_type = TTSEngineType(engine_type)
        except ValueError:
            logger.warning(f"Invalid engine type: {engine_type}, using LOCAL")
            engine_type = TTSEngineType.LOCAL
            
    # Create the appropriate adapter based on engine type
    if engine_type == TTSEngineType.API:
        # Check for specific API provider
        api_provider = config.get("api_provider", "openai")
        
        if api_provider == "openai":
            return OpenAITTSAdapter(**config)
        else:
            logger.warning(f"Unknown API provider: {api_provider}, using OpenAI")
            return OpenAITTSAdapter(**config)
            
    elif engine_type == TTSEngineType.LOCAL:
        # Check for specific model type
        model_type = config.get("model_type", "piper")
        
        if model_type == "piper":
            return PiperTTSAdapter(**config)
        elif model_type == "coqui":
            # Could be implemented in future
            logger.warning("Coqui TTS not yet implemented, falling back to Piper")
            return PiperTTSAdapter(**config)
        else:
            logger.warning(f"Unknown local model type: {model_type}, using Piper")
            return PiperTTSAdapter(**config)
            
    elif engine_type == TTSEngineType.SYSTEM:
        return SystemTTSAdapter(**config)
        
    elif engine_type == TTSEngineType.BRIDGE:
        # Create the bridge adapter for Docker on macOS
        return TTSBridgeAdapter(config)
        
    else:
        logger.warning(f"Unknown engine type: {engine_type}, using SystemTTS")
        return SystemTTSAdapter(**config)