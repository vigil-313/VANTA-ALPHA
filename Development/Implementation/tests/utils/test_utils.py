# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Tuple, Optional

def create_test_audio(duration: float = 1.0, 
                    sample_rate: int = 16000, 
                    frequency: float = 440.0,
                    samples: Optional[int] = None,
                    freq: Optional[float] = None,
                    duration_ms: Optional[int] = None) -> Tuple[np.ndarray, int]:
    """
    Create a test audio signal with a sine wave.
    
    Args:
        duration: Duration of the audio in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of the sine wave in Hz
        samples: Alternative way to specify sample_rate (for backwards compatibility)
        freq: Alternative way to specify frequency (for backwards compatibility)
        duration_ms: Alternative way to specify duration in milliseconds (for backwards compatibility)
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    # Handle alternative parameter names for backward compatibility
    if samples is not None:
        sample_rate = samples
    if freq is not None:
        frequency = freq
    if duration_ms is not None:
        duration = duration_ms / 1000.0
        
    # Generate time array
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate sine wave
    audio_data = np.sin(2 * np.pi * frequency * t)
    
    # Normalize to [-1, 1]
    audio_data = audio_data / np.max(np.abs(audio_data))
    
    return audio_data, sample_rate

def save_test_audio(audio_data, 
                   sample_rate: Optional[int] = None, 
                   path: Optional[str] = None) -> str:
    """
    Save test audio to a temporary file or specified path.
    
    Args:
        audio_data: Audio data as numpy array or tuple of (audio_data, sample_rate)
        sample_rate: Sample rate in Hz (only used if audio_data is not a tuple)
        path: Optional path to save the file
        
    Returns:
        Path to the saved audio file
    """
    # Handle case where audio_data is a tuple (audio_data, sample_rate)
    if isinstance(audio_data, tuple) and len(audio_data) == 2:
        audio_array, sr = audio_data
    else:
        audio_array = audio_data
        sr = sample_rate
        
    if sr is None:
        raise ValueError("Sample rate must be provided")
    
    if path is None:
        # Create a temporary file with .wav extension
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name
    
    # Save the audio file
    sf.write(path, audio_array, sr)
    
    return path

def audio_rms(audio_data: np.ndarray) -> float:
    """
    Calculate the root mean square (RMS) of an audio signal.
    
    Args:
        audio_data: Audio data as numpy array
        
    Returns:
        RMS value
    """
    return np.sqrt(np.mean(np.square(audio_data)))

def assert_audio_similar(audio1: np.ndarray, 
                         audio2: np.ndarray, 
                         threshold: float = 0.1) -> bool:
    """
    Assert that two audio signals are similar based on RMS difference.
    
    Args:
        audio1: First audio signal
        audio2: Second audio signal
        threshold: Similarity threshold (lower means more similar)
        
    Returns:
        True if similar, False otherwise
    """
    # Ensure same length by truncating to shorter
    min_length = min(len(audio1), len(audio2))
    audio1 = audio1[:min_length]
    audio2 = audio2[:min_length]
    
    # Calculate RMS difference
    diff = np.abs(audio1 - audio2)
    diff_rms = audio_rms(diff)
    
    # Calculate reference RMS
    rms1 = audio_rms(audio1)
    
    # Calculate relative difference
    relative_diff = diff_rms / (rms1 + 1e-10)  # Avoid division by zero
    
    return relative_diff < threshold