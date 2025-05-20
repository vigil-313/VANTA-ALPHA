#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS-specific implementations for platform abstraction layer.

This package provides macOS-specific implementations of platform abstractions,
primarily focused on audio processing using CoreAudio and AVFoundation.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

from .audio import MacOSAudioCapture, MacOSAudioPlayback

__all__ = [
    'MacOSAudioCapture',
    'MacOSAudioPlayback',
]