# Voice Pipeline Implementation - Speech-to-Text Integration [VOICE_003]

## Task Overview

This prompt guides the implementation of the Speech-to-Text (STT) component for VANTA's Voice Pipeline. The STT system is responsible for converting speech audio to text transcriptions using the Whisper model, providing the core speech recognition capabilities for the VANTA assistant.

## Implementation Context

Speech-to-Text is a critical component of the voice pipeline that converts spoken language into text for further processing by the language models. This component must handle various accents, speaking styles, and environmental conditions while maintaining high accuracy and reasonable performance on the target hardware.

### Related Documentation
- `/Development/Architecture/COMPONENT_SPECIFICATIONS/VOICE_PIPELINE.md`: Complete component specification
- `/Development/Architecture/V0_ARCHITECTURE_OVERVIEW.md`: System architecture overview
- `/Development/Architecture/DATA_MODELS.md`: Data structure definitions
- `/Development/Prompts/Phase1_Core/VoicePipeline/VOICE_001_Audio_Processing_Infrastructure.md`: Audio infrastructure implementation
- `/Development/Prompts/Phase1_Core/VoicePipeline/VOICE_002_Voice_Activity_Detection.md`: VAD implementation

### Dependencies
- TASK-VP-001: Audio Processing Infrastructure
- TASK-VP-002: Voice Activity Detection
- TASK-ENV-003: Model Preparation (for Whisper models)

## Implementation Requirements

### 1. Whisper Model Adapter (whisper_adapter.py)

Implement a Whisper model adapter with the following features:

- Integration with the model registry from ENV_003
- Support for different Whisper model sizes (tiny, base, small)
- Optimized inference for Apple M4 hardware
- Proper resource management for efficient memory usage
- Configurable inference parameters

Example interface:

```python
class WhisperAdapter:
    def __init__(self, 
                 model_size="small",  # tiny, base, small, medium
                 device="mps",       # cpu, mps (Metal)
                 compute_type="int8", # float16, int8
                 language="en",      # language code
                 beam_size=5):
        """Initialize Whisper model adapter.
        
        Args:
            model_size: Size of Whisper model to use
            device: Compute device (cpu or mps for Metal)
            compute_type: Computation precision
            language: Language code for transcription
            beam_size: Beam search size for decoding
        """
        pass
    
    def load_model(self):
        """Load the Whisper model from the model registry."""
        pass
    
    def unload_model(self):
        """Unload the model to free resources."""
        pass
    
    def is_loaded(self):
        """Check if model is currently loaded."""
        pass
    
    def transcribe(self, audio_data, **kwargs):
        """Transcribe audio data to text.
        
        Args:
            audio_data: Numpy array of audio samples
            **kwargs: Additional parameters for transcription
            
        Returns:
            Dict with transcription results:
            {
                "text": str,
                "segments": List of segment dicts,
                "language": str,
                "confidence": float
            }
        """
        pass
    
    def transcribe_with_timestamps(self, audio_data, **kwargs):
        """Transcribe audio and include word-level timestamps.
        
        Args:
            audio_data: Numpy array of audio samples
            **kwargs: Additional parameters for transcription
            
        Returns:
            Dict with detailed transcription results including timestamps
        """
        pass
    
    def get_model_info(self):
        """Get information about the loaded model."""
        pass
```

### 2. Transcription Manager (transcriber.py)

Implement a transcription manager with the following features:

- High-level interface for speech recognition
- Streaming transcription for real-time feedback
- Transcription confidence scoring and filtering
- Context-aware transcription (e.g., using previous context)
- Configurable transcription parameters
- Results caching for efficiency

Example interface:

```python
from enum import Enum

class TranscriptionQuality(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Transcriber:
    def __init__(self,
                 whisper_adapter=None,
                 min_confidence=0.4,
                 default_quality=TranscriptionQuality.MEDIUM,
                 enable_streaming=True,
                 cache_size=10):
        """Initialize transcription manager.
        
        Args:
            whisper_adapter: WhisperAdapter instance
            min_confidence: Minimum confidence threshold
            default_quality: Default transcription quality
            enable_streaming: Whether to enable streaming transcription
            cache_size: Size of result cache
        """
        pass
    
    def transcribe(self, 
                  audio_data, 
                  quality=None,
                  context=None,
                  callback=None):
        """Transcribe audio to text.
        
        Args:
            audio_data: Numpy array of audio samples
            quality: TranscriptionQuality or None for default
            context: Optional previous context to improve transcription
            callback: Optional callback for streaming results
            
        Returns:
            Dict with transcription results
        """
        pass
    
    def start_streaming(self, callback):
        """Start streaming transcription mode.
        
        Args:
            callback: Function to call with interim results
        """
        pass
    
    def feed_audio_chunk(self, audio_chunk):
        """Feed audio chunk to streaming transcription.
        
        Args:
            audio_chunk: New chunk of audio data
            
        Returns:
            Dict with interim transcription (if available)
        """
        pass
    
    def stop_streaming(self):
        """Stop streaming and return final transcription."""
        pass
    
    def set_quality(self, quality: TranscriptionQuality):
        """Set transcription quality (affects model size and parameters)."""
        pass
    
    def configure(self, **kwargs):
        """Update configuration parameters."""
        pass
```

### 3. Transcription Result Processing (transcriber.py)

Implement transcription post-processing with the following features:

- Text normalization (e.g., punctuation, capitalization)
- Confidence-based filtering or flagging
- Speaker diarization placeholders (for future implementation)
- Result formatting for language model input
- Metadata extraction for system use

Example implementation:

```python
class TranscriptionProcessor:
    def __init__(self,
                 capitalize_sentences=True,
                 filter_hesitations=True,
                 confidence_threshold=0.4):
        """Initialize transcription processor.
        
        Args:
            capitalize_sentences: Whether to auto-capitalize sentences
            filter_hesitations: Whether to filter out hesitation sounds
            confidence_threshold: Threshold for accepting words
        """
        pass
    
    def process(self, transcription_result):
        """Process a transcription result.
        
        Args:
            transcription_result: Dict from Whisper transcription
            
        Returns:
            Processed transcription with normalized text
        """
        pass
    
    def normalize_text(self, text):
        """Normalize text with proper capitalization and punctuation."""
        pass
    
    def filter_low_confidence(self, segments, threshold=None):
        """Filter out low confidence words or segments."""
        pass
    
    def extract_metadata(self, transcription_result):
        """Extract useful metadata from transcription result."""
        pass
    
    def format_for_language_model(self, processed_result):
        """Format the processed transcription for LLM input."""
        pass
```

### 4. Integration with Voice Pipeline

Integrate the STT components with the voice pipeline:

```python
# In pipeline.py
from voice.audio.capture import AudioCapture
from voice.audio.preprocessing import AudioPreprocessor
from voice.audio.playback import AudioPlayback
from voice.audio.config import AudioConfig
from voice.vad.detector import VoiceActivityDetector
from voice.vad.activation import WakeWordDetector, ActivationManager, ActivationState
from voice.stt.whisper_adapter import WhisperAdapter
from voice.stt.transcriber import Transcriber, TranscriptionProcessor

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
        
        # STT components
        stt_config = self.config.get_stt_config()
        self.whisper_adapter = WhisperAdapter(**stt_config.get("whisper", {}))
        self.transcriber = Transcriber(
            whisper_adapter=self.whisper_adapter,
            **stt_config.get("transcriber", {})
        )
        self.transcription_processor = TranscriptionProcessor(
            **stt_config.get("processor", {})
        )
        
        # Set up audio processing callback
        self.capture.add_callback(self._process_audio)
        
        # Add activation state change listener
        self.activation_manager.add_state_change_listener(self._on_activation_state_change)
        
        # Buffer for collecting speech audio during active periods
        self.speech_buffer = []
        
    def _process_audio(self, audio_data):
        """Process incoming audio data from capture."""
        # Process the audio
        processed_audio = self.preprocessor.process(audio_data)
        
        # Check activation state
        activation_result = self.activation_manager.process_audio(processed_audio)
        
        # If we should process this audio for speech recognition
        if activation_result["should_process"]:
            # Add to speech buffer for processing
            self.speech_buffer.append(processed_audio)
            
            # If we're in streaming mode, feed to streaming transcriber
            if self.transcriber.is_streaming():
                self.transcriber.feed_audio_chunk(processed_audio)
            
            # If we've reached the end of speech or max buffer size
            if (not activation_result["is_speech"] and len(self.speech_buffer) > 0) or \
               len(self.speech_buffer) >= self.config.get_max_buffer_chunks():
                # Concatenate speech chunks
                speech_audio = np.concatenate(self.speech_buffer)
                self.speech_buffer = []
                
                # Transcribe the full utterance
                transcription = self.transcriber.transcribe(speech_audio)
                
                # Process the transcription
                processed_result = self.transcription_processor.process(transcription)
                
                # Here we would pass to language model component
                # (to be implemented in future tasks)
                print(f"Transcribed: {processed_result['text']}")
            
    def _on_activation_state_change(self, old_state, new_state):
        """Handle activation state changes."""
        if new_state == ActivationState.ACTIVE:
            # Clear speech buffer when becoming active
            self.speech_buffer = []
            # Start streaming transcription
            self.transcriber.start_streaming(self._on_streaming_result)
        elif new_state == ActivationState.INACTIVE:
            # Stop streaming when becoming inactive
            if self.transcriber.is_streaming():
                final_result = self.transcriber.stop_streaming()
                if final_result:
                    processed_result = self.transcription_processor.process(final_result)
                    print(f"Final transcription: {processed_result['text']}")
            
    def _on_streaming_result(self, interim_result):
        """Handle streaming transcription results."""
        # Log interim results
        print(f"Interim: {interim_result['text']}")
```

### 5. Configuration Extensions

Extend the audio configuration module to include STT settings:

```python
# In config.py
class AudioConfig:
    DEFAULT_CONFIG = {
        # Existing audio config
        "capture": { ... },
        "preprocessing": { ... },
        "playback": { ... },
        "vad": { ... },
        "wake_word": { ... },
        "activation": { ... },
        
        # STT configuration
        "stt": {
            "whisper": {
                "model_size": "small",
                "device": "mps",
                "compute_type": "int8",
                "language": "en",
                "beam_size": 5
            },
            "transcriber": {
                "min_confidence": 0.4,
                "default_quality": "medium",
                "enable_streaming": True,
                "cache_size": 10
            },
            "processor": {
                "capitalize_sentences": True,
                "filter_hesitations": True,
                "confidence_threshold": 0.4
            }
        },
        
        # Buffer settings
        "max_buffer_chunks": 50  # Maximum chunks to buffer
    }
    
    # Add these methods to the existing AudioConfig class
    def get_stt_config(self):
        """Get STT-specific configuration."""
        return self.config.get("stt", {})
    
    def get_max_buffer_chunks(self):
        """Get maximum buffer chunks."""
        return self.config.get("max_buffer_chunks", 50)
```

## Model Integration

### 1. Whisper.cpp Integration

Implement Whisper.cpp for optimized speech recognition:

- Load models from the model registry
- Use Metal acceleration on M4 hardware
- Implement efficient memory management
- Support different models based on quality requirements

Example implementation:

```python
import whisperc  # C++ bindings for Whisper
import numpy as np
from typing import Dict, List, Any, Optional

class WhisperCppAdapter:
    def __init__(self,
                 model_path=None,
                 model_size="small",
                 language="en",
                 use_metal=True,
                 beam_size=5,
                 best_of=5):
        """Initialize Whisper.cpp adapter.
        
        Args:
            model_path: Path to model file or None to use model registry
            model_size: Size of model to use if model_path is None
            language: Language code
            use_metal: Whether to use Metal acceleration
            beam_size: Beam size for decoding
            best_of: Number of candidates to generate
        """
        self.model_size = model_size
        self.language = language
        self.use_metal = use_metal
        self.beam_size = beam_size
        self.best_of = best_of
        self.model_path = model_path
        self.context = None
        
    def _get_model_from_registry(self):
        """Get model path from the registry."""
        from models.registry import ModelRegistry
        registry = ModelRegistry()
        model_info = registry.get_model(f"whisper-{self.model_size}")
        
        if not model_info:
            raise ValueError(f"Model whisper-{self.model_size} not found in registry")
            
        return model_info["path"]
    
    def load_model(self):
        """Load the Whisper model."""
        if not self.model_path:
            self.model_path = self._get_model_from_registry()
            
        # Initialize whisper.cpp context
        self.context = whisperc.Context()
        
        # Set Metal acceleration if available and requested
        if self.use_metal and whisperc.has_metal():
            self.context.set_metal(True)
            
        # Load the model
        result = self.context.load_model(self.model_path)
        if not result:
            raise RuntimeError(f"Failed to load model from {self.model_path}")
            
        # Configure the context
        self.context.set_language(self.language)
        self.context.set_beam_search(self.beam_size, self.best_of)
        
    def unload_model(self):
        """Unload the model and free resources."""
        if self.context:
            self.context = None
            
    def is_loaded(self):
        """Check if the model is loaded."""
        return self.context is not None
        
    def transcribe(self, audio_data, **kwargs):
        """Transcribe audio using Whisper.cpp.
        
        Args:
            audio_data: Numpy array of audio samples (16kHz, mono, float32)
            
        Returns:
            Dict with transcription results
        """
        if not self.is_loaded():
            self.load_model()
            
        # Ensure audio is in the correct format
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
            
        # Convert to float32 if needed
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            
        # Ensure audio is normalized to [-1, 1]
        if np.max(np.abs(audio_data)) > 1.0:
            audio_data = audio_data / np.max(np.abs(audio_data))
            
        # Transcribe using Whisper.cpp
        params = whisperc.Params()
        params.language = kwargs.get("language", self.language)
        params.translate = kwargs.get("translate", False)
        params.beam_size = kwargs.get("beam_size", self.beam_size)
        params.best_of = kwargs.get("best_of", self.best_of)
        
        # Run inference
        result = self.context.transcribe(audio_data, params)
        
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
        
    def transcribe_with_timestamps(self, audio_data, **kwargs):
        """Transcribe with word-level timestamps."""
        # Similar to transcribe but with word timestamps
        # This is a more advanced feature that requires
        # extracting word alignments from Whisper
        pass
```

### 2. Alternative Whisper Implementation (Optional)

Provide an alternative implementation using the OpenAI Whisper Python package:

- Use for higher quality when performance is less critical
- Implement the same interface for consistent usage
- Provide fallback in case of C++ binding issues

Example implementation:

```python
import whisper
import torch
import numpy as np

class WhisperPythonAdapter:
    def __init__(self,
                 model_size="small",
                 device="mps",
                 compute_type="float16",
                 language="en"):
        """Initialize OpenAI Whisper Python adapter."""
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.model = None
        
    def load_model(self):
        """Load Whisper model using Python API."""
        # Determine the compute device
        if self.device == "mps" and torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
        # Determine compute type
        if self.compute_type == "float16" and device.type != "cpu":
            torch_dtype = torch.float16
        else:
            torch_dtype = torch.float32
            
        # Load the model
        self.model = whisper.load_model(self.model_size, device=device, download_root="models/whisper")
        
    def unload_model(self):
        """Unload the model to free resources."""
        self.model = None
        torch.cuda.empty_cache()
        
    def is_loaded(self):
        """Check if model is loaded."""
        return self.model is not None
        
    def transcribe(self, audio_data, **kwargs):
        """Transcribe audio using Whisper Python API."""
        if not self.is_loaded():
            self.load_model()
            
        # Convert audio to the expected format
        if not isinstance(audio_data, np.ndarray):
            raise TypeError("Audio data must be a numpy array")
            
        # Perform transcription
        options = {
            "language": kwargs.get("language", self.language),
            "beam_size": kwargs.get("beam_size", 5),
            "best_of": kwargs.get("best_of", 5),
            "temperature": kwargs.get("temperature", 0),
            "fp16": self.compute_type == "float16",
            "task": "transcribe"
        }
        
        result = self.model.transcribe(audio_data, **options)
        
        # Format result for consistency with the C++ adapter
        segments = []
        for i, seg in enumerate(result["segments"]):
            segments.append({
                "id": i,
                "text": seg["text"],
                "start": seg["start"],
                "end": seg["end"],
                "confidence": seg.get("confidence", 0.8)  # Default if not provided
            })
            
        return {
            "text": result["text"],
            "segments": segments,
            "language": result["language"],
            "confidence": sum(seg["confidence"] for seg in segments) / len(segments) if segments else 0
        }
```

## Testing Requirements

Implement comprehensive unit tests for each module:

- Test Whisper model loading and unloading
- Test transcription with various audio samples
- Test streaming transcription functionality
- Test transcription processing and normalization
- Test integration with audio pipeline

Example test cases:

```python
# Test whisper adapter
def test_whisper_adapter():
    adapter = WhisperAdapter(model_size="tiny")
    
    # Test model loading
    adapter.load_model()
    assert adapter.is_loaded()
    
    # Test transcription on a known audio file
    audio_data = load_test_audio("test_sentence.wav")
    result = adapter.transcribe(audio_data)
    
    # Check that text is present
    assert result["text"]
    assert len(result["segments"]) > 0
    
    # Test unloading
    adapter.unload_model()
    assert not adapter.is_loaded()

# Test transcription processing
def test_transcription_processing():
    processor = TranscriptionProcessor()
    
    # Test capitalization
    result = {
        "text": "this is a test sentence",
        "segments": [{"text": "this is a test sentence", "confidence": 0.9}]
    }
    
    processed = processor.process(result)
    assert processed["text"] == "This is a test sentence"
    
    # Test filtering
    result = {
        "text": "um this is a um test with hesitations",
        "segments": [{"text": "um this is a um test with hesitations", "confidence": 0.9}]
    }
    
    processed = processor.process(result)
    assert "um" not in processed["text"].lower()

# Test streaming transcription
def test_streaming_transcription():
    adapter = WhisperAdapter(model_size="tiny")
    transcriber = Transcriber(whisper_adapter=adapter, enable_streaming=True)
    
    # Start streaming
    results = []
    transcriber.start_streaming(lambda x: results.append(x))
    
    # Feed audio chunks
    audio_chunks = split_audio_file("test_sentence.wav", chunk_size=4096)
    for chunk in audio_chunks:
        transcriber.feed_audio_chunk(chunk)
    
    # Stop streaming and get final result
    final_result = transcriber.stop_streaming()
    
    # Check that we have interim and final results
    assert len(results) > 0
    assert final_result["text"]
```

## Technical Considerations

### Performance

- Use Whisper.cpp for best performance on Apple Silicon
- Implement model caching to avoid repeated loading
- Use streaming transcription when possible for faster feedback
- Load smaller models for faster transcription when appropriate
- Monitor memory and CPU usage during transcription

### Accuracy

- Select the appropriate model size based on accuracy requirements
- Use language-specific models when possible
- Provide confidence scores for transcriptions
- Implement post-processing to improve text quality
- Consider context from previous interactions

### Resource Management

- Implement proper model unloading to free resources
- Only load models when needed
- Monitor memory usage and adapt accordingly
- Support quality/performance tradeoffs through configuration

## Validation Criteria

The implementation will be considered successful when:

1. Whisper model integration works correctly
   - Models load correctly from the registry
   - Metal acceleration is utilized on M4 hardware
   - Memory usage is within constraints (<2GB)
   - Models are properly unloaded when not in use

2. Transcription accuracy meets targets
   - >90% Word Error Rate (WER) in quiet environments
   - Handles various accents and speaking styles
   - Correctly identifies most domain-specific terms
   - Provides reasonable confidence scores

3. Latency meets requirements
   - <500ms for typical utterance transcription
   - Streaming interim results available within 200ms
   - Model loading takes <2s (for small model)

4. Integration with pipeline works seamlessly
   - VAD triggers transcription appropriately
   - Speech buffer management works correctly
   - Streaming transcription provides timely feedback
   - Configuration system works properly

5. All tests pass
   - Unit tests for STT components
   - Integration tests with audio pipeline
   - Performance tests meet latency targets
   - Accuracy tests meet WER targets

## Resources and References

- Whisper repository: https://github.com/openai/whisper
- Whisper.cpp repository: https://github.com/ggerganov/whisper.cpp
- PyTorch Metal acceleration: https://developer.apple.com/metal/pytorch/
- Speech recognition metrics: https://en.wikipedia.org/wiki/Word_error_rate

## Implementation Notes

- Start with the C++ implementation for best performance
- Implement the Python version as a fallback
- Carefully manage memory and resources during transcription
- Log detailed performance metrics to identify bottlenecks
- Use the model registry system for model management
- Document performance characteristics with different model sizes

---

**TASK-REF**: TASK-VP-003 - Speech-to-Text Integration
**CONCEPT-REF**: CON-VANTA-001 - Voice Pipeline
**DOC-REF**: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
**DECISION-REF**: DEC-002-001 - Use Whisper for speech-to-text conversion