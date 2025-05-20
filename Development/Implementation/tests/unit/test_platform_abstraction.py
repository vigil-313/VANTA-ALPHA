#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the platform abstraction layer.

This module contains tests to validate the platform abstraction layer, including
capability detection, factory pattern, and platform-specific implementations.
"""
# TASK-REF: PLAT_001 - Platform Abstraction Layer
# CONCEPT-REF: CON-PLAT-001 - Platform Abstraction Layer
# DOC-REF: DOC-ARCH-004 - Platform Abstraction Design
# DECISION-REF: DEC-022-003 - Use factory pattern for platform-specific component creation

import os
import unittest
import platform
from unittest import mock
import numpy as np

# Import platform abstraction components
from src.core.platform.capabilities import capability_registry, CapabilityStatus, PlatformCapabilityRegistry
from src.core.platform.detection import platform_detector, PlatformDetector
from src.core.platform.factory import audio_capture_factory, audio_playback_factory
from src.core.platform.interface import PlatformAudioCapture, PlatformAudioPlayback
from src.core.platform.fallback import FallbackAudioCapture, FallbackAudioPlayback


class TestCapabilityRegistry(unittest.TestCase):
    """Test cases for capability registry."""

    def setUp(self):
        """Set up test environment."""
        # Create a fresh registry for testing
        self.registry = capability_registry

    def test_registry_initialized(self):
        """Test that capability registry is properly initialized."""
        platform_type = platform.system().lower()
        self.assertTrue(self.registry.is_available(f"platform.{platform_type}"))
        self.assertEqual(self.registry.get_platform_type(), platform_type)

    def test_register_capability(self):
        """Test registering and querying capabilities."""
        # Register a test capability
        self.registry.register_capability(
            "test.capability.example",
            CapabilityStatus.AVAILABLE,
            {"test": "value"}
        )
        
        # Test capability status
        self.assertTrue(self.registry.is_available("test.capability.example"))
        self.assertEqual(
            self.registry.get_status("test.capability.example"), 
            CapabilityStatus.AVAILABLE
        )
        
        # Test capability details
        details = self.registry.get_details("test.capability.example")
        self.assertEqual(details.get("test"), "value")
        
        # Test changing capability status
        self.registry.register_capability(
            "test.capability.example",
            CapabilityStatus.UNAVAILABLE
        )
        self.assertFalse(self.registry.is_available("test.capability.example"))
        
        # Test nonexistent capability
        self.assertFalse(self.registry.is_available("test.nonexistent.capability"))
        self.assertEqual(
            self.registry.get_status("test.nonexistent.capability"),
            CapabilityStatus.UNKNOWN
        )
        self.assertEqual(self.registry.get_details("test.nonexistent.capability"), {})

    def test_get_available_capabilities(self):
        """Test getting all available capabilities."""
        # Register some test capabilities
        self.registry.register_capability("test.available.1", CapabilityStatus.AVAILABLE)
        self.registry.register_capability("test.available.2", CapabilityStatus.AVAILABLE)
        self.registry.register_capability("test.unavailable.1", CapabilityStatus.UNAVAILABLE)
        
        available_caps = self.registry.get_available_capabilities()
        
        # Test that available capabilities are included
        self.assertIn("test.available.1", available_caps)
        self.assertIn("test.available.2", available_caps)
        
        # Test that unavailable capabilities are not included
        self.assertNotIn("test.unavailable.1", available_caps)

    def test_environment_variable_override(self):
        """Test environment variable override for capabilities."""
        
        # Test direct capability registration first
        test_registry = PlatformCapabilityRegistry()
        test_registry.register_capability("test.direct.capability", CapabilityStatus.AVAILABLE)
        self.assertTrue(test_registry.is_available("test.direct.capability"))
        
        # Now test environment variable override
        with mock.patch.dict(os.environ, {"VANTA_CAPABILITY_TEST_CAPABILITY": "1"}):
            # Create a new registry for the environment test
            env_registry = PlatformCapabilityRegistry()
            self.assertTrue(env_registry.is_available("test.capability"))


class TestPlatformDetection(unittest.TestCase):
    """Test cases for platform detection."""

    def setUp(self):
        """Set up test environment."""
        # Create a fresh detector for testing
        self.detector = platform_detector

    def test_detect_platform_info(self):
        """Test that platform information is correctly detected."""
        platform_type = platform.system().lower()
        self.assertTrue(capability_registry.is_available(f"platform.{platform_type}"))
        
        # Check platform details
        platform_details = capability_registry.get_details(f"platform.{platform_type}")
        self.assertIn("os", platform_details)
        self.assertIn("version", platform_details)
        self.assertIn("architecture", platform_details)

    @unittest.skipIf(platform.system().lower() != "darwin", "macOS-specific test")
    def test_detect_macos_capabilities(self):
        """Test macOS-specific capability detection."""
        # Run detection
        self.detector.detect_audio_capabilities()
        
        # Check for macOS audio capabilities
        self.assertIn("audio.framework.coreaudio", capability_registry.get_all_capabilities())
        self.assertIn("audio.framework.avfoundation", capability_registry.get_all_capabilities())
        
        # If PyAudio is available, check its status
        if "audio.pyaudio" in capability_registry.get_all_capabilities():
            # Just check that the status is either AVAILABLE or UNAVAILABLE
            status = capability_registry.get_status("audio.pyaudio")
            self.assertIn(status, [CapabilityStatus.AVAILABLE, CapabilityStatus.UNAVAILABLE])

    @unittest.skipIf(platform.system().lower() != "linux", "Linux-specific test")
    def test_detect_linux_capabilities(self):
        """Test Linux-specific capability detection."""
        # Run detection
        self.detector.detect_audio_capabilities()
        
        # Check for Linux audio capabilities
        self.assertIn("audio.pulseaudio", capability_registry.get_all_capabilities())
        self.assertIn("audio.alsa", capability_registry.get_all_capabilities())
        
        # Check that audio.capture.linux status is set (whether available or not)
        self.assertIn("audio.capture.linux", capability_registry.get_all_capabilities())


class TestPlatformFactory(unittest.TestCase):
    """Test cases for platform factory pattern."""

    def test_factory_creation(self):
        """Test that factories are correctly initialized."""
        self.assertIsNotNone(audio_capture_factory)
        self.assertIsNotNone(audio_playback_factory)

    @unittest.skipIf(platform.system().lower() != "darwin", "macOS-specific test")
    def test_macos_implementation_availability(self):
        """Test availability of macOS implementations in the factory."""
        available_impls = audio_capture_factory.get_available_implementations()
        
        # If macOS audio is available, check that the implementation is registered
        if capability_registry.is_available("audio.capture.macos"):
            self.assertIn("macos", available_impls)
        
        # If not, ensure fallback is available
        else:
            self.assertIn("fallback", available_impls)

    def test_fallback_implementation(self):
        """Test fallback implementation creation."""
        # Force use of fallback implementation
        capture = audio_capture_factory.create("fallback")
        playback = audio_playback_factory.create("fallback")
        
        # Test that fallback implementations are created correctly
        self.assertIsInstance(capture, FallbackAudioCapture)
        self.assertIsInstance(playback, FallbackAudioPlayback)
        
        # Test basic initialization
        self.assertTrue(capture.initialize(16000, 1, 1024))
        self.assertTrue(playback.initialize(16000, 1, 1024))


class TestPlatformAudioInterfaces(unittest.TestCase):
    """Test cases for platform audio interfaces."""

    def setUp(self):
        """Set up test environment."""
        # Create fallback implementations for testing interface conformance
        self.capture = FallbackAudioCapture()
        self.playback = FallbackAudioPlayback()

    def test_audio_capture_interface(self):
        """Test that audio capture implementation conforms to interface."""
        # Test interface methods
        self.assertTrue(self.capture.initialize(16000, 1, 1024))
        self.assertTrue(self.capture.start_capture())
        self.capture.stop_capture()  # Should not raise
        
        # Test callback registration
        test_callback_called = False
        
        def test_callback(audio_data):
            nonlocal test_callback_called
            test_callback_called = True
            self.assertIsInstance(audio_data, np.ndarray)
        
        self.capture.register_callback(test_callback)
        
        # Test device enumeration
        devices = self.capture.get_available_devices()
        self.assertIsInstance(devices, list)
        if devices:
            self.assertIsInstance(devices[0], dict)
            self.assertIn("id", devices[0])
            self.assertIn("name", devices[0])
        
        # Test device selection
        if devices:
            self.assertTrue(self.capture.select_device(devices[0]["id"]))
        
        # Test capabilities
        capabilities = self.capture.get_capabilities()
        self.assertIsInstance(capabilities, dict)
        self.assertIn("sample_rates", capabilities)

    def test_audio_playback_interface(self):
        """Test that audio playback implementation conforms to interface."""
        # Test interface methods
        self.assertTrue(self.playback.initialize(16000, 1, 1024))
        self.assertTrue(self.playback.start_playback())
        
        # Test audio playback
        test_audio = np.zeros(16000, dtype=np.int16)  # 1 second of silence
        playback_id = self.playback.play_audio(test_audio)
        self.assertIsInstance(playback_id, int)
        
        # Test stopping playback
        if playback_id >= 0:  # Valid playback ID
            self.assertTrue(self.playback.stop_audio(playback_id))
        
        self.playback.stop_playback()  # Should not raise
        
        # Test device enumeration
        devices = self.playback.get_available_devices()
        self.assertIsInstance(devices, list)
        if devices:
            self.assertIsInstance(devices[0], dict)
            self.assertIn("id", devices[0])
            self.assertIn("name", devices[0])
        
        # Test device selection
        if devices:
            self.assertTrue(self.playback.select_device(devices[0]["id"]))
        
        # Test capabilities
        capabilities = self.playback.get_capabilities()
        self.assertIsInstance(capabilities, dict)
        self.assertIn("sample_rates", capabilities)


if __name__ == "__main__":
    unittest.main()