#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple script to test platform abstraction layer natively on macOS.
This script can run in any Python environment without dependencies on test frameworks.
"""

import os
import platform
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("platform_test")

# Add current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import platform abstraction components
try:
    from src.core.platform.capabilities import capability_registry, CapabilityStatus
    from src.core.platform.detection import platform_detector
    from src.core.platform.factory import audio_capture_factory, audio_playback_factory
    print("Successfully imported platform abstraction components")
except ImportError as e:
    print(f"Error importing platform abstraction components: {e}")
    sys.exit(1)

def test_platform_detection():
    """Test platform detection."""
    print(f"Detected platform: {platform.system()}")
    print(f"Available capabilities: {capability_registry.get_available_capabilities()}")
    
    # Run platform detection
    platform_detector.detect_all_capabilities()
    print(f"Available capabilities after detection: {capability_registry.get_available_capabilities()}")
    
    # Check for platform-specific capabilities
    if platform.system() == "Darwin":
        print("Testing macOS-specific capabilities:")
        if capability_registry.is_available("audio.capture.macos"):
            print("- macOS audio capture capability is available")
        else:
            print("- macOS audio capture capability is NOT available")
        
        if capability_registry.is_available("audio.playback.macos"):
            print("- macOS audio playback capability is available")
        else:
            print("- macOS audio playback capability is NOT available")
    elif platform.system() == "Linux":
        print("Testing Linux-specific capabilities:")
        if capability_registry.is_available("audio.capture.linux"):
            print("- Linux audio capture capability is available")
        else:
            print("- Linux audio capture capability is NOT available")
        
        if capability_registry.is_available("audio.playback.linux"):
            print("- Linux audio playback capability is available")
        else:
            print("- Linux audio playback capability is NOT available")
    
    return True

def test_factory_creation():
    """Test factory implementation."""
    print("Testing factory implementation:")
    
    # Check if factories are initialized
    if audio_capture_factory is not None:
        print("- Audio capture factory is initialized")
    else:
        print("- Audio capture factory is NOT initialized")
        return False
    
    if audio_playback_factory is not None:
        print("- Audio playback factory is initialized")
    else:
        print("- Audio playback factory is NOT initialized")
        return False
    
    # Get available implementations
    try:
        capture_impls = audio_capture_factory.get_available_implementations()
        playback_impls = audio_playback_factory.get_available_implementations()
        
        print(f"- Available audio capture implementations: {capture_impls}")
        print(f"- Available audio playback implementations: {playback_impls}")
    except Exception as e:
        print(f"- Error getting implementations: {e}")
        return False
    
    return True

def test_implementation_creation():
    """Test creating implementations."""
    print("Testing implementation creation:")
    
    # Try to create implementations
    try:
        # Try to create audio capture implementation
        capture = audio_capture_factory.create()
        if capture is not None:
            print(f"- Successfully created audio capture implementation: {type(capture).__name__}")
        else:
            print("- Failed to create audio capture implementation")
        
        # Try to create audio playback implementation
        playback = audio_playback_factory.create()
        if playback is not None:
            print(f"- Successfully created audio playback implementation: {type(playback).__name__}")
        else:
            print("- Failed to create audio playback implementation")
    except Exception as e:
        print(f"- Error creating implementations: {e}")
        return False
    
    return True

def run_tests():
    """Run all platform abstraction tests."""
    print("=== Testing Platform Abstraction Layer ===")
    
    success = True
    
    print("\n--- Testing Platform Detection ---")
    if test_platform_detection():
        print("Platform detection tests passed")
    else:
        print("Platform detection tests failed")
        success = False
    
    print("\n--- Testing Factory Creation ---")
    if test_factory_creation():
        print("Factory creation tests passed")
    else:
        print("Factory creation tests failed")
        success = False
    
    print("\n--- Testing Implementation Creation ---")
    if test_implementation_creation():
        print("Implementation creation tests passed")
    else:
        print("Implementation creation tests failed")
        success = False
    
    print("\n=== Test Results ===")
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    
    return success

if __name__ == "__main__":
    run_tests()