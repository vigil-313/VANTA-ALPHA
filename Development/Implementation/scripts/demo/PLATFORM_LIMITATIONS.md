# Platform-Specific Limitations and Recommendations

This document outlines known limitations and recommendations for running VANTA on different platforms.

## macOS

### Native Environment

| Component | Status | Notes |
|-----------|--------|-------|
| Audio Capture | ✅ Excellent | Uses CoreAudio for low-latency input |
| Audio Playback | ✅ Excellent | Uses CoreAudio for high-quality output |
| TTS | ✅ Excellent | Can use system voices or API-based voices |
| STT | ✅ Good | Whisper models work well on Apple Silicon |
| Platform Detection | ✅ Excellent | Automatically detects optimal settings |

**Recommendations:**
- Use native environment for best performance on macOS
- On Apple Silicon (M1/M2/M3), use the tensorflow-metal package for GPU acceleration
- When using system TTS, select a high-quality voice like "Samantha" or "Tom"

**Limitations:**
- None significant

### Docker Environment

| Component | Status | Notes |
|-----------|--------|-------|
| Audio Capture | ❌ Limited | No direct access to host microphone |
| Audio Playback | ⚠️ Partial | Requires file-based TTS bridge |
| TTS | ✅ Good | Works via TTS bridge or container-local engines |
| STT | ✅ Good | Whisper models work well |
| Platform Detection | ✅ Good | Falls back to appropriate implementations |

**Recommendations:**
- For TTS functionality, use the file-based TTS bridge (see `DOCKER.md`)
- For audio input, consider using a file-based input bridge (not yet implemented)
- Use the `run_voice_demo_with_tts_bridge.sh` script for testing

**Limitations:**
- No direct access to host audio devices (Docker limitation)
- Microphone input requires external bridging solution

## Linux

### Native Environment

| Component | Status | Notes |
|-----------|--------|-------|
| Audio Capture | ✅ Good | Uses PulseAudio or ALSA |
| Audio Playback | ✅ Good | Uses PulseAudio or ALSA |
| TTS | ⚠️ Variable | Quality depends on installed system voices |
| STT | ✅ Good | Whisper models work well |
| Platform Detection | ✅ Good | Detects PulseAudio/ALSA automatically |

**Recommendations:**
- Install PulseAudio for best audio performance
- For TTS, consider using API-based voices for better quality
- Use the `run_voice_demo_linux.sh` script for optimal settings

**Limitations:**
- System TTS quality varies by distribution
- Some distributions may require additional audio packages

### Docker Environment

| Component | Status | Notes |
|-----------|--------|-------|
| Audio Capture | ⚠️ Limited | Requires PulseAudio socket mounting |
| Audio Playback | ⚠️ Limited | Requires PulseAudio socket mounting |
| TTS | ✅ Good | Works with container-local engines |
| STT | ✅ Good | Whisper models work well |
| Platform Detection | ✅ Good | Falls back to appropriate implementations |

**Recommendations:**
- Mount PulseAudio socket for audio access:
  ```
  docker run -v /run/user/$(id -u)/pulse:/run/user/$(id -u)/pulse ...
  ```
- Set the PULSE_SERVER environment variable:
  ```
  -e PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native
  ```

**Limitations:**
- Audio access requires PulseAudio configuration
- Some Linux distributions may need additional setup

## Windows (WSL2)

| Component | Status | Notes |
|-----------|--------|-------|
| Audio Capture | ❌ Limited | No direct access to host audio |
| Audio Playback | ❌ Limited | No direct access to host audio |
| TTS | ⚠️ Partial | Can use API-based voices |
| STT | ✅ Good | Whisper models work well |
| Platform Detection | ⚠️ Partial | Detects as Linux, not Windows |

**Recommendations:**
- Use API-based TTS instead of system voices
- Consider implementing a file-based audio bridge similar to macOS solution
- For serious usage, run on native Linux or macOS instead

**Limitations:**
- WSL2 has limited audio device access
- Performance may be lower compared to native environments

## Performance Considerations

### Audio Latency

Audio latency varies significantly by platform and implementation:

| Platform | Implementation | Avg. Latency | Notes |
|----------|----------------|--------------|-------|
| macOS | native (CoreAudio) | ~10-20ms | Best overall performance |
| macOS | fallback | ~50-100ms | Acceptable for most use cases |
| Linux | native (PulseAudio) | ~30-50ms | Good performance |
| Linux | fallback | ~50-100ms | Acceptable for most use cases |
| Docker | via bridge | ~100-200ms | Noticeable but usable |

### Memory Usage

Memory usage for audio processing is generally low across all platforms:

- Audio Capture: 10-20MB
- Audio Playback: 10-20MB
- TTS (depending on engine):
  - System: 20-50MB
  - Local models: 150-500MB
  - API-based: 10-20MB

### CPU Usage

CPU usage varies significantly based on the implementation:

| Platform | Component | CPU Usage | Notes |
|----------|-----------|-----------|-------|
| macOS | Audio (CoreAudio) | 1-2% | Very efficient |
| macOS | Audio (fallback) | 2-5% | Still efficient |
| Linux | Audio (PulseAudio) | 2-3% | Efficient |
| Linux | Audio (ALSA) | 3-5% | Slightly higher |
| Docker | Audio via bridge | 3-7% | Higher due to bridging overhead |

## Compatibility Matrix

| Feature | macOS Native | macOS Docker | Linux Native | Linux Docker | Windows WSL2 |
|---------|--------------|--------------|--------------|--------------|--------------|
| Audio Capture | ✅ | ⚠️¹ | ✅ | ⚠️² | ❌ |
| Audio Playback | ✅ | ✅³ | ✅ | ⚠️² | ❌ |
| TTS System Voices | ✅ | ✅³ | ⚠️⁴ | ⚠️⁴ | ❌ |
| TTS Local Models | ✅ | ✅ | ✅ | ✅ | ✅ |
| TTS API Models | ✅ | ✅ | ✅ | ✅ | ✅ |
| STT (Whisper) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Platform Detection | ✅ | ✅ | ✅ | ✅ | ⚠️⁵ |

¹ Requires external bridge (not yet implemented)  
² Requires PulseAudio socket mounting  
³ Requires file-based TTS bridge (implemented)  
⁴ Quality varies by distribution  
⁵ Detected as Linux, not Windows  

## Future Improvements

Planned improvements to address current limitations:

1. **File-based microphone bridge for Docker on macOS**
   - Similar to the TTS bridge but for audio input
   - Will enable full voice pipeline testing in Docker

2. **Enhanced WSL2 audio support**
   - File-based bridging for Windows/WSL2
   - Integration with Windows native voices

3. **AMD hardware acceleration**
   - Optimizations for Ryzen AI PC targets
   - ROCm integration for AMD GPUs

4. **Cross-platform CI testing**
   - Automated testing on all supported platforms
   - Performance regression tracking