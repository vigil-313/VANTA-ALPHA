#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System TTS engine adapter for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_004 - Text-to-Speech Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-009-003 - Support both API and local models for TTS

import logging
import os
import subprocess
import tempfile
import platform
import time
import numpy as np
from typing import Dict, Any, List, Optional
import soundfile as sf

from voice.tts.tts_adapter import TTSAdapter, TTSEngineType

logger = logging.getLogger(__name__)

class SystemTTSAdapter(TTSAdapter):
    """
    TTS adapter for system TTS services (e.g., macOS 'say' command).
    
    Provides integration with the operating system's built-in 
    text-to-speech capabilities.
    """
    
    def __init__(self,
                 voice_id: str = "Alex",  # Default macOS voice
                 speaking_rate: float = 1.0,
                 pitch: float = 0.0,
                 sample_rate: int = 24000,
                 **kwargs):
        """
        Initialize System TTS adapter.
        
        Args:
            voice_id: System voice name to use
            speaking_rate: Speech rate multiplier (0.5-2.0)
            pitch: Voice pitch adjustment (-10.0 to 10.0)
            sample_rate: Output audio sample rate
        """
        super().__init__(
            engine_type=TTSEngineType.SYSTEM,
            voice_id=voice_id,
            speaking_rate=speaking_rate,
            pitch=pitch,
            sample_rate=sample_rate
        )
        
        self.available_voices = []
        self.platform = platform.system()
        
        # Additional stats for system TTS
        self.stats.update({
            "total_process_time": 0.0,
            "process_errors": 0,
            "process_calls": 0
        })
    
    def load_engine(self) -> bool:
        """
        Initialize system TTS.
        
        Returns:
            True if successfully loaded, False otherwise
        """
        # Check platform compatibility
        if self.platform == "Darwin":  # macOS
            self._load_macos_voices()
            self.is_loaded_flag = True
            return True
        else:
            logger.warning(f"System TTS not fully supported on {self.platform}")
            # Still mark as loaded, but with limited functionality
            self.is_loaded_flag = True
            return True
    
    def _load_macos_voices(self) -> None:
        """
        Load available voices on macOS.
        
        Uses the 'say' command to get a list of available voices.
        """
        try:
            # Use 'say' command to get available voices
            result = subprocess.run(
                ["say", "-v", "?"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Parse the output
            lines = result.stdout.strip().split('\n')
            self.available_voices = []
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    voice_id = parts[0]
                    
                    # Try to determine gender
                    gender = "female" if any(fem in line.lower() for fem in ["fem", "woman", "girl"]) else "male"
                    if any(neu in line.lower() for neu in ["neutral", "robot"]):
                        gender = "neutral"
                        
                    # Try to extract language
                    language = "en"  # Default
                    if "#" in line:
                        lang_part = line.split("#")[1].strip()
                        if len(lang_part) >= 2:
                            language = lang_part.split("_")[0].lower()
                            
                    self.available_voices.append({
                        "id": voice_id,
                        "name": voice_id,
                        "language": language,
                        "gender": gender
                    })
            
            logger.info(f"Loaded {len(self.available_voices)} system voices")
                    
        except Exception as e:
            logger.error(f"Error loading macOS voices: {e}")
            # Add a default voice
            self.available_voices = [{
                "id": "Alex",
                "name": "Alex",
                "language": "en",
                "gender": "male"
            }]
    
    def unload_engine(self) -> bool:
        """
        Release resources.
        
        Returns:
            True if successfully unloaded
        """
        # Not much to clean up for system TTS
        self.is_loaded_flag = False
        return True
    
    def synthesize(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Synthesize speech using system TTS.
        
        Args:
            text: Text to synthesize
            **kwargs: Additional parameters
                - voice_id: Override voice to use
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
        speaking_rate = kwargs.get("speaking_rate", self.speaking_rate)
        
        # Choose platform-specific synthesis method
        if self.platform == "Darwin":  # macOS
            return self._synthesize_macos(text, voice, speaking_rate)
        else:
            logger.error(f"System TTS not supported on {self.platform}")
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": self.sample_rate,
                "duration": 0.0,
                "format": "raw",
                "error": f"System TTS not supported on {self.platform}",
                "latency": 0.0
            }
    
    def _synthesize_macos(self, text: str, voice: str, speaking_rate: float) -> Dict[str, Any]:
        """
        Synthesize speech using macOS 'say' command.
        
        Args:
            text: Text to synthesize
            voice: Voice to use
            speaking_rate: Speaking rate multiplier
            
        Returns:
            Dict with synthesis results
        """
        try:
            # Start timing
            start_time = time.time()
            
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as out_file:
                output_path = out_file.name
            
            # Create temporary text file for long inputs
            with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as text_file:
                text_file.write(text)
                text_path = text_file.name
            
            # Use 'say' command to generate speech
            rate_param = int(200 * speaking_rate)  # Default is 200
            
            # Update stats
            self.stats["process_calls"] += 1
            
            # Execute command
            process_start = time.time()
            subprocess.run([
                "say",
                "-v", voice,
                "-r", str(rate_param),
                "-o", output_path,
                "-f", text_path
            ], check=True)
            process_time = time.time() - process_start
            self.stats["total_process_time"] += process_time
            
            # Read the output audio file
            audio_array, sample_rate = sf.read(output_path)
            
            # Clean up temporary files
            try:
                os.unlink(output_path)
                os.unlink(text_path)
            except Exception as e:
                logger.warning(f"Error cleaning up temporary files: {e}")
            
            # Calculate duration
            duration = len(audio_array) / sample_rate
            
            # Update synthesis stats
            synthesis_time = time.time() - start_time
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
                "format": "aiff",
                "latency": synthesis_time
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing speech with macOS TTS: {e}")
            self.stats["process_errors"] += 1
            
            # Return empty audio on error
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": self.sample_rate,
                "duration": 0.0,
                "format": "raw",
                "error": str(e),
                "latency": time.time() - start_time
            }
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available system voices.
        
        Returns:
            List of voice information dictionaries
        """
        if not self.is_loaded():
            self.load_engine()
        return self.available_voices
    
    def get_engine_info(self) -> Dict[str, Any]:
        """
        Get information about the system TTS engine.
        
        Returns:
            Dict with engine information
        """
        info = super().get_engine_info()
        info.update({
            "platform": self.platform,
            "system_tts": "say" if self.platform == "Darwin" else "unknown"
        })
        return info