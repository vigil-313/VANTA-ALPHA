# Voice Pipeline Implementation - Text-to-Speech Integration [VOICE_004]

## Task Overview

This prompt guides the implementation of the Text-to-Speech (TTS) component for VANTA's Voice Pipeline. The TTS system is responsible for converting text responses to natural-sounding speech, providing the voice output capabilities for the VANTA assistant.

## Implementation Context

Text-to-Speech is a critical component of the voice pipeline that converts language model responses into spoken language. This component must generate natural-sounding speech with appropriate prosody and emphasis while maintaining good performance on the target hardware. The implementation should support multiple TTS engines and allow for future enhancements.

### Related Documentation
- `/Development/Architecture/COMPONENT_SPECIFICATIONS/VOICE_PIPELINE.md`: Complete component specification
- `/Development/Architecture/V0_ARCHITECTURE_OVERVIEW.md`: System architecture overview
- `/Development/Architecture/DATA_MODELS.md`: Data structure definitions
- `/Development/Prompts/Phase1_Core/VoicePipeline/VOICE_001_Audio_Processing_Infrastructure.md`: Audio infrastructure implementation
- `/Development/Prompts/Phase1_Core/VoicePipeline/VOICE_002_Voice_Activity_Detection.md`: VAD implementation
- `/Development/Prompts/Phase1_Core/VoicePipeline/VOICE_003_Speech_to_Text_Integration.md`: STT implementation

### Dependencies
- TASK-VP-001: Audio Processing Infrastructure
- TASK-VP-003: Speech-to-Text Integration
- TASK-ENV-003: Model Preparation (for TTS models)

## Implementation Requirements

### 1. TTS Engine Adapter (tts_adapter.py)

Implement a TTS engine adapter with the following features:

- Support for multiple TTS engines (API-based and local models)
- Optimized performance for Apple M4 hardware
- Voice selection and customization
- Proper resource management for efficient memory usage
- Configurable synthesis parameters

Example interface:

```python
from enum import Enum
from typing import Dict, Any, Optional, List, Union
import numpy as np

class TTSEngineType(Enum):
    """Enumeration of supported TTS engine types."""
    API = "api"  # Cloud-based API engines
    LOCAL = "local"  # Local model-based engines
    SYSTEM = "system"  # Operating system TTS

class TTSAdapter:
    def __init__(self, 
                 engine_type: Union[TTSEngineType, str] = TTSEngineType.LOCAL,
                 voice_id: str = "default",
                 model_path: Optional[str] = None,
                 api_key: Optional[str] = None,
                 speaking_rate: float = 1.0,
                 pitch: float = 0.0,
                 sample_rate: int = 24000):
        """Initialize TTS adapter.
        
        Args:
            engine_type: Type of TTS engine to use
            voice_id: Voice identifier to use
            model_path: Path to local model (if using LOCAL engine)
            api_key: API key (if using API engine)
            speaking_rate: Speech rate multiplier (0.5-2.0)
            pitch: Voice pitch adjustment (-10.0 to 10.0)
            sample_rate: Output audio sample rate
        """
        pass
    
    def load_engine(self):
        """Load the TTS engine."""
        pass
    
    def unload_engine(self):
        """Unload the engine to free resources."""
        pass
    
    def is_loaded(self):
        """Check if engine is currently loaded."""
        pass
    
    def synthesize(self, text: str, **kwargs) -> Dict[str, Any]:
        """Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            **kwargs: Additional parameters for synthesis
            
        Returns:
            Dict with synthesis results:
            {
                "audio": numpy array of audio samples,
                "sample_rate": int,
                "duration": float (seconds),
                "format": str (audio format)
            }
        """
        pass
    
    def synthesize_ssml(self, ssml: str, **kwargs) -> Dict[str, Any]:
        """Synthesize speech from SSML markup.
        
        Args:
            ssml: SSML text to synthesize
            **kwargs: Additional parameters for synthesis
            
        Returns:
            Dict with synthesis results
        """
        pass
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices for the current engine."""
        pass
    
    def set_voice(self, voice_id: str) -> bool:
        """Change the voice to use for synthesis."""
        pass
    
    def set_parameters(self, **params) -> bool:
        """Update synthesis parameters."""
        pass
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about the loaded engine."""
        pass
```

### 2. TTS Engine Implementations

Implement adapters for specific TTS engines:

#### API-Based TTS Engine (OpenAI TTS API)

```python
class OpenAITTSAdapter(TTSAdapter):
    """TTS adapter for OpenAI's TTS API."""
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 voice_id: str = "alloy",  # OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
                 model: str = "tts-1",    # "tts-1" or "tts-1-hd"
                 speaking_rate: float = 1.0,
                 pitch: float = 0.0,
                 sample_rate: int = 24000):
        """Initialize OpenAI TTS adapter."""
        pass
    
    def load_engine(self):
        """Set up the OpenAI API client."""
        pass
    
    def synthesize(self, text: str, **kwargs) -> Dict[str, Any]:
        """Synthesize speech using OpenAI TTS API."""
        pass
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available OpenAI voices."""
        pass
```

#### Local TTS Engine (e.g., Coqui TTS or Piper TTS)

```python
class LocalTTSAdapter(TTSAdapter):
    """TTS adapter for local TTS models."""
    
    def __init__(self,
                 model_path: Optional[str] = None,
                 model_type: str = "piper",  # piper, coqui, etc.
                 voice_id: str = "default",
                 speaking_rate: float = 1.0,
                 pitch: float = 0.0,
                 sample_rate: int = 24000):
        """Initialize local TTS adapter."""
        pass
    
    def load_engine(self):
        """Load the local TTS model."""
        pass
    
    def unload_engine(self):
        """Unload the model to free resources."""
        pass
    
    def synthesize(self, text: str, **kwargs) -> Dict[str, Any]:
        """Synthesize speech using local TTS model."""
        pass
```

#### System TTS Engine (macOS TTS)

```python
class SystemTTSAdapter(TTSAdapter):
    """TTS adapter for system TTS (macOS)."""
    
    def __init__(self,
                 voice_id: str = "Alex",  # System voice name
                 speaking_rate: float = 1.0,
                 pitch: float = 0.0,
                 sample_rate: int = 24000):
        """Initialize system TTS adapter."""
        pass
    
    def load_engine(self):
        """Initialize system TTS."""
        pass
    
    def synthesize(self, text: str, **kwargs) -> Dict[str, Any]:
        """Synthesize speech using system TTS."""
        pass
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available system voices."""
        pass
```

### 3. Speech Synthesis Manager (speech_synthesizer.py)

Implement a speech synthesis manager with the following features:

- High-level interface for text-to-speech synthesis
- Text preprocessing and formatting
- SSML generation for enhanced prosody
- Caching of frequently used phrases
- Configuration management

Example interface:

```python
class SpeechSynthesizer:
    def __init__(self,
                 tts_adapter: Optional[TTSAdapter] = None,
                 enable_caching: bool = True,
                 cache_size: int = 50,
                 preprocess_text: bool = True,
                 enable_ssml: bool = True):
        """Initialize speech synthesizer.
        
        Args:
            tts_adapter: TTSAdapter instance
            enable_caching: Whether to cache synthesis results
            cache_size: Size of synthesis cache
            preprocess_text: Whether to preprocess text before synthesis
            enable_ssml: Whether to use SSML for prosody control
        """
        pass
    
    def synthesize(self, 
                  text: str, 
                  voice_id: Optional[str] = None,
                  speaking_rate: Optional[float] = None,
                  pitch: Optional[float] = None,
                  use_ssml: Optional[bool] = None) -> Dict[str, Any]:
        """Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice_id: Voice to use (or None for default)
            speaking_rate: Speaking rate override
            pitch: Pitch override
            use_ssml: Whether to generate SSML (if None, use default setting)
            
        Returns:
            Dict with synthesis results
        """
        pass
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for better synthesis."""
        pass
    
    def generate_ssml(self, text: str, **kwargs) -> str:
        """Generate SSML markup for the text."""
        pass
    
    def clear_cache(self):
        """Clear synthesis cache."""
        pass
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices."""
        pass
    
    def set_voice(self, voice_id: str) -> bool:
        """Set the default voice."""
        pass
    
    def configure(self, **kwargs):
        """Update synthesizer configuration."""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get synthesizer statistics."""
        pass
```

### 4. Prosody and Formatting (prosody_formatter.py)

Implement text formatting and prosody control for TTS:

```python
class ProsodyFormatter:
    def __init__(self,
                 add_punctuation: bool = True,
                 enhance_questions: bool = True,
                 enhance_emphasis: bool = True,
                 normalize_numbers: bool = True,
                 expand_abbreviations: bool = True):
        """Initialize prosody formatter.
        
        Args:
            add_punctuation: Whether to ensure text has proper punctuation
            enhance_questions: Whether to enhance question intonation
            enhance_emphasis: Whether to add emphasis to important words
            normalize_numbers: Whether to convert numbers to speakable form
            expand_abbreviations: Whether to expand common abbreviations
        """
        pass
    
    def format_text(self, text: str) -> str:
        """Format plain text for better synthesis."""
        pass
    
    def normalize_numbers(self, text: str) -> str:
        """Convert numbers to speakable form."""
        pass
    
    def expand_abbreviations(self, text: str) -> str:
        """Expand common abbreviations."""
        pass
    
    def ensure_punctuation(self, text: str) -> str:
        """Ensure text has proper punctuation."""
        pass
    
    def to_ssml(self, text: str, 
               speaking_rate: float = 1.0,
               pitch: float = 0.0,
               emphasis_words: List[str] = None) -> str:
        """Convert plain text to SSML markup.
        
        Args:
            text: Text to convert
            speaking_rate: Overall speaking rate
            pitch: Overall pitch adjustment
            emphasis_words: Words to emphasize
            
        Returns:
            SSML markup
        """
        pass
    
    def add_prosody_marks(self, text: str) -> str:
        """Add prosody marks for improved expression."""
        pass
```

### 5. Integration with Voice Pipeline

Integrate the TTS components with the voice pipeline:

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
from voice.tts.tts_adapter import TTSAdapter, TTSEngineType
from voice.tts.speech_synthesizer import SpeechSynthesizer
from voice.tts.prosody_formatter import ProsodyFormatter

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
        
        # TTS components
        tts_config = self.config.get_tts_config()
        self.tts_adapter = TTSAdapter(**tts_config.get("engine", {}))
        self.prosody_formatter = ProsodyFormatter(**tts_config.get("prosody", {}))
        self.speech_synthesizer = SpeechSynthesizer(
            tts_adapter=self.tts_adapter,
            **tts_config.get("synthesizer", {})
        )
        
        # Set up audio processing callback
        self.capture.add_callback(self._process_audio)
        
        # Add activation state change listener
        self.activation_manager.add_state_change_listener(self._on_activation_state_change)
        
    def say(self, text, priority=0, interrupt=False):
        """Generate speech from text and play it.
        
        Args:
            text: Text to speak
            priority: Priority level (higher = more important)
            interrupt: Whether to interrupt current playback
            
        Returns:
            Playback ID
        """
        try:
            # Synthesize speech
            result = self.speech_synthesizer.synthesize(text)
            
            # Play the audio
            return self.playback.play(result["audio"], priority, interrupt)
        except Exception as e:
            logger.error(f"Error in say method: {e}")
            return ""
```

### 6. Configuration Extensions

Extend the audio configuration module to include TTS settings:

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
        "stt": { ... },
        
        # TTS configuration
        "tts": {
            "engine": {
                "engine_type": "local",  # "api", "local", "system"
                "voice_id": "default",
                "model_path": None,  # Auto-select from registry
                "api_key": None,  # For API engines
                "speaking_rate": 1.0,
                "pitch": 0.0,
                "sample_rate": 24000
            },
            "synthesizer": {
                "enable_caching": True,
                "cache_size": 50,
                "preprocess_text": True,
                "enable_ssml": True
            },
            "prosody": {
                "add_punctuation": True,
                "enhance_questions": True,
                "enhance_emphasis": True,
                "normalize_numbers": True,
                "expand_abbreviations": True
            }
        }
    }
    
    # Add this method to the existing AudioConfig class
    def get_tts_config(self):
        """Get TTS-specific configuration."""
        return self.config.get("tts", {})
```

## Engine Implementation Details

### 1. OpenAI TTS API Implementation

```python
import openai
import numpy as np
import io
from typing import Dict, Any, List
import soundfile as sf
import time

class OpenAITTSAdapter(TTSAdapter):
    def __init__(self, api_key=None, voice_id="alloy", model="tts-1", **kwargs):
        """Initialize OpenAI TTS adapter."""
        super().__init__(engine_type=TTSEngineType.API, voice_id=voice_id, **kwargs)
        self.api_key = api_key
        self.model = model
        self.speaking_rate = kwargs.get("speaking_rate", 1.0)
        self.sample_rate = kwargs.get("sample_rate", 24000)
        self.is_loaded_flag = False
        self.available_voices = [
            {"id": "alloy", "name": "Alloy", "gender": "neutral"},
            {"id": "echo", "name": "Echo", "gender": "male"},
            {"id": "fable", "name": "Fable", "gender": "female"},
            {"id": "onyx", "name": "Onyx", "gender": "male"},
            {"id": "nova", "name": "Nova", "gender": "female"},
            {"id": "shimmer", "name": "Shimmer", "gender": "female"}
        ]
        
    def load_engine(self):
        """Set up the OpenAI API client."""
        if self.api_key:
            openai.api_key = self.api_key
        self.is_loaded_flag = True
        return True
        
    def unload_engine(self):
        """Release resources."""
        self.is_loaded_flag = False
        return True
        
    def is_loaded(self):
        """Check if engine is loaded."""
        return self.is_loaded_flag
        
    def synthesize(self, text, **kwargs):
        """Synthesize speech using OpenAI TTS API."""
        if not self.is_loaded():
            self.load_engine()
            
        # Apply parameters
        voice = kwargs.get("voice_id", self.voice_id)
        model = kwargs.get("model", self.model)
        speaking_rate = kwargs.get("speaking_rate", self.speaking_rate)
        
        try:
            # Make API request
            start_time = time.time()
            response = openai.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                speed=speaking_rate,
                response_format="mp3"
            )
            
            # Get audio data
            audio_data = response.content
            
            # Convert to numpy array
            with io.BytesIO(audio_data) as audio_buffer:
                audio_array, sample_rate = sf.read(audio_buffer)
                
            # Convert to mono if needed
            if len(audio_array.shape) > 1:
                audio_array = audio_array.mean(axis=1)
                
            # Calculate duration
            duration = len(audio_array) / sample_rate
            
            return {
                "audio": audio_array,
                "sample_rate": sample_rate,
                "duration": duration,
                "format": "mp3",
                "latency": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing speech with OpenAI TTS: {e}")
            # Return empty audio on error
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": self.sample_rate,
                "duration": 0.0,
                "format": "raw",
                "error": str(e)
            }
            
    def get_available_voices(self):
        """Get list of available OpenAI voices."""
        return self.available_voices
```

### 2. Local TTS Engine Implementation (Piper TTS)

```python
import numpy as np
from typing import Dict, Any, List, Optional
import os
import subprocess
import tempfile
import soundfile as sf
import time
import json

class PiperTTSAdapter(TTSAdapter):
    def __init__(self, model_path=None, voice_id="default", **kwargs):
        """Initialize Piper TTS adapter."""
        super().__init__(engine_type=TTSEngineType.LOCAL, voice_id=voice_id, **kwargs)
        self.model_path = model_path
        self.speaking_rate = kwargs.get("speaking_rate", 1.0)
        self.pitch = kwargs.get("pitch", 0.0)
        self.sample_rate = kwargs.get("sample_rate", 24000)
        self.piper_path = self._find_piper_executable()
        self.available_voices = []
        self.is_loaded_flag = False
        
    def _find_piper_executable(self):
        """Find the Piper executable."""
        # Default locations to check
        possible_paths = [
            "/usr/local/bin/piper",
            "/opt/homebrew/bin/piper",
            os.path.expanduser("~/.local/bin/piper")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        return "piper"  # Assume it's in PATH
        
    def _get_model_from_registry(self):
        """Get model path from the registry."""
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
        
    def load_engine(self):
        """Load the Piper TTS engine."""
        if not self.model_path:
            try:
                self.model_path = self._get_model_from_registry()
            except Exception as e:
                logger.error(f"Error loading Piper model from registry: {e}")
                return False
                
        # Check if model exists
        if not os.path.exists(self.model_path):
            logger.error(f"Piper model not found at {self.model_path}")
            return False
            
        # Load available voices
        self._load_available_voices()
        
        self.is_loaded_flag = True
        return True
        
    def _load_available_voices(self):
        """Load available voices from model directory."""
        model_dir = os.path.dirname(self.model_path)
        self.available_voices = []
        
        try:
            # Try to find voice configuration files
            config_files = [f for f in os.listdir(model_dir) if f.endswith(".json")]
            
            for config_file in config_files:
                with open(os.path.join(model_dir, config_file), 'r') as f:
                    config = json.load(f)
                    if "name" in config:
                        self.available_voices.append({
                            "id": os.path.splitext(config_file)[0],
                            "name": config.get("name", "Unknown"),
                            "language": config.get("language", "en"),
                            "gender": config.get("gender", "neutral")
                        })
        except Exception as e:
            logger.error(f"Error loading Piper voices: {e}")
            
        # Add default voice if no voices found
        if not self.available_voices:
            self.available_voices.append({
                "id": "default",
                "name": "Default",
                "language": "en",
                "gender": "neutral"
            })
            
    def unload_engine(self):
        """Unload the Piper TTS engine."""
        self.is_loaded_flag = False
        return True
        
    def is_loaded(self):
        """Check if engine is loaded."""
        return self.is_loaded_flag
        
    def synthesize(self, text, **kwargs):
        """Synthesize speech using Piper TTS."""
        if not self.is_loaded():
            self.load_engine()
            
        # Apply parameters
        speaking_rate = kwargs.get("speaking_rate", self.speaking_rate)
        
        try:
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
                "--length_scale", str(1.0 / max(0.5, min(2.0, speaking_rate)))
            ]
            
            # Add input file
            cmd.extend(["--input_file", text_file_path])
            
            # Execute Piper
            start_time = time.time()
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Read the output audio file
            audio_array, sample_rate = sf.read(output_file_path)
            
            # Clean up temporary files
            try:
                os.unlink(text_file_path)
                os.unlink(output_file_path)
            except:
                pass
                
            # Calculate duration
            duration = len(audio_array) / sample_rate
            
            return {
                "audio": audio_array,
                "sample_rate": sample_rate,
                "duration": duration,
                "format": "wav",
                "latency": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing speech with Piper TTS: {e}")
            # Return empty audio on error
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": self.sample_rate,
                "duration": 0.0,
                "format": "raw",
                "error": str(e)
            }
            
    def get_available_voices(self):
        """Get list of available Piper voices."""
        if not self.is_loaded():
            self.load_engine()
        return self.available_voices
```

### 3. System TTS Implementation (macOS)

```python
import numpy as np
from typing import Dict, Any, List, Optional
import os
import subprocess
import tempfile
import soundfile as sf
import time
import platform

class SystemTTSAdapter(TTSAdapter):
    def __init__(self, voice_id="Alex", **kwargs):
        """Initialize System TTS adapter."""
        super().__init__(engine_type=TTSEngineType.SYSTEM, voice_id=voice_id, **kwargs)
        self.speaking_rate = kwargs.get("speaking_rate", 1.0)
        self.pitch = kwargs.get("pitch", 0.0)
        self.sample_rate = kwargs.get("sample_rate", 24000)
        self.available_voices = []
        self.is_loaded_flag = False
        self.platform = platform.system()
        
    def load_engine(self):
        """Initialize system TTS."""
        if self.platform == "Darwin":  # macOS
            self._load_macos_voices()
            self.is_loaded_flag = True
            return True
        else:
            logger.warning(f"System TTS not supported on {self.platform}")
            return False
            
    def _load_macos_voices(self):
        """Load available voices on macOS."""
        try:
            # Use 'say' command to get available voices
            result = subprocess.run(
                ["say", "-v", "?"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Parse the output
            lines = result.stdout.strip().split('\n')
            self.available_voices = []
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    voice_id = parts[0]
                    gender = "female" if "fem" in line.lower() else "male"
                    language = "en"  # Default
                    
                    # Try to extract language
                    if "#" in line:
                        lang_part = line.split("#")[1].strip()
                        if len(lang_part) >= 2:
                            language = lang_part.split("_")[0]
                            
                    self.available_voices.append({
                        "id": voice_id,
                        "name": voice_id,
                        "language": language,
                        "gender": gender
                    })
                    
        except Exception as e:
            logger.error(f"Error loading macOS voices: {e}")
            # Add a default voice
            self.available_voices = [{
                "id": "Alex",
                "name": "Alex",
                "language": "en",
                "gender": "male"
            }]
            
    def unload_engine(self):
        """Release resources."""
        self.is_loaded_flag = False
        return True
        
    def is_loaded(self):
        """Check if engine is loaded."""
        return self.is_loaded_flag
        
    def synthesize(self, text, **kwargs):
        """Synthesize speech using system TTS."""
        if not self.is_loaded():
            self.load_engine()
            
        # Apply parameters
        voice = kwargs.get("voice_id", self.voice_id)
        speaking_rate = kwargs.get("speaking_rate", self.speaking_rate)
        
        if self.platform == "Darwin":  # macOS
            return self._synthesize_macos(text, voice, speaking_rate)
        else:
            logger.error(f"System TTS not supported on {self.platform}")
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": self.sample_rate,
                "duration": 0.0,
                "format": "raw",
                "error": f"System TTS not supported on {self.platform}"
            }
            
    def _synthesize_macos(self, text, voice, speaking_rate):
        """Synthesize speech using macOS 'say' command."""
        try:
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as out_file:
                output_path = out_file.name
                
            # Use 'say' command to generate speech
            start_time = time.time()
            rate_param = int(200 * speaking_rate)  # Default is 200
            
            subprocess.run([
                "say",
                "-v", voice,
                "-r", str(rate_param),
                "-o", output_path,
                text
            ], check=True)
            
            # Read the output audio file
            audio_array, sample_rate = sf.read(output_path)
            
            # Clean up temporary file
            try:
                os.unlink(output_path)
            except:
                pass
                
            # Calculate duration
            duration = len(audio_array) / sample_rate
            
            return {
                "audio": audio_array,
                "sample_rate": sample_rate,
                "duration": duration,
                "format": "aiff",
                "latency": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing speech with macOS TTS: {e}")
            return {
                "audio": np.zeros(1000, dtype=np.float32),
                "sample_rate": self.sample_rate,
                "duration": 0.0,
                "format": "raw",
                "error": str(e)
            }
            
    def get_available_voices(self):
        """Get list of available system voices."""
        if not self.is_loaded():
            self.load_engine()
        return self.available_voices
```

## Prosody and Formatting Implementation

### 1. Prosody Formatter

```python
import re
from typing import List, Dict, Any, Optional
import xml.sax.saxutils as saxutils

class ProsodyFormatter:
    def __init__(self,
                 add_punctuation: bool = True,
                 enhance_questions: bool = True,
                 enhance_emphasis: bool = True,
                 normalize_numbers: bool = True,
                 expand_abbreviations: bool = True):
        """Initialize prosody formatter."""
        self.add_punctuation = add_punctuation
        self.enhance_questions = enhance_questions
        self.enhance_emphasis = enhance_emphasis
        self.normalize_numbers = normalize_numbers
        self.expand_abbreviations = expand_abbreviations
        
        # Common abbreviations and their expansions
        self.abbreviations = {
            "Mr.": "Mister",
            "Mrs.": "Misses",
            "Dr.": "Doctor",
            "Prof.": "Professor",
            "St.": "Street",
            "Apt.": "Apartment",
            "vs.": "versus",
            "e.g.": "for example",
            "i.e.": "that is",
            "etc.": "etcetera",
            "fig.": "figure",
        }
        
        # Emphasis words (commonly emphasized in speech)
        self.emphasis_words = [
            "must", "very", "extremely", "absolutely", "definitely",
            "never", "always", "critical", "important", "urgent",
            "immediately", "vital", "essential", "crucial"
        ]
        
    def format_text(self, text: str) -> str:
        """Format plain text for better synthesis."""
        formatted_text = text
        
        # Apply formatting steps based on configuration
        if self.expand_abbreviations:
            formatted_text = self.expand_abbreviations_in_text(formatted_text)
            
        if self.normalize_numbers:
            formatted_text = self.normalize_numbers_in_text(formatted_text)
            
        if self.add_punctuation:
            formatted_text = self.ensure_punctuation(formatted_text)
            
        return formatted_text
        
    def expand_abbreviations_in_text(self, text: str) -> str:
        """Expand common abbreviations."""
        result = text
        for abbr, expansion in self.abbreviations.items():
            # Use word boundary to match whole abbreviations
            pattern = r'\b' + re.escape(abbr) + r'\b'
            result = re.sub(pattern, expansion, result)
        return result
        
    def normalize_numbers_in_text(self, text: str) -> str:
        """Convert numbers to speakable form."""
        # Handle percentages
        text = re.sub(r'(\d+)%', r'\1 percent', text)
        
        # Handle currencies
        text = re.sub(r'\$(\d+)', r'\1 dollars', text)
        
        # Handle time
        text = re.sub(r'(\d+):(\d+)', r'\1 \2', text)
        
        # Handle large numbers
        text = re.sub(r'(\d{1,3}),(\d{3})(,\d{3})*', r'\1\2\3', text)
        
        return text
        
    def ensure_punctuation(self, text: str) -> str:
        """Ensure text has proper end punctuation."""
        text = text.strip()
        if not text:
            return text
            
        # Add period if no end punctuation
        if not text[-1] in ['.', '!', '?', ':', ';']:
            text += '.'
            
        return text
        
    def to_ssml(self, text: str, 
               speaking_rate: float = 1.0,
               pitch: float = 0.0,
               emphasis_words: Optional[List[str]] = None) -> str:
        """Convert plain text to SSML markup."""
        # First, escape special characters
        escaped_text = saxutils.escape(text)
        
        # Format the text
        formatted_text = self.format_text(escaped_text)
        
        # Build SSML document
        ssml = f"""<?xml version="1.0"?>
<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis">
  <prosody rate="{speaking_rate}" pitch="{pitch}st">
"""
        
        # Add emphasis to important words
        if self.enhance_emphasis:
            words_to_emphasize = emphasis_words or self.emphasis_words
            for word in words_to_emphasize:
                pattern = r'\b' + re.escape(word) + r'\b'
                formatted_text = re.sub(
                    pattern, 
                    f'<emphasis level="moderate">{word}</emphasis>', 
                    formatted_text
                )
                
        # Add processing for questions
        if self.enhance_questions and '?' in formatted_text:
            sentences = re.split(r'([.!?])', formatted_text)
            processed_text = ""
            
            for i in range(0, len(sentences), 2):
                sentence = sentences[i] if i < len(sentences) else ""
                punctuation = sentences[i+1] if i+1 < len(sentences) else ""
                
                if punctuation == '?':
                    processed_text += f'<prosody rate="0.95" pitch="+1st">{sentence}{punctuation}</prosody> '
                else:
                    processed_text += sentence + punctuation + ' '
                    
            formatted_text = processed_text.strip()
            
        # Add the formatted text to SSML
        ssml += f"    {formatted_text}\n"
        ssml += "  </prosody>\n"
        ssml += "</speak>"
        
        return ssml
        
    def detect_emotion(self, text: str) -> str:
        """Detect emotional tone of text for appropriate prosody."""
        # This is a placeholder for more sophisticated emotion detection
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["happy", "great", "excellent", "awesome"]):
            return "happy"
        elif any(word in text_lower for word in ["sad", "sorry", "unfortunate", "regret"]):
            return "sad"
        elif any(word in text_lower for word in ["urgent", "emergency", "immediately", "danger"]):
            return "urgent"
        else:
            return "neutral"
            
    def add_prosody_for_emotion(self, ssml: str, emotion: str) -> str:
        """Add emotion-specific prosody to SSML."""
        if emotion == "happy":
            return ssml.replace('<prosody rate=', '<prosody pitch="+1st" rate=')
        elif emotion == "sad":
            return ssml.replace('<prosody rate=', '<prosody pitch="-1st" rate="0.95" ')
        elif emotion == "urgent":
            return ssml.replace('<prosody rate=', '<prosody rate="1.1" volume="+2dB" ')
        else:
            return ssml
```

## Integration with Voice Pipeline

### 1. Full Voice Pipeline Implementation

The TTS components should be integrated into the existing voice pipeline. Here's how the `say` method can be fully implemented:

```python
def say(self, text: str, priority: int = 0, interrupt: bool = False) -> str:
    """Speak the provided text.
    
    Args:
        text: Text to speak
        priority: Priority level (higher = more important)
        interrupt: Whether to interrupt current speech
        
    Returns:
        Playback ID if successful, empty string otherwise
    """
    try:
        logger.info(f"TTS (priority={priority}, interrupt={interrupt}): {text}")
        
        # Synthesize speech
        result = self.speech_synthesizer.synthesize(text)
        
        if "error" in result:
            logger.error(f"TTS synthesis error: {result['error']}")
            
            # Fallback to simple tone if synthesis failed
            duration = 0.5  # seconds
            sample_rate = self.playback.sample_rate
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            frequency = 440  # A4 note
            audio_data = np.sin(2 * np.pi * frequency * t)
            audio_data = (audio_data * 32767).astype(np.int16)
            
            # Play the audio
            return self.play_audio(audio_data, priority, interrupt)
            
        # Extract audio from result
        audio_data = result["audio"]
        
        # Resample if needed
        if result["sample_rate"] != self.playback.sample_rate:
            audio_data = self.preprocessor.resample(
                audio_data, 
                result["sample_rate"],
                self.playback.sample_rate
            )
            
        # Convert to correct format
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)
            
        # Play the audio
        return self.play_audio(audio_data, priority, interrupt)
        
    except Exception as e:
        logger.error(f"Error in say method: {e}")
        return ""
```

## Factory Pattern for TTS Adapter Selection

```python
def create_tts_adapter(config: Dict[str, Any]) -> TTSAdapter:
    """Factory function to create the appropriate TTS adapter.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        TTSAdapter instance
    """
    engine_type = config.get("engine_type", "local")
    
    if isinstance(engine_type, str):
        try:
            engine_type = TTSEngineType(engine_type)
        except ValueError:
            logger.warning(f"Invalid engine type: {engine_type}, using LOCAL")
            engine_type = TTSEngineType.LOCAL
            
    # Create the appropriate adapter based on engine type
    if engine_type == TTSEngineType.API:
        # Check for specific API provider
        api_provider = config.get("api_provider", "openai")
        
        if api_provider == "openai":
            return OpenAITTSAdapter(**config)
        else:
            logger.warning(f"Unknown API provider: {api_provider}, using OpenAI")
            return OpenAITTSAdapter(**config)
            
    elif engine_type == TTSEngineType.LOCAL:
        # Check for specific model type
        model_type = config.get("model_type", "piper")
        
        if model_type == "piper":
            return PiperTTSAdapter(**config)
        elif model_type == "coqui":
            # Could be implemented in future
            logger.warning("Coqui TTS not yet implemented, falling back to Piper")
            return PiperTTSAdapter(**config)
        else:
            logger.warning(f"Unknown local model type: {model_type}, using Piper")
            return PiperTTSAdapter(**config)
            
    elif engine_type == TTSEngineType.SYSTEM:
        return SystemTTSAdapter(**config)
        
    else:
        logger.warning(f"Unknown engine type: {engine_type}, using SystemTTS")
        return SystemTTSAdapter(**config)
```

## Testing Requirements

Implement comprehensive unit tests for each module:

- Test TTS adapter loading and unloading
- Test text synthesis with various parameters
- Test SSML generation
- Test prosody formatting
- Test integration with audio pipeline

Example test cases:

```python
# Test TTS adapter
def test_tts_adapter():
    adapter = SystemTTSAdapter()
    
    # Test engine loading
    adapter.load_engine()
    assert adapter.is_loaded()
    
    # Test synthesis
    result = adapter.synthesize("This is a test.")
    
    # Check that audio is present
    assert "audio" in result
    assert len(result["audio"]) > 0
    assert "sample_rate" in result
    assert "duration" in result
    
    # Test voice listing
    voices = adapter.get_available_voices()
    assert len(voices) > 0
    
    # Test unloading
    adapter.unload_engine()
    assert not adapter.is_loaded()

# Test prosody formatting
def test_prosody_formatting():
    formatter = ProsodyFormatter()
    
    # Test basic formatting
    text = "this is a test"
    formatted = formatter.format_text(text)
    assert formatted.endswith(".")
    
    # Test abbreviation expansion
    text = "Dr. Smith lives on St. Main"
    formatted = formatter.expand_abbreviations_in_text(text)
    assert "Doctor" in formatted
    assert "Street" in formatted
    
    # Test SSML generation
    text = "Is this a question?"
    ssml = formatter.to_ssml(text)
    assert "<?xml" in ssml
    assert "<speak" in ssml
    assert "<prosody" in ssml
    assert "?" in ssml

# Test speech synthesizer
def test_speech_synthesizer():
    adapter = SystemTTSAdapter()
    synthesizer = SpeechSynthesizer(tts_adapter=adapter)
    
    # Test basic synthesis
    result = synthesizer.synthesize("Hello world.")
    assert "audio" in result
    assert len(result["audio"]) > 0
    
    # Test voice setting
    voices = adapter.get_available_voices()
    if len(voices) > 1:
        new_voice = voices[1]["id"]
        synthesizer.set_voice(new_voice)
        # Verify the voice was set
        assert adapter.voice_id == new_voice
    
    # Test caching
    first_result = synthesizer.synthesize("Hello world.")
    adapter.synthesize = mock.MagicMock(return_value=first_result)
    
    second_result = synthesizer.synthesize("Hello world.")
    # Should use cache, not call adapter.synthesize
    adapter.synthesize.assert_not_called()
```

## Technical Considerations

### Performance

- Use local TTS engines when possible for best performance
- Implement caching for frequently used phrases
- Balance quality and performance based on system capabilities
- Use streaming synthesis when possible for faster responses
- Consider pre-synthesizing common phrases for immediate playback

### Quality

- Select appropriate voice and model for the intended use case
- Use SSML to enhance prosody and expressiveness
- Apply text preprocessing for better synthesis
- Consider context for appropriate emotional tone
- Test with a variety of text styles and content

### Resource Management

- Implement proper engine unloading to free resources
- Only load voices/models when needed
- Use API-based TTS when local resources are constrained
- Monitor memory and CPU usage during synthesis
- Support quality/performance tradeoffs through configuration

## Validation Criteria

The implementation will be considered successful when:

1. TTS engine integration works correctly
   - Both local and API-based engines function properly
   - Proper voice selection and configuration
   - Error handling and fallbacks work as expected
   - Memory usage is within constraints

2. Speech quality meets targets
   - Natural-sounding speech with appropriate prosody
   - Clear pronunciation and proper emphasis
   - Appropriate emotional expression
   - Handles various text formats and content types

3. Latency meets requirements
   - <200ms to begin speaking for typical phrases
   - Caching provides immediate response for common phrases
   - Performance scales well with text length

4. Integration with pipeline works seamlessly
   - TTS components interface properly with audio playback
   - Configuration system works properly
   - Thread-safe operation for concurrent access
   - Interruption and priority handling works correctly

5. All tests pass
   - Unit tests for TTS components
   - Integration tests with audio pipeline
   - Performance tests meet latency targets
   - Quality tests validate speech output

## Resources and References

- OpenAI TTS API: https://platform.openai.com/docs/guides/text-to-speech
- Piper TTS: https://github.com/rhasspy/piper
- SSML Reference: https://www.w3.org/TR/speech-synthesis11/
- MacOS say command: https://ss64.com/osx/say.html
- Speech synthesis techniques: https://en.wikipedia.org/wiki/Speech_synthesis

## Implementation Notes

- Start with the System TTS as it requires minimal setup
- Implement the OpenAI TTS API adapter next for higher quality
- Add local TTS engines last for offline operation
- Carefully manage API usage and error handling
- Log detailed performance metrics to identify bottlenecks
- Use the model registry system for model management
- Provide clear documentation for voice selection and configuration

---

**TASK-REF**: TASK-VP-004 - Text-to-Speech Integration
**CONCEPT-REF**: CON-VANTA-001 - Voice Pipeline
**DOC-REF**: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
**DECISION-REF**: DEC-002-003 - Use multiple TTS engines for flexibility