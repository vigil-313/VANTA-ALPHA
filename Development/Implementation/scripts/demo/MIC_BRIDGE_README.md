# Microphone Input Bridge for Docker on macOS

This document describes the file-based microphone input bridge implementation for Docker containers running on macOS. This bridge enables Docker containers to access the host's microphone, similar to how the TTS bridge enables containers to use the host's text-to-speech capabilities.

## Overview

Docker containers on macOS cannot directly access the host's microphone due to security and isolation constraints. The microphone bridge solves this by:

1. Running a bridge script on the host that captures audio from the physical microphone
2. Writing audio chunks to a shared directory that is mounted in the Docker container
3. Providing a client library in the container to read these audio chunks
4. Integrating with the VANTA Voice Pipeline through an adapter class

```
┌─────────────────────┐         ┌──────────────────────┐
│  macOS Host         │         │  Docker Container    │
│                     │         │                      │
│  ┌───────────────┐  │         │  ┌────────────────┐  │
│  │ Microphone    │  │         │  │ Voice Pipeline │  │
│  │ Input Device  │  │         │  │ Application    │  │
│  └─────┬─────────┘  │         │  └────────┬───────┘  │
│        │            │         │           │          │
│  ┌─────▼─────────┐  │         │  ┌────────▼───────┐  │
│  │ mic_bridge.sh │  │         │  │ MicBridgeAdapter│  │
│  │ (monitor)     │  │         │  └────────┬───────┘  │
│  └─────┬─────────┘  │  Files  │           │          │
│        │            │  ┌─────►│  ┌────────▼───────┐  │
│  ┌─────▼─────────┐  │  │      │  │ docker_mic     │  │
│  │ /tmp/vanta-   │◄─┼──┘      │  │ _client.py     │  │
│  │ mic-bridge/   │  │         │  └────────────────┘  │
│  └───────────────┘  │         │                      │
└─────────────────────┘         └──────────────────────┘
```

## Components

### 1. Host-side Bridge (`mic_bridge_final.sh`)

This script runs on the macOS host and:
- Creates and monitors a shared directory (`/tmp/vanta-mic-bridge`)
- Watches for control files to start/stop recording
- Captures audio from the system microphone using `ffmpeg`
- Writes audio chunks to the shared directory as WAV files
- Provides status information through a JSON file

**Implementation Note**: After extensive testing, we found that the most reliable approach for capturing audio chunks in macOS is to use sequential ffmpeg processes for each chunk rather than a single segmented recording. The `mic_bridge_final.sh` script implements this approach.

### 2. Container-side Client (`docker_mic_client.py`)

This Python client runs in the Docker container and:
- Monitors the shared directory for new audio files
- Reads and processes audio chunks
- Provides a simple API for audio capture applications
- Handles start/stop recording operations
- Manages audio buffers and file processing

### 3. System Integration (`MicBridgeAdapter` class)

This adapter class integrates with the VANTA Voice Pipeline and:
- Implements the standard audio capture interface
- Manages the microphone client and audio buffers
- Provides audio data to the Voice Pipeline
- Handles configuration, statistics, and error reporting

## Directory Structure

```
/tmp/vanta-mic-bridge/              # Host directory
  control/                          # Control files
    start_recording_{uuid}.ctrl     # Signal to start recording
    stop_recording_{uuid}.ctrl      # Signal to stop recording
    status.json                     # Current status of the bridge
  audio/                            # Audio chunks
    chunk_{timestamp}_{uuid}.wav    # Audio data files
  logs/                             # Log files
    mic_bridge.log                  # Bridge logs
```

## Usage

### Starting the Bridge

Run the microphone bridge script on the host:

```bash
./mic_bridge_final.sh
```

**Note**: Multiple bridge implementations are available:
- `mic_bridge.sh`: Original implementation with ffmpeg segment muxer
- `mic_bridge_minimal.sh`: Simplified implementation for debugging
- `mic_bridge_final.sh`: Recommended implementation with improved reliability

### Docker Container Setup

Mount the bridge directory in your Docker container:

```bash
docker run -v /tmp/vanta-mic-bridge:/host/vanta-mic-bridge my-image
```

### Recording Audio from Container

```python
from docker_mic_client import MicrophoneClient

# Create microphone client
mic = MicrophoneClient(
    bridge_dir="/host/vanta-mic-bridge",
    sample_rate=16000,
    channels=1
)

# Start recording
mic.start_recording()

# Read audio data
audio_data, sample_rate, channels = mic.read_audio(duration=5.0)

# Save audio to a file
mic.save_audio("output.wav", duration=5.0)

# Stop recording
mic.stop_recording()
```

### Integration with Voice Pipeline

To use the microphone bridge with the VANTA Voice Pipeline:

1. Configure the audio capture adapter in your application:

```python
config = {
    "bridge_dir": "/host/vanta-mic-bridge",
    "sample_rate": 16000,
    "channels": 1,
    "chunk_duration": 0.5
}
adapter = MicBridgeAdapter(config)
adapter.initialize()
```

2. Use the adapter for audio capture:

```python
# Start capturing
adapter.start_capture()

# Read audio data
audio_data, sample_rate = adapter.read_audio(duration=3.0)

# Stop capturing
adapter.stop_capture()
```

## Testing

### Basic Test

Test basic microphone bridge functionality:

```bash
./test_mic_bridge_minimal.sh
```

### Direct Microphone Access Test

Test direct microphone access without the bridge:

```bash
./direct_mic_test.sh
```

### Docker Client Test

Test the microphone bridge with the Docker client:

```bash
./test_docker_mic_client.sh
```

### Docker Container Test

Test the microphone bridge from within a Docker container:

```bash
./test_docker_mic_bridge.sh
```

### Voice Pipeline Demo

Run the full voice pipeline demo with both microphone and TTS bridges:

```bash
./run_voice_demo_with_mic_bridge.sh
```

## Limitations

1. **Latency**: There is some additional latency compared to direct microphone access due to the file-based approach
2. **macOS Permissions**: The host script requires microphone permissions on macOS
3. **ffmpeg Dependency**: The bridge relies on ffmpeg being installed on the host
4. **Audio Quality**: The audio is currently captured in 16-bit WAV format, which may need adjustment for specific use cases

## Future Improvements

1. **Lower Latency**: Reduce chunk sizes for more real-time performance
2. **Audio Format Options**: Support for different audio formats and quality settings
3. **More Audio Sources**: Support for selecting specific audio input devices
4. **Compression**: Add audio compression to reduce disk I/O
5. **Websocket Option**: Alternative transport mechanism for lower latency

## Troubleshooting

1. **"No audio input devices found"**: Ensure your macOS has granted microphone permissions to the Terminal app
   - Go to System Settings → Privacy & Security → Microphone and make sure Terminal is enabled
   - You can run `./direct_mic_test.sh` to test microphone access directly
2. **"ffmpeg not found"**: Install ffmpeg on the host: `brew install ffmpeg`
3. **Audio files not appearing**: Check directory permissions and bridge log file
   - Run `ls -la /tmp/vanta-mic-bridge/audio/` to check if files are being created
   - Check the bridge log at `/tmp/vanta-mic-bridge/logs/mic_bridge.log`
4. **Empty or corrupted audio**: Check audio chunk size and format settings
   - Run `ffmpeg -i /tmp/vanta-mic-bridge/audio/chunk_*.wav -af "volumedetect" -f null /dev/null` to check audio levels
   - If audio levels are very low (below -50dB), check your microphone volume settings
5. **"Bridge directory access error"**: Ensure the directory is properly mounted in the Docker container
   - Run `docker exec <container> ls -la /host/vanta-mic-bridge` to verify
6. **"Recording process died unexpectedly"**: The ffmpeg process might be terminated by the system
   - This can happen if there are permission issues or resource constraints
   - Check the bridge log for more information
7. **Client can't find audio files**: Make sure the chunk naming format matches what the client expects
   - The client looks for files matching `chunk_*_{uuid}.wav`
   - Check permissions to ensure the container can read the files