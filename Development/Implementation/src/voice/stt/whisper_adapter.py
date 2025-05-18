#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper speech recognition adapter for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_003 - Speech-to-Text Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-001 - Use Whisper for speech-to-text conversion

import logging
import os
import numpy as np
import torch
from typing import Dict, Any, Optional, List, Union, Tuple

logger = logging.getLogger(__name__)

class WhisperAdapter:
    """
    Adapter for the Whisper speech recognition model.
    
    Provides an interface for loading and using Whisper models,
    with optimizations for Apple Silicon hardware and resource management.
    """
    
    def __init__(self, 
                model_size: str = "small",  # tiny, base, small
                device: str = "mps",       # cpu, mps (Metal)
                compute_type: str = "int8", # float16, int8, float32
                language: str = "en",      # language code
                beam_size: int = 5):
        """
        Initialize Whisper model adapter.
        
        Args:
            model_size: Size of Whisper model to use
            device: Compute device (cpu or mps for Metal)
            compute_type: Computation precision
            language: Language code for transcription
            beam_size: Beam search size for decoding
        """
        self.model_size = model_size
        self.device_name = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size
        
        # Model will be loaded on demand
        self.model = None
        self.device = None
        self.model_path = None
        
        # Statistics
        self.stats = {
            "transcription_count": 0,
            "total_audio_seconds": 0.0,
            "total_transcription_time": 0.0,
            "model_info": None
        }
        
        logger.info(f"Initialized WhisperAdapter with model_size={model_size}, "
                   f"device={device}, compute_type={compute_type}")
    
    def load_model(self) -> bool:
        """
        Load the Whisper model.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        if self.is_loaded():
            logger.info("Whisper model already loaded")
            return True
            
        logger.info(f"Loading Whisper model (size={self.model_size})")
        
        try:
            # Determine the compute device
            if self.device_name == "mps" and torch.backends.mps.is_available():
                self.device = torch.device("mps")
                logger.info("Using Metal Performance Shaders (MPS) for Whisper inference")
            elif self.device_name == "cuda" and torch.cuda.is_available():
                self.device = torch.device("cuda")
                logger.info("Using CUDA for Whisper inference")
            else:
                self.device = torch.device("cpu")
                logger.info("Using CPU for Whisper inference")
                
            # Try to use faster whisper.cpp implementation if available
            try:
                logger.info("Attempting to use whisper.cpp implementation")
                self._load_whisper_cpp()
                return True
            except (ImportError, RuntimeError) as e:
                logger.warning(f"Failed to load whisper.cpp: {e}. Falling back to Python implementation.")
                self._load_whisper_python()
                return True
                
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.model = None
            return False
    
    def _load_whisper_cpp(self) -> None:
        """
        Load the Whisper model using whisper.cpp bindings.
        """
        try:
            import whisperc  # C++ bindings for Whisper
        except ImportError:
            raise ImportError("whisper.cpp bindings not found. Make sure whisperc is installed.")
            
        # Get model path from registry
        self.model_path = self._get_model_from_registry()
        
        # Initialize whisper.cpp context
        self.model = whisperc.Context()
        
        # Set Metal acceleration if available and requested
        if self.device_name == "mps" and whisperc.has_metal():
            self.model.set_metal(True)
            
        # Load the model
        result = self.model.load_model(self.model_path)
        if not result:
            raise RuntimeError(f"Failed to load model from {self.model_path}")
            
        # Configure the context
        self.model.set_language(self.language)
        self.model.set_beam_search(self.beam_size, self.beam_size)
        
        # Store model info
        self.stats["model_info"] = {
            "implementation": "whisper.cpp",
            "model_size": self.model_size,
            "device": self.device_name,
            "compute_type": self.compute_type,
            "path": self.model_path
        }
        
        logger.info(f"Loaded Whisper model via whisper.cpp: {self.model_path}")
        self.using_cpp = True
        
    def _load_whisper_python(self) -> None:
        """
        Load the Whisper model using Python OpenAI implementation.
        """
        import whisper
        from whisper.model import type_as
        
        # Get model path from registry or use default
        try:
            self.model_path = self._get_model_from_registry()
            logger.info(f"Loading from registry path: {self.model_path}")
            download_root = os.path.dirname(os.path.dirname(self.model_path))
        except Exception as e:
            logger.warning(f"Could not get model from registry: {e}. Using default download location.")
            download_root = os.path.join(os.getcwd(), "models", "whisper")
            
        # Determine compute type
        if self.compute_type == "float16" and self.device.type != "cpu":
            torch_dtype = torch.float16
        else:
            torch_dtype = torch.float32
            
        # Load the model
        self.model = whisper.load_model(
            self.model_size, 
            device=self.device, 
            download_root=download_root, 
            in_memory=True
        )
        
        # Store model info
        self.stats["model_info"] = {
            "implementation": "whisper-python",
            "model_size": self.model_size,
            "device": self.device.type,
            "compute_type": torch_dtype.__name__,
            "path": download_root
        }
        
        logger.info(f"Loaded Whisper model via Python API: {self.model_size}")
        self.using_cpp = False
        
    def _get_model_from_registry(self) -> str:
        """
        Get model path from the registry.
        
        Returns:
            Path to the model file
            
        Raises:
            ValueError: If model not found in registry
        """
        try:
            # Dynamic import to avoid circular dependencies
            import sys
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
            from models.registry.model_registry import ModelRegistry
            
            registry = ModelRegistry()
            model_info = registry.get_model(f"whisper-{self.model_size}")
            
            if not model_info:
                raise ValueError(f"Model whisper-{self.model_size} not found in registry")
                
            return model_info["path"]
        except ImportError:
            raise ValueError("Model registry not found. Check your installation.")
    
    def unload_model(self) -> None:
        """
        Unload the model to free resources.
        """
        if not self.is_loaded():
            return
            
        logger.info("Unloading Whisper model")
        
        try:
            # Release model resources
            if hasattr(self, 'using_cpp') and self.using_cpp:
                # C++ model cleanup
                self.model = None
            else:
                # Python model cleanup
                self.model = None
                if self.device and self.device.type == "cuda":
                    # Clean CUDA cache
                    torch.cuda.empty_cache()
                elif self.device and self.device.type == "mps":
                    # Clear MPS cache if possible
                    torch.mps.empty_cache()
        except Exception as e:
            logger.error(f"Error unloading model: {e}")
        finally:
            self.model = None
    
    def is_loaded(self) -> bool:
        """
        Check if model is currently loaded.
        
        Returns:
            True if model is loaded
        """
        return self.model is not None
    
    def transcribe(self, audio_data: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Numpy array of audio samples (16kHz, mono, float32)
            **kwargs: Additional parameters for transcription
                language: Override language setting
                beam_size: Override beam size setting
                
        Returns:
            Dict with transcription results:
            {
                "text": str,
                "segments": List of segment dicts,
                "language": str,
                "confidence": float
            }
        """
        import time
        
        # Load model if not already loaded
        if not self.is_loaded():
            if not self.load_model():
                return {"text": "", "segments": [], "language": self.language, "confidence": 0}
                
        # Ensure audio is in the correct format
        if not isinstance(audio_data, np.ndarray):
            logger.error("Audio data must be a numpy array")
            return {"text": "", "segments": [], "language": self.language, "confidence": 0}
            
        # Convert to float32 if needed
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            
        # Ensure audio is normalized to [-1, 1]
        max_abs = np.max(np.abs(audio_data))
        if max_abs > 1.0:
            audio_data = audio_data / max_abs
            
        # Measure audio duration
        sample_rate = kwargs.get("sample_rate", 16000)
        audio_duration = len(audio_data) / sample_rate
        
        # Skip if audio is too short
        if audio_duration < 0.1:
            logger.debug("Audio too short, skipping transcription")
            return {"text": "", "segments": [], "language": self.language, "confidence": 0}
            
        # Track statistics
        start_time = time.time()
        
        try:
            # Choose implementation based on loaded model
            if hasattr(self, 'using_cpp') and self.using_cpp:
                result = self._transcribe_whisperc(audio_data, **kwargs)
            else:
                result = self._transcribe_whisper_python(audio_data, **kwargs)
                
            # Update statistics
            end_time = time.time()
            transcription_time = end_time - start_time
            
            self.stats["transcription_count"] += 1
            self.stats["total_audio_seconds"] += audio_duration
            self.stats["total_transcription_time"] += transcription_time
            
            logger.debug(f"Transcribed {audio_duration:.2f}s audio in {transcription_time:.2f}s "
                        f"(x{audio_duration/transcription_time:.2f} real-time)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return {"text": "", "segments": [], "language": self.language, "confidence": 0}
    
    def _transcribe_whisperc(self, audio_data: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio using whisper.cpp bindings.
        
        Args:
            audio_data: Audio data as numpy array
            **kwargs: Additional parameters
            
        Returns:
            Transcription result dictionary
        """
        import whisperc  # C++ bindings for Whisper
        
        # Set up parameters
        params = whisperc.Params()
        params.language = kwargs.get("language", self.language)
        params.translate = kwargs.get("translate", False)
        params.beam_size = kwargs.get("beam_size", self.beam_size)
        params.best_of = kwargs.get("best_of", self.beam_size)
        
        # Run inference
        result = self.model.transcribe(audio_data, params)
        
        # Convert result to dictionary
        segments = []
        for i in range(result.num_segments()):
            segment = result.segment(i)
            segments.append({
                "id": i,
                "text": segment.text,
                "start": segment.start,
                "end": segment.end,
                "confidence": segment.confidence
            })
            
        # Calculate overall confidence as average of segment confidences
        confidence = sum(seg["confidence"] for seg in segments) / len(segments) if segments else 0
            
        return {
            "text": " ".join(seg["text"] for seg in segments),
            "segments": segments,
            "language": result.language(),
            "confidence": confidence
        }
    
    def _transcribe_whisper_python(self, audio_data: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper Python implementation.
        
        Args:
            audio_data: Audio data as numpy array
            **kwargs: Additional parameters
            
        Returns:
            Transcription result dictionary
        """
        # Options for transcription
        options = {
            "language": kwargs.get("language", self.language),
            "beam_size": kwargs.get("beam_size", self.beam_size),
            "best_of": kwargs.get("best_of", self.beam_size),
            "temperature": kwargs.get("temperature", 0),
            "fp16": self.compute_type == "float16",
            "task": "transcribe"
        }
        
        # Run transcription
        result = self.model.transcribe(audio_data, **options)
        
        # Format result for consistency with C++ adapter
        segments = []
        for i, seg in enumerate(result["segments"]):
            # Add default confidence if not provided by the model
            confidence = seg.get("confidence", 0.8) 
            segments.append({
                "id": i,
                "text": seg["text"],
                "start": seg["start"],
                "end": seg["end"],
                "confidence": confidence
            })
            
        # Calculate overall confidence
        avg_confidence = sum(seg["confidence"] for seg in segments) / len(segments) if segments else 0
            
        return {
            "text": result["text"],
            "segments": segments,
            "language": result["language"],
            "confidence": avg_confidence
        }
    
    def transcribe_with_timestamps(self, audio_data: np.ndarray, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio and include word-level timestamps.
        
        Args:
            audio_data: Numpy array of audio samples
            **kwargs: Additional parameters for transcription
            
        Returns:
            Dict with detailed transcription results including timestamps
        """
        # For now, this is a placeholder that returns the same as regular transcribe
        # Word-level timestamps will be implemented in a future update
        result = self.transcribe(audio_data, **kwargs)
        
        # Add empty word timestamps for now
        for segment in result["segments"]:
            segment["words"] = []
            
        logger.warning("Word-level timestamps not fully implemented yet")
        return result
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        if not self.is_loaded():
            return {
                "loaded": False,
                "model_size": self.model_size,
                "device": self.device_name,
                "compute_type": self.compute_type
            }
            
        return {
            "loaded": True,
            **self.stats["model_info"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance statistics
        """
        stats = self.stats.copy()
        
        # Calculate real-time factor if there are transcriptions
        if stats["total_transcription_time"] > 0 and stats["total_audio_seconds"] > 0:
            stats["real_time_factor"] = stats["total_audio_seconds"] / stats["total_transcription_time"]
        else:
            stats["real_time_factor"] = 0
            
        return stats
    
    def __del__(self):
        """
        Clean up resources when object is deleted.
        """
        self.unload_model()