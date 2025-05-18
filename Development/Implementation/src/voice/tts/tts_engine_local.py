#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local TTS engine adapters for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_004 - Text-to-Speech Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-009-003 - Support both API and local models for TTS

import logging
import os
import subprocess
import tempfile
import json
import time
import numpy as np
from typing import Dict, Any, List, Optional
import soundfile as sf

from voice.tts.tts_adapter import TTSAdapter, TTSEngineType

logger = logging.getLogger(__name__)

class PiperTTSAdapter(TTSAdapter):
    """
    TTS adapter for Piper TTS (local voice synthesis).
    
    Piper is an open-source text-to-speech synthesizer that can run locally.
    This adapter provides integration with Piper for offline voice synthesis.
    """
    
    def __init__(self,
                 model_path: Optional[str] = None,
                 model_type: str = "piper",
                 voice_id: str = "default",
                 speaking_rate: float = 1.0,
                 pitch: float = 0.0,
                 sample_rate: int = 24000,
                 **kwargs):
        """
        Initialize Piper TTS adapter.
        
        Args:
            model_path: Path to Piper model files
            model_type: Type of model (always 'piper' for this adapter)
            voice_id: Voice identifier to use
            speaking_rate: Speech rate multiplier (0.5-2.0)
            pitch: Voice pitch adjustment (-10.0 to 10.0)
            sample_rate: Output audio sample rate
        """
        super().__init__(
            engine_type=TTSEngineType.LOCAL,
            voice_id=voice_id,
            model_path=model_path,
            speaking_rate=speaking_rate,
            pitch=pitch,
            sample_rate=sample_rate
        )
        
        # Piper-specific settings
        self.model_type = model_type
        self.piper_path = self._find_piper_executable()
        self.available_voices = []
        
        # Additional stats for Piper
        self.stats.update({
            "total_process_time": 0.0,
            "process_errors": 0,
            "process_calls": 0
        })
    
    def _find_piper_executable(self) -> str:
        """
        Find the Piper executable on the system.
        
        Returns:
            Path to Piper executable
        """
        # Default locations to check
        possible_paths = [
            "/usr/local/bin/piper",
            "/opt/homebrew/bin/piper",
            os.path.expanduser("~/.local/bin/piper")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found Piper executable at {path}")
                return path
                
        # If not found in standard locations, assume it's in PATH
        logger.info("Piper executable not found in standard locations, assuming it's in PATH")
        return "piper"
    
    def _get_model_from_registry(self) -> str:
        """
        Get model path from the model registry.
        
        Returns:
            Path to Piper model file
        
        Raises:
            ValueError: If no suitable model is found in registry
        """
        try:
            # Import model registry module
            # This assumes the model registry module exists as implemented in ENV_003
            from models.registry import ModelRegistry
            registry = ModelRegistry()
            
            # Try to find the specific voice
            voice_model_id = f"piper-{self.voice_id}"
            model_info = registry.get_model(voice_model_id)
            
            # If not found, get any Piper model
            if not model_info:
                models = registry.get_models_by_type("tts")
                piper_models = [m for m in models if m["name"].startswith("piper-")]
                if piper_models:
                    model_info = piper_models[0]
                    
            if not model_info:
                raise ValueError("No Piper TTS model found in registry")
                
            return model_info["path"]
            
        except ImportError:
            logger.error("Model registry module not found")
            raise ValueError("Model registry not available")
        except Exception as e:
            logger.error(f"Error loading model from registry: {e}")
            raise ValueError(f"Error loading model from registry: {e}")
    
    def load_engine(self) -> bool:
        """
        Load the Piper TTS engine.
        
        Returns:
            True if successfully loaded, False otherwise
        """
        # Try to get model path if not provided
        if not self.model_path:
            try:
                self.model_path = self._get_model_from_registry()
                logger.info(f"Loaded Piper model from registry: {self.model_path}")
            except Exception as e:
                logger.error(f"Error loading Piper model from registry: {e}")
                return False
                
        # Check if model exists
        if not os.path.exists(self.model_path):
            logger.error(f"Piper model not found at {self.model_path}")
            return False
            
        # Load available voices
        self._load_available_voices()
        
        # Check if piper executable is available
        try:
            result = subprocess.run(
                [self.piper_path, "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                logger.error(f"Piper executable check failed: {result.stderr}")
                return False
                
            logger.info(f"Piper executable found: {result.stdout.strip()}")
            
        except Exception as e:
            logger.error(f"Error checking Piper executable: {e}")
            return False
        
        self.is_loaded_flag = True
        return True
    
    def _load_available_voices(self) -> None:
        """
        Load available voices from model directory.
        
        Piper models typically have JSON configuration files that contain
        voice metadata. This method searches for these files and extracts
        the voice information.
        """
        if not self.model_path:
            return
            
        model_dir = os.path.dirname(self.model_path)
        self.available_voices = []
        
        try:
            # Try to find voice configuration files
            config_files = [f for f in os.listdir(model_dir) if f.endswith(".json")]
            
            for config_file in config_files:
                try:
                    with open(os.path.join(model_dir, config_file), 'r') as f:
                        config = json.load(f)
                        if "name" in config:
                            self.available_voices.append({
                                "id": os.path.splitext(os.path.basename(config_file))[0],
                                "name": config.get("name", "Unknown"),
                                "language": config.get("language", "en"),
                                "gender": config.get("gender", "neutral")
                            })
                except Exception as e:
                    logger.warning(f"Error parsing voice config file {config_file}: {e}")
                    
        except Exception as e:
            logger.warning(f"Error loading Piper voices: {e}")
            
        # If no voices were found, add a default voice entry
        if not self.available_voices:
            model_name = os.path.basename(self.model_path)
            self.available_voices.append({
                "id": os.path.splitext(model_name)[0],
                "name": os.path.splitext(model_name)[0],
                "language": "en",
                "gender": "neutral"
            })
            
        logger.info(f"Loaded {len(self.available_voices)} Piper voices")
    
    def unload_engine(self) -> bool:
        """
        Unload the Piper TTS engine.
        
        Returns:
            True if successfully unloaded
        """
        # Not much to clean up for Piper as it's used via subprocess
        self.is_loaded_flag = False
        return True
    
    def synthesize(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Synthesize speech using Piper TTS.
        
        Args:
            text: Text to synthesize
            **kwargs: Additional parameters
                - speaking_rate: Override speaking rate
                - pitch: Override pitch
            
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
        speaking_rate = kwargs.get("speaking_rate", self.speaking_rate)
        
        try:
            # Start timing
            start_time = time.time()
            
            # Create temporary files for input and output
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as text_file:
                text_file.write(text.encode('utf-8'))
                text_file_path = text_file.name
                
            output_file_path = text_file_path + ".wav"
            
            # Build Piper command
            cmd = [
                self.piper_path,
                "--model", self.model_path,
                "--output_file", output_file_path,
                # Piper's length scale is inverse of speaking rate
                # (higher length scale = slower speech)
                "--length_scale", str(1.0 / max(0.5, min(2.0, speaking_rate)))
            ]
            
            # Add input file
            cmd.extend(["--input_file", text_file_path])
            
            # Update stats
            self.stats["process_calls"] += 1
            
            # Execute Piper
            process_start = time.time()
            process_result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True,
                text=True
            )
            process_time = time.time() - process_start
            self.stats["total_process_time"] += process_time
            
            # Read the output audio file
            audio_array, sample_rate = sf.read(output_file_path)
            
            # Clean up temporary files
            try:
                os.unlink(text_file_path)
                os.unlink(output_file_path)
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
                "format": "wav",
                "latency": synthesis_time
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing speech with Piper TTS: {e}")
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
        Get list of available Piper voices.
        
        Returns:
            List of voice information dictionaries
        """
        if not self.is_loaded():
            self.load_engine()
        return self.available_voices
    
    def get_engine_info(self) -> Dict[str, Any]:
        """
        Get information about the Piper TTS engine.
        
        Returns:
            Dict with engine information
        """
        info = super().get_engine_info()
        info.update({
            "model_path": self.model_path,
            "model_type": self.model_type,
            "piper_executable": self.piper_path
        })
        return info