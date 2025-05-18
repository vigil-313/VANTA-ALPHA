# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

import numpy as np
import soundfile as sf
from typing import Tuple, List, Dict, Optional

def load_audio_file(file_path: str) -> Tuple[np.ndarray, int]:
    """
    Load an audio file.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    audio_data, sample_rate = sf.read(file_path)
    return audio_data, sample_rate

def detect_speech_segments(audio_data: np.ndarray, 
                          sample_rate: int, 
                          threshold: float = 0.01,
                          min_duration: float = 0.1) -> List[Tuple[float, float]]:
    """
    Detect speech segments in audio based on energy threshold.
    
    Args:
        audio_data: Audio data as numpy array
        sample_rate: Sample rate in Hz
        threshold: Energy threshold (0-1 range)
        min_duration: Minimum duration of a segment in seconds
        
    Returns:
        List of (start_time, end_time) tuples in seconds
    """
    # Convert to mono if needed
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Calculate energy
    energy = np.abs(audio_data)
    
    # Find segments above threshold
    is_speech = energy > threshold
    
    # Find segment boundaries
    changes = np.diff(is_speech.astype(int))
    segment_starts = np.where(changes == 1)[0]
    segment_ends = np.where(changes == -1)[0]
    
    # Handle edge cases
    if len(segment_starts) == 0:
        return []
    
    if is_speech[0]:
        segment_starts = np.insert(segment_starts, 0, 0)
    
    if is_speech[-1]:
        segment_ends = np.append(segment_ends, len(audio_data) - 1)
    
    # Convert to seconds and filter by minimum duration
    min_samples = int(min_duration * sample_rate)
    segments = []
    
    for start, end in zip(segment_starts, segment_ends):
        if end - start >= min_samples:
            start_time = start / sample_rate
            end_time = end / sample_rate
            segments.append((start_time, end_time))
    
    return segments

def extract_audio_features(audio_data: np.ndarray, sample_rate: int) -> Dict[str, np.ndarray]:
    """
    Extract common audio features for testing.
    
    Args:
        audio_data: Audio data as numpy array
        sample_rate: Sample rate in Hz
        
    Returns:
        Dictionary of audio features
    """
    # Convert to mono if needed
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Calculate spectral features
    try:
        # Note: In actual implementation, we'd use librosa here
        # For now, just calculate basic features to avoid dependencies
        
        # Calculate zero crossing rate (simple approximation)
        zero_crossings = np.sum(np.abs(np.diff(np.signbit(audio_data))))
        zero_crossing_rate = np.array([[zero_crossings / len(audio_data)]])
        
        # Calculate simple spectral centroid approximation
        # (In a real implementation, we'd use librosa.feature.spectral_centroid)
        spectral_centroid = np.array([[np.mean(np.abs(audio_data))]])
        
        # Return simple features
        return {
            "zero_crossing_rate": zero_crossing_rate,
            "spectral_centroid": spectral_centroid
        }
    except Exception as e:
        print(f"Error extracting audio features: {e}")
        return {}

def compare_audio_features(features1: Dict[str, np.ndarray], 
                          features2: Dict[str, np.ndarray],
                          tolerance: float = 0.1) -> bool:
    """
    Compare two sets of audio features for similarity testing.
    
    Args:
        features1: First set of audio features
        features2: Second set of audio features
        tolerance: Similarity tolerance
        
    Returns:
        True if features are similar, False otherwise
    """
    if not features1 or not features2:
        return False
    
    # Check that both have the same features
    if set(features1.keys()) != set(features2.keys()):
        return False
    
    # Compare each feature
    for feature_name in features1:
        feat1 = features1[feature_name]
        feat2 = features2[feature_name]
        
        # Ensure same shape by truncating to smaller size
        min_shape = (min(feat1.shape[0], feat2.shape[0]), min(feat1.shape[1], feat2.shape[1]))
        feat1 = feat1[:min_shape[0], :min_shape[1]]
        feat2 = feat2[:min_shape[0], :min_shape[1]]
        
        # Calculate mean squared error
        mse = np.mean((feat1 - feat2) ** 2)
        
        # Compare with tolerance
        if mse > tolerance:
            return False
    
    return True