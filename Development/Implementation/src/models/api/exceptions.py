#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Model Exceptions for VANTA.

This module defines exceptions specific to API-based language models.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# CONCEPT-REF: CON-AM-003 - API Fallback Mechanisms
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation


class APIModelError(Exception):
    """Base exception for all API model errors."""
    pass


class APIInitializationError(APIModelError):
    """Error during API client initialization."""
    pass


class APICredentialError(APIModelError):
    """Error with API credentials."""
    pass


class APIRequestError(APIModelError):
    """Error with API request."""
    pass


class APIResponseError(APIModelError):
    """Error with API response."""
    pass


class APITimeoutError(APIRequestError):
    """API request timed out."""
    pass


class APIRateLimitError(APIRequestError):
    """API rate limit exceeded."""
    pass


class APIQuotaExceededError(APIRequestError):
    """API quota exceeded."""
    pass


class APIServiceUnavailableError(APIRequestError):
    """API service is temporarily unavailable."""
    pass


class APIAuthenticationError(APICredentialError):
    """API authentication failed."""
    pass


class APIInvalidRequestError(APIRequestError):
    """API request was invalid."""
    pass


class APIInvalidResponseError(APIResponseError):
    """API response was invalid or could not be parsed."""
    pass


class APIContentFilterError(APIResponseError):
    """Content was filtered by the API's content policy."""
    pass


class APIConfigurationError(APIModelError):
    """Error in API configuration."""
    pass