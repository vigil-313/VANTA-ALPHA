#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux-specific implementations for platform abstraction layer (placeholders).

This package provides Linux-specific implementations of platform abstractions,
currently as placeholders to be fully implemented when the Ryzen AI PC arrives.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components
# DECISION-REF: DEC-022-004 - Implement platform abstraction in phases

from .audio import LinuxAudioCapture, LinuxAudioPlayback

__all__ = [
    'LinuxAudioCapture',
    'LinuxAudioPlayback',
]