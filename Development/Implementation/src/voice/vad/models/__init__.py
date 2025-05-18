#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VAD model implementations for VANTA.

This module provides implementations of various VAD models including Silero and Whisper-based VAD.
"""
# TASK-REF: VOICE_002 - Voice Activity Detection
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-004 - Support multiple activation modes

# Import model implementations
from voice.vad.models.silero import SileroVAD
from voice.vad.models.whisper_vad import WhisperVAD

__all__ = [
    'SileroVAD',
    'WhisperVAD'
]