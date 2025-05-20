#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Platform capability registry for tracking available platform features.

This module provides a registry for tracking which platform-specific capabilities
are available at runtime, supporting feature detection, environment overrides,
and capability status tracking.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-001 - Adopt platform abstraction approach for audio components

from enum import Enum, auto
from typing import Dict, Any, Optional, Set
import os
import platform
import logging

logger = logging.getLogger(__name__)


class CapabilityStatus(Enum):
    """Status values for platform capabilities."""
    AVAILABLE = auto()
    UNAVAILABLE = auto()
    UNKNOWN = auto()
    SIMULATED = auto()


class PlatformCapabilityRegistry:
    """Registry for tracking platform capabilities."""
    
    def __init__(self):
        """Initialize the capability registry."""
        self._capabilities: Dict[str, CapabilityStatus] = {}
        self._capability_details: Dict[str, Any] = {}
        self._detect_platform()
        
    def _detect_platform(self) -> None:
        """Detect the current platform and initialize basic capabilities."""
        self._platform_type = platform.system().lower()
        self._platform_version = platform.version()
        
        # Register platform as a basic capability
        self.register_capability(f"platform.{self._platform_type}", CapabilityStatus.AVAILABLE)
        
        # Check for environment variable overrides
        for env_var, env_val in os.environ.items():
            if env_var.startswith("VANTA_CAPABILITY_"):
                # Remove the prefix and convert underscores to dots
                cap_name = env_var[16:].lower().replace("_", ".")
                # Ensure no leading dots
                if cap_name.startswith("."):
                    cap_name = cap_name[1:]
                
                status = CapabilityStatus.AVAILABLE if env_val.lower() in ('1', 'true', 'yes') else CapabilityStatus.UNAVAILABLE
                self.register_capability(cap_name, status, {"source": "environment"})
                
                if status == CapabilityStatus.AVAILABLE:
                    logger.info(f"Capability {cap_name} enabled via environment variable")
                else:
                    logger.info(f"Capability {cap_name} disabled via environment variable")
    
    def register_capability(self, capability: str, status: CapabilityStatus, details: Optional[Dict[str, Any]] = None) -> None:
        """Register a platform capability.
        
        Args:
            capability: Capability identifier (e.g., 'audio.capture.coreaudio')
            status: Availability status of the capability
            details: Optional details about the capability
        """
        self._capabilities[capability] = status
        if details:
            self._capability_details[capability] = details
        logger.debug(f"Registered capability {capability} with status {status}")
    
    def is_available(self, capability: str) -> bool:
        """Check if a capability is available.
        
        Args:
            capability: Capability identifier
            
        Returns:
            True if capability is available, False otherwise
        """
        return self._capabilities.get(capability, CapabilityStatus.UNKNOWN) == CapabilityStatus.AVAILABLE
    
    def get_status(self, capability: str) -> CapabilityStatus:
        """Get the status of a capability.
        
        Args:
            capability: Capability identifier
            
        Returns:
            Status of the capability
        """
        return self._capabilities.get(capability, CapabilityStatus.UNKNOWN)
    
    def get_details(self, capability: str) -> Dict[str, Any]:
        """Get details about a capability.
        
        Args:
            capability: Capability identifier
            
        Returns:
            Dictionary of capability details
        """
        return self._capability_details.get(capability, {})
    
    def get_all_capabilities(self) -> Set[str]:
        """Get all registered capabilities.
        
        Returns:
            Set of capability identifiers
        """
        return set(self._capabilities.keys())
    
    def get_available_capabilities(self) -> Set[str]:
        """Get all available capabilities.
        
        Returns:
            Set of available capability identifiers
        """
        return {cap for cap, status in self._capabilities.items() 
                if status == CapabilityStatus.AVAILABLE}
    
    def get_all_capabilities_with_status(self) -> Dict[str, CapabilityStatus]:
        """Get all capabilities with their status.
        
        Returns:
            Dictionary mapping capability identifiers to status
        """
        return self._capabilities.copy()
    
    def get_platform_type(self) -> str:
        """Get the detected platform type.
        
        Returns:
            Platform type string (e.g., 'darwin', 'linux')
        """
        return self._platform_type
    
    def get_platform_version(self) -> str:
        """Get the detected platform version.
        
        Returns:
            Platform version string
        """
        return self._platform_version


# Singleton instance
capability_registry = PlatformCapabilityRegistry()