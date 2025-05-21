#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exceptions for streaming response handling.

This module defines exceptions specific to streaming response handling.
"""
# TASK-REF: AM_002 - Streaming Response Handling
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-002 - Streaming Response Handling Implementation

from ..exceptions import APIModelError


class StreamingError(APIModelError):
    """Base class for streaming-related errors."""
    pass


class StreamHandlerError(StreamingError):
    """Error in stream handler execution."""
    pass


class StreamProcessingError(StreamingError):
    """Error in stream processing."""
    pass


class StreamTimeoutError(StreamingError):
    """Timeout during stream processing."""
    pass


class StreamCancelledError(StreamingError):
    """Stream was cancelled."""
    pass


class StreamBufferOverflowError(StreamingError):
    """Stream buffer overflow."""
    pass