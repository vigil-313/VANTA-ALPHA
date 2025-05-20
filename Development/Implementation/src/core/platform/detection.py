#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform detection for identifying capabilities of the current system.

This module detects platform-specific capabilities and registers them with the
capability registry, including operating system features, hardware acceleration,
and available audio subsystems.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

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
        except (OSError, AttributeError) as e:
            capability_registry.register_capability(
                "audio.framework.coreaudio", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            logger.warning(f"CoreAudio framework not available: {e}")
        
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
        except (OSError, AttributeError) as e:
            capability_registry.register_capability(
                "audio.framework.avfoundation", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            logger.warning(f"AVFoundation framework not available: {e}")
        
        # Check for PyAudio with CoreAudio backend
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            device_count = pa.get_device_count()
            devices = []
            for i in range(device_count):
                device_info = pa.get_device_info_by_index(i)
                devices.append({
                    "id": i,
                    "name": device_info["name"],
                    "input_channels": device_info["maxInputChannels"],
                    "output_channels": device_info["maxOutputChannels"],
                    "default_sample_rate": device_info["defaultSampleRate"],
                })
            pa.terminate()
            
            capability_registry.register_capability(
                "audio.pyaudio", 
                CapabilityStatus.AVAILABLE,
                {"device_count": device_count, "devices": devices}
            )
            logger.info(f"Detected PyAudio with {device_count} devices")
            
            # Register audio input capability if we have input devices
            input_devices = [d for d in devices if d["input_channels"] > 0]
            if input_devices:
                capability_registry.register_capability(
                    "audio.capture.macos", 
                    CapabilityStatus.AVAILABLE,
                    {"device_count": len(input_devices)}
                )
                logger.info(f"Detected {len(input_devices)} audio input devices")
            else:
                capability_registry.register_capability(
                    "audio.capture.macos", 
                    CapabilityStatus.UNAVAILABLE,
                    {"error": "No input devices found"}
                )
                logger.warning("No audio input devices detected")
            
            # Register audio output capability if we have output devices
            output_devices = [d for d in devices if d["output_channels"] > 0]
            if output_devices:
                capability_registry.register_capability(
                    "audio.playback.macos", 
                    CapabilityStatus.AVAILABLE,
                    {"device_count": len(output_devices)}
                )
                logger.info(f"Detected {len(output_devices)} audio output devices")
            else:
                capability_registry.register_capability(
                    "audio.playback.macos", 
                    CapabilityStatus.UNAVAILABLE,
                    {"error": "No output devices found"}
                )
                logger.warning("No audio output devices detected")
                
        except (ImportError, OSError) as e:
            capability_registry.register_capability(
                "audio.pyaudio", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            capability_registry.register_capability(
                "audio.capture.macos", 
                CapabilityStatus.UNAVAILABLE,
                {"error": f"PyAudio not available: {str(e)}"}
            )
            capability_registry.register_capability(
                "audio.playback.macos", 
                CapabilityStatus.UNAVAILABLE,
                {"error": f"PyAudio not available: {str(e)}"}
            )
            logger.warning(f"PyAudio not available: {e}")
    
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
                    CapabilityStatus.UNAVAILABLE,
                    {"error": "PulseAudio server not running"}
                )
                logger.warning("PulseAudio server not running")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            capability_registry.register_capability(
                "audio.pulseaudio", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            logger.warning(f"PulseAudio not available: {e}")
        
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
                
                # Register Linux audio capabilities if ALSA is available
                capability_registry.register_capability(
                    "audio.capture.linux", 
                    CapabilityStatus.AVAILABLE,
                    {"backend": "alsa"}
                )
                capability_registry.register_capability(
                    "audio.playback.linux", 
                    CapabilityStatus.AVAILABLE,
                    {"backend": "alsa"}
                )
            else:
                capability_registry.register_capability(
                    "audio.alsa", 
                    CapabilityStatus.UNAVAILABLE,
                    {"error": f"ALSA error: {result.stderr}"}
                )
                logger.warning(f"ALSA audio system not available: {result.stderr}")
                
                # Mark Linux audio capabilities as unavailable if ALSA is not available
                capability_registry.register_capability(
                    "audio.capture.linux", 
                    CapabilityStatus.UNAVAILABLE,
                    {"error": "ALSA not available"}
                )
                capability_registry.register_capability(
                    "audio.playback.linux", 
                    CapabilityStatus.UNAVAILABLE,
                    {"error": "ALSA not available"}
                )
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            capability_registry.register_capability(
                "audio.alsa", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            capability_registry.register_capability(
                "audio.capture.linux", 
                CapabilityStatus.UNAVAILABLE,
                {"error": f"ALSA not available: {str(e)}"}
            )
            capability_registry.register_capability(
                "audio.playback.linux", 
                CapabilityStatus.UNAVAILABLE,
                {"error": f"ALSA not available: {str(e)}"}
            )
            logger.warning(f"ALSA audio system not available: {e}")
    
    def detect_hardware_acceleration(self) -> None:
        """Detect hardware acceleration capabilities."""
        if self._platform_info["os"] == "darwin":
            self._detect_macos_acceleration()
        elif self._platform_info["os"] == "linux":
            self._detect_linux_acceleration()
        else:
            logger.warning(f"Hardware acceleration detection not implemented for {self._platform_info['os']}")
    
    def _detect_macos_acceleration(self) -> None:
        """Detect macOS-specific hardware acceleration."""
        # Check for Metal framework
        try:
            metal_framework = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/Metal.framework/Metal"
            )
            capability_registry.register_capability(
                "acceleration.metal", 
                CapabilityStatus.AVAILABLE
            )
            logger.info("Detected Metal framework")
        except (OSError, AttributeError) as e:
            capability_registry.register_capability(
                "acceleration.metal", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            logger.warning(f"Metal framework not available: {e}")
    
    def _detect_linux_acceleration(self) -> None:
        """Detect Linux-specific hardware acceleration."""
        # Check for CUDA
        try:
            result = subprocess.run(
                ["nvidia-smi"], 
                capture_output=True, 
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                capability_registry.register_capability(
                    "acceleration.cuda", 
                    CapabilityStatus.AVAILABLE,
                    {"info": result.stdout}
                )
                logger.info("Detected NVIDIA GPU with CUDA support")
            else:
                capability_registry.register_capability(
                    "acceleration.cuda", 
                    CapabilityStatus.UNAVAILABLE,
                    {"error": f"nvidia-smi error: {result.stderr}"}
                )
                logger.warning(f"NVIDIA GPU not detected: {result.stderr}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            capability_registry.register_capability(
                "acceleration.cuda", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            logger.debug(f"NVIDIA tools not available: {e}")
        
        # Check for ROCm (AMD)
        try:
            result = subprocess.run(
                ["rocminfo"], 
                capture_output=True, 
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                capability_registry.register_capability(
                    "acceleration.rocm", 
                    CapabilityStatus.AVAILABLE,
                    {"info": result.stdout}
                )
                logger.info("Detected AMD GPU with ROCm support")
            else:
                capability_registry.register_capability(
                    "acceleration.rocm", 
                    CapabilityStatus.UNAVAILABLE,
                    {"error": f"rocminfo error: {result.stderr}"}
                )
                logger.warning(f"AMD GPU not detected: {result.stderr}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            capability_registry.register_capability(
                "acceleration.rocm", 
                CapabilityStatus.UNAVAILABLE,
                {"error": str(e)}
            )
            logger.debug(f"ROCm tools not available: {e}")
    
    def detect_all_capabilities(self) -> None:
        """Detect all platform capabilities."""
        # Detect audio capabilities
        self.detect_audio_capabilities()
        
        # Detect hardware acceleration
        self.detect_hardware_acceleration()
        
        # Log all detected capabilities
        available_caps = capability_registry.get_available_capabilities()
        logger.info(f"Detected {len(available_caps)} available capabilities: {', '.join(available_caps)}")


# Run platform detection
platform_detector = PlatformDetector()