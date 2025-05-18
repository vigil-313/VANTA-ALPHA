# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-IMP-013 - Test Framework
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

import numpy as np
from typing import Tuple, List, Dict, Any, Optional

class MockAudioCapture:
    """Mock audio capture device for testing."""
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.is_active = False
        self.test_audio: Optional[np.ndarray] = None
        self.position = 0
    
    def set_test_audio(self, audio: np.ndarray):
        """Set the test audio data to be returned by read."""
        self.test_audio = audio
        self.position = 0
    
    def start(self):
        """Start audio capture."""
        self.is_active = True
        self.position = 0
        return self
    
    def stop(self):
        """Stop audio capture."""
        self.is_active = False
        return self
    
    def read(self) -> Tuple[bool, np.ndarray]:
        """Read a chunk of audio data."""
        if not self.is_active or self.test_audio is None:
            return False, np.zeros(self.chunk_size, dtype=np.float32)
        
        # Calculate end position for current chunk
        end_pos = min(self.position + self.chunk_size, len(self.test_audio))
        
        # Get chunk from test audio
        chunk = self.test_audio[self.position:end_pos]
        
        # Pad if needed
        if len(chunk) < self.chunk_size:
            chunk = np.pad(chunk, (0, self.chunk_size - len(chunk)))
        
        # Update position
        self.position = end_pos
        
        # Return chunk
        return True, chunk