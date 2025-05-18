#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Speech synthesizer for the VANTA Voice Pipeline.

Provides a high-level interface for text-to-speech synthesis
with caching, preprocessing, and TTS engine management.
"""
# TASK-REF: VOICE_004 - Text-to-Speech Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-004-003 - Implement natural conversational features

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import numpy as np
from collections import OrderedDict

from voice.tts.tts_adapter import TTSAdapter, create_tts_adapter
from voice.tts.prosody_formatter import ProsodyFormatter

logger = logging.getLogger(__name__)

class SpeechSynthesizer:
    """
    High-level speech synthesis manager.
    
    Provides caching, preprocessing, and management for
    text-to-speech operations, acting as a facade over the
    underlying TTS engine implementations.
    """
    
    def __init__(self,
                 tts_adapter: Optional[TTSAdapter] = None,
                 enable_caching: bool = True,
                 cache_size: int = 50,
                 preprocess_text: bool = True,
                 enable_ssml: bool = True):
        """
        Initialize speech synthesizer.
        
        Args:
            tts_adapter: TTSAdapter instance or None to create default
            enable_caching: Whether to cache synthesis results
            cache_size: Size of synthesis cache
            preprocess_text: Whether to preprocess text before synthesis
            enable_ssml: Whether to use SSML for prosody control
        """
        # Initialize TTS adapter
        self.tts_adapter = tts_adapter or create_tts_adapter({})
        
        # Configure behavior
        self.enable_caching = enable_caching
        self.cache_size = cache_size
        self.preprocess_text = preprocess_text
        self.enable_ssml = enable_ssml
        
        # Create prosody formatter
        self.prosody_formatter = ProsodyFormatter()
        
        # Initialize synthesis cache
        self.cache = OrderedDict()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_synthesis_time": 0.0,
            "total_text_length": 0,
            "last_synthesis_time": 0.0,
            "average_latency": 0.0
        }
    
    def synthesize(self, 
                   text: str, 
                   voice_id: Optional[str] = None,
                   speaking_rate: Optional[float] = None,
                   pitch: Optional[float] = None,
                   use_ssml: Optional[bool] = None) -> Dict[str, Any]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice_id: Voice to use (or None for default)
            speaking_rate: Speaking rate override
            pitch: Pitch override
            use_ssml: Whether to generate SSML (if None, use default setting)
            
        Returns:
            Dict with synthesis results
        """
        start_time = time.time()
        self.stats["total_requests"] += 1
        self.stats["total_text_length"] += len(text)
        
        # Skip empty text
        if not text.strip():
            logger.warning("Empty text provided to synthesize")
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": 24000,
                "duration": 0.0,
                "text": "",
                "latency": 0.0
            }
        
        # Check if TTS adapter is loaded
        if not self.tts_adapter.is_loaded():
            self.tts_adapter.load_engine()
        
        # Preprocess text if enabled
        if self.preprocess_text:
            text = self.preprocess_text_for_synthesis(text)
        
        # Determine whether to use SSML
        should_use_ssml = use_ssml if use_ssml is not None else self.enable_ssml
        
        # Set up synthesis parameters
        synthesis_params = {}
        if voice_id:
            synthesis_params["voice_id"] = voice_id
        if speaking_rate:
            synthesis_params["speaking_rate"] = speaking_rate
        if pitch:
            synthesis_params["pitch"] = pitch
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            text, 
            self.tts_adapter.engine_type.value,
            voice_id or self.tts_adapter.voice_id,
            speaking_rate or self.tts_adapter.speaking_rate,
            pitch or self.tts_adapter.pitch,
            should_use_ssml
        )
        
        # Check cache
        if self.enable_caching and cache_key in self.cache:
            self.stats["cache_hits"] += 1
            # Move to end to mark as recently used
            self.cache.move_to_end(cache_key)
            logger.debug(f"Cache hit for text: '{text[:30]}...'")
            
            # Update latency stats using cached value
            synthesis_time = time.time() - start_time
            self.stats["last_synthesis_time"] = synthesis_time
            self.stats["total_synthesis_time"] += synthesis_time
            self.stats["average_latency"] = self.stats["total_synthesis_time"] / self.stats["total_requests"]
            
            return self.cache[cache_key]
        
        # Cache miss - synthesize
        self.stats["cache_misses"] += 1
        
        try:
            # Convert to SSML if needed
            if should_use_ssml:
                ssml = self.prosody_formatter.to_ssml(
                    text,
                    speaking_rate=speaking_rate or self.tts_adapter.speaking_rate,
                    pitch=pitch or self.tts_adapter.pitch
                )
                result = self.tts_adapter.synthesize_ssml(ssml, **synthesis_params)
            else:
                result = self.tts_adapter.synthesize(text, **synthesis_params)
            
            # Add original text and cache key to result
            result["text"] = text
            result["cache_key"] = cache_key
            
            # Store in cache if enabled
            if self.enable_caching and not "error" in result:
                # Add to cache
                self.cache[cache_key] = result
                
                # Enforce cache size limit
                while len(self.cache) > self.cache_size:
                    # Remove oldest entry (first item in OrderedDict)
                    self.cache.popitem(last=False)
            
            # Update latency stats
            synthesis_time = time.time() - start_time
            self.stats["last_synthesis_time"] = synthesis_time
            self.stats["total_synthesis_time"] += synthesis_time
            self.stats["average_latency"] = self.stats["total_synthesis_time"] / self.stats["total_requests"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error in speech synthesis: {e}")
            
            # Return empty audio on error
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": self.tts_adapter.sample_rate,
                "duration": 0.0,
                "text": text,
                "error": str(e),
                "latency": time.time() - start_time
            }
    
    def _generate_cache_key(self, text: str, engine_type: str, voice_id: str, 
                          speaking_rate: float, pitch: float, use_ssml: bool) -> str:
        """
        Generate a unique cache key for synthesis parameters.
        
        Args:
            text: Text to synthesize
            engine_type: TTS engine type
            voice_id: Voice ID
            speaking_rate: Speaking rate
            pitch: Pitch adjustment
            use_ssml: Whether SSML is used
            
        Returns:
            String hash for cache key
        """
        # Create a string with all parameters
        key_string = f"{text}|{engine_type}|{voice_id}|{speaking_rate}|{pitch}|{use_ssml}"
        
        # Generate hash for the key
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def preprocess_text_for_synthesis(self, text: str) -> str:
        """
        Preprocess text for better synthesis.
        
        Args:
            text: Text to preprocess
            
        Returns:
            Preprocessed text
        """
        return self.prosody_formatter.format_text(text)
    
    def generate_ssml(self, text: str, **kwargs) -> str:
        """
        Generate SSML markup for the text.
        
        Args:
            text: Text to convert to SSML
            **kwargs: Additional parameters for SSML generation
            
        Returns:
            SSML markup
        """
        return self.prosody_formatter.to_ssml(text, **kwargs)
    
    def clear_cache(self) -> None:
        """Clear synthesis cache."""
        self.cache.clear()
        logger.info("Speech synthesis cache cleared")
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available voices.
        
        Returns:
            List of voice information dictionaries
        """
        return self.tts_adapter.get_available_voices()
    
    def set_voice(self, voice_id: str) -> bool:
        """
        Set the default voice.
        
        Args:
            voice_id: Voice ID to use
            
        Returns:
            True if voice was set successfully
        """
        return self.tts_adapter.set_voice(voice_id)
    
    def configure(self, **kwargs) -> None:
        """
        Update synthesizer configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        # Update synthesizer settings
        if "enable_caching" in kwargs:
            self.enable_caching = kwargs["enable_caching"]
            
        if "cache_size" in kwargs:
            self.cache_size = kwargs["cache_size"]
            # Enforce new cache size
            while len(self.cache) > self.cache_size:
                self.cache.popitem(last=False)
                
        if "preprocess_text" in kwargs:
            self.preprocess_text = kwargs["preprocess_text"]
            
        if "enable_ssml" in kwargs:
            self.enable_ssml = kwargs["enable_ssml"]
        
        # Update prosody formatter settings
        prosody_settings = {}
        for key in ["add_punctuation", "enhance_questions", "enhance_emphasis", 
                    "normalize_numbers", "expand_abbreviations"]:
            if key in kwargs:
                prosody_settings[key] = kwargs[key]
                
        if prosody_settings:
            self.prosody_formatter = ProsodyFormatter(**prosody_settings)
            
        # Update TTS adapter settings
        adapter_settings = {}
        for key in ["voice_id", "speaking_rate", "pitch", "sample_rate", 
                    "model_path", "api_key", "model"]:
            if key in kwargs:
                adapter_settings[key] = kwargs[key]
                
        if adapter_settings:
            self.tts_adapter.set_parameters(**adapter_settings)
            
        # Create new TTS adapter if engine type changes
        if "engine_type" in kwargs:
            # Preserve existing settings
            engine_config = {
                "engine_type": kwargs["engine_type"],
                "voice_id": self.tts_adapter.voice_id,
                "speaking_rate": self.tts_adapter.speaking_rate,
                "pitch": self.tts_adapter.pitch,
                "sample_rate": self.tts_adapter.sample_rate
            }
            
            # Add engine-specific parameters
            for key in ["model_path", "api_key", "model", "model_type", "api_provider"]:
                if key in kwargs:
                    engine_config[key] = kwargs[key]
                elif hasattr(self.tts_adapter, key):
                    engine_config[key] = getattr(self.tts_adapter, key)
                    
            # Create new adapter
            self.tts_adapter = create_tts_adapter(engine_config)
            self.tts_adapter.load_engine()
            
            # Clear cache as we switched engines
            self.clear_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get synthesizer statistics.
        
        Returns:
            Dict with statistics
        """
        # Combine synthesizer and adapter stats
        stats = self.stats.copy()
        stats["adapter"] = self.tts_adapter.get_stats()
        stats["cache_size"] = len(self.cache)
        stats["cache_limit"] = self.cache_size
        stats["adapter_info"] = self.tts_adapter.get_engine_info()
        
        return stats