#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Model Credential Management for VANTA.

This module handles secure management of API credentials.
"""
# TASK-REF: AM_001 - API Model Client
# CONCEPT-REF: CON-AM-001 - API Model Client
# DOC-REF: DOC-PROMPT-AM-001 - API Model Client Implementation

import os
import json
import logging
import platform
from pathlib import Path
from typing import Dict, Optional, Any

from .exceptions import APICredentialError
from .config import get_config_dir

logger = logging.getLogger(__name__)

# Map of provider names to their environment variable names
ENV_VAR_MAPPING = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY"
}


def _get_credential_store_path() -> Path:
    """Get the path to the credential store.
    
    Returns:
        Path to the credential store file
    """
    config_dir = get_config_dir()
    credentials_file = config_dir / "api_credentials.json"
    return credentials_file


def _credential_exists(provider: str) -> bool:
    """Check if credentials exist for a provider.
    
    Args:
        provider: Name of the provider
        
    Returns:
        True if credentials exist, False otherwise
    """
    # Check environment variable first
    env_var = ENV_VAR_MAPPING.get(provider)
    if env_var and os.environ.get(env_var):
        return True
    
    # Check credential store
    credentials_file = _get_credential_store_path()
    if not credentials_file.exists():
        return False
    
    try:
        with open(credentials_file, "r") as f:
            credentials = json.load(f)
            return provider in credentials and credentials[provider] != ""
    except (json.JSONDecodeError, IOError):
        return False


def load_credential(provider: str) -> Optional[str]:
    """Load credentials for a provider.
    
    Args:
        provider: Name of the provider
        
    Returns:
        API key or None if not found
    """
    # Check environment variable first (preferred method)
    env_var = ENV_VAR_MAPPING.get(provider)
    if env_var:
        api_key = os.environ.get(env_var)
        if api_key:
            return api_key
    
    # Check credential store
    credentials_file = _get_credential_store_path()
    if not credentials_file.exists():
        return None
    
    try:
        with open(credentials_file, "r") as f:
            credentials = json.load(f)
            return credentials.get(provider)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load credentials: {str(e)}")
        return None


def save_credential(provider: str, api_key: str) -> None:
    """Save credentials for a provider.
    
    Args:
        provider: Name of the provider
        api_key: API key to save
    """
    credentials_file = _get_credential_store_path()
    credentials = {}
    
    # Load existing credentials
    if credentials_file.exists():
        try:
            with open(credentials_file, "r") as f:
                credentials = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load existing credentials: {str(e)}")
    
    # Update with new credential
    credentials[provider] = api_key
    
    # Save back to file
    try:
        with open(credentials_file, "w") as f:
            json.dump(credentials, f)
        
        # Set restrictive permissions on the file
        if platform.system() != "Windows":
            os.chmod(credentials_file, 0o600)
    except IOError as e:
        raise APICredentialError(f"Failed to save credentials: {str(e)}")


def remove_credential(provider: str) -> bool:
    """Remove credentials for a provider.
    
    Args:
        provider: Name of the provider
        
    Returns:
        True if credentials were removed, False if not found
    """
    credentials_file = _get_credential_store_path()
    if not credentials_file.exists():
        return False
    
    try:
        with open(credentials_file, "r") as f:
            credentials = json.load(f)
        
        if provider in credentials:
            del credentials[provider]
            
            with open(credentials_file, "w") as f:
                json.dump(credentials, f)
            return True
        else:
            return False
    except (json.JSONDecodeError, IOError) as e:
        raise APICredentialError(f"Failed to remove credentials: {str(e)}")


def get_credential(provider: str, config: Optional[Dict[str, Any]] = None) -> str:
    """Get credentials for a provider, trying all available sources.
    
    This function tries multiple sources in order:
    1. Environment variables
    2. Provided config dictionary
    3. Credential store
    
    Args:
        provider: Name of the provider
        config: Optional configuration dictionary that may contain credentials
        
    Returns:
        API key
        
    Raises:
        APICredentialError: If no credentials are found
    """
    # Try environment variable
    env_var = ENV_VAR_MAPPING.get(provider)
    if env_var:
        api_key = os.environ.get(env_var)
        if api_key:
            return api_key
    
    # Try config dictionary
    if config and "api_key" in config:
        return config["api_key"]
    
    # Try credential store
    api_key = load_credential(provider)
    if api_key:
        return api_key
    
    # No credentials found
    raise APICredentialError(
        f"No API key found for {provider}. "
        f"Set the {ENV_VAR_MAPPING.get(provider, 'API_KEY')} environment variable "
        f"or use the save_credential function."
    )