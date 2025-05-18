#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voice Activity Detection module for VANTA Voice Pipeline.

This module provides components for detecting spoken voice in audio streams,
wake word recognition, and managing system activation based on voice input.
"""
# TASK-REF: VOICE_002 - Voice Activity Detection
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-004 - Support multiple activation modes

from voice.vad.detector import VoiceActivityDetector
from voice.vad.activation import WakeWordDetector, ActivationManager, ActivationMode, ActivationState

__all__ = [
    'VoiceActivityDetector',
    'WakeWordDetector',
    'ActivationManager',
    'ActivationMode',
    'ActivationState'
]