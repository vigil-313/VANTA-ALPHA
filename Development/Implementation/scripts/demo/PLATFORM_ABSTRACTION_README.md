# VANTA Voice Pipeline Demo with Platform Abstraction

This document explains how to use the VANTA Voice Pipeline demo with the new platform abstraction layer capabilities.

## Overview

The platform abstraction layer allows VANTA to run efficiently across different operating systems, particularly macOS and Linux, by providing a consistent interface for platform-dependent functionality. This is especially important for audio operations, which rely heavily on platform-specific APIs.

## Running the Demo

The demo can be run using the provided `run_voice_demo.sh` script:

```bash
# Run with default settings (auto-detect platform)
./run_voice_demo.sh

# Run with specific platform preset
./run_voice_demo.sh --platform native_audio

# Run with custom configuration
./run_voice_demo.sh --config path/to/config.yaml

# Show help
./run_voice_demo.sh --help
```

## Platform Presets

The demo supports the following platform presets:

- **native_audio**: Uses platform-specific optimizations for audio capture and playback
  - On macOS: Uses CoreAudio for low-latency audio
  - On Linux: Uses PulseAudio or ALSA for native audio support
  
- **fallback_audio**: Uses generic implementations that work across all platforms
  - Provides basic audio functionality without platform-specific optimizations
  - Useful for debugging or when native implementations have issues

## Runtime Platform Switching

The demo interface now includes commands for testing different platform implementations:

- Press '**a**' to access the platform configuration menu
- Press '**d**' to list and select available audio devices

## Configuration

You can customize the platform behavior by modifying a YAML configuration file. Here's an example:

```yaml
platform:
  audio_capture:
    preferred_implementation: "macos"  # or "linux", "fallback", or null for auto-select
    fallback_implementations: ["fallback"]
  audio_playback:
    preferred_implementation: "macos"  # or "linux", "fallback", or null for auto-select
    fallback_implementations: ["fallback"]
```

## Implementation Details

The platform abstraction layer uses a factory pattern to create platform-specific implementations:

1. **PlatformImplementationFactory**: Creates appropriate implementations based on detected capabilities
2. **PlatformAudioCapture/PlatformAudioPlayback**: Abstract interfaces implemented by platform-specific classes
3. **MacOSAudioCapture/LinuxAudioCapture**: Platform-specific implementations
4. **FallbackAudioCapture**: Generic implementation for compatibility

## Troubleshooting

If you encounter issues with the platform abstraction layer:

1. **Device Selection Problems**:
   - Use command 'd' to list available devices and select a different one
   - Try switching to the fallback implementation with 'a' → '2'

2. **Audio Latency or Quality Issues**:
   - On macOS, the native implementation should provide the best performance
   - On Linux, try different audio systems if available (PulseAudio vs ALSA)
   - The fallback implementation may have higher latency but better compatibility

3. **Demo Crashes or Errors**:
   - Check the log file for detailed error messages
   - Try running with the fallback implementation to rule out platform-specific issues
   - Verify that the correct Python packages are installed

## Cross-Platform Development

When developing VANTA components:

1. **Use the platform abstraction layer** for all audio operations
2. **Test on multiple platforms** whenever possible
3. **Avoid direct use of platform-specific APIs** outside the abstraction layer
4. **Support graceful fallback** when platform-specific features are unavailable

## Upcoming Features

Future improvements to the platform abstraction layer will include:

1. **Linux-specific optimizations** for the Ryzen AI PC
2. **Hardware acceleration support** on supported platforms
3. **File-based bridge** for Docker audio on macOS
4. **Platform-specific voice synthesis** optimizations