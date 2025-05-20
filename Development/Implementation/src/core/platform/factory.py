#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform factory for creating platform-specific implementations.

This module provides factory classes for creating platform-specific component
implementations based on the detected capabilities of the current system.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components
# DECISION-REF: DEC-022-003 - Use factory pattern for platform-specific component creation

from typing import Dict, Type, Any, Optional, TypeVar, Generic, List, Tuple
import logging
import importlib
from .capabilities import capability_registry, CapabilityStatus
from .detection import platform_detector
from .interface import PlatformAudioCapture, PlatformAudioPlayback, PlatformHardwareAcceleration

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
        
        # Ensure platform detection has run
        platform_detector.detect_all_capabilities()
        
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
        suitable_impls = []
        
        for impl_name, capabilities in self._capabilities.items():
            if all(capability_registry.is_available(cap) for cap in capabilities):
                suitable_impls.append((impl_name, len(capabilities)))
        
        if suitable_impls:
            # Sort by number of capabilities (most specific implementation first)
            suitable_impls.sort(key=lambda x: x[1], reverse=True)
            
            # Try each suitable implementation in order
            for impl_name, _ in suitable_impls:
                logger.info(f"Trying {self._interface_type.__name__} implementation: {impl_name}")
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
    
    def get_available_implementations(self) -> List[str]:
        """Get names of all available implementations based on capabilities.
        
        Returns:
            List of implementation names that can be created
        """
        available_impls = []
        
        for impl_name, capabilities in self._capabilities.items():
            if all(capability_registry.is_available(cap) for cap in capabilities):
                available_impls.append(impl_name)
        
        return available_impls


# Lazy loading of platform-specific implementations
def _lazy_register_implementations():
    """Dynamically register platform-specific implementations."""
    platform_type = capability_registry.get_platform_type()
    
    # Create factories
    global audio_capture_factory, audio_playback_factory, hardware_acceleration_factory
    audio_capture_factory = PlatformImplementationFactory(PlatformAudioCapture)
    audio_playback_factory = PlatformImplementationFactory(PlatformAudioPlayback)
    hardware_acceleration_factory = PlatformImplementationFactory(PlatformHardwareAcceleration)
    
    # Register implementations based on platform
    if platform_type == "darwin":
        try:
            # Import macOS-specific implementations
            from .macos.audio import MacOSAudioCapture, MacOSAudioPlayback
            
            # Register macOS audio implementations
            audio_capture_factory.register_implementation(
                "macos", 
                MacOSAudioCapture,
                ["audio.capture.macos", "platform.darwin"],
                fallbacks=[]
            )
            
            audio_playback_factory.register_implementation(
                "macos", 
                MacOSAudioPlayback,
                ["audio.playback.macos", "platform.darwin"],
                fallbacks=[]
            )
            
            logger.info("Registered macOS audio implementations")
        except ImportError as e:
            logger.error(f"Failed to import macOS audio implementations: {e}")
    
    elif platform_type == "linux":
        try:
            # Import Linux-specific implementations
            from .linux.audio import LinuxAudioCapture, LinuxAudioPlayback
            
            # Register Linux audio implementations
            audio_capture_factory.register_implementation(
                "linux", 
                LinuxAudioCapture,
                ["audio.capture.linux", "platform.linux"],
                fallbacks=[]
            )
            
            audio_playback_factory.register_implementation(
                "linux", 
                LinuxAudioPlayback,
                ["audio.playback.linux", "platform.linux"],
                fallbacks=[]
            )
            
            logger.info("Registered Linux audio implementations")
        except ImportError as e:
            logger.error(f"Failed to import Linux audio implementations: {e}")
    
    # Add fallback implementations
    try:
        # Import fallback implementations (not platform-specific)
        from .fallback import FallbackAudioCapture, FallbackAudioPlayback
        
        # Register fallback audio implementations
        audio_capture_factory.register_implementation(
            "fallback", 
            FallbackAudioCapture,
            [],  # No specific capabilities required
            fallbacks=[]
        )
        
        audio_playback_factory.register_implementation(
            "fallback", 
            FallbackAudioPlayback,
            [],  # No specific capabilities required
            fallbacks=[]
        )
        
        logger.info("Registered fallback audio implementations")
    except ImportError as e:
        logger.warning(f"Fallback audio implementations not available: {e}")


# Run detection and lazy registration
platform_detector.detect_all_capabilities()
_lazy_register_implementations()

# Factory instances for each interface type
audio_capture_factory = None
audio_playback_factory = None
hardware_acceleration_factory = None

# Initialize factories
try:
    _lazy_register_implementations()
except Exception as e:
    logger.error(f"Failed to initialize platform factories: {e}")