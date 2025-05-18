# Voice Pipeline Implementation - Voice Activity Detection [VOICE_002]

## Task Overview

This prompt guides the implementation of the Voice Activity Detection (VAD) component for VANTA's Voice Pipeline. The VAD system is responsible for detecting when a user is speaking, determining the beginning and end of utterances, and activating the system based on different modes (wake word, continuous listening, etc.).

## Implementation Context

Voice Activity Detection is a critical component that serves as the gateway for speech processing. It filters out background noise and non-speech audio, ensuring that only relevant speech is passed to the more computationally intensive speech recognition system. It also manages different activation modes to control when VANTA should listen actively.

### Related Documentation
- `/Development/Architecture/COMPONENT_SPECIFICATIONS/VOICE_PIPELINE.md`: Complete component specification
- `/Development/Architecture/V0_ARCHITECTURE_OVERVIEW.md`: System architecture overview
- `/Development/Architecture/DATA_MODELS.md`: Data structure definitions
- `/Development/Prompts/Phase1_Core/VoicePipeline/VOICE_001_Audio_Processing_Infrastructure.md`: Audio infrastructure implementation

### Dependencies
- TASK-VP-001: Audio Processing Infrastructure
- Audio capture and preprocessing modules must be implemented first

## Implementation Requirements

### 1. Voice Activity Detector Module (detector.py)

Implement a VAD module with the following features:

- Fast, lightweight voice activity detection using ML models optimized for M4 hardware
- Support for multiple VAD models (Silero VAD, Whisper VAD)
- Configurable sensitivity and thresholds
- Frame-level and utterance-level detection
- Confidence scores for detections
- Background noise adaptation

Example interface:

```python
class VoiceActivityDetector:
    def __init__(self, 
                 model_type="silero",  # or "whisper_vad" 
                 sample_rate=16000,
                 threshold=0.5,
                 window_size_ms=96,
                 min_speech_duration_ms=250,
                 max_speech_duration_s=30,
                 min_silence_duration_ms=100):
        """Initialize voice activity detector.
        
        Args:
            model_type: Type of VAD model to use
            sample_rate: Audio sample rate in Hz
            threshold: Detection threshold (0-1)
            window_size_ms: Analysis window size in milliseconds
            min_speech_duration_ms: Minimum speech segment length
            max_speech_duration_s: Maximum speech segment length
            min_silence_duration_ms: Minimum silence for segmentation
        """
        pass
    
    def detect_speech(self, audio_data):
        """Detect if audio contains speech.
        
        Args:
            audio_data: Numpy array of audio samples
            
        Returns:
            Dict with detection results:
            {
                "is_speech": bool,
                "confidence": float,
                "speech_segments": List of (start_ms, end_ms) tuples
            }
        """
        pass
    
    def reset(self):
        """Reset detector state (e.g., between processing sessions)."""
        pass
    
    def adapt_to_noise(self, background_audio):
        """Adapt detection thresholds based on background noise.
        
        Args:
            background_audio: Numpy array of background noise samples
        """
        pass
    
    def set_threshold(self, threshold):
        """Dynamically adjust detection threshold."""
        pass
```

### 2. Wake Word Detection Module (activation.py)

Implement wake word detection with the following features:

- Default wake word recognition ("Hey Vanta")
- Configurable wake words
- Customizable activation threshold
- Noise-robust detection
- Callback interface for activation events
- Integration with continuous listening mode

Example interface:

```python
class WakeWordDetector:
    def __init__(self,
                 wake_word="hey vanta",
                 threshold=0.7,
                 sample_rate=16000):
        """Initialize wake word detector.
        
        Args:
            wake_word: The wake word or phrase to detect
            threshold: Detection threshold (0-1)
            sample_rate: Audio sample rate in Hz
        """
        pass
    
    def detect(self, audio_data):
        """Detect wake word in audio data.
        
        Args:
            audio_data: Numpy array of audio samples
            
        Returns:
            Dict with detection results:
            {
                "detected": bool,
                "confidence": float,
                "timestamp_ms": int  # Position in audio
            }
        """
        pass
    
    def add_custom_wake_word(self, phrase, samples=None):
        """Add a custom wake word or phrase.
        
        Args:
            phrase: Text of the wake word/phrase
            samples: Optional audio samples of the phrase
        """
        pass
```

### 3. Activation Manager (activation.py)

Implement an activation manager with the following features:

- Multiple activation modes (wake word, continuous, scheduled, manual)
- State management for activation phases
- Timeout handling for inactive periods
- Energy-based pre-filtering
- Event notifications for state changes
- Configuration for different environments

Example interface:

```python
from enum import Enum

class ActivationMode(Enum):
    WAKE_WORD = "wake_word"
    CONTINUOUS = "continuous"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    OFF = "off"

class ActivationState(Enum):
    INACTIVE = "inactive"
    LISTENING = "listening"
    ACTIVE = "active"
    PROCESSING = "processing"

class ActivationManager:
    def __init__(self,
                 mode=ActivationMode.WAKE_WORD,
                 vad=None,
                 wake_word_detector=None,
                 energy_threshold=0.01,
                 timeout_s=30):
        """Initialize activation manager.
        
        Args:
            mode: Initial activation mode
            vad: VoiceActivityDetector instance
            wake_word_detector: WakeWordDetector instance
            energy_threshold: Energy threshold for pre-filtering
            timeout_s: Seconds of inactivity before returning to inactive
        """
        pass
    
    def process_audio(self, audio_data):
        """Process audio and update activation state.
        
        Args:
            audio_data: Numpy array of audio samples
            
        Returns:
            Dict with updated state info:
            {
                "state": ActivationState,
                "is_speech": bool,
                "wake_word_detected": bool,
                "should_process": bool  # Whether STT should process
            }
        """
        pass
    
    def set_mode(self, mode: ActivationMode):
        """Change the activation mode."""
        pass
    
    def reset(self):
        """Reset to inactive state."""
        pass
    
    def add_state_change_listener(self, callback_fn):
        """Add callback for state change events."""
        pass
    
    def extend_timeout(self, seconds=30):
        """Extend the timeout for the current activation."""
        pass
```

### 4. Integration with Audio Pipeline

Integrate the VAD components with the audio pipeline from VOICE_001:

```python
# In pipeline.py
from voice.audio.capture import AudioCapture
from voice.audio.preprocessing import AudioPreprocessor
from voice.audio.playback import AudioPlayback
from voice.audio.config import AudioConfig
from voice.vad.detector import VoiceActivityDetector
from voice.vad.activation import WakeWordDetector, ActivationManager, ActivationState

class VoicePipeline:
    def __init__(self, config_file=None):
        """Initialize the voice pipeline with all components."""
        self.config = AudioConfig(config_file)
        
        # Audio components
        self.capture = AudioCapture(**self.config.get_capture_config())
        self.preprocessor = AudioPreprocessor(**self.config.get_preprocessing_config())
        self.playback = AudioPlayback(**self.config.get_playback_config())
        
        # VAD components
        vad_config = self.config.get_vad_config()
        self.vad = VoiceActivityDetector(**vad_config)
        
        wake_word_config = self.config.get_wake_word_config()
        self.wake_word_detector = WakeWordDetector(**wake_word_config)
        
        # Activation management
        activation_config = self.config.get_activation_config()
        self.activation_manager = ActivationManager(
            vad=self.vad,
            wake_word_detector=self.wake_word_detector,
            **activation_config
        )
        
        # Set up audio processing callback
        self.capture.add_callback(self._process_audio)
        
        # Add activation state change listener
        self.activation_manager.add_state_change_listener(self._on_activation_state_change)
        
    def _process_audio(self, audio_data):
        """Process incoming audio data from capture."""
        # Process the audio
        processed_audio = self.preprocessor.process(audio_data)
        
        # Check activation state
        activation_result = self.activation_manager.process_audio(processed_audio)
        
        # If we should process this audio for speech, continue to STT
        if activation_result["should_process"]:
            # Here we would pass to STT component
            # (to be implemented in future tasks)
            pass
            
    def _on_activation_state_change(self, old_state, new_state):
        """Handle activation state changes."""
        # Log state change
        print(f"Activation state changed: {old_state} -> {new_state}")
        
        # Handle specific state transitions
        if new_state == ActivationState.ACTIVE:
            # For example, play an activation sound
            pass
```

### 5. Configuration Extensions

Extend the audio configuration module to include VAD settings:

```python
# In config.py
class AudioConfig:
    DEFAULT_CONFIG = {
        # Existing audio config
        "capture": { ... },
        "preprocessing": { ... },
        "playback": { ... },
        
        # VAD configuration
        "vad": {
            "model_type": "silero",
            "threshold": 0.5,
            "window_size_ms": 96,
            "min_speech_duration_ms": 250,
            "max_speech_duration_s": 30,
            "min_silence_duration_ms": 100
        },
        
        # Wake word configuration
        "wake_word": {
            "enabled": True,
            "phrase": "hey vanta",
            "threshold": 0.7
        },
        
        # Activation configuration
        "activation": {
            "mode": "wake_word",  # wake_word, continuous, scheduled, manual, off
            "energy_threshold": 0.01,
            "timeout_s": 30
        }
    }
    
    # Add these methods to the existing AudioConfig class
    def get_vad_config(self):
        """Get VAD-specific configuration."""
        return self.config.get("vad", {})
    
    def get_wake_word_config(self):
        """Get wake word detection configuration."""
        return self.config.get("wake_word", {})
    
    def get_activation_config(self):
        """Get activation management configuration."""
        return self.config.get("activation", {})
```

## Model Integration

### 1. Silero VAD Model

Implement Silero VAD integration with the following features:

- Download and initialize the Silero VAD model
- Optimize for Apple Silicon (M4) hardware
- Convert the model to ONNX format for faster inference
- Implement streaming detection for real-time processing
- Ensure proper resource management

Example implementation:

```python
class SileroVAD:
    def __init__(self, 
                 model_path=None,
                 use_onnx=True,
                 sample_rate=16000):
        """Initialize Silero VAD model.
        
        Args:
            model_path: Path to pre-downloaded model (or None to download)
            use_onnx: Whether to use ONNX runtime for inference
            sample_rate: Audio sample rate
        """
        pass
    
    def _download_model(self):
        """Download the Silero VAD model if not available."""
        pass
    
    def _load_model(self):
        """Load the model into memory."""
        pass
    
    def _convert_to_onnx(self):
        """Convert PyTorch model to ONNX for faster inference."""
        pass
    
    def is_speech(self, audio_chunk):
        """Detect if audio chunk contains speech."""
        pass
    
    def get_speech_timestamps(self, audio, threshold=0.5):
        """Get timestamps of speech segments in audio."""
        pass
    
    def reset_states(self):
        """Reset model states between processing sessions."""
        pass
```

### 2. Whisper-based VAD Model

As an alternative to Silero, implement a Whisper-based VAD:

- Use Whisper model for combined VAD and wake-word detection
- Leverage model from the model registry
- Implement efficient inference for short audio segments
- Provide confidence scores for detection

Example implementation:

```python
class WhisperVAD:
    def __init__(self,
                 model_size="tiny",  # tiny, base, small
                 sample_rate=16000):
        """Initialize Whisper-based VAD.
        
        Args:
            model_size: Size of Whisper model to use
            sample_rate: Audio sample rate
        """
        pass
    
    def _load_model(self):
        """Load Whisper model from model registry."""
        pass
    
    def is_speech(self, audio_chunk):
        """Detect if audio chunk contains speech."""
        pass
    
    def transcribe_with_timestamps(self, audio):
        """Transcribe audio and get word timestamps."""
        pass
    
    def detect_wake_word(self, audio, wake_word="hey vanta"):
        """Detect if audio contains wake word."""
        pass
```

## Testing Requirements

Implement comprehensive unit tests for each module:

- Test VAD with sample audio containing speech and non-speech
- Test wake word detection with various pronunciations
- Test activation state transitions
- Test integration with audio pipeline
- Test performance and resource usage

Example test scenarios:

```python
# Test VAD accuracy
def test_vad_accuracy():
    vad = VoiceActivityDetector()
    
    # Test with speech audio file
    speech_audio = load_test_audio("speech_sample.wav")
    result = vad.detect_speech(speech_audio)
    assert result["is_speech"] == True
    assert result["confidence"] > 0.8
    
    # Test with non-speech audio file
    noise_audio = load_test_audio("background_noise.wav")
    result = vad.detect_speech(noise_audio)
    assert result["is_speech"] == False
    assert result["confidence"] < 0.3

# Test wake word detection
def test_wake_word_detection():
    detector = WakeWordDetector()
    
    # Test with wake word audio
    wake_audio = load_test_audio("hey_vanta.wav")
    result = detector.detect(wake_audio)
    assert result["detected"] == True
    assert result["confidence"] > 0.7
    
    # Test with similar but incorrect phrase
    similar_audio = load_test_audio("hey_santa.wav")
    result = detector.detect(similar_audio)
    assert result["detected"] == False
```

## Technical Considerations

### Performance

- Optimize for low-latency detection (<100ms)
- Use efficient ML model inference techniques
- Pre-filter audio based on energy levels
- Implement batched processing where appropriate
- Monitor CPU and memory usage during detection

### Error Handling

- Handle model loading failures with fallback options
- Implement retry logic for transient errors
- Log detection results for debugging
- Ensure proper resource cleanup

### Energy Efficiency

- Scale processing based on activation state
- Release resources when inactive
- Use energy-based pre-filtering to avoid unnecessary computation
- Implement power-aware activation modes

## Validation Criteria

The implementation will be considered successful when:

1. Voice activity detection correctly identifies speech vs. non-speech
   - >95% accuracy on clear speech detection
   - <10% false positive rate on background noise
   - <100ms detection latency

2. Wake word detection functions correctly
   - >90% accuracy for the default wake word
   - <5% false activation rate
   - Works with different speakers and accents

3. Activation management works as expected
   - Correctly transitions between states
   - Timeout functionality works properly
   - Different activation modes function as expected

4. Integration with audio pipeline is seamless
   - Activation events properly trigger speech processing
   - Resources are managed correctly
   - State handling works properly

5. All tests pass
   - Unit tests for VAD components
   - Integration tests with audio pipeline
   - Performance tests meet latency targets

## Resources and References

- Silero VAD: https://github.com/snakers4/silero-vad
- PyTorch to ONNX conversion: https://pytorch.org/docs/stable/onnx.html
- ONNX Runtime: https://onnxruntime.ai/
- Whisper models: https://github.com/openai/whisper

## Implementation Notes

- Start with Silero VAD as the primary implementation
- Implement Whisper VAD as an alternative option
- Follow existing project conventions for code style
- Implement proper logging for all detection events
- Document complex algorithms and model-specific behaviors
- Create visualization tools for debugging VAD performance

---

**TASK-REF**: TASK-VP-002 - Voice Activity Detection
**CONCEPT-REF**: CON-VANTA-001 - Voice Pipeline
**DOC-REF**: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
**DECISION-REF**: DEC-002-004 - Support multiple activation modes