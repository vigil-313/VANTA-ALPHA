#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Silero Voice Activity Detection (VAD) model implementation for VANTA.

This module provides a lightweight ML-based voice activity detector using the Silero VAD model.
The implementation is optimized for Apple Silicon (M4) hardware and supports both PyTorch and
ONNX runtime for inference.
"""
# TASK-REF: VOICE_002 - Voice Activity Detection
# CONCEPT-REF: CON-VOICE-012 - Silero VAD Model
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-004 - Support multiple activation modes

import os
import logging
import threading
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import torch
import requests
import time

logger = logging.getLogger(__name__)

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("ONNX Runtime not available. Using PyTorch for SileroVAD.")
except Exception as e:
    ONNX_AVAILABLE = False
    logger.warning(f"Error initializing ONNX Runtime: {e}. Using PyTorch for SileroVAD.")

class SileroVAD:
    """
    Silero VAD model integration for VANTA.
    
    Provides voice activity detection capabilities using the Silero VAD model,
    with both PyTorch and ONNX runtime inference options.
    """
    
    # Default locations for model files
    DEFAULT_MODEL_DIR = Path(os.path.expanduser("~/.cache/vanta/models/vad"))
    DEFAULT_TORCH_MODEL_PATH = DEFAULT_MODEL_DIR / "silero_vad.pt"
    DEFAULT_ONNX_MODEL_PATH = DEFAULT_MODEL_DIR / "silero_vad.onnx"
    
    # Direct download URLs for Silero VAD models
    ONNX_URL = "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.onnx"
    PT_URL = "https://github.com/snakers4/silero-vad/raw/master/files/silero_vad.pt"
    
    # Backup URLs
    BACKUP_ONNX_URL = "https://huggingface.co/snakers4/silero-vad/resolve/main/silero_vad.onnx"
    BACKUP_PT_URL = "https://huggingface.co/snakers4/silero-vad/resolve/main/silero_vad.pt"

    def __init__(self, 
                 model_path: Optional[str] = None,
                 use_onnx: bool = True,
                 sample_rate: int = 16000,
                 threshold: float = 0.5,
                 window_size_samples: int = 1536,  # 96ms at 16kHz
                 min_speech_duration_ms: int = 250,
                 max_speech_duration_s: int = 30,
                 min_silence_duration_ms: int = 100):
        """
        Initialize Silero VAD model.
        
        Args:
            model_path: Path to pre-downloaded model (or None to use default path)
            use_onnx: Whether to use ONNX runtime for inference (faster)
            sample_rate: Audio sample rate in Hz
            threshold: VAD threshold (0.0-1.0), higher = less sensitive
            window_size_samples: Number of samples to process at once
            min_speech_duration_ms: Minimum speech segment length in ms
            max_speech_duration_s: Maximum speech segment length in seconds
            min_silence_duration_ms: Minimum silence for segmentation in ms
        """
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.use_onnx = use_onnx and ONNX_AVAILABLE
        
        # Calculate window size in samples
        self.window_size_samples = window_size_samples
        
        # Time parameters
        self.min_speech_samples = int(min_speech_duration_ms * (sample_rate / 1000))
        self.max_speech_samples = int(max_speech_duration_s * sample_rate)
        self.min_silence_samples = int(min_silence_duration_ms * (sample_rate / 1000))
        
        # Threading lock for inference
        self._lock = threading.RLock()
        
        # State variables
        self.reset_states()
        
        # Determine model path
        if model_path is None:
            if self.use_onnx:
                self.model_path = self.DEFAULT_ONNX_MODEL_PATH
            else:
                self.model_path = self.DEFAULT_TORCH_MODEL_PATH
        else:
            self.model_path = Path(model_path)
        
        # Load the model
        self._load_model()
    
    def _download_model(self) -> None:
        """
        Download the Silero VAD model from direct URLs.
        
        This method uses direct URLs instead of PyTorch Hub to avoid additional dependencies.
        """
        # Create model directory if it doesn't exist
        os.makedirs(self.model_path.parent, exist_ok=True)
        
        # Determine URL based on model format
        if self.use_onnx:
            primary_url = self.ONNX_URL
            backup_url = self.BACKUP_ONNX_URL
        else:
            primary_url = self.PT_URL
            backup_url = self.BACKUP_PT_URL
        
        urls_to_try = [primary_url, backup_url]
        logger.info(f"Attempting to download Silero VAD model from {primary_url}")
        
        success = False
        last_error = None
        
        # Try each URL with retry logic
        for url in urls_to_try:
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    self._download_file(url, self.model_path)
                    success = True
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(f"Download attempt {attempt+1} from {url} failed: {e}")
                    time.sleep(1)  # Brief pause before retry
            
            if success:
                logger.info(f"Successfully downloaded Silero VAD model to {self.model_path}")
                break
        
        if not success:
            error_msg = f"Failed to download Silero VAD model from all URLs: {last_error}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _download_file(self, url: str, path: Path) -> None:
        """
        Download a file from URL to the specified path.
        
        Args:
            url: URL to download from
            path: Path to save the file to
        """
        logger.info(f"Downloading file from {url} to {path}")
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Successfully downloaded file to {path}")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise
    
    def _load_model(self) -> None:
        """
        Load the Silero VAD model into memory.
        
        Uses either ONNX runtime or PyTorch based on configuration.
        Downloads the model if not available locally.
        """
        # Check if model exists, download if not
        if not os.path.exists(self.model_path):
            self._download_model()
        
        try:
            if self.use_onnx:
                self._load_onnx_model()
            else:
                self._load_torch_model()
                
            logger.info(f"Loaded Silero VAD model from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading Silero VAD model: {e}")
            raise
    
    def _load_onnx_model(self) -> None:
        """
        Load the ONNX version of the Silero VAD model.
        
        Sets up ONNX runtime inference session with optimizations for the current hardware.
        Downloads the model if it's not found on disk.
        """
        # Check if model exists, download if not
        if not os.path.exists(self.model_path):
            logger.info(f"ONNX model not found at {self.model_path}, downloading")
            self._download_model()
        
        # Set up ONNX Runtime session options
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Check if we're on Apple Silicon
        if hasattr(ort, 'CoreMLExecutionProvider') and torch.backends.mps.is_available():
            # Use CoreML for Apple Silicon
            self.ort_session = ort.InferenceSession(
                str(self.model_path),
                providers=['CoreMLExecutionProvider', 'CPUExecutionProvider'],
                sess_options=session_options
            )
            logger.info("Using CoreML acceleration for Silero VAD")
        else:
            # Fall back to CPU
            self.ort_session = ort.InferenceSession(
                str(self.model_path), 
                providers=['CPUExecutionProvider'],
                sess_options=session_options
            )
            logger.info("Using CPU for Silero VAD inference")
        
        # Get model inputs and outputs
        self.model_inputs = [input.name for input in self.ort_session.get_inputs()]
        
        # Initialize model states (h and c)
        self.reset_states()
    
    def _load_torch_model(self) -> None:
        """
        Load the PyTorch version of the Silero VAD model.
        
        Optimizes model for inference and moves to appropriate device (MPS/CPU).
        Downloads the model if it's not found on disk.
        """
        try:
            # Check if the model exists, download if not
            if not os.path.exists(self.model_path):
                self._download_model()
            
            # Load the model
            logger.info(f"Loading PyTorch model from disk: {self.model_path}")
            model_data = torch.load(self.model_path, map_location=torch.device('cpu'))
            
            # Extract model from the dict
            if isinstance(model_data, dict) and 'model' in model_data:
                self.model = model_data['model']
            else:
                self.model = model_data
            
            # Set model to eval mode
            self.model.eval()
            
            # Check if MPS (Metal Performance Shaders) is available for Apple Silicon
            if torch.backends.mps.is_available():
                self.device = torch.device("mps")
                self.model = self.model.to(self.device)
                logger.info("Using MPS (Metal) acceleration for Silero VAD")
            else:
                self.device = torch.device("cpu")
                logger.info("Using CPU for Silero VAD inference")
        except Exception as e:
            logger.error(f"Error loading PyTorch model: {e}")
            raise
        
        # Initialize model states (h and c)
        self.reset_states()
    
    def reset_states(self) -> None:
        """
        Reset detector state for a new processing session.
        
        Resets internal LSTM states and speech detection state.
        """
        with self._lock:
            if self.use_onnx:
                # For ONNX, we need to track h and c as numpy arrays
                h_shape = (2, 1, 64)  # lstm_layers, batch_size, hidden_size
                self.h = np.zeros(h_shape, dtype=np.float32)
                self.c = np.zeros(h_shape, dtype=np.float32)
            else:
                # For PyTorch, we need to track h and c as tensors
                if hasattr(self, 'model'):
                    self.h = torch.zeros(2, 1, 64)
                    self.c = torch.zeros(2, 1, 64)
                    
                    if hasattr(self, 'device'):
                        self.h = self.h.to(self.device)
                        self.c = self.c.to(self.device)
            
            # Reset speech detection state
            self.triggered = False
            self.speech_start = 0
            self.speech_end = 0
            self.temp_end = 0
            self.current_sample = 0
    
    def is_speech(self, audio_chunk: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if audio chunk contains speech.
        
        Args:
            audio_chunk: Numpy array of audio samples (mono, 16kHz)
            
        Returns:
            Tuple of (is_speech, confidence)
        """
        with self._lock:
            # Ensure audio is the right shape
            if len(audio_chunk.shape) > 1:
                # Convert stereo to mono if needed
                audio_chunk = audio_chunk.mean(axis=1)
            
            # Process in window_size_samples chunks
            confidences = []
            
            for i in range(0, len(audio_chunk), self.window_size_samples):
                chunk = audio_chunk[i:i + self.window_size_samples]
                
                # If chunk is smaller than window size, pad with zeros
                if len(chunk) < self.window_size_samples:
                    chunk = np.pad(chunk, (0, self.window_size_samples - len(chunk)))
                
                if self.use_onnx:
                    confidence = self._inference_onnx(chunk)
                else:
                    confidence = self._inference_torch(chunk)
                
                confidences.append(confidence)
                
                # Update current sample position
                self.current_sample += len(chunk)
            
            # If we have multiple windows, average confidence
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
            else:
                avg_confidence = 0.0
            
            # Determine if this is speech
            is_speech = avg_confidence >= self.threshold
            
            return is_speech, avg_confidence
    
    def _inference_onnx(self, audio_chunk: np.ndarray) -> float:
        """
        Run inference using ONNX runtime.
        
        Args:
            audio_chunk: Numpy array of audio samples
            
        Returns:
            Speech confidence score (0.0-1.0)
        """
        # Prepare inputs
        audio_chunk = audio_chunk.astype(np.float32)
        sr = np.array(self.sample_rate, dtype=np.int64)
        
        # Run inference
        ort_inputs = {
            'input': audio_chunk.reshape(1, -1),
            'sr': sr,
            'h': self.h,
            'c': self.c
        }
        
        ort_outs = self.ort_session.run(None, ort_inputs)
        out, self.h, self.c = ort_outs
        
        return float(out[0][0])
    
    def _inference_torch(self, audio_chunk: np.ndarray) -> float:
        """
        Run inference using PyTorch.
        
        Args:
            audio_chunk: Numpy array of audio samples
            
        Returns:
            Speech confidence score (0.0-1.0)
        """
        # Convert numpy array to tensor
        audio_tensor = torch.from_numpy(audio_chunk).float()
        if len(audio_tensor.shape) == 1:
            audio_tensor = audio_tensor.unsqueeze(0)
        
        # Move tensor to the right device
        audio_tensor = audio_tensor.to(self.device)
        
        # Run inference
        with torch.no_grad():
            out, (self.h, self.c) = self.model(audio_tensor, self.h, self.c)
        
        return out.item()
    
    def get_speech_timestamps(self, audio: np.ndarray, return_seconds: bool = False) -> List[Dict[str, Union[int, float]]]:
        """
        Get timestamps of speech segments in audio.
        
        Args:
            audio: Numpy array of audio samples (mono, 16kHz)
            return_seconds: If True, return timestamps in seconds, otherwise in samples
            
        Returns:
            List of dicts with speech segment timestamps:
            [
                {
                    "start": start_time,
                    "end": end_time,
                    "duration": duration,
                    "confidence": average_confidence
                },
                ...
            ]
        """
        with self._lock:
            # Reset state for new detection
            self.reset_states()
            
            # Initialize variables
            speech_timestamps = []
            
            # Track confidence scores for each segment
            segment_confidences = []
            
            # Process audio in chunks
            for i in range(0, len(audio), self.window_size_samples):
                chunk = audio[i:i + self.window_size_samples]
                
                # If chunk is smaller than window size, pad with zeros
                if len(chunk) < self.window_size_samples:
                    chunk = np.pad(chunk, (0, self.window_size_samples - len(chunk)))
                
                # Get confidence for this chunk
                if self.use_onnx:
                    confidence = self._inference_onnx(chunk)
                else:
                    confidence = self._inference_torch(chunk)
                
                # Update speech detection state machine
                if confidence >= self.threshold:
                    segment_confidences.append(confidence)
                    
                    if not self.triggered:
                        self.triggered = True
                        self.speech_start = self.current_sample
                    
                    self.temp_end = self.current_sample + len(chunk)
                else:
                    if self.triggered:
                        # If silence is longer than min_silence_samples, end speech segment
                        if (self.current_sample - self.temp_end) >= self.min_silence_samples:
                            self.speech_end = self.temp_end
                            
                            # Filter out speech segments that are too short
                            speech_duration = self.speech_end - self.speech_start
                            if speech_duration >= self.min_speech_samples:
                                # Calculate average confidence for this segment
                                avg_confidence = sum(segment_confidences) / len(segment_confidences) if segment_confidences else 0
                                
                                # If return_seconds is True, convert to seconds
                                if return_seconds:
                                    start_time = self.speech_start / self.sample_rate
                                    end_time = self.speech_end / self.sample_rate
                                    duration = speech_duration / self.sample_rate
                                else:
                                    start_time = self.speech_start
                                    end_time = self.speech_end
                                    duration = speech_duration
                                
                                # Add speech segment to results
                                speech_timestamps.append({
                                    "start": start_time,
                                    "end": end_time,
                                    "duration": duration,
                                    "confidence": avg_confidence
                                })
                            
                            # Reset for next speech segment
                            self.triggered = False
                            segment_confidences = []
                
                # Update current sample position
                self.current_sample += len(chunk)
                
                # If we're in a speech segment that's too long, force end it
                if self.triggered and (self.current_sample - self.speech_start) >= self.max_speech_samples:
                    self.speech_end = self.current_sample
                    
                    # Calculate average confidence for this segment
                    avg_confidence = sum(segment_confidences) / len(segment_confidences) if segment_confidences else 0
                    
                    # If return_seconds is True, convert to seconds
                    if return_seconds:
                        start_time = self.speech_start / self.sample_rate
                        end_time = self.speech_end / self.sample_rate
                        duration = (self.speech_end - self.speech_start) / self.sample_rate
                    else:
                        start_time = self.speech_start
                        end_time = self.speech_end
                        duration = self.speech_end - self.speech_start
                    
                    # Add speech segment to results
                    speech_timestamps.append({
                        "start": start_time,
                        "end": end_time,
                        "duration": duration,
                        "confidence": avg_confidence
                    })
                    
                    # Reset for next speech segment
                    self.triggered = False
                    segment_confidences = []
            
            # Handle speech at the end of audio
            if self.triggered:
                self.speech_end = self.current_sample
                
                # Filter out speech segments that are too short
                speech_duration = self.speech_end - self.speech_start
                if speech_duration >= self.min_speech_samples:
                    # Calculate average confidence for this segment
                    avg_confidence = sum(segment_confidences) / len(segment_confidences) if segment_confidences else 0
                    
                    # If return_seconds is True, convert to seconds
                    if return_seconds:
                        start_time = self.speech_start / self.sample_rate
                        end_time = self.speech_end / self.sample_rate
                        duration = speech_duration / self.sample_rate
                    else:
                        start_time = self.speech_start
                        end_time = self.speech_end
                        duration = speech_duration
                    
                    # Add speech segment to results
                    speech_timestamps.append({
                        "start": start_time,
                        "end": end_time,
                        "duration": duration,
                        "confidence": avg_confidence
                    })
            
            return speech_timestamps
    
    def adapt_to_noise(self, background_audio: np.ndarray) -> None:
        """
        Adapt detection thresholds based on background noise.
        
        This is a simple implementation that adjusts the threshold based on
        false positive analysis of the background noise.
        
        Args:
            background_audio: Numpy array of background noise samples
        """
        # Process the background audio to see if any parts are detected as speech
        timestamps = self.get_speech_timestamps(background_audio)
        
        # If we detect any speech in background noise, adjust the threshold
        if timestamps:
            # Calculate the maximum confidence in the background audio
            max_confidence = max([segment["confidence"] for segment in timestamps])
            
            # Set new threshold to be slightly higher than the max confidence in noise
            new_threshold = min(max_confidence + 0.1, 0.9)
            
            # Only increase threshold, never decrease
            if new_threshold > self.threshold:
                logger.info(f"Adapting VAD threshold from {self.threshold} to {new_threshold} based on background noise")
                self.threshold = new_threshold
    
    def set_threshold(self, threshold: float) -> None:
        """
        Dynamically adjust detection threshold.
        
        Args:
            threshold: New detection threshold (0.0-1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")
        
        logger.info(f"Changing VAD threshold from {self.threshold} to {threshold}")
        self.threshold = threshold
    
    def _convert_to_onnx(self) -> None:
        """
        Convert PyTorch model to ONNX for faster inference.
        
        Exports the loaded PyTorch model to ONNX format.
        """
        # Must have PyTorch model loaded first
        if not hasattr(self, 'model'):
            self._load_torch_model()
        
        # Ensure target directory exists
        os.makedirs(self.DEFAULT_ONNX_MODEL_PATH.parent, exist_ok=True)
        
        logger.info(f"Converting PyTorch model to ONNX format at {self.DEFAULT_ONNX_MODEL_PATH}")
        
        try:
            # Create dummy input for tracing
            dummy_input = torch.zeros(1, self.window_size_samples).to(self.device)
            dummy_h = torch.zeros(2, 1, 64).to(self.device)
            dummy_c = torch.zeros(2, 1, 64).to(self.device)
            
            # Export to ONNX
            torch.onnx.export(
                self.model,
                (dummy_input, dummy_h, dummy_c),
                str(self.DEFAULT_ONNX_MODEL_PATH),
                verbose=False,
                opset_version=11,
                do_constant_folding=True,
                input_names=['input', 'h', 'c', 'sr'],
                output_names=['output', 'hn', 'cn'],
                dynamic_axes={
                    'input': {1: 'time'},
                }
            )
            
            logger.info(f"Successfully converted model to ONNX format at {self.DEFAULT_ONNX_MODEL_PATH}")
            
            # Switch to using the ONNX model if ONNX is available
            if ONNX_AVAILABLE:
                self.use_onnx = True
                self.model_path = self.DEFAULT_ONNX_MODEL_PATH
                self._load_model()
        except Exception as e:
            logger.error(f"Error converting to ONNX: {e}")
            raise