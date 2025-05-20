#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform abstraction layer for VANTA.

This package provides platform abstraction to support different operating systems
and hardware configurations while maintaining a consistent API.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

# Import key components for easy access
from .capabilities import capability_registry, CapabilityStatus
from .detection import platform_detector
from .factory import audio_capture_factory, audio_playback_factory
from .interface import PlatformAudioCapture, PlatformAudioPlayback, PlatformHardwareAcceleration

# Initialize platform detection
platform_detector.detect_all_capabilities()

__all__ = [
    'capability_registry',
    'CapabilityStatus',
    'platform_detector',
    'audio_capture_factory',
    'audio_playback_factory',
    'PlatformAudioCapture',
    'PlatformAudioPlayback',
    'PlatformHardwareAcceleration',
]