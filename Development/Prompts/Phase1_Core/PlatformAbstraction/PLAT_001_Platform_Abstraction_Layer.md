# Platform Abstraction Layer Implementation [PLAT_001]

## Task Overview

This prompt guides the implementation of the Platform Abstraction Layer for VANTA's audio processing components. This task addresses the challenges identified with Docker-based audio implementation on macOS and establishes a cross-platform foundation for future development on both macOS and Linux systems.

## Implementation Context

The Platform Abstraction Layer serves as an isolation mechanism between platform-specific implementations and core business logic. It enables VANTA to run efficiently on different operating systems while maintaining a unified codebase. This implementation focuses initially on audio components but is designed for extension to other platform-specific features.

### Related Documentation
- `/Development/Architecture/ARCHITECTURE_DIAGRAMS.md`: System architecture diagrams
- `/Development/Architecture/V0_ARCHITECTURE_OVERVIEW.md`: System architecture overview
- `/Development/Architecture/DATA_MODELS.md`: Data structure definitions
- `/Development/Implementation/PLATFORM_ABSTRACTION_PLAN.md`: Detailed platform abstraction design
- `/Development/Implementation/IMPLEMENTATION_PLAN_ADDENDUM.md`: Implementation timeline and integration

### Dependencies
- Docker environment (ENV_002): Partially completed (80%)
- Audio Processing Infrastructure (VOICE_001): Mostly completed (90%)
- Voice Activity Detection (VOICE_002): Completed
- Speech-to-Text Integration (VOICE_003): Completed
- Text-to-Speech Integration (VOICE_004): Completed

## Implementation Structure

Create the following directory structure for the Platform Abstraction Layer:

```
/Development/Implementation/src/
├── core/
│   └── platform/
│       ├── __init__.py
│       ├── capabilities.py    # Capability detection and registry
│       ├── factory.py         # Platform implementation factory
│       ├── interface.py       # Abstract interfaces
│       ├── detection.py       # Runtime platform detection
│       ├── macos/             # macOS-specific implementations
│       │   ├── __init__.py
│       │   ├── audio.py       # macOS audio implementations
│       │   └── utils.py       # macOS utility functions
│       └── linux/             # Linux-specific implementations
│           ├── __init__.py
│           ├── audio.py       # Linux audio implementations (placeholders)
│           └── utils.py       # Linux utility functions
└── voice/
    └── audio/                 # Refactor existing audio components
        ├── __init__.py
        ├── capture.py         # Update to use platform abstraction
        ├── playback.py        # Update to use platform abstraction
        └── preprocessing.py   # Update to use platform abstraction
```

## Implementation Requirements

### 1. Platform Interface Module (interface.py)

Implement abstract base classes for platform-dependent functionality:

- Define clear interfaces for audio I/O operations
- Use abstract methods to enforce implementation requirements
- Include documentation of platform capability requirements
- Design for future extension to other platform-specific features

Example interface:

```python
from abc import ABC, abstractmethod
import numpy as np
from typing import Callable, List, Dict, Any, Optional

class PlatformAudioCapture(ABC):
    """Abstract base class for platform-specific audio capture implementations."""
    
    @abstractmethod
    def initialize(self, sample_rate: int, channels: int, chunk_size: int) -> bool:
        """Initialize platform-specific audio capture resources.
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            chunk_size: Audio buffer chunk size
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start_capture(self) -> bool:
        """Start audio capture on the platform.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop_capture(self) -> None:
        """Stop audio capture and release platform resources."""
        pass
    
    @abstractmethod
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices on this platform.
        
        Returns:
            List of device descriptors with platform-specific details
        """
        pass
    
    @abstractmethod
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select input device by platform-specific identifier.
        
        Args:
            device_id: Platform-specific device identifier
            
        Returns:
            True if device selection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def register_callback(self, callback_fn: Callable[[np.ndarray], None]) -> None:
        """Register callback function to receive audio data.
        
        Args:
            callback_fn: Function to call with new audio data
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get platform-specific capabilities for audio capture.
        
        Returns:
            Dict of capability names to values or feature flags
        """
        pass


class PlatformAudioPlayback(ABC):
    """Abstract base class for platform-specific audio playback implementations."""
    
    @abstractmethod
    def initialize(self, sample_rate: int, channels: int, buffer_size: int) -> bool:
        """Initialize platform-specific audio playback resources.
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            buffer_size: Audio buffer size
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start_playback(self) -> bool:
        """Start audio playback system.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop_playback(self) -> None:
        """Stop audio playback and release platform resources."""
        pass
    
    @abstractmethod
    def play_audio(self, audio_data: np.ndarray) -> int:
        """Play audio data through platform-specific output.
        
        Args:
            audio_data: Audio samples as numpy array
            
        Returns:
            Platform-specific ID for this playback operation
        """
        pass
    
    @abstractmethod
    def stop_audio(self, playback_id: int) -> bool:
        """Stop a specific playback operation.
        
        Args:
            playback_id: Platform-specific playback ID
            
        Returns:
            True if successfully stopped, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio output devices on this platform.
        
        Returns:
            List of device descriptors with platform-specific details
        """
        pass
    
    @abstractmethod
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select output device by platform-specific identifier.
        
        Args:
            device_id: Platform-specific device identifier
            
        Returns:
            True if device selection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get platform-specific capabilities for audio playback.
        
        Returns:
            Dict of capability names to values or feature flags
        """
        pass
```

### 2. Capability Registry Module (capabilities.py)

Implement a system for tracking available platform capabilities:

- Create capability registration mechanism
- Implement feature detection for platform-specific capabilities
- Support environment variable overrides for testing
- Provide status tracking for each capability

Example implementation:

```python
from enum import Enum, auto
from typing import Dict, Any, Optional, Set
import os
import platform
import logging

logger = logging.getLogger(__name__)

class CapabilityStatus(Enum):
    AVAILABLE = auto()
    UNAVAILABLE = auto()
    UNKNOWN = auto()
    SIMULATED = auto()

class PlatformCapabilityRegistry:
    """Registry for tracking platform capabilities."""
    
    def __init__(self):
        """Initialize the capability registry."""
        self._capabilities: Dict[str, CapabilityStatus] = {}
        self._capability_details: Dict[str, Any] = {}
        self._detect_platform()
        
    def _detect_platform(self) -> None:
        """Detect the current platform and initialize basic capabilities."""
        self._platform_type = platform.system().lower()
        self._platform_version = platform.version()
        
        # Register platform as a basic capability
        self.register_capability(f"platform.{self._platform_type}", CapabilityStatus.AVAILABLE)
        
        # Check for environment variable overrides
        for env_var, env_val in os.environ.items():
            if env_var.startswith("VANTA_CAPABILITY_"):
                cap_name = env_var[16:].lower().replace("_", ".")
                status = CapabilityStatus.AVAILABLE if env_val.lower() in ('1', 'true', 'yes') else CapabilityStatus.UNAVAILABLE
                self.register_capability(cap_name, status, {"source": "environment"})
                if status == CapabilityStatus.AVAILABLE:
                    logger.info(f"Capability {cap_name} enabled via environment variable")
                else:
                    logger.info(f"Capability {cap_name} disabled via environment variable")
    
    def register_capability(self, capability: str, status: CapabilityStatus, details: Optional[Dict[str, Any]] = None) -> None:
        """Register a platform capability.
        
        Args:
            capability: Capability identifier (e.g., 'audio.capture.coreaudio')
            status: Availability status of the capability
            details: Optional details about the capability
        """
        self._capabilities[capability] = status
        if details:
            self._capability_details[capability] = details
        logger.debug(f"Registered capability {capability} with status {status}")
    
    def is_available(self, capability: str) -> bool:
        """Check if a capability is available.
        
        Args:
            capability: Capability identifier
            
        Returns:
            True if capability is available, False otherwise
        """
        return self._capabilities.get(capability, CapabilityStatus.UNKNOWN) == CapabilityStatus.AVAILABLE
    
    def get_status(self, capability: str) -> CapabilityStatus:
        """Get the status of a capability.
        
        Args:
            capability: Capability identifier
            
        Returns:
            Status of the capability
        """
        return self._capabilities.get(capability, CapabilityStatus.UNKNOWN)
    
    def get_details(self, capability: str) -> Dict[str, Any]:
        """Get details about a capability.
        
        Args:
            capability: Capability identifier
            
        Returns:
            Dictionary of capability details
        """
        return self._capability_details.get(capability, {})
    
    def get_all_capabilities(self) -> Set[str]:
        """Get all registered capabilities.
        
        Returns:
            Set of capability identifiers
        """
        return set(self._capabilities.keys())
    
    def get_available_capabilities(self) -> Set[str]:
        """Get all available capabilities.
        
        Returns:
            Set of available capability identifiers
        """
        return {cap for cap, status in self._capabilities.items() 
                if status == CapabilityStatus.AVAILABLE}

# Singleton instance
capability_registry = PlatformCapabilityRegistry()
```

### 3. Platform Factory Module (factory.py)

Implement a factory for creating platform-specific implementations:

- Use runtime platform detection to select appropriate implementations
- Support fallback chains for graceful degradation
- Allow override of implementation selection for testing
- Maintain registry of available implementations

Example implementation:

```python
from typing import Dict, Type, Any, Optional, TypeVar, Generic, List, Callable
import logging
from .capabilities import capability_registry, CapabilityStatus
from .interface import PlatformAudioCapture, PlatformAudioPlayback

logger = logging.getLogger(__name__)

T = TypeVar('T')

class PlatformImplementationFactory(Generic[T]):
    """Factory for creating platform-specific implementations."""
    
    def __init__(self, interface_type: Type[T]):
        """Initialize factory for specific interface type.
        
        Args:
            interface_type: The abstract interface type this factory creates
        """
        self._interface_type = interface_type
        self._implementations: Dict[str, Type[T]] = {}
        self._capabilities: Dict[str, List[str]] = {}
        self._fallbacks: Dict[str, List[str]] = {}
        
    def register_implementation(self, name: str, implementation: Type[T],
                               required_capabilities: List[str],
                               fallbacks: Optional[List[str]] = None) -> None:
        """Register implementation with its capabilities.
        
        Args:
            name: Unique name for this implementation
            implementation: Implementation class
            required_capabilities: List of required capability identifiers
            fallbacks: Optional ordered list of fallback implementations
        """
        self._implementations[name] = implementation
        self._capabilities[name] = required_capabilities
        if fallbacks:
            self._fallbacks[name] = fallbacks
        logger.debug(f"Registered {self._interface_type.__name__} implementation: {name}")
        
    def create(self, name: Optional[str] = None, **kwargs) -> Optional[T]:
        """Create instance of the implementation.
        
        Args:
            name: Specific implementation name to use, or None for auto-select
            **kwargs: Arguments to pass to implementation constructor
            
        Returns:
            Instance of the implementation or None if no suitable implementation
        """
        if name is not None:
            # Try to create specific implementation
            if name in self._implementations:
                return self._try_create_implementation(name, **kwargs)
            else:
                logger.error(f"Implementation {name} not found")
                return None
        
        # Auto-select implementation based on capabilities
        for impl_name, capabilities in self._capabilities.items():
            if all(capability_registry.is_available(cap) for cap in capabilities):
                logger.info(f"Selected {self._interface_type.__name__} implementation: {impl_name}")
                impl = self._try_create_implementation(impl_name, **kwargs)
                if impl is not None:
                    return impl
        
        logger.warning(f"No suitable {self._interface_type.__name__} implementation found")
        return None
    
    def _try_create_implementation(self, name: str, **kwargs) -> Optional[T]:
        """Try to create implementation with fallbacks.
        
        Args:
            name: Implementation name to create
            **kwargs: Arguments to pass to implementation constructor
            
        Returns:
            Implementation instance or None if creation failed
        """
        try:
            impl = self._implementations[name](**kwargs)
            logger.debug(f"Created {name} implementation of {self._interface_type.__name__}")
            return impl
        except Exception as e:
            logger.error(f"Failed to create {name} implementation: {str(e)}")
            
            # Try fallbacks if available
            if name in self._fallbacks:
                for fallback in self._fallbacks[name]:
                    logger.info(f"Trying fallback implementation: {fallback}")
                    try:
                        impl = self._implementations[fallback](**kwargs)
                        logger.debug(f"Created fallback {fallback} implementation")
                        return impl
                    except Exception as fallback_e:
                        logger.error(f"Fallback {fallback} also failed: {str(fallback_e)}")
            
            return None

# Factory instances for each interface type
audio_capture_factory = PlatformImplementationFactory(PlatformAudioCapture)
audio_playback_factory = PlatformImplementationFactory(PlatformAudioPlayback)
```

### 4. Platform Detection Module (detection.py)

Implement runtime platform detection:

- Detect operating system type and version
- Identify hardware capabilities
- Check for available libraries and drivers
- Register detected capabilities with the registry

Example implementation:

```python
import platform
import os
import sys
import ctypes
import logging
import subprocess
from typing import Dict, Any, List
from .capabilities import capability_registry, CapabilityStatus

logger = logging.getLogger(__name__)

class PlatformDetector:
    """Detects platform capabilities and registers them."""
    
    def __init__(self):
        """Initialize the platform detector."""
        self._platform_info = self._gather_platform_info()
        
    def _gather_platform_info(self) -> Dict[str, Any]:
        """Gather basic platform information."""
        info = {
            "os": platform.system().lower(),
            "version": platform.version(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }
        
        # Register basic platform capabilities
        capability_registry.register_capability(
            f"platform.{info['os']}", 
            CapabilityStatus.AVAILABLE,
            info
        )
        
        return info
    
    def detect_audio_capabilities(self) -> None:
        """Detect audio-related capabilities for the current platform."""
        if self._platform_info["os"] == "darwin":
            self._detect_macos_audio_capabilities()
        elif self._platform_info["os"] == "linux":
            self._detect_linux_audio_capabilities()
        else:
            logger.warning(f"Audio detection not implemented for {self._platform_info['os']}")
    
    def _detect_macos_audio_capabilities(self) -> None:
        """Detect macOS-specific audio capabilities."""
        # Check for CoreAudio
        try:
            # Try to load CoreAudio framework via ctypes
            audio_framework = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/CoreAudio.framework/CoreAudio"
            )
            capability_registry.register_capability(
                "audio.framework.coreaudio", 
                CapabilityStatus.AVAILABLE
            )
            logger.info("Detected CoreAudio framework")
        except (OSError, AttributeError):
            capability_registry.register_capability(
                "audio.framework.coreaudio", 
                CapabilityStatus.UNAVAILABLE
            )
            logger.warning("CoreAudio framework not available")
        
        # Check for AVFoundation
        try:
            # Try to load AVFoundation framework via ctypes
            avf_framework = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/AVFoundation.framework/AVFoundation"
            )
            capability_registry.register_capability(
                "audio.framework.avfoundation", 
                CapabilityStatus.AVAILABLE
            )
            logger.info("Detected AVFoundation framework")
        except (OSError, AttributeError):
            capability_registry.register_capability(
                "audio.framework.avfoundation", 
                CapabilityStatus.UNAVAILABLE
            )
            logger.warning("AVFoundation framework not available")
        
        # Check for PyAudio with CoreAudio backend
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            device_count = pa.get_device_count()
            pa.terminate()
            
            capability_registry.register_capability(
                "audio.pyaudio", 
                CapabilityStatus.AVAILABLE,
                {"device_count": device_count}
            )
            logger.info(f"Detected PyAudio with {device_count} devices")
        except (ImportError, OSError):
            capability_registry.register_capability(
                "audio.pyaudio", 
                CapabilityStatus.UNAVAILABLE
            )
            logger.warning("PyAudio not available")
    
    def _detect_linux_audio_capabilities(self) -> None:
        """Detect Linux-specific audio capabilities."""
        # Check for PulseAudio
        try:
            result = subprocess.run(
                ["pulseaudio", "--check"], 
                capture_output=True, 
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                capability_registry.register_capability(
                    "audio.pulseaudio", 
                    CapabilityStatus.AVAILABLE
                )
                logger.info("Detected PulseAudio server")
            else:
                capability_registry.register_capability(
                    "audio.pulseaudio", 
                    CapabilityStatus.UNAVAILABLE
                )
                logger.warning("PulseAudio server not running")
        except (subprocess.SubprocessError, FileNotFoundError):
            capability_registry.register_capability(
                "audio.pulseaudio", 
                CapabilityStatus.UNAVAILABLE
            )
            logger.warning("PulseAudio not available")
        
        # Check for ALSA
        try:
            result = subprocess.run(
                ["aplay", "-l"], 
                capture_output=True, 
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                capability_registry.register_capability(
                    "audio.alsa", 
                    CapabilityStatus.AVAILABLE,
                    {"devices": result.stdout}
                )
                logger.info("Detected ALSA audio system")
            else:
                capability_registry.register_capability(
                    "audio.alsa", 
                    CapabilityStatus.UNAVAILABLE
                )
                logger.warning("ALSA audio system not available")
        except (subprocess.SubprocessError, FileNotFoundError):
            capability_registry.register_capability(
                "audio.alsa", 
                CapabilityStatus.UNAVAILABLE
            )
            logger.warning("ALSA audio system not available")

# Run platform detection
platform_detector = PlatformDetector()
```

### 5. macOS Implementation Module (macos/audio.py)

Implement concrete macOS-specific implementations:

- Create implementations for PlatformAudioCapture and PlatformAudioPlayback
- Utilize Core Audio and AVFoundation on macOS
- Handle macOS-specific device enumeration and selection
- Add appropriate error handling for macOS-specific issues

Example implementation (partial):

```python
import numpy as np
import pyaudio
import logging
from typing import List, Dict, Any, Callable, Optional
from ...interface import PlatformAudioCapture, PlatformAudioPlayback
from ...capabilities import capability_registry, CapabilityStatus

logger = logging.getLogger(__name__)

class MacOSAudioCapture(PlatformAudioCapture):
    """macOS implementation of platform audio capture."""
    
    def __init__(self):
        """Initialize macOS audio capture."""
        self._pyaudio = None
        self._stream = None
        self._device_id = None
        self._sample_rate = 16000
        self._channels = 1
        self._chunk_size = 1024
        self._callbacks = []
        self._is_capturing = False
        self._check_capabilities()
    
    def _check_capabilities(self) -> None:
        """Check and register macOS-specific audio capabilities."""
        try:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            capability_registry.register_capability(
                "audio.capture.macos", 
                CapabilityStatus.AVAILABLE
            )
        except (ImportError, OSError) as e:
            logger.error(f"Failed to initialize PyAudio on macOS: {str(e)}")
            capability_registry.register_capability(
                "audio.capture.macos", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
    
    def initialize(self, sample_rate: int, channels: int, chunk_size: int) -> bool:
        """Initialize macOS audio capture resources.
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            chunk_size: Audio buffer chunk size
            
        Returns:
            True if initialization successful, False otherwise
        """
        if not capability_registry.is_available("audio.capture.macos"):
            logger.error("macOS audio capture capability not available")
            return False
        
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size
        return True
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for incoming audio data."""
        if status:
            logger.warning(f"PyAudio status: {status}")
        
        # Convert to numpy array
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        
        # Call registered callbacks
        for callback in self._callbacks:
            try:
                callback(audio_data)
            except Exception as e:
                logger.error(f"Error in audio callback: {str(e)}")
        
        return (in_data, pyaudio.paContinue)
    
    def start_capture(self) -> bool:
        """Start audio capture on macOS.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self._is_capturing:
            logger.warning("Audio capture already started")
            return True
        
        try:
            # Configure PyAudio stream
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self._channels,
                rate=self._sample_rate,
                input=True,
                output=False,
                frames_per_buffer=self._chunk_size,
                input_device_index=self._device_id,
                stream_callback=self._audio_callback
            )
            
            self._stream.start_stream()
            self._is_capturing = True
            logger.info(f"Started macOS audio capture: {self._sample_rate}Hz, {self._channels} channels")
            return True
        except Exception as e:
            logger.error(f"Failed to start macOS audio capture: {str(e)}")
            return False
    
    def stop_capture(self) -> None:
        """Stop audio capture and release platform resources."""
        if not self._is_capturing:
            return
        
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            
            self._is_capturing = False
            logger.info("Stopped macOS audio capture")
        except Exception as e:
            logger.error(f"Error stopping macOS audio capture: {str(e)}")
        
        # Only terminate PyAudio when truly shutting down to avoid reinitialization issues
        # if self._pyaudio:
        #     self._pyaudio.terminate()
        #     self._pyaudio = None
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices on macOS.
        
        Returns:
            List of device descriptors with platform-specific details
        """
        devices = []
        
        if not self._pyaudio:
            logger.error("PyAudio not initialized")
            return devices
        
        try:
            for i in range(self._pyaudio.get_device_count()):
                device_info = self._pyaudio.get_device_info_by_index(i)
                # Only include input devices
                if device_info["maxInputChannels"] > 0:
                    devices.append({
                        "id": i,
                        "name": device_info["name"],
                        "channels": device_info["maxInputChannels"],
                        "default_sample_rate": device_info["defaultSampleRate"],
                        "is_default": device_info.get("isDefaultInputDevice", False)
                    })
        except Exception as e:
            logger.error(f"Error getting macOS audio devices: {str(e)}")
        
        return devices
    
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select input device by macOS-specific identifier.
        
        Args:
            device_id: PyAudio device index as string
            
        Returns:
            True if device selection successful, False otherwise
        """
        if device_id is None:
            # Use default device
            self._device_id = None
            logger.info("Selected default macOS audio input device")
            return True
        
        try:
            index = int(device_id)
            device_info = self._pyaudio.get_device_info_by_index(index)
            if device_info["maxInputChannels"] > 0:
                self._device_id = index
                logger.info(f"Selected macOS audio input device: {device_info['name']}")
                return True
            else:
                logger.error(f"Device {index} is not an input device")
                return False
        except (ValueError, OSError) as e:
            logger.error(f"Error selecting macOS audio device {device_id}: {str(e)}")
            return False
    
    def register_callback(self, callback_fn: Callable[[np.ndarray], None]) -> None:
        """Register callback function to receive audio data.
        
        Args:
            callback_fn: Function to call with new audio data
        """
        if callback_fn not in self._callbacks:
            self._callbacks.append(callback_fn)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get platform-specific capabilities for audio capture.
        
        Returns:
            Dict of capability names to values or feature flags
        """
        caps = {
            "sample_rates": [8000, 16000, 22050, 44100, 48000],
            "bit_depths": [16],
            "channels": [1, 2],
            "api": "CoreAudio"
        }
        
        # Add device-specific capabilities if we have a selected device
        if self._device_id is not None and self._pyaudio:
            try:
                device_info = self._pyaudio.get_device_info_by_index(self._device_id)
                caps["device_sample_rate"] = device_info["defaultSampleRate"]
                caps["device_channels"] = device_info["maxInputChannels"]
            except:
                pass
        
        return caps

# Similarly implement MacOSAudioPlayback class
```

### 6. Linux Implementation Module (linux/audio.py)

Implement placeholder Linux-specific implementations:

- Create skeleton implementations for PlatformAudioCapture and PlatformAudioPlayback
- Document requirements for future Linux implementation
- Provide enough implementation to support runtime testing
- Throw appropriate NotImplementedError with informative messages

Example implementation (partial, placeholder):

```python
import numpy as np
import logging
from typing import List, Dict, Any, Callable, Optional
from ...interface import PlatformAudioCapture, PlatformAudioPlayback
from ...capabilities import capability_registry, CapabilityStatus

logger = logging.getLogger(__name__)

class LinuxAudioCapture(PlatformAudioCapture):
    """Linux implementation of platform audio capture (placeholder)."""
    
    def __init__(self):
        """Initialize Linux audio capture placeholder."""
        logger.warning("Linux audio capture is not fully implemented yet")
        capability_registry.register_capability(
            "audio.capture.linux", 
            CapabilityStatus.UNAVAILABLE,
            {"status": "placeholder implementation"}
        )
    
    def initialize(self, sample_rate: int, channels: int, chunk_size: int) -> bool:
        """Initialize Linux audio capture resources (placeholder).
        
        Args:
            sample_rate: Sampling rate in Hz
            channels: Number of audio channels
            chunk_size: Audio buffer chunk size
            
        Returns:
            False (not implemented)
        """
        logger.warning(
            f"Linux audio capture initialization not implemented "
            f"(sample_rate={sample_rate}, channels={channels}, chunk_size={chunk_size})"
        )
        return False
    
    def start_capture(self) -> bool:
        """Start audio capture on Linux (placeholder).
        
        Returns:
            False (not implemented)
        """
        logger.warning("Linux audio capture start not implemented")
        return False
    
    def stop_capture(self) -> None:
        """Stop audio capture and release platform resources (placeholder)."""
        logger.warning("Linux audio capture stop not implemented")
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices on Linux (placeholder).
        
        Returns:
            Empty list (not implemented)
        """
        logger.warning("Linux audio device enumeration not implemented")
        return []
    
    def select_device(self, device_id: Optional[str] = None) -> bool:
        """Select input device by Linux-specific identifier (placeholder).
        
        Args:
            device_id: Linux device identifier
            
        Returns:
            False (not implemented)
        """
        logger.warning(f"Linux audio device selection not implemented (device_id={device_id})")
        return False
    
    def register_callback(self, callback_fn: Callable[[np.ndarray], None]) -> None:
        """Register callback function to receive audio data (placeholder).
        
        Args:
            callback_fn: Function to call with new audio data
        """
        logger.warning("Linux audio callback registration not implemented")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get platform-specific capabilities for audio capture (placeholder).
        
        Returns:
            Empty dict (not implemented)
        """
        logger.warning("Linux audio capabilities not implemented")
        return {}

# Similarly implement LinuxAudioPlayback placeholder class
```

### 7. Refactoring Existing Audio Components

Update the existing audio capture and playback components to use the platform abstraction layer:

- Modify AudioCapture to use PlatformAudioCapture through factory
- Update AudioPlayback to use PlatformAudioPlayback through factory
- Ensure backward compatibility with existing interfaces
- Add appropriate error handling for platform-specific issues

Example refactoring (partial):

```python
# In src/voice/audio/capture.py
import numpy as np
import logging
from typing import Optional, Callable, Dict, Any
from core.platform.factory import audio_capture_factory
from core.platform.capabilities import capability_registry

logger = logging.getLogger(__name__)

class AudioCapture:
    """Audio capture component using platform abstraction."""
    
    def __init__(self, 
                 sample_rate=16000, 
                 chunk_size=4096, 
                 channels=1, 
                 buffer_seconds=5,
                 platform_impl=None):
        """Initialize audio capture system.
        
        Args:
            sample_rate: Sampling rate in Hz
            chunk_size: Number of frames per buffer
            channels: Number of audio channels (1 for mono)
            buffer_seconds: Size of circular buffer in seconds
            platform_impl: Optional specific platform implementation name
        """
        self._sample_rate = sample_rate
        self._chunk_size = chunk_size
        self._channels = channels
        self._buffer_seconds = buffer_seconds
        self._buffer_size = int(sample_rate * buffer_seconds)
        self._buffer = np.zeros(self._buffer_size, dtype=np.int16)
        self._buffer_index = 0
        self._callbacks = []
        self._is_running = False
        
        # Create platform-specific implementation
        self._platform_capture = audio_capture_factory.create(
            name=platform_impl
        )
        
        if self._platform_capture is None:
            logger.error("Failed to create platform audio capture implementation")
            raise RuntimeError("No suitable audio capture implementation available")
        
        # Initialize platform implementation
        if not self._platform_capture.initialize(
            sample_rate=sample_rate,
            channels=channels,
            chunk_size=chunk_size
        ):
            logger.error("Failed to initialize platform audio capture")
            raise RuntimeError("Audio capture initialization failed")
        
        # Register our buffer update callback
        self._platform_capture.register_callback(self._on_audio_data)
    
    def _on_audio_data(self, audio_data):
        """Handle incoming audio data from platform implementation."""
        # Store in circular buffer
        samples_to_write = len(audio_data)
        space_available = self._buffer_size - self._buffer_index
        
        if samples_to_write <= space_available:
            # Simple case - enough space at the end of the buffer
            self._buffer[self._buffer_index:self._buffer_index+samples_to_write] = audio_data
            self._buffer_index += samples_to_write
        else:
            # Split write - fill to end of buffer then wrap around
            self._buffer[self._buffer_index:] = audio_data[:space_available]
            remaining = samples_to_write - space_available
            self._buffer[:remaining] = audio_data[space_available:]
            self._buffer_index = remaining
        
        # If buffer index reaches the end, wrap around
        if self._buffer_index >= self._buffer_size:
            self._buffer_index = 0
        
        # Call registered callbacks
        for callback in self._callbacks:
            try:
                callback(audio_data)
            except Exception as e:
                logger.error(f"Error in audio callback: {str(e)}")
    
    def start(self):
        """Start audio capture."""
        if self._is_running:
            logger.warning("Audio capture already started")
            return
        
        if self._platform_capture.start_capture():
            self._is_running = True
            logger.info("Started audio capture")
        else:
            logger.error("Failed to start audio capture")
            raise RuntimeError("Failed to start audio capture")
    
    def stop(self):
        """Stop audio capture and release resources."""
        if not self._is_running:
            return
        
        self._platform_capture.stop_capture()
        self._is_running = False
        logger.info("Stopped audio capture")
    
    def get_latest_audio(self, seconds=None):
        """Get the latest N seconds of audio from the buffer."""
        if seconds is None:
            seconds = self._buffer_seconds
        
        samples = min(int(seconds * self._sample_rate), self._buffer_size)
        
        if self._buffer_index >= samples:
            # Simple case - contiguous data available
            return self._buffer[self._buffer_index-samples:self._buffer_index]
        else:
            # Data wraps around the buffer
            end_samples = self._buffer_index
            start_samples = samples - end_samples
            return np.concatenate((
                self._buffer[-start_samples:],
                self._buffer[:end_samples]
            ))
    
    def add_callback(self, callback_fn):
        """Add a callback function that's called with new audio chunks."""
        if callback_fn not in self._callbacks:
            self._callbacks.append(callback_fn)
    
    def remove_callback(self, callback_fn):
        """Remove a previously registered callback function."""
        if callback_fn in self._callbacks:
            self._callbacks.remove(callback_fn)
    
    def get_available_devices(self):
        """Get list of available audio input devices."""
        return self._platform_capture.get_available_devices()
    
    def select_device(self, device_id=None):
        """Select input device."""
        return self._platform_capture.select_device(device_id)

# Similarly refactor AudioPlayback class
```

## Technical Considerations

### Performance
- Use efficient interfaces with minimal overhead
- Avoid excessive copying between platform layer and application code
- Implement caching for platform detection results
- Consider threading implications for platform-specific calls
- Add appropriate synchronization for resource access

### Platform Compatibility
- Focus first on macOS compatibility for development
- Design for future Linux support (Ryzen AI PC)
- Document platform-specific requirements and limitations
- Include detailed error messages for platform-specific issues
- Add platform abstraction test cases

### Error Handling
- Provide meaningful error messages for platform-specific failures
- Implement fallback mechanisms for graceful degradation
- Log detailed platform information for troubleshooting
- Add capability status reporting for runtime diagnostics
- Include platform support recommendations in error messages

## Validation Criteria

The implementation will be considered successful when:

1. Platform abstraction interfaces are well-defined
   - Clear separation between interfaces and implementations
   - Abstract base classes for all platform-dependent components
   - Well-documented capability requirements

2. Platform detection works correctly
   - Accurately detects operating system and version
   - Identifies hardware capabilities
   - Registers platform-specific features
   - Provides environment variable overrides for testing

3. Factory pattern enables platform selection
   - Creates appropriate implementation for current platform
   - Supports fallback chains for graceful degradation
   - Handles missing or incompatible platforms

4. Audio components are refactored for platform abstraction
   - AudioCapture uses PlatformAudioCapture through factory
   - AudioPlayback uses PlatformAudioPlayback through factory
   - Maintains compatibility with existing interfaces
   - Properly handles platform-specific errors

5. macOS implementation is complete and functional
   - Uses native macOS audio APIs
   - Properly handles device enumeration and selection
   - Provides appropriate error handling for macOS-specific issues
   - Maintains performance requirements

6. Linux placeholders provide implementation guidance
   - Clear documentation of Linux implementation requirements
   - Appropriate NotImplementedError exceptions with informative messages
   - Guidance for future Linux implementation

7. Tests validate cross-platform support
   - Unit tests for platform abstraction components
   - Mock implementations for testing
   - Platform-specific test cases with appropriate conditionals

## Resources and References

- PyAudio documentation: http://people.csail.mit.edu/hubert/pyaudio/docs/
- macOS Core Audio documentation: https://developer.apple.com/library/archive/documentation/MusicAudio/Conceptual/CoreAudioOverview/CoreAudioEssentials/CoreAudioEssentials.html
- Linux PulseAudio documentation: https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/Developer/
- Linux ALSA documentation: https://www.alsa-project.org/alsa-doc/alsa-lib/
- Python platform detection: https://docs.python.org/3/library/platform.html
- Factory pattern in Python: https://refactoring.guru/design-patterns/factory-method/python/example

## Implementation Notes

- Start with the interface definitions to establish a clean abstraction
- Implement the capability registry next for platform feature detection
- Create the factory pattern for platform-specific implementation selection
- Implement macOS support first, as it's the primary development platform
- Create placeholder Linux implementations with detailed requirements
- Refactor existing audio components to use the platform abstraction layer
- Add comprehensive testing for all platform abstraction components
- Document platform-specific considerations and limitations

---

**TASK-REF**: PLAT_001 - Platform Abstraction Layer
**CONCEPT-REF**: CON-PLAT-001 - Platform Abstraction Layer
**DOC-REF**: DOC-ARCH-004 - Platform Abstraction Design
**DECISION-REF**: DEC-022-001 - Adopt platform abstraction approach for audio components