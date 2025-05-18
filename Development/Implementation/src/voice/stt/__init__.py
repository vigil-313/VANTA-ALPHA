#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Speech-to-Text module for the VANTA Voice Pipeline.
"""
# TASK-REF: VOICE_003 - Speech-to-Text Integration
# CONCEPT-REF: CON-VANTA-001 - Voice Pipeline
# DOC-REF: DOC-DEV-ARCH-COMP-1 - Voice Pipeline Component Specification
# DECISION-REF: DEC-002-001 - Use Whisper for speech-to-text conversion

from voice.stt.whisper_adapter import WhisperAdapter
from voice.stt.transcriber import Transcriber, TranscriptionQuality, TranscriptionProcessor

__all__ = ['WhisperAdapter', 'Transcriber', 'TranscriptionQuality', 'TranscriptionProcessor']