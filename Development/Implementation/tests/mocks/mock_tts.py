# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

import numpy as np
from typing import Dict, Any, Optional

class MockTTS:
    """Mock text-to-speech system for testing."""
    
    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self.last_text = ""
    
    def synthesize(self, text: str, voice: str = "default") -> np.ndarray:
        """
        Mock synthesize text to speech.
        
        Args:
            text: Text to synthesize
            voice: Voice to use
            
        Returns:
            Audio data as numpy array
        """
        self.last_text = text
        
        # Create simple signal proportional to text length
        duration = len(text) * 0.1  # 100ms per character
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # Generate sine wave with frequency related to voice
        if voice == "high":
            freq = 880.0
        elif voice == "low":
            freq = 220.0
        else:
            freq = 440.0
            
        audio_data = np.sin(2 * np.pi * freq * t)
        
        # Add some noise to make it more realistic
        noise = np.random.normal(0, 0.01, len(audio_data))
        audio_data = audio_data + noise
        
        # Normalize
        audio_data = audio_data / np.max(np.abs(audio_data))
        
        return audio_data