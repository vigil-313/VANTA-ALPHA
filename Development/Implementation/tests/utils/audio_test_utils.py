# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

import numpy as np
import soundfile as sf
from typing import Tuple, List, Dict, Optional, Any
import hashlib

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

def generate_spoken_text_audio(text: str, duration: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """
    Generate a synthetic audio that simulates spoken text.
    
    Args:
        text: Text to simulate
        duration: Duration of the audio in seconds
        sample_rate: Sample rate in Hz
        
    Returns:
        Audio data as numpy array
    """
    # Generate a unique frequency based on the text (deterministic result for same text)
    text_hash = int(hashlib.md5(text.encode()).hexdigest(), 16)
    base_freq = 300 + (text_hash % 200)  # Range 300-500 Hz
    
    # Generate time array
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate base sine wave
    audio_data = np.sin(2 * np.pi * base_freq * t)
    
    # Add some amplitude modulation to simulate syllables
    # Number of syllables roughly proportional to text length
    syllables = max(1, len(text) // 3)
    syllable_rate = syllables / duration
    
    # Modulate amplitude
    modulation = 0.5 + 0.5 * np.sin(2 * np.pi * syllable_rate * t)
    audio_data = audio_data * modulation
    
    # Add some noise
    noise = np.random.normal(0, 0.05, audio_data.shape)
    audio_data = audio_data + noise
    
    # Normalize to [-1, 1]
    audio_data = audio_data / np.max(np.abs(audio_data))
    
    return audio_data

def create_test_transcription_data(
    text: str, 
    num_segments: int = 1,
    confidence: float = 0.8,
    duration: float = 1.0,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Create mock transcription data for testing.
    
    Args:
        text: Transcription text
        num_segments: Number of segments to create
        confidence: Confidence score (0-1)
        duration: Total audio duration in seconds
        language: Language code
        
    Returns:
        Mock transcription data dictionary
    """
    # Create segments
    segments = []
    segment_duration = duration / num_segments
    
    for i in range(num_segments):
        # For multi-segment transcriptions, divide the text approximately equally
        if num_segments > 1:
            words = text.split()
            words_per_segment = max(1, len(words) // num_segments)
            segment_words = words[i * words_per_segment : min(len(words), (i + 1) * words_per_segment)]
            segment_text = " ".join(segment_words)
        else:
            segment_text = text
            
        segment = {
            "id": i,
            "text": segment_text,
            "start": i * segment_duration,
            "end": (i + 1) * segment_duration,
            "confidence": confidence
        }
        segments.append(segment)
    
    # Create full result
    result = {
        "text": text,
        "segments": segments,
        "language": language,
        "confidence": confidence
    }
    
    return result

def add_hesitations_to_text(text: str, hesitation_probability: float = 0.3) -> str:
    """
    Add hesitation words to text for testing hesitation filtering.
    
    Args:
        text: Original text
        hesitation_probability: Probability of adding hesitation before each word
        
    Returns:
        Text with hesitations
    """
    hesitations = ["um", "uh", "eh", "er", "ah", "mm", "hmm"]
    words = text.split()
    result = []
    
    for word in words:
        if np.random.random() < hesitation_probability:
            hesitation = np.random.choice(hesitations)
            result.append(hesitation)
        result.append(word)
        
    return " ".join(result)