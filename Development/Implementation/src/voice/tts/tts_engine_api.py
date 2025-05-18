#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API-based TTS engine adapters for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_004 - Text-to-Speech Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-009-003 - Support both API and local models for TTS

import logging
import time
import io
import numpy as np
from typing import Dict, Any, List, Optional
import soundfile as sf

from voice.tts.tts_adapter import TTSAdapter, TTSEngineType

logger = logging.getLogger(__name__)

class OpenAITTSAdapter(TTSAdapter):
    """
    TTS adapter for OpenAI's TTS API.
    
    Provides integration with OpenAI's text-to-speech API
    with support for multiple voices and configurations.
    """
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 voice_id: str = "alloy",  # OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
                 model: str = "tts-1",    # "tts-1" or "tts-1-hd"
                 speaking_rate: float = 1.0,
                 pitch: float = 0.0,
                 sample_rate: int = 24000,
                 **kwargs):
        """
        Initialize OpenAI TTS adapter.
        
        Args:
            api_key: OpenAI API key
            voice_id: Voice to use
            model: Model name to use
            speaking_rate: Speech rate multiplier (0.5-2.0)
            pitch: Voice pitch adjustment (-10.0 to 10.0)
            sample_rate: Output audio sample rate
        """
        super().__init__(
            engine_type=TTSEngineType.API,
            voice_id=voice_id,
            api_key=api_key,
            speaking_rate=speaking_rate,
            pitch=pitch,
            sample_rate=sample_rate
        )
        
        self.model = model
        self.available_voices = [
            {"id": "alloy", "name": "Alloy", "gender": "neutral", "language": "en"},
            {"id": "echo", "name": "Echo", "gender": "male", "language": "en"},
            {"id": "fable", "name": "Fable", "gender": "female", "language": "en"},
            {"id": "onyx", "name": "Onyx", "gender": "male", "language": "en"},
            {"id": "nova", "name": "Nova", "gender": "female", "language": "en"},
            {"id": "shimmer", "name": "Shimmer", "gender": "female", "language": "en"}
        ]
        
        # Additional stats for OpenAI API
        self.stats.update({
            "api_calls": 0,
            "api_errors": 0,
            "total_tokens": 0,
            "total_api_latency": 0.0
        })
        
        # Try to load OpenAI for early failure
        self._import_openai()
    
    def _import_openai(self):
        """Import the OpenAI package and check if it's available."""
        try:
            import openai
            return openai
        except ImportError:
            logger.error("OpenAI package not found. Install with: pip install openai")
            raise ImportError("OpenAI package is required for OpenAITTSAdapter")
    
    def load_engine(self) -> bool:
        """
        Set up the OpenAI API client.
        
        Returns:
            True if setup was successful, False otherwise
        """
        try:
            openai = self._import_openai()
            
            # Set API key if provided
            if self.api_key:
                openai.api_key = self.api_key
                
            # Check if API key is set
            if not openai.api_key:
                # Try to get from environment
                import os
                if "OPENAI_API_KEY" not in os.environ:
                    logger.error("OpenAI API key not provided and not found in environment")
                    return False
            
            self.is_loaded_flag = True
            return True
            
        except Exception as e:
            logger.error(f"Error loading OpenAI TTS engine: {e}")
            return False
    
    def unload_engine(self) -> bool:
        """
        Release resources associated with the OpenAI API.
        
        Returns:
            True if unloading was successful
        """
        # Not much to clean up for API-based TTS
        self.is_loaded_flag = False
        return True
    
    def synthesize(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Synthesize speech using OpenAI TTS API.
        
        Args:
            text: Text to synthesize
            **kwargs: Additional parameters
                - voice_id: Override voice to use
                - model: Override model to use
                - speaking_rate: Override speaking rate
            
        Returns:
            Dict with synthesis results
        """
        if not text.strip():
            logger.warning("Empty text provided to synthesize")
            # Return empty audio
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": self.sample_rate,
                "duration": 0.0,
                "format": "raw",
                "latency": 0.0
            }
            
        if not self.is_loaded():
            self.load_engine()
            
        # Apply parameters
        voice = kwargs.get("voice_id", self.voice_id)
        model = kwargs.get("model", self.model)
        speaking_rate = kwargs.get("speaking_rate", self.speaking_rate)
        
        try:
            # Import OpenAI
            openai = self._import_openai()
            
            # Start timing
            start_time = time.time()
            
            # Make API request
            self.stats["api_calls"] += 1
            
            # Estimate token count (very rough estimate)
            estimated_tokens = len(text.split())
            self.stats["total_tokens"] += estimated_tokens
            
            # Call OpenAI API
            response = openai.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                speed=speaking_rate,
                response_format="mp3"
            )
            
            # Get audio data
            audio_data = response.content
            
            # Convert to numpy array
            with io.BytesIO(audio_data) as audio_buffer:
                audio_array, sample_rate = sf.read(audio_buffer)
                
            # Convert to mono if needed
            if len(audio_array.shape) > 1:
                audio_array = audio_array.mean(axis=1)
                
            # Calculate duration
            duration = len(audio_array) / sample_rate
            
            # Calculate latency
            synthesis_time = time.time() - start_time
            self.stats["total_api_latency"] += synthesis_time
            
            # Update stats
            self.stats["synthesis_count"] += 1
            self.stats["total_duration"] += duration
            self.stats["total_audio_length"] += len(audio_array)
            self.stats["total_synthesis_time"] += synthesis_time
            self.stats["last_synthesis_time"] = synthesis_time
            self.stats["average_latency"] = self.stats["total_synthesis_time"] / self.stats["synthesis_count"]
            
            return {
                "audio": audio_array,
                "sample_rate": sample_rate,
                "duration": duration,
                "format": "mp3",
                "latency": synthesis_time
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing speech with OpenAI TTS: {e}")
            self.stats["api_errors"] += 1
            
            # Return empty audio on error
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": self.sample_rate,
                "duration": 0.0,
                "format": "raw",
                "error": str(e),
                "latency": time.time() - start_time
            }
    
    def synthesize_ssml(self, ssml: str, **kwargs) -> Dict[str, Any]:
        """
        Synthesize speech from SSML markup.
        
        Args:
            ssml: SSML text to synthesize
            **kwargs: Additional parameters
            
        Returns:
            Dict with synthesis results
        """
        # OpenAI doesn't support SSML directly, so we fall back to plain text
        import re
        plain_text = re.sub(r'<[^>]+>', '', ssml)
        plain_text = plain_text.replace('<?xml version="1.0"?>', '')
        plain_text = plain_text.replace('<speak>', '').replace('</speak>', '')
        plain_text = plain_text.strip()
        
        logger.info("OpenAI TTS doesn't support SSML, converting to plain text")
        return self.synthesize(plain_text, **kwargs)
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available OpenAI voices.
        
        Returns:
            List of voice information dictionaries
        """
        return self.available_voices
    
    def get_engine_info(self) -> Dict[str, Any]:
        """
        Get information about the OpenAI TTS engine.
        
        Returns:
            Dict with engine information
        """
        info = super().get_engine_info()
        info.update({
            "model": self.model,
            "api_provider": "openai"
        })
        return info
    
    def set_parameters(self, **params) -> bool:
        """
        Update synthesis parameters.
        
        Args:
            **params: Parameters to update
            
        Returns:
            True if parameters were updated successfully
        """
        # Update OpenAI-specific parameters
        if "model" in params:
            model = params["model"]
            if model in ["tts-1", "tts-1-hd"]:
                self.model = model
            else:
                logger.warning(f"Invalid OpenAI TTS model: {model}")
        
        # Update common parameters
        return super().set_parameters(**params)